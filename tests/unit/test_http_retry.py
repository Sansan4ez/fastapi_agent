"""
Unit tests for HTTP Retry Utilities.

Tests cover:
- RetryExhaustedError exception
- retry decorator for async functions
- with_retry wrapper function
- HTTP status code based retries
- Connection/timeout error based retries
- Exponential backoff behavior
- on_retry callback functionality
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.acp.core.types import RetryConfig
from app.acp.utils.http_retry import (
    RetryExhaustedError,
    retry,
    with_retry,
    _is_retryable_request_error,
)


# =============================================================================
# RetryExhaustedError Tests
# =============================================================================


class TestRetryExhaustedError:
    """Tests for RetryExhaustedError exception."""

    def test_error_message(self):
        """Verify error message is set correctly."""
        error = RetryExhaustedError(
            "All retries exhausted",
            attempts=3,
        )
        assert str(error) == "All retries exhausted"

    def test_error_attributes(self):
        """Verify all error attributes are set correctly."""
        last_exc = httpx.ConnectError("Connection failed")
        error = RetryExhaustedError(
            "Retry exhausted",
            attempts=5,
            last_exception=last_exc,
            last_status_code=503,
        )
        assert error.attempts == 5
        assert error.last_exception is last_exc
        assert error.last_status_code == 503

    def test_error_without_optional_attributes(self):
        """Verify error works without optional attributes."""
        error = RetryExhaustedError("Retry exhausted", attempts=3)
        assert error.attempts == 3
        assert error.last_exception is None
        assert error.last_status_code is None


# =============================================================================
# retry Decorator Tests
# =============================================================================


class TestRetryDecorator:
    """Tests for the @retry decorator."""

    @pytest.mark.asyncio
    async def test_successful_request_no_retry(self):
        """Verify successful request doesn't trigger retry."""
        call_count = 0

        @retry(config=RetryConfig(max_retries=3))
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_http_status_error(self):
        """Verify retry happens on retryable HTTP status codes."""
        call_count = 0

        @retry(config=RetryConfig(max_retries=3, initial_delay=0.01))
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                response = httpx.Response(503)
                raise httpx.HTTPStatusError(
                    "Service Unavailable",
                    request=MagicMock(),
                    response=response,
                )
            return "success"

        result = await flaky_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_status(self):
        """Verify no retry on non-retryable status codes like 404."""
        call_count = 0

        @retry(config=RetryConfig(max_retries=3, initial_delay=0.01))
        async def not_found_func():
            nonlocal call_count
            call_count += 1
            response = httpx.Response(404)
            raise httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=response,
            )

        with pytest.raises(httpx.HTTPStatusError):
            await not_found_func()
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises_error(self):
        """Verify RetryExhaustedError is raised when retries are exhausted."""

        @retry(config=RetryConfig(max_retries=2, initial_delay=0.01))
        async def always_fails():
            response = httpx.Response(503)
            raise httpx.HTTPStatusError(
                "Service Unavailable",
                request=MagicMock(),
                response=response,
            )

        with pytest.raises(RetryExhaustedError) as exc_info:
            await always_fails()

        assert exc_info.value.attempts == 3  # Initial + 2 retries
        assert exc_info.value.last_status_code == 503

    @pytest.mark.asyncio
    async def test_retry_on_connect_error(self):
        """Verify retry happens on connection errors."""
        call_count = 0

        @retry(config=RetryConfig(max_retries=3, initial_delay=0.01))
        async def connection_fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Connection refused")
            return "connected"

        result = await connection_fail_then_succeed()
        assert result == "connected"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_timeout_error(self):
        """Verify retry happens on timeout errors."""
        call_count = 0

        @retry(config=RetryConfig(max_retries=3, initial_delay=0.01))
        async def timeout_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ReadTimeout("Read timeout")
            return "success"

        result = await timeout_then_succeed()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_on_retry_callback_called(self):
        """Verify on_retry callback is called with correct arguments."""
        retry_calls = []

        def on_retry_callback(attempt, exc, status_code):
            retry_calls.append((attempt, type(exc).__name__, status_code))

        @retry(
            config=RetryConfig(max_retries=2, initial_delay=0.01),
            on_retry=on_retry_callback,
        )
        async def fail_twice():
            if len(retry_calls) < 2:
                response = httpx.Response(503)
                raise httpx.HTTPStatusError(
                    "Service Unavailable",
                    request=MagicMock(),
                    response=response,
                )
            return "success"

        result = await fail_twice()
        assert result == "success"
        assert len(retry_calls) == 2
        assert retry_calls[0] == (1, "HTTPStatusError", 503)
        assert retry_calls[1] == (2, "HTTPStatusError", 503)

    @pytest.mark.asyncio
    async def test_default_config_when_none_provided(self):
        """Verify default RetryConfig is used when none provided."""
        call_count = 0

        @retry()  # No config provided
        async def simple_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await simple_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_config(self):
        """Verify RetryConfig.no_retry() disables retries."""

        @retry(config=RetryConfig.no_retry())
        async def fails_once():
            response = httpx.Response(503)
            raise httpx.HTTPStatusError(
                "Service Unavailable",
                request=MagicMock(),
                response=response,
            )

        # Should fail immediately without retrying
        with pytest.raises(httpx.HTTPStatusError):
            await fails_once()

    @pytest.mark.asyncio
    async def test_preserves_function_name(self):
        """Verify decorated function preserves original name."""

        @retry()
        async def my_special_function():
            return "success"

        assert my_special_function.__name__ == "my_special_function"


