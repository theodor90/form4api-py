from __future__ import annotations

import re


class Form4ApiError(Exception):
    def __init__(self, message: str, status_code: int, error_code: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class AuthError(Form4ApiError):
    def __init__(self, message: str, error_code: str | None = None) -> None:
        super().__init__(message, 401, error_code)


class PlanError(Form4ApiError):
    """Raised on 402 PLAN_REQUIRED.

    ``required_plan`` is the minimum plan that unlocks the endpoint (e.g.
    ``"Business"``), ``current_plan`` is the plan the calling key is on, and
    ``upgrade_url`` is where to upgrade. All three may be ``None`` against
    backends older than 2026-08-05, which carried the plan names only as prose
    inside ``message``.
    """

    def __init__(
        self,
        message: str,
        required_plan: str | None = None,
        current_plan: str | None = None,
        upgrade_url: str | None = None,
    ) -> None:
        super().__init__(message, 402, "PLAN_REQUIRED")
        self.required_plan = required_plan
        self.current_plan = current_plan
        self.upgrade_url = upgrade_url


class NotFoundError(Form4ApiError):
    def __init__(self, message: str, error_code: str | None = None) -> None:
        super().__init__(message, 404, error_code)


class RateLimitError(Form4ApiError):
    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message, 429, "RATE_LIMIT_EXCEEDED")
        self.retry_after = retry_after


# Backend message shape for the plan-gated *pagination depth* 402 (see
# PaginationHelpers.MaxPageFor / TransactionsEndpoints.cs / CongressEndpoints.cs
# on the API). This is deliberately narrow: `error_code` is "PLAN_REQUIRED" for
# EVERY 402 the API returns — a whole-endpoint plan gate (e.g. GET /v1/signals
# on a sub-Business key) and a plan-gated query parameter both use the same
# code — so the message text is the only reliable signal that a given 402 is
# specifically the depth limit rather than some other plan gate. If the
# backend ever changes this message shape, the regex stops matching and
# `paginate()` re-raises the original `PlanError` untouched instead of
# mislabeling an unrelated 402.
_PAGINATION_DEPTH_MESSAGE_RE = re.compile(r"pagination depth on /v1/", re.IGNORECASE)


def is_pagination_depth_error(err: Exception) -> bool:
    """True when `err` is specifically the plan-gated pagination-depth 402 that
    `paginate()` knows how to turn into a `PaginationLimitError`."""
    return isinstance(err, PlanError) and bool(_PAGINATION_DEPTH_MESSAGE_RE.search(str(err)))


class PaginationLimitError(Form4ApiError):
    """Raised by `paginate()` (on `transactions` and `signals`) when the backend
    rejects the next page because the calling key's plan has reached its
    pagination depth limit (Free: 20 pages, Starter: 100, Pro+: unlimited).

    Pages already yielded before this point were real, complete pages — this
    error only means iteration stopped early, not that any data already
    delivered to the caller was wrong. `pages_yielded` tells you exactly how
    many. The original `PlanError` is chained as `__cause__` (via `raise ... from err`).
    """

    def __init__(self, message: str, pages_yielded: int) -> None:
        super().__init__(message, 402, "PLAN_REQUIRED")
        self.pages_yielded = pages_yielded
