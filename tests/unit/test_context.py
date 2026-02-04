"""
Unit tests for ACP Server Context.

Tests cover:
- Context: Execution context for agent handlers
- ContextBuilder: Builder pattern for creating Context objects
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest


# =============================================================================
# Helper Functions for Lazy Imports
# =============================================================================

def _get_types():
    """Lazy import of ACP types module."""
    from app.acp.core.types import (
        RunStatus,
        RunMode,
        ContentEncoding,
        MessageRole,
    )
    return {
        "RunStatus": RunStatus,
        "RunMode": RunMode,
        "ContentEncoding": ContentEncoding,
        "MessageRole": MessageRole,
    }


def _get_models():
    """Lazy import of ACP models module."""
    from app.acp.core.models import (
        MessagePart,
        Message,
        Run,
        Session,
        AwaitRequest,
    )
    return {
        "MessagePart": MessagePart,
        "Message": Message,
        "Run": Run,
        "Session": Session,
        "AwaitRequest": AwaitRequest,
    }


def _get_context():
    """Lazy import of Context and ContextBuilder."""
    from app.acp.server.context import Context, ContextBuilder
    return {
        "Context": Context,
        "ContextBuilder": ContextBuilder,
    }


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_run():
    """Create a sample Run for testing."""
    models = _get_models()
    types = _get_types()

    return models["Run"](
        agent_name="test-agent",
        input=[models["Message"].user_text("Hello, agent!")],
        metadata={"user_id": "user-123", "request_source": "api"},
    )


@pytest.fixture
def sample_run_with_session_id():
    """Create a Run with session_id."""
    models = _get_models()
    types = _get_types()

    session_id = uuid4()
    return models["Run"](
        agent_name="test-agent",
        session_id=session_id,
        input=[models["Message"].user_text("Hello!")],
    )


@pytest.fixture
def sample_session():
    """Create a sample Session for testing."""
    models = _get_models()
    types = _get_types()

    return models["Session"](
        agent_name="test-agent",
        messages=[
            models["Message"].user_text("Hello!"),
            models["Message"].agent_text("Hi! How can I help?"),
            models["Message"].user_text("Tell me about ACP."),
        ],
        context={"language": "en", "user_preference": "detailed"},
    )


@pytest.fixture
def sample_session_empty():
    """Create an empty Session for testing."""
    models = _get_models()

    return models["Session"](
        agent_name="test-agent",
        messages=[],
        context={},
    )


# =============================================================================
# Context Tests - Initialization
# =============================================================================

class TestContextInitialization:
    """Tests for Context initialization."""

    def test_context_creation_with_run_only(self, sample_run):
        """Verify Context can be created with only a Run."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        assert ctx._run == sample_run
        assert ctx._session is None
        assert ctx._metadata == {}
        assert ctx._intermediate_outputs == []

    def test_context_creation_with_run_and_session(self, sample_run, sample_session):
        """Verify Context can be created with Run and Session."""
        context_module = _get_context()

        ctx = context_module["Context"](
            run=sample_run,
            session=sample_session,
        )

        assert ctx._run == sample_run
        assert ctx._session == sample_session

    def test_context_creation_with_metadata(self, sample_run):
        """Verify Context can be created with metadata."""
        context_module = _get_context()

        metadata = {"custom_key": "custom_value", "request_id": "req-123"}

        ctx = context_module["Context"](
            run=sample_run,
            metadata=metadata,
        )

        assert ctx._metadata == metadata
        assert ctx._metadata["custom_key"] == "custom_value"

    def test_context_creation_with_none_metadata(self, sample_run):
        """Verify Context handles None metadata gracefully."""
        context_module = _get_context()

        ctx = context_module["Context"](
            run=sample_run,
            metadata=None,
        )

        assert ctx._metadata == {}

    def test_context_creation_with_all_parameters(self, sample_run, sample_session):
        """Verify Context can be created with all parameters."""
        context_module = _get_context()

        metadata = {"key": "value"}

        ctx = context_module["Context"](
            run=sample_run,
            session=sample_session,
            metadata=metadata,
        )

        assert ctx._run == sample_run
        assert ctx._session == sample_session
        assert ctx._metadata == metadata
        assert ctx._intermediate_outputs == []


# =============================================================================
# Context Tests - Properties
# =============================================================================

