"""
Unit tests for ACP MessageEncoder and MessageDecoder.

Tests cover:
- MessageEncoder: JSON serialization, base64 encoding, message creation
- MessageDecoder: JSON deserialization, base64 decoding, content extraction
- Round-trip encoding/decoding
- Edge cases and error handling
"""

from __future__ import annotations

import base64
import json
from typing import Any

import pytest


# =============================================================================
# Helper Functions for Lazy Imports
# =============================================================================

def _get_types():
    """Lazy import of ACP types module."""
    from app.acp.core.types import ContentEncoding, MessageRole
    return {
        "ContentEncoding": ContentEncoding,
        "MessageRole": MessageRole,
    }


def _get_models():
    """Lazy import of ACP models module."""
    from app.acp.core.models import Message, MessagePart
    return {
        "Message": Message,
        "MessagePart": MessagePart,
    }


def _get_encoder_decoder():
    """Lazy import of MessageEncoder and MessageDecoder."""
    from app.acp.protocol.message import MessageEncoder, MessageDecoder
    return {
        "MessageEncoder": MessageEncoder,
        "MessageDecoder": MessageDecoder,
    }


# =============================================================================
# MessageEncoder Tests
# =============================================================================

class TestMessageEncoder:
    """Tests for MessageEncoder class - message encoding utilities."""

    # -------------------------------------------------------------------------
    # encode_message Tests
    # -------------------------------------------------------------------------

    def test_encode_message_simple_text(self):
        """Verify encode_message converts a simple text message to dict."""
        models = _get_models()
        encoder = _get_encoder_decoder()["MessageEncoder"]

        message = models["Message"].user_text("Hello, World!")
        result = encoder.encode_message(message)

        assert isinstance(result, dict)
        assert result["role"] == "user"
        assert len(result["parts"]) == 1
        assert result["parts"][0]["content"] == "Hello, World!"
        assert result["parts"][0]["content_type"] == "text/plain"

    def test_encode_message_with_agent_role(self):
        """Verify encode_message handles agent role correctly."""
        models = _get_models()
        encoder = _get_encoder_decoder()["MessageEncoder"]

        message = models["Message"].agent_text("Response from agent")
        result = encoder.encode_message(message)

        assert result["role"] == "agent"
        assert result["parts"][0]["content"] == "Response from agent"

    def test_encode_message_with_named_agent(self):
        """Verify encode_message handles named agent role correctly."""
        models = _get_models()
        encoder = _get_encoder_decoder()["MessageEncoder"]

        message = models["Message"].agent_text("Response", agent_name="assistant")
        result = encoder.encode_message(message)

        assert result["role"] == "agent/assistant"

    def test_encode_message_with_multiple_parts(self):
        """Verify encode_message handles multiple parts correctly."""
        models = _get_models()
        types = _get_types()
        encoder = _get_encoder_decoder()["MessageEncoder"]

        message = models["Message"](
            role=types["MessageRole"].USER,
            parts=[
                models["MessagePart"](content="Text content", content_type="text/plain"),
                models["MessagePart"](
                    content='{"key": "value"}',
                    content_type="application/json",
                ),
            ],
        )
        result = encoder.encode_message(message)

        assert len(result["parts"]) == 2
        assert result["parts"][0]["content"] == "Text content"
        assert result["parts"][1]["content_type"] == "application/json"

    def test_encode_message_excludes_none_values(self):
        """Verify encode_message excludes None values from output."""
        models = _get_models()
        encoder = _get_encoder_decoder()["MessageEncoder"]

        message = models["Message"].user_text("Test")
        result = encoder.encode_message(message)

        # content_url is None and should be excluded
        assert "content_url" not in result["parts"][0] or result["parts"][0].get("content_url") is None

    def test_encode_message_preserves_metadata(self):
        """Verify encode_message preserves part metadata."""
        models = _get_models()
        types = _get_types()
        encoder = _get_encoder_decoder()["MessageEncoder"]

        metadata = {"source": "https://example.com", "title": "Test Source"}
        message = models["Message"](
            role=types["MessageRole"].AGENT,
            parts=[
                models["MessagePart"](
                    content="Citation content",
                    content_type="text/plain",
                    metadata=metadata,
                ),
            ],
        )
        result = encoder.encode_message(message)

        assert result["parts"][0]["metadata"] == metadata

    # -------------------------------------------------------------------------
    # encode_messages Tests
    # -------------------------------------------------------------------------

    def test_encode_messages_empty_list(self):
        """Verify encode_messages handles empty list."""
        encoder = _get_encoder_decoder()["MessageEncoder"]

        result = encoder.encode_messages([])

        assert result == []

    def test_encode_messages_single_message(self):
        """Verify encode_messages handles single message."""
        models = _get_models()
        encoder = _get_encoder_decoder()["MessageEncoder"]

        messages = [models["Message"].user_text("Hello")]
        result = encoder.encode_messages(messages)

        assert len(result) == 1
        assert result[0]["parts"][0]["content"] == "Hello"

    def test_encode_messages_multiple_messages(self):
        """Verify encode_messages handles multiple messages."""
        models = _get_models()
        encoder = _get_encoder_decoder()["MessageEncoder"]

        messages = [
            models["Message"].user_text("Question"),
            models["Message"].agent_text("Answer"),
            models["Message"].user_text("Follow-up"),
        ]
        result = encoder.encode_messages(messages)

        assert len(result) == 3
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "agent"
        assert result[2]["role"] == "user"

    def test_encode_messages_preserves_order(self):
        """Verify encode_messages preserves message order."""
        models = _get_models()
        encoder = _get_encoder_decoder()["MessageEncoder"]

        messages = [models["Message"].user_text(f"Message {i}") for i in range(5)]
        result = encoder.encode_messages(messages)

        for i, msg in enumerate(result):
            assert msg["parts"][0]["content"] == f"Message {i}"

    # -------------------------------------------------------------------------
    # encode_binary_content Tests
    # -------------------------------------------------------------------------

    def test_encode_binary_content_simple(self):
        """Verify encode_binary_content creates base64-encoded part."""
        encoder = _get_encoder_decoder()["MessageEncoder"]
        types = _get_types()

        data = b"Hello, binary world!"
        result = encoder.encode_binary_content(data)

        assert result.content_encoding == types["ContentEncoding"].BASE64
        assert result.content == base64.b64encode(data).decode("utf-8")
        assert result.content_type == "application/octet-stream"

    def test_encode_binary_content_with_custom_type(self):
        """Verify encode_binary_content accepts custom content type."""
        encoder = _get_encoder_decoder()["MessageEncoder"]

        data = b"\x89PNG\r\n\x1a\n"  # PNG header
        result = encoder.encode_binary_content(data, content_type="image/png")

        assert result.content_type == "image/png"

    def test_encode_binary_content_empty_data(self):
        """Verify encode_binary_content handles empty data."""
        encoder = _get_encoder_decoder()["MessageEncoder"]

        data = b""
        result = encoder.encode_binary_content(data)

        assert result.content == ""

    def test_encode_binary_content_large_data(self):
        """Verify encode_binary_content handles large data."""
        encoder = _get_encoder_decoder()["MessageEncoder"]

        data = b"x" * 100000  # 100KB of data
        result = encoder.encode_binary_content(data)

        assert len(result.content) > 100000  # base64 increases size

    # -------------------------------------------------------------------------
    # encode_json_content Tests
    # -------------------------------------------------------------------------

    def test_encode_json_content_dict(self):
        """Verify encode_json_content handles dict."""
        encoder = _get_encoder_decoder()["MessageEncoder"]
        types = _get_types()

        data = {"key": "value", "number": 42}
        result = encoder.encode_json_content(data)

        assert result.content_type == "application/json"
        assert result.content_encoding == types["ContentEncoding"].PLAIN
        assert json.loads(result.content) == data

    def test_encode_json_content_list(self):
        """Verify encode_json_content handles list."""
        encoder = _get_encoder_decoder()["MessageEncoder"]

        data = [1, 2, 3, "four", {"five": 5}]
        result = encoder.encode_json_content(data)

        assert json.loads(result.content) == data

    def test_encode_json_content_nested(self):
        """Verify encode_json_content handles nested structures."""
        encoder = _get_encoder_decoder()["MessageEncoder"]

        data = {
            "level1": {
                "level2": {
                    "level3": [1, 2, 3],
                },
            },
        }
        result = encoder.encode_json_content(data)

        assert json.loads(result.content) == data

    def test_encode_json_content_primitives(self):
        """Verify encode_json_content handles primitive types."""
        encoder = _get_encoder_decoder()["MessageEncoder"]

        # String
        result = encoder.encode_json_content("hello")
        assert json.loads(result.content) == "hello"

        # Number
        result = encoder.encode_json_content(42)
        assert json.loads(result.content) == 42

        # Boolean
        result = encoder.encode_json_content(True)
        assert json.loads(result.content) is True

        # Null
        result = encoder.encode_json_content(None)
        assert json.loads(result.content) is None

    # -------------------------------------------------------------------------
    # create_text_message Tests
    # -------------------------------------------------------------------------

    def test_create_text_message_user(self):
        """Verify create_text_message creates user message."""
        encoder = _get_encoder_decoder()["MessageEncoder"]

        result = encoder.create_text_message("user", "Hello!")

        assert result.role == "user"
        assert len(result.parts) == 1
        assert result.parts[0].content == "Hello!"
        assert result.parts[0].content_type == "text/plain"

    def test_create_text_message_agent(self):
        """Verify create_text_message creates agent message."""
        encoder = _get_encoder_decoder()["MessageEncoder"]

        result = encoder.create_text_message("agent", "Response")

        assert result.role == "agent"
        assert result.parts[0].content == "Response"

    def test_create_text_message_system(self):
        """Verify create_text_message creates system message."""
        encoder = _get_encoder_decoder()["MessageEncoder"]

        result = encoder.create_text_message("system", "You are helpful.")

        assert result.role == "system"
        assert result.parts[0].content == "You are helpful."

    def test_create_text_message_empty_content(self):
        """Verify create_text_message handles empty content."""
        encoder = _get_encoder_decoder()["MessageEncoder"]

        result = encoder.create_text_message("user", "")

        assert result.parts[0].content == ""

    # -------------------------------------------------------------------------
    # create_multipart_message Tests
    # -------------------------------------------------------------------------

    def test_create_multipart_message_basic(self):
        """Verify create_multipart_message creates message with multiple parts."""
        encoder = _get_encoder_decoder()["MessageEncoder"]

        parts = [
            ("Text content", "text/plain", None),
            ('{"data": 1}', "application/json", "data.json"),
        ]
        result = encoder.create_multipart_message("user", parts)

        assert result.role == "user"
        assert len(result.parts) == 2
        assert result.parts[0].content == "Text content"
        assert result.parts[0].content_type == "text/plain"
        assert result.parts[0].name is None
        assert result.parts[1].content == '{"data": 1}'
        assert result.parts[1].content_type == "application/json"
        assert result.parts[1].name == "data.json"

    def test_create_multipart_message_single_part(self):
        """Verify create_multipart_message handles single part."""
        encoder = _get_encoder_decoder()["MessageEncoder"]

        parts = [("Content", "text/plain", "file.txt")]
        result = encoder.create_multipart_message("agent", parts)

        assert len(result.parts) == 1
        assert result.parts[0].name == "file.txt"

    def test_create_multipart_message_empty_parts(self):
        """Verify create_multipart_message handles empty parts list."""
        encoder = _get_encoder_decoder()["MessageEncoder"]

        result = encoder.create_multipart_message("user", [])

        assert result.role == "user"
        assert len(result.parts) == 0

    def test_create_multipart_message_with_various_content_types(self):
        """Verify create_multipart_message handles various content types."""
        encoder = _get_encoder_decoder()["MessageEncoder"]

        parts = [
            ("Plain text", "text/plain", None),
            ("# Markdown", "text/markdown", None),
            ("<html></html>", "text/html", None),
            ('{"json": true}', "application/json", None),
        ]
        result = encoder.create_multipart_message("agent", parts)

        assert len(result.parts) == 4
        assert result.parts[0].content_type == "text/plain"
        assert result.parts[1].content_type == "text/markdown"
        assert result.parts[2].content_type == "text/html"
        assert result.parts[3].content_type == "application/json"


