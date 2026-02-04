"""
ACP Mock Server Fixtures using respx

Provides comprehensive fixtures for mocking ACP server HTTP responses using respx.
These fixtures enable testing of ACP client code without needing a real server.

Usage:
    Import fixtures in your test file or conftest.py:

        pytest_plugins = ["tests.fixtures.acp_server_fixtures"]

    Then use fixtures in your tests:

        @pytest.mark.anyio
        async def test_list_agents(mock_acp_server):
            async with ACPClient(base_url="http://localhost:8000") as client:
                agents = await client.list_agents()
                assert len(agents.agents) == 3

    Or use specific endpoint fixtures:

        @pytest.mark.anyio
        async def test_run_agent(mock_acp_run_sync):
            async with ACPClient(base_url="http://localhost:8000") as client:
                result = await client.run_sync(...)

    Or import factory functions directly:

        from tests.fixtures.acp_server_fixtures import (
            create_mock_acp_server,
            mock_agent_list_response,
            mock_run_response,
        )
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable
from uuid import UUID, uuid4

import httpx
import pytest
import respx

# Import types and models (lazy import pattern)
from tests.fixtures.acp_fixtures import (
    FIXTURE_RUN_ID,
    FIXTURE_SESSION_ID,
    FIXTURE_TIMESTAMP,
    FIXTURE_TIMESTAMP_LATER,
)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_BASE_URL = "http://localhost:8000"

# Sample agent data for mocking
SAMPLE_AGENTS_DATA = [
    {
        "name": "test-assistant",
        "description": "A helpful test assistant for unit testing",
        "input_content_types": ["text/plain", "application/json"],
        "output_content_types": ["text/plain", "application/json"],
        "status": "active",
        "metadata": {
            "version": "1.0.0",
            "capabilities": ["text-generation", "summarization"],
        },
    },
    {
        "name": "echo-agent",
        "description": "An agent that echoes back messages",
        "input_content_types": ["text/plain"],
        "output_content_types": ["text/plain"],
        "status": "active",
        "metadata": {"version": "1.0.0"},
    },
    {
        "name": "math-agent",
        "description": "An agent for mathematical calculations",
        "input_content_types": ["text/plain", "application/json"],
        "output_content_types": ["text/plain", "application/json"],
        "status": "active",
        "metadata": {
            "version": "2.1.0",
            "capabilities": ["arithmetic", "algebra"],
        },
    },
]


# =============================================================================
# Helper Functions for Creating Response Data
# =============================================================================

def create_agent_list_response(
    agents: list[dict[str, Any]] | None = None,
    total: int | None = None,
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Create a mock AgentListResponse.

    Args:
        agents: List of agent dictionaries. Defaults to SAMPLE_AGENTS_DATA.
        total: Total count. Defaults to len(agents).
        offset: Pagination offset.
        limit: Pagination limit.

    Returns:
        Dictionary matching AgentListResponse schema.
    """
    if agents is None:
        agents = SAMPLE_AGENTS_DATA
    if total is None:
        total = len(agents)

    return {
        "agents": agents,
        "total": total,
        "offset": offset,
        "limit": limit,
    }


