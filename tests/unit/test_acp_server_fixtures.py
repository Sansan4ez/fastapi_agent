"""
Unit tests to verify ACP server mock fixtures work correctly.

These tests ensure all mock fixtures are functional and produce valid responses.
"""

from __future__ import annotations

import json
from uuid import UUID

import httpx
import pytest
import respx

# Register the fixture plugins
pytest_plugins = [
    "tests.fixtures.acp_fixtures",
    "tests.fixtures.acp_server_fixtures",
]


# =============================================================================
# Test Helper Functions
# =============================================================================

class TestResponseCreators:
    """Test response creator functions."""

    def test_create_agent_list_response_default(self):
        """Test create_agent_list_response with defaults."""
        from tests.fixtures.acp_server_fixtures import create_agent_list_response

        response = create_agent_list_response()

        assert "agents" in response
        assert "total" in response
        assert "offset" in response
        assert "limit" in response
        assert len(response["agents"]) == 3  # Default sample agents
        assert response["total"] == 3

    def test_create_agent_list_response_custom(self):
        """Test create_agent_list_response with custom agents."""
        from tests.fixtures.acp_server_fixtures import create_agent_list_response

        custom_agents = [
            {"name": "custom-agent", "description": "A custom agent"},
        ]

        response = create_agent_list_response(
            agents=custom_agents,
            offset=10,
            limit=50,
        )

        assert len(response["agents"]) == 1
        assert response["total"] == 1
        assert response["offset"] == 10
        assert response["limit"] == 50

    def test_create_agent_response(self):
        """Test create_agent_response."""
        from tests.fixtures.acp_server_fixtures import create_agent_response

        response = create_agent_response(
            name="test-agent",
            description="Test description",
            status="active",
        )

        assert "agent" in response
        assert response["agent"]["name"] == "test-agent"
        assert response["agent"]["description"] == "Test description"
        assert response["agent"]["status"] == "active"

    def test_create_run_response_completed(self):
        """Test create_run_response for completed run."""
        from tests.fixtures.acp_server_fixtures import create_run_response, FIXTURE_RUN_ID

        response = create_run_response(
            status="completed",
            output_text="Test output",
        )

        assert response["status"] == "completed"
        assert response["run_id"] == str(FIXTURE_RUN_ID)
        assert len(response["output"]) == 1
        assert response["output"][0]["parts"][0]["content"] == "Test output"
        assert response["completed_at"] is not None

    def test_create_run_response_in_progress(self):
        """Test create_run_response for in-progress run."""
        from tests.fixtures.acp_server_fixtures import create_run_response

        response = create_run_response(
            status="in_progress",
            output_text="",
        )

        assert response["status"] == "in_progress"
        assert len(response["output"]) == 0

    def test_create_run_response_with_error(self):
        """Test create_run_response with error."""
        from tests.fixtures.acp_server_fixtures import create_run_response

        error = {
            "code": "agent_error",
            "message": "Something went wrong",
        }

        response = create_run_response(
            status="failed",
            error=error,
        )

        assert response["status"] == "failed"
        assert response["error"] == error

    def test_create_session_response(self):
        """Test create_session_response."""
        from tests.fixtures.acp_server_fixtures import create_session_response, FIXTURE_SESSION_ID

        response = create_session_response(
            agent_name="test-agent",
            run_count=5,
        )

        assert response["session_id"] == str(FIXTURE_SESSION_ID)
        assert response["agent_name"] == "test-agent"
        assert response["run_count"] == 5

    def test_create_error_response(self):
        """Test create_error_response."""
        from tests.fixtures.acp_server_fixtures import create_error_response

        response = create_error_response(
            code="validation_error",
            message="Invalid input",
            data={"field": "name"},
        )

        assert response["code"] == "validation_error"
        assert response["message"] == "Invalid input"
        assert response["data"]["field"] == "name"

    def test_create_health_response(self):
        """Test create_health_response."""
        from tests.fixtures.acp_server_fixtures import create_health_response

        response = create_health_response(
            status="healthy",
            version="2.0.0",
            agent_count=10,
            uptime_seconds=7200.0,
        )

        assert response["status"] == "healthy"
        assert response["version"] == "2.0.0"
        assert response["agent_count"] == 10
        assert response["uptime_seconds"] == 7200.0


# =============================================================================
# Test Mock Server Configuration
# =============================================================================

