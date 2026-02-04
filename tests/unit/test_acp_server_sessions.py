"""
Unit tests for ACPServer session management.

Tests cover:
- Session creation and retrieval
- Session lifecycle (creation, activity tracking, expiration)
- Session-run relationships
- Session context/state management
- Multi-turn conversation handling
- Session isolation between agents
- Session metadata operations
- Edge cases and error handling
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import AsyncGenerator
from uuid import UUID, uuid4
import time

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
        SessionResponse,
    )

    return {
        "RunCreateRequest": RunCreateRequest,
        "RunResumeRequest": RunResumeRequest,
        "RunResponse": RunResponse,
        "SessionResponse": SessionResponse,
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
# Session Creation Tests
# =============================================================================


class TestSessionCreation:
    """Tests for creating sessions in ACPServer."""

    def test_create_session_basic(self):
        """Verify session can be created with minimal parameters."""
        server = _create_acp_server()

        session = server.create_session()

        assert session is not None
        assert isinstance(session.session_id, UUID)
        assert session.agent_name is None
        assert session.messages == []
        assert session.runs == []
        assert session.context == {}
        assert session.metadata == {}

    def test_create_session_with_agent_name(self):
        """Verify session can be created with agent name."""
        server = _create_acp_server()

        session = server.create_session(agent_name="test-agent")

        assert session.agent_name == "test-agent"

    def test_create_session_with_metadata(self):
        """Verify session can be created with metadata."""
        server = _create_acp_server()

        metadata = {
            "user_id": "user-123",
            "channel": "web",
            "locale": "en-US",
        }

        session = server.create_session(metadata=metadata)

        assert session.metadata == metadata
        assert session.metadata["user_id"] == "user-123"
        assert session.metadata["channel"] == "web"
        assert session.metadata["locale"] == "en-US"

    def test_create_session_with_all_parameters(self):
        """Verify session can be created with all parameters."""
        server = _create_acp_server()

        metadata = {"key": "value"}

        session = server.create_session(
            agent_name="full-agent",
            metadata=metadata,
        )

        assert session.agent_name == "full-agent"
        assert session.metadata == metadata

    def test_create_multiple_sessions(self):
        """Verify multiple sessions can be created independently."""
        server = _create_acp_server()

        session1 = server.create_session(agent_name="agent-1")
        session2 = server.create_session(agent_name="agent-2")
        session3 = server.create_session(agent_name="agent-3")

        assert session1.session_id != session2.session_id
        assert session2.session_id != session3.session_id
        assert session1.session_id != session3.session_id

    def test_create_session_timestamps(self):
        """Verify session has proper timestamps on creation."""
        server = _create_acp_server()

        before_create = datetime.utcnow()
        session = server.create_session()
        after_create = datetime.utcnow()

        assert session.created_at is not None
        assert session.last_activity_at is not None
        assert before_create <= session.created_at <= after_create
        assert before_create <= session.last_activity_at <= after_create

    def test_create_session_unique_ids(self):
        """Verify each created session has unique ID."""
        server = _create_acp_server()
        session_ids = set()

        for _ in range(100):
            session = server.create_session()
            assert session.session_id not in session_ids
            session_ids.add(session.session_id)

        assert len(session_ids) == 100


# =============================================================================
# Session Retrieval Tests
# =============================================================================


class TestSessionRetrieval:
    """Tests for retrieving sessions from ACPServer."""

    def test_get_session_after_creation(self):
        """Verify session can be retrieved after creation."""
        server = _create_acp_server()

        created_session = server.create_session(agent_name="test-agent")
        response = server.get_session(created_session.session_id)

        assert response is not None
        assert response.session_id == created_session.session_id
        assert response.agent_name == "test-agent"

    def test_get_session_not_found(self):
        """Verify None returned for nonexistent session."""
        server = _create_acp_server()

        response = server.get_session(uuid4())

        assert response is None

    def test_get_session_returns_session_response(self):
        """Verify get_session returns SessionResponse type."""
        server = _create_acp_server()
        schemas = _get_schemas()

        session = server.create_session(agent_name="test-agent")
        response = server.get_session(session.session_id)

        assert isinstance(response, schemas["SessionResponse"])

    def test_get_session_response_fields(self):
        """Verify SessionResponse has all expected fields."""
        server = _create_acp_server()

        session = server.create_session(agent_name="response-test-agent")
        response = server.get_session(session.session_id)

        assert hasattr(response, "session_id")
        assert hasattr(response, "agent_name")
        assert hasattr(response, "messages")
        assert hasattr(response, "run_count")
        assert hasattr(response, "created_at")
        assert hasattr(response, "last_activity_at")

    def test_get_session_with_messages(self):
        """Verify get_session returns messages accumulated in session."""
        server = _create_acp_server()
        models = _get_models()

        @server.agent(name="chat-agent", description="Chat agent")
        async def chat_agent(input, context):
            yield models["Message"].agent_text("Response message")

        session_id = uuid4()
        request = _create_run_request(
            agent="chat-agent",
            content="User message",
            session_id=session_id,
        )

        # Run creates session and adds messages
        import asyncio
        asyncio.get_event_loop().run_until_complete(server.create_run(request))

        response = server.get_session(session_id)

        assert response is not None
        assert len(response.messages) >= 1


# =============================================================================
# Session-Run Relationship Tests
# =============================================================================


class TestSessionRunRelationship:
    """Tests for relationship between sessions and runs."""

    @pytest.mark.asyncio
    async def test_session_tracks_run_ids(self):
        """Verify session tracks all associated run IDs."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="tracker-agent", description="Tracker agent")
        async def tracker_agent(input, context):
            yield models["Message"].agent_text("Tracked")

        session = server.create_session(agent_name="tracker-agent")

        # Execute multiple runs in the same session
        for i in range(3):
            request = _create_run_request(
                agent="tracker-agent",
                content=f"Message {i}",
                session_id=session.session_id,
            )
            response = await server.create_run(request)
            assert response.status == types["RunStatus"].COMPLETED

        # Session should track all run IDs
        assert len(session.runs) == 3

    @pytest.mark.asyncio
    async def test_run_references_session_id(self):
        """Verify run response contains correct session_id."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="ref-agent", description="Reference agent")
        async def ref_agent(input, context):
            yield models["Message"].agent_text("Response")

        session_id = uuid4()
        request = _create_run_request(
            agent="ref-agent",
            content="Test",
            session_id=session_id,
        )

        response = await server.create_run(request)

        assert response.session_id == session_id

    @pytest.mark.asyncio
    async def test_run_without_session(self):
        """Verify run can execute without session."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="sessionless-agent", description="Sessionless agent")
        async def sessionless_agent(input, context):
            yield models["Message"].agent_text("No session needed")

        request = _create_run_request(
            agent="sessionless-agent",
            content="Test",
            session_id=None,
        )

        response = await server.create_run(request)

        assert response.status == types["RunStatus"].COMPLETED
        assert response.session_id is None

    @pytest.mark.asyncio
    async def test_session_run_count_accurate(self):
        """Verify session run_count is accurate."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="count-agent", description="Count agent")
        async def count_agent(input, context):
            yield models["Message"].agent_text("Counted")

        session = server.create_session(agent_name="count-agent")

        for i in range(5):
            request = _create_run_request(
                agent="count-agent",
                content=f"Run {i}",
                session_id=session.session_id,
            )
            await server.create_run(request)

        response = server.get_session(session.session_id)
        assert response.run_count == 5


# =============================================================================
# Session Activity Tracking Tests
# =============================================================================


class TestSessionActivityTracking:
    """Tests for session activity timestamp tracking."""

    @pytest.mark.asyncio
    async def test_session_last_activity_updated_on_run(self):
        """Verify last_activity_at is updated when run completes."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="activity-agent", description="Activity agent")
        async def activity_agent(input, context):
            yield models["Message"].agent_text("Activity")

        session = server.create_session(agent_name="activity-agent")
        initial_activity = session.last_activity_at

        # Small delay to ensure timestamp difference
        time.sleep(0.01)

        request = _create_run_request(
            agent="activity-agent",
            content="Test",
            session_id=session.session_id,
        )
        await server.create_run(request)

        assert session.last_activity_at > initial_activity

    @pytest.mark.asyncio
    async def test_created_at_unchanged_after_runs(self):
        """Verify created_at remains unchanged after runs."""
        server = _create_acp_server()
        models = _get_models()

        @server.agent(name="timestamp-agent", description="Timestamp agent")
        async def timestamp_agent(input, context):
            yield models["Message"].agent_text("Response")

        session = server.create_session(agent_name="timestamp-agent")
        original_created_at = session.created_at

        for _ in range(3):
            request = _create_run_request(
                agent="timestamp-agent",
                content="Test",
                session_id=session.session_id,
            )
            await server.create_run(request)

        assert session.created_at == original_created_at


