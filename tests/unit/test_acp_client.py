"""
Unit tests for ACP Client HTTP operations.

Tests cover:
- ACPClient initialization and connection management
- Agent operations (list_agents, get_agent)
- Run operations (run_sync, run_async, get_run, wait_for_run, resume_run, cancel_run)
- Session operations (get_session)
- Streaming operations (run_stream)
- Convenience methods (run_text)
- Error handling
- ACPClientService operations

All tests use mocked httpx to avoid actual network requests.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest

from app.acp.client.base import ACPClient, ACPClientError
from app.acp.core.models import Message, MessagePart, AgentManifest, AgentMetadata
from app.acp.core.types import RunStatus, RunMode, AgentStatus, ErrorCode, RetryConfig
from app.acp.core.schemas import (
    RunResponse,
    AgentListResponse,
    AgentResponse,
    SessionResponse,
)
from app.acp.utils.http_retry import RetryExhaustedError
from app.services.acp_client import ACPClientService, ACPClientError as ServiceClientError


# =============================================================================
# Fixed Test Data
# =============================================================================

FIXTURE_RUN_ID = UUID("12345678-1234-5678-1234-567812345678")
FIXTURE_SESSION_ID = UUID("87654321-4321-8765-4321-876543218765")
FIXTURE_TIMESTAMP = datetime(2024, 1, 15, 12, 0, 0)
FIXTURE_TIMESTAMP_LATER = datetime(2024, 1, 15, 12, 5, 0)


# =============================================================================
# ACPClient Tests
# =============================================================================


class TestACPClientInitialization:
    """Tests for ACPClient initialization and configuration."""

    def test_init_with_base_url(self):
        """Verify client initializes with base URL."""
        client = ACPClient(base_url="http://localhost:8000")
        assert client._base_url == "http://localhost:8000"
        assert client._timeout == 30.0
        assert client._headers == {}
        assert client._client is None

    def test_init_strips_trailing_slash(self):
        """Verify trailing slash is stripped from base URL."""
        client = ACPClient(base_url="http://localhost:8000/")
        assert client._base_url == "http://localhost:8000"

    def test_init_with_custom_timeout(self):
        """Verify client initializes with custom timeout."""
        client = ACPClient(base_url="http://localhost:8000", timeout=60.0)
        assert client._timeout == 60.0

    def test_init_with_custom_headers(self):
        """Verify client initializes with custom headers."""
        headers = {"Authorization": "Bearer token123"}
        client = ACPClient(base_url="http://localhost:8000", headers=headers)
        assert client._headers == headers


class TestACPClientConnectionManagement:
    """Tests for ACPClient connection lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_creates_client(self):
        """Verify connect creates httpx client."""
        client = ACPClient(base_url="http://localhost:8000")

        await client.connect()

        assert client._client is not None
        assert isinstance(client._client, httpx.AsyncClient)

        await client.close()

    @pytest.mark.asyncio
    async def test_connect_idempotent(self):
        """Verify multiple connect calls don't create new clients."""
        client = ACPClient(base_url="http://localhost:8000")

        await client.connect()
        first_client = client._client

        await client.connect()
        second_client = client._client

        assert first_client is second_client

        await client.close()

    @pytest.mark.asyncio
    async def test_close_cleans_up_client(self):
        """Verify close cleans up httpx client."""
        client = ACPClient(base_url="http://localhost:8000")

        await client.connect()
        assert client._client is not None

        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        """Verify multiple close calls are safe."""
        client = ACPClient(base_url="http://localhost:8000")

        await client.connect()
        await client.close()
        await client.close()  # Should not raise

        assert client._client is None

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Verify async context manager connects and closes."""
        async with ACPClient(base_url="http://localhost:8000") as client:
            assert client._client is not None

        assert client._client is None

    def test_ensure_connected_raises_when_not_connected(self):
        """Verify _ensure_connected raises when not connected."""
        client = ACPClient(base_url="http://localhost:8000")

        with pytest.raises(ACPClientError) as exc_info:
            client._ensure_connected()

        assert "not connected" in str(exc_info.value).lower()


# =============================================================================
# Agent Operations Tests
# =============================================================================


class TestACPClientListAgents:
    """Tests for ACPClient.list_agents method."""

    @pytest.mark.asyncio
    async def test_list_agents_success(self):
        """Verify list_agents returns agents on success."""
        mock_response_data = {
            "agents": [
                {
                    "name": "test-agent",
                    "description": "A test agent",
                    "input_content_types": ["text/plain"],
                    "output_content_types": ["text/plain"],
                    "status": "active",
                },
            ],
            "total": 1,
            "offset": 0,
            "limit": 100,
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        result = await client.list_agents()

        assert isinstance(result, AgentListResponse)
        assert len(result.agents) == 1
        assert result.agents[0].name == "test-agent"
        assert result.total == 1

        mock_http_client.get.assert_called_once_with(
            "/agents",
            params={"offset": 0, "limit": 100},
        )

    @pytest.mark.asyncio
    async def test_list_agents_with_pagination(self):
        """Verify list_agents passes pagination parameters."""
        mock_response_data = {
            "agents": [],
            "total": 50,
            "offset": 10,
            "limit": 20,
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        result = await client.list_agents(offset=10, limit=20)

        assert result.offset == 10
        assert result.limit == 20

        mock_http_client.get.assert_called_once_with(
            "/agents",
            params={"offset": 10, "limit": 20},
        )

    @pytest.mark.asyncio
    async def test_list_agents_raises_on_http_error(self):
        """Verify list_agents raises RetryExhaustedError on retryable HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=mock_response,
        )

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        # Use no_retry config to avoid delays in tests
        client = ACPClient(
            base_url="http://localhost:8000",
            retry_config=RetryConfig.no_retry(),
        )
        client._client = mock_http_client

        # With no_retry config, it raises the original HTTPStatusError
        with pytest.raises(httpx.HTTPStatusError):
            await client.list_agents()

    @pytest.mark.asyncio
    async def test_list_agents_raises_retry_exhausted_on_repeated_error(self):
        """Verify list_agents raises RetryExhaustedError when retries are exhausted."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service Unavailable",
            request=MagicMock(),
            response=mock_response,
        )

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        # Use minimal retries for faster tests
        client = ACPClient(
            base_url="http://localhost:8000",
            retry_config=RetryConfig(max_retries=1, initial_delay=0.01),
        )
        client._client = mock_http_client

        with pytest.raises(RetryExhaustedError):
            await client.list_agents()


class TestACPClientGetAgent:
    """Tests for ACPClient.get_agent method."""

    @pytest.mark.asyncio
    async def test_get_agent_success(self):
        """Verify get_agent returns agent manifest on success."""
        mock_response_data = {
            "agent": {
                "name": "test-agent",
                "description": "A test agent",
                "input_content_types": ["text/plain"],
                "output_content_types": ["text/plain"],
                "status": "active",
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        client = ACPClient(
            base_url="http://localhost:8000",
            retry_config=RetryConfig.no_retry(),
        )
        client._client = mock_http_client

        result = await client.get_agent("test-agent")

        assert isinstance(result, AgentManifest)
        assert result.name == "test-agent"

        # Verify the GET request was made (with params=None from _request_get)
        mock_http_client.get.assert_called_once()
        call_args = mock_http_client.get.call_args
        assert call_args[0][0] == "/agents/test-agent"

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self):
        """Verify get_agent raises ACPClientError when agent not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response,
        )

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        client = ACPClient(
            base_url="http://localhost:8000",
            retry_config=RetryConfig.no_retry(),
        )
        client._client = mock_http_client

        with pytest.raises(ACPClientError) as exc_info:
            await client.get_agent("nonexistent-agent")

        assert exc_info.value.code == "not_found"
        assert "nonexistent-agent" in str(exc_info.value)


