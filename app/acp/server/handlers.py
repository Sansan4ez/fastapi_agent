"""
ACP Server HTTP Handlers

Standalone handler functions for ACP endpoints.
These can be integrated with any ASGI framework (FastAPI, Starlette, etc.)
"""

from uuid import UUID

from app.acp.core.schemas import (
    RunCreateRequest,
    RunResumeRequest,
    RunResponse,
    AgentListResponse,
    AgentResponse,
    SessionResponse,
    ErrorResponse,
    HealthResponse,
)
from app.acp.core.types import ErrorCode
from app.acp.server.base import ACPServer


async def list_agents_handler(
    server: ACPServer,
    offset: int = 0,
    limit: int = 100,
) -> AgentListResponse:
    """
    Handle GET /agents request.

    Lists all available agents with pagination.

    Args:
        server: The ACP server instance
        offset: Pagination offset
        limit: Maximum agents to return

    Returns:
        AgentListResponse with agents list
    """
    return server.list_agents(offset=offset, limit=limit)


async def get_agent_handler(
    server: ACPServer,
    agent_name: str,
) -> AgentResponse | ErrorResponse:
    """
    Handle GET /agents/{name} request.

    Get details for a specific agent.

    Args:
        server: The ACP server instance
        agent_name: Name of the agent

    Returns:
        AgentResponse or ErrorResponse if not found
    """
    response = server.get_agent(agent_name)
    if response:
        return response
    return ErrorResponse(
        code=ErrorCode.NOT_FOUND,
        message=f"Agent '{agent_name}' not found",
    )


async def create_run_handler(
    server: ACPServer,
    request: RunCreateRequest,
) -> RunResponse:
    """
    Handle POST /runs request.

    Create and execute a new agent run.

    Args:
        server: The ACP server instance
        request: Run creation request

    Returns:
        RunResponse with execution results
    """
    return await server.create_run(request)


async def get_run_handler(
    server: ACPServer,
    run_id: UUID,
) -> RunResponse | ErrorResponse:
    """
    Handle GET /runs/{run_id} request.

    Get status and details of a specific run.

    Args:
        server: The ACP server instance
        run_id: The run ID

    Returns:
        RunResponse or ErrorResponse if not found
    """
    response = await server.get_run(run_id)
    if response:
        return response
    return ErrorResponse(
        code=ErrorCode.NOT_FOUND,
        message=f"Run '{run_id}' not found",
    )


async def resume_run_handler(
    server: ACPServer,
    run_id: UUID,
    request: RunResumeRequest,
) -> RunResponse | ErrorResponse:
    """
    Handle POST /runs/{run_id} request.

    Resume an awaiting run with new input.

    Args:
        server: The ACP server instance
        run_id: The run ID to resume
        request: Resume request with input

    Returns:
        RunResponse or ErrorResponse if not found/invalid state
    """
    response = await server.resume_run(run_id, request)
    if response:
        return response
    return ErrorResponse(
        code=ErrorCode.NOT_FOUND,
        message=f"Run '{run_id}' not found",
    )


async def cancel_run_handler(
    server: ACPServer,
    run_id: UUID,
) -> RunResponse | ErrorResponse:
    """
    Handle POST /runs/{run_id}/cancel request.

    Cancel a running agent execution.

    Args:
        server: The ACP server instance
        run_id: The run ID to cancel

    Returns:
        RunResponse or ErrorResponse if not found
    """
    response = await server.cancel_run(run_id)
    if response:
        return response
    return ErrorResponse(
        code=ErrorCode.NOT_FOUND,
        message=f"Run '{run_id}' not found",
    )


async def get_session_handler(
    server: ACPServer,
    session_id: UUID,
) -> SessionResponse | ErrorResponse:
    """
    Handle GET /sessions/{session_id} request.

    Get session details and history.

    Args:
        server: The ACP server instance
        session_id: The session ID

    Returns:
        SessionResponse or ErrorResponse if not found
    """
    response = server.get_session(session_id)
    if response:
        return response
    return ErrorResponse(
        code=ErrorCode.NOT_FOUND,
        message=f"Session '{session_id}' not found",
    )


async def health_handler(
    server: ACPServer,
) -> HealthResponse:
    """
    Handle GET /health request.

    Get server health status.

    Args:
        server: The ACP server instance

    Returns:
        HealthResponse with status information
    """
    return HealthResponse(
        status="healthy",
        version=server.version,
        agent_count=server.registry.count,
        uptime_seconds=server.uptime_seconds,
    )
