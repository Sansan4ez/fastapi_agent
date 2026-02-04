"""
ACP Server Context

Provides execution context for agent handlers, including session state,
metadata, and utility methods.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from app.acp.core.models import Message, Session, Run, AwaitRequest
from app.acp.core.types import RunStatus


class Context:
    """
    Execution context provided to agent handlers.

    The context provides access to:
    - Current run information
    - Session state and history
    - Metadata and configuration
    - Utility methods for common operations
    """

    def __init__(
        self,
        run: Run,
        session: Session | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize the execution context.

        Args:
            run: The current run being executed
            session: Optional session for multi-turn conversations
            metadata: Optional metadata dictionary
        """
        self._run = run
        self._session = session
        self._metadata = metadata or {}
        self._intermediate_outputs: list[Message] = []

    @property
    def run_id(self) -> UUID:
        """Get the current run ID."""
        return self._run.run_id

    @property
    def session_id(self) -> UUID | None:
        """Get the session ID if available."""
        return self._run.session_id

    @property
    def agent_name(self) -> str:
        """Get the name of the agent being executed."""
        return self._run.agent_name

    @property
    def run(self) -> Run:
        """Get the full run object."""
        return self._run

    @property
    def session(self) -> Session | None:
        """Get the session object if available."""
        return self._session

    @property
    def metadata(self) -> dict[str, Any]:
        """Get the metadata dictionary."""
        return self._metadata

    @property
    def messages(self) -> list[Message]:
        """Get conversation history from the session."""
        if self._session:
            return self._session.messages
        return self._run.input

    @property
    def intermediate_outputs(self) -> list[Message]:
        """Get intermediate outputs generated during this run."""
        return self._intermediate_outputs

    def get_context_value(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the session or run context.

        Args:
            key: The context key to look up
            default: Default value if key not found

        Returns:
            The context value or default
        """
        # Check run metadata first
        if key in self._run.metadata:
            return self._run.metadata[key]

        # Then check session context
        if self._session and key in self._session.context:
            return self._session.context[key]

        # Then check context metadata
        if key in self._metadata:
            return self._metadata[key]

        return default

    def set_context_value(self, key: str, value: Any) -> None:
        """
        Set a value in the session context.

        Args:
            key: The context key
            value: The value to store
        """
        if self._session:
            self._session.context[key] = value
        else:
            self._metadata[key] = value

    def add_intermediate_output(self, message: Message) -> None:
        """
        Add an intermediate output message.

        Intermediate outputs are partial results that can be
        streamed to the client during execution.

        Args:
            message: The message to add
        """
        self._intermediate_outputs.append(message)

    def create_await_request(
        self,
        await_type: str,
        description: str | None = None,
        schema: dict[str, Any] | None = None,
        timeout_seconds: int | None = None,
    ) -> AwaitRequest:
        """
        Create an await request for pausing execution.

        Use this when the agent needs external information
        to continue (human-in-the-loop pattern).

        Args:
            await_type: Type of information being awaited
            description: Human-readable description
            schema: JSON Schema for expected response
            timeout_seconds: How long to wait before timeout

        Returns:
            An AwaitRequest object
        """
        return AwaitRequest(
            type=await_type,
            description=description,
            schema=schema,
            timeout_seconds=timeout_seconds,
        )

    def get_last_user_message(self) -> Message | None:
        """
        Get the most recent user message.

        Returns:
            The last user message or None
        """
        for message in reversed(self.messages):
            if message.role == "user":
                return message
        return None

    def get_message_text(self, message: Message) -> str:
        """
        Extract text content from a message.

        Concatenates all text/plain parts.

        Args:
            message: The message to extract text from

        Returns:
            Combined text content
        """
        texts = []
        for part in message.parts:
            if part.content_type == "text/plain" and part.content:
                texts.append(part.content)
        return "\n".join(texts)

    def update_session_activity(self) -> None:
        """Update the session's last activity timestamp."""
        if self._session:
            self._session.last_activity_at = datetime.utcnow()


class ContextBuilder:
    """
    Builder for creating Context objects.
    """

    def __init__(self):
        self._run: Run | None = None
        self._session: Session | None = None
        self._metadata: dict[str, Any] = {}

    def with_run(self, run: Run) -> "ContextBuilder":
        """Set the run for the context."""
        self._run = run
        return self

    def with_session(self, session: Session) -> "ContextBuilder":
        """Set the session for the context."""
        self._session = session
        return self

    def with_metadata(self, metadata: dict[str, Any]) -> "ContextBuilder":
        """Set metadata for the context."""
        self._metadata = metadata
        return self

    def add_metadata(self, key: str, value: Any) -> "ContextBuilder":
        """Add a single metadata entry."""
        self._metadata[key] = value
        return self

    def build(self) -> Context:
        """
        Build the Context object.

        Raises:
            ValueError: If run is not set
        """
        if self._run is None:
            raise ValueError("Run must be set before building context")

        return Context(
            run=self._run,
            session=self._session,
            metadata=self._metadata,
        )
