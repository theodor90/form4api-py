from __future__ import annotations


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
