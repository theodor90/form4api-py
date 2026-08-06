from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

from collections.abc import AsyncGenerator

from form4api._generated import GeneratedAsyncSignalsResource, GeneratedSignalsResource
from form4api._types import InsiderSignal

if TYPE_CHECKING:
    from form4api._client import AsyncForm4ApiClient, Form4ApiClient


def _list_params(
    ticker: str | None,
    cluster_buy: bool | None,
    cluster_sell: bool | None,
    page: int,
    per_page: int,
) -> dict[str, str]:
    """Shared by the sync and async twins so the request shape cannot drift."""
    params: dict[str, str] = {"page": str(page), "per_page": str(per_page)}
    if ticker is not None:
        params["ticker"] = ticker
    if cluster_buy is not None:
        params["cluster_buy"] = str(cluster_buy).lower()
    if cluster_sell is not None:
        params["cluster_sell"] = str(cluster_sell).lower()
    return params


# Extends the generated base rather than replacing it, so spec-derived
# methods (explain(), sentiment(), convergence()) arrive by regenerating while the curated
# signatures below stay exactly as published on PyPI. Move an operation out
# of HANDLED_BY_HANDWRITTEN in codegen/generate.py to let codegen own it.
class SignalsResource(GeneratedSignalsResource):
    def __init__(self, client: Form4ApiClient) -> None:
        self._client = client

    def list(
        self,
        *,
        ticker: str | None = None,
        cluster_buy: bool | None = None,
        cluster_sell: bool | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> list[InsiderSignal]:
        params = _list_params(ticker, cluster_buy, cluster_sell, page, per_page)
        data = self._client._get("/v1/signals", params)
        return [InsiderSignal(**item) for item in data]

    def paginate(
        self,
        *,
        ticker: str | None = None,
        cluster_buy: bool | None = None,
        cluster_sell: bool | None = None,
        per_page: int = 100,
    ) -> Generator[list[InsiderSignal], None, None]:
        page = 1
        while True:
            batch = self.list(
                ticker=ticker, cluster_buy=cluster_buy, cluster_sell=cluster_sell,
                page=page, per_page=per_page,
            )
            if not batch:
                break
            yield batch
            if len(batch) < per_page:
                break
            page += 1





class AsyncSignalsResource(GeneratedAsyncSignalsResource):
    """Async twin of SignalsResource. See AsyncCompaniesResource for the rationale."""

    def __init__(self, client: AsyncForm4ApiClient) -> None:
        self._client = client

    async def list(
        self,
        *,
        ticker: str | None = None,
        cluster_buy: bool | None = None,
        cluster_sell: bool | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> list[InsiderSignal]:
        params = _list_params(ticker, cluster_buy, cluster_sell, page, per_page)
        data = await self._client._get("/v1/signals", params)
        return [InsiderSignal(**item) for item in data]

    async def paginate(
        self,
        *,
        ticker: str | None = None,
        cluster_buy: bool | None = None,
        cluster_sell: bool | None = None,
        per_page: int = 100,
    ) -> AsyncGenerator[list[InsiderSignal], None]:
        page = 1
        while True:
            batch = await self.list(
                ticker=ticker, cluster_buy=cluster_buy, cluster_sell=cluster_sell,
                page=page, per_page=per_page,
            )
            if not batch:
                break
            yield batch
            if len(batch) < per_page:
                break
            page += 1