def create_agent_response(
    name: str = "test-assistant",
    description: str = "A helpful test assistant",
    status: str = "active",
    input_content_types: list[str] | None = None,
    output_content_types: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a mock AgentResponse.

    Args:
        name: Agent name.
        description: Agent description.
        status: Agent status.
        input_content_types: Supported input content types.
        output_content_types: Supported output content types.
        metadata: Agent metadata.

    Returns:
        Dictionary matching AgentResponse schema.
    """
    return {
        "agent": {
            "name": name,
            "description": description,
            "status": status,
            "input_content_types": input_content_types or ["text/plain"],
            "output_content_types": output_content_types or ["text/plain"],
            "metadata": metadata or {},
        }
    }


def create_run_response(
    run_id: UUID | str | None = None,
    agent_name: str = "test-assistant",
    session_id: UUID | str | None = None,
    status: str = "completed",
    output_text: str = "This is the agent's response.",
    error: dict[str, Any] | None = None,
    await_request: dict[str, Any] | None = None,
    created_at: datetime | str | None = None,
    completed_at: datetime | str | None = None,
) -> dict[str, Any]:
    """
    Create a mock RunResponse.

    Args:
        run_id: Run ID. Defaults to FIXTURE_RUN_ID.
        agent_name: Agent name.
        session_id: Session ID.
        status: Run status.
        output_text: Text content for the output message.
        error: Error details if status is 'failed'.
        await_request: Await request if status is 'awaiting'.
        created_at: Creation timestamp.
        completed_at: Completion timestamp.

    Returns:
        Dictionary matching RunResponse schema.
    """
    if run_id is None:
        run_id = FIXTURE_RUN_ID
    if created_at is None:
        created_at = FIXTURE_TIMESTAMP
    if completed_at is None and status == "completed":
        completed_at = FIXTURE_TIMESTAMP_LATER

    # Convert UUIDs and datetimes to strings for JSON serialization
    run_id_str = str(run_id) if isinstance(run_id, UUID) else run_id
    session_id_str = str(session_id) if isinstance(session_id, UUID) else session_id
    created_at_str = created_at.isoformat() if isinstance(created_at, datetime) else created_at
    completed_at_str = completed_at.isoformat() if isinstance(completed_at, datetime) else completed_at

    response = {
        "run_id": run_id_str,
        "agent_name": agent_name,
        "session_id": session_id_str,
        "status": status,
        "output": [
            {
                "role": "agent",
                "parts": [
                    {
                        "content": output_text,
                        "content_type": "text/plain",
                        "content_encoding": "plain",
                    }
                ],
                "created_at": created_at_str,
            }
        ] if status == "completed" else [],
        "error": error,
        "await_request": await_request,
        "created_at": created_at_str,
        "completed_at": completed_at_str,
    }

    return response


def create_session_response(
    session_id: UUID | str | None = None,
    agent_name: str = "test-assistant",
    messages: list[dict[str, Any]] | None = None,
    run_count: int = 1,
    created_at: datetime | str | None = None,
    last_activity_at: datetime | str | None = None,
) -> dict[str, Any]:
    """
    Create a mock SessionResponse.

    Args:
        session_id: Session ID. Defaults to FIXTURE_SESSION_ID.
        agent_name: Primary agent name.
        messages: Conversation history.
        run_count: Number of runs in session.
        created_at: Creation timestamp.
        last_activity_at: Last activity timestamp.

    Returns:
        Dictionary matching SessionResponse schema.
    """
    if session_id is None:
        session_id = FIXTURE_SESSION_ID
    if created_at is None:
        created_at = FIXTURE_TIMESTAMP
    if last_activity_at is None:
        last_activity_at = FIXTURE_TIMESTAMP_LATER

    session_id_str = str(session_id) if isinstance(session_id, UUID) else session_id
    created_at_str = created_at.isoformat() if isinstance(created_at, datetime) else created_at
    last_activity_at_str = last_activity_at.isoformat() if isinstance(last_activity_at, datetime) else last_activity_at

    return {
        "session_id": session_id_str,
        "agent_name": agent_name,
        "messages": messages or [],
        "run_count": run_count,
        "created_at": created_at_str,
        "last_activity_at": last_activity_at_str,
    }


def create_error_response(
    code: str = "agent_error",
    message: str = "An error occurred",
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a mock ErrorResponse.

    Args:
        code: Error code.
        message: Error message.
        data: Additional error data.

    Returns:
        Dictionary matching ErrorResponse schema.
    """
    return {
        "code": code,
        "message": message,
        "data": data,
    }


def create_health_response(
    status: str = "healthy",
    version: str = "1.0.0",
    agent_count: int = 3,
    uptime_seconds: float = 3600.0,
) -> dict[str, Any]:
    """
    Create a mock HealthResponse.

    Args:
        status: Health status.
        version: Server version.
        agent_count: Number of registered agents.
        uptime_seconds: Server uptime.

    Returns:
        Dictionary matching HealthResponse schema.
    """
    return {
        "status": status,
        "version": version,
        "agent_count": agent_count,
        "uptime_seconds": uptime_seconds,
    }


# =============================================================================
# Mock Server Configuration Class
# =============================================================================

class MockACPServerConfig:
    """
    Configuration for mock ACP server behavior.

    Use this to customize how the mock server responds to requests.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        agents: list[dict[str, Any]] | None = None,
        default_run_status: str = "completed",
        default_output_text: str = "This is the agent's response.",
        simulate_errors: bool = False,
        error_code: str = "agent_error",
        error_message: str = "Simulated error",
        latency_ms: int = 0,
    ):
        """
        Initialize mock server configuration.

        Args:
            base_url: Base URL for the mock server.
            agents: List of agents to return. Defaults to SAMPLE_AGENTS_DATA.
            default_run_status: Default status for run responses.
            default_output_text: Default output text for completed runs.
            simulate_errors: Whether to simulate error responses.
            error_code: Error code for simulated errors.
            error_message: Error message for simulated errors.
            latency_ms: Simulated latency in milliseconds (not implemented).
        """
        self.base_url = base_url
        self.agents = agents if agents is not None else SAMPLE_AGENTS_DATA.copy()
        self.default_run_status = default_run_status
        self.default_output_text = default_output_text
        self.simulate_errors = simulate_errors
        self.error_code = error_code
        self.error_message = error_message
        self.latency_ms = latency_ms

        # Track requests for assertions
        self.request_history: list[httpx.Request] = []

    def reset(self):
        """Reset request history."""
        self.request_history.clear()

    def get_agent_by_name(self, name: str) -> dict[str, Any] | None:
        """Get an agent by name."""
        for agent in self.agents:
            if agent["name"] == name:
                return agent
        return None


# =============================================================================
# Mock Server Setup Functions
# =============================================================================

def setup_mock_acp_endpoints(
    mock: respx.MockRouter,
    config: MockACPServerConfig | None = None,
) -> MockACPServerConfig:
    """
    Set up all mock ACP endpoints on a respx MockRouter.

    Args:
        mock: The respx MockRouter to configure.
        config: Optional configuration. Creates default if not provided.

    Returns:
        The MockACPServerConfig used for setup.
    """
    if config is None:
        config = MockACPServerConfig()

    base_url = config.base_url

    # Helper to track requests
    def track_request(request: httpx.Request) -> None:
        config.request_history.append(request)

    # --- Health/Ping Endpoints ---

    @mock.get(f"{base_url}/ping")
    def mock_ping(request: httpx.Request) -> httpx.Response:
        track_request(request)
        if config.simulate_errors:
            return httpx.Response(503, json=create_error_response(
                code="service_unavailable",
                message="Service temporarily unavailable",
            ))
        return httpx.Response(200, json={"status": "ok"})

    @mock.get(f"{base_url}/health")
    def mock_health(request: httpx.Request) -> httpx.Response:
        track_request(request)
        if config.simulate_errors:
            return httpx.Response(503, json=create_error_response(
                code="service_unavailable",
                message="Service temporarily unavailable",
            ))
        return httpx.Response(200, json=create_health_response(
            agent_count=len(config.agents),
        ))

    # --- Agent Endpoints ---

    @mock.get(f"{base_url}/agents")
    def mock_list_agents(request: httpx.Request) -> httpx.Response:
        track_request(request)
        if config.simulate_errors:
            return httpx.Response(500, json=create_error_response(
                code=config.error_code,
                message=config.error_message,
            ))
        return httpx.Response(200, json=create_agent_list_response(
            agents=config.agents,
        ))

    @mock.get(url__regex=rf"{base_url}/agents/(?P<name>[^/]+)$")
    def mock_get_agent(request: httpx.Request, name: str) -> httpx.Response:
        track_request(request)
        if config.simulate_errors:
            return httpx.Response(500, json=create_error_response(
                code=config.error_code,
                message=config.error_message,
            ))

        agent = config.get_agent_by_name(name)
        if agent is None:
            return httpx.Response(404, json=create_error_response(
                code="not_found",
                message=f"Agent '{name}' not found",
            ))

        return httpx.Response(200, json={"agent": agent})

    # --- Run Endpoints ---

    @mock.post(f"{base_url}/runs")
    def mock_create_run(request: httpx.Request) -> httpx.Response:
        track_request(request)

        if config.simulate_errors:
            return httpx.Response(500, json=create_error_response(
                code=config.error_code,
                message=config.error_message,
            ))

        # Parse request body
        body = json.loads(request.content)
        agent_name = body.get("agent", "unknown")

        # Check if agent exists
        agent = config.get_agent_by_name(agent_name)
        if agent is None:
            return httpx.Response(404, json=create_error_response(
                code="not_found",
                message=f"Agent '{agent_name}' not found",
            ))

        # Generate run response
        run_id = uuid4()
        session_id = body.get("session_id")

        return httpx.Response(200, json=create_run_response(
            run_id=run_id,
            agent_name=agent_name,
            session_id=session_id,
            status=config.default_run_status,
            output_text=config.default_output_text,
        ))

    @mock.get(url__regex=rf"{base_url}/runs/(?P<run_id>[^/]+)$")
    def mock_get_run(request: httpx.Request, run_id: str) -> httpx.Response:
        track_request(request)

        if config.simulate_errors:
            return httpx.Response(500, json=create_error_response(
                code=config.error_code,
                message=config.error_message,
            ))

        return httpx.Response(200, json=create_run_response(
            run_id=run_id,
            status=config.default_run_status,
            output_text=config.default_output_text,
        ))

    @mock.post(url__regex=rf"{base_url}/runs/(?P<run_id>[^/]+)$")
    def mock_resume_run(request: httpx.Request, run_id: str) -> httpx.Response:
        track_request(request)

        if config.simulate_errors:
            return httpx.Response(500, json=create_error_response(
                code=config.error_code,
                message=config.error_message,
            ))

        return httpx.Response(200, json=create_run_response(
            run_id=run_id,
            status="completed",
            output_text="Run resumed successfully.",
        ))

    @mock.post(url__regex=rf"{base_url}/runs/(?P<run_id>[^/]+)/cancel$")
    def mock_cancel_run(request: httpx.Request, run_id: str) -> httpx.Response:
        track_request(request)

        if config.simulate_errors:
            return httpx.Response(500, json=create_error_response(
                code=config.error_code,
                message=config.error_message,
            ))

        return httpx.Response(200, json=create_run_response(
            run_id=run_id,
            status="cancelled",
            output_text="",
        ))

    # --- Legacy Endpoint (for ACPClientService compatibility) ---

    @mock.post(url__regex=rf"{base_url}/agents/(?P<agent_name>[^/]+)/runs$")
    def mock_legacy_create_run(request: httpx.Request, agent_name: str) -> httpx.Response:
        track_request(request)

        if config.simulate_errors:
            return httpx.Response(500, json=create_error_response(
                code=config.error_code,
                message=config.error_message,
            ))

        agent = config.get_agent_by_name(agent_name)
        if agent is None:
            return httpx.Response(404, json=create_error_response(
                code="not_found",
                message=f"Agent '{agent_name}' not found",
            ))

        body = json.loads(request.content)
        session_id = body.get("session_id")
        run_id = uuid4()

        return httpx.Response(200, json=create_run_response(
            run_id=run_id,
            agent_name=agent_name,
            session_id=session_id,
            status=config.default_run_status,
            output_text=config.default_output_text,
        ))

    # --- Session Endpoints ---

    @mock.get(url__regex=rf"{base_url}/sessions/(?P<session_id>[^/]+)$")
    def mock_get_session(request: httpx.Request, session_id: str) -> httpx.Response:
        track_request(request)

        if config.simulate_errors:
            return httpx.Response(500, json=create_error_response(
                code=config.error_code,
                message=config.error_message,
            ))

        return httpx.Response(200, json=create_session_response(
            session_id=session_id,
        ))

    return config


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture
def mock_acp_server_config() -> MockACPServerConfig:
    """
    Create a default MockACPServerConfig.

    Can be overridden in tests to customize behavior.
    """
    return MockACPServerConfig()


@pytest.fixture
def mock_acp_server(mock_acp_server_config: MockACPServerConfig):
    """
    Create a mock ACP server using respx.

    This fixture sets up mocked responses for all ACP endpoints.
    Use this for comprehensive integration testing.

    Example:
        @pytest.mark.anyio
        async def test_list_agents(mock_acp_server):
            config, mock = mock_acp_server
            async with ACPClient(base_url=config.base_url) as client:
                agents = await client.list_agents()
                assert len(agents.agents) == 3

            # Check request history
            assert len(config.request_history) == 1
    """
    with respx.mock(assert_all_called=False) as mock:
        setup_mock_acp_endpoints(mock, mock_acp_server_config)
        yield mock_acp_server_config, mock


@pytest.fixture
def mock_acp_server_error():
    """
    Create a mock ACP server that simulates errors.

    Example:
        @pytest.mark.anyio
        async def test_handle_server_error(mock_acp_server_error):
            config, mock = mock_acp_server_error
            async with ACPClient(base_url=config.base_url) as client:
                with pytest.raises(httpx.HTTPStatusError):
                    await client.list_agents()
    """
    config = MockACPServerConfig(simulate_errors=True)
    with respx.mock(assert_all_called=False) as mock:
        setup_mock_acp_endpoints(mock, config)
        yield config, mock


@pytest.fixture
def mock_acp_agents_endpoint():
    """
    Create a mock for just the /agents endpoint.

    Use for focused testing of agent discovery.
    """
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{DEFAULT_BASE_URL}/agents").respond(
            200,
            json=create_agent_list_response(),
        )
        yield mock


@pytest.fixture
def mock_acp_run_sync():
    """
    Create a mock for synchronous run creation.

    Example:
        @pytest.mark.anyio
        async def test_run_sync(mock_acp_run_sync):
            async with ACPClient(base_url="http://localhost:8000") as client:
                result = await client.run_sync(
                    agent="test-assistant",
                    input=[Message.user_text("Hello")],
                )
                assert result.status == RunStatus.COMPLETED
    """
    with respx.mock(assert_all_called=False) as mock:
        mock.post(f"{DEFAULT_BASE_URL}/runs").respond(
            200,
            json=create_run_response(),
        )
        yield mock


@pytest.fixture
def mock_acp_run_async():
    """
    Create a mock for async run creation and polling.

    Sets up mocks for POST /runs and GET /runs/{run_id}.
    """
    run_id = str(uuid4())

    with respx.mock(assert_all_called=False) as mock:
        # Initial creation returns in_progress
        mock.post(f"{DEFAULT_BASE_URL}/runs").respond(
            200,
            json=create_run_response(run_id=run_id, status="in_progress", output_text=""),
        )

        # Polling returns completed
        mock.get(url__regex=rf"{DEFAULT_BASE_URL}/runs/.*").respond(
            200,
            json=create_run_response(run_id=run_id, status="completed"),
        )

        yield mock, run_id


@pytest.fixture
def mock_acp_run_awaiting():
    """
    Create a mock for runs that go into awaiting state.

    Useful for testing await/resume workflows.
    """
    run_id = str(FIXTURE_RUN_ID)

    await_request = {
        "type": "user_confirmation",
        "description": "Please confirm you want to proceed.",
        "schema_": {
            "type": "object",
            "properties": {"confirmed": {"type": "boolean"}},
            "required": ["confirmed"],
        },
        "timeout_seconds": 300,
    }

    with respx.mock(assert_all_called=False) as mock:
        # Initial creation returns awaiting
        mock.post(f"{DEFAULT_BASE_URL}/runs").respond(
            200,
            json=create_run_response(
                run_id=run_id,
                status="awaiting",
                output_text="",
                await_request=await_request,
            ),
        )

        # Resume returns completed
        mock.post(url__regex=rf"{DEFAULT_BASE_URL}/runs/{run_id}$").respond(
            200,
            json=create_run_response(
                run_id=run_id,
                status="completed",
                output_text="Action confirmed and completed.",
            ),
        )

        yield mock, run_id


@pytest.fixture
def mock_acp_agent_not_found():
    """
    Create a mock that returns 404 for agent requests.

    Useful for testing error handling.
    """
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url__regex=rf"{DEFAULT_BASE_URL}/agents/.*").respond(
            404,
            json=create_error_response(
                code="not_found",
                message="Agent not found",
            ),
        )
        mock.post(f"{DEFAULT_BASE_URL}/runs").respond(
            404,
            json=create_error_response(
                code="not_found",
                message="Agent not found",
            ),
        )
        mock.post(url__regex=rf"{DEFAULT_BASE_URL}/agents/.*/runs").respond(
            404,
            json=create_error_response(
                code="not_found",
                message="Agent not found",
            ),
        )
        yield mock


@pytest.fixture
def mock_acp_run_failed():
    """
    Create a mock that returns a failed run.

    Useful for testing error handling in run responses.
    """
    error = {
        "code": "agent_error",
        "message": "Agent failed to process the request",
        "data": {"details": "Internal processing error"},
    }

    with respx.mock(assert_all_called=False) as mock:
        mock.post(f"{DEFAULT_BASE_URL}/runs").respond(
            200,  # Note: Run creation succeeds, but run status is failed
            json=create_run_response(
                status="failed",
                output_text="",
                error=error,
            ),
        )
        yield mock


@pytest.fixture
def mock_acp_client_service():
    """
    Create a mock specifically for the ACPClientService (legacy client).

    This mock handles the /agents and /agents/{name}/runs endpoints
    used by the simpler ACPClientService class.
    """
    with respx.mock(assert_all_called=False) as mock:
        # Mock /ping
        mock.get(f"{DEFAULT_BASE_URL}/ping").respond(200, json={"status": "ok"})

        # Mock /agents - return list format for ACPClientService
        mock.get(f"{DEFAULT_BASE_URL}/agents").respond(
            200,
            json=SAMPLE_AGENTS_DATA,  # Returns list directly
        )

        # Mock /agents/{name}/runs
        def handle_agent_run(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            return httpx.Response(200, json={
                "status": "completed",
                "run_id": str(uuid4()),
                "output": [
                    {
                        "role": "agent",
                        "parts": [{"content": "Response from agent", "content_type": "text/plain"}],
                    }
                ],
            })

        mock.post(url__regex=rf"{DEFAULT_BASE_URL}/agents/[^/]+/runs").mock(
            side_effect=handle_agent_run
        )

        yield mock


@pytest.fixture
def mock_acp_ping_success():
    """Create a mock for successful ping endpoint."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{DEFAULT_BASE_URL}/ping").respond(200, json={"status": "ok"})
        yield mock


