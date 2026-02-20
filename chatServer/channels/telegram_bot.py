"""
Telegram bot service for receiving and sending messages.

Uses aiogram 3.x in webhook mode — the bot runs inside the FastAPI process.
Telegram POSTs updates to /api/telegram/webhook, which feeds them to the dispatcher.

Capabilities:
- Outbound: send notifications, heartbeat summaries, approval inline keyboards
- Inbound: /start linking, free-text messages routed to agent, approve/reject callbacks
"""

import json
import logging
import uuid
from typing import Optional

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

router = Router()


class TelegramBotService:
    """
    Manages the Telegram bot lifecycle and message routing.

    Initialized once at app startup (if TELEGRAM_BOT_TOKEN is set).
    Processes updates via webhook — no long-polling thread needed.
    """

    def __init__(self, token: str):
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        # Guard against re-attaching a module-level router that's already attached
        # (can happen in tests or if multiple instances are created)
        if not router.parent_router:
            self.dp.include_router(router)
        self._db_client = None  # Set after initialization

    def set_db_client(self, db_client) -> None:
        """Set the database client for channel lookups."""
        self._db_client = db_client

    async def setup_webhook(self, webhook_url: str) -> None:
        """Register the webhook URL with Telegram."""
        try:
            await self.bot.set_webhook(webhook_url)
            logger.info(f"Telegram webhook set to {webhook_url}")
        except Exception as e:
            logger.error(f"Failed to set Telegram webhook: {e}", exc_info=True)

    async def process_update(self, update_data: dict) -> None:
        """Process an incoming webhook update from Telegram."""
        try:
            update = types.Update.model_validate(update_data)
            await self.dp.feed_update(self.bot, update)
        except Exception as e:
            logger.error(f"Error processing Telegram update: {e}", exc_info=True)

    async def send_notification(
        self,
        chat_id: str,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> None:
        """Send a text notification to a Telegram chat."""
        try:
            # Truncate to Telegram's 4096 char limit
            if len(text) > 4000:
                text = text[:3997] + "..."
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram message to {chat_id}: {e}", exc_info=True)

    async def send_approval_request(
        self,
        chat_id: str,
        action_id: str,
        tool_name: str,
        tool_args: dict,
    ) -> None:
        """Send an approval request with inline approve/reject buttons."""
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Approve", callback_data=f"approve:{action_id}"),
                    InlineKeyboardButton(text="Reject", callback_data=f"reject:{action_id}"),
                ]
            ]
        )

        args_preview = json.dumps(tool_args, indent=2)[:500]
        text = f"*Action requires approval*\n\nTool: `{tool_name}`\nArgs:\n```\n{args_preview}\n```"

        await self.send_notification(chat_id, text, reply_markup=keyboard)

    async def shutdown(self) -> None:
        """Clean up bot resources."""
        try:
            await self.bot.delete_webhook()
            await self.bot.session.close()
            logger.info("Telegram bot shutdown complete")
        except Exception as e:
            logger.error(f"Error during Telegram bot shutdown: {e}")


# =============================================================================
# Message Handlers (registered on the module-level router)
# =============================================================================


@router.message(CommandStart())
async def handle_start(message: types.Message) -> None:
    """
    Handle /start command — used for account linking.

    Usage: /start <linking_token>
    The token is generated via the web UI and has a 10-minute expiry.
    """
    if not message.text:
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "Welcome! To link your account, use the link from your Clarity settings page.\n\n"
            "It will give you a command like: `/start abc123`"
        )
        return

    token = parts[1]
    chat_id = str(message.chat.id)

    # Token validation is handled by the router endpoint — we just store the
    # intent here. The actual linking happens via the TelegramLinkingService
    # which is called from the router.
    bot_service = get_telegram_bot_service()
    if bot_service and bot_service._db_client:
        try:
            from ..services.telegram_linking_service import link_telegram_account

            success = await link_telegram_account(
                db_client=bot_service._db_client,
                token=token,
                chat_id=chat_id,
            )
            if success:
                await message.answer("Account linked successfully! You will receive notifications here.")
            else:
                await message.answer("Invalid or expired token. Please generate a new one from Settings.")
        except Exception as e:
            logger.error(f"Error linking Telegram account: {e}", exc_info=True)
            await message.answer("Something went wrong. Please try again.")
    else:
        await message.answer("Bot is still initializing. Please try again in a moment.")


@router.callback_query(lambda c: c.data and c.data.startswith(("approve:", "reject:")))
async def handle_approval_callback(callback: types.CallbackQuery) -> None:
    """Handle inline keyboard approve/reject button presses."""
    if not callback.data:
        return

    action, action_id = callback.data.split(":", 1)
    chat_id = str(callback.message.chat.id) if callback.message else None

    if not chat_id:
        return

    bot_service = get_telegram_bot_service()
    if not bot_service or not bot_service._db_client:
        await callback.answer("Bot not ready. Try again.")
        return

    try:
        # Look up user_id from chat_id
        result = (
            await bot_service._db_client.table("user_channels")
            .select("user_id")
            .eq("channel_type", "telegram")
            .eq("channel_id", chat_id)
            .eq("is_active", True)
            .single()
            .execute()
        )

        if not result.data:
            await callback.answer("Account not linked.")
            return

        user_id = result.data["user_id"]

        from ..services.audit_service import AuditService
        from ..services.pending_actions import PendingActionsService

        audit_service = AuditService(bot_service._db_client)
        pending_service = PendingActionsService(
            db_client=bot_service._db_client,
            audit_service=audit_service,
        )

        if action == "approve":
            result = await pending_service.approve_action(action_id, user_id)
            if result.success:
                await callback.answer("Action approved!")
                if callback.message:
                    await callback.message.edit_text(
                        callback.message.text + "\n\n_Approved_",
                        parse_mode="Markdown",
                    )
            else:
                await callback.answer(f"Failed: {result.error}")
        elif action == "reject":
            result = await pending_service.reject_action(action_id, user_id)
            await callback.answer("Action rejected.")
            if callback.message:
                await callback.message.edit_text(
                    callback.message.text + "\n\n_Rejected_",
                    parse_mode="Markdown",
                )

    except Exception as e:
        logger.error(f"Error handling approval callback: {e}", exc_info=True)
        await callback.answer("Error processing action.")