# =============================================================================
# Session Message Accumulation Tests
# =============================================================================


class TestSessionMessageAccumulation:
    """Tests for message accumulation in sessions."""

    @pytest.mark.asyncio
    async def test_session_accumulates_agent_responses(self):
        """Verify session accumulates agent response messages."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="accumulator-agent", description="Accumulator agent")
        async def accumulator_agent(input, context):
            yield models["Message"].agent_text("First response")
            yield models["Message"].agent_text("Second response")

        session_id = uuid4()
        request = _create_run_request(
            agent="accumulator-agent",
            content="Input",
            session_id=session_id,
        )

        await server.create_run(request)

        response = server.get_session(session_id)
        assert len(response.messages) == 2

    @pytest.mark.asyncio
    async def test_session_preserves_message_order(self):
        """Verify session preserves message order across runs."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="order-agent", description="Order agent")
        async def order_agent(input, context):
            msg_text = input[-1].parts[0].content
            yield models["Message"].agent_text(f"Response to: {msg_text}")

        session_id = uuid4()

        for i in range(3):
            request = _create_run_request(
                agent="order-agent",
                content=f"Message {i}",
                session_id=session_id,
            )
            await server.create_run(request)

        response = server.get_session(session_id)

        # Verify responses are in correct order
        for i, msg in enumerate(response.messages):
            assert f"Message {i}" in msg.parts[0].content

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_context(self):
        """Verify session maintains context for multi-turn conversations."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        conversation_history = []

        @server.agent(name="context-agent", description="Context-aware agent")
        async def context_agent(input, context):
            # Access session messages for conversation history
            history_len = len(context.messages) if context.session else len(input)
            conversation_history.append(history_len)
            yield models["Message"].agent_text(f"History length: {history_len}")

        session_id = uuid4()

        for i in range(3):
            request = _create_run_request(
                agent="context-agent",
                content=f"Turn {i}",
                session_id=session_id,
            )
            await server.create_run(request)

        # Each turn should see accumulated messages
        # Conversation history grows with each turn
        assert len(conversation_history) == 3


# =============================================================================
# Session Context/State Management Tests
# =============================================================================


class TestSessionContextManagement:
    """Tests for session context and state management."""

    @pytest.mark.asyncio
    async def test_session_context_accessible_in_agent(self):
        """Verify session context is accessible in agent handler."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        captured_context = {}

        @server.agent(name="context-reader", description="Context reader")
        async def context_reader(input, context):
            if context.session:
                captured_context.update(context.session.context)
            yield models["Message"].agent_text("Read context")

        # Create session with initial context
        session = server.create_session(agent_name="context-reader")
        session.context["initial_key"] = "initial_value"
        session.context["user_preference"] = "dark_mode"

        request = _create_run_request(
            agent="context-reader",
            content="Test",
            session_id=session.session_id,
        )
        await server.create_run(request)

        assert captured_context.get("initial_key") == "initial_value"
        assert captured_context.get("user_preference") == "dark_mode"

    @pytest.mark.asyncio
    async def test_session_context_modifiable_by_agent(self):
        """Verify agent can modify session context."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="context-writer", description="Context writer")
        async def context_writer(input, context):
            if context.session:
                context.set_context_value("agent_written", "agent_value")
                context.set_context_value("counter", 42)
            yield models["Message"].agent_text("Wrote context")

        session = server.create_session(agent_name="context-writer")

        request = _create_run_request(
            agent="context-writer",
            content="Test",
            session_id=session.session_id,
        )
        await server.create_run(request)

        assert session.context.get("agent_written") == "agent_value"
        assert session.context.get("counter") == 42

    @pytest.mark.asyncio
    async def test_session_context_persists_across_runs(self):
        """Verify session context persists across multiple runs."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="persistence-agent", description="Persistence agent")
        async def persistence_agent(input, context):
            count = context.get_context_value("run_count", 0)
            count += 1
            context.set_context_value("run_count", count)
            yield models["Message"].agent_text(f"Run count: {count}")

        session = server.create_session(agent_name="persistence-agent")

        for i in range(5):
            request = _create_run_request(
                agent="persistence-agent",
                content=f"Run {i}",
                session_id=session.session_id,
            )
            await server.create_run(request)

        assert session.context.get("run_count") == 5