@pytest.fixture
def mock_acp_ping_failure():
    """Create a mock for failed ping endpoint."""
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{DEFAULT_BASE_URL}/ping").respond(503)
        yield mock


# =============================================================================
# Custom Mock Factory Function
# =============================================================================

def create_custom_mock_acp_server(
    agents: list[dict[str, Any]] | None = None,
    default_run_status: str = "completed",
    default_output_text: str = "Custom response",
    simulate_errors: bool = False,
    base_url: str = DEFAULT_BASE_URL,
) -> tuple[MockACPServerConfig, respx.MockRouter]:
    """
    Factory function to create a custom mock ACP server.

    Use this when you need more control than the fixtures provide.

    Example:
        with create_custom_mock_acp_server(
            agents=[{"name": "custom", "description": "Custom agent"}],
            default_output_text="Custom output",
        ) as (config, mock):
            async with ACPClient(base_url=config.base_url) as client:
                result = await client.run_text("custom", "Hello")
                assert result == "Custom output"

    Args:
        agents: Custom agents list.
        default_run_status: Default run status.
        default_output_text: Default output text.
        simulate_errors: Whether to simulate errors.
        base_url: Base URL.

    Returns:
        Tuple of (config, mock_router).
    """
    config = MockACPServerConfig(
        base_url=base_url,
        agents=agents,
        default_run_status=default_run_status,
        default_output_text=default_output_text,
        simulate_errors=simulate_errors,
    )

    mock = respx.mock(assert_all_called=False)
    mock.start()
    setup_mock_acp_endpoints(mock, config)

    return config, mock


