"""
ACP Shared Test Fixtures

Provides comprehensive fixtures for ACP types, models, and schemas.
These fixtures can be used across all tests that need ACP-related test data.

Usage:
    Import fixtures in your test file or conftest.py:

        from tests.fixtures.acp_fixtures import (
            sample_message_part,
            sample_user_message,
            sample_agent_manifest,
            ...
        )

    Or import all fixtures:

        from tests.fixtures.acp_fixtures import *
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest

# Import types for type checking only - actual imports happen in fixtures
if TYPE_CHECKING:
    from app.acp.core.types import (
        RunStatus,
        AgentStatus,
        RunMode,
        ContentEncoding,
        MessageRole,
        ErrorCode,
        MetadataType,
    )
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
    from app.acp.core.schemas import (
        RunCreateRequest,
        RunResumeRequest,
        RunResponse,
        AgentListResponse,
        AgentResponse,
        SessionResponse,
        ErrorResponse,
        RunEventResponse,
        PaginationParams,
        HealthResponse,
    )


# =============================================================================
# Helper function for lazy imports
# =============================================================================

def _get_acp_types():
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


def _get_acp_models():
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


def _get_acp_schemas():
    """Lazy import of ACP schemas module."""
    from app.acp.core.schemas import (
        RunCreateRequest,
        RunResumeRequest,
        RunResponse,
        AgentListResponse,
        AgentResponse,
        SessionResponse,
        ErrorResponse,
        RunEventResponse,
        PaginationParams,
        HealthResponse,
    )
    return {
        "RunCreateRequest": RunCreateRequest,
        "RunResumeRequest": RunResumeRequest,
        "RunResponse": RunResponse,
        "AgentListResponse": AgentListResponse,
        "AgentResponse": AgentResponse,
        "SessionResponse": SessionResponse,
        "ErrorResponse": ErrorResponse,
        "RunEventResponse": RunEventResponse,
        "PaginationParams": PaginationParams,
        "HealthResponse": HealthResponse,
    }


# =============================================================================
# Fixed UUIDs for deterministic testing
# =============================================================================

FIXTURE_RUN_ID = UUID("12345678-1234-5678-1234-567812345678")
FIXTURE_SESSION_ID = UUID("87654321-4321-8765-4321-876543218765")
FIXTURE_ALT_RUN_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
FIXTURE_ALT_SESSION_ID = UUID("11111111-2222-3333-4444-555555555555")

FIXTURE_TIMESTAMP = datetime(2024, 1, 15, 12, 0, 0)
FIXTURE_TIMESTAMP_LATER = datetime(2024, 1, 15, 12, 5, 0)


# =============================================================================
# MessagePart Fixtures
# =============================================================================

@pytest.fixture
def sample_message_part():
    """Create a simple text message part."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["MessagePart"](
        content="Hello, this is a test message.",
        content_type="text/plain",
        content_encoding=types["ContentEncoding"].PLAIN,
    )


@pytest.fixture
def sample_message_part_with_url():
    """Create a message part with content URL."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["MessagePart"](
        content_url="https://example.com/document.pdf",
        content_type="application/pdf",
        content_encoding=types["ContentEncoding"].PLAIN,
        name="document.pdf",
    )


@pytest.fixture
def sample_message_part_base64():
    """Create a base64-encoded message part."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["MessagePart"](
        content="SGVsbG8gV29ybGQh",  # "Hello World!" in base64
        content_type="text/plain",
        content_encoding=types["ContentEncoding"].BASE64,
    )


@pytest.fixture
def sample_message_part_with_metadata():
    """Create a message part with citation metadata."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["MessagePart"](
        content="According to the research...",
        content_type="text/plain",
        content_encoding=types["ContentEncoding"].PLAIN,
        metadata={
            "type": types["MetadataType"].CITATION,
            "source": "https://example.com/paper",
            "title": "Test Paper",
            "author": "Test Author",
        },
    )


@pytest.fixture
def sample_image_part():
    """Create an image message part."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["MessagePart"](
        content_url="https://example.com/image.png",
        content_type="image/png",
        content_encoding=types["ContentEncoding"].PLAIN,
        name="screenshot.png",
    )


