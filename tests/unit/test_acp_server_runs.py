"""
Unit tests for ACPServer run creation and execution.

Tests cover:
- Run creation with sync/async/stream modes
- Run execution flow (success, failure, awaiting)
- Run state management (get, cancel, resume)
- Session integration with runs
- Error handling and edge cases
"""

from __future__ import annotations

from datetime import datetime
from typing import AsyncGenerator
from uuid import UUID, uuid4

import pytest


# =============================================================================
# Helper Functions for Lazy Imports
# =============================================================================


def _get_types():
    """Lazy import of ACP types module."""
    from app.acp.core.types import RunStatus, RunMode, ErrorCode

    return {
        "RunStatus": RunStatus,
        "RunMode": RunMode,
        "ErrorCode": ErrorCode,
    }


def _get_models():
    """Lazy import of ACP models module."""
    from app.acp.core.models import Message, Run, Session

    return {
        "Message": Message,
        "Run": Run,
        "Session": Session,
    }


def _get_schemas():
    """Lazy import of ACP schemas module."""
    from app.acp.core.schemas import (
        RunCreateRequest,
        RunResumeRequest,
        RunResponse,
    )

    return {
        "RunCreateRequest": RunCreateRequest,
        "RunResumeRequest": RunResumeRequest,
        "RunResponse": RunResponse,
    }


def _get_server():
    """Lazy import of ACPServer module."""
    from app.acp.server.base import ACPServer

    return {"ACPServer": ACPServer}


def _get_context():
    """Lazy import of Context module."""
    from app.acp.server.context import Context

    return {"Context": Context}


def _create_acp_server(name: str = "test-server", version: str = "1.0.0"):
    """Create an ACPServer instance for testing."""
    server_module = _get_server()
    return server_module["ACPServer"](name=name, version=version)


def _create_user_message(content: str = "Hello"):
    """Create a user message for testing."""
    models = _get_models()
    return models["Message"].user_text(content)


def _create_run_request(
    agent: str,
    content: str = "Hello",
    mode: str = "sync",
    session_id: UUID | None = None,
    metadata: dict | None = None,
):
    """Create a RunCreateRequest for testing."""
    schemas = _get_schemas()
    types = _get_types()
    models = _get_models()

    mode_enum = types["RunMode"](mode)
    input_messages = [models["Message"].user_text(content)]

    return schemas["RunCreateRequest"](
        agent=agent,
        input=input_messages,
        mode=mode_enum,
        session_id=session_id,
        metadata=metadata or {},
    )


# =============================================================================
# ACPServer Initialization Tests
# =============================================================================


class TestACPServerInitialization:
    """Tests for ACPServer initialization."""

    def test_server_creation_default(self):
        """Verify ACPServer can be created with defaults."""
        server = _create_acp_server()

        assert server.name == "test-server"
        assert server.version == "1.0.0"
        assert server.registry.count == 0

    def test_server_creation_custom_name(self):
        """Verify ACPServer can be created with custom name."""
        server = _create_acp_server(name="custom-server", version="2.0.0")

        assert server.name == "custom-server"
        assert server.version == "2.0.0"

    def test_server_uptime_tracking(self):
        """Verify ACPServer tracks uptime."""
        server = _create_acp_server()

        assert server.uptime_seconds >= 0
        assert isinstance(server.uptime_seconds, float)


# =============================================================================
# Agent Registration Tests
# =============================================================================


