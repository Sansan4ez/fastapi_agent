"""
Unit tests to verify Telegram fixtures work correctly.

These tests ensure all fixtures are loadable and produce valid mock objects.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime


# Register the Telegram fixtures plugin
pytest_plugins = ["tests.fixtures.telegram_fixtures"]


class TestUserFixtures:
    """Test Telegram User fixtures."""

    def test_mock_telegram_user(self, mock_telegram_user):
        """Verify mock_telegram_user fixture."""
        assert isinstance(mock_telegram_user, MagicMock)
        assert mock_telegram_user.id == 123456789
        assert mock_telegram_user.is_bot is False
        assert mock_telegram_user.first_name == "Test"
        assert mock_telegram_user.last_name == "User"
        assert mock_telegram_user.username == "test_user"
        assert mock_telegram_user.full_name == "Test User"

    def test_mock_telegram_user_no_username(self, mock_telegram_user_no_username):
        """Verify mock_telegram_user_no_username fixture."""
        assert isinstance(mock_telegram_user_no_username, MagicMock)
        assert mock_telegram_user_no_username.username is None
        assert mock_telegram_user_no_username.first_name == "NoUsername"

    def test_mock_telegram_user_premium(self, mock_telegram_user_premium):
        """Verify mock_telegram_user_premium fixture."""
        assert isinstance(mock_telegram_user_premium, MagicMock)
        assert mock_telegram_user_premium.is_premium is True

    def test_mock_telegram_bot_user(self, mock_telegram_bot_user):
        """Verify mock_telegram_bot_user fixture."""
        assert isinstance(mock_telegram_bot_user, MagicMock)
        assert mock_telegram_bot_user.is_bot is True
        assert mock_telegram_bot_user.can_join_groups is True


class TestChatFixtures:
    """Test Telegram Chat fixtures."""

    def test_mock_telegram_chat(self, mock_telegram_chat):
        """Verify mock_telegram_chat fixture."""
        assert isinstance(mock_telegram_chat, MagicMock)
        assert mock_telegram_chat.id == 123456789
        assert mock_telegram_chat.type == "private"
        assert mock_telegram_chat.first_name == "Test"

    def test_mock_telegram_group_chat(self, mock_telegram_group_chat):
        """Verify mock_telegram_group_chat fixture."""
        assert isinstance(mock_telegram_group_chat, MagicMock)
        assert mock_telegram_group_chat.type == "supergroup"
        assert mock_telegram_group_chat.title == "Test Group"
        assert mock_telegram_group_chat.id < 0  # Group IDs are negative

    def test_mock_telegram_channel(self, mock_telegram_channel):
        """Verify mock_telegram_channel fixture."""
        assert isinstance(mock_telegram_channel, MagicMock)
        assert mock_telegram_channel.type == "channel"
        assert mock_telegram_channel.title == "Test Channel"

    def test_mock_telegram_forum_chat(self, mock_telegram_forum_chat):
        """Verify mock_telegram_forum_chat fixture."""
        assert isinstance(mock_telegram_forum_chat, MagicMock)
        assert mock_telegram_forum_chat.is_forum is True


class TestMessageFixtures:
    """Test Telegram Message fixtures."""

    def test_mock_telegram_message(self, mock_telegram_message):
        """Verify mock_telegram_message fixture."""
        assert isinstance(mock_telegram_message, MagicMock)
        assert mock_telegram_message.message_id == 1001
        assert mock_telegram_message.text == "Hello, this is a test message"
        assert mock_telegram_message.chat is not None
        assert mock_telegram_message.from_user is not None

    def test_mock_telegram_message_has_async_methods(self, mock_telegram_message):
        """Verify mock_telegram_message has async methods."""
        assert isinstance(mock_telegram_message.answer, AsyncMock)
        assert isinstance(mock_telegram_message.reply, AsyncMock)
        assert isinstance(mock_telegram_message.edit_text, AsyncMock)
        assert isinstance(mock_telegram_message.delete, AsyncMock)

    def test_mock_telegram_message_with_photo(self, mock_telegram_message_with_photo):
        """Verify mock_telegram_message_with_photo fixture."""
        assert isinstance(mock_telegram_message_with_photo, MagicMock)
        assert mock_telegram_message_with_photo.text is None
        assert mock_telegram_message_with_photo.photo is not None
        assert len(mock_telegram_message_with_photo.photo) > 0
        assert mock_telegram_message_with_photo.caption == "Photo caption"

    def test_mock_telegram_message_with_document(self, mock_telegram_message_with_document):
        """Verify mock_telegram_message_with_document fixture."""
        assert isinstance(mock_telegram_message_with_document, MagicMock)
        assert mock_telegram_message_with_document.text is None
        assert mock_telegram_message_with_document.document is not None
        assert mock_telegram_message_with_document.document.file_name == "document.pdf"
        assert mock_telegram_message_with_document.document.mime_type == "application/pdf"

    def test_mock_telegram_command_start(self, mock_telegram_command_start):
        """Verify mock_telegram_command_start fixture."""
        assert isinstance(mock_telegram_command_start, MagicMock)
        assert mock_telegram_command_start.text == "/start"
        assert mock_telegram_command_start.entities is not None
        assert len(mock_telegram_command_start.entities) > 0
        assert mock_telegram_command_start.entities[0].type == "bot_command"

    def test_mock_telegram_command_help(self, mock_telegram_command_help):
        """Verify mock_telegram_command_help fixture."""
        assert isinstance(mock_telegram_command_help, MagicMock)
        assert mock_telegram_command_help.text == "/help"

    def test_mock_telegram_reply_message(self, mock_telegram_reply_message):
        """Verify mock_telegram_reply_message fixture."""
        assert isinstance(mock_telegram_reply_message, MagicMock)
        assert mock_telegram_reply_message.reply_to_message is not None
        assert mock_telegram_reply_message.reply_to_message.text == "Original message"

    def test_mock_telegram_forwarded_message(self, mock_telegram_forwarded_message):
        """Verify mock_telegram_forwarded_message fixture."""
        assert isinstance(mock_telegram_forwarded_message, MagicMock)
        assert mock_telegram_forwarded_message.forward_from is not None
        assert mock_telegram_forwarded_message.forward_date is not None


class TestCallbackQueryFixtures:
    """Test Telegram CallbackQuery fixtures."""

    def test_mock_telegram_callback_query(self, mock_telegram_callback_query):
        """Verify mock_telegram_callback_query fixture."""
        assert isinstance(mock_telegram_callback_query, MagicMock)
        assert mock_telegram_callback_query.id == "callback_query_12345"
        assert mock_telegram_callback_query.data == "callback_data"
        assert mock_telegram_callback_query.from_user is not None
        assert mock_telegram_callback_query.message is not None

    def test_mock_telegram_callback_query_has_async_methods(self, mock_telegram_callback_query):
        """Verify mock_telegram_callback_query has async methods."""
        assert isinstance(mock_telegram_callback_query.answer, AsyncMock)

    def test_mock_telegram_callback_query_agent_select(self, mock_telegram_callback_query_agent_select):
        """Verify mock_telegram_callback_query_agent_select fixture."""
        assert isinstance(mock_telegram_callback_query_agent_select, MagicMock)
        assert mock_telegram_callback_query_agent_select.data == "agent_select:test-assistant"

    def test_mock_telegram_inline_callback_query(self, mock_telegram_inline_callback_query):
        """Verify mock_telegram_inline_callback_query fixture."""
        assert isinstance(mock_telegram_inline_callback_query, MagicMock)
        assert mock_telegram_inline_callback_query.message is None
        assert mock_telegram_inline_callback_query.inline_message_id is not None


class TestUpdateFixtures:
    """Test Telegram Update fixtures."""

    def test_mock_telegram_update(self, mock_telegram_update):
        """Verify mock_telegram_update fixture."""
        assert isinstance(mock_telegram_update, MagicMock)
        assert mock_telegram_update.update_id == 100001
        assert mock_telegram_update.message is not None
        assert mock_telegram_update.message.text == "Hello, this is a test message"

    def test_mock_telegram_update_callback(self, mock_telegram_update_callback):
        """Verify mock_telegram_update_callback fixture."""
        assert isinstance(mock_telegram_update_callback, MagicMock)
        assert mock_telegram_update_callback.callback_query is not None
        assert mock_telegram_update_callback.message is None

    def test_mock_telegram_update_command_start(self, mock_telegram_update_command_start):
        """Verify mock_telegram_update_command_start fixture."""
        assert isinstance(mock_telegram_update_command_start, MagicMock)
        assert mock_telegram_update_command_start.message is not None
        assert mock_telegram_update_command_start.message.text == "/start"

    def test_mock_telegram_update_command_help(self, mock_telegram_update_command_help):
        """Verify mock_telegram_update_command_help fixture."""
        assert isinstance(mock_telegram_update_command_help, MagicMock)
        assert mock_telegram_update_command_help.message.text == "/help"

    def test_mock_telegram_update_edited_message(self, mock_telegram_update_edited_message):
        """Verify mock_telegram_update_edited_message fixture."""
        assert isinstance(mock_telegram_update_edited_message, MagicMock)
        assert mock_telegram_update_edited_message.edited_message is not None
        assert mock_telegram_update_edited_message.message is None
        assert mock_telegram_update_edited_message.edited_message.edit_date is not None


class TestBotFixtures:
    """Test Telegram Bot fixtures."""

    def test_mock_telegram_bot(self, mock_telegram_bot):
        """Verify mock_telegram_bot fixture."""
        assert isinstance(mock_telegram_bot, MagicMock)
        assert mock_telegram_bot.id == 1234567890
        assert mock_telegram_bot.username == "test_bot"
        assert mock_telegram_bot.first_name == "TestBot"

    def test_mock_telegram_bot_has_async_methods(self, mock_telegram_bot):
        """Verify mock_telegram_bot has async methods."""
        assert isinstance(mock_telegram_bot.send_message, AsyncMock)
        assert isinstance(mock_telegram_bot.send_photo, AsyncMock)
        assert isinstance(mock_telegram_bot.send_document, AsyncMock)
        assert isinstance(mock_telegram_bot.edit_message_text, AsyncMock)
        assert isinstance(mock_telegram_bot.delete_message, AsyncMock)
        assert isinstance(mock_telegram_bot.answer_callback_query, AsyncMock)
        assert isinstance(mock_telegram_bot.get_me, AsyncMock)


class TestInlineQueryFixtures:
    """Test Telegram InlineQuery fixtures."""

    def test_mock_telegram_inline_query(self, mock_telegram_inline_query):
        """Verify mock_telegram_inline_query fixture."""
        assert isinstance(mock_telegram_inline_query, MagicMock)
        assert mock_telegram_inline_query.id == "inline_query_12345"
        assert mock_telegram_inline_query.query == "search query"
        assert mock_telegram_inline_query.from_user is not None
        assert isinstance(mock_telegram_inline_query.answer, AsyncMock)


class TestCompositeScenarios:
    """Test composite scenario fixtures."""

    def test_telegram_conversation_scenario(self, telegram_conversation_scenario):
        """Verify telegram_conversation_scenario fixture."""
        assert isinstance(telegram_conversation_scenario, dict)
        assert "user" in telegram_conversation_scenario
        assert "chat" in telegram_conversation_scenario
        assert "bot" in telegram_conversation_scenario
        assert "messages" in telegram_conversation_scenario
        assert len(telegram_conversation_scenario["messages"]) >= 3
        assert telegram_conversation_scenario["user_id"] == 123456789

    def test_telegram_callback_scenario(self, telegram_callback_scenario):
        """Verify telegram_callback_scenario fixture."""
        assert isinstance(telegram_callback_scenario, dict)
        assert "callback_query" in telegram_callback_scenario
        assert "update" in telegram_callback_scenario
        assert "original_message" in telegram_callback_scenario
        assert telegram_callback_scenario["callback_data"] == "agent_select:assistant"

    def test_telegram_group_scenario(self, telegram_group_scenario):
        """Verify telegram_group_scenario fixture."""
        assert isinstance(telegram_group_scenario, dict)
        assert "chat" in telegram_group_scenario
        assert telegram_group_scenario["chat"].type == "supergroup"
        assert len(telegram_group_scenario["messages"]) >= 2


class TestFactoryFunctions:
    """Test factory functions."""

    def test_create_telegram_user(self):
        """Test create_telegram_user factory function."""
        from tests.fixtures.telegram_fixtures import create_telegram_user

        user = create_telegram_user(
            id=999,
            first_name="Custom",
            username="custom_user",
        )
        assert isinstance(user, MagicMock)
        assert user.id == 999
        assert user.first_name == "Custom"
        assert user.username == "custom_user"

    def test_create_telegram_chat(self):
        """Test create_telegram_chat factory function."""
        from tests.fixtures.telegram_fixtures import create_telegram_chat

        chat = create_telegram_chat(
            id=888,
            type="group",
            title="Custom Group",
        )
        assert isinstance(chat, MagicMock)
        assert chat.id == 888
        assert chat.type == "group"
        assert chat.title == "Custom Group"

    def test_create_telegram_message(self):
        """Test create_telegram_message factory function."""
        from tests.fixtures.telegram_fixtures import create_telegram_message

        message = create_telegram_message(
            message_id=2000,
            text="Custom message text",
        )
        assert isinstance(message, MagicMock)
        assert message.message_id == 2000
        assert message.text == "Custom message text"
        assert isinstance(message.answer, AsyncMock)

    def test_create_telegram_message_with_photo(self):
        """Test create_telegram_message_with_photo factory function."""
        from tests.fixtures.telegram_fixtures import create_telegram_message_with_photo

        message = create_telegram_message_with_photo(
            caption="Custom photo caption",
            file_id="custom_file_id",
        )
        assert isinstance(message, MagicMock)
        assert message.caption == "Custom photo caption"
        assert message.photo[0].file_id == "custom_file_id"

    def test_create_telegram_message_with_document(self):
        """Test create_telegram_message_with_document factory function."""
        from tests.fixtures.telegram_fixtures import create_telegram_message_with_document

        message = create_telegram_message_with_document(
            file_name="test.txt",
            mime_type="text/plain",
        )
        assert isinstance(message, MagicMock)
        assert message.document.file_name == "test.txt"
        assert message.document.mime_type == "text/plain"

    def test_create_telegram_command_message(self):
        """Test create_telegram_command_message factory function."""
        from tests.fixtures.telegram_fixtures import create_telegram_command_message

        message = create_telegram_command_message(
            command="/custom",
            args="arg1 arg2",
        )
        assert isinstance(message, MagicMock)
        assert message.text == "/custom arg1 arg2"
        assert message.get_command() == "/custom"
        assert message.get_args() == "arg1 arg2"

    def test_create_telegram_callback_query(self):
        """Test create_telegram_callback_query factory function."""
        from tests.fixtures.telegram_fixtures import create_telegram_callback_query

        callback = create_telegram_callback_query(
            id="custom_callback_id",
            data="custom_data",
        )
        assert isinstance(callback, MagicMock)
        assert callback.id == "custom_callback_id"
        assert callback.data == "custom_data"

    def test_create_telegram_update(self):
        """Test create_telegram_update factory function."""
        from tests.fixtures.telegram_fixtures import (
            create_telegram_update,
            create_telegram_message,
        )

        message = create_telegram_message(text="Update test")
        update = create_telegram_update(
            update_id=200001,
            message=message,
        )
        assert isinstance(update, MagicMock)
        assert update.update_id == 200001
        assert update.message.text == "Update test"

    def test_create_message_update(self):
        """Test create_message_update factory function."""
        from tests.fixtures.telegram_fixtures import create_message_update

        update = create_message_update(
            update_id=300001,
            text="Direct update creation",
        )
        assert isinstance(update, MagicMock)
        assert update.update_id == 300001
        assert update.message.text == "Direct update creation"

    def test_create_callback_update(self):
        """Test create_callback_update factory function."""
        from tests.fixtures.telegram_fixtures import create_callback_update

        update = create_callback_update(
            update_id=400001,
            callback_data="test_callback",
        )
        assert isinstance(update, MagicMock)
        assert update.update_id == 400001
        assert update.callback_query.data == "test_callback"

    def test_create_command_update(self):
        """Test create_command_update factory function."""
        from tests.fixtures.telegram_fixtures import create_command_update

        update = create_command_update(
            update_id=500001,
            command="/test",
            args="arg1",
        )
        assert isinstance(update, MagicMock)
        assert update.update_id == 500001
        assert update.message.text == "/test arg1"

    def test_create_telegram_bot(self):
        """Test create_telegram_bot factory function."""
        from tests.fixtures.telegram_fixtures import create_telegram_bot

        bot = create_telegram_bot(
            id=9999,
            username="custom_bot",
            first_name="CustomBot",
        )
        assert isinstance(bot, MagicMock)
        assert bot.id == 9999
        assert bot.username == "custom_bot"
        assert isinstance(bot.send_message, AsyncMock)

    def test_create_telegram_inline_query(self):
        """Test create_telegram_inline_query factory function."""
        from tests.fixtures.telegram_fixtures import create_telegram_inline_query

        query = create_telegram_inline_query(
            id="custom_query_id",
            query="custom search",
        )
        assert isinstance(query, MagicMock)
        assert query.id == "custom_query_id"
        assert query.query == "custom search"

    def test_create_message_entity(self):
        """Test create_message_entity factory function."""
        from tests.fixtures.telegram_fixtures import create_message_entity

        entity = create_message_entity(
            type="text_link",
            offset=0,
            length=10,
            url="https://example.com",
        )
        assert isinstance(entity, MagicMock)
        assert entity.type == "text_link"
        assert entity.url == "https://example.com"

    def test_create_group_chat(self):
        """Test create_group_chat factory function."""
        from tests.fixtures.telegram_fixtures import create_group_chat

        chat = create_group_chat(
            title="My Group",
            is_forum=True,
        )
        assert isinstance(chat, MagicMock)
        assert chat.type == "supergroup"
        assert chat.title == "My Group"
        assert chat.is_forum is True

    def test_create_channel_chat(self):
        """Test create_channel_chat factory function."""
        from tests.fixtures.telegram_fixtures import create_channel_chat

        chat = create_channel_chat(
            title="My Channel",
            username="my_channel",
        )
        assert isinstance(chat, MagicMock)
        assert chat.type == "channel"
        assert chat.title == "My Channel"
        assert chat.username == "my_channel"


class TestParametrizedFixtures:
    """Test parametrized fixtures."""

    def test_any_chat_type(self, any_chat_type):
        """Verify any_chat_type parametrized fixture."""
        assert any_chat_type in ["private", "group", "supergroup", "channel"]

    def test_any_entity_type(self, any_entity_type):
        """Verify any_entity_type parametrized fixture."""
        expected_types = [
            "mention", "hashtag", "cashtag", "bot_command", "url",
            "email", "phone_number", "bold", "italic", "underline",
            "strikethrough", "spoiler", "code", "pre", "text_link",
            "text_mention", "custom_emoji",
        ]
        assert any_entity_type in expected_types


class TestAsyncMethodsWork:
    """Test that async methods can be awaited properly."""

    @pytest.mark.asyncio
    async def test_message_answer_can_be_awaited(self, mock_telegram_message):
        """Verify message.answer() can be awaited."""
        result = await mock_telegram_message.answer("Response")
        assert result is not None

    @pytest.mark.asyncio
    async def test_message_reply_can_be_awaited(self, mock_telegram_message):
        """Verify message.reply() can be awaited."""
        result = await mock_telegram_message.reply("Reply")
        assert result is not None

    @pytest.mark.asyncio
    async def test_callback_answer_can_be_awaited(self, mock_telegram_callback_query):
        """Verify callback.answer() can be awaited."""
        result = await mock_telegram_callback_query.answer()
        assert result is True

    @pytest.mark.asyncio
    async def test_bot_send_message_can_be_awaited(self, mock_telegram_bot):
        """Verify bot.send_message() can be awaited."""
        result = await mock_telegram_bot.send_message(
            chat_id=123,
            text="Test",
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_bot_get_me_can_be_awaited(self, mock_telegram_bot):
        """Verify bot.get_me() can be awaited."""
        result = await mock_telegram_bot.get_me()
        assert result is not None
        assert result.is_bot is True
