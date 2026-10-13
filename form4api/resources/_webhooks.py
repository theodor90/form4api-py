from __future__ import annotations

from typing import TYPE_CHECKING

from form4api._types import (
    WebhookAuthHeaderResult,
    WebhookCreated,
    WebhookEnableResult,
    WebhookEvent,
    WebhookSubscription,
    WebhookTestResult,
)

if TYPE_CHECKING:
    from form4api._client import AsyncForm4ApiClient, Form4ApiClient


def _create_body(
    url: str, event_types: list[str], auth_header: dict[str, str] | None
) -> dict:
    body: dict = {"url": url, "eventTypes": event_types}
    if auth_header is not None:
        body["authHeader"] = {"name": auth_header["name"], "value": auth_header["value"]}
    return body


class WebhooksResource:
    def __init__(self, client: Form4ApiClient) -> None:
        self._client = client

    def create(
        self,
        url: str,
        event_types: list[str],
        *,
        auth_header: dict[str, str] | None = None,
    ) -> WebhookCreated:
        """Register a webhook. `event_types` are exact names: TransactionFiled,
        ClusterBuy, ClusterSell, CongressTradeFiled (Starter+), ConvergenceSignal
        (Pro+). `auth_header={"name": ..., "value": ...}` adds one custom header
        (for example `Authorization: Bearer ...`) to every delivery. The signing
        secret in the response is shown once."""
        data = self._client._post("/v1/webhooks", _create_body(url, event_types, auth_header))
        return WebhookCreated._from_dict(data)

    def list(self) -> list[WebhookSubscription]:
        data = self._client._get("/v1/webhooks")
        return [WebhookSubscription._from_dict(item) for item in data]

    def delete(self, subscription_id: int) -> None:
        self._client._delete(f"/v1/webhooks/{subscription_id}")

    def enable(self, subscription_id: int) -> WebhookEnableResult:
        """Re-enable a subscription the system auto-disabled after delivery failures."""
        data = self._client._post(f"/v1/webhooks/{subscription_id}/enable")
        return WebhookEnableResult._from_dict(data)

    def test(self, subscription_id: int) -> WebhookTestResult:
        """Send one synthetic delivery (payload has `"test": true`) to the
        subscription's URL. A failed send is returned (`delivered=False`), not raised."""
        data = self._client._post(f"/v1/webhooks/{subscription_id}/test")
        return WebhookTestResult._from_dict(data)

    def set_auth_header(self, subscription_id: int, name: str, value: str) -> WebhookAuthHeaderResult:
        """Set or replace the custom auth header sent with deliveries. The value is write-only."""
        data = self._client._put(
            f"/v1/webhooks/{subscription_id}/auth-header", {"name": name, "value": value}
        )
        return WebhookAuthHeaderResult._from_dict(data)

    def delete_auth_header(self, subscription_id: int) -> None:
        """Remove the custom auth header. Idempotent; returns None (204, no body)."""
        self._client._delete(f"/v1/webhooks/{subscription_id}/auth-header")

    def events(self, *, since: str | None = None) -> list[WebhookEvent]:
        params: dict[str, str] = {}
        if since is not None:
            params["since"] = since
        data = self._client._get("/v1/webhooks/events", params or None)
        return [WebhookEvent._from_dict(item) for item in data]


class AsyncWebhooksResource:
    """Async twin of WebhooksResource. See AsyncCompaniesResource for the rationale."""

    def __init__(self, client: AsyncForm4ApiClient) -> None:
        self._client = client

    async def create(
        self,
        url: str,
        event_types: list[str],
        *,
        auth_header: dict[str, str] | None = None,
    ) -> WebhookCreated:
        """See `WebhooksResource.create`."""
        data = await self._client._post("/v1/webhooks", _create_body(url, event_types, auth_header))
        return WebhookCreated._from_dict(data)

    async def list(self) -> list[WebhookSubscription]:
        data = await self._client._get("/v1/webhooks")
        return [WebhookSubscription._from_dict(item) for item in data]

    async def delete(self, subscription_id: int) -> None:
        await self._client._delete(f"/v1/webhooks/{subscription_id}")

    async def enable(self, subscription_id: int) -> WebhookEnableResult:
        """See `WebhooksResource.enable`."""
        data = await self._client._post(f"/v1/webhooks/{subscription_id}/enable")
        return WebhookEnableResult._from_dict(data)

    async def test(self, subscription_id: int) -> WebhookTestResult:
        """See `WebhooksResource.test`."""
        data = await self._client._post(f"/v1/webhooks/{subscription_id}/test")
        return WebhookTestResult._from_dict(data)

    async def set_auth_header(
        self, subscription_id: int, name: str, value: str
    ) -> WebhookAuthHeaderResult:
        """See `WebhooksResource.set_auth_header`."""
        data = await self._client._put(
            f"/v1/webhooks/{subscription_id}/auth-header", {"name": name, "value": value}
        )
        return WebhookAuthHeaderResult._from_dict(data)

    async def delete_auth_header(self, subscription_id: int) -> None:
        """See `WebhooksResource.delete_auth_header`."""
        await self._client._delete(f"/v1/webhooks/{subscription_id}/auth-header")

    async def events(self, *, since: str | None = None) -> list[WebhookEvent]:
        params: dict[str, str] = {}
        if since is not None:
            params["since"] = since
        data = await self._client._get("/v1/webhooks/events", params or None)
        return [WebhookEvent._from_dict(item) for item in data]