# =============================================================================
# Run Operations Tests
# =============================================================================


class TestACPClientRunSync:
    """Tests for ACPClient.run_sync method."""

    @pytest.mark.asyncio
    async def test_run_sync_success(self):
        """Verify run_sync creates run and returns response."""
        mock_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "session_id": str(FIXTURE_SESSION_ID),
            "status": "completed",
            "output": [
                {
                    "role": "agent",
                    "parts": [{"content": "Hello!", "content_type": "text/plain"}],
                }
            ],
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
            "completed_at": FIXTURE_TIMESTAMP_LATER.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        input_messages = [Message.user_text("Hello!")]
        result = await client.run_sync(
            agent="test-agent",
            input=input_messages,
            session_id=FIXTURE_SESSION_ID,
        )

        assert isinstance(result, RunResponse)
        assert result.run_id == FIXTURE_RUN_ID
        assert result.status == RunStatus.COMPLETED

        # Verify POST was called with correct payload
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert call_args[0][0] == "/runs"

        payload = call_args[1]["json"]
        assert payload["agent"] == "test-agent"
        assert payload["mode"] == "sync"

    @pytest.mark.asyncio
    async def test_run_sync_with_metadata(self):
        """Verify run_sync passes metadata to request."""
        mock_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "completed",
            "output": [],
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        metadata = {"user_id": "user-123", "source": "test"}
        await client.run_sync(
            agent="test-agent",
            input=[Message.user_text("Hello!")],
            metadata=metadata,
        )

        call_args = mock_http_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["metadata"] == metadata


