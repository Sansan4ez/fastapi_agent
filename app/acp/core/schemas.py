"""
ACP Core Schemas

Pydantic schemas for API request and response validation.
These schemas define the structure of data exchanged over HTTP.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.acp.core.types import RunStatus, RunMode, ErrorCode
from app.acp.core.models import Message, AgentManifest, RunError, AwaitRequest


class RunCreateRequest(BaseModel):
    """
    Request schema for creating a new run.

    POST /runs
    """

    model_config = ConfigDict(from_attributes=True)

    agent: str = Field(
        description="Name of the agent to run",
    )
    input: list[Message] = Field(
        description="Input messages for the agent",
    )
    session_id: UUID | None = Field(
        default=None,
        description="Optional session ID for multi-turn conversations",
    )
    mode: RunMode = Field(
        default=RunMode.SYNC,
        description="Execution mode (sync, async, stream)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata for the run",
    )


class RunResumeRequest(BaseModel):
    """
    Request schema for resuming an awaiting run.

    POST /runs/{run_id}
    """

    model_config = ConfigDict(from_attributes=True)

    input: list[Message] = Field(
        description="Input messages to resume the run with",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional additional metadata",
    )


class RunResponse(BaseModel):
    """
    Response schema for run operations.

    Returned by GET /runs/{run_id} and POST /runs
    """

    model_config = ConfigDict(from_attributes=True)

    run_id: UUID = Field(
        description="Unique run identifier",
    )
    agent_name: str = Field(
        description="Name of the agent",
    )
    session_id: UUID | None = Field(
        default=None,
        description="Session ID if part of a session",
    )
    status: RunStatus = Field(
        description="Current run status",
    )
    output: list[Message] = Field(
        default_factory=list,
        description="Output messages from the run",
    )
    error: RunError | None = Field(
        default=None,
        description="Error details if status is 'failed'",
    )
    await_request: AwaitRequest | None = Field(
        default=None,
        description="Await details if status is 'awaiting'",
    )
    created_at: datetime = Field(
        description="When the run was created",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When the run completed",
    )


class AgentListResponse(BaseModel):
    """
    Response schema for listing agents.

    GET /agents
    """

    model_config = ConfigDict(from_attributes=True)

    agents: list[AgentManifest] = Field(
        description="List of available agents",
    )
    total: int = Field(
        description="Total number of agents",
    )
    offset: int = Field(
        default=0,
        description="Pagination offset",
    )
    limit: int = Field(
        default=100,
        description="Pagination limit",
    )


class AgentResponse(BaseModel):
    """
    Response schema for getting a specific agent.

    GET /agents/{name}
    """

    model_config = ConfigDict(from_attributes=True)

    agent: AgentManifest = Field(
        description="Agent manifest",
    )


class SessionResponse(BaseModel):
    """
    Response schema for session operations.

    GET /sessions/{session_id}
    """

    model_config = ConfigDict(from_attributes=True)

    session_id: UUID = Field(
        description="Unique session identifier",
    )
    agent_name: str | None = Field(
        default=None,
        description="Primary agent for this session",
    )
    messages: list[Message] = Field(
        default_factory=list,
        description="Conversation history",
    )
    run_count: int = Field(
        default=0,
        description="Number of runs in this session",
    )
    created_at: datetime = Field(
        description="When the session was created",
    )
    last_activity_at: datetime = Field(
        description="Last activity timestamp",
    )


class ErrorResponse(BaseModel):
    """
    Standard error response schema.
    """

    model_config = ConfigDict(from_attributes=True)

    code: ErrorCode = Field(
        description="Error code",
    )
    message: str = Field(
        description="Human-readable error message",
    )
    data: dict[str, Any] | None = Field(
        default=None,
        description="Additional error context",
    )


class RunEventResponse(BaseModel):
    """
    Response schema for run events (streaming).

    GET /runs/{run_id}/events
    """

    model_config = ConfigDict(from_attributes=True)

    event_id: str = Field(
        description="Unique event identifier",
    )
    event_type: str = Field(
        description="Type of event (message, status, error, thought)",
    )
    data: dict[str, Any] = Field(
        description="Event payload",
    )
    timestamp: datetime = Field(
        description="When the event occurred",
    )


class PaginationParams(BaseModel):
    """
    Common pagination parameters.
    """

    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of items to return",
    )


class HealthResponse(BaseModel):
    """
    Health check response schema.
    """

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(
        default="healthy",
        description="Server health status",
    )
    version: str = Field(
        description="ACP server version",
    )
    agent_count: int = Field(
        default=0,
        description="Number of registered agents",
    )
    uptime_seconds: float = Field(
        default=0,
        description="Server uptime in seconds",
    )