# =============================================================================
# with_retry Wrapper Tests
# =============================================================================


class TestWithRetryWrapper:
    """Tests for the with_retry wrapper function."""

    @pytest.mark.asyncio
    async def test_successful_call(self):
        """Verify successful function call through wrapper."""

        async def simple_func(x, y):
            return x + y

        result = await with_retry(simple_func, 2, 3)
        assert result == 5

    @pytest.mark.asyncio
    async def test_with_keyword_arguments(self):
        """Verify wrapper passes keyword arguments correctly."""

        async def func_with_kwargs(a, b, c=10):
            return a + b + c

        result = await with_retry(func_with_kwargs, 1, 2, c=20)
        assert result == 23

    @pytest.mark.asyncio
    async def test_retry_with_config(self):
        """Verify wrapper uses provided config."""
        call_count = 0

        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                response = httpx.Response(503)
                raise httpx.HTTPStatusError(
                    "Service Unavailable",
                    request=MagicMock(),
                    response=response,
                )
            return "success"

        result = await with_retry(
            flaky_func,
            config=RetryConfig(max_retries=3, initial_delay=0.01),
        )
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_with_retry_callback(self):
        """Verify on_retry callback works with wrapper."""
        retry_calls = []

        async def fail_once():
            if len(retry_calls) < 1:
                response = httpx.Response(502)
                raise httpx.HTTPStatusError(
                    "Bad Gateway",
                    request=MagicMock(),
                    response=response,
                )
            return "success"

        def on_retry(attempt, exc, status_code):
            retry_calls.append(status_code)

        result = await with_retry(
            fail_once,
            config=RetryConfig(max_retries=2, initial_delay=0.01),
            on_retry=on_retry,
        )
        assert result == "success"
        assert retry_calls == [502]

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises_error(self):
        """Verify RetryExhaustedError is raised when retries exhausted."""

        async def always_fails():
            raise httpx.ConnectError("Connection refused")

        with pytest.raises(RetryExhaustedError) as exc_info:
            await with_retry(
                always_fails,
                config=RetryConfig(max_retries=2, initial_delay=0.01),
            )

        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.last_exception, httpx.ConnectError)


# =============================================================================
# _is_retryable_request_error Tests
# =============================================================================


class TestIsRetryableRequestError:
    """Tests for the _is_retryable_request_error helper."""

    def test_connect_error_is_retryable(self):
        """Verify ConnectError is retryable when ConnectionError is configured."""
        config = RetryConfig()
        exc = httpx.ConnectError("Connection refused")
        assert _is_retryable_request_error(exc, config) is True

    def test_connect_timeout_is_retryable(self):
        """Verify ConnectTimeout is retryable when TimeoutError is configured."""
        config = RetryConfig()
        exc = httpx.ConnectTimeout("Connection timed out")
        assert _is_retryable_request_error(exc, config) is True

    def test_read_timeout_is_retryable(self):
        """Verify ReadTimeout is retryable when TimeoutError is configured."""
        config = RetryConfig()
        exc = httpx.ReadTimeout("Read timed out")
        assert _is_retryable_request_error(exc, config) is True

    def test_write_timeout_is_retryable(self):
        """Verify WriteTimeout is retryable when TimeoutError is configured."""
        config = RetryConfig()
        exc = httpx.WriteTimeout("Write timed out")
        assert _is_retryable_request_error(exc, config) is True

    def test_network_error_is_retryable(self):
        """Verify NetworkError is retryable when ConnectionError is configured."""
        config = RetryConfig()
        # NetworkError is abstract, use a concrete subclass
        exc = httpx.ConnectError("Network error")
        assert _is_retryable_request_error(exc, config) is True

    def test_non_configured_error_not_retryable(self):
        """Verify errors not in config are not retryable."""
        # Config without ConnectionError or TimeoutError
        config = RetryConfig(retryable_exceptions=())
        exc = httpx.ConnectError("Connection refused")
        assert _is_retryable_request_error(exc, config) is False

    def test_direct_exception_match(self):
        """Verify direct exception type match works."""
        # Config that directly includes httpx.ConnectError
        config = RetryConfig(retryable_exceptions=(httpx.ConnectError,))
        exc = httpx.ConnectError("Connection refused")
        assert _is_retryable_request_error(exc, config) is True