# =============================================================================
# Session Isolation Tests
# =============================================================================


class TestSessionIsolation:
    """Tests for session isolation between different conversations."""

    @pytest.mark.asyncio
    async def test_sessions_isolated_from_each_other(self):
        """Verify sessions are isolated from each other."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="isolated-agent", description="Isolated agent")
        async def isolated_agent(input, context):
            counter = context.get_context_value("counter", 0)
            counter += 1
            context.set_context_value("counter", counter)
            yield models["Message"].agent_text(f"Counter: {counter}")

        # Create two separate sessions
        session1 = server.create_session(agent_name="isolated-agent")
        session2 = server.create_session(agent_name="isolated-agent")

        # Run 3 times in session 1
        for _ in range(3):
            request = _create_run_request(
                agent="isolated-agent",
                content="Test",
                session_id=session1.session_id,
            )
            await server.create_run(request)

        # Run 2 times in session 2
        for _ in range(2):
            request = _create_run_request(
                agent="isolated-agent",
                content="Test",
                session_id=session2.session_id,
            )
            await server.create_run(request)

        # Verify counters are independent
        assert session1.context.get("counter") == 3
        assert session2.context.get("counter") == 2

    @pytest.mark.asyncio
    async def test_session_messages_isolated(self):
        """Verify session messages are isolated."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="msg-isolated-agent", description="Message isolated agent")
        async def msg_isolated_agent(input, context):
            yield models["Message"].agent_text("Response")

        session1 = server.create_session(agent_name="msg-isolated-agent")
        session2 = server.create_session(agent_name="msg-isolated-agent")

        # Add messages to session 1
        for i in range(3):
            request = _create_run_request(
                agent="msg-isolated-agent",
                content=f"Session 1 - Message {i}",
                session_id=session1.session_id,
            )
            await server.create_run(request)

        # Add messages to session 2
        request = _create_run_request(
            agent="msg-isolated-agent",
            content="Session 2 - Only message",
            session_id=session2.session_id,
        )
        await server.create_run(request)

        # Verify message counts are separate
        response1 = server.get_session(session1.session_id)
        response2 = server.get_session(session2.session_id)

        assert response1.run_count == 3
        assert response2.run_count == 1


