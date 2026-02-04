"""
ACP Core Models

Defines the data models for ACP protocol entities.
These models represent the internal structure of ACP objects.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict

from app.acp.core.types import (
    RunStatus,
    AgentStatus,
    RunMode,
    ContentEncoding,
    MessageRole,
    ErrorCode,
)


class MessagePart(BaseModel):
    """
    A single part of a message with MIME-typed content.

    Supports both inline content and URL-referenced content.
    """

    model_config = ConfigDict(from_attributes=True)

    content: str | None = Field(
        default=None,
        description="Inline content (mutually exclusive with content_url)",
    )
    content_url: str | None = Field(
        default=None,
        description="URL to external content (mutually exclusive with content)",
    )
    content_type: str = Field(
        default="text/plain",
        description="MIME type of the content",
    )
    content_encoding: ContentEncoding = Field(
        default=ContentEncoding.PLAIN,
        description="Encoding of the content (plain or base64)",
    )
    name: str | None = Field(
        default=None,
        description="Optional identifier for artifacts",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata (CitationMetadata, TrajectoryMetadata, or custom)",
    )


class Message(BaseModel):
    """
    A message in the ACP protocol.

    Messages are the primary unit of communication between clients and agents.
    Each message has a role and one or more parts.
    """

    model_config = ConfigDict(from_attributes=True)

    role: str = Field(
        description="Message author role (user, agent, agent/{name}, system)",
    )
    parts: list[MessagePart] = Field(
        default_factory=list,
        description="Message content parts",
    )
    created_at: datetime | None = Field(
        default=None,
        description="When the message was created",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When the message was completed",
    )

    @classmethod
    def user_text(cls, content: str) -> "Message":
        """Create a simple user text message."""
        return cls(
            role=MessageRole.USER,
            parts=[MessagePart(content=content, content_type="text/plain")],
            created_at=datetime.utcnow(),
        )

    @classmethod
    def agent_text(cls, content: str, agent_name: str | None = None) -> "Message":
        """Create a simple agent text message."""
        role = f"agent/{agent_name}" if agent_name else MessageRole.AGENT
        return cls(
            role=role,
            parts=[MessagePart(content=content, content_type="text/plain")],
            created_at=datetime.utcnow(),
        )


class AgentMetadata(BaseModel):
    """
    Extended metadata for an agent manifest.
    """

    model_config = ConfigDict(from_attributes=True)

    documentation: str | None = Field(
        default=None,
        description="URL to agent documentation",
    )
    license: str | None = Field(
        default=None,
        description="License identifier (e.g., MIT, Apache-2.0)",
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="List of agent capabilities",
    )
    domains: list[str] = Field(
        default_factory=list,
        description="Domain areas the agent operates in",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Searchable tags for discovery",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Other agents this agent depends on",
    )
    version: str | None = Field(
        default=None,
        description="Agent version",
    )
    created_by: str | None = Field(
        default=None,
        description="Creator/owner of the agent",
    )
    successor_agent: str | None = Field(
        default=None,
        description="Name of successor agent (for RETIRING agents)",
    )


class AgentManifest(BaseModel):
    """
    Agent manifest describing an agent's capabilities.

    This is returned when querying agent information and is used
    for agent discovery.
    """

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(
        description="Unique agent identifier",
    )
    description: str = Field(
        description="Human-readable description of the agent",
    )
    input_content_types: list[str] = Field(
        default_factory=lambda: ["text/plain"],
        description="Accepted input MIME types",
    )
    output_content_types: list[str] = Field(
        default_factory=lambda: ["text/plain"],
        description="Produced output MIME types",
    )
    metadata: AgentMetadata = Field(
        default_factory=AgentMetadata,
        description="Extended agent metadata",
    )
    status: AgentStatus = Field(
        default=AgentStatus.ACTIVE,
        description="Current lifecycle status of the agent",
    )


class RunError(BaseModel):
    """
    Error information for a failed run.
    """

    model_config = ConfigDict(from_attributes=True)

    code: ErrorCode = Field(
        description="Error code categorizing the error",
    )
    message: str = Field(
        description="Human-readable error message",
    )
    data: dict[str, Any] | None = Field(
        default=None,
        description="Additional error context",
    )


class AwaitRequest(BaseModel):
    """
    Information about what an agent is awaiting.

    Used when a run enters the 'awaiting' state.
    """

    model_config = ConfigDict(from_attributes=True)

    type: str = Field(
        description="Type of information being awaited",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description of what's needed",
    )
    schema_: dict[str, Any] | None = Field(
        default=None,
        alias="schema",
        description="JSON Schema for the expected response",
    )
    timeout_seconds: int | None = Field(
        default=None,
        description="How long the agent will wait before timing out",
    )


class Run(BaseModel):
    """
    A run represents a single agent execution.

    Runs track the lifecycle of an agent invocation from creation
    through completion or failure.
    """

    model_config = ConfigDict(from_attributes=True)

    run_id: UUID = Field(
        default_factory=uuid4,
        description="Unique run identifier",
    )
    agent_name: str = Field(
        description="Name of the agent being run",
    )
    session_id: UUID | None = Field(
        default=None,
        description="Session this run belongs to (if any)",
    )
    status: RunStatus = Field(
        default=RunStatus.CREATED,
        description="Current run status",
    )
    mode: RunMode = Field(
        default=RunMode.SYNC,
        description="Execution mode for this run",
    )
    input: list[Message] = Field(
        default_factory=list,
        description="Input messages for this run",
    )
    output: list[Message] = Field(
        default_factory=list,
        description="Output messages from this run",
    )
    error: RunError | None = Field(
        default=None,
        description="Error information (if status is 'failed')",
    )
    await_request: AwaitRequest | None = Field(
        default=None,
        description="Information about what's being awaited (if status is 'awaiting')",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the run was created",
    )
    started_at: datetime | None = Field(
        default=None,
        description="When the run started executing",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When the run completed",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata for this run",
    )


class Session(BaseModel):
    """
    A session maintains state across multiple agent runs.

    Sessions enable multi-turn conversations and persistent context.
    """

    model_config = ConfigDict(from_attributes=True)

    session_id: UUID = Field(
        default_factory=uuid4,
        description="Unique session identifier",
    )
    agent_name: str | None = Field(
        default=None,
        description="Primary agent for this session (if any)",
    )
    messages: list[Message] = Field(
        default_factory=list,
        description="Conversation history",
    )
    runs: list[UUID] = Field(
        default_factory=list,
        description="Run IDs associated with this session",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Session-level context data",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the session was created",
    )
    last_activity_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last activity timestamp",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="When the session expires (if applicable)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom session metadata",
    )


class CitationMetadata(BaseModel):
    """
    Metadata for citations in message parts.
    """

    model_config = ConfigDict(from_attributes=True)

    source: str = Field(description="Source identifier or URL")
    title: str | None = Field(default=None, description="Source title")
    author: str | None = Field(default=None, description="Source author")
    date: str | None = Field(default=None, description="Publication date")
    snippet: str | None = Field(default=None, description="Relevant excerpt")


class TrajectoryMetadata(BaseModel):
    """
    Metadata for agent reasoning steps or tool execution records.
    """

    model_config = ConfigDict(from_attributes=True)

    step_type: str = Field(description="Type of step (thought, action, observation)")
    tool_name: str | None = Field(default=None, description="Tool used (if action)")
    tool_input: dict[str, Any] | None = Field(default=None, description="Tool input")
    tool_output: str | None = Field(default=None, description="Tool output")
    duration_ms: int | None = Field(default=None, description="Step duration")
