"""
ACP Message Encoding and Decoding

Provides utilities for encoding and decoding ACP messages,
including multipart MIME handling and content transformation.
"""

import base64
import json
from typing import Any

from app.acp.core.models import Message, MessagePart
from app.acp.core.types import ContentEncoding


class MessageEncoder:
    """
    Encoder for ACP messages.

    Handles:
    - JSON serialization
    - Base64 encoding for binary content
    - Multipart message construction
    """

    @staticmethod
    def encode_message(message: Message) -> dict[str, Any]:
        """
        Encode a message to a JSON-serializable dict.

        Args:
            message: Message to encode

        Returns:
            JSON-serializable dictionary
        """
        return message.model_dump(mode="json", exclude_none=True)

    @staticmethod
    def encode_messages(messages: list[Message]) -> list[dict[str, Any]]:
        """
        Encode multiple messages.

        Args:
            messages: Messages to encode

        Returns:
            List of JSON-serializable dictionaries
        """
        return [MessageEncoder.encode_message(m) for m in messages]

    @staticmethod
    def encode_binary_content(data: bytes, content_type: str = "application/octet-stream") -> MessagePart:
        """
        Encode binary data as a base64-encoded message part.

        Args:
            data: Binary data to encode
            content_type: MIME type of the data

        Returns:
            MessagePart with base64-encoded content
        """
        encoded = base64.b64encode(data).decode("utf-8")
        return MessagePart(
            content=encoded,
            content_type=content_type,
            content_encoding=ContentEncoding.BASE64,
        )

    @staticmethod
    def encode_json_content(data: Any) -> MessagePart:
        """
        Encode JSON data as a message part.

        Args:
            data: JSON-serializable data

        Returns:
            MessagePart with JSON content
        """
        return MessagePart(
            content=json.dumps(data),
            content_type="application/json",
            content_encoding=ContentEncoding.PLAIN,
        )

    @staticmethod
    def create_text_message(role: str, text: str) -> Message:
        """
        Create a simple text message.

        Args:
            role: Message role
            text: Text content

        Returns:
            Message with text/plain part
        """
        return Message(
            role=role,
            parts=[
                MessagePart(
                    content=text,
                    content_type="text/plain",
                )
            ],
        )

    @staticmethod
    def create_multipart_message(role: str, parts: list[tuple[str, str, str | None]]) -> Message:
        """
        Create a multipart message.

        Args:
            role: Message role
            parts: List of (content, content_type, name) tuples

        Returns:
            Message with multiple parts
        """
        message_parts = []
        for content, content_type, name in parts:
            message_parts.append(
                MessagePart(
                    content=content,
                    content_type=content_type,
                    name=name,
                )
            )
        return Message(role=role, parts=message_parts)


class MessageDecoder:
    """
    Decoder for ACP messages.

    Handles:
    - JSON deserialization
    - Base64 decoding
    - Content extraction
    """

    @staticmethod
    def decode_message(data: dict[str, Any]) -> Message:
        """
        Decode a message from a dictionary.

        Args:
            data: Dictionary representation of a message

        Returns:
            Message object
        """
        return Message.model_validate(data)

    @staticmethod
    def decode_messages(data: list[dict[str, Any]]) -> list[Message]:
        """
        Decode multiple messages.

        Args:
            data: List of message dictionaries

        Returns:
            List of Message objects
        """
        return [MessageDecoder.decode_message(d) for d in data]

    @staticmethod
    def decode_binary_content(part: MessagePart) -> bytes:
        """
        Decode binary content from a message part.

        Args:
            part: Message part with base64 content

        Returns:
            Decoded binary data

        Raises:
            ValueError: If content is not base64 encoded
        """
        if part.content_encoding != ContentEncoding.BASE64:
            raise ValueError("Part is not base64 encoded")

        if not part.content:
            return b""

        return base64.b64decode(part.content)

    @staticmethod
    def decode_json_content(part: MessagePart) -> Any:
        """
        Decode JSON content from a message part.

        Args:
            part: Message part with JSON content

        Returns:
            Parsed JSON data

        Raises:
            ValueError: If content is not JSON
        """
        if part.content_type != "application/json":
            raise ValueError("Part is not JSON content")

        if not part.content:
            return None

        return json.loads(part.content)

    @staticmethod
    def extract_text(message: Message) -> str:
        """
        Extract all text content from a message.

        Args:
            message: Message to extract from

        Returns:
            Combined text content
        """
        texts = []
        for part in message.parts:
            if part.content_type == "text/plain" and part.content:
                texts.append(part.content)
        return "\n".join(texts)

    @staticmethod
    def extract_text_from_messages(messages: list[Message]) -> str:
        """
        Extract text from multiple messages.

        Args:
            messages: Messages to extract from

        Returns:
            Combined text content
        """
        texts = []
        for message in messages:
            text = MessageDecoder.extract_text(message)
            if text:
                texts.append(f"[{message.role}]: {text}")
        return "\n".join(texts)

    @staticmethod
    def get_part_by_name(message: Message, name: str) -> MessagePart | None:
        """
        Get a specific part by name.

        Args:
            message: Message to search
            name: Part name

        Returns:
            MessagePart or None
        """
        for part in message.parts:
            if part.name == name:
                return part
        return None

    @staticmethod
    def get_parts_by_type(message: Message, content_type: str) -> list[MessagePart]:
        """
        Get all parts of a specific content type.

        Args:
            message: Message to search
            content_type: MIME type to filter by

        Returns:
            List of matching parts
        """
        return [p for p in message.parts if p.content_type == content_type]