class TestACPServerAgentRegistration:
    """Tests for registering agents with ACPServer."""

    def test_register_agent_via_decorator(self):
        """Verify agent can be registered via decorator."""
        server = _create_acp_server()
        models = _get_models()

        @server.agent(name="echo", description="Echo agent")
        async def echo_agent(input, context):
            for msg in input:
                yield models["Message"].agent_text(f"Echo: {msg.parts[0].content}")

        assert server.registry.has_agent("echo")
        assert server.registry.count == 1

    def test_register_multiple_agents(self):
        """Verify multiple agents can be registered."""
        server = _create_acp_server()
        models = _get_models()

        @server.agent(name="agent-1", description="First agent")
        async def agent_one(input, context):
            yield models["Message"].agent_text("One")

        @server.agent(name="agent-2", description="Second agent")
        async def agent_two(input, context):
            yield models["Message"].agent_text("Two")

        @server.agent(name="agent-3", description="Third agent")
        async def agent_three(input, context):
            yield models["Message"].agent_text("Three")

        assert server.registry.count == 3
        assert server.registry.has_agent("agent-1")
        assert server.registry.has_agent("agent-2")
        assert server.registry.has_agent("agent-3")

    def test_register_agent_with_custom_content_types(self):
        """Verify agent can be registered with custom content types."""
        server = _create_acp_server()
        models = _get_models()

        @server.agent(
            name="multimodal-agent",
            description="Multimodal agent",
            input_content_types=["text/plain", "image/png"],
            output_content_types=["text/plain", "application/json"],
        )
        async def multimodal_agent(input, context):
            yield models["Message"].agent_text("Processed")

        manifest = server.registry.get_manifest("multimodal-agent")
        assert "text/plain" in manifest.input_content_types
        assert "image/png" in manifest.input_content_types
        assert "application/json" in manifest.output_content_types


# =============================================================================
# Run Creation Tests - Sync Mode
# =============================================================================


class TestACPServerRunCreationSync:
    """Tests for creating and executing runs in sync mode."""

    @pytest.mark.asyncio
    async def test_create_run_sync_success(self):
        """Verify sync run completes successfully."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="echo", description="Echo agent")
        async def echo_agent(input, context):
            for msg in input:
                yield models["Message"].agent_text(f"Echo: {msg.parts[0].content}")

        request = _create_run_request(agent="echo", content="Hello World", mode="sync")
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].COMPLETED
        assert response.agent_name == "echo"
        assert len(response.output) == 1
        assert response.output[0].parts[0].content == "Echo: Hello World"
        assert response.completed_at is not None
        assert response.error is None

    @pytest.mark.asyncio
    async def test_create_run_sync_multiple_outputs(self):
        """Verify sync run can produce multiple output messages."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="multi-output", description="Multiple output agent")
        async def multi_output_agent(input, context):
            yield models["Message"].agent_text("First response")
            yield models["Message"].agent_text("Second response")
            yield models["Message"].agent_text("Third response")

        request = _create_run_request(agent="multi-output", content="Hello")
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].COMPLETED
        assert len(response.output) == 3
        assert response.output[0].parts[0].content == "First response"
        assert response.output[1].parts[0].content == "Second response"
        assert response.output[2].parts[0].content == "Third response"

    @pytest.mark.asyncio
    async def test_create_run_sync_with_context(self):
        """Verify sync run receives proper context."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        captured_context = {}

        @server.agent(name="context-test", description="Context test agent")
        async def context_agent(input, context):
            captured_context["run_id"] = context.run_id
            captured_context["agent_name"] = context.agent_name
            captured_context["metadata"] = context.metadata
            yield models["Message"].agent_text("Context captured")

        request = _create_run_request(
            agent="context-test",
            content="Hello",
            metadata={"custom_key": "custom_value"},
        )
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].COMPLETED
        assert captured_context["run_id"] is not None
        assert captured_context["agent_name"] == "context-test"
        assert captured_context["metadata"]["custom_key"] == "custom_value"

    @pytest.mark.asyncio
    async def test_create_run_agent_not_found(self):
        """Verify error when agent doesn't exist."""
        server = _create_acp_server()
        types = _get_types()

        request = _create_run_request(agent="nonexistent-agent", content="Hello")
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].FAILED
        assert response.error is not None
        assert response.error.code == types["ErrorCode"].NOT_FOUND
        assert "nonexistent-agent" in response.error.message

    @pytest.mark.asyncio
    async def test_create_run_sync_with_agent_error(self):
        """Verify run fails when agent raises exception."""
        server = _create_acp_server()
        types = _get_types()

        @server.agent(name="error-agent", description="Agent that raises errors")
        async def error_agent(input, context):
            raise RuntimeError("Something went wrong!")
            yield  # Make it a generator

        request = _create_run_request(agent="error-agent", content="Hello")
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].FAILED
        assert response.error is not None
        assert response.error.code == types["ErrorCode"].AGENT_ERROR
        assert "Something went wrong" in response.error.message
        assert response.completed_at is not None


# =============================================================================
# Run Creation Tests - Async Mode
# =============================================================================