class TestContextProperties:
    """Tests for Context properties."""

    def test_run_id_property(self, sample_run):
        """Verify run_id property returns correct value."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        assert ctx.run_id == sample_run.run_id
        assert isinstance(ctx.run_id, UUID)

    def test_session_id_property_with_session(self, sample_run_with_session_id):
        """Verify session_id property when session_id exists on run."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run_with_session_id)

        assert ctx.session_id == sample_run_with_session_id.session_id
        assert isinstance(ctx.session_id, UUID)

    def test_session_id_property_without_session(self, sample_run):
        """Verify session_id property returns None when no session_id on run."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        assert ctx.session_id is None

    def test_agent_name_property(self, sample_run):
        """Verify agent_name property returns correct value."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        assert ctx.agent_name == "test-agent"

    def test_run_property(self, sample_run):
        """Verify run property returns the full Run object."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        assert ctx.run == sample_run
        assert ctx.run.agent_name == "test-agent"

    def test_session_property_with_session(self, sample_run, sample_session):
        """Verify session property returns Session when present."""
        context_module = _get_context()

        ctx = context_module["Context"](
            run=sample_run,
            session=sample_session,
        )

        assert ctx.session == sample_session
        assert ctx.session.agent_name == "test-agent"

    def test_session_property_without_session(self, sample_run):
        """Verify session property returns None when no session."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        assert ctx.session is None

    def test_metadata_property(self, sample_run):
        """Verify metadata property returns correct value."""
        context_module = _get_context()

        metadata = {"key1": "value1", "key2": "value2"}
        ctx = context_module["Context"](run=sample_run, metadata=metadata)

        assert ctx.metadata == metadata
        assert ctx.metadata["key1"] == "value1"

    def test_messages_property_with_session(self, sample_run, sample_session):
        """Verify messages property returns session messages when session exists."""
        context_module = _get_context()

        ctx = context_module["Context"](
            run=sample_run,
            session=sample_session,
        )

        assert ctx.messages == sample_session.messages
        assert len(ctx.messages) == 3

    def test_messages_property_without_session(self, sample_run):
        """Verify messages property returns run input when no session."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        assert ctx.messages == sample_run.input
        assert len(ctx.messages) == 1

    def test_intermediate_outputs_property_initially_empty(self, sample_run):
        """Verify intermediate_outputs is initially empty."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        assert ctx.intermediate_outputs == []
        assert len(ctx.intermediate_outputs) == 0


# =============================================================================
# Context Tests - get_context_value
# =============================================================================

class TestContextGetContextValue:
    """Tests for Context.get_context_value method."""

    def test_get_context_value_from_run_metadata(self, sample_run):
        """Verify get_context_value retrieves from run metadata first."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        assert ctx.get_context_value("user_id") == "user-123"
        assert ctx.get_context_value("request_source") == "api"

    def test_get_context_value_from_session_context(self, sample_run, sample_session):
        """Verify get_context_value retrieves from session context."""
        context_module = _get_context()

        ctx = context_module["Context"](
            run=sample_run,
            session=sample_session,
        )

        assert ctx.get_context_value("language") == "en"
        assert ctx.get_context_value("user_preference") == "detailed"

    def test_get_context_value_from_context_metadata(self, sample_run):
        """Verify get_context_value retrieves from context metadata."""
        context_module = _get_context()

        metadata = {"custom_setting": "enabled"}
        ctx = context_module["Context"](run=sample_run, metadata=metadata)

        assert ctx.get_context_value("custom_setting") == "enabled"

    def test_get_context_value_priority_run_over_session(self, sample_session):
        """Verify run metadata takes priority over session context."""
        models = _get_models()
        context_module = _get_context()

        # Create run with metadata that has same key as session context
        run = models["Run"](
            agent_name="test-agent",
            metadata={"language": "fr"},  # Same key as session context
        )

        ctx = context_module["Context"](
            run=run,
            session=sample_session,  # Has language: "en"
        )

        # Run metadata should take priority
        assert ctx.get_context_value("language") == "fr"

    def test_get_context_value_priority_session_over_metadata(self):
        """Verify session context takes priority over context metadata."""
        models = _get_models()
        context_module = _get_context()

        run = models["Run"](agent_name="test-agent")
        session = models["Session"](
            agent_name="test-agent",
            context={"setting": "from_session"},
        )
        metadata = {"setting": "from_metadata"}

        ctx = context_module["Context"](
            run=run,
            session=session,
            metadata=metadata,
        )

        # Session context should take priority over context metadata
        assert ctx.get_context_value("setting") == "from_session"

    def test_get_context_value_default_when_not_found(self, sample_run):
        """Verify get_context_value returns default when key not found."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        assert ctx.get_context_value("nonexistent") is None
        assert ctx.get_context_value("nonexistent", "default_value") == "default_value"

    def test_get_context_value_with_none_values(self):
        """Verify get_context_value correctly returns None values stored in context."""
        models = _get_models()
        context_module = _get_context()

        run = models["Run"](
            agent_name="test-agent",
            metadata={"null_value": None},
        )

        ctx = context_module["Context"](run=run)

        # The key exists but value is None
        assert ctx.get_context_value("null_value") is None
        # With a default, it should still return None because key exists
        # Note: This tests current behavior - the value None is returned because key exists
        assert ctx.get_context_value("null_value", "default") is None


