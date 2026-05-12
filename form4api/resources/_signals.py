from __future__ import annotations

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
        page: int = 1,
        per_page: int = 100,
    ) -> list[InsiderSignal]:
        params: dict[str, str] = {"page": str(page), "per_page": str(per_page)}
        if ticker is not None:
            params["ticker"] = ticker
        data = self._client._get("/v1/signals", params)
        return [InsiderSignal(**item) for item in data]



