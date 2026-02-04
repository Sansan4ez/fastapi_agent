"""
ACP Core Types and Enumerations

Defines the fundamental types used throughout the ACP protocol.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import random


class RunStatus(str, Enum):
    """
    Run lifecycle states as defined by ACP specification.

    State transitions:
        created -> in_progress -> completed
                              -> failed
                              -> awaiting (pause for external info)
                              -> cancelling -> cancelled
    """

    CREATED = "created"
    IN_PROGRESS = "in-progress"
    AWAITING = "awaiting"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentStatus(str, Enum):
    """
    Agent lifecycle states for operational monitoring.

    State transitions:
        INITIALIZING -> ACTIVE -> DEGRADED -> RETIRING -> RETIRED
    """

    INITIALIZING = "initializing"
    ACTIVE = "active"
    DEGRADED = "degraded"
    RETIRING = "retiring"
    RETIRED = "retired"


class RunMode(str, Enum):
    """
    Execution modes for agent runs.

    - SYNC: Blocks until completion, returns full response
    - ASYNC: Fire-and-forget with run_id, poll for results
    - STREAM: Server pushes incremental delta messages via SSE/WebSocket
    """

    SYNC = "sync"
    ASYNC = "async"
    STREAM = "stream"


class ContentEncoding(str, Enum):
    """
    Content encoding for message parts.

    - PLAIN: Content is plain text/JSON
    - BASE64: Content is base64 encoded (for binary data)
    """

    PLAIN = "plain"
    BASE64 = "base64"


class MessageRole(str, Enum):
    """
    Role identifier for message authors.

    - USER: Message from the user/client
    - AGENT: Message from an agent (generic)
    - SYSTEM: System-level messages

    Note: Agent-specific roles use format "agent/{agent_name}"
    """

    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class ErrorCode(str, Enum):
    """
    Standard error codes for ACP responses.
    """

    SERVER_ERROR = "server_error"
    INVALID_INPUT = "invalid_input"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    CONFLICT = "conflict"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    AGENT_ERROR = "agent_error"
    VALIDATION_ERROR = "validation_error"


class MetadataType(str, Enum):
    """
    Types of metadata that can be attached to message parts.
    """

    CITATION = "citation"
    TRAJECTORY = "trajectory"
    CUSTOM = "custom"


class AuthType(str, Enum):
    """
    Authentication types supported for ACP client connections.

    - NONE: No authentication required
    - BEARER: Bearer token authentication (Authorization: Bearer <token>)
    - API_KEY: API key authentication (configurable header or query parameter)
    """

    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"


@dataclass
class AuthConfig:
    """
    Configuration for authentication when connecting to ACP servers.

    Supports multiple authentication methods:
    - Bearer token: Adds 'Authorization: Bearer <token>' header
    - API key: Adds API key to a configurable header (default: X-API-Key)
      or query parameter

    Attributes:
        auth_type: The type of authentication to use.
        token: The authentication token (for Bearer auth).
        key: The API key (for API key auth).
        key_header: Header name for API key (default: "X-API-Key").
        key_query_param: Query parameter name for API key (alternative to header).

    Examples:
        >>> # No authentication
        >>> config = AuthConfig.none()

        >>> # Bearer token authentication
        >>> config = AuthConfig.bearer("my-secret-token")

        >>> # API key in header (default: X-API-Key)
        >>> config = AuthConfig.api_key("my-api-key")

        >>> # API key in custom header
        >>> config = AuthConfig.api_key("my-api-key", header="Authorization")

        >>> # API key as query parameter
        >>> config = AuthConfig.api_key("my-api-key", query_param="api_key")
    """

    auth_type: AuthType = AuthType.NONE
    token: Optional[str] = None
    key: Optional[str] = None
    key_header: str = "X-API-Key"
    key_query_param: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.auth_type == AuthType.BEARER and not self.token:
            raise ValueError("Bearer authentication requires a token")
        if self.auth_type == AuthType.API_KEY and not self.key:
            raise ValueError("API key authentication requires a key")

    def get_headers(self) -> dict[str, str]:
        """
        Get authentication headers to include in requests.

        Returns:
            Dictionary of headers to add to HTTP requests.

        Example:
            >>> config = AuthConfig.bearer("my-token")
            >>> config.get_headers()
            {'Authorization': 'Bearer my-token'}

            >>> config = AuthConfig.api_key("my-key")
            >>> config.get_headers()
            {'X-API-Key': 'my-key'}
        """
        headers: dict[str, str] = {}

        if self.auth_type == AuthType.BEARER and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.auth_type == AuthType.API_KEY and self.key:
            if self.key_query_param is None:
                # Use header-based auth
                headers[self.key_header] = self.key

        return headers

    def get_query_params(self) -> dict[str, str]:
        """
        Get authentication query parameters to include in requests.

        Returns:
            Dictionary of query parameters to add to HTTP requests.

        Example:
            >>> config = AuthConfig.api_key("my-key", query_param="api_key")
            >>> config.get_query_params()
            {'api_key': 'my-key'}
        """
        params: dict[str, str] = {}

        if (
            self.auth_type == AuthType.API_KEY
            and self.key
            and self.key_query_param
        ):
            params[self.key_query_param] = self.key

        return params

    @classmethod
    def none(cls) -> "AuthConfig":
        """
        Create a configuration with no authentication.

        Returns:
            AuthConfig with auth_type=NONE.

        Example:
            >>> config = AuthConfig.none()
            >>> config.auth_type
            <AuthType.NONE: 'none'>
        """
        return cls(auth_type=AuthType.NONE)

    @classmethod
    def bearer(cls, token: str) -> "AuthConfig":
        """
        Create a Bearer token authentication configuration.

        Args:
            token: The Bearer token to use for authentication.

        Returns:
            AuthConfig configured for Bearer authentication.

        Example:
            >>> config = AuthConfig.bearer("my-secret-token")
            >>> config.get_headers()
            {'Authorization': 'Bearer my-secret-token'}
        """
        return cls(auth_type=AuthType.BEARER, token=token)

    @classmethod
    def api_key(
        cls,
        key: str,
        header: str = "X-API-Key",
        query_param: Optional[str] = None,
    ) -> "AuthConfig":
        """
        Create an API key authentication configuration.

        Args:
            key: The API key to use for authentication.
            header: Header name for API key (default: "X-API-Key").
                   Ignored if query_param is specified.
            query_param: Query parameter name for API key.
                        If specified, the API key will be sent as a query
                        parameter instead of a header.

        Returns:
            AuthConfig configured for API key authentication.

        Example:
            >>> # API key in default header
            >>> config = AuthConfig.api_key("my-key")
            >>> config.get_headers()
            {'X-API-Key': 'my-key'}

            >>> # API key in custom header
            >>> config = AuthConfig.api_key("my-key", header="Api-Token")
            >>> config.get_headers()
            {'Api-Token': 'my-key'}

            >>> # API key as query parameter
            >>> config = AuthConfig.api_key("my-key", query_param="apikey")
            >>> config.get_query_params()
            {'apikey': 'my-key'}
        """
        return cls(
            auth_type=AuthType.API_KEY,
            key=key,
            key_header=header,
            key_query_param=query_param,
        )


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior with exponential backoff.

    Implements exponential backoff with optional jitter for robust retry logic.
    The delay between retries is calculated as:
        delay = min(initial_delay * (exponential_base ** attempt), max_delay)

    If jitter is enabled, a random factor (0.5 to 1.5) is applied to the delay
    to prevent thundering herd problems when multiple clients retry simultaneously.

    Attributes:
        max_retries: Maximum number of retry attempts (0 means no retries).
        initial_delay: Initial delay in seconds before the first retry.
        max_delay: Maximum delay in seconds between retries (caps the exponential growth).
        exponential_base: Base for exponential backoff calculation (default 2.0 for doubling).
        jitter: Whether to add random jitter to retry delays.
        retryable_status_codes: HTTP status codes that should trigger a retry.
        retryable_exceptions: Tuple of exception types that should trigger a retry.

    Example:
        >>> config = RetryConfig(max_retries=3, initial_delay=1.0)
        >>> # Retry delays: ~1s, ~2s, ~4s (with jitter applied if enabled)

        >>> config = RetryConfig(
        ...     max_retries=5,
        ...     initial_delay=0.5,
        ...     max_delay=30.0,
        ...     exponential_base=2.0,
        ...     jitter=True
        ... )
    """

    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_status_codes: tuple[int, ...] = field(
        default_factory=lambda: (408, 429, 500, 502, 503, 504)
    )
    retryable_exceptions: tuple[type[Exception], ...] = field(
        default_factory=lambda: (ConnectionError, TimeoutError)
    )

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.initial_delay <= 0:
            raise ValueError("initial_delay must be positive")
        if self.max_delay <= 0:
            raise ValueError("max_delay must be positive")
        if self.exponential_base <= 1:
            raise ValueError("exponential_base must be greater than 1")
        if self.initial_delay > self.max_delay:
            raise ValueError("initial_delay cannot exceed max_delay")

    def get_delay(self, attempt: int) -> float:
        """
        Calculate the delay for a given retry attempt.

        Args:
            attempt: The retry attempt number (0-indexed, 0 is the first retry).

        Returns:
            The delay in seconds before the next retry.

        Example:
            >>> config = RetryConfig(initial_delay=1.0, exponential_base=2.0)
            >>> config.get_delay(0)  # First retry
            1.0  # (may vary with jitter)
            >>> config.get_delay(1)  # Second retry
            2.0  # (may vary with jitter)
            >>> config.get_delay(2)  # Third retry
            4.0  # (may vary with jitter)
        """
        # Calculate base delay with exponential backoff
        delay = self.initial_delay * (self.exponential_base ** attempt)

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Apply jitter if enabled (random factor between 0.5 and 1.5)
        if self.jitter:
            jitter_factor = 0.5 + random.random()  # Range: [0.5, 1.5)
            delay = delay * jitter_factor

        return delay

    def should_retry(
        self,
        attempt: int,
        status_code: Optional[int] = None,
        exception: Optional[Exception] = None,
    ) -> bool:
        """
        Determine if a retry should be attempted.

        Args:
            attempt: The current attempt number (0-indexed).
            status_code: Optional HTTP status code from the response.
            exception: Optional exception that was raised.

        Returns:
            True if a retry should be attempted, False otherwise.

        Example:
            >>> config = RetryConfig(max_retries=3)
            >>> config.should_retry(0, status_code=503)
            True
            >>> config.should_retry(3, status_code=503)  # Max retries reached
            False
            >>> config.should_retry(0, status_code=404)  # Not retryable
            False
        """
        # Check if we've exceeded max retries
        if attempt >= self.max_retries:
            return False

        # Check status code
        if status_code is not None:
            return status_code in self.retryable_status_codes

        # Check exception type
        if exception is not None:
            return isinstance(exception, self.retryable_exceptions)

        # Default: don't retry if no condition matched
        return False

    @classmethod
    def no_retry(cls) -> "RetryConfig":
        """
        Create a configuration that disables retries.

        Returns:
            RetryConfig with max_retries=0.

        Example:
            >>> config = RetryConfig.no_retry()
            >>> config.max_retries
            0
        """
        return cls(max_retries=0)

    @classmethod
    def aggressive(cls) -> "RetryConfig":
        """
        Create an aggressive retry configuration for critical operations.

        Uses more retries with shorter initial delays.

        Returns:
            RetryConfig optimized for critical operations.

        Example:
            >>> config = RetryConfig.aggressive()
            >>> config.max_retries
            5
        """
        return cls(
            max_retries=5,
            initial_delay=0.5,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True,
        )

    @classmethod
    def conservative(cls) -> "RetryConfig":
        """
        Create a conservative retry configuration.

        Uses fewer retries with longer delays to reduce load on servers.

        Returns:
            RetryConfig optimized for reducing server load.

        Example:
            >>> config = RetryConfig.conservative()
            >>> config.max_retries
            2
        """
        return cls(
            max_retries=2,
            initial_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=True,
        )
