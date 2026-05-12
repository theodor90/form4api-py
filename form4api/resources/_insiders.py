from __future__ import annotations

from typing import TYPE_CHECKING

from form4api._types import Insider, Transaction

if TYPE_CHECKING:
    from form4api._client import Form4ApiClient


class InsidersResource:
    def __init__(self, client: Form4ApiClient) -> None:
        self._client = client

    def search(
        self,
        name: str,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> list[Insider]:
        params: dict[str, str] = {"name": name, "page": str(page), "per_page": str(per_page)}
        data = self._client._get("/v1/insiders", params)
        return [Insider(**item) for item in data]

    def get(self, cik: str) -> Insider:
        data = self._client._get(f"/v1/insiders/{cik}")
        return Insider(**data)

    def transactions(
        self,
        cik: str,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> list[Transaction]:
        params: dict[str, str] = {"page": str(page), "per_page": str(per_page)}
        if from_date is not None:
            params["from"] = from_date
        if to_date is not None:
            params["to"] = to_date
        data = self._client._get(f"/v1/insiders/{cik}/transactions", params)
        return [Transaction(**item) for item in data]



