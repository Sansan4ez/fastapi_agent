"""
ACP Telegram Integration

Provides adapter for integrating ACP agents with Telegram bots via Aiogram.
"""

from typing import Any, Callable, Awaitable
from uuid import UUID

from loguru import logger

from app.acp.core.models import Message, MessagePart, Session
from app.acp.core.types import RunStatus, RunMode
from app.acp.core.schemas import RunCreateRequest, RunResponse
from app.acp.client.base import ACPClient, ACPClientError
from app.acp.client.session import SessionManager, LocalSession


class TelegramAdapter:
    """
    Adapter for integrating ACP with Telegram bots.

    Provides:
    - Conversion between Telegram messages and ACP messages
    - Session management per chat
    - Response formatting for Telegram
    """

    def __init__(
        self,
        client: ACPClient,
        default_agent: str | None = None,
    ):
        """
        Initialize the Telegram adapter.

        Args:
            client: ACP client for server communication
            default_agent: Default agent to use for messages
        """
        self._client = client
        self._default_agent = default_agent
        self._session_manager = SessionManager()
        self._chat_sessions: dict[int, UUID] = {}  # chat_id -> session_id

    @property
    def client(self) -> ACPClient:
        """Get the ACP client."""
        return self._client

    @property
    def session_manager(self) -> SessionManager:
        """Get the session manager."""
        return self._session_manager

    def get_or_create_session(
        self,
        chat_id: int,
        agent_name: str | None = None,
    ) -> LocalSession:
        """
        Get or create a session for a Telegram chat.

        Args:
            chat_id: Telegram chat ID
            agent_name: Agent name for new sessions

        Returns:
            LocalSession for the chat
        """
        session_id = self._chat_sessions.get(chat_id)

        if session_id:
            session = self._session_manager.get_session(session_id)
            if session:
                return session

        # Create new session
        session = self._session_manager.create_session(
            agent_name=agent_name or self._default_agent,
            metadata={"telegram_chat_id": chat_id},
        )
        self._chat_sessions[chat_id] = session.session_id
        return session

    def close_session(self, chat_id: int) -> bool:
        """
        Close the session for a chat.

        Args:
            chat_id: Telegram chat ID

        Returns:
            True if session was closed
        """
        session_id = self._chat_sessions.pop(chat_id, None)
        if session_id:
            return self._session_manager.close_session(session_id)
        return False

    @staticmethod
    def telegram_to_acp_message(
        text: str,
        user_id: int,
        username: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> Message:
        """
        Convert a Telegram message to an ACP message.

        Args:
            text: Message text
            user_id: Telegram user ID
            username: Optional username
            attachments: Optional file attachments

        Returns:
            ACP Message
        """
        parts = [
            MessagePart(
                content=text,
                content_type="text/plain",
                metadata={
                    "telegram_user_id": user_id,
                    "telegram_username": username,
                },
            )
        ]

        # Add attachment parts if present
        if attachments:
            for attachment in attachments:
                parts.append(
                    MessagePart(
                        content_url=attachment.get("url"),
                        content_type=attachment.get("mime_type", "application/octet-stream"),
                        name=attachment.get("file_name"),
                        metadata=attachment.get("metadata"),
                    )
                )

        return Message(role="user", parts=parts)

    @staticmethod
    def acp_to_telegram_text(response: RunResponse) -> str:
        """
        Extract text content from an ACP response for Telegram.

        Args:
            response: ACP run response

        Returns:
            Text suitable for Telegram message
        """
        if response.status == RunStatus.FAILED:
            error_msg = response.error.message if response.error else "Unknown error"
            return f"❌ Error: {error_msg}"

        if response.status == RunStatus.AWAITING:
            await_msg = (
                response.await_request.description
                if response.await_request
                else "Waiting for input"
            )
            return f"⏳ {await_msg}"

        # Extract text from output messages
        texts = []
        for message in response.output:
            for part in message.parts:
                if part.content_type == "text/plain" and part.content:
                    texts.append(part.content)

        return "\n".join(texts) if texts else "✅ Completed (no output)"

    @staticmethod
    def format_for_telegram(
        text: str,
        max_length: int = 4096,
        parse_mode: str | None = None,
    ) -> list[str]:
        """
        Format text for Telegram, splitting if necessary.

        Args:
            text: Text to format
            max_length: Maximum message length (Telegram limit is 4096)
            parse_mode: Parse mode (HTML, Markdown, etc.)

        Returns:
            List of message chunks
        """
        if len(text) <= max_length:
            return [text]

        # Split on newlines first, then by length
        chunks = []
        current_chunk = ""

        for line in text.split("\n"):
            if len(current_chunk) + len(line) + 1 <= max_length:
                current_chunk += ("\n" if current_chunk else "") + line
            else:
                if current_chunk:
                    chunks.append(current_chunk)

                # Handle lines longer than max_length
                while len(line) > max_length:
                    chunks.append(line[:max_length])
                    line = line[max_length:]

                current_chunk = line

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    async def process_message(
        self,
        chat_id: int,
        text: str,
        user_id: int,
        username: str | None = None,
        agent_name: str | None = None,
    ) -> str:
        """
        Process a Telegram message through ACP.

        Args:
            chat_id: Telegram chat ID
            text: Message text
            user_id: Telegram user ID
            username: Optional username
            agent_name: Agent to use (falls back to default)

        Returns:
            Response text for Telegram
        """
        agent = agent_name or self._default_agent
        if not agent:
            return "❌ No agent configured. Use /agent to set one."

        # Get or create session
        session = self.get_or_create_session(chat_id, agent)

        # Convert to ACP message
        acp_message = self.telegram_to_acp_message(
            text=text,
            user_id=user_id,
            username=username,
        )

        # Add to session history
        session.add_message(acp_message)

        try:
            # Run the agent
            response = await self._client.run_sync(
                agent=agent,
                input=[acp_message],
                session_id=session.session_id,
            )

            # Track the run
            session.add_run(response.run_id)

            # Add response to session history
            for msg in response.output:
                session.add_message(msg)

            # Convert to Telegram format
            return self.acp_to_telegram_text(response)

        except ACPClientError as e:
            logger.error(f"ACP client error: {e}")
            return f"❌ Error: {e}"
        except Exception as e:
            logger.exception(f"Unexpected error processing message")
            return f"❌ Unexpected error: {str(e)}"

    async def list_available_agents(self) -> list[str]:
        """
        Get list of available agent names.

        Returns:
            List of agent names
        """
        try:
            response = await self._client.list_agents()
            return [agent.name for agent in response.agents]
        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return []


class TelegramCallbackHandler:
    """
    Handler for Telegram callback queries related to ACP.

    Useful for interactive features like:
    - Agent selection buttons
    - Confirmation dialogs
    - Run status updates
    """

    def __init__(self, adapter: TelegramAdapter):
        """
        Initialize the callback handler.

        Args:
            adapter: The Telegram adapter
        """
        self._adapter = adapter
        self._handlers: dict[str, Callable[[int, str], Awaitable[str]]] = {}

    def register_handler(
        self,
        prefix: str,
        handler: Callable[[int, str], Awaitable[str]],
    ) -> None:
        """
        Register a callback handler for a prefix.

        Args:
            prefix: Callback data prefix (e.g., "agent_select")
            handler: Async handler function (chat_id, data) -> response
        """
        self._handlers[prefix] = handler

    async def handle_callback(
        self,
        chat_id: int,
        callback_data: str,
    ) -> str | None:
        """
        Handle a callback query.

        Args:
            chat_id: Telegram chat ID
            callback_data: Callback data string

        Returns:
            Response text or None if not handled
        """
        for prefix, handler in self._handlers.items():
            if callback_data.startswith(prefix):
                return await handler(chat_id, callback_data)
        return None
