"""0.11.0 surface: webhooks.update(id, url) and url_warning, sync and async."""
import asyncio
import json

import httpx
import pytest
import respx

from form4api import Form4ApiClient
from form4api._client import AsyncForm4ApiClient
from form4api._errors import Form4ApiError, NotFoundError

BASE = "https://api.form4api.com"
UNKNOWN = {"somethingNewFromTheBackend": 1}


def client() -> Form4ApiClient:
    return Form4ApiClient("test-key", max_retries=0)


def aclient() -> AsyncForm4ApiClient:
    return AsyncForm4ApiClient("test-key", max_retries=0)


SUB = {
    "subscriptionId": 7,
    "url": "https://abc.ngrok.io/h",
    "eventTypes": ["ClusterBuy"],
    "createdAt": "2026-10-01T00:00:00",
    "isActive": False,
    "isReadOnly": False,
    "disabledAt": "2026-10-05T00:00:00",
    "disabledReason": "delivery_failures",
    "lastAttemptAt": None,
    "lastSuccessAt": None,
    "lastStatusCode": None,
    "lastErrorClass": None,
    "authHeaderName": None,
    "urlWarning": "Temporary tunnel host",
    **UNKNOWN,
}


@respx.mock
def test_update_sends_patch_with_url_and_returns_parsed_row():
    route = respx.patch(f"{BASE}/v1/webhooks/7").mock(return_value=httpx.Response(200, json=SUB))
    sub = client().webhooks.update(7, "https://abc.ngrok.io/h")
    req = route.calls.last.request
    assert req.method == "PATCH"
    assert req.url.path == "/v1/webhooks/7"
    assert json.loads(req.content) == {"url": "https://abc.ngrok.io/h"}
    assert sub.subscription_id == 7
    assert sub.url == "https://abc.ngrok.io/h"
    assert sub.url_warning == "Temporary tunnel host"
    assert sub.disabled_reason == "delivery_failures"
    assert sub.last_attempt_at is None


@respx.mock
def test_update_400_raises_with_error_code():
    respx.patch(f"{BASE}/v1/webhooks/7").mock(
        return_value=httpx.Response(
            400, json={"error": {"code": "INSECURE_URL", "message": "URL must use HTTPS"}}
        )
    )
    with pytest.raises(Form4ApiError) as exc:
        client().webhooks.update(7, "http://example.com/h")
    assert exc.value.status_code == 400
    assert exc.value.error_code == "INSECURE_URL"


@respx.mock
def test_update_404_raises_not_found():
    respx.patch(f"{BASE}/v1/webhooks/99").mock(
        return_value=httpx.Response(404, json={"error": {"code": "NOT_FOUND", "message": "nope"}})
    )
    with pytest.raises(NotFoundError):
        client().webhooks.update(99, "https://example.com/h")


@respx.mock
def test_update_async_sends_patch_and_parses():
    route = respx.patch(f"{BASE}/v1/webhooks/7").mock(return_value=httpx.Response(200, json=SUB))

    async def run():
        c = aclient()
        try:
            return await c.webhooks.update(7, "https://abc.ngrok.io/h")
        finally:
            await c.close()

    sub = asyncio.run(run())
    req = route.calls.last.request
    assert req.method == "PATCH"
    assert json.loads(req.content) == {"url": "https://abc.ngrok.io/h"}
    assert sub.url_warning == "Temporary tunnel host"


@respx.mock
def test_update_async_400_raises_with_error_code():
    respx.patch(f"{BASE}/v1/webhooks/7").mock(
        return_value=httpx.Response(
            400, json={"error": {"code": "PRIVATE_ADDRESS", "message": "private"}}
        )
    )

    async def run():
        c = aclient()
        try:
            await c.webhooks.update(7, "https://10.0.0.1/h")
        finally:
            await c.close()

    with pytest.raises(Form4ApiError) as exc:
        asyncio.run(run())
    assert exc.value.error_code == "PRIVATE_ADDRESS"


@respx.mock
def test_url_warning_parses_on_create():
    respx.post(f"{BASE}/v1/webhooks").mock(
        return_value=httpx.Response(
            200,
            json={
                "subscriptionId": 8,
                "url": "https://x.trycloudflare.com/h",
                "eventTypes": ["ClusterBuy"],
                "secret": "s",
                "createdAt": "2026-10-13T00:00:00",
                "warning": "Store the secret securely",
                "urlWarning": "Temporary tunnel host",
                **UNKNOWN,
            },
        )
    )
    created = client().webhooks.create("https://x.trycloudflare.com/h", ["ClusterBuy"])
    assert created.url_warning == "Temporary tunnel host"


@respx.mock
def test_url_warning_parses_on_list_and_defaults_to_none_for_old_payloads():
    old = {k: v for k, v in SUB.items() if k != "urlWarning"}
    respx.get(f"{BASE}/v1/webhooks").mock(
        return_value=httpx.Response(200, json=[SUB, {**old, "subscriptionId": 9}, {**SUB, "subscriptionId": 10, "urlWarning": None}])
    )
    subs = client().webhooks.list()
    assert subs[0].url_warning == "Temporary tunnel host"
    assert subs[1].url_warning is None
    assert subs[2].url_warning is None
