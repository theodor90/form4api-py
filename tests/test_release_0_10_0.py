"""0.10.0 surface: webhook management, ownership, transaction filters, filed_at.

Driven through the real client with respx, sync and async, like the other test
modules. Responses carry an unknown key to prove `_from_dict` filtering holds on
the new models too.
"""
import asyncio
import hashlib
import hmac
import json

import httpx
import respx

from form4api import Form4ApiClient, verify_webhook
from form4api._client import AsyncForm4ApiClient

BASE = "https://api.form4api.com"
UNKNOWN = {"somethingNewFromTheBackend": 1}


def client() -> Form4ApiClient:
    return Form4ApiClient("test-key", max_retries=0)


def aclient() -> AsyncForm4ApiClient:
    return AsyncForm4ApiClient("test-key", max_retries=0)


SUB = {
    "subscriptionId": 7,
    "url": "https://x.test/h",
    "eventTypes": ["ClusterBuy"],
    "createdAt": "2026-10-01T00:00:00",
    "isActive": False,
    "isReadOnly": False,
    "disabledAt": "2026-10-05T00:00:00",
    "disabledReason": "delivery_failures",
    "lastAttemptAt": "2026-10-05T00:00:00",
    "lastSuccessAt": None,
    "lastStatusCode": 503,
    "lastErrorClass": "HTTP_5XX",
    "authHeaderName": "Authorization",
    **UNKNOWN,
}


@respx.mock
def test_list_exposes_delivery_health_and_ignores_unknown_fields():
    respx.get(f"{BASE}/v1/webhooks").mock(return_value=httpx.Response(200, json=[SUB]))
    [sub] = client().webhooks.list()
    assert sub.disabled_reason == "delivery_failures"
    assert sub.last_status_code == 503
    assert sub.last_error_class == "HTTP_5XX"
    assert sub.auth_header_name == "Authorization"
    assert sub.last_success_at is None


@respx.mock
def test_list_tolerates_an_old_payload_without_the_new_fields():
    old = {"subscriptionId": 1, "url": "u", "eventTypes": [], "createdAt": "c", "isActive": True}
    respx.get(f"{BASE}/v1/webhooks").mock(return_value=httpx.Response(200, json=[old]))
    [sub] = client().webhooks.list()
    assert sub.disabled_at is None and sub.auth_header_name is None and sub.is_read_only is None


@respx.mock
def test_create_sends_auth_header_only_when_given():
    route = respx.post(f"{BASE}/v1/webhooks").mock(
        return_value=httpx.Response(
            200,
            json={"subscriptionId": 1, "url": "u", "eventTypes": [], "secret": "s",
                  "createdAt": "c", "warning": None, "isReadOnly": False,
                  "authHeaderName": "Authorization", **UNKNOWN},
        )
    )
    c = client()
    c.webhooks.create("https://x.test/h", ["ClusterBuy"])
    created = c.webhooks.create(
        "https://x.test/h", ["ClusterBuy"], auth_header={"name": "Authorization", "value": "Bearer t"}
    )
    assert json.loads(route.calls[0].request.content) == {
        "url": "https://x.test/h", "eventTypes": ["ClusterBuy"]}
    assert json.loads(route.calls[1].request.content) == {
        "url": "https://x.test/h", "eventTypes": ["ClusterBuy"],
        "authHeader": {"name": "Authorization", "value": "Bearer t"}}
    assert created.auth_header_name == "Authorization"


@respx.mock
def test_enable_and_test():
    respx.post(f"{BASE}/v1/webhooks/7/enable").mock(
        return_value=httpx.Response(200, json={"subscriptionId": 7, "isActive": True, **UNKNOWN}))
    respx.post(f"{BASE}/v1/webhooks/7/test").mock(
        return_value=httpx.Response(
            200, json={"delivered": False, "statusCode": 0, "durationMs": 12,
                       "error": "NETWORK_ERROR", **UNKNOWN}))
    c = client()
    assert c.webhooks.enable(7).is_active is True
    result = c.webhooks.test(7)
    assert result.delivered is False
    assert result.error == "NETWORK_ERROR"
    assert result.duration_ms == 12


@respx.mock
def test_set_and_delete_auth_header():
    put = respx.put(f"{BASE}/v1/webhooks/7/auth-header").mock(
        return_value=httpx.Response(
            200, json={"subscriptionId": 7, "authHeaderName": "Authorization", **UNKNOWN}))
    delete = respx.delete(f"{BASE}/v1/webhooks/7/auth-header").mock(
        return_value=httpx.Response(204))
    c = client()
    result = c.webhooks.set_auth_header(7, "Authorization", "Bearer t")
    assert json.loads(put.calls[0].request.content) == {"name": "Authorization", "value": "Bearer t"}
    assert result.auth_header_name == "Authorization"
    assert c.webhooks.delete_auth_header(7) is None
    assert delete.called


