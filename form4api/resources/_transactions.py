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
        exclude_10b5: bool | None = None,
        codes: str | None = None,
        exclude_codes: str | None = None,
        category: str | None = None,
        exclude_category: str | None = None,
        exclude_derivative: bool | None = None,
        significant: bool | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        min_shares: float | None = None,
        max_shares: float | None = None,
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
        if exclude_10b5 is not None:
            params["exclude_10b5"] = str(exclude_10b5).lower()
        if codes is not None:
            params["codes"] = codes
        if exclude_codes is not None:
            params["exclude_codes"] = exclude_codes
        if category is not None:
            params["category"] = category
        if exclude_category is not None:
            params["exclude_category"] = exclude_category
        if exclude_derivative is not None:
            params["exclude_derivative"] = str(exclude_derivative).lower()
        if significant is not None:
            params["significant"] = str(significant).lower()
        if min_value is not None:
            params["min_value"] = str(min_value)
        if max_value is not None:
            params["max_value"] = str(max_value)
        if min_shares is not None:
            params["min_shares"] = str(min_shares)
        if max_shares is not None:
            params["max_shares"] = str(max_shares)
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
        exclude_10b5: bool | None = None,
        codes: str | None = None,
        exclude_codes: str | None = None,
        category: str | None = None,
        exclude_category: str | None = None,
        exclude_derivative: bool | None = None,
        significant: bool | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        min_shares: float | None = None,
        max_shares: float | None = None,
        per_page: int = 50,
    ) -> Generator[list[Transaction], None, None]:
        page = 1
        while True:
            batch = self.list(
                ticker=ticker, cik=cik, insider_cik=insider_cik,
                code=code, from_date=from_date, to_date=to_date,
                exclude_10b5=exclude_10b5,
                codes=codes, exclude_codes=exclude_codes,
                category=category, exclude_category=exclude_category,
                exclude_derivative=exclude_derivative, significant=significant,
                min_value=min_value, max_value=max_value,
                min_shares=min_shares, max_shares=max_shares,
                page=page, per_page=per_page,
            )
            if not batch:
                break
            yield batch
            if len(batch) < per_page:
                break
            page += 1



