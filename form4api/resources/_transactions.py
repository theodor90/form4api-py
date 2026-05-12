from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

from form4api._types import Transaction

if TYPE_CHECKING:
    from form4api._client import Form4ApiClient


class TransactionsResource:
    def __init__(self, client: Form4ApiClient) -> None:
        self._client = client

    def list(
        self,
        *,
        ticker: str | None = None,
        cik: str | None = None,
        insider_cik: str | None = None,
        code: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> list[Transaction]:
        params: dict[str, str] = {"page": str(page), "per_page": str(per_page)}
        if ticker is not None:
            params["ticker"] = ticker
        if cik is not None:
            params["cik"] = cik
        if insider_cik is not None:
            params["insider_cik"] = insider_cik
        if code is not None:
            params["code"] = code
        if from_date is not None:
            params["from"] = from_date
        if to_date is not None:
            params["to"] = to_date
        data = self._client._get("/v1/transactions", params)
        return [Transaction(**item) for item in data]

    def paginate(
        self,
        *,
        ticker: str | None = None,
        cik: str | None = None,
        insider_cik: str | None = None,
        code: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        per_page: int = 50,
    ) -> Generator[list[Transaction], None, None]:
        page = 1
        while True:
            batch = self.list(
                ticker=ticker, cik=cik, insider_cik=insider_cik,
                code=code, from_date=from_date, to_date=to_date,
                page=page, per_page=per_page,
            )
            if not batch:
                break
            yield batch
            if len(batch) < per_page:
                break
            page += 1



