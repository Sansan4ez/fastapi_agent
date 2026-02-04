"""
ACP (Agent Communication Protocol) Telegram Bot Handlers

This module provides Telegram bot command handlers for interacting with
ACP agents:
- /agents - List available agents
- /agent <name> <message> - Invoke an agent with a message
- /acp_status - Check ACP server status
"""

from aiogram import F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.router import Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from app.services.acp_client import ACPClientService, ACPClientError, get_acp_client
from app.config import settings


router = Router()

# Maximum message length for Telegram
MAX_TG_MESSAGE_LENGTH = 4096


def truncate_message(text: str, max_length: int = MAX_TG_MESSAGE_LENGTH) -> str:
    """Truncate message to fit Telegram's length limit."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 100] + "\n\n... (message truncated)"


@router.message(Command("agents"))
async def cmd_list_agents(message: Message):
    """
    Handler for /agents command.
    Lists all available agents on the ACP server.
    """
    try:
        await message.answer("🔍 Discovering available agents...")

        async with ACPClientService() as client:
            agents = await client.list_agents()

        if not agents:
            await message.answer(
                "📭 No agents available on the ACP server.\n\n"
                f"Server URL: <code>{settings.ACP_SERVER_URL}</code>"
            )
            return

        # Build agent list message
        agent_lines = []
        for agent in agents:
            agent_lines.append(f"• <b>{agent.name}</b>\n  {agent.description}")

        agents_text = "\n\n".join(agent_lines)
        response = (
            f"🤖 <b>Available Agents ({len(agents)})</b>\n\n"
            f"{agents_text}\n\n"
            f"💡 Use <code>/agent &lt;name&gt; &lt;message&gt;</code> to invoke an agent."
        )

        await message.answer(truncate_message(response))

    except ACPClientError as e:
        logger.error(f"ACP client error listing agents: {e}")
        await message.answer(
            f"❌ Failed to connect to ACP server.\n\n"
            f"Error: {e}\n\n"
            f"Server URL: <code>{settings.ACP_SERVER_URL}</code>"
        )
    except Exception as e:
        logger.error(f"Unexpected error listing agents: {e}")
        await message.answer(
            "❌ An unexpected error occurred while listing agents.\n"
            "Please try again later."
        )


@router.message(Command("agent"))
async def cmd_invoke_agent(message: Message, command: CommandObject):
    """
    Handler for /agent command.
    Invokes a specific agent with a user message.

    Usage: /agent <agent_name> <message>
    """
    if not command.args:
        await message.answer(
            "ℹ️ <b>Usage:</b> <code>/agent &lt;name&gt; &lt;message&gt;</code>\n\n"
            "Example: <code>/agent echo Hello, agent!</code>\n\n"
            "Use <code>/agents</code> to see available agents."
        )
        return

    # Parse agent name and message from args
    args_parts = command.args.split(maxsplit=1)
    agent_name = args_parts[0]

    if len(args_parts) < 2:
        await message.answer(
            f"ℹ️ Please provide a message for agent <b>{agent_name}</b>.\n\n"
            f"Example: <code>/agent {agent_name} Hello!</code>"
        )
        return

    user_message = args_parts[1]

    try:
        # Show typing indicator
        processing_msg = await message.answer(
            f"⏳ Invoking agent <b>{agent_name}</b>...\n\n"
            f"<i>Your message:</i> {user_message[:100]}{'...' if len(user_message) > 100 else ''}"
        )

        # Use session ID based on user ID for conversation continuity
        session_id = f"tg_user_{message.from_user.id}"

        async with ACPClientService() as client:
            result = await client.run_agent(
                agent_name=agent_name,
                message=user_message,
                session_id=session_id
            )

        # Format response
        status_emoji = "✅" if result.status == "completed" else "⚠️"
        response = (
            f"{status_emoji} <b>Agent: {agent_name}</b>\n"
            f"<i>Status: {result.status}</i>\n\n"
            f"{result.output}"
        )

        # Delete processing message and send response
        await processing_msg.delete()
        await message.answer(truncate_message(response))

    except ACPClientError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            await message.answer(
                f"❌ Agent <b>{agent_name}</b> not found.\n\n"
                "Use <code>/agents</code> to see available agents."
            )
        else:
            logger.error(f"ACP client error invoking agent {agent_name}: {e}")
            await message.answer(
                f"❌ Failed to invoke agent <b>{agent_name}</b>.\n\n"
                f"Error: {error_msg}"
            )
    except Exception as e:
        logger.error(f"Unexpected error invoking agent {agent_name}: {e}")
        await message.answer(
            f"❌ An unexpected error occurred while invoking agent <b>{agent_name}</b>.\n"
            "Please try again later."
        )


@router.message(Command("acp_status"))
async def cmd_acp_status(message: Message):
    """
    Handler for /acp_status command.
    Shows the status of the ACP server connection.
    """
    try:
        async with ACPClientService() as client:
            is_available = await client.ping()

            if is_available:
                # Try to get agent count
                try:
                    agents = await client.list_agents()
                    agent_count = len(agents)
                except Exception:
                    agent_count = "unknown"

                await message.answer(
                    f"✅ <b>ACP Server Status</b>\n\n"
                    f"🔗 URL: <code>{settings.ACP_SERVER_URL}</code>\n"
                    f"📡 Status: <b>Online</b>\n"
                    f"🤖 Agents: {agent_count}\n"
                    f"⏱ Timeout: {settings.ACP_REQUEST_TIMEOUT}s"
                )
            else:
                await message.answer(
                    f"❌ <b>ACP Server Status</b>\n\n"
                    f"🔗 URL: <code>{settings.ACP_SERVER_URL}</code>\n"
                    f"📡 Status: <b>Offline</b>\n\n"
                    "The server is not responding to ping requests."
                )

    except Exception as e:
        logger.error(f"Error checking ACP status: {e}")
        await message.answer(
            f"❌ <b>ACP Server Status</b>\n\n"
            f"🔗 URL: <code>{settings.ACP_SERVER_URL}</code>\n"
            f"📡 Status: <b>Error</b>\n\n"
            f"Could not connect: {e}"
        )


@router.message(Command("acp_help"))
async def cmd_acp_help(message: Message):
    """
    Handler for /acp_help command.
    Shows help information for ACP commands.
    """
    help_text = """
🤖 <b>ACP (Agent Communication Protocol) Commands</b>

<b>Available Commands:</b>

• <code>/agents</code>
  List all available AI agents on the ACP server.

• <code>/agent &lt;name&gt; &lt;message&gt;</code>
  Invoke an agent with your message.
  Example: <code>/agent echo Hello, world!</code>

• <code>/acp_status</code>
  Check the ACP server connection status.

• <code>/acp_help</code>
  Show this help message.

<b>About ACP:</b>
The Agent Communication Protocol enables standardized communication
between AI agents, applications, and humans. Through this bot, you
can discover and interact with various AI agents available on the
connected ACP server.

<b>Session Support:</b>
Your conversations with agents are tracked by session, allowing
for multi-turn interactions where the agent remembers context
from previous messages.
"""
    await message.answer(help_text.strip())