# =============================================================================
# Message Fixtures
# =============================================================================

@pytest.fixture
def sample_user_message(sample_message_part):
    """Create a simple user message."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["Message"](
        role=types["MessageRole"].USER,
        parts=[sample_message_part],
        created_at=FIXTURE_TIMESTAMP,
    )


@pytest.fixture
def sample_agent_message():
    """Create a simple agent message."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["Message"](
        role=types["MessageRole"].AGENT,
        parts=[models["MessagePart"](content="I can help you with that.", content_type="text/plain")],
        created_at=FIXTURE_TIMESTAMP,
        completed_at=FIXTURE_TIMESTAMP_LATER,
    )


@pytest.fixture
def sample_named_agent_message():
    """Create a message from a specific named agent."""
    models = _get_acp_models()
    return models["Message"](
        role="agent/assistant",
        parts=[models["MessagePart"](content="Response from assistant agent.", content_type="text/plain")],
        created_at=FIXTURE_TIMESTAMP,
    )


@pytest.fixture
def sample_system_message():
    """Create a system message."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["Message"](
        role=types["MessageRole"].SYSTEM,
        parts=[models["MessagePart"](content="You are a helpful assistant.", content_type="text/plain")],
        created_at=FIXTURE_TIMESTAMP,
    )


@pytest.fixture
def sample_multipart_message():
    """Create a message with multiple parts."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["Message"](
        role=types["MessageRole"].USER,
        parts=[
            models["MessagePart"](content="Please analyze this image:", content_type="text/plain"),
            models["MessagePart"](content_url="https://example.com/image.png", content_type="image/png"),
        ],
        created_at=FIXTURE_TIMESTAMP,
    )


@pytest.fixture
def conversation_history(
    sample_user_message,
    sample_agent_message,
):
    """Create a sample conversation history."""
    models = _get_acp_models()
    Message = models["Message"]
    return [
        sample_user_message,
        sample_agent_message,
        Message.user_text("Follow-up question"),
        Message.agent_text("Here's the answer to your follow-up."),
    ]


# =============================================================================
# AgentMetadata Fixtures
# =============================================================================

@pytest.fixture
def sample_agent_metadata():
    """Create sample agent metadata."""
    models = _get_acp_models()
    return models["AgentMetadata"](
        documentation="https://docs.example.com/agent",
        license="MIT",
        capabilities=["text-generation", "summarization"],
        domains=["general", "customer-support"],
        tags=["ai", "assistant", "nlp"],
        dependencies=[],
        version="1.0.0",
        created_by="test-team",
    )


@pytest.fixture
def minimal_agent_metadata():
    """Create minimal agent metadata with defaults."""
    models = _get_acp_models()
    return models["AgentMetadata"]()


@pytest.fixture
def retiring_agent_metadata():
    """Create metadata for a retiring agent."""
    models = _get_acp_models()
    return models["AgentMetadata"](
        version="1.0.0",
        successor_agent="new-assistant-v2",
    )


# =============================================================================
# AgentManifest Fixtures
# =============================================================================

@pytest.fixture
def sample_agent_manifest(sample_agent_metadata):
    """Create a sample agent manifest."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["AgentManifest"](
        name="test-assistant",
        description="A helpful test assistant for unit testing",
        input_content_types=["text/plain", "application/json"],
        output_content_types=["text/plain", "application/json"],
        metadata=sample_agent_metadata,
        status=types["AgentStatus"].ACTIVE,
    )


@pytest.fixture
def minimal_agent_manifest():
    """Create a minimal agent manifest with defaults."""
    models = _get_acp_models()
    return models["AgentManifest"](
        name="minimal-agent",
        description="A minimal test agent",
    )


@pytest.fixture
def degraded_agent_manifest():
    """Create an agent manifest in degraded status."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["AgentManifest"](
        name="degraded-agent",
        description="An agent currently experiencing issues",
        status=types["AgentStatus"].DEGRADED,
    )


