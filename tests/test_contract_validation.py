"""Offline tests for the live-contract validator (scripts/contract_check.py).

The live stage of scripts/release_check.py compares real API responses with the
OpenAPI spec. That needs a key, so CI cannot run it, but the validator itself
can be proven here with a saved row and a trimmed copy of the spec. The case
that motivated it: `disclosureLagDays` became nullable on the API, and nothing
in the mocked suite would have noticed had it not.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from form4api import Form4ApiClient
from form4api._generated import CongressTradeDto

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

_spec = importlib.util.spec_from_file_location("contract_check", ROOT / "scripts" / "contract_check.py")
contract_check = importlib.util.module_from_spec(_spec)
sys.modules["contract_check"] = contract_check
_spec.loader.exec_module(contract_check)  # type: ignore[union-attr]

pytest.importorskip("openapi_schema_validator", reason="install the dev extra: pip install -e '.[dev]'")

PATH, VERB = "/v1/congress/trades", "GET"


@pytest.fixture
def spec() -> dict:
    return json.loads((FIXTURES / "congress_spec.json").read_text(encoding="utf-8"))


@pytest.fixture
def null_lag_row() -> dict:
    row = json.loads((FIXTURES / "congress_trade_null_lag.json").read_text(encoding="utf-8"))
    assert row["disclosureLagDays"] is None and row["dateQuality"] is not None  # the point of the fixture
    return row


def _errors(spec: dict, payload: object) -> list[str]:
    schema = contract_check.response_schema(spec, PATH, VERB)
    assert schema is not None
    return contract_check.validate_instance(spec, schema, payload)


def test_null_lag_passes_against_the_current_nullable_spec(spec: dict, null_lag_row: dict) -> None:
    assert _errors(spec, [null_lag_row]) == []


def test_null_lag_fails_when_the_spec_says_not_nullable(spec: dict, null_lag_row: dict) -> None:
    """The regression case: a spec that does not allow null must reject a null lag."""
    stale = copy.deepcopy(spec)
    lag = stale["components"]["schemas"]["CongressTradeDto"]["properties"]["disclosureLagDays"]
    assert lag.pop("nullable") is True  # the live spec really does declare it nullable

    errors = _errors(stale, [null_lag_row])
    assert errors, "a null lag against a non-nullable field must fail validation"
    assert any("disclosureLagDays" in e and "integer" in e for e in errors), errors


def test_wrong_type_fails(spec: dict, null_lag_row: dict) -> None:
    null_lag_row["disclosureLagDays"] = "12"
    assert any("disclosureLagDays" in e for e in _errors(spec, [null_lag_row]))


def test_missing_required_field_fails(spec: dict, null_lag_row: dict) -> None:
    del null_lag_row["dateQuality"]
    assert any("dateQuality" in e for e in _errors(spec, [null_lag_row]))


def test_nested_ref_is_resolved_and_checked(spec: dict, null_lag_row: dict) -> None:
    null_lag_row["politician"]["state"] = None  # `state` is required and not nullable
    assert any("politician/state" in e for e in _errors(spec, [null_lag_row]))


def test_date_time_without_offset_fails() -> None:
    """Formats are enforced, matching the JS gate. The live API returned
    "2026-06-30T00:00:00" (no offset) for a date-time field on 2026-10-05; RFC 3339
    requires an offset, and JS parses an offset-less value as local time."""
    tiny = {"openapi": "3.0.1", "components": {}}
    schema = {"type": "object", "properties": {"quarter": {"type": "string", "format": "date-time"}}}
    assert contract_check.validate_instance(tiny, schema, {"quarter": "2026-06-30T00:00:00Z"}) == []
    errors = contract_check.validate_instance(tiny, schema, {"quarter": "2026-06-30T00:00:00"})
    assert any("quarter" in e and "date-time" in e for e in errors), errors


def test_additional_properties_are_allowed(spec: dict, null_lag_row: dict) -> None:
    null_lag_row["somethingTheBackendAddedLater"] = {"any": "shape"}
    assert _errors(spec, [null_lag_row]) == []


def test_sdk_model_keeps_the_null_lag(null_lag_row: dict) -> None:
    """Same row through the SDK's own parsing path: None must survive."""
    from form4api._client import _normalise

    trade = CongressTradeDto._from_dict(_normalise(null_lag_row))
    assert trade.disclosure_lag_days is None
    assert trade.date_quality == "transaction_after_disclosure"


def test_live_calls_file_is_well_formed_and_bound_methods_exist() -> None:
    calls = contract_check.load_calls(ROOT / "contract" / "live-calls.json")
    assert len(calls) == 9
    client = Form4ApiClient("k")
    for call in calls:
        verb, path = contract_check.parse_method(call["method"])
        binding = contract_check.BINDINGS.get(f"{verb} {path}")
        if binding is None:
            continue  # reported as a parity gap by the live stage
        obj = client
        for part in binding["attr"].split("."):
            obj = getattr(obj, part)
        assert callable(obj)
        assert contract_check._resolve(binding["model"]) is not None
