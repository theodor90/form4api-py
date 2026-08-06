from __future__ import annotations

from typing import TYPE_CHECKING

from form4api._generated import GeneratedAsyncInsidersResource, GeneratedInsidersResource
from form4api._types import Insider, Transaction

if TYPE_CHECKING:
    from form4api._client import AsyncForm4ApiClient, Form4ApiClient


def _search_params(name: str, page: int, per_page: int) -> dict[str, str]:
    """Shared by the sync and async twins so the request shape cannot drift."""
    return {"name": name, "page": str(page), "per_page": str(per_page)}


def _transactions_params(from_date: str | None, to_date: str | None, page: int, per_page: int) -> dict[str, str]:
    params: dict[str, str] = {"page": str(page), "per_page": str(per_page)}
    if from_date is not None:
        params["from"] = from_date
    if to_date is not None:
        params["to"] = to_date
    return params


# Extends the generated base rather than replacing it, so spec-derived
# methods (list(), summary(), scorecard()) arrive by regenerating while the curated
# signatures below stay exactly as published on PyPI. Move an operation out
# of HANDLED_BY_HANDWRITTEN in codegen/generate.py to let codegen own it.
class InsidersResource(GeneratedInsidersResource):
    def __init__(self, client: Form4ApiClient) -> None:
        self._client = client

    def search(
        self,
        name: str,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> list[Insider]:
        data = self._client._get("/v1/insiders", _search_params(name, page, per_page))
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
        params = _transactions_params(from_date, to_date, page, per_page)
        data = self._client._get(f"/v1/insiders/{cik}/transactions", params)
        return [Transaction(**item) for item in data]


class AsyncInsidersResource(GeneratedAsyncInsidersResource):
    """Async twin of InsidersResource. See AsyncCompaniesResource for the rationale."""

    def __init__(self, client: AsyncForm4ApiClient) -> None:
        self._client = client

    async def search(self, name: str, *, page: int = 1, per_page: int = 20) -> list[Insider]:
        data = await self._client._get("/v1/insiders", _search_params(name, page, per_page))
        return [Insider(**item) for item in data]

    async def get(self, cik: str) -> Insider:
        data = await self._client._get(f"/v1/insiders/{cik}")
        return Insider(**data)

    async def transactions(
        self,
        cik: str,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> list[Transaction]:
        params = _transactions_params(from_date, to_date, page, per_page)
        data = await self._client._get(f"/v1/insiders/{cik}/transactions", params)
        return [Transaction(**item) for item in data]