@pytest.fixture
def retiring_agent_manifest(retiring_agent_metadata):
    """Create a retiring agent manifest."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["AgentManifest"](
        name="legacy-agent",
        description="An agent being retired",
        metadata=retiring_agent_metadata,
        status=types["AgentStatus"].RETIRING,
    )


@pytest.fixture
def agent_manifest_list(sample_agent_manifest):
    """Create a list of agent manifests for testing pagination."""
    models = _get_acp_models()
    return [
        sample_agent_manifest,
        models["AgentManifest"](name="agent-2", description="Second test agent"),
        models["AgentManifest"](name="agent-3", description="Third test agent"),
    ]


# =============================================================================
# Error Fixtures
# =============================================================================

@pytest.fixture
def sample_run_error():
    """Create a sample run error."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["RunError"](
        code=types["ErrorCode"].AGENT_ERROR,
        message="Agent failed to process the request",
        data={"details": "Internal processing error"},
    )


@pytest.fixture
def validation_error():
    """Create a validation error."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["RunError"](
        code=types["ErrorCode"].VALIDATION_ERROR,
        message="Input validation failed",
        data={"field": "input", "reason": "Required field missing"},
    )


@pytest.fixture
def not_found_error():
    """Create a not found error."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["RunError"](
        code=types["ErrorCode"].NOT_FOUND,
        message="Resource not found",
    )


@pytest.fixture
def timeout_error():
    """Create a timeout error."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["RunError"](
        code=types["ErrorCode"].TIMEOUT,
        message="Request timed out after 30 seconds",
        data={"timeout_seconds": 30},
    )


# =============================================================================
# AwaitRequest Fixtures
# =============================================================================

@pytest.fixture
def sample_await_request():
    """Create a sample await request."""
    models = _get_acp_models()
    return models["AwaitRequest"](
        type="user_confirmation",
        description="Please confirm you want to proceed with this action.",
        schema_={
            "type": "object",
            "properties": {
                "confirmed": {"type": "boolean"},
                "reason": {"type": "string"},
            },
            "required": ["confirmed"],
        },
        timeout_seconds=300,
    )


@pytest.fixture
def simple_await_request():
    """Create a simple await request without schema."""
    models = _get_acp_models()
    return models["AwaitRequest"](
        type="additional_info",
        description="Please provide additional information.",
    )


# =============================================================================
# Run Fixtures
# =============================================================================

@pytest.fixture
def sample_created_run(sample_user_message):
    """Create a run in CREATED status."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["Run"](
        run_id=FIXTURE_RUN_ID,
        agent_name="test-assistant",
        session_id=FIXTURE_SESSION_ID,
        status=types["RunStatus"].CREATED,
        mode=types["RunMode"].SYNC,
        input=[sample_user_message],
        created_at=FIXTURE_TIMESTAMP,
    )


@pytest.fixture
def sample_in_progress_run(sample_user_message):
    """Create a run in IN_PROGRESS status."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["Run"](
        run_id=FIXTURE_RUN_ID,
        agent_name="test-assistant",
        status=types["RunStatus"].IN_PROGRESS,
        mode=types["RunMode"].SYNC,
        input=[sample_user_message],
        created_at=FIXTURE_TIMESTAMP,
        started_at=FIXTURE_TIMESTAMP,
    )


@pytest.fixture
def sample_completed_run(
    sample_user_message,
    sample_agent_message,
):
    """Create a completed run with output."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["Run"](
        run_id=FIXTURE_RUN_ID,
        agent_name="test-assistant",
        session_id=FIXTURE_SESSION_ID,
        status=types["RunStatus"].COMPLETED,
        mode=types["RunMode"].SYNC,
        input=[sample_user_message],
        output=[sample_agent_message],
        created_at=FIXTURE_TIMESTAMP,
        started_at=FIXTURE_TIMESTAMP,
        completed_at=FIXTURE_TIMESTAMP_LATER,
    )