class TestACPServerRunCreationAsync:
    """Tests for creating runs in async mode."""

    @pytest.mark.asyncio
    async def test_create_run_async_returns_in_progress(self):
        """Verify async run returns in-progress status immediately."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="async-agent", description="Async agent")
        async def async_agent(input, context):
            yield models["Message"].agent_text("Response")

        request = _create_run_request(agent="async-agent", content="Hello", mode="async")
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].IN_PROGRESS
        assert response.agent_name == "async-agent"
        assert response.run_id is not None


# =============================================================================
# Run Creation Tests - Stream Mode
# =============================================================================


class TestACPServerRunCreationStream:
    """Tests for creating runs in stream mode."""

    @pytest.mark.asyncio
    async def test_create_run_stream_returns_in_progress(self):
        """Verify stream run returns in-progress status."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="stream-agent", description="Stream agent")
        async def stream_agent(input, context):
            yield models["Message"].agent_text("Chunk 1")
            yield models["Message"].agent_text("Chunk 2")

        request = _create_run_request(agent="stream-agent", content="Hello", mode="stream")
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].IN_PROGRESS
        assert response.agent_name == "stream-agent"


# =============================================================================
# Run Retrieval Tests
# =============================================================================


class TestACPServerGetRun:
    """Tests for retrieving run status."""

    @pytest.mark.asyncio
    async def test_get_run_after_completion(self):
        """Verify completed run can be retrieved."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="echo", description="Echo agent")
        async def echo_agent(input, context):
            yield models["Message"].agent_text("Echo response")

        request = _create_run_request(agent="echo", content="Hello")
        create_response = await server.create_run(request)

        get_response = await server.get_run(create_response.run_id)

        assert get_response is not None
        assert get_response.run_id == create_response.run_id
        assert get_response.status == types["RunStatus"].COMPLETED
        assert get_response.agent_name == "echo"

    @pytest.mark.asyncio
    async def test_get_run_not_found(self):
        """Verify None returned for nonexistent run."""
        server = _create_acp_server()

        response = await server.get_run(uuid4())

        assert response is None

    @pytest.mark.asyncio
    async def test_get_run_preserves_output(self):
        """Verify run output is preserved when retrieved."""
        server = _create_acp_server()
        models = _get_models()

        @server.agent(name="echo", description="Echo agent")
        async def echo_agent(input, context):
            yield models["Message"].agent_text("Output message")

        request = _create_run_request(agent="echo", content="Hello")
        create_response = await server.create_run(request)

        get_response = await server.get_run(create_response.run_id)

        assert len(get_response.output) == 1
        assert get_response.output[0].parts[0].content == "Output message"


# =============================================================================
# Run Cancellation Tests
# =============================================================================


class TestACPServerCancelRun:
    """Tests for cancelling runs."""

    @pytest.mark.asyncio
    async def test_cancel_completed_run(self):
        """Verify cancelling completed run returns current status."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="echo", description="Echo agent")
        async def echo_agent(input, context):
            yield models["Message"].agent_text("Response")

        request = _create_run_request(agent="echo", content="Hello")
        create_response = await server.create_run(request)

        cancel_response = await server.cancel_run(create_response.run_id)

        # Completed runs stay completed
        assert cancel_response.status == types["RunStatus"].COMPLETED

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_run(self):
        """Verify None returned when cancelling nonexistent run."""
        server = _create_acp_server()

        response = await server.cancel_run(uuid4())

        assert response is None

    @pytest.mark.asyncio
    async def test_cancel_failed_run(self):
        """Verify cancelling failed run returns current status."""
        server = _create_acp_server()
        types = _get_types()

        @server.agent(name="error-agent", description="Agent that errors")
        async def error_agent(input, context):
            raise RuntimeError("Error!")
            yield

        request = _create_run_request(agent="error-agent", content="Hello")
        create_response = await server.create_run(request)

        cancel_response = await server.cancel_run(create_response.run_id)

        # Failed runs stay failed
        assert cancel_response.status == types["RunStatus"].FAILED


# =============================================================================
# Run Awaiting Tests
# =============================================================================