class TestACPClientRunAsync:
    """Tests for ACPClient.run_async method."""

    @pytest.mark.asyncio
    async def test_run_async_returns_run_id(self):
        """Verify run_async returns run ID for polling."""
        mock_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "in-progress",
            "output": [],
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        result = await client.run_async(
            agent="test-agent",
            input=[Message.user_text("Hello!")],
        )

        assert result == FIXTURE_RUN_ID

        # Verify async mode was used
        call_args = mock_http_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["mode"] == "async"


class TestACPClientGetRun:
    """Tests for ACPClient.get_run method."""

    @pytest.mark.asyncio
    async def test_get_run_success(self):
        """Verify get_run returns run response."""
        mock_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "completed",
            "output": [
                {
                    "role": "agent",
                    "parts": [{"content": "Response", "content_type": "text/plain"}],
                }
            ],
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
            "completed_at": FIXTURE_TIMESTAMP_LATER.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        client = ACPClient(
            base_url="http://localhost:8000",
            retry_config=RetryConfig.no_retry(),
        )
        client._client = mock_http_client

        result = await client.get_run(FIXTURE_RUN_ID)

        assert isinstance(result, RunResponse)
        assert result.run_id == FIXTURE_RUN_ID
        assert result.status == RunStatus.COMPLETED

        # Verify GET was called with correct path
        mock_http_client.get.assert_called_once()
        call_args = mock_http_client.get.call_args
        assert call_args[0][0] == f"/runs/{FIXTURE_RUN_ID}"

    @pytest.mark.asyncio
    async def test_get_run_not_found(self):
        """Verify get_run raises ACPClientError when run not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response,
        )

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        client = ACPClient(
            base_url="http://localhost:8000",
            retry_config=RetryConfig.no_retry(),
        )
        client._client = mock_http_client

        with pytest.raises(ACPClientError) as exc_info:
            await client.get_run(FIXTURE_RUN_ID)

        assert exc_info.value.code == "not_found"


class TestACPClientWaitForRun:
    """Tests for ACPClient.wait_for_run method."""

    @pytest.mark.asyncio
    async def test_wait_for_run_returns_on_completed(self):
        """Verify wait_for_run returns when run is completed."""
        mock_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "completed",
            "output": [],
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        result = await client.wait_for_run(FIXTURE_RUN_ID, poll_interval=0.01)

        assert result.status == RunStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_wait_for_run_returns_on_failed(self):
        """Verify wait_for_run returns when run has failed."""
        mock_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "failed",
            "output": [],
            "error": {"code": "agent_error", "message": "Something went wrong"},
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        result = await client.wait_for_run(FIXTURE_RUN_ID, poll_interval=0.01)

        assert result.status == RunStatus.FAILED

    @pytest.mark.asyncio
    async def test_wait_for_run_polls_until_complete(self):
        """Verify wait_for_run polls until run completes."""
        in_progress_response = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "in-progress",
            "output": [],
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
        }
        completed_response = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "completed",
            "output": [],
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
        }

        call_count = 0

        def get_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            if call_count < 3:
                mock_response.json.return_value = in_progress_response
            else:
                mock_response.json.return_value = completed_response
            return mock_response

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(side_effect=get_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        result = await client.wait_for_run(FIXTURE_RUN_ID, poll_interval=0.01)

        assert result.status == RunStatus.COMPLETED
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_wait_for_run_timeout(self):
        """Verify wait_for_run raises on timeout."""
        in_progress_response = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "in-progress",
            "output": [],
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = in_progress_response
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        with pytest.raises(ACPClientError) as exc_info:
            await client.wait_for_run(
                FIXTURE_RUN_ID,
                poll_interval=0.01,
                timeout=0.05,
            )

        assert exc_info.value.code == "timeout"

    @pytest.mark.asyncio
    async def test_wait_for_run_returns_on_awaiting(self):
        """Verify wait_for_run returns when run is awaiting."""
        mock_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "awaiting",
            "output": [],
            "await_request": {
                "type": "user_input",
                "description": "Please provide more info",
            },
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        result = await client.wait_for_run(FIXTURE_RUN_ID, poll_interval=0.01)

        assert result.status == RunStatus.AWAITING


class TestACPClientResumeRun:
    """Tests for ACPClient.resume_run method."""

    @pytest.mark.asyncio
    async def test_resume_run_success(self):
        """Verify resume_run sends input and returns response."""
        mock_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "completed",
            "output": [
                {
                    "role": "agent",
                    "parts": [{"content": "Resumed!", "content_type": "text/plain"}],
                }
            ],
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
            "completed_at": FIXTURE_TIMESTAMP_LATER.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        input_messages = [Message.user_text("Yes, proceed")]
        result = await client.resume_run(
            run_id=FIXTURE_RUN_ID,
            input=input_messages,
            metadata={"confirmed": True},
        )

        assert isinstance(result, RunResponse)
        assert result.status == RunStatus.COMPLETED

        # Verify correct endpoint and payload
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert call_args[0][0] == f"/runs/{FIXTURE_RUN_ID}"

        payload = call_args[1]["json"]
        assert len(payload["input"]) == 1
        assert payload["metadata"] == {"confirmed": True}


class TestACPClientCancelRun:
    """Tests for ACPClient.cancel_run method."""

    @pytest.mark.asyncio
    async def test_cancel_run_success(self):
        """Verify cancel_run cancels the run."""
        mock_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "cancelled",
            "output": [],
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        client = ACPClient(
            base_url="http://localhost:8000",
            retry_config=RetryConfig.no_retry(),
        )
        client._client = mock_http_client

        result = await client.cancel_run(FIXTURE_RUN_ID)

        assert isinstance(result, RunResponse)
        assert result.status == RunStatus.CANCELLED

        # Verify POST was called with correct path
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert call_args[0][0] == f"/runs/{FIXTURE_RUN_ID}/cancel"


# =============================================================================
# Session Operations Tests
# =============================================================================


class TestACPClientGetSession:
    """Tests for ACPClient.get_session method."""

    @pytest.mark.asyncio
    async def test_get_session_success(self):
        """Verify get_session returns session response."""
        mock_response_data = {
            "session_id": str(FIXTURE_SESSION_ID),
            "agent_name": "test-agent",
            "messages": [
                {
                    "role": "user",
                    "parts": [{"content": "Hello", "content_type": "text/plain"}],
                },
                {
                    "role": "agent",
                    "parts": [{"content": "Hi there!", "content_type": "text/plain"}],
                },
            ],
            "run_count": 1,
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
            "last_activity_at": FIXTURE_TIMESTAMP_LATER.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        result = await client.get_session(FIXTURE_SESSION_ID)

        assert isinstance(result, SessionResponse)
        assert result.session_id == FIXTURE_SESSION_ID
        assert result.agent_name == "test-agent"
        assert len(result.messages) == 2

        # Verify GET was called with correct path
        mock_http_client.get.assert_called_once()
        call_args = mock_http_client.get.call_args
        assert call_args[0][0] == f"/sessions/{FIXTURE_SESSION_ID}"

    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        """Verify get_session raises ACPClientError when session not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response,
        )

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        client = ACPClient(
            base_url="http://localhost:8000",
            retry_config=RetryConfig.no_retry(),
        )
        client._client = mock_http_client

        with pytest.raises(ACPClientError) as exc_info:
            await client.get_session(FIXTURE_SESSION_ID)

        assert exc_info.value.code == "not_found"