class TestMockACPServerConfig:
    """Test MockACPServerConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        from tests.fixtures.acp_server_fixtures import MockACPServerConfig, DEFAULT_BASE_URL

        config = MockACPServerConfig()

        assert config.base_url == DEFAULT_BASE_URL
        assert len(config.agents) == 3
        assert config.default_run_status == "completed"
        assert config.simulate_errors is False

    def test_custom_config(self):
        """Test custom configuration values."""
        from tests.fixtures.acp_server_fixtures import MockACPServerConfig

        custom_agents = [{"name": "custom", "description": "Custom agent"}]

        config = MockACPServerConfig(
            base_url="http://custom:9000",
            agents=custom_agents,
            default_run_status="in_progress",
            simulate_errors=True,
            error_code="custom_error",
        )

        assert config.base_url == "http://custom:9000"
        assert len(config.agents) == 1
        assert config.default_run_status == "in_progress"
        assert config.simulate_errors is True
        assert config.error_code == "custom_error"

    def test_get_agent_by_name_found(self):
        """Test get_agent_by_name when agent exists."""
        from tests.fixtures.acp_server_fixtures import MockACPServerConfig

        config = MockACPServerConfig()
        agent = config.get_agent_by_name("test-assistant")

        assert agent is not None
        assert agent["name"] == "test-assistant"

    def test_get_agent_by_name_not_found(self):
        """Test get_agent_by_name when agent doesn't exist."""
        from tests.fixtures.acp_server_fixtures import MockACPServerConfig

        config = MockACPServerConfig()
        agent = config.get_agent_by_name("nonexistent-agent")

        assert agent is None

    def test_request_history_tracking(self):
        """Test request history tracking."""
        from tests.fixtures.acp_server_fixtures import MockACPServerConfig

        config = MockACPServerConfig()
        assert len(config.request_history) == 0

        # Create a mock request
        request = httpx.Request("GET", "http://localhost:8000/test")
        config.request_history.append(request)

        assert len(config.request_history) == 1

        config.reset()
        assert len(config.request_history) == 0


# =============================================================================
# Test Mock Endpoints (Integration)
# =============================================================================

class TestMockEndpoints:
    """Test mock endpoints respond correctly."""

    @pytest.mark.anyio
    async def test_mock_ping_endpoint(self, mock_acp_server):
        """Test ping endpoint responds correctly."""
        config, mock = mock_acp_server

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.base_url}/ping")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @pytest.mark.anyio
    async def test_mock_health_endpoint(self, mock_acp_server):
        """Test health endpoint responds correctly."""
        config, mock = mock_acp_server

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.base_url}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["agent_count"] == 3

    @pytest.mark.anyio
    async def test_mock_list_agents_endpoint(self, mock_acp_server):
        """Test list agents endpoint responds correctly."""
        config, mock = mock_acp_server

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.base_url}/agents")

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) == 3

    @pytest.mark.anyio
    async def test_mock_get_agent_endpoint(self, mock_acp_server):
        """Test get agent endpoint responds correctly."""
        config, mock = mock_acp_server

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.base_url}/agents/test-assistant")

        assert response.status_code == 200
        data = response.json()
        assert data["agent"]["name"] == "test-assistant"

    @pytest.mark.anyio
    async def test_mock_get_agent_not_found(self, mock_acp_server):
        """Test get agent endpoint returns 404 for unknown agent."""
        config, mock = mock_acp_server

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.base_url}/agents/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "not_found"

    @pytest.mark.anyio
    async def test_mock_create_run_endpoint(self, mock_acp_server):
        """Test create run endpoint responds correctly."""
        config, mock = mock_acp_server

        payload = {
            "agent": "test-assistant",
            "input": [
                {
                    "role": "user",
                    "parts": [{"content": "Hello", "content_type": "text/plain"}],
                }
            ],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.base_url}/runs",
                json=payload,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["agent_name"] == "test-assistant"
        assert "run_id" in data

    @pytest.mark.anyio
    async def test_mock_create_run_agent_not_found(self, mock_acp_server):
        """Test create run endpoint returns 404 for unknown agent."""
        config, mock = mock_acp_server

        payload = {
            "agent": "nonexistent-agent",
            "input": [
                {
                    "role": "user",
                    "parts": [{"content": "Hello", "content_type": "text/plain"}],
                }
            ],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.base_url}/runs",
                json=payload,
            )

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_mock_get_run_endpoint(self, mock_acp_server):
        """Test get run endpoint responds correctly."""
        config, mock = mock_acp_server
        run_id = "12345678-1234-5678-1234-567812345678"

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.base_url}/runs/{run_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id

    @pytest.mark.anyio
    async def test_mock_resume_run_endpoint(self, mock_acp_server):
        """Test resume run endpoint responds correctly."""
        config, mock = mock_acp_server
        run_id = "12345678-1234-5678-1234-567812345678"

        payload = {
            "input": [
                {
                    "role": "user",
                    "parts": [{"content": "Yes", "content_type": "text/plain"}],
                }
            ],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.base_url}/runs/{run_id}",
                json=payload,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    @pytest.mark.anyio
    async def test_mock_cancel_run_endpoint(self, mock_acp_server):
        """Test cancel run endpoint responds correctly."""
        config, mock = mock_acp_server
        run_id = "12345678-1234-5678-1234-567812345678"

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{config.base_url}/runs/{run_id}/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    @pytest.mark.anyio
    async def test_mock_get_session_endpoint(self, mock_acp_server):
        """Test get session endpoint responds correctly."""
        config, mock = mock_acp_server
        session_id = "87654321-4321-8765-4321-876543218765"

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.base_url}/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id

    @pytest.mark.anyio
    async def test_mock_legacy_create_run_endpoint(self, mock_acp_server):
        """Test legacy /agents/{name}/runs endpoint responds correctly."""
        config, mock = mock_acp_server

        payload = {
            "input": [
                {
                    "role": "user",
                    "parts": [{"content": "Hello", "content_type": "text/plain"}],
                }
            ],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.base_url}/agents/test-assistant/runs",
                json=payload,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["agent_name"] == "test-assistant"


