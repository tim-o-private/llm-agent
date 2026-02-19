"""Chat service for handling chat processing logic."""
# @docs memory-bank/patterns/api-patterns.md#pattern-3-service-layer-pattern
# @rules memory-bank/rules/api-rules.json#api-003
# @examples memory-bank/patterns/api-patterns.md#pattern-4-dependency-injection-pattern

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

import psycopg
from fastapi import HTTPException, Request

try:
    from ..config.constants import CHAT_MESSAGE_HISTORY_TABLE_NAME, DEFAULT_LOG_LEVEL
    from ..database.supabase_client import get_supabase_client
    from ..dependencies.auth import get_jwt_from_request_context
    from ..models.chat import ChatRequest, ChatResponse
    from ..protocols.agent_executor import AgentExecutorProtocol
    from ..security.tool_wrapper import ApprovalContext, wrap_tools_with_approval
    from ..services.audit_service import AuditService
    from ..services.pending_actions import PendingActionsService
except ImportError:
    from config.constants import CHAT_MESSAGE_HISTORY_TABLE_NAME, DEFAULT_LOG_LEVEL
    from database.supabase_client import get_supabase_client
    from models.chat import ChatRequest, ChatResponse
    from protocols.agent_executor import AgentExecutorProtocol
    from security.tool_wrapper import ApprovalContext, wrap_tools_with_approval

    from services.audit_service import AuditService
    from services.pending_actions import PendingActionsService

from langchain.memory import ConversationBufferWindowMemory
from langchain_core.messages import BaseMessage
from langchain_postgres import PostgresChatMessageHistory

logger = logging.getLogger(__name__)


