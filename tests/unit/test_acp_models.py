"""
Unit tests for ACP Core Models.

Tests cover:
- MessagePart: Message content parts with MIME types and encoding
- Message: Messages with roles and parts
- Run: Agent run lifecycle and state management
- Session: Session state and conversation history
- AgentManifest, AgentMetadata, RunError, AwaitRequest, CitationMetadata, TrajectoryMetadata
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError


# =============================================================================
# Helper Functions for Lazy Imports
# =============================================================================

def _get_types():
    """Lazy import of ACP types module."""
    from app.acp.core.types import (
        RunStatus,
        AgentStatus,
        RunMode,
        ContentEncoding,
        MessageRole,
        ErrorCode,
        MetadataType,
    )
    return {
        "RunStatus": RunStatus,
        "AgentStatus": AgentStatus,
        "RunMode": RunMode,
        "ContentEncoding": ContentEncoding,
        "MessageRole": MessageRole,
        "ErrorCode": ErrorCode,
        "MetadataType": MetadataType,
    }


def _get_models():
    """Lazy import of ACP models module."""
    from app.acp.core.models import (
        MessagePart,
        Message,
        AgentMetadata,
        AgentManifest,
        RunError,
        AwaitRequest,
        Run,
        Session,
        CitationMetadata,
        TrajectoryMetadata,
    )
    return {
        "MessagePart": MessagePart,
        "Message": Message,
        "AgentMetadata": AgentMetadata,
        "AgentManifest": AgentManifest,
        "RunError": RunError,
        "AwaitRequest": AwaitRequest,
        "Run": Run,
        "Session": Session,
        "CitationMetadata": CitationMetadata,
        "TrajectoryMetadata": TrajectoryMetadata,
    }


# =============================================================================
# MessagePart Tests
# =============================================================================

class TestMessagePart:
    """Tests for MessagePart model - message content parts."""

    def test_message_part_creation_with_content(self):
        """Verify MessagePart can be created with inline content."""
        models = _get_models()
        types = _get_types()

        part = models["MessagePart"](
            content="Hello, World!",
            content_type="text/plain",
        )

        assert part.content == "Hello, World!"
        assert part.content_type == "text/plain"
        assert part.content_encoding == types["ContentEncoding"].PLAIN
        assert part.content_url is None
        assert part.name is None
        assert part.metadata is None

    def test_message_part_creation_with_url(self):
        """Verify MessagePart can be created with content URL."""
        models = _get_models()

        part = models["MessagePart"](
            content_url="https://example.com/document.pdf",
            content_type="application/pdf",
            name="document.pdf",
        )

        assert part.content is None
        assert part.content_url == "https://example.com/document.pdf"
        assert part.content_type == "application/pdf"
        assert part.name == "document.pdf"

    def test_message_part_creation_with_base64_encoding(self):
        """Verify MessagePart can be created with base64 encoding."""
        models = _get_models()
        types = _get_types()

        # "Hello World!" in base64
        base64_content = "SGVsbG8gV29ybGQh"

        part = models["MessagePart"](
            content=base64_content,
            content_type="text/plain",
            content_encoding=types["ContentEncoding"].BASE64,
        )

        assert part.content == base64_content
        assert part.content_encoding == types["ContentEncoding"].BASE64

    def test_message_part_creation_with_metadata(self):
        """Verify MessagePart can be created with metadata."""
        models = _get_models()

        metadata = {
            "source": "https://example.com/paper",
            "title": "Research Paper",
            "author": "Dr. Smith",
        }

        part = models["MessagePart"](
            content="According to the research...",
            content_type="text/plain",
            metadata=metadata,
        )

        assert part.metadata == metadata
        assert part.metadata["source"] == "https://example.com/paper"

    def test_message_part_default_values(self):
        """Verify MessagePart default values."""
        models = _get_models()
        types = _get_types()

        part = models["MessagePart"]()

        assert part.content is None
        assert part.content_url is None
        assert part.content_type == "text/plain"
        assert part.content_encoding == types["ContentEncoding"].PLAIN
        assert part.name is None
        assert part.metadata is None

    def test_message_part_with_image_content_type(self):
        """Verify MessagePart works with image content types."""
        models = _get_models()

        part = models["MessagePart"](
            content_url="https://example.com/image.png",
            content_type="image/png",
            name="screenshot.png",
        )

        assert part.content_type == "image/png"
        assert part.name == "screenshot.png"

    def test_message_part_with_json_content_type(self):
        """Verify MessagePart works with JSON content types."""
        models = _get_models()

        json_content = json.dumps({"key": "value", "number": 42})

        part = models["MessagePart"](
            content=json_content,
            content_type="application/json",
        )

        assert part.content_type == "application/json"
        assert json.loads(part.content) == {"key": "value", "number": 42}

    def test_message_part_serialization(self):
        """Verify MessagePart can be serialized to dict."""
        models = _get_models()
        types = _get_types()

        part = models["MessagePart"](
            content="Test content",
            content_type="text/plain",
            content_encoding=types["ContentEncoding"].PLAIN,
        )

        data = part.model_dump()

        assert data["content"] == "Test content"
        assert data["content_type"] == "text/plain"
        assert data["content_encoding"] == "plain"

    def test_message_part_json_serialization(self):
        """Verify MessagePart can be serialized to JSON."""
        models = _get_models()

        part = models["MessagePart"](
            content="Test content",
            content_type="text/plain",
        )

        json_str = part.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["content"] == "Test content"
        assert parsed["content_type"] == "text/plain"

    def test_message_part_deserialization(self):
        """Verify MessagePart can be deserialized from dict."""
        models = _get_models()

        data = {
            "content": "Deserialized content",
            "content_type": "text/markdown",
            "content_encoding": "plain",
        }

        part = models["MessagePart"](**data)

        assert part.content == "Deserialized content"
        assert part.content_type == "text/markdown"

    def test_message_part_immutability(self):
        """Verify MessagePart fields can be updated (Pydantic v2 behavior)."""
        models = _get_models()

        part = models["MessagePart"](content="Original")
        part.content = "Updated"

        assert part.content == "Updated"

    def test_message_part_equality(self):
        """Verify MessagePart equality comparison."""
        models = _get_models()

        part1 = models["MessagePart"](content="Same content", content_type="text/plain")
        part2 = models["MessagePart"](content="Same content", content_type="text/plain")
        part3 = models["MessagePart"](content="Different content", content_type="text/plain")

        assert part1 == part2
        assert part1 != part3


# =============================================================================
# Message Tests
# =============================================================================

class TestMessage:
    """Tests for Message model - messages with roles and parts."""

    def test_message_creation_with_user_role(self):
        """Verify Message can be created with user role."""
        models = _get_models()
        types = _get_types()

        message = models["Message"](
            role=types["MessageRole"].USER,
            parts=[models["MessagePart"](content="Hello!")],
        )

        assert message.role == types["MessageRole"].USER
        assert message.role == "user"
        assert len(message.parts) == 1
        assert message.parts[0].content == "Hello!"

    def test_message_creation_with_agent_role(self):
        """Verify Message can be created with agent role."""
        models = _get_models()
        types = _get_types()

        message = models["Message"](
            role=types["MessageRole"].AGENT,
            parts=[models["MessagePart"](content="I can help with that.")],
        )

        assert message.role == types["MessageRole"].AGENT
        assert message.role == "agent"

    def test_message_creation_with_system_role(self):
        """Verify Message can be created with system role."""
        models = _get_models()
        types = _get_types()

        message = models["Message"](
            role=types["MessageRole"].SYSTEM,
            parts=[models["MessagePart"](content="You are a helpful assistant.")],
        )

        assert message.role == types["MessageRole"].SYSTEM
        assert message.role == "system"

    def test_message_creation_with_named_agent(self):
        """Verify Message can be created with named agent role."""
        models = _get_models()

        message = models["Message"](
            role="agent/assistant",
            parts=[models["MessagePart"](content="Response from assistant.")],
        )

        assert message.role == "agent/assistant"
        assert message.role.startswith("agent/")

    def test_message_creation_with_timestamps(self):
        """Verify Message can be created with timestamps."""
        models = _get_models()
        types = _get_types()

        created = datetime(2024, 1, 15, 12, 0, 0)
        completed = datetime(2024, 1, 15, 12, 5, 0)

        message = models["Message"](
            role=types["MessageRole"].AGENT,
            parts=[models["MessagePart"](content="Response")],
            created_at=created,
            completed_at=completed,
        )

        assert message.created_at == created
        assert message.completed_at == completed

    def test_message_default_parts(self):
        """Verify Message has empty parts list by default."""
        models = _get_models()
        types = _get_types()

        message = models["Message"](role=types["MessageRole"].USER)

        assert message.parts == []
        assert len(message.parts) == 0

    def test_message_with_multiple_parts(self):
        """Verify Message can have multiple parts."""
        models = _get_models()
        types = _get_types()

        message = models["Message"](
            role=types["MessageRole"].USER,
            parts=[
                models["MessagePart"](content="Please analyze this image:"),
                models["MessagePart"](
                    content_url="https://example.com/image.png",
                    content_type="image/png",
                ),
            ],
        )

        assert len(message.parts) == 2
        assert message.parts[0].content == "Please analyze this image:"
        assert message.parts[1].content_url == "https://example.com/image.png"

    def test_message_user_text_factory(self):
        """Verify Message.user_text factory method."""
        models = _get_models()
        types = _get_types()

        message = models["Message"].user_text("Hello from user!")

        assert message.role == types["MessageRole"].USER
        assert len(message.parts) == 1
        assert message.parts[0].content == "Hello from user!"
        assert message.parts[0].content_type == "text/plain"
        assert message.created_at is not None

    def test_message_agent_text_factory_without_name(self):
        """Verify Message.agent_text factory method without agent name."""
        models = _get_models()
        types = _get_types()

        message = models["Message"].agent_text("Response from agent!")

        assert message.role == types["MessageRole"].AGENT
        assert len(message.parts) == 1
        assert message.parts[0].content == "Response from agent!"
        assert message.created_at is not None

    def test_message_agent_text_factory_with_name(self):
        """Verify Message.agent_text factory method with agent name."""
        models = _get_models()

        message = models["Message"].agent_text("Response!", agent_name="assistant")

        assert message.role == "agent/assistant"
        assert message.parts[0].content == "Response!"

    def test_message_serialization(self):
        """Verify Message can be serialized to dict."""
        models = _get_models()
        types = _get_types()

        message = models["Message"](
            role=types["MessageRole"].USER,
            parts=[models["MessagePart"](content="Test")],
            created_at=datetime(2024, 1, 15, 12, 0, 0),
        )

        data = message.model_dump()

        assert data["role"] == "user"
        assert len(data["parts"]) == 1
        assert data["parts"][0]["content"] == "Test"

    def test_message_json_serialization(self):
        """Verify Message can be serialized to JSON."""
        models = _get_models()
        types = _get_types()

        message = models["Message"](
            role=types["MessageRole"].USER,
            parts=[models["MessagePart"](content="Test")],
        )

        json_str = message.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["role"] == "user"
        assert parsed["parts"][0]["content"] == "Test"

    def test_message_deserialization(self):
        """Verify Message can be deserialized from dict."""
        models = _get_models()

        data = {
            "role": "user",
            "parts": [
                {"content": "Deserialized message", "content_type": "text/plain"}
            ],
        }

        message = models["Message"](**data)

        assert message.role == "user"
        assert message.parts[0].content == "Deserialized message"

    def test_message_equality(self):
        """Verify Message equality comparison."""
        models = _get_models()
        types = _get_types()

        msg1 = models["Message"](
            role=types["MessageRole"].USER,
            parts=[models["MessagePart"](content="Same")],
            created_at=datetime(2024, 1, 15),
        )
        msg2 = models["Message"](
            role=types["MessageRole"].USER,
            parts=[models["MessagePart"](content="Same")],
            created_at=datetime(2024, 1, 15),
        )
        msg3 = models["Message"](
            role=types["MessageRole"].AGENT,
            parts=[models["MessagePart"](content="Same")],
            created_at=datetime(2024, 1, 15),
        )

        assert msg1 == msg2
        assert msg1 != msg3


# =============================================================================
# Run Tests
# =============================================================================

class TestRun:
    """Tests for Run model - agent run lifecycle and state management."""

    def test_run_creation_with_minimal_fields(self):
        """Verify Run can be created with minimal required fields."""
        models = _get_models()
        types = _get_types()

        run = models["Run"](agent_name="test-agent")

        assert run.agent_name == "test-agent"
        assert isinstance(run.run_id, UUID)
        assert run.status == types["RunStatus"].CREATED
        assert run.mode == types["RunMode"].SYNC
        assert run.session_id is None
        assert run.input == []
        assert run.output == []
        assert run.error is None
        assert run.await_request is None
        assert run.created_at is not None
        assert run.started_at is None
        assert run.completed_at is None
        assert run.metadata == {}

    def test_run_creation_with_all_fields(self):
        """Verify Run can be created with all fields."""
        models = _get_models()
        types = _get_types()

        run_id = uuid4()
        session_id = uuid4()
        created_at = datetime(2024, 1, 15, 12, 0, 0)
        started_at = datetime(2024, 1, 15, 12, 0, 1)
        completed_at = datetime(2024, 1, 15, 12, 5, 0)

        user_message = models["Message"].user_text("Hello")
        agent_message = models["Message"].agent_text("Hi there!")

        run = models["Run"](
            run_id=run_id,
            agent_name="test-agent",
            session_id=session_id,
            status=types["RunStatus"].COMPLETED,
            mode=types["RunMode"].ASYNC,
            input=[user_message],
            output=[agent_message],
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            metadata={"user_id": "user-123"},
        )

        assert run.run_id == run_id
        assert run.session_id == session_id
        assert run.status == types["RunStatus"].COMPLETED
        assert run.mode == types["RunMode"].ASYNC
        assert len(run.input) == 1
        assert len(run.output) == 1
        assert run.created_at == created_at
        assert run.started_at == started_at
        assert run.completed_at == completed_at
        assert run.metadata["user_id"] == "user-123"

    def test_run_with_created_status(self):
        """Verify Run in CREATED status."""
        models = _get_models()
        types = _get_types()

        run = models["Run"](
            agent_name="test-agent",
            status=types["RunStatus"].CREATED,
        )

        assert run.status == types["RunStatus"].CREATED
        assert run.status == "created"

    def test_run_with_in_progress_status(self):
        """Verify Run in IN_PROGRESS status."""
        models = _get_models()
        types = _get_types()

        run = models["Run"](
            agent_name="test-agent",
            status=types["RunStatus"].IN_PROGRESS,
            started_at=datetime.utcnow(),
        )

        assert run.status == types["RunStatus"].IN_PROGRESS
        assert run.status == "in-progress"
        assert run.started_at is not None

    def test_run_with_awaiting_status(self):
        """Verify Run in AWAITING status with await_request."""
        models = _get_models()
        types = _get_types()

        await_request = models["AwaitRequest"](
            type="user_confirmation",
            description="Please confirm",
            timeout_seconds=300,
        )

        run = models["Run"](
            agent_name="test-agent",
            status=types["RunStatus"].AWAITING,
            await_request=await_request,
        )

        assert run.status == types["RunStatus"].AWAITING
        assert run.await_request is not None
        assert run.await_request.type == "user_confirmation"

    def test_run_with_completed_status(self):
        """Verify Run in COMPLETED status with output."""
        models = _get_models()
        types = _get_types()

        output_message = models["Message"].agent_text("Task completed!")

        run = models["Run"](
            agent_name="test-agent",
            status=types["RunStatus"].COMPLETED,
            output=[output_message],
            completed_at=datetime.utcnow(),
        )

        assert run.status == types["RunStatus"].COMPLETED
        assert len(run.output) == 1
        assert run.completed_at is not None

    def test_run_with_failed_status(self):
        """Verify Run in FAILED status with error."""
        models = _get_models()
        types = _get_types()

        error = models["RunError"](
            code=types["ErrorCode"].AGENT_ERROR,
            message="Agent failed to process request",
            data={"details": "Internal error"},
        )

        run = models["Run"](
            agent_name="test-agent",
            status=types["RunStatus"].FAILED,
            error=error,
            completed_at=datetime.utcnow(),
        )

        assert run.status == types["RunStatus"].FAILED
        assert run.error is not None
        assert run.error.code == types["ErrorCode"].AGENT_ERROR

    def test_run_with_cancelled_status(self):
        """Verify Run in CANCELLED status."""
        models = _get_models()
        types = _get_types()

        run = models["Run"](
            agent_name="test-agent",
            status=types["RunStatus"].CANCELLED,
            completed_at=datetime.utcnow(),
        )

        assert run.status == types["RunStatus"].CANCELLED
        assert run.status == "cancelled"

    def test_run_with_cancelling_status(self):
        """Verify Run in CANCELLING status."""
        models = _get_models()
        types = _get_types()

        run = models["Run"](
            agent_name="test-agent",
            status=types["RunStatus"].CANCELLING,
        )

        assert run.status == types["RunStatus"].CANCELLING
        assert run.status == "cancelling"

    def test_run_sync_mode(self):
        """Verify Run with SYNC mode."""
        models = _get_models()
        types = _get_types()

        run = models["Run"](
            agent_name="test-agent",
            mode=types["RunMode"].SYNC,
        )

        assert run.mode == types["RunMode"].SYNC
        assert run.mode == "sync"

    def test_run_async_mode(self):
        """Verify Run with ASYNC mode."""
        models = _get_models()
        types = _get_types()

        run = models["Run"](
            agent_name="test-agent",
            mode=types["RunMode"].ASYNC,
        )

        assert run.mode == types["RunMode"].ASYNC
        assert run.mode == "async"

    def test_run_stream_mode(self):
        """Verify Run with STREAM mode."""
        models = _get_models()
        types = _get_types()

        run = models["Run"](
            agent_name="test-agent",
            mode=types["RunMode"].STREAM,
        )

        assert run.mode == types["RunMode"].STREAM
        assert run.mode == "stream"

    def test_run_with_multiple_input_messages(self):
        """Verify Run can have multiple input messages."""
        models = _get_models()

        run = models["Run"](
            agent_name="test-agent",
            input=[
                models["Message"].user_text("First message"),
                models["Message"].user_text("Second message"),
            ],
        )

        assert len(run.input) == 2
        assert run.input[0].parts[0].content == "First message"
        assert run.input[1].parts[0].content == "Second message"

    def test_run_with_multiple_output_messages(self):
        """Verify Run can have multiple output messages."""
        models = _get_models()
        types = _get_types()

        run = models["Run"](
            agent_name="test-agent",
            status=types["RunStatus"].COMPLETED,
            output=[
                models["Message"].agent_text("First response"),
                models["Message"].agent_text("Second response"),
            ],
        )

        assert len(run.output) == 2

    def test_run_serialization(self):
        """Verify Run can be serialized to dict."""
        models = _get_models()
        types = _get_types()

        run_id = UUID("12345678-1234-5678-1234-567812345678")

        run = models["Run"](
            run_id=run_id,
            agent_name="test-agent",
            status=types["RunStatus"].COMPLETED,
            mode=types["RunMode"].SYNC,
        )

        data = run.model_dump()

        assert data["run_id"] == run_id
        assert data["agent_name"] == "test-agent"
        assert data["status"] == "completed"
        assert data["mode"] == "sync"

    def test_run_json_serialization(self):
        """Verify Run can be serialized to JSON."""
        models = _get_models()

        run = models["Run"](agent_name="test-agent")

        json_str = run.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["agent_name"] == "test-agent"
        assert "run_id" in parsed

    def test_run_deserialization(self):
        """Verify Run can be deserialized from dict."""
        models = _get_models()

        run_id = uuid4()
        data = {
            "run_id": str(run_id),
            "agent_name": "deserialized-agent",
            "status": "in-progress",
            "mode": "async",
            "input": [],
            "output": [],
            "metadata": {},
        }

        run = models["Run"](**data)

        assert run.run_id == run_id
        assert run.agent_name == "deserialized-agent"
        assert run.status == "in-progress"

    def test_run_uuid_auto_generation(self):
        """Verify Run generates unique UUIDs automatically."""
        models = _get_models()

        run1 = models["Run"](agent_name="agent-1")
        run2 = models["Run"](agent_name="agent-2")

        assert run1.run_id != run2.run_id
        assert isinstance(run1.run_id, UUID)
        assert isinstance(run2.run_id, UUID)

    def test_run_created_at_auto_generation(self):
        """Verify Run generates created_at automatically."""
        models = _get_models()

        before = datetime.utcnow()
        run = models["Run"](agent_name="test-agent")
        after = datetime.utcnow()

        assert run.created_at is not None
        assert before <= run.created_at <= after


# =============================================================================
# Session Tests
# =============================================================================

class TestSession:
    """Tests for Session model - session state and conversation history."""

    def test_session_creation_with_minimal_fields(self):
        """Verify Session can be created with minimal fields."""
        models = _get_models()

        session = models["Session"]()

        assert isinstance(session.session_id, UUID)
        assert session.agent_name is None
        assert session.messages == []
        assert session.runs == []
        assert session.context == {}
        assert session.created_at is not None
        assert session.last_activity_at is not None
        assert session.expires_at is None
        assert session.metadata == {}

    def test_session_creation_with_all_fields(self):
        """Verify Session can be created with all fields."""
        models = _get_models()

        session_id = uuid4()
        run_id = uuid4()
        created_at = datetime(2024, 1, 15, 12, 0, 0)
        last_activity = datetime(2024, 1, 15, 13, 0, 0)
        expires_at = datetime(2024, 1, 16, 12, 0, 0)

        message = models["Message"].user_text("Hello")

        session = models["Session"](
            session_id=session_id,
            agent_name="test-agent",
            messages=[message],
            runs=[run_id],
            context={"language": "en"},
            created_at=created_at,
            last_activity_at=last_activity,
            expires_at=expires_at,
            metadata={"source": "test"},
        )

        assert session.session_id == session_id
        assert session.agent_name == "test-agent"
        assert len(session.messages) == 1
        assert session.runs == [run_id]
        assert session.context["language"] == "en"
        assert session.created_at == created_at
        assert session.last_activity_at == last_activity
        assert session.expires_at == expires_at
        assert session.metadata["source"] == "test"

    def test_session_with_conversation_history(self):
        """Verify Session can store conversation history."""
        models = _get_models()
        types = _get_types()

        messages = [
            models["Message"].user_text("Hello!"),
            models["Message"].agent_text("Hi! How can I help?"),
            models["Message"].user_text("Tell me about ACP."),
            models["Message"].agent_text("ACP is Agent Communication Protocol..."),
        ]

        session = models["Session"](
            agent_name="test-agent",
            messages=messages,
        )

        assert len(session.messages) == 4
        assert session.messages[0].role == types["MessageRole"].USER
        assert session.messages[1].role == types["MessageRole"].AGENT

    def test_session_with_multiple_runs(self):
        """Verify Session can track multiple runs."""
        models = _get_models()

        run_ids = [uuid4(), uuid4(), uuid4()]

        session = models["Session"](
            agent_name="test-agent",
            runs=run_ids,
        )

        assert len(session.runs) == 3
        assert all(isinstance(rid, UUID) for rid in session.runs)

    def test_session_with_context(self):
        """Verify Session can store context data."""
        models = _get_models()

        context = {
            "user_preferences": {
                "language": "en",
                "timezone": "UTC",
            },
            "conversation_state": "active",
            "custom_data": [1, 2, 3],
        }

        session = models["Session"](
            agent_name="test-agent",
            context=context,
        )

        assert session.context["user_preferences"]["language"] == "en"
        assert session.context["conversation_state"] == "active"
        assert session.context["custom_data"] == [1, 2, 3]

    def test_session_expiration(self):
        """Verify Session expiration tracking."""
        models = _get_models()

        now = datetime.utcnow()
        expires = now + timedelta(hours=24)

        session = models["Session"](
            agent_name="test-agent",
            expires_at=expires,
        )

        assert session.expires_at == expires
        assert session.expires_at > now

    def test_session_already_expired(self):
        """Verify Session can be created as already expired."""
        models = _get_models()

        expired_time = datetime(2020, 1, 1, 0, 0, 0)

        session = models["Session"](
            agent_name="test-agent",
            expires_at=expired_time,
        )

        assert session.expires_at == expired_time
        assert session.expires_at < datetime.utcnow()

    def test_session_serialization(self):
        """Verify Session can be serialized to dict."""
        models = _get_models()

        session_id = UUID("87654321-4321-8765-4321-876543218765")

        session = models["Session"](
            session_id=session_id,
            agent_name="test-agent",
            context={"key": "value"},
        )

        data = session.model_dump()

        assert data["session_id"] == session_id
        assert data["agent_name"] == "test-agent"
        assert data["context"]["key"] == "value"

    def test_session_json_serialization(self):
        """Verify Session can be serialized to JSON."""
        models = _get_models()

        session = models["Session"](agent_name="test-agent")

        json_str = session.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["agent_name"] == "test-agent"
        assert "session_id" in parsed

    def test_session_deserialization(self):
        """Verify Session can be deserialized from dict."""
        models = _get_models()

        session_id = uuid4()
        data = {
            "session_id": str(session_id),
            "agent_name": "deserialized-agent",
            "messages": [],
            "runs": [],
            "context": {},
            "metadata": {},
        }

        session = models["Session"](**data)

        assert session.session_id == session_id
        assert session.agent_name == "deserialized-agent"

    def test_session_uuid_auto_generation(self):
        """Verify Session generates unique UUIDs automatically."""
        models = _get_models()

        session1 = models["Session"]()
        session2 = models["Session"]()

        assert session1.session_id != session2.session_id
        assert isinstance(session1.session_id, UUID)
        assert isinstance(session2.session_id, UUID)

    def test_session_timestamps_auto_generation(self):
        """Verify Session generates timestamps automatically."""
        models = _get_models()

        before = datetime.utcnow()
        session = models["Session"]()
        after = datetime.utcnow()

        assert before <= session.created_at <= after
        assert before <= session.last_activity_at <= after

    def test_empty_session(self):
        """Verify empty session with no messages."""
        models = _get_models()

        session = models["Session"](
            agent_name="test-agent",
        )

        assert len(session.messages) == 0
        assert len(session.runs) == 0


# =============================================================================
# RunError Tests
# =============================================================================

class TestRunError:
    """Tests for RunError model - error information for failed runs."""

    def test_run_error_creation(self):
        """Verify RunError can be created."""
        models = _get_models()
        types = _get_types()

        error = models["RunError"](
            code=types["ErrorCode"].AGENT_ERROR,
            message="An error occurred",
        )

        assert error.code == types["ErrorCode"].AGENT_ERROR
        assert error.message == "An error occurred"
        assert error.data is None

    def test_run_error_with_data(self):
        """Verify RunError can include additional data."""
        models = _get_models()
        types = _get_types()

        error = models["RunError"](
            code=types["ErrorCode"].VALIDATION_ERROR,
            message="Input validation failed",
            data={"field": "email", "reason": "Invalid format"},
        )

        assert error.data is not None
        assert error.data["field"] == "email"
        assert error.data["reason"] == "Invalid format"

    @pytest.mark.parametrize("error_code", [
        "SERVER_ERROR",
        "INVALID_INPUT",
        "NOT_FOUND",
        "UNAUTHORIZED",
        "FORBIDDEN",
        "CONFLICT",
        "RATE_LIMITED",
        "TIMEOUT",
        "AGENT_ERROR",
        "VALIDATION_ERROR",
    ])
    def test_run_error_with_all_error_codes(self, error_code):
        """Verify RunError works with all error codes."""
        models = _get_models()
        types = _get_types()

        code = getattr(types["ErrorCode"], error_code)
        error = models["RunError"](
            code=code,
            message=f"Error with code {error_code}",
        )

        assert error.code == code


# =============================================================================
# AwaitRequest Tests
# =============================================================================

class TestAwaitRequest:
    """Tests for AwaitRequest model - information about what agent is awaiting."""

    def test_await_request_creation(self):
        """Verify AwaitRequest can be created."""
        models = _get_models()

        await_req = models["AwaitRequest"](
            type="user_confirmation",
            description="Please confirm the action",
        )

        assert await_req.type == "user_confirmation"
        assert await_req.description == "Please confirm the action"
        assert await_req.schema_ is None
        assert await_req.timeout_seconds is None

    def test_await_request_with_schema(self):
        """Verify AwaitRequest can include JSON schema."""
        models = _get_models()

        schema = {
            "type": "object",
            "properties": {
                "confirmed": {"type": "boolean"},
            },
            "required": ["confirmed"],
        }

        # Note: The field uses alias="schema", so we pass via the alias
        await_req = models["AwaitRequest"](
            type="user_confirmation",
            description="Confirm action",
            schema=schema,  # Using the alias
        )

        assert await_req.schema_ == schema

    def test_await_request_with_timeout(self):
        """Verify AwaitRequest can include timeout."""
        models = _get_models()

        await_req = models["AwaitRequest"](
            type="additional_info",
            timeout_seconds=300,
        )

        assert await_req.timeout_seconds == 300


# =============================================================================
# AgentMetadata Tests
# =============================================================================

class TestAgentMetadata:
    """Tests for AgentMetadata model."""

    def test_agent_metadata_defaults(self):
        """Verify AgentMetadata default values."""
        models = _get_models()

        metadata = models["AgentMetadata"]()

        assert metadata.documentation is None
        assert metadata.license is None
        assert metadata.capabilities == []
        assert metadata.domains == []
        assert metadata.tags == []
        assert metadata.dependencies == []
        assert metadata.version is None
        assert metadata.created_by is None
        assert metadata.successor_agent is None

    def test_agent_metadata_full(self):
        """Verify AgentMetadata with all fields."""
        models = _get_models()

        metadata = models["AgentMetadata"](
            documentation="https://docs.example.com",
            license="MIT",
            capabilities=["text-generation", "summarization"],
            domains=["general"],
            tags=["ai", "nlp"],
            dependencies=["base-agent"],
            version="1.0.0",
            created_by="test-team",
            successor_agent="new-agent",
        )

        assert metadata.documentation == "https://docs.example.com"
        assert metadata.license == "MIT"
        assert len(metadata.capabilities) == 2
        assert metadata.version == "1.0.0"


# =============================================================================
# AgentManifest Tests
# =============================================================================

class TestAgentManifest:
    """Tests for AgentManifest model."""

    def test_agent_manifest_creation(self):
        """Verify AgentManifest can be created."""
        models = _get_models()
        types = _get_types()

        manifest = models["AgentManifest"](
            name="test-agent",
            description="A test agent",
        )

        assert manifest.name == "test-agent"
        assert manifest.description == "A test agent"
        assert manifest.status == types["AgentStatus"].ACTIVE
        assert manifest.input_content_types == ["text/plain"]
        assert manifest.output_content_types == ["text/plain"]

    def test_agent_manifest_with_custom_content_types(self):
        """Verify AgentManifest with custom content types."""
        models = _get_models()

        manifest = models["AgentManifest"](
            name="multimodal-agent",
            description="Handles multiple content types",
            input_content_types=["text/plain", "image/png", "application/json"],
            output_content_types=["text/plain", "application/json"],
        )

        assert len(manifest.input_content_types) == 3
        assert "image/png" in manifest.input_content_types

    @pytest.mark.parametrize("status_name", [
        "INITIALIZING",
        "ACTIVE",
        "DEGRADED",
        "RETIRING",
        "RETIRED",
    ])
    def test_agent_manifest_with_all_statuses(self, status_name):
        """Verify AgentManifest works with all agent statuses."""
        models = _get_models()
        types = _get_types()

        status = getattr(types["AgentStatus"], status_name)
        manifest = models["AgentManifest"](
            name="test-agent",
            description="Test agent",
            status=status,
        )

        assert manifest.status == status


# =============================================================================
# CitationMetadata Tests
# =============================================================================

class TestCitationMetadata:
    """Tests for CitationMetadata model."""

    def test_citation_metadata_minimal(self):
        """Verify CitationMetadata with minimal fields."""
        models = _get_models()

        citation = models["CitationMetadata"](
            source="https://example.com",
        )

        assert citation.source == "https://example.com"
        assert citation.title is None
        assert citation.author is None
        assert citation.date is None
        assert citation.snippet is None

    def test_citation_metadata_full(self):
        """Verify CitationMetadata with all fields."""
        models = _get_models()

        citation = models["CitationMetadata"](
            source="https://example.com/paper",
            title="Important Research",
            author="Dr. Smith",
            date="2024-01-15",
            snippet="Key finding...",
        )

        assert citation.source == "https://example.com/paper"
        assert citation.title == "Important Research"
        assert citation.author == "Dr. Smith"
        assert citation.date == "2024-01-15"
        assert citation.snippet == "Key finding..."


# =============================================================================
# TrajectoryMetadata Tests
# =============================================================================

class TestTrajectoryMetadata:
    """Tests for TrajectoryMetadata model."""

    def test_trajectory_metadata_thought(self):
        """Verify TrajectoryMetadata for thought step."""
        models = _get_models()

        trajectory = models["TrajectoryMetadata"](
            step_type="thought",
            duration_ms=50,
        )

        assert trajectory.step_type == "thought"
        assert trajectory.duration_ms == 50
        assert trajectory.tool_name is None

    def test_trajectory_metadata_action(self):
        """Verify TrajectoryMetadata for action step."""
        models = _get_models()

        trajectory = models["TrajectoryMetadata"](
            step_type="action",
            tool_name="web_search",
            tool_input={"query": "test query"},
            tool_output="Search results...",
            duration_ms=150,
        )

        assert trajectory.step_type == "action"
        assert trajectory.tool_name == "web_search"
        assert trajectory.tool_input == {"query": "test query"}
        assert trajectory.tool_output == "Search results..."

    def test_trajectory_metadata_observation(self):
        """Verify TrajectoryMetadata for observation step."""
        models = _get_models()

        trajectory = models["TrajectoryMetadata"](
            step_type="observation",
            tool_output="Observed patterns...",
        )

        assert trajectory.step_type == "observation"
        assert trajectory.tool_output == "Observed patterns..."


# =============================================================================
# Integration Tests - Model Relationships
# =============================================================================

class TestModelRelationships:
    """Tests for relationships between ACP models."""

    def test_run_with_session(self):
        """Verify Run can be associated with a Session."""
        models = _get_models()
        types = _get_types()

        session = models["Session"](agent_name="test-agent")

        run = models["Run"](
            agent_name="test-agent",
            session_id=session.session_id,
        )

        assert run.session_id == session.session_id

    def test_session_with_runs(self):
        """Verify Session can track multiple Run IDs."""
        models = _get_models()

        run1 = models["Run"](agent_name="test-agent")
        run2 = models["Run"](agent_name="test-agent")

        session = models["Session"](
            agent_name="test-agent",
            runs=[run1.run_id, run2.run_id],
        )

        assert run1.run_id in session.runs
        assert run2.run_id in session.runs

    def test_message_in_session_and_run(self):
        """Verify Messages can be used in both Session and Run."""
        models = _get_models()
        types = _get_types()

        message = models["Message"].user_text("Hello!")

        session = models["Session"](
            agent_name="test-agent",
            messages=[message],
        )

        run = models["Run"](
            agent_name="test-agent",
            session_id=session.session_id,
            input=[message],
        )

        assert session.messages[0] == run.input[0]

    def test_complete_conversation_flow(self):
        """Test a complete conversation flow with all models."""
        models = _get_models()
        types = _get_types()

        # Create agent manifest
        agent = models["AgentManifest"](
            name="conversation-agent",
            description="An agent for testing conversation flow",
        )

        # Create session
        session = models["Session"](
            agent_name=agent.name,
        )

        # Create user message
        user_msg = models["Message"].user_text("Hello, agent!")
        session.messages.append(user_msg)

        # Create run
        run = models["Run"](
            agent_name=agent.name,
            session_id=session.session_id,
            input=[user_msg],
            status=types["RunStatus"].IN_PROGRESS,
            started_at=datetime.utcnow(),
        )
        session.runs.append(run.run_id)

        # Complete the run with agent response
        agent_msg = models["Message"].agent_text("Hello! How can I help you?")
        run.output.append(agent_msg)
        run.status = types["RunStatus"].COMPLETED
        run.completed_at = datetime.utcnow()

        # Add agent message to session
        session.messages.append(agent_msg)
        session.last_activity_at = datetime.utcnow()

        # Verify the complete flow
        assert len(session.messages) == 2
        assert session.messages[0].role == types["MessageRole"].USER
        assert session.messages[1].role == types["MessageRole"].AGENT
        assert run.run_id in session.runs
        assert run.status == types["RunStatus"].COMPLETED
        assert len(run.output) == 1


# =============================================================================
# Edge Cases and Validation Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and validation."""

    def test_message_part_both_content_and_url(self):
        """Verify MessagePart can have both content and URL (no validation prevents it)."""
        models = _get_models()

        # The model allows both, validation should happen at a higher level
        part = models["MessagePart"](
            content="Inline content",
            content_url="https://example.com/content",
        )

        assert part.content == "Inline content"
        assert part.content_url == "https://example.com/content"

    def test_run_with_empty_input(self):
        """Verify Run can be created with empty input."""
        models = _get_models()

        run = models["Run"](
            agent_name="test-agent",
            input=[],
        )

        assert len(run.input) == 0

    def test_session_with_empty_messages(self):
        """Verify Session can be created with empty messages."""
        models = _get_models()

        session = models["Session"](
            agent_name="test-agent",
            messages=[],
        )

        assert len(session.messages) == 0

    def test_message_part_with_empty_string_content(self):
        """Verify MessagePart can have empty string content."""
        models = _get_models()

        part = models["MessagePart"](content="")

        assert part.content == ""

    def test_run_metadata_complex_structure(self):
        """Verify Run metadata can contain complex nested structures."""
        models = _get_models()

        metadata = {
            "nested": {
                "level1": {
                    "level2": [1, 2, 3],
                },
            },
            "list": [{"key": "value"}],
            "number": 42,
            "boolean": True,
            "null": None,
        }

        run = models["Run"](
            agent_name="test-agent",
            metadata=metadata,
        )

        assert run.metadata["nested"]["level1"]["level2"] == [1, 2, 3]
        assert run.metadata["boolean"] is True
        assert run.metadata["null"] is None

    def test_session_context_update(self):
        """Verify Session context can be updated."""
        models = _get_models()

        session = models["Session"](
            agent_name="test-agent",
            context={"initial": "value"},
        )

        session.context["new_key"] = "new_value"
        session.context["initial"] = "updated"

        assert session.context["new_key"] == "new_value"
        assert session.context["initial"] == "updated"

    def test_message_with_large_content(self):
        """Verify Message can handle large content."""
        models = _get_models()

        large_content = "x" * 100000  # 100KB of content

        message = models["Message"].user_text(large_content)

        assert len(message.parts[0].content) == 100000

    def test_run_with_many_messages(self):
        """Verify Run can handle many messages."""
        models = _get_models()
        types = _get_types()

        messages = [models["Message"].user_text(f"Message {i}") for i in range(100)]

        run = models["Run"](
            agent_name="test-agent",
            input=messages,
        )

        assert len(run.input) == 100