# =============================================================================
# Test Error Simulation
# =============================================================================

class TestErrorSimulation:
    """Test error simulation in mock server."""

    @pytest.mark.anyio
    async def test_mock_server_error_ping(self, mock_acp_server_error):
        """Test ping endpoint returns error when configured."""
        config, mock = mock_acp_server_error

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.base_url}/ping")

        assert response.status_code == 503

    @pytest.mark.anyio
    async def test_mock_server_error_list_agents(self, mock_acp_server_error):
        """Test list agents endpoint returns error when configured."""
        config, mock = mock_acp_server_error

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.base_url}/agents")

        assert response.status_code == 500

    @pytest.mark.anyio
    async def test_mock_server_error_create_run(self, mock_acp_server_error):
        """Test create run endpoint returns error when configured."""
        config, mock = mock_acp_server_error

        payload = {
            "agent": "test-assistant",
            "input": [{"role": "user", "parts": [{"content": "Hello"}]}],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.base_url}/runs",
                json=payload,
            )

        assert response.status_code == 500


# =============================================================================
# Test Specific Fixture Scenarios
# =============================================================================

class TestSpecificFixtures:
    """Test specific fixture scenarios."""

    @pytest.mark.anyio
    async def test_mock_acp_agents_endpoint(self, mock_acp_agents_endpoint):
        """Test the agents-only endpoint fixture."""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/agents")

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data

    @pytest.mark.anyio
    async def test_mock_acp_run_sync(self, mock_acp_run_sync):
        """Test the sync run fixture."""
        payload = {
            "agent": "test-assistant",
            "input": [{"role": "user", "parts": [{"content": "Hello"}]}],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/runs",
                json=payload,
            )

        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    @pytest.mark.anyio
    async def test_mock_acp_run_async(self, mock_acp_run_async):
        """Test the async run fixture."""
        mock, run_id = mock_acp_run_async

        # Create run
        payload = {
            "agent": "test-assistant",
            "input": [{"role": "user", "parts": [{"content": "Hello"}]}],
            "mode": "async",
        }

        async with httpx.AsyncClient() as client:
            # Create returns in_progress
            response = await client.post(
                "http://localhost:8000/runs",
                json=payload,
            )
            assert response.json()["status"] == "in_progress"

            # Poll returns completed
            response = await client.get(f"http://localhost:8000/runs/{run_id}")
            assert response.json()["status"] == "completed"

    @pytest.mark.anyio
    async def test_mock_acp_run_awaiting(self, mock_acp_run_awaiting):
        """Test the awaiting run fixture."""
        mock, run_id = mock_acp_run_awaiting

        # Create run
        payload = {
            "agent": "test-assistant",
            "input": [{"role": "user", "parts": [{"content": "Do something"}]}],
        }

        async with httpx.AsyncClient() as client:
            # Create returns awaiting
            response = await client.post(
                "http://localhost:8000/runs",
                json=payload,
            )
            data = response.json()
            assert data["status"] == "awaiting"
            assert data["await_request"] is not None

            # Resume returns completed
            resume_payload = {
                "input": [{"role": "user", "parts": [{"content": "Yes"}]}],
            }
            response = await client.post(
                f"http://localhost:8000/runs/{run_id}",
                json=resume_payload,
            )
            assert response.json()["status"] == "completed"

    @pytest.mark.anyio
    async def test_mock_acp_agent_not_found(self, mock_acp_agent_not_found):
        """Test the agent not found fixture."""
        async with httpx.AsyncClient() as client:
            # Get agent returns 404
            response = await client.get("http://localhost:8000/agents/any-agent")
            assert response.status_code == 404

            # Create run returns 404
            payload = {
                "agent": "any-agent",
                "input": [{"role": "user", "parts": [{"content": "Hello"}]}],
            }
            response = await client.post(
                "http://localhost:8000/runs",
                json=payload,
            )
            assert response.status_code == 404

    @pytest.mark.anyio
    async def test_mock_acp_run_failed(self, mock_acp_run_failed):
        """Test the failed run fixture."""
        payload = {
            "agent": "test-assistant",
            "input": [{"role": "user", "parts": [{"content": "Hello"}]}],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/runs",
                json=payload,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] is not None
        assert data["error"]["code"] == "agent_error"

    @pytest.mark.anyio
    async def test_mock_acp_ping_success(self, mock_acp_ping_success):
        """Test the ping success fixture."""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/ping")

        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_mock_acp_ping_failure(self, mock_acp_ping_failure):
        """Test the ping failure fixture."""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/ping")

        assert response.status_code == 503