@pytest.fixture
def sample_failed_run(
    sample_user_message,
    sample_run_error,
):
    """Create a failed run with error."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["Run"](
        run_id=FIXTURE_RUN_ID,
        agent_name="test-assistant",
        status=types["RunStatus"].FAILED,
        mode=types["RunMode"].SYNC,
        input=[sample_user_message],
        error=sample_run_error,
        created_at=FIXTURE_TIMESTAMP,
        started_at=FIXTURE_TIMESTAMP,
        completed_at=FIXTURE_TIMESTAMP_LATER,
    )


@pytest.fixture
def sample_awaiting_run(
    sample_user_message,
    sample_await_request,
):
    """Create a run in AWAITING status."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["Run"](
        run_id=FIXTURE_RUN_ID,
        agent_name="test-assistant",
        status=types["RunStatus"].AWAITING,
        mode=types["RunMode"].SYNC,
        input=[sample_user_message],
        await_request=sample_await_request,
        created_at=FIXTURE_TIMESTAMP,
        started_at=FIXTURE_TIMESTAMP,
    )


@pytest.fixture
def sample_async_run(sample_user_message):
    """Create an async mode run."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["Run"](
        run_id=FIXTURE_RUN_ID,
        agent_name="test-assistant",
        status=types["RunStatus"].IN_PROGRESS,
        mode=types["RunMode"].ASYNC,
        input=[sample_user_message],
        created_at=FIXTURE_TIMESTAMP,
        started_at=FIXTURE_TIMESTAMP,
    )


@pytest.fixture
def sample_streaming_run(sample_user_message):
    """Create a streaming mode run."""
    models = _get_acp_models()
    types = _get_acp_types()
    return models["Run"](
        run_id=FIXTURE_RUN_ID,
        agent_name="test-assistant",
        status=types["RunStatus"].IN_PROGRESS,
        mode=types["RunMode"].STREAM,
        input=[sample_user_message],
        created_at=FIXTURE_TIMESTAMP,
        started_at=FIXTURE_TIMESTAMP,
    )


@pytest.fixture
def sample_run_with_metadata(sample_user_message):
    """Create a run with custom metadata."""
    models = _get_acp_models()
    types = _get_acp_types()
    Message = models["Message"]
    return models["Run"](
        run_id=FIXTURE_RUN_ID,
        agent_name="test-assistant",
        status=types["RunStatus"].COMPLETED,
        mode=types["RunMode"].SYNC,
        input=[sample_user_message],
        output=[Message.agent_text("Response")],
        metadata={
            "user_id": "user-123",
            "request_id": "req-456",
            "custom_field": "custom_value",
        },
        created_at=FIXTURE_TIMESTAMP,
        completed_at=FIXTURE_TIMESTAMP_LATER,
    )


# =============================================================================
# Session Fixtures
# =============================================================================

@pytest.fixture
def sample_session(conversation_history):
    """Create a sample session with conversation history."""
    models = _get_acp_models()
    return models["Session"](
        session_id=FIXTURE_SESSION_ID,
        agent_name="test-assistant",
        messages=conversation_history,
        runs=[FIXTURE_RUN_ID, FIXTURE_ALT_RUN_ID],
        context={"language": "en", "timezone": "UTC"},
        created_at=FIXTURE_TIMESTAMP,
        last_activity_at=FIXTURE_TIMESTAMP_LATER,
        metadata={"source": "test"},
    )


@pytest.fixture
def empty_session():
    """Create an empty session."""
    models = _get_acp_models()
    return models["Session"](
        session_id=FIXTURE_SESSION_ID,
        agent_name="test-assistant",
        created_at=FIXTURE_TIMESTAMP,
        last_activity_at=FIXTURE_TIMESTAMP,
    )


@pytest.fixture
def expired_session():
    """Create an expired session."""
    models = _get_acp_models()
    return models["Session"](
        session_id=FIXTURE_SESSION_ID,
        agent_name="test-assistant",
        created_at=FIXTURE_TIMESTAMP,
        last_activity_at=FIXTURE_TIMESTAMP,
        expires_at=FIXTURE_TIMESTAMP,  # Already expired
    )


# =============================================================================
# Metadata Type Fixtures
# =============================================================================

@pytest.fixture
def sample_citation_metadata():
    """Create sample citation metadata."""
    models = _get_acp_models()
    return models["CitationMetadata"](
        source="https://example.com/article",
        title="Important Research Paper",
        author="Dr. Jane Smith",
        date="2024-01-15",
        snippet="The key finding of our research indicates...",
    )


@pytest.fixture
def minimal_citation_metadata():
    """Create minimal citation metadata."""
    models = _get_acp_models()
    return models["CitationMetadata"](source="https://example.com")


@pytest.fixture
def sample_trajectory_metadata():
    """Create sample trajectory metadata for tool use."""
    models = _get_acp_models()
    return models["TrajectoryMetadata"](
        step_type="action",
        tool_name="web_search",
        tool_input={"query": "test query"},
        tool_output="Search results...",
        duration_ms=150,
    )


@pytest.fixture
def thought_trajectory_metadata():
    """Create trajectory metadata for a thought step."""
    models = _get_acp_models()
    return models["TrajectoryMetadata"](
        step_type="thought",
        duration_ms=50,
    )


@pytest.fixture
def observation_trajectory_metadata():
    """Create trajectory metadata for an observation step."""
    models = _get_acp_models()
    return models["TrajectoryMetadata"](
        step_type="observation",
        tool_output="Observed the following patterns...",
        duration_ms=10,
    )


# =============================================================================
# Request Schema Fixtures
# =============================================================================

@pytest.fixture
def sample_run_create_request(sample_user_message):
    """Create a sample run creation request."""
    schemas = _get_acp_schemas()
    types = _get_acp_types()
    return schemas["RunCreateRequest"](
        agent="test-assistant",
        input=[sample_user_message],
        session_id=FIXTURE_SESSION_ID,
        mode=types["RunMode"].SYNC,
        metadata={"source": "test"},
    )


@pytest.fixture
def minimal_run_create_request():
    """Create a minimal run creation request."""
    schemas = _get_acp_schemas()
    models = _get_acp_models()
    Message = models["Message"]
    return schemas["RunCreateRequest"](
        agent="test-assistant",
        input=[Message.user_text("Hello")],
    )


@pytest.fixture
def async_run_create_request(sample_user_message):
    """Create an async run creation request."""
    schemas = _get_acp_schemas()
    types = _get_acp_types()
    return schemas["RunCreateRequest"](
        agent="test-assistant",
        input=[sample_user_message],
        mode=types["RunMode"].ASYNC,
    )


@pytest.fixture
def streaming_run_create_request(sample_user_message):
    """Create a streaming run creation request."""
    schemas = _get_acp_schemas()
    types = _get_acp_types()
    return schemas["RunCreateRequest"](
        agent="test-assistant",
        input=[sample_user_message],
        mode=types["RunMode"].STREAM,
    )


@pytest.fixture
def sample_run_resume_request():
    """Create a sample run resume request."""
    schemas = _get_acp_schemas()
    models = _get_acp_models()
    Message = models["Message"]
    return schemas["RunResumeRequest"](
        input=[Message.user_text("Yes, please proceed.")],
        metadata={"confirmed": True},
    )


# =============================================================================
# Response Schema Fixtures
# =============================================================================

@pytest.fixture
def sample_run_response(sample_completed_run):
    """Create a sample run response."""
    schemas = _get_acp_schemas()
    return schemas["RunResponse"](
        run_id=sample_completed_run.run_id,
        agent_name=sample_completed_run.agent_name,
        session_id=sample_completed_run.session_id,
        status=sample_completed_run.status,
        output=sample_completed_run.output,
        created_at=sample_completed_run.created_at,
        completed_at=sample_completed_run.completed_at,
    )


@pytest.fixture
def sample_agent_list_response(agent_manifest_list):
    """Create a sample agent list response."""
    schemas = _get_acp_schemas()
    return schemas["AgentListResponse"](
        agents=agent_manifest_list,
        total=len(agent_manifest_list),
        offset=0,
        limit=100,
    )


@pytest.fixture
def sample_agent_response(sample_agent_manifest):
    """Create a sample agent response."""
    schemas = _get_acp_schemas()
    return schemas["AgentResponse"](agent=sample_agent_manifest)


@pytest.fixture
def sample_session_response(sample_session):
    """Create a sample session response."""
    schemas = _get_acp_schemas()
    return schemas["SessionResponse"](
        session_id=sample_session.session_id,
        agent_name=sample_session.agent_name,
        messages=sample_session.messages,
        run_count=len(sample_session.runs),
        created_at=sample_session.created_at,
        last_activity_at=sample_session.last_activity_at,
    )


@pytest.fixture
def sample_error_response(sample_run_error):
    """Create a sample error response."""
    schemas = _get_acp_schemas()
    return schemas["ErrorResponse"](
        code=sample_run_error.code,
        message=sample_run_error.message,
        data=sample_run_error.data,
    )


@pytest.fixture
def sample_run_event_response():
    """Create a sample run event response."""
    schemas = _get_acp_schemas()
    return schemas["RunEventResponse"](
        event_id="evt-001",
        event_type="message",
        data={
            "role": "agent",
            "content": "Partial response...",
        },
        timestamp=FIXTURE_TIMESTAMP,
    )


@pytest.fixture
def sample_health_response():
    """Create a sample health response."""
    schemas = _get_acp_schemas()
    return schemas["HealthResponse"](
        status="healthy",
        version="1.0.0",
        agent_count=5,
        uptime_seconds=3600.0,
    )


@pytest.fixture
def sample_pagination_params():
    """Create sample pagination parameters."""
    schemas = _get_acp_schemas()
    return schemas["PaginationParams"](offset=0, limit=50)


# =============================================================================
# Factory Functions (for creating customized fixtures)
# =============================================================================

def create_message_part(
    content: str = "Test content",
    content_type: str = "text/plain",
    content_encoding=None,
    content_url: str | None = None,
    name: str | None = None,
    metadata: dict[str, Any] | None = None,
):
    """Factory function to create a MessagePart with custom values."""
    models = _get_acp_models()
    types = _get_acp_types()
    if content_encoding is None:
        content_encoding = types["ContentEncoding"].PLAIN
    return models["MessagePart"](
        content=content if content_url is None else None,
        content_url=content_url,
        content_type=content_type,
        content_encoding=content_encoding,
        name=name,
        metadata=metadata,
    )


def create_message(
    role=None,
    content: str = "Test message",
    created_at: datetime | None = None,
    completed_at: datetime | None = None,
):
    """Factory function to create a Message with custom values."""
    models = _get_acp_models()
    types = _get_acp_types()
    if role is None:
        role = types["MessageRole"].USER
    return models["Message"](
        role=role,
        parts=[models["MessagePart"](content=content, content_type="text/plain")],
        created_at=created_at or datetime.utcnow(),
        completed_at=completed_at,
    )


def create_run(
    run_id: UUID | None = None,
    agent_name: str = "test-agent",
    status=None,
    mode=None,
    session_id: UUID | None = None,
    input_messages: list | None = None,
    output_messages: list | None = None,
    error=None,
    await_request=None,
    metadata: dict[str, Any] | None = None,
):
    """Factory function to create a Run with custom values."""
    models = _get_acp_models()
    types = _get_acp_types()
    Message = models["Message"]
    if status is None:
        status = types["RunStatus"].CREATED
    if mode is None:
        mode = types["RunMode"].SYNC
    return models["Run"](
        run_id=run_id or uuid4(),
        agent_name=agent_name,
        session_id=session_id,
        status=status,
        mode=mode,
        input=input_messages or [Message.user_text("Test input")],
        output=output_messages or [],
        error=error,
        await_request=await_request,
        metadata=metadata or {},
        created_at=datetime.utcnow(),
    )


def create_session(
    session_id: UUID | None = None,
    agent_name: str | None = "test-agent",
    messages: list | None = None,
    runs: list[UUID] | None = None,
    context: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    expires_at: datetime | None = None,
):
    """Factory function to create a Session with custom values."""
    models = _get_acp_models()
    return models["Session"](
        session_id=session_id or uuid4(),
        agent_name=agent_name,
        messages=messages or [],
        runs=runs or [],
        context=context or {},
        metadata=metadata or {},
        created_at=datetime.utcnow(),
        last_activity_at=datetime.utcnow(),
        expires_at=expires_at,
    )


def create_agent_manifest(
    name: str = "test-agent",
    description: str = "A test agent",
    status=None,
    input_content_types: list[str] | None = None,
    output_content_types: list[str] | None = None,
    metadata=None,
):
    """Factory function to create an AgentManifest with custom values."""
    models = _get_acp_models()
    types = _get_acp_types()
    if status is None:
        status = types["AgentStatus"].ACTIVE
    if metadata is None:
        metadata = models["AgentMetadata"]()
    return models["AgentManifest"](
        name=name,
        description=description,
        input_content_types=input_content_types or ["text/plain"],
        output_content_types=output_content_types or ["text/plain"],
        metadata=metadata,
        status=status,
    )


def create_run_error(
    code=None,
    message: str = "An error occurred",
    data: dict[str, Any] | None = None,
):
    """Factory function to create a RunError with custom values."""
    models = _get_acp_models()
    types = _get_acp_types()
    if code is None:
        code = types["ErrorCode"].AGENT_ERROR
    return models["RunError"](code=code, message=message, data=data)


# =============================================================================
# Parametrized Fixture Helpers
# =============================================================================

def _get_all_run_statuses():
    """Get all RunStatus values."""
    types = _get_acp_types()
    return list(types["RunStatus"])


def _get_all_agent_statuses():
    """Get all AgentStatus values."""
    types = _get_acp_types()
    return list(types["AgentStatus"])


def _get_all_run_modes():
    """Get all RunMode values."""
    types = _get_acp_types()
    return list(types["RunMode"])


def _get_all_error_codes():
    """Get all ErrorCode values."""
    types = _get_acp_types()
    return list(types["ErrorCode"])


def _get_all_message_roles():
    """Get all MessageRole values."""
    types = _get_acp_types()
    MessageRole = types["MessageRole"]
    return [MessageRole.USER, MessageRole.AGENT, MessageRole.SYSTEM]


# Note: These parametrized fixtures are defined using pytest_generate_tests
# to avoid importing at module load time


def pytest_generate_tests(metafunc):
    """Generate tests for parametrized enum fixtures."""
    if "any_run_status" in metafunc.fixturenames:
        metafunc.parametrize("any_run_status", _get_all_run_statuses())
    if "any_agent_status" in metafunc.fixturenames:
        metafunc.parametrize("any_agent_status", _get_all_agent_statuses())
    if "any_run_mode" in metafunc.fixturenames:
        metafunc.parametrize("any_run_mode", _get_all_run_modes())
    if "any_error_code" in metafunc.fixturenames:
        metafunc.parametrize("any_error_code", _get_all_error_codes())
    if "any_message_role" in metafunc.fixturenames:
        metafunc.parametrize("any_message_role", _get_all_message_roles())


# =============================================================================
# Composite Fixtures for Integration Testing
# =============================================================================

@pytest.fixture
def full_conversation_scenario(
    sample_agent_manifest,
    sample_session,
    sample_completed_run,
):
    """Create a complete conversation scenario with all components."""
    return {
        "agent": sample_agent_manifest,
        "session": sample_session,
        "run": sample_completed_run,
        "run_id": FIXTURE_RUN_ID,
        "session_id": FIXTURE_SESSION_ID,
    }


@pytest.fixture
def error_scenario(
    sample_agent_manifest,
    sample_failed_run,
    sample_error_response,
):
    """Create an error scenario with failed run."""
    return {
        "agent": sample_agent_manifest,
        "run": sample_failed_run,
        "error_response": sample_error_response,
    }


@pytest.fixture
def await_scenario(
    sample_agent_manifest,
    sample_awaiting_run,
    sample_run_resume_request,
):
    """Create an await/resume scenario."""
    return {
        "agent": sample_agent_manifest,
        "awaiting_run": sample_awaiting_run,
        "resume_request": sample_run_resume_request,
    }
