"""
HTTP Retry Utilities

Provides retry decorator and wrapper for HTTP requests with exponential backoff.
Uses the RetryConfig class for configuration and integrates with httpx.
"""

import asyncio
import functools
from typing import Any, Callable, TypeVar, ParamSpec, Awaitable

import httpx
from loguru import logger

from app.acp.core.types import RetryConfig


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(
        self,
        message: str,
        attempts: int,
        last_exception: Exception | None = None,
        last_status_code: int | None = None,
    ):
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception
        self.last_status_code = last_status_code


P = ParamSpec("P")
T = TypeVar("T")


def retry(
    config: RetryConfig | None = None,
    *,
    on_retry: Callable[[int, Exception | None, int | None], None] | None = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    Decorator for adding retry logic to async HTTP request functions.

    Handles both httpx.HTTPStatusError (for retryable status codes) and
    httpx.RequestError (for connection/timeout errors).

    Args:
        config: RetryConfig instance. Defaults to RetryConfig() if not provided.
        on_retry: Optional callback called before each retry with
                  (attempt, exception, status_code) arguments.

    Returns:
        Decorated async function with retry logic.

    Example:
        >>> @retry(config=RetryConfig(max_retries=3))
        ... async def fetch_data(client: httpx.AsyncClient, url: str):
        ...     response = await client.get(url)
        ...     response.raise_for_status()
        ...     return response.json()

        >>> @retry(config=RetryConfig.aggressive())
        ... async def critical_operation(client: httpx.AsyncClient):
        ...     response = await client.post("/important", json={"data": "value"})
        ...     response.raise_for_status()
        ...     return response.json()
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await _execute_with_retry(
                func,
                config,
                on_retry,
                *args,
                **kwargs,
            )

        return wrapper

    return decorator


async def with_retry(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    config: RetryConfig | None = None,
    on_retry: Callable[[int, Exception | None, int | None], None] | None = None,
    **kwargs: Any,
) -> T:
    """
    Execute an async function with retry logic.

    This is a wrapper function alternative to the @retry decorator.
    Useful when you need to apply retry logic dynamically or to
    functions you don't control.

    Args:
        func: Async function to execute with retries.
        *args: Positional arguments to pass to the function.
        config: RetryConfig instance. Defaults to RetryConfig() if not provided.
        on_retry: Optional callback called before each retry with
                  (attempt, exception, status_code) arguments.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        The return value of the function.

    Raises:
        RetryExhaustedError: When all retry attempts have been exhausted.
        Exception: The original exception if it's not retryable.

    Example:
        >>> async def make_request(client, url):
        ...     response = await client.get(url)
        ...     response.raise_for_status()
        ...     return response.json()

        >>> result = await with_retry(
        ...     make_request,
        ...     client,
        ...     "/api/data",
        ...     config=RetryConfig(max_retries=3),
        ... )

        >>> # With aggressive retry for critical operations
        >>> result = await with_retry(
        ...     make_request,
        ...     client,
        ...     "/api/critical",
        ...     config=RetryConfig.aggressive(),
        ... )
    """
    if config is None:
        config = RetryConfig()

    return await _execute_with_retry(func, config, on_retry, *args, **kwargs)


async def _execute_with_retry(
    func: Callable[..., Awaitable[T]],
    config: RetryConfig,
    on_retry: Callable[[int, Exception | None, int | None], None] | None,
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Internal function that implements the retry logic.

    Handles the core retry loop with exponential backoff, supporting
    both HTTP status errors and request/connection errors.
    """
    attempt = 0
    last_exception: Exception | None = None
    last_status_code: int | None = None
    func_name = getattr(func, "__name__", str(func))

    while True:
        try:
            return await func(*args, **kwargs)

        except httpx.HTTPStatusError as exc:
            last_exception = exc
            last_status_code = exc.response.status_code

            # Check if status code is retryable (ignore attempt count for this check)
            if last_status_code not in config.retryable_status_codes:
                logger.warning(
                    f"Non-retryable HTTP status {last_status_code} "
                    f"from {func_name}, not retrying"
                )
                raise

            # If max_retries is 0, re-raise immediately (no retries configured)
            if config.max_retries == 0:
                logger.debug(
                    f"Retries disabled for {func_name}, re-raising HTTP {last_status_code}"
                )
                raise

            attempt += 1
            if attempt > config.max_retries:
                logger.error(
                    f"Retry exhausted for {func_name} after {attempt} attempts, "
                    f"last status: {last_status_code}"
                )
                raise RetryExhaustedError(
                    f"All {config.max_retries} retry attempts exhausted",
                    attempts=attempt,
                    last_exception=exc,
                    last_status_code=last_status_code,
                )

            delay = config.get_delay(attempt - 1)
            logger.warning(
                f"HTTP {last_status_code} from {func_name}, "
                f"retry {attempt}/{config.max_retries} in {delay:.2f}s"
            )

            if on_retry:
                on_retry(attempt, exc, last_status_code)

            await asyncio.sleep(delay)

        except httpx.RequestError as exc:
            last_exception = exc
            last_status_code = None

            # Check if exception type is retryable (ignore attempt count for this check)
            is_retryable = _is_retryable_request_error(exc, config)

            if not is_retryable:
                logger.warning(
                    f"Non-retryable request error from {func_name}: {exc}, not retrying"
                )
                raise

            # If max_retries is 0, re-raise immediately (no retries configured)
            if config.max_retries == 0:
                logger.debug(
                    f"Retries disabled for {func_name}, re-raising {type(exc).__name__}"
                )
                raise

            attempt += 1
            if attempt > config.max_retries:
                logger.error(
                    f"Retry exhausted for {func_name} after {attempt} attempts, "
                    f"last error: {exc}"
                )
                raise RetryExhaustedError(
                    f"All {config.max_retries} retry attempts exhausted",
                    attempts=attempt,
                    last_exception=exc,
                    last_status_code=None,
                )

            delay = config.get_delay(attempt - 1)
            logger.warning(
                f"Request error from {func_name}: {exc}, "
                f"retry {attempt}/{config.max_retries} in {delay:.2f}s"
            )

            if on_retry:
                on_retry(attempt, exc, None)

            await asyncio.sleep(delay)


def _is_retryable_request_error(exc: httpx.RequestError, config: RetryConfig) -> bool:
    """
    Check if an httpx.RequestError should trigger a retry.

    Maps httpx exceptions to the retryable exception types defined in RetryConfig.
    """
    # Check if the exception itself matches configured retryable types
    if isinstance(exc, config.retryable_exceptions):
        return True

    # Map specific httpx exceptions to retryable types
    # httpx.ConnectError -> ConnectionError
    if isinstance(exc, httpx.ConnectError):
        return ConnectionError in config.retryable_exceptions

    # httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout -> TimeoutError
    if isinstance(exc, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout)):
        return TimeoutError in config.retryable_exceptions

    # httpx.TimeoutException (base class for all timeouts) -> TimeoutError
    if isinstance(exc, httpx.TimeoutException):
        return TimeoutError in config.retryable_exceptions

    # httpx.NetworkError -> ConnectionError
    if isinstance(exc, httpx.NetworkError):
        return ConnectionError in config.retryable_exceptions

    return False