# =============================================================================
# Context Tests - set_context_value
# =============================================================================

class TestContextSetContextValue:
    """Tests for Context.set_context_value method."""

    def test_set_context_value_with_session(self, sample_run, sample_session):
        """Verify set_context_value stores in session context when session exists."""
        context_module = _get_context()

        ctx = context_module["Context"](
            run=sample_run,
            session=sample_session,
        )

        ctx.set_context_value("new_key", "new_value")

        assert sample_session.context["new_key"] == "new_value"

    def test_set_context_value_without_session(self, sample_run):
        """Verify set_context_value stores in context metadata when no session."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        ctx.set_context_value("new_key", "new_value")

        assert ctx._metadata["new_key"] == "new_value"

    def test_set_context_value_overwrites_existing(self, sample_run, sample_session):
        """Verify set_context_value can overwrite existing values."""
        context_module = _get_context()

        ctx = context_module["Context"](
            run=sample_run,
            session=sample_session,
        )

        ctx.set_context_value("language", "fr")

        assert sample_session.context["language"] == "fr"

    def test_set_context_value_with_complex_value(self, sample_run, sample_session):
        """Verify set_context_value handles complex values."""
        context_module = _get_context()

        ctx = context_module["Context"](
            run=sample_run,
            session=sample_session,
        )

        complex_value = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "number": 42,
        }

        ctx.set_context_value("complex", complex_value)

        assert sample_session.context["complex"] == complex_value
        assert sample_session.context["complex"]["nested"]["key"] == "value"


# =============================================================================
# Context Tests - add_intermediate_output
# =============================================================================

class TestContextAddIntermediateOutput:
    """Tests for Context.add_intermediate_output method."""

    def test_add_intermediate_output_single_message(self, sample_run):
        """Verify add_intermediate_output adds a single message."""
        models = _get_models()
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        message = models["Message"].agent_text("Processing...")
        ctx.add_intermediate_output(message)

        assert len(ctx.intermediate_outputs) == 1
        assert ctx.intermediate_outputs[0] == message

    def test_add_intermediate_output_multiple_messages(self, sample_run):
        """Verify add_intermediate_output can add multiple messages."""
        models = _get_models()
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        msg1 = models["Message"].agent_text("Step 1...")
        msg2 = models["Message"].agent_text("Step 2...")
        msg3 = models["Message"].agent_text("Step 3...")

        ctx.add_intermediate_output(msg1)
        ctx.add_intermediate_output(msg2)
        ctx.add_intermediate_output(msg3)

        assert len(ctx.intermediate_outputs) == 3
        assert ctx.intermediate_outputs[0].parts[0].content == "Step 1..."
        assert ctx.intermediate_outputs[1].parts[0].content == "Step 2..."
        assert ctx.intermediate_outputs[2].parts[0].content == "Step 3..."

    def test_add_intermediate_output_preserves_order(self, sample_run):
        """Verify intermediate outputs maintain insertion order."""
        models = _get_models()
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        for i in range(5):
            msg = models["Message"].agent_text(f"Message {i}")
            ctx.add_intermediate_output(msg)

        for i in range(5):
            assert ctx.intermediate_outputs[i].parts[0].content == f"Message {i}"


# =============================================================================
# Context Tests - create_await_request
# =============================================================================

class TestContextCreateAwaitRequest:
    """Tests for Context.create_await_request method."""

    def test_create_await_request_minimal(self, sample_run):
        """Verify create_await_request with minimal parameters."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        await_req = ctx.create_await_request(await_type="user_confirmation")

        assert await_req.type == "user_confirmation"
        assert await_req.description is None
        assert await_req.schema_ is None
        assert await_req.timeout_seconds is None

    def test_create_await_request_with_description(self, sample_run):
        """Verify create_await_request with description."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        await_req = ctx.create_await_request(
            await_type="additional_info",
            description="Please provide your email address",
        )

        assert await_req.type == "additional_info"
        assert await_req.description == "Please provide your email address"

    def test_create_await_request_with_schema(self, sample_run):
        """Verify create_await_request with JSON schema."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        schema = {
            "type": "object",
            "properties": {
                "confirmed": {"type": "boolean"},
                "reason": {"type": "string"},
            },
            "required": ["confirmed"],
        }

        await_req = ctx.create_await_request(
            await_type="user_confirmation",
            schema=schema,
        )

        assert await_req.schema_ == schema

    def test_create_await_request_with_timeout(self, sample_run):
        """Verify create_await_request with timeout."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        await_req = ctx.create_await_request(
            await_type="user_input",
            timeout_seconds=300,
        )

        assert await_req.timeout_seconds == 300

    def test_create_await_request_with_all_parameters(self, sample_run):
        """Verify create_await_request with all parameters."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        schema = {"type": "string"}

        await_req = ctx.create_await_request(
            await_type="document_upload",
            description="Please upload the required document",
            schema=schema,
            timeout_seconds=600,
        )

        assert await_req.type == "document_upload"
        assert await_req.description == "Please upload the required document"
        assert await_req.schema_ == schema
        assert await_req.timeout_seconds == 600