@router.message()
async def handle_message(message: types.Message) -> None:
    """
    Handle free-text messages — route to the assistant agent.

    This is the channel normalization pattern: same agent, same tools,
    same approval system, different input/output channel.
    """
    if not message.text:
        return

    chat_id = str(message.chat.id)
    bot_service = get_telegram_bot_service()

    if not bot_service or not bot_service._db_client:
        await message.answer("Bot is initializing. Try again in a moment.")
        return

    try:
        # Look up user_id from chat_id
        result = (
            await bot_service._db_client.table("user_channels")
            .select("user_id")
            .eq("channel_type", "telegram")
            .eq("channel_id", chat_id)
            .eq("is_active", True)
            .single()
            .execute()
        )

        if not result.data:
            await message.answer("Your account isn't linked yet. Go to Settings in the web app to connect Telegram.")
            return

        user_id = result.data["user_id"]

        # Route to assistant agent
        from ..security.tool_wrapper import ApprovalContext, wrap_tools_with_approval
        from ..services.audit_service import AuditService
        from ..services.pending_actions import PendingActionsService
        from src.core.agent_loader_db import load_agent_executor_db

        # Cross-channel session sharing: reuse most recent web session if one exists
        web_session_result = (
            await bot_service._db_client.table("chat_sessions")
            .select("chat_id")
            .eq("user_id", user_id)
            .eq("channel", "web")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )

        if web_session_result.data and web_session_result.data[0].get("chat_id"):
            session_id = str(web_session_result.data[0]["chat_id"])
            logger.info(f"Telegram sharing web session: {session_id}")
        else:
            session_id = str(uuid.uuid4())
            logger.info(f"Telegram creating new session: {session_id}")

        # Ensure chat_sessions row exists for this Telegram conversation
        existing = (
            await bot_service._db_client.table("chat_sessions")
            .select("id")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if not existing.data:
            await bot_service._db_client.table("chat_sessions").insert(
                {
                    "user_id": user_id,
                    "session_id": session_id,
                    "channel": "telegram",
                    "agent_name": "assistant",
                    "is_active": True,
                }
            ).execute()

        import asyncio
        loop = asyncio.get_event_loop()
        agent_executor = await loop.run_in_executor(
            None,
            lambda: load_agent_executor_db(
                agent_name="assistant",
                user_id=user_id,
                session_id=session_id,
                channel="telegram",
            ),
        )

        # Wrap tools with approval
        audit_service = AuditService(bot_service._db_client)
        pending_service = PendingActionsService(
            db_client=bot_service._db_client,
            audit_service=audit_service,
        )
        approval_context = ApprovalContext(
            user_id=user_id,
            session_id=session_id,
            agent_name="assistant",
            db_client=bot_service._db_client,
            pending_actions_service=pending_service,
            audit_service=audit_service,
        )
        if hasattr(agent_executor, "tools") and agent_executor.tools:
            wrap_tools_with_approval(agent_executor.tools, approval_context)

        # Set up persistent memory and invoke agent within a DB connection scope
        from ..database.connection import get_database_manager
        from ..config.constants import CHAT_MESSAGE_HISTORY_TABLE_NAME

        db_manager = get_database_manager()
        await db_manager.ensure_initialized()

        async with db_manager.pool.connection() as pg_conn:
            # Wire up memory so this turn is saved to the shared message store
            from langchain_postgres import PostgresChatMessageHistory

            from ..services.chat import AsyncConversationBufferWindowMemory

            pg_history = PostgresChatMessageHistory(
                CHAT_MESSAGE_HISTORY_TABLE_NAME,
                session_id,
                async_connection=pg_conn,
            )
            agent_executor.memory = AsyncConversationBufferWindowMemory(
                chat_memory=pg_history,
                k=50,
                return_messages=True,
                memory_key="chat_history",
                input_key="input",
            )

            # Send typing indicator
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

            # Invoke agent (memory auto-saves the turn to message_store)
            response = await agent_executor.ainvoke({"input": message.text})

        output = response.get("output", "")
        if isinstance(output, list):
            output = (
                "".join(
                    block.get("text", "") for block in output if isinstance(block, dict) and block.get("type") == "text"
                )
                or "No response."
            )

        # Send response (split if too long for Telegram's 4096 limit)
        if len(output) > 4000:
            for i in range(0, len(output), 4000):
                await message.answer(output[i : i + 4000])
        else:
            await message.answer(output)

    except Exception as e:
        logger.error(f"Error handling Telegram message from {chat_id}: {e}", exc_info=True)
        await message.answer("Sorry, something went wrong. Please try again.")


# =============================================================================
# Global singleton
# =============================================================================

_telegram_bot_service: Optional[TelegramBotService] = None


def get_telegram_bot_service() -> Optional[TelegramBotService]:
    """Get the global Telegram bot service instance (None if not configured)."""
    return _telegram_bot_service


def initialize_telegram_bot(token: str) -> TelegramBotService:
    """Initialize the global Telegram bot service."""
    global _telegram_bot_service
    _telegram_bot_service = TelegramBotService(token)
    return _telegram_bot_service
