"""
ACP Server Base

Main server class for hosting ACP agents.
"""

from datetime import datetime
from typing import Any, Callable
from uuid import UUID, uuid4

from loguru import logger

from app.acp.core.models import (
    Message,
    Run,
    Session,
    RunError,
    AgentManifest,
    AgentMetadata,
)
from app.acp.core.types import RunStatus, RunMode, ErrorCode
from app.acp.core.schemas import (
    RunCreateRequest,
    RunResumeRequest,
    RunResponse,
    AgentListResponse,
    AgentResponse,
    SessionResponse,
)
from app.acp.server.agent import (
    AgentRegistry,
    AgentHandler,
    create_agent_decorator,
    RunYield,
    RunYieldResume,
)
from app.acp.server.context import Context, ContextBuilder


class ACPServer:
    """
    ACP Server for hosting and managing agents.

    The server provides:
    - Agent registration via decorators
    - Run lifecycle management
    - Session management
    - Request handling for ACP endpoints

    Usage:
        server = ACPServer()

        @server.agent(name="echo", description="Echoes input")
        async def echo_agent(input: list[Message], context: Context):
            for msg in input:
                yield Message.agent_text(f"Echo: {msg.parts[0].content}")

        # Start the server (integration with FastAPI/ASGI)
        app = server.create_fastapi_app()
    """

    def __init__(
        self,
        name: str = "acp-server",
        version: str = "0.1.0",
    ):
        """
        Initialize the ACP server.

        Args:
            name: Server name for identification
            version: Server version string
        """
        self._name = name
        self._version = version
        self._registry = AgentRegistry()
        self._runs: dict[UUID, Run] = {}
        self._sessions: dict[UUID, Session] = {}
        self._started_at = datetime.utcnow()

        # Create bound decorator
        self._agent_decorator = create_agent_decorator(self._registry)

        logger.info(f"ACP Server '{name}' v{version} initialized")

    @property
    def name(self) -> str:
        """Get the server name."""
        return self._name

    @property
    def version(self) -> str:
        """Get the server version."""
        return self._version

    @property
    def registry(self) -> AgentRegistry:
        """Get the agent registry."""
        return self._registry

    @property
    def uptime_seconds(self) -> float:
        """Get server uptime in seconds."""
        return (datetime.utcnow() - self._started_at).total_seconds()

    def agent(
        self,
        name: str | None = None,
        description: str | None = None,
        input_content_types: list[str] | None = None,
        output_content_types: list[str] | None = None,
        metadata: AgentMetadata | dict[str, Any] | None = None,
    ) -> Callable:
        """
        Decorator for registering agent handlers.

        Usage:
            @server.agent(name="my_agent", description="My agent")
            async def my_agent(input: list[Message], context: Context):
                yield Message.agent_text("Hello!")

        Args:
            name: Agent name (defaults to function name)
            description: Agent description
            input_content_types: Accepted input MIME types
            output_content_types: Produced output MIME types
            metadata: Additional agent metadata

        Returns:
            Decorator function
        """
        return self._agent_decorator(
            name=name,
            description=description,
            input_content_types=input_content_types,
            output_content_types=output_content_types,
            metadata=metadata,
        )

    # --- Agent Operations ---

    def list_agents(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> AgentListResponse:
        """
        List all registered agents.

        Args:
            offset: Pagination offset
            limit: Maximum agents to return

        Returns:
            AgentListResponse with agents and pagination info
        """
        agents, total = self._registry.list_agents(offset=offset, limit=limit)
        return AgentListResponse(
            agents=agents,
            total=total,
            offset=offset,
            limit=limit,
        )

    def get_agent(self, name: str) -> AgentResponse | None:
        """
        Get a specific agent by name.

        Args:
            name: Agent name

        Returns:
            AgentResponse or None if not found
        """
        manifest = self._registry.get_manifest(name)
        if manifest:
            return AgentResponse(agent=manifest)
        return None

    # --- Run Operations ---

    async def create_run(
        self,
        request: RunCreateRequest,
    ) -> RunResponse:
        """
        Create and execute a new run.

        Args:
            request: Run creation request

        Returns:
            RunResponse with results
        """
        # Validate agent exists
        handler = self._registry.get(request.agent)
        if not handler:
            return self._create_error_response(
                agent_name=request.agent,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Agent '{request.agent}' not found",
            )

        # Create or get session
        session = None
        if request.session_id:
            session = self._sessions.get(request.session_id)
            if not session:
                # Create new session with provided ID
                session = Session(
                    session_id=request.session_id,
                    agent_name=request.agent,
                )
                self._sessions[request.session_id] = session

        # Create run
        run = Run(
            run_id=uuid4(),
            agent_name=request.agent,
            session_id=session.session_id if session else None,
            status=RunStatus.CREATED,
            mode=request.mode,
            input=request.input,
            metadata=request.metadata,
        )
        self._runs[run.run_id] = run

        # Execute based on mode
        if request.mode == RunMode.SYNC:
            return await self._execute_sync(run, handler, session)
        elif request.mode == RunMode.ASYNC:
            return await self._execute_async(run, handler, session)
        else:  # STREAM
            # For streaming, return immediately with run_id
            # Actual streaming handled separately
            run.status = RunStatus.IN_PROGRESS
            return self._run_to_response(run)

    async def get_run(self, run_id: UUID) -> RunResponse | None:
        """
        Get a run by ID.

        Args:
            run_id: The run ID

        Returns:
            RunResponse or None if not found
        """
        run = self._runs.get(run_id)
        if run:
            return self._run_to_response(run)
        return None

    async def resume_run(
        self,
        run_id: UUID,
        request: RunResumeRequest,
    ) -> RunResponse | None:
        """
        Resume an awaiting run.

        Args:
            run_id: The run ID to resume
            request: Resume request with input

        Returns:
            RunResponse or None if not found
        """
        run = self._runs.get(run_id)
        if not run:
            return None

        if run.status != RunStatus.AWAITING:
            return self._create_error_response(
                agent_name=run.agent_name,
                run_id=run.run_id,
                error_code=ErrorCode.CONFLICT,
                message=f"Run is not in awaiting state (current: {run.status})",
            )

        # Add resume input to run
        run.input.extend(request.input)
        run.await_request = None

        # Get handler and session
        handler = self._registry.get(run.agent_name)
        session = self._sessions.get(run.session_id) if run.session_id else None

        # Continue execution
        return await self._execute_sync(run, handler, session)

    async def cancel_run(self, run_id: UUID) -> RunResponse | None:
        """
        Cancel a running run.

        Args:
            run_id: The run ID to cancel

        Returns:
            RunResponse or None if not found
        """
        run = self._runs.get(run_id)
        if not run:
            return None

        if run.status in [RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED]:
            return self._run_to_response(run)

        run.status = RunStatus.CANCELLING
        # In a real implementation, this would signal the agent to stop
        run.status = RunStatus.CANCELLED
        run.completed_at = datetime.utcnow()

        return self._run_to_response(run)

    # --- Session Operations ---

    def get_session(self, session_id: UUID) -> SessionResponse | None:
        """
        Get a session by ID.

        Args:
            session_id: The session ID

        Returns:
            SessionResponse or None if not found
        """
        session = self._sessions.get(session_id)
        if session:
            return SessionResponse(
                session_id=session.session_id,
                agent_name=session.agent_name,
                messages=session.messages,
                run_count=len(session.runs),
                created_at=session.created_at,
                last_activity_at=session.last_activity_at,
            )
        return None

    def create_session(
        self,
        agent_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        """
        Create a new session.

        Args:
            agent_name: Primary agent for the session
            metadata: Session metadata

        Returns:
            The created session
        """
        session = Session(
            session_id=uuid4(),
            agent_name=agent_name,
            metadata=metadata or {},
        )
        self._sessions[session.session_id] = session
        return session

    # --- Internal Methods ---

    async def _execute_sync(
        self,
        run: Run,
        handler: AgentHandler,
        session: Session | None,
    ) -> RunResponse:
        """Execute a run synchronously."""
        run.status = RunStatus.IN_PROGRESS
        run.started_at = datetime.utcnow()

        # Build context
        context = (
            ContextBuilder()
            .with_run(run)
            .with_session(session)
            .with_metadata(run.metadata)
            .build()
        )

        try:
            outputs: list[Message] = []

            # Execute the agent
            async for item in handler(run.input, context):
                if isinstance(item, Message):
                    outputs.append(item)
                    # Add to session history
                    if session:
                        session.messages.append(item)
                elif isinstance(item, dict):
                    # Handle thoughts/metadata
                    if "await" in item:
                        # Agent is awaiting input
                        run.status = RunStatus.AWAITING
                        run.await_request = item["await"]
                        run.output = outputs
                        return self._run_to_response(run)

            # Run completed successfully
            run.status = RunStatus.COMPLETED
            run.output = outputs
            run.completed_at = datetime.utcnow()

            # Update session
            if session:
                session.runs.append(run.run_id)
                session.last_activity_at = datetime.utcnow()

        except Exception as e:
            logger.exception(f"Error executing agent '{run.agent_name}'")
            run.status = RunStatus.FAILED
            run.error = RunError(
                code=ErrorCode.AGENT_ERROR,
                message=str(e),
            )
            run.completed_at = datetime.utcnow()

        return self._run_to_response(run)

    async def _execute_async(
        self,
        run: Run,
        handler: AgentHandler,
        session: Session | None,
    ) -> RunResponse:
        """Start async execution and return immediately."""
        run.status = RunStatus.IN_PROGRESS
        run.started_at = datetime.utcnow()

        # In a real implementation, this would spawn a background task
        # For now, we just return the in-progress response
        # The actual execution would be handled by a task queue

        return self._run_to_response(run)

    def _run_to_response(self, run: Run) -> RunResponse:
        """Convert a Run to a RunResponse."""
        return RunResponse(
            run_id=run.run_id,
            agent_name=run.agent_name,
            session_id=run.session_id,
            status=run.status,
            output=run.output,
            error=run.error,
            await_request=run.await_request,
            created_at=run.created_at,
            completed_at=run.completed_at,
        )

    def _create_error_response(
        self,
        agent_name: str,
        error_code: ErrorCode,
        message: str,
        run_id: UUID | None = None,
    ) -> RunResponse:
        """Create an error response."""
        return RunResponse(
            run_id=run_id or uuid4(),
            agent_name=agent_name,
            status=RunStatus.FAILED,
            error=RunError(code=error_code, message=message),
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
