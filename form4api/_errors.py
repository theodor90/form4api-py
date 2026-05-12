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
    def __init__(self, message: str, required_plan: str | None = None) -> None:
        super().__init__(message, 402, "PLAN_REQUIRED")
        self.required_plan = required_plan


class NotFoundError(Form4ApiError):
    def __init__(self, message: str, error_code: str | None = None) -> None:
        super().__init__(message, 404, error_code)


class RateLimitError(Form4ApiError):
    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message, 429, "RATE_LIMIT_EXCEEDED")
        self.retry_after = retry_after
