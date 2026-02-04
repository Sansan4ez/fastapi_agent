"""
Unit tests for client-side session management.

Tests cover:
- SessionManager operations (create, get, close, list sessions)
- LocalSession operations (messages, context, run tracking)
- Session lifecycle and state management
- Multi-session isolation
- SessionResponse conversion
- Edge cases and error handling
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4
import time

import pytest

from app.acp.client.session import SessionManager, LocalSession
from app.acp.core.models import Message
from app.acp.core.schemas import SessionResponse


# =============================================================================
# Fixed Test Data
# =============================================================================

FIXTURE_SESSION_ID = UUID("87654321-4321-8765-4321-876543218765")
FIXTURE_RUN_ID_1 = UUID("11111111-1111-1111-1111-111111111111")
FIXTURE_RUN_ID_2 = UUID("22222222-2222-2222-2222-222222222222")
FIXTURE_RUN_ID_3 = UUID("33333333-3333-3333-3333-333333333333")


# =============================================================================
# SessionManager Creation Tests
# =============================================================================


class TestSessionManagerCreation:
    """Tests for SessionManager session creation."""

    def test_create_session_basic(self):
        """Verify session can be created with minimal parameters."""
        manager = SessionManager()

        session = manager.create_session()

        assert session is not None
        assert isinstance(session.session_id, UUID)
        assert session.agent_name is None
        assert session.messages == []
        assert session.context == {}

    def test_create_session_with_agent_name(self):
        """Verify session can be created with agent name."""
        manager = SessionManager()

        session = manager.create_session(agent_name="test-agent")

        assert session.agent_name == "test-agent"

    def test_create_session_with_metadata(self):
        """Verify session can be created with metadata."""
        manager = SessionManager()

        metadata = {
            "user_id": "user-123",
            "channel": "web",
            "locale": "en-US",
        }

        session = manager.create_session(metadata=metadata)

        assert session._metadata == metadata

    def test_create_session_with_all_parameters(self):
        """Verify session can be created with all parameters."""
        manager = SessionManager()

        metadata = {"key": "value"}

        session = manager.create_session(
            agent_name="full-agent",
            metadata=metadata,
        )

        assert session.agent_name == "full-agent"
        assert session._metadata == metadata

    def test_create_multiple_sessions(self):
        """Verify multiple sessions can be created independently."""
        manager = SessionManager()

        session1 = manager.create_session(agent_name="agent-1")
        session2 = manager.create_session(agent_name="agent-2")
        session3 = manager.create_session(agent_name="agent-3")

        assert session1.session_id != session2.session_id
        assert session2.session_id != session3.session_id
        assert session1.session_id != session3.session_id

    def test_create_session_unique_ids(self):
        """Verify each created session has unique ID."""
        manager = SessionManager()
        session_ids = set()

        for _ in range(100):
            session = manager.create_session()
            assert session.session_id not in session_ids
            session_ids.add(session.session_id)

        assert len(session_ids) == 100

    def test_create_session_stored_in_manager(self):
        """Verify created session is stored in manager."""
        manager = SessionManager()

        session = manager.create_session(agent_name="stored-agent")

        retrieved = manager.get_session(session.session_id)
        assert retrieved is session


# =============================================================================
# SessionManager Retrieval Tests
# =============================================================================


class TestSessionManagerRetrieval:
    """Tests for SessionManager session retrieval."""

    def test_get_session_after_creation(self):
        """Verify session can be retrieved after creation."""
        manager = SessionManager()

        created_session = manager.create_session(agent_name="test-agent")
        retrieved = manager.get_session(created_session.session_id)

        assert retrieved is not None
        assert retrieved.session_id == created_session.session_id
        assert retrieved.agent_name == "test-agent"

    def test_get_session_not_found(self):
        """Verify None returned for nonexistent session."""
        manager = SessionManager()

        result = manager.get_session(uuid4())

        assert result is None

    def test_get_session_returns_same_instance(self):
        """Verify get_session returns the same session instance."""
        manager = SessionManager()

        session = manager.create_session(agent_name="test-agent")
        retrieved1 = manager.get_session(session.session_id)
        retrieved2 = manager.get_session(session.session_id)

        assert retrieved1 is retrieved2
        assert retrieved1 is session


# =============================================================================
# SessionManager Close Tests
# =============================================================================


class TestSessionManagerClose:
    """Tests for SessionManager session closing."""

    def test_close_session_success(self):
        """Verify session can be closed successfully."""
        manager = SessionManager()

        session = manager.create_session(agent_name="test-agent")
        result = manager.close_session(session.session_id)

        assert result is True
        assert manager.get_session(session.session_id) is None

    def test_close_session_nonexistent(self):
        """Verify closing nonexistent session returns False."""
        manager = SessionManager()

        result = manager.close_session(uuid4())

        assert result is False

    def test_close_session_removes_from_list(self):
        """Verify closed session is removed from session list."""
        manager = SessionManager()

        session1 = manager.create_session(agent_name="agent-1")
        session2 = manager.create_session(agent_name="agent-2")

        initial_count = len(manager.list_sessions())

        manager.close_session(session1.session_id)

        assert len(manager.list_sessions()) == initial_count - 1
        assert session2 in manager.list_sessions()


# =============================================================================
# SessionManager List Tests
# =============================================================================


class TestSessionManagerList:
    """Tests for SessionManager session listing."""

    def test_list_sessions_empty(self):
        """Verify list_sessions returns empty list when no sessions."""
        manager = SessionManager()

        result = manager.list_sessions()

        assert result == []

    def test_list_sessions_with_sessions(self):
        """Verify list_sessions returns all sessions."""
        manager = SessionManager()

        session1 = manager.create_session(agent_name="agent-1")
        session2 = manager.create_session(agent_name="agent-2")
        session3 = manager.create_session(agent_name="agent-3")

        result = manager.list_sessions()

        assert len(result) == 3
        assert session1 in result
        assert session2 in result
        assert session3 in result

    def test_get_sessions_for_agent(self):
        """Verify get_sessions_for_agent filters by agent name."""
        manager = SessionManager()

        manager.create_session(agent_name="agent-a")
        manager.create_session(agent_name="agent-a")
        manager.create_session(agent_name="agent-b")

        agent_a_sessions = manager.get_sessions_for_agent("agent-a")
        agent_b_sessions = manager.get_sessions_for_agent("agent-b")
        agent_c_sessions = manager.get_sessions_for_agent("agent-c")

        assert len(agent_a_sessions) == 2
        assert len(agent_b_sessions) == 1
        assert len(agent_c_sessions) == 0

    def test_get_sessions_for_agent_all_same_agent(self):
        """Verify all sessions returned when all have same agent."""
        manager = SessionManager()

        for _ in range(5):
            manager.create_session(agent_name="same-agent")

        result = manager.get_sessions_for_agent("same-agent")

        assert len(result) == 5


# =============================================================================
# LocalSession Initialization Tests
# =============================================================================


class TestLocalSessionInitialization:
    """Tests for LocalSession initialization."""

    def test_init_with_defaults(self):
        """Verify LocalSession initializes with default values."""
        session = LocalSession()

        assert isinstance(session.session_id, UUID)
        assert session.agent_name is None
        assert session.messages == []
        assert session.context == {}
        assert session.run_count == 0

    def test_init_with_session_id(self):
        """Verify LocalSession can be created with specific session ID."""
        session = LocalSession(session_id=FIXTURE_SESSION_ID)

        assert session.session_id == FIXTURE_SESSION_ID

    def test_init_with_agent_name(self):
        """Verify LocalSession can be created with agent name."""
        session = LocalSession(agent_name="test-agent")

        assert session.agent_name == "test-agent"

    def test_init_with_metadata(self):
        """Verify LocalSession can be created with metadata."""
        metadata = {"key": "value", "nested": {"inner": 123}}
        session = LocalSession(metadata=metadata)

        assert session._metadata == metadata

    def test_init_timestamps(self):
        """Verify LocalSession has proper timestamps on creation."""
        before = datetime.utcnow()
        session = LocalSession()
        after = datetime.utcnow()

        assert session.created_at is not None
        assert session.last_activity_at is not None
        assert before <= session.created_at <= after
        assert before <= session.last_activity_at <= after


# =============================================================================
# LocalSession Message Operations Tests
# =============================================================================


class TestLocalSessionMessages:
    """Tests for LocalSession message operations."""

    def test_add_message(self):
        """Verify single message can be added."""
        session = LocalSession()
        message = Message.user_text("Hello")

        session.add_message(message)

        assert len(session.messages) == 1
        assert session.messages[0] == message

    def test_add_multiple_messages_individually(self):
        """Verify multiple messages can be added individually."""
        session = LocalSession()

        msg1 = Message.user_text("Message 1")
        msg2 = Message.agent_text("Response 1")
        msg3 = Message.user_text("Message 2")

        session.add_message(msg1)
        session.add_message(msg2)
        session.add_message(msg3)

        assert len(session.messages) == 3
        assert session.messages[0] == msg1
        assert session.messages[1] == msg2
        assert session.messages[2] == msg3

    def test_add_messages_batch(self):
        """Verify multiple messages can be added in batch."""
        session = LocalSession()

        messages = [
            Message.user_text("Message 1"),
            Message.agent_text("Response 1"),
            Message.user_text("Message 2"),
        ]

        session.add_messages(messages)

        assert len(session.messages) == 3
        assert session.messages == messages

    def test_add_message_updates_last_activity(self):
        """Verify adding message updates last_activity_at."""
        session = LocalSession()
        initial_activity = session.last_activity_at

        time.sleep(0.01)  # Small delay

        session.add_message(Message.user_text("Hello"))

        assert session.last_activity_at > initial_activity

    def test_add_messages_updates_last_activity(self):
        """Verify adding messages in batch updates last_activity_at."""
        session = LocalSession()
        initial_activity = session.last_activity_at

        time.sleep(0.01)  # Small delay

        session.add_messages([Message.user_text("Hello")])

        assert session.last_activity_at > initial_activity

    def test_get_last_message_no_filter(self):
        """Verify get_last_message returns last message without filter."""
        session = LocalSession()

        session.add_message(Message.user_text("First"))
        session.add_message(Message.agent_text("Second"))
        session.add_message(Message.user_text("Third"))

        last = session.get_last_message()

        assert last is not None
        assert last.parts[0].content == "Third"

    def test_get_last_message_filter_by_role(self):
        """Verify get_last_message filters by role."""
        session = LocalSession()

        session.add_message(Message.user_text("User 1"))
        session.add_message(Message.agent_text("Agent 1"))
        session.add_message(Message.user_text("User 2"))
        session.add_message(Message.agent_text("Agent 2"))

        last_user = session.get_last_message(role="user")
        last_agent = session.get_last_message(role="agent")

        assert last_user is not None
        assert last_user.parts[0].content == "User 2"
        assert last_agent is not None
        assert last_agent.parts[0].content == "Agent 2"

    def test_get_last_message_empty_session(self):
        """Verify get_last_message returns None for empty session."""
        session = LocalSession()

        result = session.get_last_message()

        assert result is None

    def test_get_last_message_no_matching_role(self):
        """Verify get_last_message returns None when no matching role."""
        session = LocalSession()

        session.add_message(Message.user_text("User message"))

        result = session.get_last_message(role="agent")

        assert result is None

    def test_get_messages_since(self):
        """Verify get_messages_since returns last N messages."""
        session = LocalSession()

        for i in range(5):
            session.add_message(Message.user_text(f"Message {i}"))

        result = session.get_messages_since(3)

        assert len(result) == 3
        assert result[0].parts[0].content == "Message 2"
        assert result[1].parts[0].content == "Message 3"
        assert result[2].parts[0].content == "Message 4"

    def test_get_messages_since_more_than_available(self):
        """Verify get_messages_since handles count > available messages."""
        session = LocalSession()

        session.add_message(Message.user_text("Message 1"))
        session.add_message(Message.user_text("Message 2"))

        result = session.get_messages_since(10)

        assert len(result) == 2

    def test_get_messages_since_zero(self):
        """Verify get_messages_since with zero returns empty list."""
        session = LocalSession()

        session.add_message(Message.user_text("Message"))

        result = session.get_messages_since(0)

        assert result == []

    def test_clear_history(self):
        """Verify clear_history removes all messages."""
        session = LocalSession()

        session.add_message(Message.user_text("Message 1"))
        session.add_message(Message.user_text("Message 2"))

        session.clear_history()

        assert session.messages == []


# =============================================================================
# LocalSession Context Operations Tests
# =============================================================================


class TestLocalSessionContext:
    """Tests for LocalSession context operations."""

    def test_set_context_single_value(self):
        """Verify single context value can be set."""
        session = LocalSession()

        session.set_context("key", "value")

        assert session.context["key"] == "value"

    def test_set_context_multiple_values(self):
        """Verify multiple context values can be set."""
        session = LocalSession()

        session.set_context("key1", "value1")
        session.set_context("key2", 123)
        session.set_context("key3", {"nested": "value"})

        assert session.context["key1"] == "value1"
        assert session.context["key2"] == 123
        assert session.context["key3"] == {"nested": "value"}

    def test_set_context_overwrite(self):
        """Verify context value can be overwritten."""
        session = LocalSession()

        session.set_context("key", "initial")
        session.set_context("key", "updated")

        assert session.context["key"] == "updated"

    def test_get_context_existing(self):
        """Verify get_context returns existing value."""
        session = LocalSession()

        session.set_context("key", "value")
        result = session.get_context("key")

        assert result == "value"

    def test_get_context_nonexistent(self):
        """Verify get_context returns None for nonexistent key."""
        session = LocalSession()

        result = session.get_context("nonexistent")

        assert result is None

    def test_get_context_with_default(self):
        """Verify get_context returns default for nonexistent key."""
        session = LocalSession()

        result = session.get_context("nonexistent", default="default_value")

        assert result == "default_value"

    def test_get_context_default_not_used_when_exists(self):
        """Verify default is not used when key exists."""
        session = LocalSession()

        session.set_context("key", "actual_value")
        result = session.get_context("key", default="default_value")

        assert result == "actual_value"

    def test_clear_context(self):
        """Verify clear_context removes all context values."""
        session = LocalSession()

        session.set_context("key1", "value1")
        session.set_context("key2", "value2")

        session.clear_context()

        assert session.context == {}

    def test_context_property_returns_reference(self):
        """Verify context property returns reference to internal dict."""
        session = LocalSession()

        session.set_context("key", "value")
        context = session.context

        # Modifying returned context affects session
        context["new_key"] = "new_value"

        assert session.context["new_key"] == "new_value"


# =============================================================================
# LocalSession Run Tracking Tests
# =============================================================================


class TestLocalSessionRunTracking:
    """Tests for LocalSession run tracking."""

    def test_add_run(self):
        """Verify run ID can be added."""
        session = LocalSession()

        session.add_run(FIXTURE_RUN_ID_1)

        assert session.run_count == 1

    def test_add_multiple_runs(self):
        """Verify multiple run IDs can be added."""
        session = LocalSession()

        session.add_run(FIXTURE_RUN_ID_1)
        session.add_run(FIXTURE_RUN_ID_2)
        session.add_run(FIXTURE_RUN_ID_3)

        assert session.run_count == 3

    def test_add_run_updates_last_activity(self):
        """Verify adding run updates last_activity_at."""
        session = LocalSession()
        initial_activity = session.last_activity_at

        time.sleep(0.01)  # Small delay

        session.add_run(FIXTURE_RUN_ID_1)

        assert session.last_activity_at > initial_activity

    def test_run_count_starts_at_zero(self):
        """Verify run_count starts at zero."""
        session = LocalSession()

        assert session.run_count == 0


# =============================================================================
# LocalSession Timestamp Tests
# =============================================================================


class TestLocalSessionTimestamps:
    """Tests for LocalSession timestamp handling."""

    def test_created_at_immutable(self):
        """Verify created_at does not change after operations."""
        session = LocalSession()
        original_created_at = session.created_at

        session.add_message(Message.user_text("Test"))
        session.add_run(FIXTURE_RUN_ID_1)
        session.set_context("key", "value")

        assert session.created_at == original_created_at

    def test_last_activity_updates_on_add_message(self):
        """Verify last_activity_at updates on add_message."""
        session = LocalSession()
        initial = session.last_activity_at

        time.sleep(0.01)
        session.add_message(Message.user_text("Test"))

        assert session.last_activity_at > initial

    def test_last_activity_updates_on_add_messages(self):
        """Verify last_activity_at updates on add_messages."""
        session = LocalSession()
        initial = session.last_activity_at

        time.sleep(0.01)
        session.add_messages([Message.user_text("Test")])

        assert session.last_activity_at > initial

    def test_last_activity_updates_on_add_run(self):
        """Verify last_activity_at updates on add_run."""
        session = LocalSession()
        initial = session.last_activity_at

        time.sleep(0.01)
        session.add_run(FIXTURE_RUN_ID_1)

        assert session.last_activity_at > initial


# =============================================================================
# LocalSession Properties Tests
# =============================================================================


class TestLocalSessionProperties:
    """Tests for LocalSession property accessors."""

    def test_session_id_property(self):
        """Verify session_id property returns correct value."""
        session = LocalSession(session_id=FIXTURE_SESSION_ID)

        assert session.session_id == FIXTURE_SESSION_ID

    def test_agent_name_property(self):
        """Verify agent_name property returns correct value."""
        session = LocalSession(agent_name="test-agent")

        assert session.agent_name == "test-agent"

    def test_messages_property(self):
        """Verify messages property returns message list."""
        session = LocalSession()
        msg = Message.user_text("Test")
        session.add_message(msg)

        assert session.messages == [msg]

    def test_context_property(self):
        """Verify context property returns context dict."""
        session = LocalSession()
        session.set_context("key", "value")

        assert session.context == {"key": "value"}

    def test_run_count_property(self):
        """Verify run_count property returns correct count."""
        session = LocalSession()
        session.add_run(FIXTURE_RUN_ID_1)
        session.add_run(FIXTURE_RUN_ID_2)

        assert session.run_count == 2

    def test_created_at_property(self):
        """Verify created_at property returns datetime."""
        session = LocalSession()

        assert isinstance(session.created_at, datetime)

    def test_last_activity_at_property(self):
        """Verify last_activity_at property returns datetime."""
        session = LocalSession()

        assert isinstance(session.last_activity_at, datetime)


# =============================================================================
# LocalSession to SessionResponse Conversion Tests
# =============================================================================


class TestLocalSessionToSessionResponse:
    """Tests for LocalSession.to_session_response conversion."""

    def test_to_session_response_basic(self):
        """Verify basic conversion to SessionResponse."""
        session = LocalSession(
            session_id=FIXTURE_SESSION_ID,
            agent_name="test-agent",
        )

        response = session.to_session_response()

        assert isinstance(response, SessionResponse)
        assert response.session_id == FIXTURE_SESSION_ID
        assert response.agent_name == "test-agent"

    def test_to_session_response_with_messages(self):
        """Verify conversion includes messages."""
        session = LocalSession()
        session.add_message(Message.user_text("Message 1"))
        session.add_message(Message.agent_text("Response 1"))

        response = session.to_session_response()

        assert len(response.messages) == 2
        assert response.messages[0].parts[0].content == "Message 1"
        assert response.messages[1].parts[0].content == "Response 1"

    def test_to_session_response_run_count(self):
        """Verify conversion includes correct run count."""
        session = LocalSession()
        session.add_run(FIXTURE_RUN_ID_1)
        session.add_run(FIXTURE_RUN_ID_2)
        session.add_run(FIXTURE_RUN_ID_3)

        response = session.to_session_response()

        assert response.run_count == 3

    def test_to_session_response_timestamps(self):
        """Verify conversion includes timestamps."""
        session = LocalSession()

        response = session.to_session_response()

        assert response.created_at is not None
        assert response.last_activity_at is not None
        assert response.created_at == session.created_at
        assert response.last_activity_at == session.last_activity_at

    def test_to_session_response_no_agent(self):
        """Verify conversion works with no agent name."""
        session = LocalSession()

        response = session.to_session_response()

        assert response.agent_name is None


# =============================================================================
# Session Isolation Tests
# =============================================================================


class TestSessionIsolation:
    """Tests for session isolation."""

    def test_sessions_have_independent_messages(self):
        """Verify sessions have independent message lists."""
        manager = SessionManager()

        session1 = manager.create_session()
        session2 = manager.create_session()

        session1.add_message(Message.user_text("Session 1 message"))

        assert len(session1.messages) == 1
        assert len(session2.messages) == 0

    def test_sessions_have_independent_context(self):
        """Verify sessions have independent context."""
        manager = SessionManager()

        session1 = manager.create_session()
        session2 = manager.create_session()

        session1.set_context("key", "session1_value")
        session2.set_context("key", "session2_value")

        assert session1.get_context("key") == "session1_value"
        assert session2.get_context("key") == "session2_value"

    def test_sessions_have_independent_run_counts(self):
        """Verify sessions have independent run counts."""
        manager = SessionManager()

        session1 = manager.create_session()
        session2 = manager.create_session()

        session1.add_run(FIXTURE_RUN_ID_1)
        session1.add_run(FIXTURE_RUN_ID_2)
        session2.add_run(FIXTURE_RUN_ID_3)

        assert session1.run_count == 2
        assert session2.run_count == 1


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestSessionEdgeCases:
    """Tests for session edge cases."""

    def test_create_session_with_empty_metadata(self):
        """Verify session can be created with empty metadata."""
        manager = SessionManager()

        session = manager.create_session(metadata={})

        assert session._metadata == {}

    def test_create_session_with_none_metadata(self):
        """Verify session handles None metadata."""
        manager = SessionManager()

        session = manager.create_session(metadata=None)

        assert session._metadata == {}

    def test_session_with_none_agent_name(self):
        """Verify session handles None agent name."""
        session = LocalSession(agent_name=None)

        assert session.agent_name is None

    def test_context_with_none_value(self):
        """Verify context can store None values."""
        session = LocalSession()

        session.set_context("nullable_key", None)

        assert session.get_context("nullable_key") is None
        assert "nullable_key" in session.context

    def test_context_with_complex_types(self):
        """Verify context can store complex types."""
        session = LocalSession()

        complex_value: dict[str, Any] = {
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "tuple_as_list": [1, "two", 3.0],
        }

        session.set_context("complex", complex_value)

        assert session.get_context("complex") == complex_value

    def test_get_messages_since_negative(self):
        """Verify get_messages_since handles negative count."""
        session = LocalSession()
        session.add_message(Message.user_text("Test"))

        # Python's slice with negative returns empty list
        result = session.get_messages_since(-1)

        assert result == []

    def test_clear_empty_history(self):
        """Verify clearing empty history is safe."""
        session = LocalSession()

        session.clear_history()

        assert session.messages == []

    def test_clear_empty_context(self):
        """Verify clearing empty context is safe."""
        session = LocalSession()

        session.clear_context()

        assert session.context == {}


# =============================================================================
# Multi-Turn Conversation Tests
# =============================================================================


class TestMultiTurnConversation:
    """Tests for multi-turn conversation support."""

    def test_conversation_flow(self):
        """Verify typical multi-turn conversation flow."""
        session = LocalSession(agent_name="chat-agent")

        # Turn 1
        session.add_message(Message.user_text("Hello!"))
        session.add_message(Message.agent_text("Hi there! How can I help?"))
        session.add_run(FIXTURE_RUN_ID_1)

        # Turn 2
        session.add_message(Message.user_text("What's the weather?"))
        session.add_message(Message.agent_text("I can check that for you."))
        session.add_run(FIXTURE_RUN_ID_2)

        # Turn 3
        session.add_message(Message.user_text("Thanks!"))
        session.add_message(Message.agent_text("You're welcome!"))
        session.add_run(FIXTURE_RUN_ID_3)

        assert len(session.messages) == 6
        assert session.run_count == 3

        # Check last messages
        last_user = session.get_last_message(role="user")
        last_agent = session.get_last_message(role="agent")

        assert last_user.parts[0].content == "Thanks!"
        assert last_agent.parts[0].content == "You're welcome!"

    def test_conversation_with_context_accumulation(self):
        """Verify context accumulates across turns."""
        session = LocalSession()

        # Simulate context building across turns
        session.set_context("user_name", "Alice")
        session.add_message(Message.user_text("My name is Alice"))
        session.add_run(FIXTURE_RUN_ID_1)

        session.set_context("user_preference", "dark_mode")
        session.add_message(Message.user_text("I prefer dark mode"))
        session.add_run(FIXTURE_RUN_ID_2)

        session.set_context("last_topic", "settings")
        session.add_message(Message.user_text("Let's talk about settings"))
        session.add_run(FIXTURE_RUN_ID_3)

        assert session.get_context("user_name") == "Alice"
        assert session.get_context("user_preference") == "dark_mode"
        assert session.get_context("last_topic") == "settings"
        assert session.run_count == 3

    def test_recent_messages_window(self):
        """Verify getting recent messages for context window."""
        session = LocalSession()

        # Add 10 messages
        for i in range(10):
            session.add_message(Message.user_text(f"Message {i}"))

        # Get last 3 messages for context
        recent = session.get_messages_since(3)

        assert len(recent) == 3
        assert recent[0].parts[0].content == "Message 7"
        assert recent[1].parts[0].content == "Message 8"
        assert recent[2].parts[0].content == "Message 9"
