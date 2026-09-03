from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from typing import TYPE_CHECKING

from form4api._errors import PaginationLimitError, PlanError, is_pagination_depth_error
from form4api._types import Transaction

if TYPE_CHECKING:
    from form4api._client import AsyncForm4ApiClient, Form4ApiClient


def _list_params(
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
    page: int,
    per_page: int,
) -> dict[str, str]:
    """Shared by the sync and async twins.

    Eighteen optional filters is exactly the kind of block that drifts when it
    is copy-pasted, so it lives in one place and both twins call it. Only the
    signature is duplicated, and only because that is what preserves type hints.
    """
    params: dict[str, str] = {"page": str(page), "per_page": str(per_page)}
    for key, value in (
        ("ticker", ticker), ("cik", cik), ("insider_cik", insider_cik), ("code", code),
        ("from", from_date), ("to", to_date), ("codes", codes),
        ("exclude_codes", exclude_codes), ("category", category),
        ("exclude_category", exclude_category),
    ):
        if value is not None:
            params[key] = value
    for key, value in (
        ("exclude_10b5", exclude_10b5), ("exclude_derivative", exclude_derivative),
        ("significant", significant),
    ):
        if value is not None:
            params[key] = str(value).lower()
    for key, value in (
        ("min_value", min_value), ("max_value", max_value),
        ("min_shares", min_shares), ("max_shares", max_shares),
    ):
        if value is not None:
            params[key] = str(value)
    return params


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
        params = _list_params(
            ticker=ticker, cik=cik, insider_cik=insider_cik, code=code,
            from_date=from_date, to_date=to_date, exclude_10b5=exclude_10b5,
            codes=codes, exclude_codes=exclude_codes, category=category,
            exclude_category=exclude_category, exclude_derivative=exclude_derivative,
            significant=significant, min_value=min_value, max_value=max_value,
            min_shares=min_shares, max_shares=max_shares,
            page=page, per_page=per_page,
        )
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
        max_pages: int | None = None,
    ) -> Generator[list[Transaction], None, None]:
        """Pages through /v1/transactions until the data runs out (a short or
        empty page) or, since the backend's 2026-08-01 plan-gated pagination
        depth (Free: 20 pages, Starter: 100, Pro+: unlimited), the next page is
        rejected with a 402. That 402 is NOT swallowed — a scripted caller who
        silently stopped there would see what looks like "no more data" and
        never learn their dataset was truncated. Instead this raises
        `PaginationLimitError` mid-iteration, after every page already yielded
        has been delivered to the caller. Pass `max_pages` to stop deliberately
        before that ever happens.
        """
        page = 1
        pages_yielded = 0
        while True:
            if max_pages is not None and pages_yielded >= max_pages:
                break

            try:
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
            except PlanError as err:
                if is_pagination_depth_error(err):
                    raise PaginationLimitError(
                        f"transactions.paginate() stopped after yielding {pages_yielded} page(s) — {err}",
                        pages_yielded,
                    ) from err
                raise

            if not batch:
                break
            yield batch
            pages_yielded += 1
            if len(batch) < per_page:
                break
            page += 1


class AsyncTransactionsResource:
    """Async twin of TransactionsResource. See AsyncCompaniesResource for the rationale."""

    def __init__(self, client: AsyncForm4ApiClient) -> None:
        self._client = client

    async def list(
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
        params = _list_params(
            ticker=ticker, cik=cik, insider_cik=insider_cik, code=code,
            from_date=from_date, to_date=to_date, exclude_10b5=exclude_10b5,
            codes=codes, exclude_codes=exclude_codes, category=category,
            exclude_category=exclude_category, exclude_derivative=exclude_derivative,
            significant=significant, min_value=min_value, max_value=max_value,
            min_shares=min_shares, max_shares=max_shares,
            page=page, per_page=per_page,
        )
        data = await self._client._get("/v1/transactions", params)
        return [Transaction(**item) for item in data]

    async def paginate(
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
        max_pages: int | None = None,
    ) -> AsyncGenerator[list[Transaction], None]:
        """Async twin of `TransactionsResource.paginate` — same depth-limit
        semantics, see there for the full rationale."""
        page = 1
        pages_yielded = 0
        while True:
            if max_pages is not None and pages_yielded >= max_pages:
                break

            try:
                batch = await self.list(
                    ticker=ticker, cik=cik, insider_cik=insider_cik, code=code,
                    from_date=from_date, to_date=to_date, exclude_10b5=exclude_10b5,
                    codes=codes, exclude_codes=exclude_codes, category=category,
                    exclude_category=exclude_category, exclude_derivative=exclude_derivative,
                    significant=significant, min_value=min_value, max_value=max_value,
                    min_shares=min_shares, max_shares=max_shares,
                    page=page, per_page=per_page,
                )
            except PlanError as err:
                if is_pagination_depth_error(err):
                    raise PaginationLimitError(
                        f"transactions.paginate() stopped after yielding {pages_yielded} page(s) — {err}",
                        pages_yielded,
                    ) from err
                raise

            if not batch:
                break
            yield batch
            pages_yielded += 1
            if len(batch) < per_page:
                break
            page += 1