# =============================================================================
# Exponential Backoff Tests
# =============================================================================


class TestExponentialBackoff:
    """Tests for exponential backoff behavior."""

    @pytest.mark.asyncio
    async def test_delays_increase_exponentially(self):
        """Verify delays follow exponential pattern."""
        delays = []
        call_count = 0

        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            delays.append(delay)
            # Don't actually sleep in tests

        @retry(
            config=RetryConfig(
                max_retries=3,
                initial_delay=1.0,
                exponential_base=2.0,
                jitter=False,  # Disable jitter for predictable testing
            )
        )
        async def always_fails():
            nonlocal call_count
            call_count += 1
            response = httpx.Response(503)
            raise httpx.HTTPStatusError(
                "Service Unavailable",
                request=MagicMock(),
                response=response,
            )

        with patch("asyncio.sleep", mock_sleep):
            with pytest.raises(RetryExhaustedError):
                await always_fails()

        # Verify exponential delays: 1.0, 2.0, 4.0
        assert len(delays) == 3
        assert delays[0] == pytest.approx(1.0)
        assert delays[1] == pytest.approx(2.0)
        assert delays[2] == pytest.approx(4.0)

    @pytest.mark.asyncio
    async def test_max_delay_caps_backoff(self):
        """Verify max_delay caps the exponential growth."""
        delays = []

        async def mock_sleep(delay):
            delays.append(delay)

        @retry(
            config=RetryConfig(
                max_retries=5,
                initial_delay=1.0,
                max_delay=3.0,  # Cap at 3 seconds
                exponential_base=2.0,
                jitter=False,
            )
        )
        async def always_fails():
            response = httpx.Response(503)
            raise httpx.HTTPStatusError(
                "Service Unavailable",
                request=MagicMock(),
                response=response,
            )

        with patch("asyncio.sleep", mock_sleep):
            with pytest.raises(RetryExhaustedError):
                await always_fails()

        # Delays should be: 1.0, 2.0, 3.0 (capped), 3.0 (capped), 3.0 (capped)
        assert all(d <= 3.0 for d in delays)


# =============================================================================
# Integration Tests
# =============================================================================


class TestRetryIntegration:
    """Integration tests for retry with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_retry_with_httpx_client_style_function(self):
        """Test retry with a function that mimics httpx client usage."""
        call_count = 0

        async def make_request(client, url, data):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                response = httpx.Response(500)
                raise httpx.HTTPStatusError(
                    "Internal Server Error",
                    request=MagicMock(),
                    response=response,
                )
            return {"status": "ok", "url": url, "data": data}

        mock_client = MagicMock()

        result = await with_retry(
            make_request,
            mock_client,
            "https://api.example.com",
            {"key": "value"},
            config=RetryConfig(max_retries=3, initial_delay=0.01),
        )

        assert result == {"status": "ok", "url": "https://api.example.com", "data": {"key": "value"}}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_rate_limited_response_retry(self):
        """Test retry behavior for 429 Too Many Requests."""
        call_count = 0

        @retry(config=RetryConfig(max_retries=3, initial_delay=0.01))
        async def rate_limited_request():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                response = httpx.Response(429)
                raise httpx.HTTPStatusError(
                    "Too Many Requests",
                    request=MagicMock(),
                    response=response,
                )
            return "success"

        result = await rate_limited_request()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_aggressive_config_behavior(self):
        """Test RetryConfig.aggressive() preset."""
        config = RetryConfig.aggressive()
        assert config.max_retries == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 30.0

    @pytest.mark.asyncio
    async def test_conservative_config_behavior(self):
        """Test RetryConfig.conservative() preset."""
        config = RetryConfig.conservative()
        assert config.max_retries == 2
        assert config.initial_delay == 2.0
        assert config.max_delay == 120.0