# =============================================================================
# Test Legacy Client Support
# =============================================================================

class TestLegacyClientSupport:
    """Test fixtures work with ACPClientService (legacy client)."""

    @pytest.mark.anyio
    async def test_mock_acp_client_service_ping(self, mock_acp_client_service):
        """Test ping endpoint for legacy client."""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/ping")

        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_mock_acp_client_service_list_agents(self, mock_acp_client_service):
        """Test list agents returns list format for legacy client."""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/agents")

        assert response.status_code == 200
        data = response.json()
        # Legacy client expects list format
        assert isinstance(data, list)
        assert len(data) == 3

    @pytest.mark.anyio
    async def test_mock_acp_client_service_run_agent(self, mock_acp_client_service):
        """Test run agent endpoint for legacy client."""
        payload = {
            "input": [
                {
                    "role": "user",
                    "parts": [{"content": "Hello", "content_type": "text/plain"}],
                }
            ],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/agents/test-assistant/runs",
                json=payload,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "output" in data


# =============================================================================
# Test Custom Mock Factory
# =============================================================================

class TestCustomMockFactory:
    """Test custom mock factory functions."""

    @pytest.mark.anyio
    async def test_custom_mock_acp_server_context_manager(self):
        """Test CustomMockACPServer context manager."""
        from tests.fixtures.acp_server_fixtures import CustomMockACPServer

        custom_agents = [{"name": "custom-agent", "description": "Custom agent", "status": "active"}]

        with CustomMockACPServer(
            agents=custom_agents,
            default_output_text="Custom output",
        ) as (config, mock):
            async with httpx.AsyncClient() as client:
                # List agents
                response = await client.get(f"{config.base_url}/agents")
                assert response.status_code == 200
                data = response.json()
                assert len(data["agents"]) == 1
                assert data["agents"][0]["name"] == "custom-agent"

                # Create run
                payload = {
                    "agent": "custom-agent",
                    "input": [{"role": "user", "parts": [{"content": "Hello"}]}],
                }
                response = await client.post(
                    f"{config.base_url}/runs",
                    json=payload,
                )
                assert response.status_code == 200
                data = response.json()
                assert data["output"][0]["parts"][0]["content"] == "Custom output"


# =============================================================================
# Test Request History Tracking
# =============================================================================

class TestRequestHistoryTracking:
    """Test request history tracking in mock server."""

    @pytest.mark.anyio
    async def test_request_history_is_tracked(self, mock_acp_server):
        """Test that requests are tracked in history."""
        config, mock = mock_acp_server

        assert len(config.request_history) == 0

        async with httpx.AsyncClient() as client:
            await client.get(f"{config.base_url}/ping")
            await client.get(f"{config.base_url}/agents")

        assert len(config.request_history) == 2

    @pytest.mark.anyio
    async def test_request_history_reset(self, mock_acp_server):
        """Test request history can be reset."""
        config, mock = mock_acp_server

        async with httpx.AsyncClient() as client:
            await client.get(f"{config.base_url}/ping")

        assert len(config.request_history) == 1

        config.reset()
        assert len(config.request_history) == 0


# =============================================================================
# Test SSE Response Creation
# =============================================================================

class TestSSEResponseCreation:
    """Test SSE response creation for streaming."""

    def test_create_sse_response(self):
        """Test create_sse_response function."""
        from tests.fixtures.acp_server_fixtures import create_sse_response

        events = [
            {"message": "Hello"},
            {"message": "World"},
        ]

        sse_response = create_sse_response(events)

        assert "data: " in sse_response
        assert '{"message": "Hello"}' in sse_response
        assert '{"message": "World"}' in sse_response

    @pytest.mark.anyio
    async def test_mock_acp_run_stream(self, mock_acp_run_stream):
        """Test streaming run fixture."""
        mock, events = mock_acp_run_stream

        payload = {
            "agent": "test-assistant",
            "input": [{"role": "user", "parts": [{"content": "Hello"}]}],
            "mode": "stream",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/runs",
                json=payload,
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
