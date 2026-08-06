from __future__ import annotations

from typing import TYPE_CHECKING

from form4api._generated import GeneratedAsyncCompaniesResource, GeneratedCompaniesResource
from form4api._types import Company, Insider

if TYPE_CHECKING:
    from form4api._client import AsyncForm4ApiClient, Form4ApiClient


# Extends the generated base rather than replacing it, so spec-derived
# methods (list()) arrive by regenerating while the curated
# signatures below stay exactly as published on PyPI. Move an operation out
# of HANDLED_BY_HANDWRITTEN in codegen/generate.py to let codegen own it.
class CompaniesResource(GeneratedCompaniesResource):
    def __init__(self, client: Form4ApiClient) -> None:
        self._client = client

    def get(self, ticker: str) -> Company:
        data = self._client._get(f"/v1/companies/{ticker}")
        return Company(**data)

    def insiders(self, ticker: str) -> list[Insider]:
        data = self._client._get(f"/v1/companies/{ticker}/insiders")
        return [Insider(**item) for item in data]


class AsyncCompaniesResource(GeneratedAsyncCompaniesResource):
    """Async twin of CompaniesResource.

    Python cannot bridge sync and async in a single code path, so the signatures
    are duplicated deliberately — that is what keeps type hints and IDE
    completion intact, and it is how the major typed Python SDKs do it. Only the
    await differs; any request-shaping logic is factored into module-level
    helpers so the two paths cannot drift.
    """

    def __init__(self, client: AsyncForm4ApiClient) -> None:
        self._client = client

    async def get(self, ticker: str) -> Company:
        data = await self._client._get(f"/v1/companies/{ticker}")
        return Company(**data)

    async def insiders(self, ticker: str) -> list[Insider]:
        data = await self._client._get(f"/v1/companies/{ticker}/insiders")
        return [Insider(**item) for item in data]



