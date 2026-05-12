from __future__ import annotations

from typing import TYPE_CHECKING

from form4api._types import Company, Insider

if TYPE_CHECKING:
    from form4api._client import Form4ApiClient


class CompaniesResource:
    def __init__(self, client: Form4ApiClient) -> None:
        self._client = client

    def get(self, ticker: str) -> Company:
        data = self._client._get(f"/v1/companies/{ticker}")
        return Company(**data)

    def insiders(self, ticker: str) -> list[Insider]:
        data = self._client._get(f"/v1/companies/{ticker}/insiders")
        return [Insider(**item) for item in data]



