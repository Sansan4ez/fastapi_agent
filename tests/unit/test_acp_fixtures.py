"""
Unit tests to verify ACP fixtures work correctly.

These tests ensure all fixtures are loadable and produce valid objects.
"""

from __future__ import annotations

import pytest
from uuid import UUID
from datetime import datetime


# Register the ACP fixtures plugin
pytest_plugins = ["tests.fixtures.acp_fixtures"]


# Helper to get types/models at runtime (avoiding module-level imports)
def _get_types():
    from app.acp.core.types import (
        RunStatus, AgentStatus, RunMode, ContentEncoding, MessageRole, ErrorCode,
    )
    return {
        "RunStatus": RunStatus,
        "AgentStatus": AgentStatus,
        "RunMode": RunMode,
        "ContentEncoding": ContentEncoding,
        "MessageRole": MessageRole,
        "ErrorCode": ErrorCode,
    }


def _get_models():
    from app.acp.core.models import (
        MessagePart, Message, AgentMetadata, AgentManifest, RunError,
        AwaitRequest, Run, Session, CitationMetadata, TrajectoryMetadata,
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


def _get_schemas():
    from app.acp.core.schemas import (
        RunCreateRequest, RunResumeRequest, RunResponse, AgentListResponse,
        AgentResponse, SessionResponse, ErrorResponse, RunEventResponse,
        PaginationParams, HealthResponse,
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


class TestMessagePartFixtures:
    """Test MessagePart fixtures."""

    def test_sample_message_part(self, sample_message_part):
        """Verify sample_message_part fixture."""
        models = _get_models()
        types = _get_types()
        assert isinstance(sample_message_part, models["MessagePart"])
        assert sample_message_part.content is not None
        assert sample_message_part.content_type == "text/plain"
        assert sample_message_part.content_encoding == types["ContentEncoding"].PLAIN

    def test_sample_message_part_with_url(self, sample_message_part_with_url):
        """Verify sample_message_part_with_url fixture."""
        models = _get_models()
        assert isinstance(sample_message_part_with_url, models["MessagePart"])
        assert sample_message_part_with_url.content_url is not None
        assert sample_message_part_with_url.content_type == "application/pdf"

    def test_sample_message_part_base64(self, sample_message_part_base64):
        """Verify sample_message_part_base64 fixture."""
        models = _get_models()
        types = _get_types()
        assert isinstance(sample_message_part_base64, models["MessagePart"])
        assert sample_message_part_base64.content_encoding == types["ContentEncoding"].BASE64


class TestMessageFixtures:
    """Test Message fixtures."""

    def test_sample_user_message(self, sample_user_message):
        """Verify sample_user_message fixture."""
        models = _get_models()
        types = _get_types()
        assert isinstance(sample_user_message, models["Message"])
        assert sample_user_message.role == types["MessageRole"].USER
        assert len(sample_user_message.parts) > 0

    def test_sample_agent_message(self, sample_agent_message):
        """Verify sample_agent_message fixture."""
        models = _get_models()
        types = _get_types()
        assert isinstance(sample_agent_message, models["Message"])
        assert sample_agent_message.role == types["MessageRole"].AGENT
        assert sample_agent_message.completed_at is not None

    def test_sample_named_agent_message(self, sample_named_agent_message):
        """Verify sample_named_agent_message fixture."""
        models = _get_models()
        assert isinstance(sample_named_agent_message, models["Message"])
        assert sample_named_agent_message.role.startswith("agent/")

    def test_sample_system_message(self, sample_system_message):
        """Verify sample_system_message fixture."""
        models = _get_models()
        types = _get_types()
        assert isinstance(sample_system_message, models["Message"])
        assert sample_system_message.role == types["MessageRole"].SYSTEM

    def test_sample_multipart_message(self, sample_multipart_message):
        """Verify sample_multipart_message fixture has multiple parts."""
        models = _get_models()
        assert isinstance(sample_multipart_message, models["Message"])
        assert len(sample_multipart_message.parts) > 1

    def test_conversation_history(self, conversation_history):
        """Verify conversation_history fixture."""
        assert isinstance(conversation_history, list)
        assert len(conversation_history) >= 2


class TestAgentFixtures:
    """Test Agent-related fixtures."""

    def test_sample_agent_metadata(self, sample_agent_metadata):
        """Verify sample_agent_metadata fixture."""
        models = _get_models()
        assert isinstance(sample_agent_metadata, models["AgentMetadata"])
        assert sample_agent_metadata.version is not None

    def test_sample_agent_manifest(self, sample_agent_manifest):
        """Verify sample_agent_manifest fixture."""
        models = _get_models()
        types = _get_types()
        assert isinstance(sample_agent_manifest, models["AgentManifest"])
        assert sample_agent_manifest.name is not None
        assert sample_agent_manifest.description is not None
        assert sample_agent_manifest.status == types["AgentStatus"].ACTIVE

    def test_minimal_agent_manifest(self, minimal_agent_manifest):
        """Verify minimal_agent_manifest fixture has defaults."""
        models = _get_models()
        types = _get_types()
        assert isinstance(minimal_agent_manifest, models["AgentManifest"])
        assert minimal_agent_manifest.status == types["AgentStatus"].ACTIVE

    def test_degraded_agent_manifest(self, degraded_agent_manifest):
        """Verify degraded_agent_manifest fixture."""
        models = _get_models()
        types = _get_types()
        assert isinstance(degraded_agent_manifest, models["AgentManifest"])
        assert degraded_agent_manifest.status == types["AgentStatus"].DEGRADED


class TestRunFixtures:
    """Test Run fixtures."""

    def test_sample_created_run(self, sample_created_run):
        """Verify sample_created_run fixture."""
        models = _get_models()
        types = _get_types()
        assert isinstance(sample_created_run, models["Run"])
        assert sample_created_run.status == types["RunStatus"].CREATED
        assert isinstance(sample_created_run.run_id, UUID)

    def test_sample_in_progress_run(self, sample_in_progress_run):
        """Verify sample_in_progress_run fixture."""
        models = _get_models()
        types = _get_types()
        assert isinstance(sample_in_progress_run, models["Run"])
        assert sample_in_progress_run.status == types["RunStatus"].IN_PROGRESS
        assert sample_in_progress_run.started_at is not None

    def test_sample_completed_run(self, sample_completed_run):
        """Verify sample_completed_run fixture."""
        models = _get_models()
        types = _get_types()
        assert isinstance(sample_completed_run, models["Run"])
        assert sample_completed_run.status == types["RunStatus"].COMPLETED
        assert len(sample_completed_run.output) > 0
        assert sample_completed_run.completed_at is not None

    def test_sample_failed_run(self, sample_failed_run):
        """Verify sample_failed_run fixture."""
        models = _get_models()
        types = _get_types()
        assert isinstance(sample_failed_run, models["Run"])
        assert sample_failed_run.status == types["RunStatus"].FAILED
        assert sample_failed_run.error is not None

    def test_sample_awaiting_run(self, sample_awaiting_run):
        """Verify sample_awaiting_run fixture."""
        models = _get_models()
        types = _get_types()
        assert isinstance(sample_awaiting_run, models["Run"])
        assert sample_awaiting_run.status == types["RunStatus"].AWAITING
        assert sample_awaiting_run.await_request is not None

    def test_sample_async_run(self, sample_async_run):
        """Verify sample_async_run fixture."""
        models = _get_models()
        types = _get_types()
        assert isinstance(sample_async_run, models["Run"])
        assert sample_async_run.mode == types["RunMode"].ASYNC

    def test_sample_streaming_run(self, sample_streaming_run):
        """Verify sample_streaming_run fixture."""
        models = _get_models()
        types = _get_types()
        assert isinstance(sample_streaming_run, models["Run"])
        assert sample_streaming_run.mode == types["RunMode"].STREAM


class TestSessionFixtures:
    """Test Session fixtures."""

    def test_sample_session(self, sample_session):
        """Verify sample_session fixture."""
        models = _get_models()
        assert isinstance(sample_session, models["Session"])
        assert isinstance(sample_session.session_id, UUID)
        assert len(sample_session.messages) > 0

    def test_empty_session(self, empty_session):
        """Verify empty_session fixture."""
        models = _get_models()
        assert isinstance(empty_session, models["Session"])
        assert len(empty_session.messages) == 0


class TestErrorFixtures:
    """Test Error fixtures."""

    def test_sample_run_error(self, sample_run_error):
        """Verify sample_run_error fixture."""
        models = _get_models()
        types = _get_types()
        assert isinstance(sample_run_error, models["RunError"])
        assert sample_run_error.code == types["ErrorCode"].AGENT_ERROR

    def test_validation_error(self, validation_error):
        """Verify validation_error fixture."""
        models = _get_models()
        types = _get_types()
        assert isinstance(validation_error, models["RunError"])
        assert validation_error.code == types["ErrorCode"].VALIDATION_ERROR


class TestMetadataFixtures:
    """Test metadata fixtures."""

    def test_sample_citation_metadata(self, sample_citation_metadata):
        """Verify sample_citation_metadata fixture."""
        models = _get_models()
        assert isinstance(sample_citation_metadata, models["CitationMetadata"])
        assert sample_citation_metadata.source is not None

    def test_sample_trajectory_metadata(self, sample_trajectory_metadata):
        """Verify sample_trajectory_metadata fixture."""
        models = _get_models()
        assert isinstance(sample_trajectory_metadata, models["TrajectoryMetadata"])
        assert sample_trajectory_metadata.step_type is not None


class TestRequestSchemaFixtures:
    """Test request schema fixtures."""

    def test_sample_run_create_request(self, sample_run_create_request):
        """Verify sample_run_create_request fixture."""
        schemas = _get_schemas()
        assert isinstance(sample_run_create_request, schemas["RunCreateRequest"])
        assert sample_run_create_request.agent is not None
        assert len(sample_run_create_request.input) > 0

    def test_sample_run_resume_request(self, sample_run_resume_request):
        """Verify sample_run_resume_request fixture."""
        schemas = _get_schemas()
        assert isinstance(sample_run_resume_request, schemas["RunResumeRequest"])
        assert len(sample_run_resume_request.input) > 0


class TestResponseSchemaFixtures:
    """Test response schema fixtures."""

    def test_sample_run_response(self, sample_run_response):
        """Verify sample_run_response fixture."""
        schemas = _get_schemas()
        assert isinstance(sample_run_response, schemas["RunResponse"])
        assert isinstance(sample_run_response.run_id, UUID)

    def test_sample_agent_list_response(self, sample_agent_list_response):
        """Verify sample_agent_list_response fixture."""
        schemas = _get_schemas()
        assert isinstance(sample_agent_list_response, schemas["AgentListResponse"])
        assert len(sample_agent_list_response.agents) > 0

    def test_sample_agent_response(self, sample_agent_response):
        """Verify sample_agent_response fixture."""
        schemas = _get_schemas()
        assert isinstance(sample_agent_response, schemas["AgentResponse"])
        assert sample_agent_response.agent is not None

    def test_sample_session_response(self, sample_session_response):
        """Verify sample_session_response fixture."""
        schemas = _get_schemas()
        assert isinstance(sample_session_response, schemas["SessionResponse"])
        assert isinstance(sample_session_response.session_id, UUID)

    def test_sample_error_response(self, sample_error_response):
        """Verify sample_error_response fixture."""
        schemas = _get_schemas()
        assert isinstance(sample_error_response, schemas["ErrorResponse"])
        assert sample_error_response.code is not None

    def test_sample_health_response(self, sample_health_response):
        """Verify sample_health_response fixture."""
        schemas = _get_schemas()
        assert isinstance(sample_health_response, schemas["HealthResponse"])
        assert sample_health_response.status == "healthy"


class TestParametrizedFixtures:
    """Test parametrized fixtures that iterate over enum values."""

    def test_any_run_status(self, any_run_status):
        """Verify any_run_status parametrized fixture."""
        types = _get_types()
        assert isinstance(any_run_status, types["RunStatus"])
        assert any_run_status in list(types["RunStatus"])

    def test_any_agent_status(self, any_agent_status):
        """Verify any_agent_status parametrized fixture."""
        types = _get_types()
        assert isinstance(any_agent_status, types["AgentStatus"])
        assert any_agent_status in list(types["AgentStatus"])

    def test_any_run_mode(self, any_run_mode):
        """Verify any_run_mode parametrized fixture."""
        types = _get_types()
        assert isinstance(any_run_mode, types["RunMode"])
        assert any_run_mode in list(types["RunMode"])

    def test_any_error_code(self, any_error_code):
        """Verify any_error_code parametrized fixture."""
        types = _get_types()
        assert isinstance(any_error_code, types["ErrorCode"])
        assert any_error_code in list(types["ErrorCode"])


class TestCompositeFixtures:
    """Test composite scenario fixtures."""

    def test_full_conversation_scenario(self, full_conversation_scenario):
        """Verify full_conversation_scenario fixture."""
        types = _get_types()
        assert isinstance(full_conversation_scenario, dict)
        assert "agent" in full_conversation_scenario
        assert "session" in full_conversation_scenario
        assert "run" in full_conversation_scenario

    def test_error_scenario(self, error_scenario):
        """Verify error_scenario fixture."""
        types = _get_types()
        assert isinstance(error_scenario, dict)
        assert "run" in error_scenario
        assert error_scenario["run"].status == types["RunStatus"].FAILED

    def test_await_scenario(self, await_scenario):
        """Verify await_scenario fixture."""
        assert isinstance(await_scenario, dict)
        assert "awaiting_run" in await_scenario
        assert "resume_request" in await_scenario


class TestFactoryFunctions:
    """Test factory functions."""

    def test_create_message_part(self):
        """Test create_message_part factory function."""
        from tests.fixtures.acp_fixtures import create_message_part
        models = _get_models()

        part = create_message_part(content="Custom content")
        assert isinstance(part, models["MessagePart"])
        assert part.content == "Custom content"

    def test_create_message(self):
        """Test create_message factory function."""
        from tests.fixtures.acp_fixtures import create_message
        models = _get_models()
        types = _get_types()

        msg = create_message(role=types["MessageRole"].AGENT, content="Agent response")
        assert isinstance(msg, models["Message"])
        assert msg.role == types["MessageRole"].AGENT

    def test_create_run(self):
        """Test create_run factory function."""
        from tests.fixtures.acp_fixtures import create_run
        models = _get_models()
        types = _get_types()

        run = create_run(
            agent_name="custom-agent",
            status=types["RunStatus"].COMPLETED,
            mode=types["RunMode"].ASYNC,
        )
        assert isinstance(run, models["Run"])
        assert run.agent_name == "custom-agent"
        assert run.status == types["RunStatus"].COMPLETED
        assert run.mode == types["RunMode"].ASYNC

    def test_create_session(self):
        """Test create_session factory function."""
        from tests.fixtures.acp_fixtures import create_session
        models = _get_models()

        session = create_session(agent_name="test-agent")
        assert isinstance(session, models["Session"])
        assert session.agent_name == "test-agent"

    def test_create_agent_manifest(self):
        """Test create_agent_manifest factory function."""
        from tests.fixtures.acp_fixtures import create_agent_manifest
        models = _get_models()
        types = _get_types()

        manifest = create_agent_manifest(
            name="my-agent",
            description="My test agent",
            status=types["AgentStatus"].DEGRADED,
        )
        assert isinstance(manifest, models["AgentManifest"])
        assert manifest.name == "my-agent"
        assert manifest.status == types["AgentStatus"].DEGRADED

    def test_create_run_error(self):
        """Test create_run_error factory function."""
        from tests.fixtures.acp_fixtures import create_run_error
        models = _get_models()
        types = _get_types()

        error = create_run_error(
            code=types["ErrorCode"].TIMEOUT,
            message="Request timed out",
        )
        assert isinstance(error, models["RunError"])
        assert error.code == types["ErrorCode"].TIMEOUT
