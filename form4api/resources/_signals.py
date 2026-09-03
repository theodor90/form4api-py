from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

from collections.abc import AsyncGenerator

from form4api._errors import PaginationLimitError, PlanError, is_pagination_depth_error
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
        max_pages: int | None = None,
    ) -> Generator[list[InsiderSignal], None, None]:
        """Pages through /v1/signals until the data runs out (a short or empty
        page) or the calling key's plan-gated pagination depth is exceeded —
        see `TransactionsResource.paginate` for the full rationale. That 402
        is NOT swallowed; it becomes a `PaginationLimitError` after every page
        already yielded has been delivered to the caller. Pass `max_pages` to
        stop deliberately before that happens.
        """
        page = 1
        pages_yielded = 0
        while True:
            if max_pages is not None and pages_yielded >= max_pages:
                break

            try:
                batch = self.list(
                    ticker=ticker, cluster_buy=cluster_buy, cluster_sell=cluster_sell,
                    page=page, per_page=per_page,
                )
            except PlanError as err:
                if is_pagination_depth_error(err):
                    raise PaginationLimitError(
                        f"signals.paginate() stopped after yielding {pages_yielded} page(s) — {err}",
                        pages_yielded,
                        err,
                    ) from err
                raise

            if not batch:
                break
            yield batch
            pages_yielded += 1
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
        max_pages: int | None = None,
    ) -> AsyncGenerator[list[InsiderSignal], None]:
        """Async twin of `SignalsResource.paginate` — same depth-limit
        semantics, see there for the full rationale."""
        page = 1
        pages_yielded = 0
        while True:
            if max_pages is not None and pages_yielded >= max_pages:
                break

            try:
                batch = await self.list(
                    ticker=ticker, cluster_buy=cluster_buy, cluster_sell=cluster_sell,
                    page=page, per_page=per_page,
                )
            except PlanError as err:
                if is_pagination_depth_error(err):
                    raise PaginationLimitError(
                        f"signals.paginate() stopped after yielding {pages_yielded} page(s) — {err}",
                        pages_yielded,
                        err,
                    ) from err
                raise

            if not batch:
                break
            yield batch
            pages_yielded += 1
            if len(batch) < per_page:
                break
            page += 1