# =============================================================================
# MessageDecoder Tests
# =============================================================================

class TestMessageDecoder:
    """Tests for MessageDecoder class - message decoding utilities."""

    # -------------------------------------------------------------------------
    # decode_message Tests
    # -------------------------------------------------------------------------

    def test_decode_message_simple(self):
        """Verify decode_message converts dict to Message."""
        decoder = _get_encoder_decoder()["MessageDecoder"]

        data = {
            "role": "user",
            "parts": [{"content": "Hello!", "content_type": "text/plain"}],
        }
        result = decoder.decode_message(data)

        assert result.role == "user"
        assert len(result.parts) == 1
        assert result.parts[0].content == "Hello!"

    def test_decode_message_with_all_fields(self):
        """Verify decode_message handles all fields."""
        decoder = _get_encoder_decoder()["MessageDecoder"]

        data = {
            "role": "agent",
            "parts": [
                {
                    "content": "Response",
                    "content_type": "text/plain",
                    "content_encoding": "plain",
                    "name": "response.txt",
                    "metadata": {"key": "value"},
                }
            ],
            "created_at": "2024-01-15T12:00:00",
            "completed_at": "2024-01-15T12:00:01",
        }
        result = decoder.decode_message(data)

        assert result.role == "agent"
        assert result.parts[0].name == "response.txt"
        assert result.parts[0].metadata == {"key": "value"}
        assert result.created_at is not None
        assert result.completed_at is not None

    def test_decode_message_with_content_url(self):
        """Verify decode_message handles content_url."""
        decoder = _get_encoder_decoder()["MessageDecoder"]

        data = {
            "role": "user",
            "parts": [
                {
                    "content_url": "https://example.com/file.pdf",
                    "content_type": "application/pdf",
                }
            ],
        }
        result = decoder.decode_message(data)

        assert result.parts[0].content_url == "https://example.com/file.pdf"
        assert result.parts[0].content is None

    def test_decode_message_empty_parts(self):
        """Verify decode_message handles empty parts list."""
        decoder = _get_encoder_decoder()["MessageDecoder"]

        data = {"role": "user", "parts": []}
        result = decoder.decode_message(data)

        assert len(result.parts) == 0

    # -------------------------------------------------------------------------
    # decode_messages Tests
    # -------------------------------------------------------------------------

    def test_decode_messages_empty_list(self):
        """Verify decode_messages handles empty list."""
        decoder = _get_encoder_decoder()["MessageDecoder"]

        result = decoder.decode_messages([])

        assert result == []

    def test_decode_messages_single_message(self):
        """Verify decode_messages handles single message."""
        decoder = _get_encoder_decoder()["MessageDecoder"]

        data = [
            {"role": "user", "parts": [{"content": "Test"}]},
        ]
        result = decoder.decode_messages(data)

        assert len(result) == 1
        assert result[0].parts[0].content == "Test"

    def test_decode_messages_multiple_messages(self):
        """Verify decode_messages handles multiple messages."""
        decoder = _get_encoder_decoder()["MessageDecoder"]

        data = [
            {"role": "user", "parts": [{"content": "Question"}]},
            {"role": "agent", "parts": [{"content": "Answer"}]},
        ]
        result = decoder.decode_messages(data)

        assert len(result) == 2
        assert result[0].role == "user"
        assert result[1].role == "agent"

    def test_decode_messages_preserves_order(self):
        """Verify decode_messages preserves message order."""
        decoder = _get_encoder_decoder()["MessageDecoder"]

        data = [
            {"role": "user", "parts": [{"content": f"Message {i}"}]}
            for i in range(5)
        ]
        result = decoder.decode_messages(data)

        for i, msg in enumerate(result):
            assert msg.parts[0].content == f"Message {i}"

    # -------------------------------------------------------------------------
    # decode_binary_content Tests
    # -------------------------------------------------------------------------

    def test_decode_binary_content_simple(self):
        """Verify decode_binary_content decodes base64 content."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        original_data = b"Hello, binary world!"
        encoded = base64.b64encode(original_data).decode("utf-8")

        part = models["MessagePart"](
            content=encoded,
            content_type="application/octet-stream",
            content_encoding=types["ContentEncoding"].BASE64,
        )
        result = decoder.decode_binary_content(part)

        assert result == original_data

    def test_decode_binary_content_empty(self):
        """Verify decode_binary_content handles empty content."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        part = models["MessagePart"](
            content="",
            content_encoding=types["ContentEncoding"].BASE64,
        )
        result = decoder.decode_binary_content(part)

        assert result == b""

    def test_decode_binary_content_none(self):
        """Verify decode_binary_content handles None content."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        part = models["MessagePart"](
            content=None,
            content_encoding=types["ContentEncoding"].BASE64,
        )
        result = decoder.decode_binary_content(part)

        assert result == b""

    def test_decode_binary_content_not_base64_raises(self):
        """Verify decode_binary_content raises for non-base64 encoding."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        part = models["MessagePart"](
            content="Plain text content",
            content_encoding=types["ContentEncoding"].PLAIN,
        )

        with pytest.raises(ValueError, match="not base64 encoded"):
            decoder.decode_binary_content(part)

    def test_decode_binary_content_large_data(self):
        """Verify decode_binary_content handles large data."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        original_data = b"x" * 100000
        encoded = base64.b64encode(original_data).decode("utf-8")

        part = models["MessagePart"](
            content=encoded,
            content_encoding=types["ContentEncoding"].BASE64,
        )
        result = decoder.decode_binary_content(part)

        assert result == original_data

    # -------------------------------------------------------------------------
    # decode_json_content Tests
    # -------------------------------------------------------------------------

    def test_decode_json_content_dict(self):
        """Verify decode_json_content decodes JSON dict."""
        models = _get_models()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        data = {"key": "value", "number": 42}
        part = models["MessagePart"](
            content=json.dumps(data),
            content_type="application/json",
        )
        result = decoder.decode_json_content(part)

        assert result == data

    def test_decode_json_content_list(self):
        """Verify decode_json_content decodes JSON list."""
        models = _get_models()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        data = [1, 2, 3, "four"]
        part = models["MessagePart"](
            content=json.dumps(data),
            content_type="application/json",
        )
        result = decoder.decode_json_content(part)

        assert result == data

    def test_decode_json_content_primitives(self):
        """Verify decode_json_content decodes primitive types."""
        models = _get_models()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        # String
        part = models["MessagePart"](content='"hello"', content_type="application/json")
        assert decoder.decode_json_content(part) == "hello"

        # Number
        part = models["MessagePart"](content="42", content_type="application/json")
        assert decoder.decode_json_content(part) == 42

        # Boolean
        part = models["MessagePart"](content="true", content_type="application/json")
        assert decoder.decode_json_content(part) is True

        # Null
        part = models["MessagePart"](content="null", content_type="application/json")
        assert decoder.decode_json_content(part) is None

    def test_decode_json_content_empty_returns_none(self):
        """Verify decode_json_content returns None for empty content."""
        models = _get_models()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        part = models["MessagePart"](
            content="",
            content_type="application/json",
        )
        result = decoder.decode_json_content(part)

        assert result is None

    def test_decode_json_content_none_returns_none(self):
        """Verify decode_json_content returns None for None content."""
        models = _get_models()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        part = models["MessagePart"](
            content=None,
            content_type="application/json",
        )
        result = decoder.decode_json_content(part)

        assert result is None

    def test_decode_json_content_not_json_raises(self):
        """Verify decode_json_content raises for non-JSON content type."""
        models = _get_models()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        part = models["MessagePart"](
            content='{"key": "value"}',
            content_type="text/plain",
        )

        with pytest.raises(ValueError, match="not JSON content"):
            decoder.decode_json_content(part)

    # -------------------------------------------------------------------------
    # extract_text Tests
    # -------------------------------------------------------------------------

    def test_extract_text_single_part(self):
        """Verify extract_text extracts text from single part."""
        models = _get_models()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        message = models["Message"].user_text("Hello, World!")
        result = decoder.extract_text(message)

        assert result == "Hello, World!"

    def test_extract_text_multiple_parts(self):
        """Verify extract_text combines multiple text parts."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        message = models["Message"](
            role=types["MessageRole"].USER,
            parts=[
                models["MessagePart"](content="First line", content_type="text/plain"),
                models["MessagePart"](content="Second line", content_type="text/plain"),
            ],
        )
        result = decoder.extract_text(message)

        assert result == "First line\nSecond line"

    def test_extract_text_ignores_non_text_parts(self):
        """Verify extract_text ignores non-text/plain parts."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        message = models["Message"](
            role=types["MessageRole"].USER,
            parts=[
                models["MessagePart"](content="Text content", content_type="text/plain"),
                models["MessagePart"](content='{"json": true}', content_type="application/json"),
                models["MessagePart"](content="More text", content_type="text/plain"),
            ],
        )
        result = decoder.extract_text(message)

        assert result == "Text content\nMore text"
        assert "json" not in result

    def test_extract_text_empty_parts(self):
        """Verify extract_text handles empty parts list."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        message = models["Message"](role=types["MessageRole"].USER, parts=[])
        result = decoder.extract_text(message)

        assert result == ""

    def test_extract_text_none_content(self):
        """Verify extract_text skips parts with None content."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        message = models["Message"](
            role=types["MessageRole"].USER,
            parts=[
                models["MessagePart"](content=None, content_type="text/plain"),
                models["MessagePart"](content="Valid content", content_type="text/plain"),
            ],
        )
        result = decoder.extract_text(message)

        assert result == "Valid content"

    # -------------------------------------------------------------------------
    # extract_text_from_messages Tests
    # -------------------------------------------------------------------------

    def test_extract_text_from_messages_single(self):
        """Verify extract_text_from_messages handles single message."""
        models = _get_models()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        messages = [models["Message"].user_text("Hello")]
        result = decoder.extract_text_from_messages(messages)

        assert result == "[user]: Hello"

    def test_extract_text_from_messages_multiple(self):
        """Verify extract_text_from_messages combines multiple messages."""
        models = _get_models()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        messages = [
            models["Message"].user_text("Question?"),
            models["Message"].agent_text("Answer."),
        ]
        result = decoder.extract_text_from_messages(messages)

        assert "[user]: Question?" in result
        assert "[agent]: Answer." in result
        assert result == "[user]: Question?\n[agent]: Answer."

    def test_extract_text_from_messages_empty_list(self):
        """Verify extract_text_from_messages handles empty list."""
        decoder = _get_encoder_decoder()["MessageDecoder"]

        result = decoder.extract_text_from_messages([])

        assert result == ""

    def test_extract_text_from_messages_skips_empty(self):
        """Verify extract_text_from_messages skips messages with no text."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        messages = [
            models["Message"].user_text("Valid"),
            models["Message"](
                role=types["MessageRole"].USER,
                parts=[models["MessagePart"](content='{"json": true}', content_type="application/json")],
            ),
        ]
        result = decoder.extract_text_from_messages(messages)

        assert result == "[user]: Valid"

    def test_extract_text_from_messages_named_agent(self):
        """Verify extract_text_from_messages handles named agent roles."""
        models = _get_models()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        messages = [
            models["Message"].agent_text("Response", agent_name="assistant"),
        ]
        result = decoder.extract_text_from_messages(messages)

        assert result == "[agent/assistant]: Response"

    # -------------------------------------------------------------------------
    # get_part_by_name Tests
    # -------------------------------------------------------------------------

    def test_get_part_by_name_found(self):
        """Verify get_part_by_name returns matching part."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        message = models["Message"](
            role=types["MessageRole"].AGENT,
            parts=[
                models["MessagePart"](content="Part 1", name="first"),
                models["MessagePart"](content="Part 2", name="second"),
            ],
        )
        result = decoder.get_part_by_name(message, "second")

        assert result is not None
        assert result.content == "Part 2"

    def test_get_part_by_name_not_found(self):
        """Verify get_part_by_name returns None when not found."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        message = models["Message"](
            role=types["MessageRole"].AGENT,
            parts=[models["MessagePart"](content="Part 1", name="first")],
        )
        result = decoder.get_part_by_name(message, "nonexistent")

        assert result is None

    def test_get_part_by_name_no_named_parts(self):
        """Verify get_part_by_name returns None when no parts have names."""
        models = _get_models()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        message = models["Message"].user_text("No named parts")
        result = decoder.get_part_by_name(message, "any_name")

        assert result is None

    def test_get_part_by_name_first_match(self):
        """Verify get_part_by_name returns first matching part."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        message = models["Message"](
            role=types["MessageRole"].AGENT,
            parts=[
                models["MessagePart"](content="First", name="duplicate"),
                models["MessagePart"](content="Second", name="duplicate"),
            ],
        )
        result = decoder.get_part_by_name(message, "duplicate")

        assert result is not None
        assert result.content == "First"

    # -------------------------------------------------------------------------
    # get_parts_by_type Tests
    # -------------------------------------------------------------------------

    def test_get_parts_by_type_single_match(self):
        """Verify get_parts_by_type returns matching parts."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        message = models["Message"](
            role=types["MessageRole"].AGENT,
            parts=[
                models["MessagePart"](content="Text", content_type="text/plain"),
                models["MessagePart"](content='{"json": true}', content_type="application/json"),
            ],
        )
        result = decoder.get_parts_by_type(message, "application/json")

        assert len(result) == 1
        assert result[0].content == '{"json": true}'

    def test_get_parts_by_type_multiple_matches(self):
        """Verify get_parts_by_type returns all matching parts."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        message = models["Message"](
            role=types["MessageRole"].AGENT,
            parts=[
                models["MessagePart"](content="First", content_type="text/plain"),
                models["MessagePart"](content='{"a": 1}', content_type="application/json"),
                models["MessagePart"](content="Second", content_type="text/plain"),
            ],
        )
        result = decoder.get_parts_by_type(message, "text/plain")

        assert len(result) == 2
        assert result[0].content == "First"
        assert result[1].content == "Second"

    def test_get_parts_by_type_no_matches(self):
        """Verify get_parts_by_type returns empty list when no matches."""
        models = _get_models()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        message = models["Message"].user_text("Plain text only")
        result = decoder.get_parts_by_type(message, "application/json")

        assert result == []

    def test_get_parts_by_type_empty_message(self):
        """Verify get_parts_by_type handles empty parts list."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        message = models["Message"](role=types["MessageRole"].USER, parts=[])
        result = decoder.get_parts_by_type(message, "text/plain")

        assert result == []


