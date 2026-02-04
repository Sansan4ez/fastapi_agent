"""
ACP Session Manager

Provides session management functionality for the ACP client.
"""

from typing import Any
from uuid import UUID, uuid4
from datetime import datetime

from loguru import logger

from app.acp.core.models import Message, Session
from app.acp.core.schemas import SessionResponse


class SessionManager:
    """
    Manager for ACP session operations.

    Provides:
    - Local session tracking
    - Session state management
    - Multi-turn conversation support
    """

    def __init__(self):
        """Initialize the session manager."""
        self._sessions: dict[UUID, LocalSession] = {}

    def create_session(
        self,
        agent_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "LocalSession":
        """
        Create a new local session.

        Args:
            agent_name: Primary agent for the session
            metadata: Session metadata

        Returns:
            LocalSession instance
        """
        session = LocalSession(
            agent_name=agent_name,
            metadata=metadata or {},
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: UUID) -> "LocalSession | None":
        """
        Get a session by ID.

        Args:
            session_id: The session ID

        Returns:
            LocalSession or None
        """
        return self._sessions.get(session_id)

    def close_session(self, session_id: UUID) -> bool:
        """
        Close and remove a session.

        Args:
            session_id: The session ID

        Returns:
            True if session was closed
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> list["LocalSession"]:
        """Get all active sessions."""
        return list(self._sessions.values())

    def get_sessions_for_agent(self, agent_name: str) -> list["LocalSession"]:
        """Get sessions for a specific agent."""
        return [s for s in self._sessions.values() if s.agent_name == agent_name]


class LocalSession:
    """
    Local session state for client-side tracking.

    Maintains conversation history and context between runs.
    """

    def __init__(
        self,
        session_id: UUID | None = None,
        agent_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize a local session.

        Args:
            session_id: Session ID (generated if not provided)
            agent_name: Primary agent for the session
            metadata: Session metadata
        """
        self._session_id = session_id or uuid4()
        self._agent_name = agent_name
        self._metadata = metadata or {}
        self._messages: list[Message] = []
        self._context: dict[str, Any] = {}
        self._run_ids: list[UUID] = []
        self._created_at = datetime.utcnow()
        self._last_activity_at = datetime.utcnow()

    @property
    def session_id(self) -> UUID:
        """Get the session ID."""
        return self._session_id

    @property
    def agent_name(self) -> str | None:
        """Get the agent name."""
        return self._agent_name

    @property
    def messages(self) -> list[Message]:
        """Get the conversation history."""
        return self._messages

    @property
    def context(self) -> dict[str, Any]:
        """Get the session context."""
        return self._context

    @property
    def run_count(self) -> int:
        """Get the number of runs."""
        return len(self._run_ids)

    @property
    def created_at(self) -> datetime:
        """Get creation timestamp."""
        return self._created_at

    @property
    def last_activity_at(self) -> datetime:
        """Get last activity timestamp."""
        return self._last_activity_at

    def add_message(self, message: Message) -> None:
        """
        Add a message to the conversation history.

        Args:
            message: Message to add
        """
        self._messages.append(message)
        self._last_activity_at = datetime.utcnow()

    def add_messages(self, messages: list[Message]) -> None:
        """
        Add multiple messages to the history.

        Args:
            messages: Messages to add
        """
        self._messages.extend(messages)
        self._last_activity_at = datetime.utcnow()

    def add_run(self, run_id: UUID) -> None:
        """
        Record a run ID for this session.

        Args:
            run_id: The run ID
        """
        self._run_ids.append(run_id)
        self._last_activity_at = datetime.utcnow()

    def set_context(self, key: str, value: Any) -> None:
        """
        Set a context value.

        Args:
            key: Context key
            value: Context value
        """
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """
        Get a context value.

        Args:
            key: Context key
            default: Default value

        Returns:
            Context value or default
        """
        return self._context.get(key, default)

    def clear_context(self) -> None:
        """Clear all context values."""
        self._context.clear()

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._messages.clear()

    def get_last_message(self, role: str | None = None) -> Message | None:
        """
        Get the last message, optionally filtered by role.

        Args:
            role: Filter by role (user, agent)

        Returns:
            Last message or None
        """
        for msg in reversed(self._messages):
            if role is None or msg.role == role:
                return msg
        return None

    def get_messages_since(self, count: int) -> list[Message]:
        """
        Get the last N messages.

        Args:
            count: Number of messages

        Returns:
            List of messages
        """
        return self._messages[-count:] if count > 0 else []

    def to_session_response(self) -> SessionResponse:
        """Convert to SessionResponse schema."""
        return SessionResponse(
            session_id=self._session_id,
            agent_name=self._agent_name,
            messages=self._messages,
            run_count=len(self._run_ids),
            created_at=self._created_at,
            last_activity_at=self._last_activity_at,
        )
