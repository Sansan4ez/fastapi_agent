"""
ACP FastAPI Integration

Provides FastAPI router and adapter for hosting ACP servers.
"""

from typing import Any
from uuid import UUID

from loguru import logger

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
from app.acp.server.handlers import (
    list_agents_handler,
    get_agent_handler,
    create_run_handler,
    get_run_handler,
    resume_run_handler,
    cancel_run_handler,
    get_session_handler,
    health_handler,
)


class ACPFastAPIAdapter:
    """
    Adapter for integrating ACP server with FastAPI.

    Provides route handlers that can be mounted on a FastAPI app.
    """

    def __init__(self, server: ACPServer):
        """
        Initialize the adapter.

        Args:
            server: ACP server instance
        """
        self._server = server

    @property
    def server(self) -> ACPServer:
        """Get the ACP server."""
        return self._server

    async def list_agents(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> AgentListResponse:
        """Handle GET /agents."""
        return await list_agents_handler(self._server, offset, limit)

    async def get_agent(self, name: str) -> AgentResponse | ErrorResponse:
        """Handle GET /agents/{name}."""
        return await get_agent_handler(self._server, name)

    async def create_run(self, request: RunCreateRequest) -> RunResponse:
        """Handle POST /runs."""
        return await create_run_handler(self._server, request)

    async def get_run(self, run_id: UUID) -> RunResponse | ErrorResponse:
        """Handle GET /runs/{run_id}."""
        return await get_run_handler(self._server, run_id)

    async def resume_run(
        self,
        run_id: UUID,
        request: RunResumeRequest,
    ) -> RunResponse | ErrorResponse:
        """Handle POST /runs/{run_id}."""
        return await resume_run_handler(self._server, run_id, request)

    async def cancel_run(self, run_id: UUID) -> RunResponse | ErrorResponse:
        """Handle POST /runs/{run_id}/cancel."""
        return await cancel_run_handler(self._server, run_id)

    async def get_session(self, session_id: UUID) -> SessionResponse | ErrorResponse:
        """Handle GET /sessions/{session_id}."""
        return await get_session_handler(self._server, session_id)

    async def health(self) -> HealthResponse:
        """Handle GET /health."""
        return await health_handler(self._server)


def create_acp_router(server: ACPServer, prefix: str = "/acp"):
    """
    Create a FastAPI router with ACP endpoints.

    This function creates a router that can be included in a FastAPI app:

        from fastapi import FastAPI
        from app.acp.server import ACPServer
        from app.acp.integration.fastapi import create_acp_router

        app = FastAPI()
        acp_server = ACPServer()
        app.include_router(create_acp_router(acp_server))

    Args:
        server: ACP server instance
        prefix: URL prefix for ACP routes

    Returns:
        FastAPI APIRouter

    Note:
        This function requires FastAPI to be installed.
        Import is deferred to avoid hard dependency.
    """
    try:
        from fastapi import APIRouter, HTTPException, Query
        from fastapi.responses import StreamingResponse
    except ImportError:
        raise ImportError(
            "FastAPI is required for create_acp_router. "
            "Install it with: pip install fastapi"
        )

    router = APIRouter(prefix=prefix, tags=["ACP"])
    adapter = ACPFastAPIAdapter(server)

    @router.get("/health", response_model=HealthResponse)
    async def health():
        """Get server health status."""
        return await adapter.health()

    @router.get("/agents", response_model=AgentListResponse)
    async def list_agents(
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=1000),
    ):
        """List available agents."""
        return await adapter.list_agents(offset=offset, limit=limit)

    @router.get("/agents/{name}")
    async def get_agent(name: str):
        """Get agent details by name."""
        result = await adapter.get_agent(name)
        if isinstance(result, ErrorResponse):
            raise HTTPException(status_code=404, detail=result.message)
        return result

    @router.post("/runs", response_model=RunResponse)
    async def create_run(request: RunCreateRequest):
        """Create and execute a new agent run."""
        return await adapter.create_run(request)

    @router.get("/runs/{run_id}")
    async def get_run(run_id: UUID):
        """Get run details by ID."""
        result = await adapter.get_run(run_id)
        if isinstance(result, ErrorResponse):
            raise HTTPException(status_code=404, detail=result.message)
        return result

    @router.post("/runs/{run_id}")
    async def resume_run(run_id: UUID, request: RunResumeRequest):
        """Resume an awaiting run."""
        result = await adapter.resume_run(run_id, request)
        if isinstance(result, ErrorResponse):
            if result.code == ErrorCode.NOT_FOUND:
                raise HTTPException(status_code=404, detail=result.message)
            elif result.code == ErrorCode.CONFLICT:
                raise HTTPException(status_code=409, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)
        return result

    @router.post("/runs/{run_id}/cancel")
    async def cancel_run(run_id: UUID):
        """Cancel a running agent execution."""
        result = await adapter.cancel_run(run_id)
        if isinstance(result, ErrorResponse):
            raise HTTPException(status_code=404, detail=result.message)
        return result

    @router.get("/sessions/{session_id}")
    async def get_session(session_id: UUID):
        """Get session details by ID."""
        result = await adapter.get_session(session_id)
        if isinstance(result, ErrorResponse):
            raise HTTPException(status_code=404, detail=result.message)
        return result

    return router


def create_streaming_response(server: ACPServer, request: RunCreateRequest):
    """
    Create a streaming response for SSE.

    Args:
        server: ACP server instance
        request: Run creation request

    Returns:
        StreamingResponse for FastAPI

    Note:
        This function requires FastAPI to be installed.
    """
    try:
        from fastapi.responses import StreamingResponse
    except ImportError:
        raise ImportError("FastAPI is required for streaming responses")

    from app.acp.protocol.streaming import SSEFormatter, EventType, StreamEvent
    from app.acp.core.types import RunMode

    async def event_generator():
        # Ensure streaming mode
        request.mode = RunMode.STREAM

        # Create the run
        response = await server.create_run(request)

        # Send initial status
        yield SSEFormatter.format_status(response.status, str(response.run_id))

        # If sync completion (small response), send all at once
        if response.status.value in ["completed", "failed"]:
            for message in response.output:
                yield SSEFormatter.format_message(message)
            return

        # For streaming, we would need to implement generator-based execution
        # This is a placeholder for the full streaming implementation
        yield SSEFormatter.format_event(
            StreamEvent(
                event_type=EventType.MESSAGE,
                data={"note": "Full streaming implementation pending"},
            )
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