# =============================================================================
# Round-trip Tests
# =============================================================================

class TestEncoderDecoderRoundTrip:
    """Tests for round-trip encoding and decoding."""

    def test_roundtrip_simple_message(self):
        """Verify simple message survives encode/decode round-trip."""
        models = _get_models()
        encoder = _get_encoder_decoder()["MessageEncoder"]
        decoder = _get_encoder_decoder()["MessageDecoder"]

        original = models["Message"].user_text("Hello, World!")
        encoded = encoder.encode_message(original)
        decoded = decoder.decode_message(encoded)

        assert decoded.role == original.role
        assert decoded.parts[0].content == original.parts[0].content
        assert decoded.parts[0].content_type == original.parts[0].content_type

    def test_roundtrip_multipart_message(self):
        """Verify multipart message survives encode/decode round-trip."""
        models = _get_models()
        types = _get_types()
        encoder = _get_encoder_decoder()["MessageEncoder"]
        decoder = _get_encoder_decoder()["MessageDecoder"]

        original = models["Message"](
            role=types["MessageRole"].AGENT,
            parts=[
                models["MessagePart"](content="Text part", content_type="text/plain"),
                models["MessagePart"](
                    content='{"key": "value"}',
                    content_type="application/json",
                    name="data.json",
                ),
            ],
        )
        encoded = encoder.encode_message(original)
        decoded = decoder.decode_message(encoded)

        assert len(decoded.parts) == 2
        assert decoded.parts[0].content == "Text part"
        assert decoded.parts[1].name == "data.json"

    def test_roundtrip_multiple_messages(self):
        """Verify multiple messages survive encode/decode round-trip."""
        models = _get_models()
        encoder = _get_encoder_decoder()["MessageEncoder"]
        decoder = _get_encoder_decoder()["MessageDecoder"]

        originals = [
            models["Message"].user_text("Question 1"),
            models["Message"].agent_text("Answer 1"),
            models["Message"].user_text("Question 2"),
            models["Message"].agent_text("Answer 2"),
        ]
        encoded = encoder.encode_messages(originals)
        decoded = decoder.decode_messages(encoded)

        assert len(decoded) == 4
        for orig, dec in zip(originals, decoded):
            assert orig.role == dec.role
            assert orig.parts[0].content == dec.parts[0].content

    def test_roundtrip_binary_content(self):
        """Verify binary content survives encode/decode round-trip."""
        models = _get_models()
        types = _get_types()
        encoder = _get_encoder_decoder()["MessageEncoder"]
        decoder = _get_encoder_decoder()["MessageDecoder"]

        original_data = b"\x00\x01\x02\x03\xff\xfe\xfd"
        encoded_part = encoder.encode_binary_content(original_data, "application/octet-stream")

        # Create message with the encoded part
        message = models["Message"](
            role=types["MessageRole"].USER,
            parts=[encoded_part],
        )

        # Encode and decode the message
        encoded_msg = encoder.encode_message(message)
        decoded_msg = decoder.decode_message(encoded_msg)

        # Decode the binary content
        decoded_data = decoder.decode_binary_content(decoded_msg.parts[0])

        assert decoded_data == original_data

    def test_roundtrip_json_content(self):
        """Verify JSON content survives encode/decode round-trip."""
        models = _get_models()
        types = _get_types()
        encoder = _get_encoder_decoder()["MessageEncoder"]
        decoder = _get_encoder_decoder()["MessageDecoder"]

        original_json = {"nested": {"data": [1, 2, 3]}, "flag": True}
        encoded_part = encoder.encode_json_content(original_json)

        # Create message with the encoded part
        message = models["Message"](
            role=types["MessageRole"].AGENT,
            parts=[encoded_part],
        )

        # Encode and decode the message
        encoded_msg = encoder.encode_message(message)
        decoded_msg = decoder.decode_message(encoded_msg)

        # Decode the JSON content
        decoded_json = decoder.decode_json_content(decoded_msg.parts[0])

        assert decoded_json == original_json

    def test_roundtrip_preserves_metadata(self):
        """Verify metadata survives encode/decode round-trip."""
        models = _get_models()
        types = _get_types()
        encoder = _get_encoder_decoder()["MessageEncoder"]
        decoder = _get_encoder_decoder()["MessageDecoder"]

        metadata = {
            "source": "https://example.com",
            "title": "Test Document",
            "custom_field": {"nested": "value"},
        }
        original = models["Message"](
            role=types["MessageRole"].AGENT,
            parts=[
                models["MessagePart"](
                    content="Content with metadata",
                    content_type="text/plain",
                    metadata=metadata,
                ),
            ],
        )

        encoded = encoder.encode_message(original)
        decoded = decoder.decode_message(encoded)

        assert decoded.parts[0].metadata == metadata


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_encode_message_with_unicode(self):
        """Verify encoding handles Unicode characters."""
        models = _get_models()
        encoder = _get_encoder_decoder()["MessageEncoder"]

        message = models["Message"].user_text("Hello! \u4e2d\u6587 \U0001f600 \u0420\u0443\u0441\u0441\u043a\u0438\u0439")
        result = encoder.encode_message(message)

        assert result["parts"][0]["content"] == "Hello! \u4e2d\u6587 \U0001f600 \u0420\u0443\u0441\u0441\u043a\u0438\u0439"

    def test_decode_message_with_unicode(self):
        """Verify decoding handles Unicode characters."""
        decoder = _get_encoder_decoder()["MessageDecoder"]

        data = {
            "role": "user",
            "parts": [{"content": "Hello! \u4e2d\u6587 \U0001f600"}],
        }
        result = decoder.decode_message(data)

        assert result.parts[0].content == "Hello! \u4e2d\u6587 \U0001f600"

    def test_encode_binary_with_special_bytes(self):
        """Verify encoding handles special byte values."""
        encoder = _get_encoder_decoder()["MessageEncoder"]
        decoder = _get_encoder_decoder()["MessageDecoder"]

        # All possible byte values
        data = bytes(range(256))
        encoded = encoder.encode_binary_content(data)
        decoded = decoder.decode_binary_content(encoded)

        assert decoded == data

    def test_create_text_message_with_newlines(self):
        """Verify create_text_message handles newlines correctly."""
        encoder = _get_encoder_decoder()["MessageEncoder"]

        text = "Line 1\nLine 2\nLine 3"
        result = encoder.create_text_message("user", text)

        assert result.parts[0].content == text
        assert "\n" in result.parts[0].content

    def test_extract_text_with_empty_string_content(self):
        """Verify extract_text handles empty string content."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        message = models["Message"](
            role=types["MessageRole"].USER,
            parts=[
                models["MessagePart"](content="", content_type="text/plain"),
                models["MessagePart"](content="Valid", content_type="text/plain"),
            ],
        )
        result = decoder.extract_text(message)

        # Empty string is falsy, so it should be skipped
        assert result == "Valid"

    def test_json_encode_decode_special_values(self):
        """Verify JSON encoding handles special float values."""
        encoder = _get_encoder_decoder()["MessageEncoder"]
        decoder = _get_encoder_decoder()["MessageDecoder"]

        # Note: JSON doesn't support Infinity/NaN, so we test valid special values
        data = {"zero": 0, "negative_zero": -0.0, "large": 1e308}
        part = encoder.encode_json_content(data)
        decoded = decoder.decode_json_content(part)

        assert decoded["zero"] == 0
        assert decoded["large"] == 1e308

    def test_message_with_very_long_content(self):
        """Verify handling of very long content."""
        models = _get_models()
        encoder = _get_encoder_decoder()["MessageEncoder"]
        decoder = _get_encoder_decoder()["MessageDecoder"]

        long_content = "x" * 1000000  # 1MB of content
        message = models["Message"].user_text(long_content)

        encoded = encoder.encode_message(message)
        decoded = decoder.decode_message(encoded)

        assert len(decoded.parts[0].content) == 1000000

    def test_get_parts_by_type_case_sensitive(self):
        """Verify get_parts_by_type is case-sensitive."""
        models = _get_models()
        types = _get_types()
        decoder = _get_encoder_decoder()["MessageDecoder"]

        message = models["Message"](
            role=types["MessageRole"].AGENT,
            parts=[
                models["MessagePart"](content="Test", content_type="text/plain"),
            ],
        )

        # Exact match should work
        result = decoder.get_parts_by_type(message, "text/plain")
        assert len(result) == 1

        # Different case should not match
        result = decoder.get_parts_by_type(message, "TEXT/PLAIN")
        assert len(result) == 0

    def test_decode_message_missing_optional_fields(self):
        """Verify decoding handles missing optional fields gracefully."""
        decoder = _get_encoder_decoder()["MessageDecoder"]

        # Minimal valid message
        data = {"role": "user"}
        result = decoder.decode_message(data)

        assert result.role == "user"
        assert result.parts == []
        assert result.created_at is None
        assert result.completed_at is None