# =============================================================================
# Context Tests - get_last_user_message
# =============================================================================

class TestContextGetLastUserMessage:
    """Tests for Context.get_last_user_message method."""

    def test_get_last_user_message_from_session(self, sample_run, sample_session):
        """Verify get_last_user_message returns last user message from session."""
        context_module = _get_context()
        types = _get_types()

        ctx = context_module["Context"](
            run=sample_run,
            session=sample_session,
        )

        last_user_msg = ctx.get_last_user_message()

        assert last_user_msg is not None
        assert last_user_msg.role == types["MessageRole"].USER
        assert last_user_msg.parts[0].content == "Tell me about ACP."

    def test_get_last_user_message_from_run_input(self, sample_run):
        """Verify get_last_user_message returns from run input when no session."""
        context_module = _get_context()
        types = _get_types()

        ctx = context_module["Context"](run=sample_run)

        last_user_msg = ctx.get_last_user_message()

        assert last_user_msg is not None
        assert last_user_msg.role == types["MessageRole"].USER
        assert last_user_msg.parts[0].content == "Hello, agent!"

    def test_get_last_user_message_with_no_user_messages(self):
        """Verify get_last_user_message returns None when no user messages."""
        models = _get_models()
        context_module = _get_context()
        types = _get_types()

        run = models["Run"](
            agent_name="test-agent",
            input=[models["Message"].agent_text("Agent message only")],
        )

        ctx = context_module["Context"](run=run)

        assert ctx.get_last_user_message() is None

    def test_get_last_user_message_with_empty_messages(self, sample_run, sample_session_empty):
        """Verify get_last_user_message returns None when messages are empty."""
        context_module = _get_context()

        ctx = context_module["Context"](
            run=sample_run,
            session=sample_session_empty,
        )

        # Session has no messages, so should return None
        assert ctx.get_last_user_message() is None

    def test_get_last_user_message_mixed_conversation(self):
        """Verify get_last_user_message finds correct message in mixed conversation."""
        models = _get_models()
        context_module = _get_context()
        types = _get_types()

        session = models["Session"](
            agent_name="test-agent",
            messages=[
                models["Message"].user_text("First user message"),
                models["Message"].agent_text("Agent response"),
                models["Message"].user_text("Second user message"),
                models["Message"].agent_text("Another agent response"),
                models["Message"].agent_text("Yet another agent response"),
            ],
        )

        run = models["Run"](agent_name="test-agent")

        ctx = context_module["Context"](run=run, session=session)

        last_user_msg = ctx.get_last_user_message()

        assert last_user_msg is not None
        assert last_user_msg.parts[0].content == "Second user message"