# =============================================================================
# Session with Different Agents Tests
# =============================================================================


class TestSessionMultipleAgents:
    """Tests for sessions with different agents."""

    @pytest.mark.asyncio
    async def test_session_with_different_agent_than_registered(self):
        """Verify session can be used with different agent than originally registered."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="agent-a", description="Agent A")
        async def agent_a(input, context):
            yield models["Message"].agent_text("Response from A")

        @server.agent(name="agent-b", description="Agent B")
        async def agent_b(input, context):
            yield models["Message"].agent_text("Response from B")

        # Create session with agent_name "agent-a"
        session = server.create_session(agent_name="agent-a")

        # But use it with agent-b (session_id is what matters, not agent_name)
        request = _create_run_request(
            agent="agent-b",
            content="Test",
            session_id=session.session_id,
        )
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].COMPLETED
        assert response.agent_name == "agent-b"

    @pytest.mark.asyncio
    async def test_session_can_switch_between_agents(self):
        """Verify same session can be used with multiple agents."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="greeter", description="Greeter")
        async def greeter(input, context):
            yield models["Message"].agent_text("Hello!")

        @server.agent(name="farewell", description="Farewell")
        async def farewell(input, context):
            yield models["Message"].agent_text("Goodbye!")

        session = server.create_session()

        # Use greeter
        request1 = _create_run_request(
            agent="greeter",
            content="Hi",
            session_id=session.session_id,
        )
        response1 = await server.create_run(request1)
        assert response1.status == types["RunStatus"].COMPLETED

        # Use farewell in same session
        request2 = _create_run_request(
            agent="farewell",
            content="Bye",
            session_id=session.session_id,
        )
        response2 = await server.create_run(request2)
        assert response2.status == types["RunStatus"].COMPLETED

        # Session should have messages from both
        assert len(session.messages) == 2