class AsyncConversationBufferWindowMemory(ConversationBufferWindowMemory):
    """Properly implemented async version of ConversationBufferWindowMemory.

    This fixes the default implementation which uses run_in_executor to run
    the synchronous load_memory_variables method, causing it to try to access
    chat_memory.messages synchronously.
    """

    async def aload_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Properly async implementation that directly calls aget_messages."""
        messages = await self.chat_memory.aget_messages()

        # Apply window just like buffer_as_messages does, but asynchronously
        if self.k > 0:
            messages = messages[-self.k * 2:]

        return {self.memory_key: messages if self.return_messages else self.messages_to_string(messages)}

    def messages_to_string(self, messages: List[BaseMessage]) -> str:
        """Convert messages to string format, similar to buffer_as_str."""
        from langchain.schema import get_buffer_string
        return get_buffer_string(
            messages,
            human_prefix=self.human_prefix,
            ai_prefix=self.ai_prefix,
        )


class ChatService:
    """Service for handling chat processing logic."""

    def __init__(self, agent_executor_cache: Dict[Tuple[str, str], Any]):
        """Initialize the chat service with an agent executor cache.

        Args:
            agent_executor_cache: Cache for storing agent executors by (user_id, agent_name)
        """
        self.agent_executor_cache = agent_executor_cache
        self._load_locks: Dict[Tuple[str, str], asyncio.Lock] = {}

    def create_chat_memory(self, session_id: str, pg_connection: psycopg.AsyncConnection) -> AsyncConversationBufferWindowMemory:
        """Create chat memory for a session.

        Args:
            session_id: The session ID for chat history
            pg_connection: PostgreSQL connection for chat history

        Returns:
            Configured async conversation buffer window memory
        """
        # Initialize PostgresChatMessageHistory using the connection from the pool
        chat_memory = PostgresChatMessageHistory(
            CHAT_MESSAGE_HISTORY_TABLE_NAME,
            session_id,
            async_connection=pg_connection
        )

        # Wrap the chat_memory in ConversationBufferWindowMemory
        agent_short_term_memory = AsyncConversationBufferWindowMemory(
            chat_memory=chat_memory,
            k=50,  # Keep last 50 messages (user + AI). Can be configured.
            return_messages=True,
            memory_key="chat_history",  # Must match the input variable in the agent's prompt
            input_key="input"  # Must match the key for the user's input message
        )

        return agent_short_term_memory

    async def get_or_load_agent_executor(
        self,
        user_id: str,
        agent_name: str,
        session_id: str,
        agent_loader_module: Any,
        memory: AsyncConversationBufferWindowMemory
    ) -> AgentExecutorProtocol:
        """Get agent executor from cache or load a new one (async).

        Uses async loading path to avoid blocking the event loop.
        Per-key locking prevents duplicate concurrent loads for the same agent.

        Args:
            user_id: User ID
            agent_name: Name of the agent
            session_id: Session ID for history
            agent_loader_module: Agent loader module
            memory: Chat memory for the session

        Returns:
            Agent executor instance

        Raises:
            HTTPException: If agent loading fails or executor is invalid
        """
        cache_key = (user_id, agent_name)

        if cache_key in self.agent_executor_cache:
            agent_executor = self.agent_executor_cache[cache_key]
            logger.debug(f"Cache HIT for agent executor: key={cache_key}")
        else:
            # Per-key lock prevents duplicate concurrent loads
            lock = self._load_locks.setdefault(cache_key, asyncio.Lock())
            async with lock:
                # Double-check after acquiring lock
                if cache_key in self.agent_executor_cache:
                    agent_executor = self.agent_executor_cache[cache_key]
                    logger.debug(f"Cache HIT (post-lock) for agent executor: key={cache_key}")
                else:
                    logger.debug(f"Cache MISS for agent executor: key={cache_key}. Loading new executor.")
                    try:
                        # Prefer async path if available
                        if hasattr(agent_loader_module, 'async_load_agent_executor'):
                            agent_executor = await agent_loader_module.async_load_agent_executor(
                                agent_name=agent_name,
                                user_id=user_id,
                                session_id=session_id,
                                log_level=DEFAULT_LOG_LEVEL,
                            )
                        else:
                            # Fallback to sync path (e.g., CLI usage)
                            agent_executor = agent_loader_module.load_agent_executor(
                                user_id=user_id,
                                agent_name=agent_name,
                                session_id=session_id,
                                log_level=DEFAULT_LOG_LEVEL,
                            )
                        self.agent_executor_cache[cache_key] = agent_executor
                    except Exception as e:
                        logger.error(f"Error loading agent executor for agent {agent_name}: {e}", exc_info=True)
                        raise HTTPException(status_code=500, detail=f"Could not load agent: {e}")

        # Check if agent_executor implements the required interface
        if not hasattr(agent_executor, 'ainvoke') or not hasattr(agent_executor, 'memory'):
            logger.error(f"Loaded agent does not implement required interface. Type: {type(agent_executor)}")
            raise HTTPException(status_code=500, detail="Agent loading failed to produce a compatible executor.")

        # CRITICAL: Ensure the cached/newly loaded executor uses the correct memory for THIS session
        agent_executor.memory = memory

        return agent_executor

    async def _push_to_telegram_if_linked(
        self, user_id: str, session_id: str, response_text: str, db_client
    ) -> None:
        """Push an agent response to Telegram if this session is the linked one."""
        # 1. Check if user has an active Telegram link
        channel_result = (
            await db_client.table("user_channels")
            .select("channel_id")
            .eq("user_id", user_id)
            .eq("channel_type", "telegram")
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if not channel_result.data:
            return
        telegram_chat_id = channel_result.data[0]["channel_id"]

        # 2. Check if this session is the most recent web session (the linked one)
        web_session = (
            await db_client.table("chat_sessions")
            .select("chat_id")
            .eq("user_id", user_id)
            .eq("channel", "web")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if not web_session.data or str(web_session.data[0]["chat_id"]) != session_id:
            return

        # 3. Send to Telegram
        try:
            from ..channels.telegram_bot import get_telegram_bot_service
        except ImportError:
            from channels.telegram_bot import get_telegram_bot_service

        bot_service = get_telegram_bot_service()
        if bot_service:
            await bot_service.send_notification(telegram_chat_id, response_text)

    def extract_tool_info(self, response_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Extract tool information from agent response data.

        Args:
            response_data: Response data from agent execution

        Returns:
            Tuple of (tool_name, tool_input) or (None, None) if no tool info
        """
        invoked_tool_name: Optional[str] = None
        invoked_tool_input: Optional[Dict[str, Any]] = None

        # Example of how one might extract the last tool call, if needed by client
        if "intermediate_steps" in response_data and response_data["intermediate_steps"]:
            last_step = response_data["intermediate_steps"][-1]
            if isinstance(last_step, tuple) and len(last_step) > 0:
                action, observation = last_step
                if hasattr(action, 'tool'):
                    invoked_tool_name = action.tool
                if hasattr(action, 'tool_input'):
                    invoked_tool_input = action.tool_input

        return invoked_tool_name, invoked_tool_input

    async def process_chat(
        self,
        chat_input: ChatRequest,
        user_id: str,
        pg_connection: psycopg.AsyncConnection,
        agent_loader_module: Any,
        request: Request
    ) -> ChatResponse:
        """Process a chat request and return a response.

        Args:
            chat_input: The chat request
            user_id: User ID
            pg_connection: PostgreSQL connection
            agent_loader_module: Agent loader module
            request: FastAPI request object

        Returns:
            Chat response

        Raises:
            HTTPException: For various error conditions
        """
        logger.debug(f"Processing chat request for agent {chat_input.agent_name} with session_id: {chat_input.session_id} from user {user_id}")

        if not chat_input.session_id:
            logger.error("session_id missing from chat_input")
            raise HTTPException(status_code=400, detail="session_id is required")

        session_id_for_history = chat_input.session_id
        agent_name = chat_input.agent_name

        try:
            # Create chat memory
            agent_short_term_memory = self.create_chat_memory(session_id_for_history, pg_connection)

            # Get or load agent executor
            agent_executor = await self.get_or_load_agent_executor(
                user_id=user_id,
                agent_name=agent_name,
                session_id=session_id_for_history,
                agent_loader_module=agent_loader_module,
                memory=agent_short_term_memory
            )

            # Wrap tools with approval checking
            try:
                supabase_client = await get_supabase_client()
                audit_service = AuditService(supabase_client)
                pending_actions_service = PendingActionsService(
                    db_client=supabase_client,
                    audit_service=audit_service,
                )
                approval_context = ApprovalContext(
                    user_id=user_id,
                    session_id=session_id_for_history,
                    agent_name=agent_name,
                    db_client=supabase_client,
                    pending_actions_service=pending_actions_service,
                    audit_service=audit_service,
                )
                if hasattr(agent_executor, 'tools') and agent_executor.tools:
                    wrap_tools_with_approval(agent_executor.tools, approval_context)
                    logger.info(f"Wrapped {len(agent_executor.tools)} tools with approval for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to wrap tools with approval (non-fatal): {e}")

            try:
                # Execute the agent
                response_data = await agent_executor.ainvoke({"input": chat_input.message})
                ai_response_content = response_data.get("output", "No output from agent.")

                # Handle content block lists from newer langchain-anthropic versions
                if isinstance(ai_response_content, list):
                    ai_response_content = "".join(
                        block.get("text", "") for block in ai_response_content
                        if isinstance(block, dict) and block.get("type") == "text"
                    ) or "No text content in response."

                # Extract tool information
                invoked_tool_name, invoked_tool_input = self.extract_tool_info(response_data)

                chat_response_payload = ChatResponse(
                    session_id=session_id_for_history,
                    response=ai_response_content,
                    tool_name=invoked_tool_name,
                    tool_input=invoked_tool_input,
                    error=None
                )
                logger.info(f"Successfully processed chat. Returning to client: {chat_response_payload.model_dump_json(indent=2)}")

                # Push to Telegram if this is the linked session (best-effort)
                try:
                    tg_text = f"*You (web):* {chat_input.message}\n\n{ai_response_content}"
                    await self._push_to_telegram_if_linked(
                        user_id, session_id_for_history, tg_text, supabase_client
                    )
                except Exception as e:
                    logger.debug(f"Telegram push skipped: {e}")

                return chat_response_payload

            except Exception as e:
                logger.error(f"Error during agent execution for session {session_id_for_history}: {e}", exc_info=True)
                error_response_payload = ChatResponse(
                    session_id=session_id_for_history,
                    response="An error occurred processing your request.",
                    error=str(e)
                )
                logger.info(f"Error during agent execution. Returning to client: {error_response_payload.model_dump_json(indent=2)}")
                return error_response_payload

        except psycopg.Error as pe:
            logger.error(f"Database error (psycopg.Error) during chat_memory setup for session {session_id_for_history}: {pe}", exc_info=True)
            db_error_payload = ChatResponse(
                session_id=session_id_for_history,
                response="A database error occurred during chat setup.",
                error=f"Database error: {str(pe)}"
            )
            logger.info(f"Database error. Returning to client: {db_error_payload.model_dump_json(indent=2)}")
            raise HTTPException(status_code=503, detail=f"Database error during chat setup: {pe}")

        except Exception as e:
            logger.error(f"Failed to process chat request before agent execution for session {session_id_for_history}: {e}", exc_info=True)
            setup_error_payload = ChatResponse(
                session_id=session_id_for_history,
                response="An error occurred setting up the chat environment.",
                error=f"Setup error: {str(e)}"
            )
            logger.info(f"Setup error. Returning to client: {setup_error_payload.model_dump_json(indent=2)}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail=f"Could not process chat request: {e}")


# Global instance for use in main.py
_chat_service: Optional[ChatService] = None


def get_chat_service(agent_executor_cache: Dict[Tuple[str, str], Any]) -> ChatService:
    """Get the global chat service instance.

    Args:
        agent_executor_cache: Cache for storing agent executors

    Returns:
        Chat service instance
    """
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService(agent_executor_cache)
    return _chat_service