# =============================================================================
# Context Tests - get_message_text
# =============================================================================

class TestContextGetMessageText:
    """Tests for Context.get_message_text method."""

    def test_get_message_text_single_part(self, sample_run):
        """Verify get_message_text extracts text from single part message."""
        models = _get_models()
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        message = models["Message"].user_text("Hello, World!")
        text = ctx.get_message_text(message)

        assert text == "Hello, World!"

    def test_get_message_text_multiple_parts(self, sample_run):
        """Verify get_message_text concatenates text from multiple parts."""
        models = _get_models()
        context_module = _get_context()
        types = _get_types()

        ctx = context_module["Context"](run=sample_run)

        message = models["Message"](
            role=types["MessageRole"].USER,
            parts=[
                models["MessagePart"](content="First part.", content_type="text/plain"),
                models["MessagePart"](content="Second part.", content_type="text/plain"),
                models["MessagePart"](content="Third part.", content_type="text/plain"),
            ],
        )

        text = ctx.get_message_text(message)

        assert text == "First part.\nSecond part.\nThird part."

    def test_get_message_text_ignores_non_text_parts(self, sample_run):
        """Verify get_message_text ignores non-text/plain parts."""
        models = _get_models()
        context_module = _get_context()
        types = _get_types()

        ctx = context_module["Context"](run=sample_run)

        message = models["Message"](
            role=types["MessageRole"].USER,
            parts=[
                models["MessagePart"](content="Text content", content_type="text/plain"),
                models["MessagePart"](content_url="https://example.com/image.png", content_type="image/png"),
                models["MessagePart"](content='{"key": "value"}', content_type="application/json"),
            ],
        )

        text = ctx.get_message_text(message)

        assert text == "Text content"

    def test_get_message_text_empty_message(self, sample_run):
        """Verify get_message_text handles message with no parts."""
        models = _get_models()
        context_module = _get_context()
        types = _get_types()

        ctx = context_module["Context"](run=sample_run)

        message = models["Message"](
            role=types["MessageRole"].USER,
            parts=[],
        )

        text = ctx.get_message_text(message)

        assert text == ""

    def test_get_message_text_with_none_content(self, sample_run):
        """Verify get_message_text handles parts with None content."""
        models = _get_models()
        context_module = _get_context()
        types = _get_types()

        ctx = context_module["Context"](run=sample_run)

        message = models["Message"](
            role=types["MessageRole"].USER,
            parts=[
                models["MessagePart"](content=None, content_type="text/plain"),
                models["MessagePart"](content="Valid content", content_type="text/plain"),
            ],
        )

        text = ctx.get_message_text(message)

        # Should only include the valid content
        assert text == "Valid content"


# =============================================================================
# Context Tests - update_session_activity
# =============================================================================

class TestContextUpdateSessionActivity:
    """Tests for Context.update_session_activity method."""

    def test_update_session_activity_with_session(self, sample_run, sample_session):
        """Verify update_session_activity updates session timestamp."""
        context_module = _get_context()

        ctx = context_module["Context"](
            run=sample_run,
            session=sample_session,
        )

        old_activity = sample_session.last_activity_at

        # Small delay to ensure timestamp changes
        import time
        time.sleep(0.001)

        ctx.update_session_activity()

        assert sample_session.last_activity_at >= old_activity

    def test_update_session_activity_without_session(self, sample_run):
        """Verify update_session_activity does nothing when no session."""
        context_module = _get_context()

        ctx = context_module["Context"](run=sample_run)

        # Should not raise any exception
        ctx.update_session_activity()

        # No assertion needed - just verify no exception


# =============================================================================
# ContextBuilder Tests - Initialization
# =============================================================================

class TestContextBuilderInitialization:
    """Tests for ContextBuilder initialization."""

    def test_context_builder_initialization(self):
        """Verify ContextBuilder initializes with None/empty values."""
        context_module = _get_context()

        builder = context_module["ContextBuilder"]()

        assert builder._run is None
        assert builder._session is None
        assert builder._metadata == {}


# =============================================================================
# ContextBuilder Tests - Builder Methods
# =============================================================================

