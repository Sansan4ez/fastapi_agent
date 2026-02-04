"""
ACP (Agent Communication Protocol) Client Service.

This module provides a client service for discovering and invoking
external AI agents via the ACP protocol.
"""

from typing import Optional, Callable
from dataclasses import dataclass

import httpx
from loguru import logger

from app.config import settings
from app.acp.core.types import RetryConfig
from app.acp.utils.http_retry import with_retry, RetryExhaustedError


@dataclass
class AgentInfo:
    """Information about an ACP agent."""
    name: str
    description: str


@dataclass
class RunResult:
    """Result from running an ACP agent."""
    status: str
    output: str
    run_id: Optional[str] = None


class ACPClientService:
    """
    Client service for interacting with ACP (Agent Communication Protocol) servers.

    This service provides methods to:
    - Discover available agents on an ACP server
    - Invoke agents with user messages
    - Track conversation sessions
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        retry_config: Optional[RetryConfig] = None,
        on_retry: Optional[Callable[[int, Optional[Exception], Optional[int]], None]] = None,
    ):
        """
        Initialize the ACP client service.

        Args:
            base_url: Base URL of the ACP server. Defaults to settings.ACP_SERVER_URL.
            timeout: Request timeout in seconds. Defaults to settings.ACP_REQUEST_TIMEOUT.
            retry_config: Configuration for retry behavior with exponential backoff.
                         Pass RetryConfig.no_retry() to disable retries.
                         Defaults to RetryConfig() (3 retries with exponential backoff).
            on_retry: Optional callback called before each retry with
                     (attempt, exception, status_code) arguments.
        """
        self.base_url = (base_url or settings.ACP_SERVER_URL).rstrip("/")
        self.timeout = timeout or settings.ACP_REQUEST_TIMEOUT
        self._client: Optional[httpx.AsyncClient] = None
        self._retry_config = retry_config if retry_config is not None else RetryConfig()
        self._on_retry = on_retry

    async def __aenter__(self) -> "ACPClientService":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get the HTTP client, creating one if needed."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout)
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request_get(self, path: str) -> httpx.Response:
        """Make a GET request with retry logic."""
        client = self._get_client()

        async def _do_request() -> httpx.Response:
            response = await client.get(path)
            response.raise_for_status()
            return response

        return await with_retry(
            _do_request,
            config=self._retry_config,
            on_retry=self._on_retry,
        )

    async def _request_post(self, path: str, json: dict) -> httpx.Response:
        """Make a POST request with retry logic."""
        client = self._get_client()

        async def _do_request() -> httpx.Response:
            response = await client.post(path, json=json)
            response.raise_for_status()
            return response

        return await with_retry(
            _do_request,
            config=self._retry_config,
            on_retry=self._on_retry,
        )

    async def ping(self) -> bool:
        """
        Check if the ACP server is reachable.

        Returns:
            True if the server responds, False otherwise.
        """
        try:
            client = self._get_client()
            response = await client.get("/ping")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"ACP server ping failed: {e}")
            return False

    async def list_agents(self) -> list[AgentInfo]:
        """
        Discover available agents on the ACP server.

        Returns:
            List of AgentInfo objects describing available agents.

        Raises:
            ACPClientError: If the request fails.
            RetryExhaustedError: If all retry attempts fail.
        """
        try:
            response = await self._request_get("/agents")
            data = response.json()
            agents = []

            # Handle both list and dict response formats
            if isinstance(data, list):
                for agent_data in data:
                    agents.append(AgentInfo(
                        name=agent_data.get("name", "unknown"),
                        description=agent_data.get("description", "No description available")
                    ))
            elif isinstance(data, dict):
                # Some ACP servers return agents in a dict format
                for name, details in data.items():
                    if isinstance(details, dict):
                        agents.append(AgentInfo(
                            name=name,
                            description=details.get("description", "No description available")
                        ))
                    else:
                        agents.append(AgentInfo(name=name, description=str(details)))

            logger.info(f"Discovered {len(agents)} agents from ACP server")
            return agents

        except RetryExhaustedError:
            logger.error("Failed to list agents: all retry attempts exhausted")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list agents: HTTP {e.response.status_code}")
            raise ACPClientError(f"Failed to list agents: HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to ACP server: {e}")
            raise ACPClientError(f"Failed to connect to ACP server: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error listing agents: {e}")
            raise ACPClientError(f"Unexpected error: {e}") from e

    async def run_agent(
        self,
        agent_name: str,
        message: str,
        session_id: Optional[str] = None
    ) -> RunResult:
        """
        Invoke an agent with a message and get the response.

        Args:
            agent_name: Name of the agent to invoke.
            message: User message to send to the agent.
            session_id: Optional session ID for conversation continuity.

        Returns:
            RunResult containing the agent's response.

        Raises:
            ACPClientError: If the request fails.
            RetryExhaustedError: If all retry attempts fail.
        """
        try:
            # Build the request payload following ACP protocol
            payload: dict = {
                "input": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "content": message,
                                "content_type": "text/plain"
                            }
                        ]
                    }
                ]
            }

            if session_id:
                payload["session_id"] = session_id

            # Create a synchronous run (waits for completion)
            response = await self._request_post(
                f"/agents/{agent_name}/runs",
                json=payload
            )

            data = response.json()

            # Extract output from response
            output_text = self._extract_output(data)

            logger.info(f"Agent '{agent_name}' run completed successfully")

            return RunResult(
                status=data.get("status", "completed"),
                output=output_text,
                run_id=data.get("run_id") or data.get("id")
            )

        except RetryExhaustedError:
            logger.error(f"Agent '{agent_name}' run failed: all retry attempts exhausted")
            raise
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ACPClientError(f"Agent '{agent_name}' not found") from e
            logger.error(f"Agent run failed: HTTP {e.response.status_code}")
            raise ACPClientError(f"Agent run failed: HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to ACP server: {e}")
            raise ACPClientError(f"Failed to connect to ACP server: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error running agent: {e}")
            raise ACPClientError(f"Unexpected error: {e}") from e

    def _extract_output(self, response_data: dict) -> str:
        """
        Extract readable text output from ACP response.

        Args:
            response_data: Raw response data from ACP server.

        Returns:
            Extracted text content.
        """
        # Try to extract output from various response formats
        if "output" in response_data:
            output = response_data["output"]
            if isinstance(output, str):
                return output
            if isinstance(output, list):
                # Output is a list of messages
                texts = []
                for msg in output:
                    if isinstance(msg, dict):
                        parts = msg.get("parts", [])
                        for part in parts:
                            if isinstance(part, dict):
                                content = part.get("content", "")
                                if content:
                                    texts.append(str(content))
                            elif isinstance(part, str):
                                texts.append(part)
                    elif isinstance(msg, str):
                        texts.append(msg)
                return "\n".join(texts) if texts else "No output"

        # Fallback: try to get any text-like content
        if "result" in response_data:
            return str(response_data["result"])

        if "message" in response_data:
            return str(response_data["message"])

        return "Agent completed (no text output)"


class ACPClientError(Exception):
    """Exception raised for ACP client errors."""
    pass


# Singleton instance for convenience
_default_client: Optional[ACPClientService] = None


def get_acp_client() -> ACPClientService:
    """
    Get the default ACP client instance.

    Returns:
        ACPClientService instance.
    """
    global _default_client
    if _default_client is None:
        _default_client = ACPClientService()
    return _default_client