# =============================================================================
# Streaming Operations Tests
# =============================================================================


class TestACPClientRunStream:
    """Tests for ACPClient.run_stream method."""

    @pytest.mark.asyncio
    async def test_run_stream_yields_messages(self):
        """Verify run_stream yields messages from SSE stream."""
        # Simulate SSE response lines
        sse_lines = [
            'data: {"role": "agent", "parts": [{"content": "Hello", "content_type": "text/plain"}]}',
            'data: {"role": "agent", "parts": [{"content": " world!", "content_type": "text/plain"}]}',
            'data: {"status": "completed"}',
        ]

        async def mock_aiter_lines():
            for line in sse_lines:
                yield line

        mock_stream_response = MagicMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.aiter_lines = mock_aiter_lines
        mock_stream_response.__aenter__ = AsyncMock(return_value=mock_stream_response)
        mock_stream_response.__aexit__ = AsyncMock(return_value=None)

        mock_http_client = MagicMock()
        mock_http_client.stream = MagicMock(return_value=mock_stream_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        results = []
        async for item in client.run_stream(
            agent="test-agent",
            input=[Message.user_text("Hello!")],
        ):
            results.append(item)

        assert len(results) == 3
        # First two should be Message objects
        assert isinstance(results[0], Message)
        assert isinstance(results[1], Message)
        # Last one is a status dict
        assert results[2] == {"status": "completed"}

    @pytest.mark.asyncio
    async def test_run_stream_ignores_non_data_lines(self):
        """Verify run_stream ignores non-data SSE lines."""
        sse_lines = [
            ': keep-alive',
            '',
            'event: message',
            'data: {"role": "agent", "parts": [{"content": "Hello", "content_type": "text/plain"}]}',
        ]

        async def mock_aiter_lines():
            for line in sse_lines:
                yield line

        mock_stream_response = MagicMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.aiter_lines = mock_aiter_lines
        mock_stream_response.__aenter__ = AsyncMock(return_value=mock_stream_response)
        mock_stream_response.__aexit__ = AsyncMock(return_value=None)

        mock_http_client = MagicMock()
        mock_http_client.stream = MagicMock(return_value=mock_stream_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        results = []
        async for item in client.run_stream(
            agent="test-agent",
            input=[Message.user_text("Hello!")],
        ):
            results.append(item)

        # Only one data line should be processed
        assert len(results) == 1
        assert isinstance(results[0], Message)


# =============================================================================
# Convenience Methods Tests
# =============================================================================


class TestACPClientRunText:
    """Tests for ACPClient.run_text convenience method."""

    @pytest.mark.asyncio
    async def test_run_text_success(self):
        """Verify run_text returns text output."""
        mock_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "completed",
            "output": [
                {
                    "role": "agent",
                    "parts": [{"content": "Hello back!", "content_type": "text/plain"}],
                }
            ],
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        result = await client.run_text(agent="test-agent", text="Hello!")

        assert result == "Hello back!"

    @pytest.mark.asyncio
    async def test_run_text_returns_empty_on_no_output(self):
        """Verify run_text returns empty string when no output."""
        mock_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "completed",
            "output": [],
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        result = await client.run_text(agent="test-agent", text="Hello!")

        assert result == ""

    @pytest.mark.asyncio
    async def test_run_text_raises_on_failed_run(self):
        """Verify run_text raises ACPClientError when run fails."""
        mock_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "failed",
            "output": [],
            "error": {"code": "agent_error", "message": "Something went wrong"},
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        with pytest.raises(ACPClientError) as exc_info:
            await client.run_text(agent="test-agent", text="Hello!")

        assert "failed" in str(exc_info.value).lower()


# =============================================================================
# ACPClientError Tests
# =============================================================================


class TestACPClientError:
    """Tests for ACPClientError exception."""

    def test_error_message(self):
        """Verify error message is set correctly."""
        error = ACPClientError("Something went wrong")
        assert str(error) == "Something went wrong"

    def test_error_with_code(self):
        """Verify error code is set correctly."""
        error = ACPClientError("Not found", code="not_found")
        assert error.code == "not_found"

    def test_error_with_data(self):
        """Verify error data is set correctly."""
        error = ACPClientError(
            "Validation failed",
            code="validation_error",
            data={"field": "input", "reason": "required"},
        )
        assert error.data == {"field": "input", "reason": "required"}

    def test_error_without_optional_fields(self):
        """Verify error works without optional fields."""
        error = ACPClientError("Error")
        assert error.code is None
        assert error.data is None


# =============================================================================
# ACPClientService Tests
# =============================================================================


class TestACPClientServiceInitialization:
    """Tests for ACPClientService initialization."""

    def test_init_with_default_values(self):
        """Verify service initializes with default values from settings."""
        service = ACPClientService()
        assert service.base_url is not None
        assert service.timeout is not None
        assert service._client is None

    def test_init_with_custom_values(self):
        """Verify service initializes with custom values."""
        service = ACPClientService(
            base_url="http://custom-server:9000/",
            timeout=60,
        )
        assert service.base_url == "http://custom-server:9000"
        assert service.timeout == 60


class TestACPClientServiceContextManager:
    """Tests for ACPClientService async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_creates_and_closes_client(self):
        """Verify context manager lifecycle."""
        service = ACPClientService(base_url="http://localhost:8000")

        async with service as svc:
            assert svc._client is not None
            assert isinstance(svc._client, httpx.AsyncClient)

        assert service._client is None


class TestACPClientServicePing:
    """Tests for ACPClientService.ping method."""

    @pytest.mark.asyncio
    async def test_ping_success(self):
        """Verify ping returns True on successful response."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        service = ACPClientService(base_url="http://localhost:8000")
        service._client = mock_http_client

        result = await service.ping()

        assert result is True
        mock_http_client.get.assert_called_once_with("/ping")

    @pytest.mark.asyncio
    async def test_ping_failure(self):
        """Verify ping returns False on connection error."""
        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        service = ACPClientService(base_url="http://localhost:8000")
        service._client = mock_http_client

        result = await service.ping()

        assert result is False

    @pytest.mark.asyncio
    async def test_ping_non_200_status(self):
        """Verify ping returns False on non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 503

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        service = ACPClientService(base_url="http://localhost:8000")
        service._client = mock_http_client

        result = await service.ping()

        assert result is False


class TestACPClientServiceListAgents:
    """Tests for ACPClientService.list_agents method."""

    @pytest.mark.asyncio
    async def test_list_agents_list_format(self):
        """Verify list_agents handles list response format."""
        mock_response_data = [
            {"name": "agent1", "description": "First agent"},
            {"name": "agent2", "description": "Second agent"},
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        service = ACPClientService(base_url="http://localhost:8000")
        service._client = mock_http_client

        result = await service.list_agents()

        assert len(result) == 2
        assert result[0].name == "agent1"
        assert result[1].name == "agent2"

    @pytest.mark.asyncio
    async def test_list_agents_dict_format(self):
        """Verify list_agents handles dict response format."""
        mock_response_data = {
            "agent1": {"description": "First agent"},
            "agent2": "Simple description",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        service = ACPClientService(base_url="http://localhost:8000")
        service._client = mock_http_client

        result = await service.list_agents()

        assert len(result) == 2
        names = [a.name for a in result]
        assert "agent1" in names
        assert "agent2" in names

    @pytest.mark.asyncio
    async def test_list_agents_http_error(self):
        """Verify list_agents raises ACPClientError on HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=mock_response,
        )

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        # Use no_retry to avoid delays in tests
        service = ACPClientService(
            base_url="http://localhost:8000",
            retry_config=RetryConfig.no_retry(),
        )
        service._client = mock_http_client

        with pytest.raises(ServiceClientError) as exc_info:
            await service.list_agents()

        assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_agents_connection_error(self):
        """Verify list_agents raises ACPClientError on connection error."""
        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(
            side_effect=httpx.RequestError("Connection refused")
        )

        service = ACPClientService(base_url="http://localhost:8000")
        service._client = mock_http_client

        with pytest.raises(ServiceClientError) as exc_info:
            await service.list_agents()

        assert "connect" in str(exc_info.value).lower()


class TestACPClientServiceRunAgent:
    """Tests for ACPClientService.run_agent method."""

    @pytest.mark.asyncio
    async def test_run_agent_success(self):
        """Verify run_agent returns RunResult on success."""
        mock_response_data = {
            "status": "completed",
            "run_id": "run-123",
            "output": [
                {
                    "parts": [
                        {"content": "Hello back!"}
                    ]
                }
            ],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        service = ACPClientService(base_url="http://localhost:8000")
        service._client = mock_http_client

        result = await service.run_agent(
            agent_name="test-agent",
            message="Hello!",
        )

        assert result.status == "completed"
        assert result.output == "Hello back!"
        assert result.run_id == "run-123"

        # Verify correct endpoint
        call_args = mock_http_client.post.call_args
        assert "/agents/test-agent/runs" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_run_agent_with_session_id(self):
        """Verify run_agent passes session_id in payload."""
        mock_response_data = {
            "status": "completed",
            "output": "Response",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        service = ACPClientService(base_url="http://localhost:8000")
        service._client = mock_http_client

        await service.run_agent(
            agent_name="test-agent",
            message="Hello!",
            session_id="session-123",
        )

        call_args = mock_http_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["session_id"] == "session-123"

    @pytest.mark.asyncio
    async def test_run_agent_not_found(self):
        """Verify run_agent raises ACPClientError when agent not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response,
        )

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        service = ACPClientService(base_url="http://localhost:8000")
        service._client = mock_http_client

        with pytest.raises(ServiceClientError) as exc_info:
            await service.run_agent(
                agent_name="nonexistent",
                message="Hello!",
            )

        assert "not found" in str(exc_info.value).lower()


class TestACPClientServiceExtractOutput:
    """Tests for ACPClientService._extract_output helper method."""

    def test_extract_output_string(self):
        """Verify _extract_output handles string output."""
        service = ACPClientService(base_url="http://localhost:8000")

        result = service._extract_output({"output": "Direct string output"})

        assert result == "Direct string output"

    def test_extract_output_message_list(self):
        """Verify _extract_output handles message list output."""
        service = ACPClientService(base_url="http://localhost:8000")

        response_data = {
            "output": [
                {
                    "parts": [
                        {"content": "First part"},
                        {"content": "Second part"},
                    ]
                },
                {
                    "parts": [{"content": "Third part"}]
                },
            ]
        }

        result = service._extract_output(response_data)

        assert "First part" in result
        assert "Second part" in result
        assert "Third part" in result

    def test_extract_output_result_field(self):
        """Verify _extract_output handles result field."""
        service = ACPClientService(base_url="http://localhost:8000")

        result = service._extract_output({"result": "Result value"})

        assert result == "Result value"

    def test_extract_output_message_field(self):
        """Verify _extract_output handles message field."""
        service = ACPClientService(base_url="http://localhost:8000")

        result = service._extract_output({"message": "Message value"})

        assert result == "Message value"

    def test_extract_output_fallback(self):
        """Verify _extract_output returns fallback for empty response."""
        service = ACPClientService(base_url="http://localhost:8000")

        result = service._extract_output({})

        assert "completed" in result.lower() or "no" in result.lower()


class TestACPClientServiceGetClient:
    """Tests for ACPClientService._get_client method."""

    @pytest.mark.asyncio
    async def test_get_client_creates_if_none(self):
        """Verify _get_client creates client if none exists."""
        service = ACPClientService(base_url="http://localhost:8000")

        assert service._client is None

        client = service._get_client()

        assert client is not None
        assert isinstance(client, httpx.AsyncClient)

        # Cleanup
        await service.close()

    @pytest.mark.asyncio
    async def test_get_client_returns_existing(self):
        """Verify _get_client returns existing client."""
        service = ACPClientService(base_url="http://localhost:8000")

        first_client = service._get_client()
        second_client = service._get_client()

        assert first_client is second_client

        # Cleanup
        await service.close()


class TestACPClientServiceClose:
    """Tests for ACPClientService.close method."""

    @pytest.mark.asyncio
    async def test_close_cleans_up_client(self):
        """Verify close cleans up the client."""
        service = ACPClientService(base_url="http://localhost:8000")

        _ = service._get_client()  # Create client
        assert service._client is not None

        await service.close()

        assert service._client is None

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        """Verify multiple close calls are safe."""
        service = ACPClientService(base_url="http://localhost:8000")

        await service.close()  # No client yet
        await service.close()  # Should not raise

        assert service._client is None


# =============================================================================
# Integration-Style Tests (with full mock chain)
# =============================================================================


class TestACPClientIntegration:
    """Integration-style tests for ACPClient with complete mock chains."""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """Test complete conversation flow: create run -> wait -> get result."""
        # First call: create run (async)
        create_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "in-progress",
            "output": [],
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
        }

        # Second call: poll (still in progress)
        poll_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "in-progress",
            "output": [],
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
        }

        # Third call: poll (completed)
        completed_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "completed",
            "output": [
                {
                    "role": "agent",
                    "parts": [{"content": "Final response!", "content_type": "text/plain"}],
                }
            ],
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
            "completed_at": FIXTURE_TIMESTAMP_LATER.isoformat(),
        }

        call_count = 0

        def mock_post(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.json.return_value = create_response_data
            mock_response.raise_for_status = MagicMock()
            return mock_response

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            if call_count < 2:
                mock_response.json.return_value = poll_response_data
            else:
                mock_response.json.return_value = completed_response_data
            return mock_response

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(side_effect=mock_post)
        mock_http_client.get = AsyncMock(side_effect=mock_get)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        # Step 1: Create async run
        run_id = await client.run_async(
            agent="test-agent",
            input=[Message.user_text("Hello!")],
        )
        assert run_id == FIXTURE_RUN_ID

        # Step 2: Wait for completion
        result = await client.wait_for_run(run_id, poll_interval=0.01)

        assert result.status == RunStatus.COMPLETED
        assert len(result.output) == 1

    @pytest.mark.asyncio
    async def test_await_resume_flow(self):
        """Test await/resume flow: run -> await -> resume -> complete."""
        # First call: run (returns awaiting)
        awaiting_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "awaiting",
            "output": [],
            "await_request": {
                "type": "user_confirmation",
                "description": "Please confirm",
            },
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
        }

        # Second call: resume (returns completed)
        completed_response_data = {
            "run_id": str(FIXTURE_RUN_ID),
            "agent_name": "test-agent",
            "status": "completed",
            "output": [
                {
                    "role": "agent",
                    "parts": [{"content": "Action completed!", "content_type": "text/plain"}],
                }
            ],
            "created_at": FIXTURE_TIMESTAMP.isoformat(),
            "completed_at": FIXTURE_TIMESTAMP_LATER.isoformat(),
        }

        call_count = 0

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            if call_count == 1:
                mock_response.json.return_value = awaiting_response_data
            else:
                mock_response.json.return_value = completed_response_data
            return mock_response

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(side_effect=mock_post)

        client = ACPClient(base_url="http://localhost:8000")
        client._client = mock_http_client

        # Step 1: Run and get awaiting status
        result = await client.run_sync(
            agent="test-agent",
            input=[Message.user_text("Do something")],
        )
        assert result.status == RunStatus.AWAITING
        assert result.await_request is not None

        # Step 2: Resume with confirmation
        final_result = await client.resume_run(
            run_id=FIXTURE_RUN_ID,
            input=[Message.user_text("Yes, confirmed")],
        )

        assert final_result.status == RunStatus.COMPLETED
        assert len(final_result.output) == 1