class TestContextBuilderMethods:
    """Tests for ContextBuilder builder methods."""

    def test_with_run(self, sample_run):
        """Verify with_run sets the run and returns builder."""
        context_module = _get_context()

        builder = context_module["ContextBuilder"]()
        result = builder.with_run(sample_run)

        assert builder._run == sample_run
        assert result is builder  # Returns self for chaining

    def test_with_session(self, sample_session):
        """Verify with_session sets the session and returns builder."""
        context_module = _get_context()

        builder = context_module["ContextBuilder"]()
        result = builder.with_session(sample_session)

        assert builder._session == sample_session
        assert result is builder

    def test_with_metadata(self):
        """Verify with_metadata sets metadata and returns builder."""
        context_module = _get_context()

        metadata = {"key": "value", "number": 42}

        builder = context_module["ContextBuilder"]()
        result = builder.with_metadata(metadata)

        assert builder._metadata == metadata
        assert result is builder

    def test_with_metadata_replaces_existing(self):
        """Verify with_metadata replaces existing metadata."""
        context_module = _get_context()

        builder = context_module["ContextBuilder"]()
        builder.with_metadata({"old": "value"})
        builder.with_metadata({"new": "value"})

        assert builder._metadata == {"new": "value"}
        assert "old" not in builder._metadata

    def test_add_metadata(self):
        """Verify add_metadata adds single entry and returns builder."""
        context_module = _get_context()

        builder = context_module["ContextBuilder"]()
        result = builder.add_metadata("key1", "value1")

        assert builder._metadata["key1"] == "value1"
        assert result is builder

    def test_add_metadata_multiple_entries(self):
        """Verify add_metadata can add multiple entries."""
        context_module = _get_context()

        builder = context_module["ContextBuilder"]()
        builder.add_metadata("key1", "value1")
        builder.add_metadata("key2", "value2")
        builder.add_metadata("key3", "value3")

        assert builder._metadata == {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        }

    def test_add_metadata_overwrites_existing_key(self):
        """Verify add_metadata overwrites existing key."""
        context_module = _get_context()

        builder = context_module["ContextBuilder"]()
        builder.add_metadata("key", "original")
        builder.add_metadata("key", "updated")

        assert builder._metadata["key"] == "updated"


# =============================================================================
# ContextBuilder Tests - Method Chaining
# =============================================================================

class TestContextBuilderChaining:
    """Tests for ContextBuilder method chaining."""

    def test_fluent_api_chaining(self, sample_run, sample_session):
        """Verify all builder methods support fluent chaining."""
        context_module = _get_context()

        builder = (
            context_module["ContextBuilder"]()
            .with_run(sample_run)
            .with_session(sample_session)
            .with_metadata({"base": "metadata"})
            .add_metadata("extra", "value")
        )

        assert builder._run == sample_run
        assert builder._session == sample_session
        assert builder._metadata == {"base": "metadata", "extra": "value"}

    def test_chaining_order_independence(self, sample_run, sample_session):
        """Verify chaining works regardless of order."""
        context_module = _get_context()

        builder = (
            context_module["ContextBuilder"]()
            .add_metadata("first", "value")
            .with_session(sample_session)
            .add_metadata("second", "value")
            .with_run(sample_run)
        )

        assert builder._run == sample_run
        assert builder._session == sample_session
        assert builder._metadata == {"first": "value", "second": "value"}


# =============================================================================
# ContextBuilder Tests - build() Method
# =============================================================================

class TestContextBuilderBuild:
    """Tests for ContextBuilder.build() method."""

    def test_build_with_run_only(self, sample_run):
        """Verify build creates Context with only run."""
        context_module = _get_context()

        ctx = (
            context_module["ContextBuilder"]()
            .with_run(sample_run)
            .build()
        )

        assert isinstance(ctx, context_module["Context"])
        assert ctx.run == sample_run
        assert ctx.session is None
        assert ctx.metadata == {}

    def test_build_with_all_fields(self, sample_run, sample_session):
        """Verify build creates Context with all fields."""
        context_module = _get_context()

        metadata = {"key": "value"}

        ctx = (
            context_module["ContextBuilder"]()
            .with_run(sample_run)
            .with_session(sample_session)
            .with_metadata(metadata)
            .build()
        )

        assert ctx.run == sample_run
        assert ctx.session == sample_session
        assert ctx.metadata == metadata

    def test_build_raises_without_run(self):
        """Verify build raises ValueError when run is not set."""
        context_module = _get_context()

        builder = context_module["ContextBuilder"]()

        with pytest.raises(ValueError, match="Run must be set"):
            builder.build()

    def test_build_raises_without_run_even_with_session(self, sample_session):
        """Verify build raises ValueError even if session is set but run is not."""
        context_module = _get_context()

        builder = (
            context_module["ContextBuilder"]()
            .with_session(sample_session)
            .with_metadata({"key": "value"})
        )

        with pytest.raises(ValueError, match="Run must be set"):
            builder.build()

    def test_build_creates_independent_context(self, sample_run):
        """Verify multiple build calls create independent Context objects."""
        context_module = _get_context()

        builder = (
            context_module["ContextBuilder"]()
            .with_run(sample_run)
        )

        ctx1 = builder.build()
        ctx2 = builder.build()

        # They should be separate instances
        assert ctx1 is not ctx2

        # But share the same run
        assert ctx1.run == ctx2.run


