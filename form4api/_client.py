from __future__ import annotations

import asyncio
import re
import time
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from typing import Any, TypeVar

import httpx

from form4api._errors import AuthError, Form4ApiError, NotFoundError, PlanError, RateLimitError

# Sent as the User-Agent so the backend can attribute traffic to the Python SDK
# channel (the admin dashboard buckets by client). Read from installed package
# metadata so it never drifts from the pyproject version.
try:
    _SDK_VERSION = _pkg_version("form4api")
except PackageNotFoundError:  # not installed (e.g. running from a source tree)
    _SDK_VERSION = "0.0.0"
_USER_AGENT = f"form4api-py/{_SDK_VERSION}"
from form4api.resources._companies import CompaniesResource
from form4api.resources._insiders import InsidersResource
from form4api.resources._signals import SignalsResource
from form4api.resources._transactions import TransactionsResource
from form4api.resources._webhooks import WebhooksResource

DEFAULT_BASE_URL = "https://api.form4api.com"
_RETRY_DELAYS = [0.5, 1.0, 2.0]

T = TypeVar("T")


def _camel_to_snake(name: str) -> str:
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    return re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s).lower()


def _normalise(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {_camel_to_snake(k): _normalise(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalise(i) for i in obj]
    return obj


class Form4ApiClient:
    """Synchronous client for the Form4API."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        max_retries: int = 2,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._http = httpx.Client(
            timeout=timeout,
            headers={"X-Api-Key": api_key, "User-Agent": _USER_AGENT},
        )
        self.transactions = TransactionsResource(self)
        self.insiders = InsidersResource(self)
        self.companies = CompaniesResource(self)
        self.signals = SignalsResource(self)
        self.webhooks = WebhooksResource(self)

    def __enter__(self) -> Form4ApiClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = self._base_url + path
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                time.sleep(_RETRY_DELAYS[min(attempt - 1, len(_RETRY_DELAYS) - 1)])
            try:
                res = self._http.request(method, url, **kwargs)
                if res.status_code < 500:
                    return res
                if attempt == self._max_retries:
                    return res
                last_exc = None
            except httpx.TransportError as exc:
                if attempt == self._max_retries:
                    raise
                last_exc = exc

        raise last_exc  # type: ignore[misc]

    def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        res = self._request("GET", path, params=params)
        return _normalise(self._parse(res))

    def _post(self, path: str, body: Any = None) -> Any:
        res = self._request("POST", path, json=body)
        return _normalise(self._parse(res))

    def _delete(self, path: str) -> None:
        res = self._request("DELETE", path)
        if not res.is_success and res.status_code != 204:
            self._raise(res)

    def _parse(self, res: httpx.Response) -> Any:
        if res.is_success:
            return res.json()
        self._raise(res)

    def _raise(self, res: httpx.Response) -> None:
        try:
            body = res.json()
        except Exception:
            body = {}
        error = body.get("error", {}) if isinstance(body, dict) else {}
        code = error.get("code") if isinstance(error, dict) else None
        message = (error.get("message") if isinstance(error, dict) else None) or f"HTTP {res.status_code}"

        if res.status_code == 401:
            raise AuthError(message, code)
        if res.status_code == 402:
            # Read from the nested `error` object, not the top level. This was
            # reading body["requiredPlan"], which the API has never emitted at
            # any level, so PlanError.required_plan was permanently None. The
            # backend now returns requiredPlan/currentPlan/upgradeUrl inside the
            # standard error envelope.
            raise PlanError(
                message,
                error.get("requiredPlan") if isinstance(error, dict) else None,
                error.get("currentPlan") if isinstance(error, dict) else None,
                error.get("upgradeUrl") if isinstance(error, dict) else None,
            )
        if res.status_code == 404:
            raise NotFoundError(message, code)
        if res.status_code == 429:
            retry_after = res.headers.get("Retry-After")
            raise RateLimitError(message, int(retry_after) if retry_after else None)
        raise Form4ApiError(message, res.status_code, code)


class AsyncForm4ApiClient:
    """Async client for the Form4API."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        max_retries: int = 2,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._http = httpx.AsyncClient(
            timeout=timeout,
            headers={"X-Api-Key": api_key, "User-Agent": _USER_AGENT},
        )
        self.transactions = TransactionsResource(self)  # type: ignore[arg-type]
        self.insiders = InsidersResource(self)  # type: ignore[arg-type]
        self.companies = CompaniesResource(self)  # type: ignore[arg-type]
        self.signals = SignalsResource(self)  # type: ignore[arg-type]
        self.webhooks = WebhooksResource(self)  # type: ignore[arg-type]

    async def __aenter__(self) -> AsyncForm4ApiClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = self._base_url + path
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                await asyncio.sleep(_RETRY_DELAYS[min(attempt - 1, len(_RETRY_DELAYS) - 1)])
            try:
                res = await self._http.request(method, url, **kwargs)
                if res.status_code < 500:
                    return res
                if attempt == self._max_retries:
                    return res
                last_exc = None
            except httpx.TransportError as exc:
                if attempt == self._max_retries:
                    raise
                last_exc = exc

        raise last_exc  # type: ignore[misc]

    async def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        res = await self._request("GET", path, params=params)
        return _normalise(self._parse(res))

    async def _post(self, path: str, body: Any = None) -> Any:
        res = await self._request("POST", path, json=body)
        return _normalise(self._parse(res))

    async def _delete(self, path: str) -> None:
        res = await self._request("DELETE", path)
        if not res.is_success and res.status_code != 204:
            self._raise(res)

    def _parse(self, res: httpx.Response) -> Any:
        if res.is_success:
            return res.json()
        self._raise(res)

    def _raise(self, res: httpx.Response) -> None:
        try:
            body = res.json()
        except Exception:
            body = {}
        error = body.get("error", {}) if isinstance(body, dict) else {}
        code = error.get("code") if isinstance(error, dict) else None
        message = (error.get("message") if isinstance(error, dict) else None) or f"HTTP {res.status_code}"

        if res.status_code == 401:
            raise AuthError(message, code)
        if res.status_code == 402:
            # Read from the nested `error` object, not the top level. This was
            # reading body["requiredPlan"], which the API has never emitted at
            # any level, so PlanError.required_plan was permanently None. The
            # backend now returns requiredPlan/currentPlan/upgradeUrl inside the
            # standard error envelope.
            raise PlanError(
                message,
                error.get("requiredPlan") if isinstance(error, dict) else None,
                error.get("currentPlan") if isinstance(error, dict) else None,
                error.get("upgradeUrl") if isinstance(error, dict) else None,
            )
        if res.status_code == 404:
            raise NotFoundError(message, code)
        if res.status_code == 429:
            retry_after = res.headers.get("Retry-After")
            raise RateLimitError(message, int(retry_after) if retry_after else None)
        raise Form4ApiError(message, res.status_code, code)
