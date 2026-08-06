"""Covers the resource families generated from the OpenAPI spec.

Before these existed, all 6 Pro-gated endpoints and 9 of the 10 Business-gated
ones were unreachable from this SDK: a customer paying $149 for Business could
not call Form 144 or 13F holdings from the client library at all. These tests
pin that the generated methods are wired to the client and hit the paths the
spec declares — a generator that emits a method nobody attached is worth nothing.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from form4api import Form4ApiClient
from form4api._client import AsyncForm4ApiClient
from form4api._generated import Form144Response

BASE = "http://test.local"


@pytest.fixture
def client() -> Form4ApiClient:
    return Form4ApiClient("test-key", base_url=BASE, max_retries=0)


@respx.mock
def test_form144_list_hits_path_and_forwards_params(client: Form4ApiClient) -> None:
    route = respx.get(f"{BASE}/v1/form144").mock(return_value=httpx.Response(200, json=[]))
    client.form144.list(ticker="AAPL", per_page=5)

    request = route.calls.last.request
    assert request.url.path == "/v1/form144"
    assert request.url.params["ticker"] == "AAPL"
    # Numbers are stringified for the query string, not dropped.
    assert request.url.params["per_page"] == "5"


@respx.mock
def test_omits_none_params_rather_than_sending_the_string_none(client: Form4ApiClient) -> None:
    route = respx.get(f"{BASE}/v1/form144").mock(return_value=httpx.Response(200, json=[]))
    client.form144.list(ticker="AAPL", insider_name=None)

    params = route.calls.last.request.url.params
    assert params["ticker"] == "AAPL"
    assert "insider_name" not in params


@respx.mock
def test_holdings_and_managers_are_distinct_endpoints(client: Form4ApiClient) -> None:
    holdings = respx.get(f"{BASE}/v1/holdings").mock(return_value=httpx.Response(200, json=[]))
    managers = respx.get(f"{BASE}/v1/managers").mock(return_value=httpx.Response(200, json=[]))

    client.holdings.list()
    client.holdings.managers()

    assert holdings.calls.last.request.url.path == "/v1/holdings"
    assert managers.calls.last.request.url.path == "/v1/managers"


@respx.mock
def test_congress_exposes_all_four_spec_operations(client: Form4ApiClient) -> None:
    trades = respx.get(f"{BASE}/v1/congress/trades").mock(return_value=httpx.Response(200, json=[]))
    politicians = respx.get(f"{BASE}/v1/congress/politicians").mock(
        return_value=httpx.Response(200, json=[])
    )
    politician = respx.get(f"{BASE}/v1/congress/politicians/nancy-pelosi").mock(
        return_value=httpx.Response(200, json={})
    )
    ticker = respx.get(f"{BASE}/v1/congress/tickers/NVDA").mock(
        return_value=httpx.Response(200, json={})
    )

    client.congress.trades()
    client.congress.politicians()
    client.congress.politician("nancy-pelosi")
    client.congress.ticker("NVDA")

    assert trades.called and politicians.called and politician.called and ticker.called


@respx.mock
def test_previously_unreachable_paid_tier_endpoints(client: Form4ApiClient) -> None:
    scorecard = respx.get(f"{BASE}/v1/insiders/0001234567/scorecard").mock(
        return_value=httpx.Response(200, json={})
    )
    convergence = respx.get(f"{BASE}/v1/signals/convergence").mock(
        return_value=httpx.Response(200, json=[])
    )
    sentiment = respx.get(f"{BASE}/v1/signals/sentiment/NVDA").mock(
        return_value=httpx.Response(200, json={})
    )

    client.insiders.scorecard("0001234567")
    client.signals.convergence()
    client.signals.sentiment("NVDA")

    assert scorecard.called and convergence.called and sentiment.called


@respx.mock
def test_hand_written_surface_still_works_alongside_inherited_methods(
    client: Form4ApiClient,
) -> None:
    # A complete payload: `Company` is the HAND-WRITTEN dataclass in _types.py,
    # which is constructed with Company(**data) and so is strict about missing
    # fields. The generated dataclasses are tolerant by design; this one is not,
    # and that difference is unchanged by the codegen work.
    get = respx.get(f"{BASE}/v1/companies/AAPL").mock(
        return_value=httpx.Response(
            200,
            json={
                "cik": "0000320193",
                "name": "Apple Inc.",
                "ticker": "AAPL",
                "exchange": "NASDAQ",
                "totalFilings": 10,
                "activeInsiders": 3,
                "sicDescription": "Electronic Computers",
                "stateOfIncorporation": "CA",
                "website": "https://apple.com",
            },
        )
    )
    listing = respx.get(f"{BASE}/v1/companies").mock(return_value=httpx.Response(200, json=[]))

    # Curated and hand-written — must not have been renamed by codegen.
    client.companies.get("AAPL")
    # Inherited from the generated base on the same object.
    client.companies.list()

    assert get.called and listing.called


@respx.mock
def test_response_parsing_snake_cases_and_ignores_unknown_fields(client: Form4ApiClient) -> None:
    # The client normalises camelCase to snake_case before the dataclass sees it,
    # and _from_dict drops unknown keys so a backend adding a field cannot break
    # an older SDK.
    respx.get(f"{BASE}/v1/form144").mock(
        return_value=httpx.Response(
            200,
            json=[{"accessionNumber": "0001-25-01", "ticker": "AAPL", "brandNewField": "future"}],
        )
    )
    rows = client.form144.list()

    assert isinstance(rows[0], Form144Response)
    assert rows[0].accession_number == "0001-25-01"
    assert rows[0].ticker == "AAPL"
    assert not hasattr(rows[0], "brand_new_field")


@respx.mock
def test_generated_async_resources_actually_await() -> None:
    """The async client's generated families work.

    Driven through asyncio.run rather than pytest-asyncio so this needs no new
    dev dependency on a published package.

    Contrast with the five hand-written resources, which are sync-only and
    reused on the async client behind a `# type: ignore[arg-type]`: there,
    `Dataclass(**data)` receives a coroutine and raises. That is a pre-existing
    bug tracked separately; generating async variants keeps the new families
    out of it — see the companion test below, which pins the current broken
    behaviour so a fix is visible when it lands.
    """
    respx.get(f"{BASE}/v1/form144").mock(
        return_value=httpx.Response(200, json=[{"ticker": "AAPL"}])
    )

    async def go():
        async with AsyncForm4ApiClient("test-key", base_url=BASE, max_retries=0) as client:
            return await client.form144.list(ticker="AAPL")

    rows = asyncio.run(go())
    assert rows[0].ticker == "AAPL"


@respx.mock
def test_hand_written_resources_are_broken_on_the_async_client() -> None:
    """Pins a PRE-EXISTING bug so it is visible rather than silent.

    AsyncForm4ApiClient reuses the sync hand-written resources behind a
    `# type: ignore[arg-type]`. Its `_get` is a coroutine, so `Company(**data)`
    is handed a coroutine and raises. Every hand-written resource method is
    therefore broken on the async client and always has been — there were no
    async tests, and the type: ignore suppressed the error that would have
    caught it.

    When that is fixed, this test will fail. That is the point: delete it and
    assert the correct behaviour instead.
    """
    respx.get(f"{BASE}/v1/companies/AAPL").mock(
        return_value=httpx.Response(200, json={"ticker": "AAPL"})
    )

    async def go():
        async with AsyncForm4ApiClient("test-key", base_url=BASE, max_retries=0) as client:
            return await client.companies.get("AAPL")

    with pytest.raises(TypeError, match="must be a mapping, not coroutine"):
        asyncio.run(go())
