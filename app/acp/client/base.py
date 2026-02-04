"""
ACP Client Base

Main client class for interacting with ACP servers.
"""

from typing import Any, AsyncGenerator, Callable
from uuid import UUID
import httpx
from loguru import logger

from app.acp.core.models import Message, MessagePart, AgentManifest, Run
from app.acp.core.types import RunStatus, RunMode, RetryConfig
from app.acp.core.schemas import (
    RunCreateRequest,
    RunResumeRequest,
    RunResponse,
    AgentListResponse,
    AgentResponse,
    SessionResponse,
)
from app.acp.utils.http_retry import with_retry, RetryExhaustedError


class ACPClientError(Exception):
    """Base exception for ACP client errors."""

    def __init__(self, message: str, code: str | None = None, data: Any = None):
        super().__init__(message)
        self.code = code
        self.data = data


class ACPClient:
    """
    ACP Client for interacting with ACP servers.

    Provides methods for:
    - Agent discovery and listing
    - Creating and managing runs
    - Session management
    - Streaming responses

    Usage:
        async with ACPClient(base_url="http://localhost:8000") as client:
            # List agents
            agents = await client.list_agents()

            # Run an agent synchronously
            result = await client.run_sync(
                agent="my_agent",
                input=[Message.user_text("Hello!")],
            )

            # Run an agent asynchronously
            run_id = await client.run_async(agent="my_agent", input=[...])
            result = await client.wait_for_run(run_id)
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        retry_config: RetryConfig | None = None,
        on_retry: Callable[[int, Exception | None, int | None], None] | None = None,
    ):
        """
        Initialize the ACP client.

        Args:
            base_url: Base URL of the ACP server
            timeout: Request timeout in seconds
            headers: Additional headers for requests
            retry_config: Configuration for retry behavior with exponential backoff.
                         Pass RetryConfig.no_retry() to disable retries.
                         Defaults to RetryConfig() (3 retries with exponential backoff).
            on_retry: Optional callback called before each retry with
                     (attempt, exception, status_code) arguments.
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._headers = headers or {}
        self._client: httpx.AsyncClient | None = None
        self._retry_config = retry_config if retry_config is not None else RetryConfig()
        self._on_retry = on_retry

    async def __aenter__(self) -> "ACPClient":
        """Enter async context."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context."""
        await self.close()

    async def connect(self) -> None:
        """Open the HTTP client connection."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers=self._headers,
            )
            logger.debug(f"ACP client connected to {self._base_url}")

    async def close(self) -> None:
        """Close the HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("ACP client disconnected")

    def _ensure_connected(self) -> httpx.AsyncClient:
        """Ensure the client is connected."""
        if self._client is None:
            raise ACPClientError("Client not connected. Use 'async with' or call connect()")
        return self._client

    # --- Internal Request Methods with Retry ---

    async def _request_get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """
        Make a GET request with retry logic.

        Args:
            path: URL path to request
            params: Optional query parameters

        Returns:
            httpx.Response

        Raises:
            ACPClientError: If client not connected
            RetryExhaustedError: If all retry attempts fail
            httpx.HTTPStatusError: If non-retryable HTTP error occurs
        """
        client = self._ensure_connected()

        async def _do_request() -> httpx.Response:
            response = await client.get(path, params=params)
            response.raise_for_status()
            return response

        return await with_retry(
            _do_request,
            config=self._retry_config,
            on_retry=self._on_retry,
        )

    async def _request_post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """
        Make a POST request with retry logic.

        Args:
            path: URL path to request
            json: Optional JSON body

        Returns:
            httpx.Response

        Raises:
            ACPClientError: If client not connected
            RetryExhaustedError: If all retry attempts fail
            httpx.HTTPStatusError: If non-retryable HTTP error occurs
        """
        client = self._ensure_connected()

        async def _do_request() -> httpx.Response:
            response = await client.post(path, json=json)
            response.raise_for_status()
            return response

        return await with_retry(
            _do_request,
            config=self._retry_config,
            on_retry=self._on_retry,
        )

    # --- Agent Operations ---

    async def list_agents(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> AgentListResponse:
        """
        List available agents.

        Args:
            offset: Pagination offset
            limit: Maximum agents to return

        Returns:
            AgentListResponse with agents list

        Raises:
            RetryExhaustedError: If all retry attempts fail
            httpx.HTTPStatusError: If non-retryable HTTP error occurs
        """
        response = await self._request_get(
            "/agents",
            params={"offset": offset, "limit": limit},
        )
        return AgentListResponse.model_validate(response.json())

    async def get_agent(self, name: str) -> AgentManifest:
        """
        Get a specific agent by name.

        Args:
            name: Agent name

        Returns:
            AgentManifest

        Raises:
            ACPClientError: If agent not found
            RetryExhaustedError: If all retry attempts fail
            httpx.HTTPStatusError: If non-retryable HTTP error occurs
        """
        try:
            response = await self._request_get(f"/agents/{name}")
            data = AgentResponse.model_validate(response.json())
            return data.agent
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise ACPClientError(f"Agent '{name}' not found", code="not_found") from exc
            raise

    # --- Run Operations ---

    async def run_sync(
        self,
        agent: str,
        input: list[Message],
        session_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RunResponse:
        """
        Run an agent synchronously (blocks until completion).

        Args:
            agent: Agent name
            input: Input messages
            session_id: Optional session ID
            metadata: Optional metadata

        Returns:
            RunResponse with results
        """
        return await self._create_run(
            agent=agent,
            input=input,
            mode=RunMode.SYNC,
            session_id=session_id,
            metadata=metadata,
        )

    async def run_async(
        self,
        agent: str,
        input: list[Message],
        session_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UUID:
        """
        Run an agent asynchronously (returns immediately).

        Args:
            agent: Agent name
            input: Input messages
            session_id: Optional session ID
            metadata: Optional metadata

        Returns:
            Run ID for polling
        """
        response = await self._create_run(
            agent=agent,
            input=input,
            mode=RunMode.ASYNC,
            session_id=session_id,
            metadata=metadata,
        )
        return response.run_id

    async def run_stream(
        self,
        agent: str,
        input: list[Message],
        session_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncGenerator[Message | dict[str, Any], None]:
        """
        Run an agent with streaming response.

        Args:
            agent: Agent name
            input: Input messages
            session_id: Optional session ID
            metadata: Optional metadata

        Yields:
            Messages and events as they arrive
        """
        client = self._ensure_connected()

        request = RunCreateRequest(
            agent=agent,
            input=input,
            mode=RunMode.STREAM,
            session_id=session_id,
            metadata=metadata or {},
        )

        async with client.stream(
            "POST",
            "/runs",
            json=request.model_dump(mode="json"),
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    import json
                    data = json.loads(line[6:])

                    if "role" in data:
                        yield Message.model_validate(data)
                    else:
                        yield data

    async def _create_run(
        self,
        agent: str,
        input: list[Message],
        mode: RunMode,
        session_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RunResponse:
        """
        Create a run with the specified mode.

        Raises:
            RetryExhaustedError: If all retry attempts fail
            httpx.HTTPStatusError: If non-retryable HTTP error occurs
        """
        request = RunCreateRequest(
            agent=agent,
            input=input,
            mode=mode,
            session_id=session_id,
            metadata=metadata or {},
        )

        response = await self._request_post(
            "/runs",
            json=request.model_dump(mode="json"),
        )
        return RunResponse.model_validate(response.json())

    async def get_run(self, run_id: UUID) -> RunResponse:
        """
        Get a run by ID.

        Args:
            run_id: The run ID

        Returns:
            RunResponse

        Raises:
            ACPClientError: If run not found
            RetryExhaustedError: If all retry attempts fail
            httpx.HTTPStatusError: If non-retryable HTTP error occurs
        """
        try:
            response = await self._request_get(f"/runs/{run_id}")
            return RunResponse.model_validate(response.json())
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise ACPClientError(f"Run '{run_id}' not found", code="not_found") from exc
            raise

    async def wait_for_run(
        self,
        run_id: UUID,
        poll_interval: float = 1.0,
        timeout: float | None = None,
    ) -> RunResponse:
        """
        Wait for an async run to complete.

        Args:
            run_id: The run ID
            poll_interval: Seconds between polls
            timeout: Maximum wait time (None for no timeout)

        Returns:
            Final RunResponse

        Raises:
            ACPClientError: If timeout exceeded
        """
        import asyncio

        start_time = asyncio.get_event_loop().time()

        while True:
            response = await self.get_run(run_id)

            if response.status in [
                RunStatus.COMPLETED,
                RunStatus.FAILED,
                RunStatus.CANCELLED,
                RunStatus.AWAITING,
            ]:
                return response

            if timeout:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    raise ACPClientError(
                        f"Timeout waiting for run {run_id}",
                        code="timeout",
                    )

            await asyncio.sleep(poll_interval)

    async def resume_run(
        self,
        run_id: UUID,
        input: list[Message],
        metadata: dict[str, Any] | None = None,
    ) -> RunResponse:
        """
        Resume an awaiting run.

        Args:
            run_id: The run ID to resume
            input: Input messages for resumption
            metadata: Optional additional metadata

        Returns:
            RunResponse

        Raises:
            RetryExhaustedError: If all retry attempts fail
            httpx.HTTPStatusError: If non-retryable HTTP error occurs
        """
        request = RunResumeRequest(
            input=input,
            metadata=metadata or {},
        )

        response = await self._request_post(
            f"/runs/{run_id}",
            json=request.model_dump(mode="json"),
        )
        return RunResponse.model_validate(response.json())

    async def cancel_run(self, run_id: UUID) -> RunResponse:
        """
        Cancel a running run.

        Args:
            run_id: The run ID to cancel

        Returns:
            RunResponse

        Raises:
            RetryExhaustedError: If all retry attempts fail
            httpx.HTTPStatusError: If non-retryable HTTP error occurs
        """
        response = await self._request_post(f"/runs/{run_id}/cancel")
        return RunResponse.model_validate(response.json())

    # --- Session Operations ---

    async def get_session(self, session_id: UUID) -> SessionResponse:
        """
        Get a session by ID.

        Args:
            session_id: The session ID

        Returns:
            SessionResponse

        Raises:
            ACPClientError: If session not found
            RetryExhaustedError: If all retry attempts fail
            httpx.HTTPStatusError: If non-retryable HTTP error occurs
        """
        try:
            response = await self._request_get(f"/sessions/{session_id}")
            return SessionResponse.model_validate(response.json())
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise ACPClientError(f"Session '{session_id}' not found", code="not_found") from exc
            raise

    # --- Convenience Methods ---

    async def run_text(
        self,
        agent: str,
        text: str,
        session_id: UUID | None = None,
    ) -> str:
        """
        Simple convenience method to run an agent with text input.

        Args:
            agent: Agent name
            text: Input text
            session_id: Optional session ID

        Returns:
            Output text (first text/plain part from first message)
        """
        response = await self.run_sync(
            agent=agent,
            input=[Message.user_text(text)],
            session_id=session_id,
        )

        if response.status == RunStatus.FAILED:
            error_msg = response.error.message if response.error else "Unknown error"
            raise ACPClientError(f"Agent execution failed: {error_msg}")

        if response.output:
            for part in response.output[0].parts:
                if part.content_type == "text/plain" and part.content:
                    return part.content

        return ""