class CustomMockACPServer:
    """
    Context manager for creating custom mock ACP servers.

    Example:
        async def test_custom():
            with CustomMockACPServer(
                default_output_text="Custom response"
            ) as (config, mock):
                async with ACPClient(base_url=config.base_url) as client:
                    result = await client.run_text("test-assistant", "Hello")
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.config: MockACPServerConfig | None = None
        self.mock: respx.MockRouter | None = None

    def __enter__(self) -> tuple[MockACPServerConfig, respx.MockRouter]:
        self.config = MockACPServerConfig(**self.kwargs)
        self.mock = respx.mock(assert_all_called=False)
        self.mock.start()
        setup_mock_acp_endpoints(self.mock, self.config)
        return self.config, self.mock

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.mock:
            self.mock.stop()


# =============================================================================
# Streaming Mock Support
# =============================================================================

def create_sse_response(events: list[dict[str, Any]]) -> str:
    """
    Create a Server-Sent Events response body.

    Args:
        events: List of event data dictionaries.

    Returns:
        SSE-formatted string.
    """
    lines = []
    for event in events:
        lines.append(f"data: {json.dumps(event)}")
        lines.append("")  # Empty line between events
    return "\n".join(lines)


@pytest.fixture
def mock_acp_run_stream():
    """
    Create a mock for streaming run responses.

    Note: This provides basic streaming support. For full streaming
    tests, you may need to use httpx's MockTransport directly.
    """
    stream_events = [
        {"role": "agent", "parts": [{"content": "Hello", "content_type": "text/plain"}]},
        {"role": "agent", "parts": [{"content": " world", "content_type": "text/plain"}]},
        {"event": "done"},
    ]

    with respx.mock(assert_all_called=False) as mock:
        mock.post(f"{DEFAULT_BASE_URL}/runs").respond(
            200,
            content=create_sse_response(stream_events),
            headers={"Content-Type": "text/event-stream"},
        )
        yield mock, stream_events
