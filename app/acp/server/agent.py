"""
ACP Agent Registry and Decorator

Provides agent registration and management functionality.
"""

from typing import Any, AsyncGenerator, Callable, TypeVar
from functools import wraps
import inspect

from app.acp.core.models import Message, AgentManifest, AgentMetadata
from app.acp.core.types import AgentStatus
from app.acp.server.context import Context


# Type for agent handler functions
RunYield = Message | dict[str, Any]  # Message or thought/metadata dict
RunYieldResume = list[Message] | None  # Resume data or None

AgentFunc = Callable[
    [list[Message], Context],
    AsyncGenerator[RunYield, RunYieldResume],
]

T = TypeVar("T", bound=AgentFunc)


class AgentHandler:
    """
    Wrapper for an agent handler function with its manifest.
    """

    def __init__(
        self,
        func: AgentFunc,
        manifest: AgentManifest,
    ):
        """
        Initialize the agent handler.

        Args:
            func: The agent handler function
            manifest: The agent's manifest
        """
        self.func = func
        self.manifest = manifest
        self._name = manifest.name

    @property
    def name(self) -> str:
        """Get the agent name."""
        return self._name

    async def __call__(
        self,
        input: list[Message],
        context: Context,
    ) -> AsyncGenerator[RunYield, RunYieldResume]:
        """
        Invoke the agent handler.

        Args:
            input: Input messages
            context: Execution context

        Yields:
            Messages and thoughts from the agent
        """
        async for item in self.func(input, context):
            yield item


class AgentRegistry:
    """
    Registry for managing ACP agents.

    Provides methods to register, unregister, and look up agents.
    """

    def __init__(self):
        """Initialize an empty agent registry."""
        self._agents: dict[str, AgentHandler] = {}

    def register(
        self,
        handler: AgentHandler,
    ) -> None:
        """
        Register an agent handler.

        Args:
            handler: The agent handler to register

        Raises:
            ValueError: If an agent with the same name already exists
        """
        if handler.name in self._agents:
            raise ValueError(f"Agent '{handler.name}' is already registered")
        self._agents[handler.name] = handler

    def unregister(self, name: str) -> bool:
        """
        Unregister an agent by name.

        Args:
            name: The agent name to unregister

        Returns:
            True if the agent was unregistered, False if not found
        """
        if name in self._agents:
            del self._agents[name]
            return True
        return False

    def get(self, name: str) -> AgentHandler | None:
        """
        Get an agent handler by name.

        Args:
            name: The agent name

        Returns:
            The agent handler or None if not found
        """
        return self._agents.get(name)

    def get_manifest(self, name: str) -> AgentManifest | None:
        """
        Get an agent's manifest by name.

        Args:
            name: The agent name

        Returns:
            The agent manifest or None if not found
        """
        handler = self._agents.get(name)
        return handler.manifest if handler else None

    def list_agents(
        self,
        offset: int = 0,
        limit: int = 100,
        status: AgentStatus | None = None,
    ) -> tuple[list[AgentManifest], int]:
        """
        List registered agents with pagination.

        Args:
            offset: Number of agents to skip
            limit: Maximum number to return
            status: Filter by agent status

        Returns:
            Tuple of (agent manifests, total count)
        """
        agents = list(self._agents.values())

        # Filter by status if specified
        if status:
            agents = [a for a in agents if a.manifest.status == status]

        total = len(agents)

        # Apply pagination
        agents = agents[offset : offset + limit]

        return [a.manifest for a in agents], total

    def has_agent(self, name: str) -> bool:
        """
        Check if an agent is registered.

        Args:
            name: The agent name

        Returns:
            True if registered, False otherwise
        """
        return name in self._agents

    @property
    def count(self) -> int:
        """Get the number of registered agents."""
        return len(self._agents)


def agent_decorator(
    registry: AgentRegistry,
    name: str | None = None,
    description: str | None = None,
    input_content_types: list[str] | None = None,
    output_content_types: list[str] | None = None,
    metadata: AgentMetadata | dict[str, Any] | None = None,
) -> Callable[[T], T]:
    """
    Decorator for registering agent handler functions.

    Usage:
        registry = AgentRegistry()

        @agent_decorator(registry, name="my_agent", description="My agent")
        async def my_agent(input: list[Message], context: Context):
            yield Message.agent_text("Hello!")

    Args:
        registry: The agent registry to register with
        name: Agent name (defaults to function name)
        description: Agent description (defaults to docstring)
        input_content_types: Accepted input MIME types
        output_content_types: Produced output MIME types
        metadata: Additional agent metadata

    Returns:
        Decorator function
    """

    def decorator(func: T) -> T:
        # Determine agent name
        agent_name = name or func.__name__

        # Determine description from docstring if not provided
        agent_description = description or (func.__doc__ or "").strip() or f"Agent: {agent_name}"

        # Convert metadata dict to AgentMetadata if needed
        agent_metadata = metadata
        if isinstance(metadata, dict):
            agent_metadata = AgentMetadata(**metadata)
        elif metadata is None:
            agent_metadata = AgentMetadata()

        # Create manifest
        manifest = AgentManifest(
            name=agent_name,
            description=agent_description,
            input_content_types=input_content_types or ["text/plain"],
            output_content_types=output_content_types or ["text/plain"],
            metadata=agent_metadata,
        )

        # Create handler and register
        handler = AgentHandler(func=func, manifest=manifest)
        registry.register(handler)

        # Return the original function (for direct calls if needed)
        @wraps(func)
        async def wrapper(
            input: list[Message],
            context: Context,
        ) -> AsyncGenerator[RunYield, RunYieldResume]:
            async for item in func(input, context):
                yield item

        return wrapper  # type: ignore

    return decorator


def create_agent_decorator(registry: AgentRegistry) -> Callable[..., Callable[[T], T]]:
    """
    Create a bound agent decorator for a specific registry.

    This allows for a cleaner API:
        server = ACPServer()

        @server.agent(name="my_agent")
        async def my_agent(input, context):
            ...

    Args:
        registry: The registry to bind to

    Returns:
        A partially applied agent_decorator function
    """

    def decorator(
        name: str | None = None,
        description: str | None = None,
        input_content_types: list[str] | None = None,
        output_content_types: list[str] | None = None,
        metadata: AgentMetadata | dict[str, Any] | None = None,
    ) -> Callable[[T], T]:
        return agent_decorator(
            registry=registry,
            name=name,
            description=description,
            input_content_types=input_content_types,
            output_content_types=output_content_types,
            metadata=metadata,
        )

    return decorator