class TestACPServerAwaitingRuns:
    """Tests for runs in awaiting state."""

    @pytest.mark.asyncio
    async def test_run_awaiting_state(self):
        """Verify run can enter awaiting state."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="await-agent", description="Agent that awaits")
        async def await_agent(input, context):
            yield models["Message"].agent_text("Processing...")
            yield {"await": {"type": "user_confirmation", "description": "Please confirm"}}

        request = _create_run_request(agent="await-agent", content="Hello")
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].AWAITING
        assert response.await_request is not None
        assert len(response.output) == 1
        assert response.output[0].parts[0].content == "Processing..."

    @pytest.mark.asyncio
    async def test_resume_awaiting_run(self):
        """Verify awaiting run can be resumed."""
        server = _create_acp_server()
        models = _get_models()
        schemas = _get_schemas()
        types = _get_types()

        call_count = [0]

        @server.agent(name="await-agent", description="Agent that awaits")
        async def await_agent(input, context):
            call_count[0] += 1
            if call_count[0] == 1:
                yield models["Message"].agent_text("Processing...")
                yield {"await": {"type": "user_confirmation", "description": "Please confirm"}}
            else:
                yield models["Message"].agent_text("Resumed and completed")

        # First call - enters awaiting state
        request = _create_run_request(agent="await-agent", content="Hello")
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].AWAITING

        # Resume the run
        resume_request = schemas["RunResumeRequest"](
            input=[models["Message"].user_text("Yes, confirmed")]
        )
        resume_response = await server.resume_run(response.run_id, resume_request)

        assert resume_response is not None
        assert resume_response.status == types["RunStatus"].COMPLETED
        assert len(resume_response.output) > 0

    @pytest.mark.asyncio
    async def test_resume_non_awaiting_run(self):
        """Verify error when resuming non-awaiting run."""
        server = _create_acp_server()
        models = _get_models()
        schemas = _get_schemas()
        types = _get_types()

        @server.agent(name="echo", description="Echo agent")
        async def echo_agent(input, context):
            yield models["Message"].agent_text("Done")

        # Create a completed run
        request = _create_run_request(agent="echo", content="Hello")
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].COMPLETED

        # Try to resume it
        resume_request = schemas["RunResumeRequest"](
            input=[models["Message"].user_text("Resume")]
        )
        resume_response = await server.resume_run(response.run_id, resume_request)

        assert resume_response.status == types["RunStatus"].FAILED
        assert resume_response.error.code == types["ErrorCode"].CONFLICT

    @pytest.mark.asyncio
    async def test_resume_nonexistent_run(self):
        """Verify None returned when resuming nonexistent run."""
        server = _create_acp_server()
        models = _get_models()
        schemas = _get_schemas()

        resume_request = schemas["RunResumeRequest"](
            input=[models["Message"].user_text("Resume")]
        )
        response = await server.resume_run(uuid4(), resume_request)

        assert response is None


# =============================================================================
# Session Integration Tests
# =============================================================================


class TestACPServerSessionIntegration:
    """Tests for session integration with runs."""

    @pytest.mark.asyncio
    async def test_create_run_with_new_session(self):
        """Verify run can create new session."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="echo", description="Echo agent")
        async def echo_agent(input, context):
            yield models["Message"].agent_text("Response")

        session_id = uuid4()
        request = _create_run_request(
            agent="echo", content="Hello", session_id=session_id
        )
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].COMPLETED
        assert response.session_id == session_id

        # Verify session was created
        session_response = server.get_session(session_id)
        assert session_response is not None
        assert session_response.session_id == session_id
        assert session_response.agent_name == "echo"

    @pytest.mark.asyncio
    async def test_create_run_with_existing_session(self):
        """Verify run can use existing session."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="echo", description="Echo agent")
        async def echo_agent(input, context):
            yield models["Message"].agent_text("Response")

        # Create session first
        session = server.create_session(agent_name="echo")

        # Create run with existing session
        request = _create_run_request(
            agent="echo", content="Hello", session_id=session.session_id
        )
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].COMPLETED
        assert response.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_session_accumulates_messages(self):
        """Verify session accumulates messages from multiple runs."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="echo", description="Echo agent")
        async def echo_agent(input, context):
            yield models["Message"].agent_text(f"Response to: {input[-1].parts[0].content}")

        session_id = uuid4()

        # First run
        request1 = _create_run_request(
            agent="echo", content="First message", session_id=session_id
        )
        response1 = await server.create_run(request1)
        assert response1.status == types["RunStatus"].COMPLETED

        # Second run
        request2 = _create_run_request(
            agent="echo", content="Second message", session_id=session_id
        )
        response2 = await server.create_run(request2)
        assert response2.status == types["RunStatus"].COMPLETED

        # Check session has accumulated messages
        session_response = server.get_session(session_id)
        assert session_response is not None
        assert session_response.run_count == 2
        # Session should have both response messages
        assert len(session_response.messages) >= 2

    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        """Verify None returned for nonexistent session."""
        server = _create_acp_server()

        response = server.get_session(uuid4())

        assert response is None

    def test_create_session_with_metadata(self):
        """Verify session can be created with metadata."""
        server = _create_acp_server()

        session = server.create_session(
            agent_name="test-agent",
            metadata={"custom_key": "custom_value"},
        )

        assert session.session_id is not None
        assert session.agent_name == "test-agent"
        assert session.metadata["custom_key"] == "custom_value"


