from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

from form4api._types import InsiderSignal

if TYPE_CHECKING:
    from form4api._client import Form4ApiClient


class SignalsResource:
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
        params: dict[str, str] = {"page": str(page), "per_page": str(per_page)}
        if ticker is not None:
            params["ticker"] = ticker
        if cluster_buy is not None:
            params["cluster_buy"] = str(cluster_buy).lower()
        if cluster_sell is not None:
            params["cluster_sell"] = str(cluster_sell).lower()
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



