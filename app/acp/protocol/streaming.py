"""
ACP Streaming Support

Provides utilities for streaming responses using Server-Sent Events (SSE)
and other streaming protocols.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator
from uuid import uuid4

from app.acp.core.models import Message, MessagePart
from app.acp.core.types import RunStatus


class EventType(str, Enum):
    """Types of streaming events."""

    # Run lifecycle events
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    RUN_AWAITING = "run.awaiting"
    RUN_CANCELLED = "run.cancelled"

    # Message events
    MESSAGE = "message"
    MESSAGE_DELTA = "message.delta"
    MESSAGE_COMPLETE = "message.complete"

    # Agent events
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"

    # System events
    HEARTBEAT = "heartbeat"
    ERROR = "error"


@dataclass
class StreamEvent:
    """A streaming event."""

    event_type: EventType
    data: dict[str, Any]
    event_id: str | None = None
    timestamp: datetime | None = None

    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid4())
        if not self.timestamp:
            self.timestamp = datetime.utcnow()


class SSEFormatter:
    """
    Server-Sent Events formatter.

    Formats events according to the SSE specification:
    https://html.spec.whatwg.org/multipage/server-sent-events.html
    """

    @staticmethod
    def format_event(event: StreamEvent) -> str:
        """
        Format an event as SSE.

        Args:
            event: The event to format

        Returns:
            SSE-formatted string
        """
        lines = []

        # Event ID (optional but recommended)
        if event.event_id:
            lines.append(f"id: {event.event_id}")

        # Event type
        lines.append(f"event: {event.event_type.value}")

        # Data (JSON-encoded)
        data = {
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            **event.data,
        }
        lines.append(f"data: {json.dumps(data)}")

        # SSE requires double newline to terminate event
        return "\n".join(lines) + "\n\n"

    @staticmethod
    def format_message(message: Message) -> str:
        """
        Format a message as an SSE event.

        Args:
            message: The message to format

        Returns:
            SSE-formatted string
        """
        event = StreamEvent(
            event_type=EventType.MESSAGE,
            data=message.model_dump(mode="json"),
        )
        return SSEFormatter.format_event(event)

    @staticmethod
    def format_delta(
        content: str,
        part_index: int = 0,
        message_id: str | None = None,
    ) -> str:
        """
        Format a content delta as an SSE event.

        Args:
            content: The content delta
            part_index: Index of the part being updated
            message_id: Associated message ID

        Returns:
            SSE-formatted string
        """
        event = StreamEvent(
            event_type=EventType.MESSAGE_DELTA,
            data={
                "content": content,
                "part_index": part_index,
                "message_id": message_id,
            },
        )
        return SSEFormatter.format_event(event)

    @staticmethod
    def format_status(status: RunStatus, run_id: str) -> str:
        """
        Format a status change as an SSE event.

        Args:
            status: The new status
            run_id: The run ID

        Returns:
            SSE-formatted string
        """
        event_type_map = {
            RunStatus.IN_PROGRESS: EventType.RUN_STARTED,
            RunStatus.COMPLETED: EventType.RUN_COMPLETED,
            RunStatus.FAILED: EventType.RUN_FAILED,
            RunStatus.AWAITING: EventType.RUN_AWAITING,
            RunStatus.CANCELLED: EventType.RUN_CANCELLED,
        }

        event = StreamEvent(
            event_type=event_type_map.get(status, EventType.MESSAGE),
            data={"run_id": run_id, "status": status.value},
        )
        return SSEFormatter.format_event(event)

    @staticmethod
    def format_heartbeat() -> str:
        """
        Format a heartbeat event.

        Returns:
            SSE-formatted heartbeat (comment)
        """
        return ": heartbeat\n\n"

    @staticmethod
    def format_error(error_code: str, message: str) -> str:
        """
        Format an error as an SSE event.

        Args:
            error_code: Error code
            message: Error message

        Returns:
            SSE-formatted string
        """
        event = StreamEvent(
            event_type=EventType.ERROR,
            data={"code": error_code, "message": message},
        )
        return SSEFormatter.format_event(event)


class StreamHandler:
    """
    Handler for processing and generating streaming events.

    Provides:
    - Event buffering
    - Delta accumulation
    - Complete message reconstruction
    """

    def __init__(self):
        """Initialize the stream handler."""
        self._buffer: list[StreamEvent] = []
        self._current_message: dict[str, Any] | None = None
        self._accumulated_content: dict[int, str] = {}

    def add_event(self, event: StreamEvent) -> None:
        """
        Add an event to the buffer.

        Args:
            event: Event to add
        """
        self._buffer.append(event)

        # Handle delta accumulation
        if event.event_type == EventType.MESSAGE_DELTA:
            part_index = event.data.get("part_index", 0)
            content = event.data.get("content", "")
            self._accumulated_content[part_index] = (
                self._accumulated_content.get(part_index, "") + content
            )

    def get_accumulated_content(self, part_index: int = 0) -> str:
        """
        Get accumulated content for a part.

        Args:
            part_index: The part index

        Returns:
            Accumulated content string
        """
        return self._accumulated_content.get(part_index, "")

    def clear(self) -> None:
        """Clear the buffer and accumulated content."""
        self._buffer.clear()
        self._current_message = None
        self._accumulated_content.clear()

    def get_events(self) -> list[StreamEvent]:
        """Get all buffered events."""
        return self._buffer.copy()

    def reconstruct_message(self, role: str = "agent") -> Message:
        """
        Reconstruct a complete message from accumulated content.

        Args:
            role: Message role

        Returns:
            Reconstructed Message
        """
        parts = []
        for part_index in sorted(self._accumulated_content.keys()):
            parts.append(
                MessagePart(
                    content=self._accumulated_content[part_index],
                    content_type="text/plain",
                )
            )

        return Message(
            role=role,
            parts=parts,
            created_at=datetime.utcnow(),
        )


async def stream_messages(
    messages: list[Message],
    chunk_size: int = 10,
) -> AsyncGenerator[str, None]:
    """
    Stream messages as SSE events.

    Simulates streaming by chunking message content.

    Args:
        messages: Messages to stream
        chunk_size: Characters per chunk

    Yields:
        SSE-formatted event strings
    """
    for message in messages:
        for part_index, part in enumerate(message.parts):
            if not part.content:
                continue

            content = part.content

            # Stream in chunks
            for i in range(0, len(content), chunk_size):
                chunk = content[i : i + chunk_size]
                yield SSEFormatter.format_delta(
                    content=chunk,
                    part_index=part_index,
                )

        # Signal message complete
        yield SSEFormatter.format_message(message)


async def stream_with_heartbeat(
    stream: AsyncGenerator[str, None],
    heartbeat_interval: float = 30.0,
) -> AsyncGenerator[str, None]:
    """
    Wrap a stream with periodic heartbeats.

    Prevents connection timeouts on slow streams.

    Args:
        stream: The underlying stream
        heartbeat_interval: Seconds between heartbeats

    Yields:
        SSE-formatted event strings
    """
    import asyncio

    last_event_time = asyncio.get_event_loop().time()

    async for event in stream:
        yield event
        last_event_time = asyncio.get_event_loop().time()

    # Send final heartbeat
    yield SSEFormatter.format_heartbeat()
