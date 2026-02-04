"""
Telegram Mock Factories and Fixtures

Provides comprehensive fixtures and factory functions for creating mock Telegram
messages, updates, users, chats, and callback queries for testing the ACP-Telegram
integration.

Usage:
    Import fixtures in your test file or conftest.py:

        from tests.fixtures.telegram_fixtures import (
            mock_telegram_user,
            mock_telegram_chat,
            mock_telegram_message,
            mock_telegram_update,
            ...
        )

    Or import factory functions directly:

        from tests.fixtures.telegram_fixtures import (
            create_telegram_user,
            create_telegram_message,
            create_telegram_update,
            ...
        )
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, AsyncMock, PropertyMock

import pytest


# =============================================================================
# Fixed IDs for deterministic testing
# =============================================================================

FIXTURE_USER_ID = 123456789
FIXTURE_CHAT_ID = 123456789
FIXTURE_MESSAGE_ID = 1001
FIXTURE_CALLBACK_QUERY_ID = "callback_query_12345"
FIXTURE_BOT_ID = 1234567890
FIXTURE_INLINE_MESSAGE_ID = "inline_message_12345"

FIXTURE_TIMESTAMP = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
FIXTURE_TIMESTAMP_LATER = datetime(2024, 1, 15, 12, 5, 0, tzinfo=timezone.utc)


# =============================================================================
# User Factory and Fixtures
# =============================================================================

def create_telegram_user(
    id: int = FIXTURE_USER_ID,
    is_bot: bool = False,
    first_name: str = "Test",
    last_name: str | None = "User",
    username: str | None = "test_user",
    language_code: str | None = "en",
    is_premium: bool | None = None,
    added_to_attachment_menu: bool | None = None,
    can_join_groups: bool | None = None,
    can_read_all_group_messages: bool | None = None,
    supports_inline_queries: bool | None = None,
) -> MagicMock:
    """
    Factory function to create a mock Telegram User.

    Args:
        id: Unique identifier for the user
        is_bot: True if this user is a bot
        first_name: User's first name
        last_name: User's last name (optional)
        username: User's username (optional)
        language_code: IETF language tag (optional)
        is_premium: True if user is a Telegram Premium subscriber
        added_to_attachment_menu: True if bot is added to attachment menu
        can_join_groups: True if bot can be invited to groups
        can_read_all_group_messages: True if privacy mode is disabled for bot
        supports_inline_queries: True if bot supports inline queries

    Returns:
        MagicMock representing a Telegram User
    """
    user = MagicMock()
    user.id = id
    user.is_bot = is_bot
    user.first_name = first_name
    user.last_name = last_name
    user.username = username
    user.language_code = language_code
    user.is_premium = is_premium
    user.added_to_attachment_menu = added_to_attachment_menu
    user.can_join_groups = can_join_groups
    user.can_read_all_group_messages = can_read_all_group_messages
    user.supports_inline_queries = supports_inline_queries

    # Computed property
    user.full_name = f"{first_name} {last_name}".strip() if last_name else first_name

    return user


def create_bot_user(
    id: int = FIXTURE_BOT_ID,
    first_name: str = "TestBot",
    username: str = "test_bot",
    can_join_groups: bool = True,
    can_read_all_group_messages: bool = False,
    supports_inline_queries: bool = True,
) -> MagicMock:
    """
    Factory function to create a mock Telegram Bot User.

    Args:
        id: Unique identifier for the bot
        first_name: Bot's name
        username: Bot's username
        can_join_groups: True if bot can be invited to groups
        can_read_all_group_messages: True if privacy mode is disabled
        supports_inline_queries: True if bot supports inline queries

    Returns:
        MagicMock representing a Telegram Bot User
    """
    return create_telegram_user(
        id=id,
        is_bot=True,
        first_name=first_name,
        last_name=None,
        username=username,
        can_join_groups=can_join_groups,
        can_read_all_group_messages=can_read_all_group_messages,
        supports_inline_queries=supports_inline_queries,
    )


@pytest.fixture
def mock_telegram_user() -> MagicMock:
    """Create a standard mock Telegram user."""
    return create_telegram_user()


@pytest.fixture
def mock_telegram_user_no_username() -> MagicMock:
    """Create a mock Telegram user without a username."""
    return create_telegram_user(
        username=None,
        first_name="NoUsername",
        last_name="User",
    )


@pytest.fixture
def mock_telegram_user_premium() -> MagicMock:
    """Create a mock Telegram Premium user."""
    return create_telegram_user(
        first_name="Premium",
        last_name="User",
        username="premium_user",
        is_premium=True,
    )


@pytest.fixture
def mock_telegram_bot_user() -> MagicMock:
    """Create a mock Telegram bot user."""
    return create_bot_user()


# =============================================================================
# Chat Factory and Fixtures
# =============================================================================

def create_telegram_chat(
    id: int = FIXTURE_CHAT_ID,
    type: str = "private",
    title: str | None = None,
    username: str | None = None,
    first_name: str | None = "Test",
    last_name: str | None = "User",
    is_forum: bool | None = None,
    description: str | None = None,
    invite_link: str | None = None,
    pinned_message: MagicMock | None = None,
    slow_mode_delay: int | None = None,
    has_protected_content: bool | None = None,
) -> MagicMock:
    """
    Factory function to create a mock Telegram Chat.

    Args:
        id: Unique identifier for the chat
        type: Type of chat ("private", "group", "supergroup", "channel")
        title: Title for groups, supergroups, and channels
        username: Chat username if available
        first_name: First name of the other party in private chat
        last_name: Last name of the other party in private chat
        is_forum: True if the supergroup is a forum
        description: Description for groups, supergroups, and channels
        invite_link: Primary invite link
        pinned_message: Pinned message in the chat
        slow_mode_delay: Slow mode delay in seconds
        has_protected_content: True if messages can't be forwarded

    Returns:
        MagicMock representing a Telegram Chat
    """
    chat = MagicMock()
    chat.id = id
    chat.type = type
    chat.title = title
    chat.username = username
    chat.first_name = first_name
    chat.last_name = last_name
    chat.is_forum = is_forum
    chat.description = description
    chat.invite_link = invite_link
    chat.pinned_message = pinned_message
    chat.slow_mode_delay = slow_mode_delay
    chat.has_protected_content = has_protected_content

    # Computed property for full name
    if type == "private":
        chat.full_name = f"{first_name} {last_name}".strip() if last_name else first_name
    else:
        chat.full_name = title

    return chat


def create_group_chat(
    id: int = -1001234567890,
    title: str = "Test Group",
    type: str = "supergroup",
    username: str | None = None,
    is_forum: bool = False,
    description: str | None = None,
) -> MagicMock:
    """
    Factory function to create a mock Telegram group/supergroup chat.

    Args:
        id: Unique identifier for the group (negative for groups)
        title: Group title
        type: Type of chat ("group" or "supergroup")
        username: Public username if available
        is_forum: True if the supergroup is a forum
        description: Group description

    Returns:
        MagicMock representing a Telegram group chat
    """
    return create_telegram_chat(
        id=id,
        type=type,
        title=title,
        username=username,
        first_name=None,
        last_name=None,
        is_forum=is_forum,
        description=description,
    )


def create_channel_chat(
    id: int = -1009876543210,
    title: str = "Test Channel",
    username: str | None = "test_channel",
    description: str | None = "A test channel",
) -> MagicMock:
    """
    Factory function to create a mock Telegram channel chat.

    Args:
        id: Unique identifier for the channel (negative)
        title: Channel title
        username: Public username if available
        description: Channel description

    Returns:
        MagicMock representing a Telegram channel
    """
    return create_telegram_chat(
        id=id,
        type="channel",
        title=title,
        username=username,
        first_name=None,
        last_name=None,
        description=description,
    )


@pytest.fixture
def mock_telegram_chat() -> MagicMock:
    """Create a standard mock private Telegram chat."""
    return create_telegram_chat()


@pytest.fixture
def mock_telegram_group_chat() -> MagicMock:
    """Create a mock Telegram group chat."""
    return create_group_chat()


@pytest.fixture
def mock_telegram_channel() -> MagicMock:
    """Create a mock Telegram channel."""
    return create_channel_chat()


@pytest.fixture
def mock_telegram_forum_chat() -> MagicMock:
    """Create a mock Telegram forum supergroup."""
    return create_group_chat(
        title="Test Forum",
        is_forum=True,
    )


# =============================================================================
# Message Factory and Fixtures
# =============================================================================

def create_telegram_message(
    message_id: int = FIXTURE_MESSAGE_ID,
    date: datetime = FIXTURE_TIMESTAMP,
    chat: MagicMock | None = None,
    from_user: MagicMock | None = None,
    text: str | None = "Hello, this is a test message",
    entities: list[MagicMock] | None = None,
    reply_to_message: MagicMock | None = None,
    forward_from: MagicMock | None = None,
    forward_from_chat: MagicMock | None = None,
    forward_date: datetime | None = None,
    edit_date: datetime | None = None,
    photo: list[MagicMock] | None = None,
    document: MagicMock | None = None,
    audio: MagicMock | None = None,
    video: MagicMock | None = None,
    voice: MagicMock | None = None,
    video_note: MagicMock | None = None,
    sticker: MagicMock | None = None,
    caption: str | None = None,
    caption_entities: list[MagicMock] | None = None,
    contact: MagicMock | None = None,
    location: MagicMock | None = None,
    venue: MagicMock | None = None,
    poll: MagicMock | None = None,
    reply_markup: MagicMock | None = None,
    via_bot: MagicMock | None = None,
    media_group_id: str | None = None,
) -> MagicMock:
    """
    Factory function to create a mock Telegram Message.

    Args:
        message_id: Unique message identifier within the chat
        date: Date the message was sent
        chat: Chat the message belongs to
        from_user: Sender of the message
        text: Text content of the message
        entities: List of message entities (bold, links, etc.)
        reply_to_message: Message being replied to
        forward_from: Original sender for forwarded messages
        forward_from_chat: Original chat for forwarded messages
        forward_date: Date of the original message for forwards
        edit_date: Date of last edit
        photo: List of photo sizes if message contains photo
        document: Document attached to message
        audio: Audio file attached to message
        video: Video attached to message
        voice: Voice message
        video_note: Video note (round video)
        sticker: Sticker
        caption: Caption for media messages
        caption_entities: Entities in the caption
        contact: Shared contact
        location: Shared location
        venue: Shared venue
        poll: Poll in the message
        reply_markup: Inline keyboard markup
        via_bot: Bot that sent the message via inline mode
        media_group_id: Media group ID for album messages

    Returns:
        MagicMock representing a Telegram Message
    """
    message = MagicMock()
    message.message_id = message_id
    message.date = date
    message.chat = chat or create_telegram_chat()
    message.from_user = from_user or create_telegram_user()
    message.text = text
    message.entities = entities
    message.reply_to_message = reply_to_message
    message.forward_from = forward_from
    message.forward_from_chat = forward_from_chat
    message.forward_date = forward_date
    message.edit_date = edit_date
    message.photo = photo
    message.document = document
    message.audio = audio
    message.video = video
    message.voice = voice
    message.video_note = video_note
    message.sticker = sticker
    message.caption = caption
    message.caption_entities = caption_entities
    message.contact = contact
    message.location = location
    message.venue = venue
    message.poll = poll
    message.reply_markup = reply_markup
    message.via_bot = via_bot
    message.media_group_id = media_group_id

    # Add async methods commonly used
    message.answer = AsyncMock(return_value=MagicMock())
    message.reply = AsyncMock(return_value=MagicMock())
    message.edit_text = AsyncMock(return_value=MagicMock())
    message.delete = AsyncMock(return_value=True)
    message.forward = AsyncMock(return_value=MagicMock())
    message.copy_to = AsyncMock(return_value=MagicMock())

    # Helper method to get content type
    def _get_content_type():
        if text:
            return "text"
        if photo:
            return "photo"
        if document:
            return "document"
        if audio:
            return "audio"
        if video:
            return "video"
        if voice:
            return "voice"
        if video_note:
            return "video_note"
        if sticker:
            return "sticker"
        if contact:
            return "contact"
        if location:
            return "location"
        if venue:
            return "venue"
        if poll:
            return "poll"
        return "unknown"

    type(message).content_type = PropertyMock(return_value=_get_content_type())

    return message


def create_telegram_message_with_photo(
    message_id: int = FIXTURE_MESSAGE_ID,
    caption: str | None = "Photo caption",
    file_id: str = "photo_file_id_12345",
    file_unique_id: str = "photo_unique_id_12345",
    width: int = 1920,
    height: int = 1080,
    file_size: int = 150000,
    **kwargs,
) -> MagicMock:
    """
    Factory function to create a mock Telegram Message with a photo.

    Args:
        message_id: Unique message identifier
        caption: Photo caption
        file_id: File identifier for the photo
        file_unique_id: Unique file identifier
        width: Photo width
        height: Photo height
        file_size: File size in bytes
        **kwargs: Additional message parameters

    Returns:
        MagicMock representing a Telegram Message with photo
    """
    photo_size = MagicMock()
    photo_size.file_id = file_id
    photo_size.file_unique_id = file_unique_id
    photo_size.width = width
    photo_size.height = height
    photo_size.file_size = file_size

    return create_telegram_message(
        message_id=message_id,
        text=None,
        photo=[photo_size],
        caption=caption,
        **kwargs,
    )


def create_telegram_message_with_document(
    message_id: int = FIXTURE_MESSAGE_ID,
    caption: str | None = None,
    file_id: str = "doc_file_id_12345",
    file_unique_id: str = "doc_unique_id_12345",
    file_name: str = "document.pdf",
    mime_type: str = "application/pdf",
    file_size: int = 250000,
    **kwargs,
) -> MagicMock:
    """
    Factory function to create a mock Telegram Message with a document.

    Args:
        message_id: Unique message identifier
        caption: Document caption
        file_id: File identifier
        file_unique_id: Unique file identifier
        file_name: Original filename
        mime_type: MIME type of the file
        file_size: File size in bytes
        **kwargs: Additional message parameters

    Returns:
        MagicMock representing a Telegram Message with document
    """
    document = MagicMock()
    document.file_id = file_id
    document.file_unique_id = file_unique_id
    document.file_name = file_name
    document.mime_type = mime_type
    document.file_size = file_size
    document.thumb = None

    return create_telegram_message(
        message_id=message_id,
        text=None,
        document=document,
        caption=caption,
        **kwargs,
    )


def create_telegram_command_message(
    command: str = "/start",
    args: str | None = None,
    message_id: int = FIXTURE_MESSAGE_ID,
    **kwargs,
) -> MagicMock:
    """
    Factory function to create a mock Telegram Message with a command.

    Args:
        command: The command (e.g., "/start", "/help")
        args: Arguments after the command
        message_id: Unique message identifier
        **kwargs: Additional message parameters

    Returns:
        MagicMock representing a Telegram Message with a command
    """
    text = f"{command} {args}".strip() if args else command

    # Create bot command entity
    entity = MagicMock()
    entity.type = "bot_command"
    entity.offset = 0
    entity.length = len(command)

    message = create_telegram_message(
        message_id=message_id,
        text=text,
        entities=[entity],
        **kwargs,
    )

    # Helper to extract command
    message.get_command = MagicMock(return_value=command)
    message.get_args = MagicMock(return_value=args)

    return message


@pytest.fixture
def mock_telegram_message() -> MagicMock:
    """Create a standard mock Telegram text message."""
    return create_telegram_message()


@pytest.fixture
def mock_telegram_message_with_photo() -> MagicMock:
    """Create a mock Telegram message with a photo."""
    return create_telegram_message_with_photo()


@pytest.fixture
def mock_telegram_message_with_document() -> MagicMock:
    """Create a mock Telegram message with a document."""
    return create_telegram_message_with_document()


@pytest.fixture
def mock_telegram_command_start() -> MagicMock:
    """Create a mock /start command message."""
    return create_telegram_command_message(command="/start")


@pytest.fixture
def mock_telegram_command_help() -> MagicMock:
    """Create a mock /help command message."""
    return create_telegram_command_message(command="/help")


@pytest.fixture
def mock_telegram_reply_message() -> MagicMock:
    """Create a mock Telegram message that is a reply to another message."""
    original_message = create_telegram_message(
        message_id=FIXTURE_MESSAGE_ID - 1,
        text="Original message",
    )
    return create_telegram_message(
        message_id=FIXTURE_MESSAGE_ID,
        text="Reply to original message",
        reply_to_message=original_message,
    )


@pytest.fixture
def mock_telegram_forwarded_message() -> MagicMock:
    """Create a mock forwarded Telegram message."""
    forward_from = create_telegram_user(
        id=987654321,
        first_name="Forward",
        last_name="Source",
        username="forward_source",
    )
    return create_telegram_message(
        message_id=FIXTURE_MESSAGE_ID,
        text="This is a forwarded message",
        forward_from=forward_from,
        forward_date=FIXTURE_TIMESTAMP,
    )


# =============================================================================
# Callback Query Factory and Fixtures
# =============================================================================

# Sentinel value for "not provided" (different from None)
_NOT_PROVIDED = object()


def create_telegram_callback_query(
    id: str = FIXTURE_CALLBACK_QUERY_ID,
    from_user: MagicMock | None = None,
    chat_instance: str = "chat_instance_12345",
    message: MagicMock | None = _NOT_PROVIDED,
    inline_message_id: str | None = None,
    data: str | None = "callback_data",
    game_short_name: str | None = None,
) -> MagicMock:
    """
    Factory function to create a mock Telegram CallbackQuery.

    Args:
        id: Unique identifier for this query
        from_user: Sender of the callback
        chat_instance: Global identifier for the chat
        message: Message with the callback button (use None for inline callbacks)
        inline_message_id: Identifier of inline message
        data: Data associated with the callback button
        game_short_name: Short name of the game

    Returns:
        MagicMock representing a Telegram CallbackQuery
    """
    callback = MagicMock()
    callback.id = id
    callback.from_user = from_user or create_telegram_user()
    callback.chat_instance = chat_instance
    # Use sentinel to distinguish between "not provided" and "explicitly None"
    callback.message = create_telegram_message() if message is _NOT_PROVIDED else message
    callback.inline_message_id = inline_message_id
    callback.data = data
    callback.game_short_name = game_short_name

    # Add async methods
    callback.answer = AsyncMock(return_value=True)

    return callback


def create_inline_callback_query(
    id: str = FIXTURE_CALLBACK_QUERY_ID,
    inline_message_id: str = FIXTURE_INLINE_MESSAGE_ID,
    data: str = "inline_callback_data",
    **kwargs,
) -> MagicMock:
    """
    Factory function to create a mock inline CallbackQuery (no message).

    Args:
        id: Unique identifier for this query
        inline_message_id: Identifier of the inline message
        data: Data associated with the callback button
        **kwargs: Additional callback query parameters

    Returns:
        MagicMock representing an inline CallbackQuery
    """
    return create_telegram_callback_query(
        id=id,
        message=None,
        inline_message_id=inline_message_id,
        data=data,
        **kwargs,
    )


@pytest.fixture
def mock_telegram_callback_query() -> MagicMock:
    """Create a standard mock Telegram callback query."""
    return create_telegram_callback_query()


@pytest.fixture
def mock_telegram_callback_query_agent_select() -> MagicMock:
    """Create a mock callback query for agent selection."""
    return create_telegram_callback_query(
        data="agent_select:test-assistant",
    )


@pytest.fixture
def mock_telegram_inline_callback_query() -> MagicMock:
    """Create a mock inline callback query."""
    return create_inline_callback_query()


# =============================================================================
# Update Factory and Fixtures
# =============================================================================

def create_telegram_update(
    update_id: int = 100001,
    message: MagicMock | None = None,
    edited_message: MagicMock | None = None,
    channel_post: MagicMock | None = None,
    edited_channel_post: MagicMock | None = None,
    callback_query: MagicMock | None = None,
    inline_query: MagicMock | None = None,
    chosen_inline_result: MagicMock | None = None,
    shipping_query: MagicMock | None = None,
    pre_checkout_query: MagicMock | None = None,
    poll: MagicMock | None = None,
    poll_answer: MagicMock | None = None,
    my_chat_member: MagicMock | None = None,
    chat_member: MagicMock | None = None,
    chat_join_request: MagicMock | None = None,
) -> MagicMock:
    """
    Factory function to create a mock Telegram Update.

    Args:
        update_id: The update's unique identifier
        message: New incoming message
        edited_message: Edited message
        channel_post: New channel post
        edited_channel_post: Edited channel post
        callback_query: Incoming callback query
        inline_query: Incoming inline query
        chosen_inline_result: Result of inline query chosen by user
        shipping_query: Shipping query
        pre_checkout_query: Pre-checkout query
        poll: New poll state
        poll_answer: User changed their answer in a poll
        my_chat_member: Bot's chat member status changed
        chat_member: Chat member status changed
        chat_join_request: User sent a join request

    Returns:
        MagicMock representing a Telegram Update
    """
    update = MagicMock()
    update.update_id = update_id
    update.message = message
    update.edited_message = edited_message
    update.channel_post = channel_post
    update.edited_channel_post = edited_channel_post
    update.callback_query = callback_query
    update.inline_query = inline_query
    update.chosen_inline_result = chosen_inline_result
    update.shipping_query = shipping_query
    update.pre_checkout_query = pre_checkout_query
    update.poll = poll
    update.poll_answer = poll_answer
    update.my_chat_member = my_chat_member
    update.chat_member = chat_member
    update.chat_join_request = chat_join_request

    # Helper to get event type
    def _get_event_type():
        if message:
            return "message"
        if edited_message:
            return "edited_message"
        if channel_post:
            return "channel_post"
        if edited_channel_post:
            return "edited_channel_post"
        if callback_query:
            return "callback_query"
        if inline_query:
            return "inline_query"
        return "unknown"

    type(update).event_type = PropertyMock(return_value=_get_event_type())

    return update


def create_message_update(
    update_id: int = 100001,
    text: str = "Hello, this is a test message",
    message_id: int = FIXTURE_MESSAGE_ID,
    **kwargs,
) -> MagicMock:
    """
    Factory function to create a mock Update with a text message.

    Args:
        update_id: The update's unique identifier
        text: Message text content
        message_id: Unique message identifier
        **kwargs: Additional message parameters

    Returns:
        MagicMock representing an Update with a message
    """
    message = create_telegram_message(
        message_id=message_id,
        text=text,
        **kwargs,
    )
    return create_telegram_update(update_id=update_id, message=message)


def create_callback_update(
    update_id: int = 100001,
    callback_data: str = "callback_data",
    **kwargs,
) -> MagicMock:
    """
    Factory function to create a mock Update with a callback query.

    Args:
        update_id: The update's unique identifier
        callback_data: Data associated with the callback button
        **kwargs: Additional callback query parameters

    Returns:
        MagicMock representing an Update with a callback query
    """
    callback_query = create_telegram_callback_query(data=callback_data, **kwargs)
    return create_telegram_update(update_id=update_id, callback_query=callback_query)


def create_command_update(
    update_id: int = 100001,
    command: str = "/start",
    args: str | None = None,
    **kwargs,
) -> MagicMock:
    """
    Factory function to create a mock Update with a command message.

    Args:
        update_id: The update's unique identifier
        command: The command (e.g., "/start")
        args: Arguments after the command
        **kwargs: Additional message parameters

    Returns:
        MagicMock representing an Update with a command message
    """
    message = create_telegram_command_message(
        command=command,
        args=args,
        **kwargs,
    )
    return create_telegram_update(update_id=update_id, message=message)


@pytest.fixture
def mock_telegram_update() -> MagicMock:
    """Create a standard mock Telegram update with a text message."""
    return create_message_update()


@pytest.fixture
def mock_telegram_update_callback() -> MagicMock:
    """Create a mock Telegram update with a callback query."""
    return create_callback_update()


@pytest.fixture
def mock_telegram_update_command_start() -> MagicMock:
    """Create a mock Telegram update with /start command."""
    return create_command_update(command="/start")


@pytest.fixture
def mock_telegram_update_command_help() -> MagicMock:
    """Create a mock Telegram update with /help command."""
    return create_command_update(command="/help")


@pytest.fixture
def mock_telegram_update_edited_message() -> MagicMock:
    """Create a mock Telegram update with an edited message."""
    edited_message = create_telegram_message(
        message_id=FIXTURE_MESSAGE_ID,
        text="Edited message content",
        edit_date=FIXTURE_TIMESTAMP_LATER,
    )
    return create_telegram_update(update_id=100001, edited_message=edited_message)


# =============================================================================
# Bot Factory and Fixtures
# =============================================================================

def create_telegram_bot(
    id: int = FIXTURE_BOT_ID,
    username: str = "test_bot",
    first_name: str = "TestBot",
    can_join_groups: bool = True,
    can_read_all_group_messages: bool = False,
    supports_inline_queries: bool = True,
) -> MagicMock:
    """
    Factory function to create a mock Telegram Bot instance.

    Args:
        id: Bot's unique identifier
        username: Bot's username
        first_name: Bot's display name
        can_join_groups: Whether bot can join groups
        can_read_all_group_messages: Whether bot can read all messages
        supports_inline_queries: Whether bot supports inline queries

    Returns:
        MagicMock representing a Telegram Bot
    """
    bot = MagicMock()
    bot.id = id
    bot.username = username
    bot.first_name = first_name
    bot.can_join_groups = can_join_groups
    bot.can_read_all_group_messages = can_read_all_group_messages
    bot.supports_inline_queries = supports_inline_queries

    # Add async methods commonly used
    bot.send_message = AsyncMock(return_value=create_telegram_message())
    bot.send_photo = AsyncMock(return_value=create_telegram_message_with_photo())
    bot.send_document = AsyncMock(return_value=create_telegram_message_with_document())
    bot.edit_message_text = AsyncMock(return_value=create_telegram_message())
    bot.delete_message = AsyncMock(return_value=True)
    bot.answer_callback_query = AsyncMock(return_value=True)
    bot.get_me = AsyncMock(return_value=create_bot_user(id=id, username=username, first_name=first_name))
    bot.get_chat = AsyncMock(return_value=create_telegram_chat())
    bot.get_chat_member = AsyncMock(return_value=MagicMock())
    bot.forward_message = AsyncMock(return_value=create_telegram_message())
    bot.copy_message = AsyncMock(return_value=MagicMock())

    return bot


@pytest.fixture
def mock_telegram_bot() -> MagicMock:
    """Create a standard mock Telegram Bot instance."""
    return create_telegram_bot()


# =============================================================================
# Inline Query Factory and Fixtures
# =============================================================================

def create_telegram_inline_query(
    id: str = "inline_query_12345",
    from_user: MagicMock | None = None,
    query: str = "search query",
    offset: str = "",
    chat_type: str | None = None,
    location: MagicMock | None = None,
) -> MagicMock:
    """
    Factory function to create a mock Telegram InlineQuery.

    Args:
        id: Unique identifier for this query
        from_user: Sender of the query
        query: Text of the query
        offset: Offset of the results to be returned
        chat_type: Type of the chat the query was sent from
        location: Sender location (for location-based results)

    Returns:
        MagicMock representing a Telegram InlineQuery
    """
    inline_query = MagicMock()
    inline_query.id = id
    inline_query.from_user = from_user or create_telegram_user()
    inline_query.query = query
    inline_query.offset = offset
    inline_query.chat_type = chat_type
    inline_query.location = location

    # Add async methods
    inline_query.answer = AsyncMock(return_value=True)

    return inline_query


@pytest.fixture
def mock_telegram_inline_query() -> MagicMock:
    """Create a standard mock Telegram inline query."""
    return create_telegram_inline_query()


# =============================================================================
# Message Entity Factory
# =============================================================================

def create_message_entity(
    type: str = "bold",
    offset: int = 0,
    length: int = 5,
    url: str | None = None,
    user: MagicMock | None = None,
    language: str | None = None,
    custom_emoji_id: str | None = None,
) -> MagicMock:
    """
    Factory function to create a mock Telegram MessageEntity.

    Args:
        type: Type of entity (mention, hashtag, cashtag, bot_command, url,
              email, phone_number, bold, italic, underline, strikethrough,
              spoiler, code, pre, text_link, text_mention, custom_emoji)
        offset: Offset in UTF-16 code units
        length: Length of the entity in UTF-16 code units
        url: URL for text_link type
        user: User for text_mention type
        language: Programming language for pre type
        custom_emoji_id: Custom emoji ID

    Returns:
        MagicMock representing a MessageEntity
    """
    entity = MagicMock()
    entity.type = type
    entity.offset = offset
    entity.length = length
    entity.url = url
    entity.user = user
    entity.language = language
    entity.custom_emoji_id = custom_emoji_id

    return entity


# =============================================================================
# Composite Scenarios for Integration Testing
# =============================================================================

@pytest.fixture
def telegram_conversation_scenario(
    mock_telegram_user,
    mock_telegram_chat,
    mock_telegram_bot,
) -> dict[str, Any]:
    """
    Create a complete Telegram conversation scenario.

    Returns a dict with user, chat, bot, and a series of messages
    simulating a conversation flow.
    """
    messages = [
        create_telegram_message(
            message_id=1,
            text="/start",
            from_user=mock_telegram_user,
            chat=mock_telegram_chat,
        ),
        create_telegram_message(
            message_id=2,
            text="Welcome! How can I help you?",
            from_user=create_bot_user(),
            chat=mock_telegram_chat,
        ),
        create_telegram_message(
            message_id=3,
            text="I need help with my account",
            from_user=mock_telegram_user,
            chat=mock_telegram_chat,
        ),
    ]

    return {
        "user": mock_telegram_user,
        "chat": mock_telegram_chat,
        "bot": mock_telegram_bot,
        "messages": messages,
        "user_id": FIXTURE_USER_ID,
        "chat_id": FIXTURE_CHAT_ID,
    }


@pytest.fixture
def telegram_callback_scenario(
    mock_telegram_user,
    mock_telegram_chat,
    mock_telegram_bot,
) -> dict[str, Any]:
    """
    Create a Telegram callback query scenario.

    Returns a dict simulating a user clicking an inline button.
    """
    original_message = create_telegram_message(
        message_id=FIXTURE_MESSAGE_ID,
        text="Select an agent:",
        from_user=create_bot_user(),
        chat=mock_telegram_chat,
    )

    callback_query = create_telegram_callback_query(
        from_user=mock_telegram_user,
        message=original_message,
        data="agent_select:assistant",
    )

    update = create_telegram_update(callback_query=callback_query)

    return {
        "user": mock_telegram_user,
        "chat": mock_telegram_chat,
        "bot": mock_telegram_bot,
        "original_message": original_message,
        "callback_query": callback_query,
        "update": update,
        "callback_data": "agent_select:assistant",
    }


@pytest.fixture
def telegram_group_scenario(
    mock_telegram_user,
    mock_telegram_group_chat,
    mock_telegram_bot,
) -> dict[str, Any]:
    """
    Create a Telegram group chat scenario.

    Returns a dict simulating messages in a group chat.
    """
    messages = [
        create_telegram_message(
            message_id=1,
            text="/start@test_bot",
            from_user=mock_telegram_user,
            chat=mock_telegram_group_chat,
        ),
        create_telegram_message(
            message_id=2,
            text="@test_bot help me",
            from_user=mock_telegram_user,
            chat=mock_telegram_group_chat,
        ),
    ]

    return {
        "user": mock_telegram_user,
        "chat": mock_telegram_group_chat,
        "bot": mock_telegram_bot,
        "messages": messages,
        "chat_id": mock_telegram_group_chat.id,
    }


# =============================================================================
# Parametrized Fixture Helpers
# =============================================================================

def _get_all_chat_types() -> list[str]:
    """Get all chat type values."""
    return ["private", "group", "supergroup", "channel"]


def _get_all_message_entity_types() -> list[str]:
    """Get common message entity types."""
    return [
        "mention", "hashtag", "cashtag", "bot_command", "url",
        "email", "phone_number", "bold", "italic", "underline",
        "strikethrough", "spoiler", "code", "pre", "text_link",
        "text_mention", "custom_emoji",
    ]


def pytest_generate_tests(metafunc):
    """Generate tests for parametrized fixtures."""
    if "any_chat_type" in metafunc.fixturenames:
        metafunc.parametrize("any_chat_type", _get_all_chat_types())
    if "any_entity_type" in metafunc.fixturenames:
        metafunc.parametrize("any_entity_type", _get_all_message_entity_types())