# =============================================================================
# Agent List/Get Operations Tests
# =============================================================================


class TestACPServerAgentOperations:
    """Tests for agent listing and retrieval operations."""

    def test_list_agents_empty(self):
        """Verify list_agents returns empty for new server."""
        server = _create_acp_server()

        response = server.list_agents()

        assert response.agents == []
        assert response.total == 0

    def test_list_agents_with_agents(self):
        """Verify list_agents returns registered agents."""
        server = _create_acp_server()
        models = _get_models()

        @server.agent(name="agent-1", description="First agent")
        async def agent_one(input, context):
            yield models["Message"].agent_text("One")

        @server.agent(name="agent-2", description="Second agent")
        async def agent_two(input, context):
            yield models["Message"].agent_text("Two")

        response = server.list_agents()

        assert response.total == 2
        assert len(response.agents) == 2
        names = [a.name for a in response.agents]
        assert "agent-1" in names
        assert "agent-2" in names

    def test_list_agents_pagination(self):
        """Verify list_agents respects pagination."""
        server = _create_acp_server()
        models = _get_models()

        for i in range(5):
            @server.agent(name=f"agent-{i}", description=f"Agent {i}")
            async def agent_func(input, context, i=i):
                yield models["Message"].agent_text(f"Agent {i}")

        response = server.list_agents(offset=2, limit=2)

        assert response.total == 5
        assert len(response.agents) == 2
        assert response.offset == 2
        assert response.limit == 2

    def test_get_agent_existing(self):
        """Verify get_agent returns existing agent."""
        server = _create_acp_server()
        models = _get_models()

        @server.agent(name="test-agent", description="Test agent description")
        async def test_agent(input, context):
            yield models["Message"].agent_text("Hello")

        response = server.get_agent("test-agent")

        assert response is not None
        assert response.agent.name == "test-agent"
        assert response.agent.description == "Test agent description"

    def test_get_agent_not_found(self):
        """Verify get_agent returns None for nonexistent agent."""
        server = _create_acp_server()

        response = server.get_agent("nonexistent-agent")

        assert response is None


# =============================================================================
# Run Metadata Tests
# =============================================================================