# =============================================================================
# Integration Tests
# =============================================================================

class TestContextIntegration:
    """Integration tests for Context and ContextBuilder."""

    def test_full_workflow_with_builder(self):
        """Test complete workflow using ContextBuilder."""
        models = _get_models()
        context_module = _get_context()
        types = _get_types()

        # Create session
        session = models["Session"](
            agent_name="integration-agent",
            messages=[
                models["Message"].user_text("What is 2+2?"),
            ],
            context={"difficulty": "easy"},
        )

        # Create run
        run = models["Run"](
            agent_name="integration-agent",
            session_id=session.session_id,
            input=session.messages,
            metadata={"source": "test"},
        )

        # Build context
        ctx = (
            context_module["ContextBuilder"]()
            .with_run(run)
            .with_session(session)
            .add_metadata("test_id", "integration-001")
            .build()
        )

        # Verify context properties
        assert ctx.agent_name == "integration-agent"
        assert ctx.session_id == session.session_id

        # Verify message access
        last_msg = ctx.get_last_user_message()
        assert last_msg.parts[0].content == "What is 2+2?"

        # Verify context value retrieval
        assert ctx.get_context_value("source") == "test"  # From run metadata
        assert ctx.get_context_value("difficulty") == "easy"  # From session context
        assert ctx.get_context_value("test_id") == "integration-001"  # From ctx metadata

        # Set new context value
        ctx.set_context_value("answer", "4")
        assert session.context["answer"] == "4"

        # Add intermediate output
        intermediate = models["Message"].agent_text("Thinking...")
        ctx.add_intermediate_output(intermediate)
        assert len(ctx.intermediate_outputs) == 1

        # Update session activity
        ctx.update_session_activity()
        assert session.last_activity_at is not None

    def test_context_without_session(self):
        """Test Context workflow without session."""
        models = _get_models()
        context_module = _get_context()

        run = models["Run"](
            agent_name="sessionless-agent",
            input=[models["Message"].user_text("One-shot question")],
            metadata={"mode": "one-shot"},
        )

        ctx = (
            context_module["ContextBuilder"]()
            .with_run(run)
            .add_metadata("request_id", "req-123")
            .build()
        )

        # Messages should come from run input
        assert len(ctx.messages) == 1
        assert ctx.messages[0].parts[0].content == "One-shot question"

        # Get last user message from run input
        last_msg = ctx.get_last_user_message()
        assert last_msg.parts[0].content == "One-shot question"

        # Context values should work
        assert ctx.get_context_value("mode") == "one-shot"
        assert ctx.get_context_value("request_id") == "req-123"

        # Set context value should use metadata
        ctx.set_context_value("response_time", 100)
        assert ctx._metadata["response_time"] == 100

    def test_await_request_creation(self):
        """Test creating and using await requests."""
        models = _get_models()
        context_module = _get_context()
        types = _get_types()

        run = models["Run"](agent_name="interactive-agent")

        ctx = (
            context_module["ContextBuilder"]()
            .with_run(run)
            .build()
        )

        # Create await request for human-in-the-loop
        await_req = ctx.create_await_request(
            await_type="approval",
            description="Please approve the generated content",
            schema={
                "type": "object",
                "properties": {
                    "approved": {"type": "boolean"},
                    "feedback": {"type": "string"},
                },
                "required": ["approved"],
            },
            timeout_seconds=3600,
        )

        # Verify await request
        assert await_req.type == "approval"
        assert await_req.description == "Please approve the generated content"
        assert await_req.timeout_seconds == 3600
        assert await_req.schema_["required"] == ["approved"]
