"""
ACP (Agent Communication Protocol) Module

This module provides a comprehensive implementation of the Agent Communication Protocol,
enabling standardized agent-to-agent communication with support for:
- REST-based agent discovery and invocation
- Multipart MIME-typed message handling
- Run lifecycle management (sync, async, streaming)
- Session management for multi-turn conversations
- Await/resume patterns for human-in-the-loop workflows

Usage:
    # Server-side: Create an ACP server with agents
    from app.acp import ACPServer, Message, MessagePart, Context

    server = ACPServer()

    @server.agent(name="echo", description="Echoes messages back")
    async def echo_agent(input: list[Message], context: Context):
        for msg in input:
            yield msg

    # Client-side: Call an agent via Telegram or directly
    from app.services.acp_client import ACPClientService

    async with ACPClientService(base_url="http://localhost:8000") as client:
        agents = await client.list_agents()
        result = await client.run_agent(agent="echo", message="Hello!")
"""

# Core types and enums
from app.acp.core.types import (
    RunStatus,
    AgentStatus,
    RunMode,
    ContentEncoding,
    MessageRole,
    ErrorCode,
)

# Core models
from app.acp.core.models import (
    MessagePart,
    Message,
    AgentManifest,
    AgentMetadata,
    Run,
    RunError,
    Session,
    AwaitRequest,
)

# Core schemas (Pydantic request/response models)
from app.acp.core.schemas import (
    RunCreateRequest,
    RunResumeRequest,
    RunResponse,
    AgentListResponse,
    AgentResponse,
    SessionResponse,
    ErrorResponse,
)

# Server components
from app.acp.server import (
    ACPServer,
    Context,
    AgentRegistry,
    agent_decorator,
)

# Telegram bot router for ACP commands
from app.acp.router import router as acp_router

__all__ = [
    # Types
    "RunStatus",
    "AgentStatus",
    "RunMode",
    "ContentEncoding",
    "MessageRole",
    "ErrorCode",
    # Models
    "MessagePart",
    "Message",
    "AgentManifest",
    "AgentMetadata",
    "Run",
    "RunError",
    "Session",
    "AwaitRequest",
    # Schemas
    "RunCreateRequest",
    "RunResumeRequest",
    "RunResponse",
    "AgentListResponse",
    "AgentResponse",
    "SessionResponse",
    "ErrorResponse",
    # Server
    "ACPServer",
    "Context",
    "AgentRegistry",
    "agent_decorator",
    # Router
    "acp_router",
]

__version__ = "0.1.0"
