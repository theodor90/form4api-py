"""Live contract check: does the real API still match what the SDK expects?

Two halves in one file so the validation logic is shared:

* `validate_instance()` and friends are plain functions, imported by the pytest
  suite (tests/test_contract_validation.py) with no API key and no network.
* `main()` is the live stage of scripts/release_check.py. It is run with the
  python of a throwaway venv that has only the built WHEEL installed, so it
  exercises the installed package, never the source tree.

For every entry in contract/live-calls.json it calls the SDK method, captures the
RAW JSON the API sent (before the client rewrites camelCase to snake_case), and
validates that against the operation's 200 response schema in the live OpenAPI
document. It also checks the SDK call itself succeeded and returned the SDK's
model types.

How the raw JSON is captured: the client keeps one httpx.Client on `_http`, so
a response event hook on it sees every response with no change to the SDK and
no second request (a parallel httpx call would double the quota use and could
disagree with what the SDK actually received). The hook is installed from
outside; the shipped package is untouched. It depends on the private `_http`
attribute, which the stage reports clearly if it ever goes away.

The API key is read from FORM4API_TEST_KEY and is never printed.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_SPEC_URL = "https://api.form4api.com/openapi/v1.json"  # same default as codegen/generate.py
KEY_ENV = "FORM4API_TEST_KEY"
HERE = Path(__file__).resolve().parent
DEFAULT_CALLS = HERE.parent / "contract" / "live-calls.json"

# operation ("VERB /path") -> how the Python SDK exposes it.
#   attr        dotted attribute path on the client
#   positional  contract param names that are passed positionally
#   rename      contract param name -> Python keyword name (the hand-written
#               resources take `per_page`, the spec's `limit` is only an alias)
#   shape       "list" (every element must be `model`) or "one"
#   model       dotted import path of the expected return type
# An operation missing from this table has no SDK method: that is the parity
# failure the live stage reports.
# GET /v1/keys/usage is deliberately absent from live-calls.json and from this
# table: codegen lists GetKeyUsage in SKIP_OPERATIONS (no SDK method by design)
# and the spec declares no 200 schema for it, so there is nothing to call or
# validate. Do not add a usage method just to make a contract entry pass.
BINDINGS: dict[str, dict[str, Any]] = {
    "GET /v1/stats": {"attr": "stats.get", "shape": "one", "model": "form4api._generated.CorpusStats"},
    "GET /v1/transactions": {
        "attr": "transactions.list", "rename": {"limit": "per_page"},
        "shape": "list", "model": "form4api.Transaction",
    },
    "GET /v1/filings": {"attr": "filings.list", "shape": "list", "model": "form4api._generated.FilingResponse"},
    "GET /v1/companies/{ticker}": {
        "attr": "companies.get", "positional": ["ticker"], "shape": "one", "model": "form4api.Company",
    },
    "GET /v1/companies/{ticker}/insiders": {
        "attr": "companies.insiders", "positional": ["ticker"], "shape": "list", "model": "form4api.Insider",
    },
    "GET /v1/insiders": {
        "attr": "insiders.search", "positional": ["name"], "shape": "list", "model": "form4api.Insider",
    },
    "GET /v1/signals": {
        "attr": "signals.list", "rename": {"limit": "per_page"}, "shape": "list", "model": "form4api.InsiderSignal",
    },
    "GET /v1/congress/trades": {
        "attr": "congress.trades", "shape": "list", "model": "form4api._generated.CongressTradeDto",
    },
    "GET /v1/search": {"attr": "search", "positional": ["q"], "shape": "one", "model": "form4api.SearchResults"},
}


# ---------------------------------------------------------------------------
# Pure validation (no network, no key). Shared with the pytest suite.
# ---------------------------------------------------------------------------

def response_schema(spec: dict, path: str, verb: str, status: str = "200") -> dict | None:
    """The JSON schema of `status` for an operation, or None when it declares none."""
    op = spec["paths"][path][verb.lower()]
    resp = op["responses"][status]
    return ((resp.get("content") or {}).get("application/json") or {}).get("schema")


def validate_instance(spec: dict, schema: dict, instance: Any, max_errors: int = 8) -> list[str]:
    """Validate `instance` against an OpenAPI schema; return human-readable errors.

    Strict about types, required fields, enums and OpenAPI 3.0 `nullable`;
    additional properties are allowed (the backend adding a field is not drift
    the SDK needs to fail on). `$ref`s resolve against the spec's components.
    """
    from openapi_schema_validator import (
        OAS30Validator,
        OAS31Validator,
        oas30_format_checker,
        oas31_format_checker,
    )

    openapi = str(spec.get("openapi", "3.0"))
    is31 = openapi.startswith("3.1")
    validator_cls = OAS31Validator if is31 else OAS30Validator
    # Formats are checked too (date-time must carry an RFC 3339 offset), matching the
    # JS gate's ajv-formats. Without this, the 2026-10-05 live run passed a
    # timezone-less "quarter" here while the JS gate failed it.
    format_checker = oas31_format_checker if is31 else oas30_format_checker
    # Embed components in the root so "#/components/schemas/X" resolves.
    root = dict(schema)
    root["components"] = spec.get("components", {})

    grouped: dict[tuple[str, str], int] = {}
    for err in validator_cls(root, format_checker=format_checker).iter_errors(instance):
        where = "/".join("[]" if isinstance(p, int) else str(p) for p in err.absolute_path) or "(root)"
        msg = err.message if len(err.message) <= 160 else err.message[:157] + "..."
        grouped[(where, msg)] = grouped.get((where, msg), 0) + 1

    out = [f"{w}: {m}" + (f"  (x{n})" if n > 1 else "") for (w, m), n in grouped.items()]
    if len(out) > max_errors:
        out = out[:max_errors] + [f"... and {len(out) - max_errors} more distinct errors"]
    return out


def parse_method(method: str) -> tuple[str, str]:
    verb, _, path = method.strip().partition(" ")
    if not verb or not path.startswith("/"):
        raise ValueError(f'bad method {method!r}; expected "GET /v1/path"')
    return verb.upper(), path


def load_calls(path: Path) -> list[dict]:
    calls = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(calls, list):
        raise ValueError("live-calls.json must be a JSON array")
    seen: set[str] = set()
    for c in calls:
        if set(c) != {"id", "method", "params"}:
            raise ValueError(f"entry {c.get('id', c)!r} must have exactly id, method, params")
        if c["id"] in seen:
            raise ValueError(f"duplicate id {c['id']!r}")
        seen.add(c["id"])
        parse_method(c["method"])
    return calls


# ---------------------------------------------------------------------------
# Live stage (runs inside the temp venv).
# ---------------------------------------------------------------------------

def _resolve(dotted: str) -> Any:
    mod, _, name = dotted.rpartition(".")
    return getattr(importlib.import_module(mod), name)


def _fetch_spec(source: str) -> dict:
    if source.startswith("http"):
        req = urllib.request.Request(source, headers={"User-Agent": "form4api-py-release-check"})
        with urllib.request.urlopen(req, timeout=60) as fh:
            return json.load(fh)
    return json.loads(Path(source).read_text(encoding="utf-8"))


def _run_call(client: Any, spec: dict, entry: dict, captured: list) -> str:
    """Run one entry. Returns a one-line PASS detail; raises AssertionError on failure."""
    verb, path = parse_method(entry["method"])
    key = f"{verb} {path}"

    if path not in spec["paths"] or verb.lower() not in spec["paths"][path]:
        raise AssertionError(f"operation {key} is not in the live OpenAPI spec (the API removed or renamed it)")
    binding = BINDINGS.get(key)
    if binding is None:
        raise AssertionError(
            f"PARITY: {key} has no SDK method in the installed form4api package "
            f"(see BINDINGS in scripts/contract_check.py)"
        )

    obj: Any = client
    for part in binding["attr"].split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            raise AssertionError(f"PARITY: SDK method `{binding['attr']}` for {key} does not exist")

    params = dict(entry["params"])
    positional = binding.get("positional", [])
    rename = binding.get("rename", {})
    args = [params.pop(name) for name in positional]
    kwargs = {rename.get(k, k): v for k, v in params.items()}

    del captured[:]
    try:
        result = obj(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - report any SDK failure as a FAIL with its type
        raise AssertionError(f"SDK call {binding['attr']}() raised {type(exc).__name__}: {exc}") from None

    model = _resolve(binding["model"])
    items = result if binding["shape"] == "list" else [result]
    if binding["shape"] == "list" and not isinstance(result, list):
        raise AssertionError(f"{binding['attr']}() returned {type(result).__name__}, expected list")
    bad = [type(i).__name__ for i in items if not isinstance(i, model)]
    if bad:
        raise AssertionError(f"{binding['attr']}() returned {bad[0]} items, expected {model.__name__}")

    ok = [r for r in captured if r.status_code == 200]
    if not ok:
        raise AssertionError("no 200 response was captured for this call")
    raw = ok[-1].json()

    schema = response_schema(spec, path, verb)
    notes = []
    if schema is None:
        notes.append("spec declares no 200 schema, so the response shape is unvalidated")
    else:
        errors = validate_instance(spec, schema, raw)
        if errors:
            raise AssertionError("response does not match the 200 schema:\n      " + "\n      ".join(errors))
    if isinstance(raw, list) and not raw and entry["id"] != "congress-sony":
        notes.append("empty array, nothing validated (WARN)")

    if entry["id"] == "congress-sony":
        flagged = [r for r in raw if r.get("disclosureLagDays") is None and r.get("dateQuality") is not None]
        if not flagged:
            raise AssertionError(
                "regression: expected at least one row with disclosureLagDays null and dateQuality "
                f"non-null among {len(raw)} rows, found none"
            )
        parsed = [m for m in items if m.disclosure_lag_days is None and m.date_quality is not None]
        if not parsed:
            raise AssertionError("SDK model dropped the null lag / date_quality of a flagged row")
        notes.append(f"{len(flagged)} flagged row(s) with null lag")

    count = len(raw) if isinstance(raw, list) else 1
    return f"{count} item(s) validated" + ("; " + "; ".join(notes) if notes else "")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--spec", default=os.environ.get("FORM4API_OPENAPI_URL", DEFAULT_SPEC_URL))
    ap.add_argument("--calls", default=str(DEFAULT_CALLS))
    ap.add_argument("--forbid-root", help="fail if form4api is imported from under this directory")
    args = ap.parse_args(argv)

    key = os.environ.get(KEY_ENV)
    if not key:
        print(f"{KEY_ENV} is not set.")
        return 2

    import form4api

    if args.forbid_root:
        loc = Path(form4api.__file__).resolve()
        root = Path(args.forbid_root).resolve()
        if root in loc.parents:
            print(f"form4api was imported from the source tree ({loc}), not the installed wheel.")
            return 2
    print(f"  form4api {form4api.__version__} from {Path(form4api.__file__).resolve().parent}")

    spec = _fetch_spec(args.spec)
    print(f"  spec: OpenAPI {spec.get('openapi')}, {len(spec['paths'])} paths")
    calls = load_calls(Path(args.calls))

    captured: list = []
    client = form4api.Form4ApiClient(key, max_retries=1, timeout=30.0)
    if not hasattr(client, "_http"):
        print("The client no longer exposes `_http`; update the capture hook in scripts/contract_check.py.")
        return 2
    client._http.event_hooks = {"request": [], "response": [lambda r: (r.read(), captured.append(r))]}

    failures = 0
    try:
        for entry in calls:
            try:
                detail = _run_call(client, spec, entry, captured)
                print(f"  PASS {entry['id']:<24} {detail}")
            except AssertionError as exc:
                failures += 1
                print(f"  FAIL {entry['id']:<24} {exc}")
    finally:
        client.close()

    print(f"  {len(calls) - failures}/{len(calls)} live calls passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
