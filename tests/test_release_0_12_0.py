"""0.12.0 surface: companies.peers(ticker, limit=None), sync and async."""
import asyncio

import httpx
import respx

import pytest

from form4api import Form4ApiClient
from form4api._client import AsyncForm4ApiClient
from form4api._errors import NotFoundError

BASE = "https://api.form4api.com"

PEER = {
    "ticker": "DELL",
    "name": "Dell Technologies Inc.",
    "cik": "0001571996",
    "sicCode": "3571",
    "filings12m": 42,
    "matchLevel": "sic4",
    "somethingNewFromTheBackend": 1,
}
BODY = {
    "ticker": "AAPL",
    "sicCode": "3571",
    "sicDescription": "Electronic Computers",
    "basis": "sic4",
    "peers": [PEER],
}


def client() -> Form4ApiClient:
    return Form4ApiClient("test-key", max_retries=0)


def aclient() -> AsyncForm4ApiClient:
    return AsyncForm4ApiClient("test-key", max_retries=0)


@respx.mock
def test_peers_happy_path_parses_models():
    route = respx.get(f"{BASE}/v1/companies/AAPL/peers").mock(return_value=httpx.Response(200, json=BODY))
    res = client().companies.peers("AAPL")
    req = route.calls.last.request
    assert req.url.path == "/v1/companies/AAPL/peers"
    assert "limit" not in req.url.params
    assert res.basis == "sic4"
    assert res.sic_description == "Electronic Computers"
    assert res.peers[0].ticker == "DELL"
    assert res.peers[0].filings12m == 42
    assert res.peers[0].match_level == "sic4"
    assert res.peers[0].sic_code == "3571"


@respx.mock
def test_peers_passes_limit_through():
    route = respx.get(f"{BASE}/v1/companies/AAPL/peers").mock(return_value=httpx.Response(200, json=BODY))
    client().companies.peers("AAPL", limit=5)
    assert route.calls.last.request.url.params["limit"] == "5"


@respx.mock
def test_peers_empty_list_without_sic_code():
    body = {"ticker": "XYZ", "sicCode": None, "sicDescription": None, "basis": "none", "peers": []}
    respx.get(f"{BASE}/v1/companies/XYZ/peers").mock(return_value=httpx.Response(200, json=body))
    res = client().companies.peers("XYZ")
    assert res.sic_code is None
    assert res.basis == "none"
    assert res.peers == []


@respx.mock
def test_peers_404_raises_not_found():
    respx.get(f"{BASE}/v1/companies/ZZZZ/peers").mock(
        return_value=httpx.Response(404, json={"error": {"code": "NOT_FOUND", "message": "Unknown ticker"}})
    )
    with pytest.raises(NotFoundError):
        client().companies.peers("ZZZZ")


@respx.mock
def test_peers_async_happy_path_and_limit():
    route = respx.get(f"{BASE}/v1/companies/AAPL/peers").mock(return_value=httpx.Response(200, json=BODY))

    async def run():
        async with aclient() as c:
            return await c.companies.peers("AAPL", limit=3)

    res = asyncio.run(run())
    assert route.calls.last.request.url.params["limit"] == "3"
    assert res.peers[0].ticker == "DELL"


@respx.mock
def test_peers_async_404_raises_not_found():
    respx.get(f"{BASE}/v1/companies/ZZZZ/peers").mock(
        return_value=httpx.Response(404, json={"error": {"code": "NOT_FOUND", "message": "Unknown ticker"}})
    )

    async def run():
        async with aclient() as c:
            await c.companies.peers("ZZZZ")

    with pytest.raises(NotFoundError):
        asyncio.run(run())