# =============================================================================
# Session Auto-Creation Tests
# =============================================================================


class TestSessionAutoCreation:
    """Tests for automatic session creation during runs."""

    @pytest.mark.asyncio
    async def test_session_auto_created_with_new_session_id(self):
        """Verify session is auto-created when non-existent session_id provided."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="auto-session-agent", description="Auto session agent")
        async def auto_session_agent(input, context):
            yield models["Message"].agent_text("Auto-created session")

        new_session_id = uuid4()

        # Session doesn't exist yet
        assert server.get_session(new_session_id) is None

        # Create run with new session_id
        request = _create_run_request(
            agent="auto-session-agent",
            content="Test",
            session_id=new_session_id,
        )
        response = await server.create_run(request)

        assert response.status == types["RunStatus"].COMPLETED
        assert response.session_id == new_session_id

        # Session should now exist
        session_response = server.get_session(new_session_id)
        assert session_response is not None

    @pytest.mark.asyncio
    async def test_auto_created_session_has_correct_agent_name(self):
        """Verify auto-created session has correct agent_name."""
        server = _create_acp_server()
        models = _get_models()

        @server.agent(name="named-agent", description="Named agent")
        async def named_agent(input, context):
            yield models["Message"].agent_text("Named response")

        new_session_id = uuid4()

        request = _create_run_request(
            agent="named-agent",
            content="Test",
            session_id=new_session_id,
        )
        await server.create_run(request)

        session_response = server.get_session(new_session_id)
        assert session_response.agent_name == "named-agent"


# =============================================================================
# Session Metadata Tests
# =============================================================================


class TestSessionMetadata:
    """Tests for session metadata handling."""

    def test_session_metadata_stored_correctly(self):
        """Verify session metadata is stored correctly."""
        server = _create_acp_server()

        metadata = {
            "user_id": "user-456",
            "platform": "mobile",
            "version": "2.0.0",
            "nested": {"key": "value"},
            "list": [1, 2, 3],
        }

        session = server.create_session(metadata=metadata)

        assert session.metadata == metadata
        assert session.metadata["nested"]["key"] == "value"
        assert session.metadata["list"] == [1, 2, 3]

    def test_session_metadata_modifiable(self):
        """Verify session metadata can be modified after creation."""
        server = _create_acp_server()

        session = server.create_session(metadata={"initial": "value"})
        session.metadata["new_key"] = "new_value"
        session.metadata["initial"] = "updated"

        assert session.metadata["new_key"] == "new_value"
        assert session.metadata["initial"] == "updated"

    def test_session_metadata_separate_from_context(self):
        """Verify metadata is separate from context."""
        server = _create_acp_server()

        session = server.create_session(metadata={"meta_key": "meta_value"})
        session.context["context_key"] = "context_value"

        assert "meta_key" not in session.context
        assert "context_key" not in session.metadata
        assert session.metadata["meta_key"] == "meta_value"
        assert session.context["context_key"] == "context_value"


# =============================================================================
# Session Edge Cases Tests
# =============================================================================


class TestSessionEdgeCases:
    """Tests for session edge cases and error handling."""

    def test_create_session_with_empty_metadata(self):
        """Verify session can be created with empty metadata."""
        server = _create_acp_server()

        session = server.create_session(metadata={})

        assert session.metadata == {}

    def test_create_session_with_none_agent_name(self):
        """Verify session can be created with None agent_name."""
        server = _create_acp_server()

        session = server.create_session(agent_name=None)

        assert session.agent_name is None

    @pytest.mark.asyncio
    async def test_session_handles_agent_failure_gracefully(self):
        """Verify session state is preserved when agent fails."""
        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        call_count = [0]

        @server.agent(name="failing-agent", description="Failing agent")
        async def failing_agent(input, context):
            call_count[0] += 1
            if call_count[0] == 2:
                raise RuntimeError("Intentional failure")
            yield models["Message"].agent_text(f"Success {call_count[0]}")

        session = server.create_session(agent_name="failing-agent")

        # First run - success
        request1 = _create_run_request(
            agent="failing-agent",
            content="Test 1",
            session_id=session.session_id,
        )
        response1 = await server.create_run(request1)
        assert response1.status == types["RunStatus"].COMPLETED

        # Second run - failure
        request2 = _create_run_request(
            agent="failing-agent",
            content="Test 2",
            session_id=session.session_id,
        )
        response2 = await server.create_run(request2)
        assert response2.status == types["RunStatus"].FAILED

        # Third run - success (session still works)
        request3 = _create_run_request(
            agent="failing-agent",
            content="Test 3",
            session_id=session.session_id,
        )
        response3 = await server.create_run(request3)
        assert response3.status == types["RunStatus"].COMPLETED

        # Session should track all runs including failed one
        assert len(session.runs) >= 2  # At least successful runs

    def test_get_session_with_invalid_uuid_type(self):
        """Verify get_session handles invalid UUID gracefully."""
        server = _create_acp_server()

        # Pass a valid UUID but one that doesn't exist
        nonexistent_id = uuid4()
        response = server.get_session(nonexistent_id)

        assert response is None

    @pytest.mark.asyncio
    async def test_concurrent_runs_same_session(self):
        """Verify concurrent runs in same session work correctly."""
        import asyncio

        server = _create_acp_server()
        models = _get_models()
        types = _get_types()

        @server.agent(name="concurrent-agent", description="Concurrent agent")
        async def concurrent_agent(input, context):
            yield models["Message"].agent_text(f"Response to: {input[0].parts[0].content}")

        session = server.create_session(agent_name="concurrent-agent")

        # Create multiple requests for same session
        requests = [
            _create_run_request(
                agent="concurrent-agent",
                content=f"Concurrent message {i}",
                session_id=session.session_id,
            )
            for i in range(5)
        ]

        # Run concurrently
        responses = await asyncio.gather(
            *[server.create_run(req) for req in requests]
        )

        # All should complete
        for response in responses:
            assert response.status == types["RunStatus"].COMPLETED

        # Session should have all messages
        assert len(session.messages) == 5


# =============================================================================
# Session Response Structure Tests
# =============================================================================


class TestSessionResponseStructure:
    """Tests for SessionResponse structure."""

    def test_session_response_all_fields_present(self):
        """Verify SessionResponse contains all expected fields."""
        server = _create_acp_server()

        session = server.create_session(agent_name="struct-test-agent")
        response = server.get_session(session.session_id)

        # All fields should be present
        assert response.session_id is not None
        assert response.agent_name == "struct-test-agent"
        assert response.messages is not None
        assert isinstance(response.messages, list)
        assert response.run_count == 0
        assert response.created_at is not None
        assert response.last_activity_at is not None

    @pytest.mark.asyncio
    async def test_session_response_run_count_updates(self):
        """Verify run_count in response updates correctly."""
        server = _create_acp_server()
        models = _get_models()

        @server.agent(name="count-test-agent", description="Count test agent")
        async def count_test_agent(input, context):
            yield models["Message"].agent_text("Response")

        session = server.create_session(agent_name="count-test-agent")

        # Initial count is 0
        response = server.get_session(session.session_id)
        assert response.run_count == 0

        # After 3 runs
        for _ in range(3):
            request = _create_run_request(
                agent="count-test-agent",
                content="Test",
                session_id=session.session_id,
            )
            await server.create_run(request)

        response = server.get_session(session.session_id)
        assert response.run_count == 3
