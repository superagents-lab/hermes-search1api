from __future__ import annotations

from typing import Any, Mapping, Optional


class Search1APIError(Exception):
    """Base exception for the Search1API SDK."""


class Search1APIConfigurationError(Search1APIError):
    pass


class APIConnectionError(Search1APIError):
    pass


class APITimeoutError(APIConnectionError):
    pass


class APIStatusError(Search1APIError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.headers = headers or {}
        self.request_id = self.headers.get("x-request-id")


class BadRequestError(APIStatusError):
    pass


class AuthenticationError(APIStatusError):
    pass


class PaymentRequiredError(APIStatusError):
    pass


class NotFoundError(APIStatusError):
    pass


class UnprocessableEntityError(APIStatusError):
    pass


class RateLimitError(APIStatusError):
    pass


class InternalServerError(APIStatusError):
    pass


class DeepcrawlFailedError(Search1APIError):
    def __init__(self, response: Mapping[str, Any]) -> None:
        task_id = response.get("taskId", "unknown")
        message = (
            response.get("error")
            or response.get("message")
            or f"Deepcrawl task {task_id} failed"
        )
        super().__init__(str(message))
        self.response = response


class DeepcrawlTimeoutError(Search1APIError):
    def __init__(self, task_id: str, timeout: float) -> None:
        super().__init__(f"Deepcrawl task {task_id} did not finish within {timeout:g}s")
        self.task_id = task_id


def api_status_error(
    status_code: int,
    body: Optional[Mapping[str, Any]],
    headers: Mapping[str, str],
) -> APIStatusError:
    body = body or {}
    message = (
        body.get("message")
        or body.get("detail")
        or body.get("error")
        or body.get("title")
        or f"Search1API request failed with status {status_code}"
    )
    error_class = {
        400: BadRequestError,
        401: AuthenticationError,
        402: PaymentRequiredError,
        404: NotFoundError,
        422: UnprocessableEntityError,
        429: RateLimitError,
    }.get(status_code, InternalServerError if status_code >= 500 else APIStatusError)
    return error_class(
        str(message), status_code=status_code, body=body, headers=headers
    )
