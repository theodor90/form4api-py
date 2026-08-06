from __future__ import annotations

from typing import TYPE_CHECKING

from form4api._types import WebhookCreated, WebhookEvent, WebhookSubscription

if TYPE_CHECKING:
    from form4api._client import AsyncForm4ApiClient, Form4ApiClient


class WebhooksResource:
    def __init__(self, client: Form4ApiClient) -> None:
        self._client = client

    def create(self, url: str, event_types: list[str]) -> WebhookCreated:
        data = self._client._post("/v1/webhooks", {"url": url, "eventTypes": event_types})
        return WebhookCreated(**data)

    def list(self) -> list[WebhookSubscription]:
        data = self._client._get("/v1/webhooks")
        return [WebhookSubscription(**item) for item in data]

    def delete(self, subscription_id: int) -> None:
        self._client._delete(f"/v1/webhooks/{subscription_id}")

    def events(self, *, since: str | None = None) -> list[WebhookEvent]:
        params: dict[str, str] = {}
        if since is not None:
            params["since"] = since
        data = self._client._get("/v1/webhooks/events", params or None)
        return [WebhookEvent(**item) for item in data]


class AsyncWebhooksResource:
    """Async twin of WebhooksResource. See AsyncCompaniesResource for the rationale."""

    def __init__(self, client: AsyncForm4ApiClient) -> None:
        self._client = client

    async def create(self, url: str, event_types: list[str]) -> WebhookCreated:
        data = await self._client._post("/v1/webhooks", {"url": url, "eventTypes": event_types})
        return WebhookCreated(**data)

    async def list(self) -> list[WebhookSubscription]:
        data = await self._client._get("/v1/webhooks")
        return [WebhookSubscription(**item) for item in data]

    async def delete(self, subscription_id: int) -> None:
        await self._client._delete(f"/v1/webhooks/{subscription_id}")

    async def events(self, *, since: str | None = None) -> list[WebhookEvent]:
        params: dict[str, str] = {}
        if since is not None:
            params["since"] = since
        data = await self._client._get("/v1/webhooks/events", params or None)
        return [WebhookEvent(**item) for item in data]