class TestACPServerRunMetadata:
    """Tests for run metadata handling."""

    @pytest.mark.asyncio
    async def test_run_metadata_passed_to_context(self):
        """Verify run metadata is accessible in context."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        received_metadata = {}

        @server.agent(name="metadata-agent", description="Metadata test agent")
        async def metadata_agent(input, context):
            received_metadata.update(context.metadata)
            yield models["Message"].agent_text("Done")

        request = _create_run_request(
            agent="metadata-agent",
            content="Hello",
            metadata={"key1": "value1", "key2": "value2"},
        )
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].COMPLETED
        assert received_metadata["key1"] == "value1"
        assert received_metadata["key2"] == "value2"

    @pytest.mark.asyncio
    async def test_run_timestamps(self):
        """Verify run timestamps are set correctly."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="echo", description="Echo agent")
        async def echo_agent(input, context):
            yield models["Message"].agent_text("Response")

        request = _create_run_request(agent="echo", content="Hello")
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].COMPLETED
        assert response.created_at is not None
        assert response.completed_at is not None
        assert response.completed_at >= response.created_at


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestACPServerEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_agent_yields_no_output(self):
        """Verify run completes with empty output when agent yields nothing."""
        server = _create_acp_server()
        types = _get_types()

        @server.agent(name="empty-agent", description="Agent with no output")
        async def empty_agent(input, context):
            # Generator that yields nothing
            return
            yield  # Make it a generator

        request = _create_run_request(agent="empty-agent", content="Hello")
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].COMPLETED
        assert response.output == []

    @pytest.mark.asyncio
    async def test_run_with_multiple_input_messages(self):
        """Verify run handles multiple input messages."""
        server = _create_acp_server()
        models = _get_models()
        schemas = _get_schemas()
        types = _get_types()

        received_count = [0]

        @server.agent(name="counter", description="Message counter")
        async def counter_agent(input, context):
            received_count[0] = len(input)
            yield models["Message"].agent_text(f"Received {len(input)} messages")

        # Create request with multiple input messages
        input_messages = [
            models["Message"].user_text("Message 1"),
            models["Message"].user_text("Message 2"),
            models["Message"].user_text("Message 3"),
        ]

        request = schemas["RunCreateRequest"](
            agent="counter",
            input=input_messages,
            mode=types["RunMode"].SYNC,
        )
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].COMPLETED
        assert received_count[0] == 3
        assert "3 messages" in response.output[0].parts[0].content

    @pytest.mark.asyncio
    async def test_run_isolation_between_agents(self):
        """Verify runs are isolated between different agents."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="agent-a", description="Agent A")
        async def agent_a(input, context):
            yield models["Message"].agent_text("A response")

        @server.agent(name="agent-b", description="Agent B")
        async def agent_b(input, context):
            yield models["Message"].agent_text("B response")

        request_a = _create_run_request(agent="agent-a", content="Hello A")
        request_b = _create_run_request(agent="agent-b", content="Hello B")

        response_a = await server.create_run(request_a)
        response_b = await server.create_run(request_b)

        assert response_a.agent_name == "agent-a"
        assert response_b.agent_name == "agent-b"
        assert response_a.output[0].parts[0].content == "A response"
        assert response_b.output[0].parts[0].content == "B response"
        assert response_a.run_id != response_b.run_id

    @pytest.mark.asyncio
    async def test_concurrent_runs_same_agent(self):
        """Verify multiple concurrent runs work correctly."""
        import asyncio

        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="echo", description="Echo agent")
        async def echo_agent(input, context):
            yield models["Message"].agent_text(f"Echo: {input[0].parts[0].content}")

        # Create multiple requests
        requests = [
            _create_run_request(agent="echo", content=f"Message {i}")
            for i in range(5)
        ]

        # Run concurrently
        responses = await asyncio.gather(
            *[server.create_run(req) for req in requests]
        )

        # Verify all completed
        for i, response in enumerate(responses):
            assert response.status == types["RunStatus"].COMPLETED
            assert f"Message {i}" in response.output[0].parts[0].content


# =============================================================================
# Run Response Structure Tests
# =============================================================================


class TestACPServerRunResponse:
    """Tests for run response structure."""

    @pytest.mark.asyncio
    async def test_run_response_has_required_fields(self):
        """Verify run response contains all required fields."""
        server = _create_acp_server()
        models = _get_models()

        @server.agent(name="echo", description="Echo agent")
        async def echo_agent(input, context):
            yield models["Message"].agent_text("Response")

        request = _create_run_request(agent="echo", content="Hello")
        response = await server.create_run(request)

        # Required fields
        assert hasattr(response, "run_id")
        assert hasattr(response, "agent_name")
        assert hasattr(response, "status")
        assert hasattr(response, "output")
        assert hasattr(response, "error")
        assert hasattr(response, "created_at")
        assert hasattr(response, "completed_at")

        # Check types
        assert isinstance(response.run_id, UUID)
        assert isinstance(response.agent_name, str)
        assert isinstance(response.output, list)

    @pytest.mark.asyncio
    async def test_run_response_error_structure(self):
        """Verify error response has correct structure."""
        server = _create_acp_server()
        types = _get_types()

        @server.agent(name="error-agent", description="Error agent")
        async def error_agent(input, context):
            raise ValueError("Test error message")
            yield

        request = _create_run_request(agent="error-agent", content="Hello")
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].FAILED
        assert response.error is not None
        assert hasattr(response.error, "code")
        assert hasattr(response.error, "message")
        assert "Test error message" in response.error.message