@respx.mock
def test_async_webhook_methods():
    respx.post(f"{BASE}/v1/webhooks/7/enable").mock(
        return_value=httpx.Response(200, json={"subscriptionId": 7, "isActive": True}))
    respx.post(f"{BASE}/v1/webhooks/7/test").mock(
        return_value=httpx.Response(
            200, json={"delivered": True, "statusCode": 200, "durationMs": 5, "error": None}))
    respx.put(f"{BASE}/v1/webhooks/7/auth-header").mock(
        return_value=httpx.Response(200, json={"subscriptionId": 7, "authHeaderName": "X-Token"}))
    respx.delete(f"{BASE}/v1/webhooks/7/auth-header").mock(return_value=httpx.Response(204))

    async def run():
        async with aclient() as c:
            assert (await c.webhooks.enable(7)).is_active is True
            assert (await c.webhooks.test(7)).delivered is True
            assert (await c.webhooks.set_auth_header(7, "X-Token", "v")).auth_header_name == "X-Token"
            assert await c.webhooks.delete_auth_header(7) is None

    asyncio.run(run())


@respx.mock
def test_ownership_schedule_13dg_sync_and_async():
    route = respx.get(f"{BASE}/v1/ownership/13d-13g").mock(
        return_value=httpx.Response(200, json=[{"accessionNumber": "0001-26-000001", **UNKNOWN}]))
    rows = client().ownership.schedule_13dg(ticker="AAPL", form_type="13D", is_amendment=False)
    assert len(rows) == 1
    params = route.calls[0].request.url.params
    assert params["ticker"] == "AAPL"
    assert params["form_type"] == "13D"
    assert params["is_amendment"].lower() == "false"

    async def run():
        async with aclient() as c:
            return await c.ownership.schedule_13dg(ticker="AAPL")

    assert len(asyncio.run(run())) == 1


@respx.mock
def test_transactions_new_filters_sync():
    route = respx.get(f"{BASE}/v1/transactions").mock(return_value=httpx.Response(200, json=[]))
    client().transactions.list(
        min_return_1d=0.01, max_return_1d=0.5, min_return_1w=0.02, max_return_1w=0.6,
        min_return_1m=0.03, max_return_1m=0.7, min_return_3m=0.0, max_return_3m=0.8,
        min_return_6m=0.05, max_return_6m=0.9, has_returns=False,
        inst_ownership_trend="increasing", role="ten_percent_owner", sort="value",
    )
    p = route.calls[0].request.url.params
    assert p["min_return_1d"] == "0.01"
    assert p["max_return_1d"] == "0.5"
    assert p["min_return_3m"] == "0.0"  # zero is a real threshold, not "unset"
    assert p["max_return_6m"] == "0.9"
    assert p["has_returns"] == "false"
    assert p["inst_ownership_trend"] == "increasing"
    assert p["role"] == "ten_percent_owner"
    assert p["sort"] == "value"


@respx.mock
def test_transactions_new_filters_async_and_paginate():
    route = respx.get(f"{BASE}/v1/transactions").mock(return_value=httpx.Response(200, json=[]))
    list(client().transactions.paginate(sort="value", role="officer", min_return_1m=0.1))
    p = route.calls[0].request.url.params
    assert p["sort"] == "value" and p["role"] == "officer" and p["min_return_1m"] == "0.1"

    async def run():
        async with aclient() as c:
            await c.transactions.list(has_returns=True, inst_ownership_trend="stable")
            async for _ in c.transactions.paginate(sort="date"):
                pass

    asyncio.run(run())
    q = route.calls[1].request.url.params
    assert q["has_returns"] == "true" and q["inst_ownership_trend"] == "stable"
    assert route.calls[2].request.url.params["sort"] == "date"


@respx.mock
def test_transaction_filed_at_is_populated():
    tx = {
        "ticker": "AAPL", "companyName": "Apple", "insiderName": "X", "insiderCik": "1",
        "insiderTitle": None, "isDirector": False, "isOfficer": True, "is10PctOwner": False,
        "accessionNumber": "a", "securityTitle": "Common", "transactionCode": "P",
        "isOpenMarket": True, "is10b5Plan": False, "sharesAmount": 1, "pricePerShare": 1.0,
        "totalValue": 1.0, "sharesOwnedAfter": 1, "directIndirect": "D", "isDerivative": False,
        "transactionDate": "2026-10-01T00:00:00", "periodOfReport": "2026-10-01T00:00:00",
        "filedAt": "2026-10-02T00:00:00", "return1d": 0.01, **UNKNOWN,
    }
    respx.get(f"{BASE}/v1/transactions").mock(return_value=httpx.Response(200, json=[tx]))
    [t] = client().transactions.list()
    assert t.filed_at == "2026-10-02T00:00:00"
    assert t.return1d == 0.01


def test_verify_webhook_roundtrip():
    secret, body = "whsec_test", '{"FilingId":1}'
    sig = "sha256=" + hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    assert verify_webhook(body, sig, secret) is True
    assert verify_webhook(body.encode(), sig, secret) is True
    assert verify_webhook(body + " ", sig, secret) is False
    assert verify_webhook(body, sig, "other") is False
