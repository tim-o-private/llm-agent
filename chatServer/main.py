import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import List

import psycopg
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from utils.config_loader import ConfigLoader
from utils.logging_utils import get_logger

from .config.constants import PROMPT_CUSTOMIZATIONS_TAG
from .config.settings import get_settings
from .database.connection import get_db_connection
from .database.supabase_client import get_user_scoped_client
from .dependencies.auth import get_current_user
from .models.chat import ChatRequest, ChatResponse
from .models.prompt_customization import PromptCustomization, PromptCustomizationCreate
from .models.webhook import SupabasePayload
from .routers.actions import router as actions_router
from .routers.approvals_router import router as approvals_router
from .routers.chat_history_router import router as chat_history_router
from .routers.email_agent_router import router as email_agent_router
from .routers.external_api_router import router as external_api_router
from .routers.notifications_router import router as notifications_router
from .routers.oauth_router import router as oauth_router
from .routers.session_open_router import router as session_open_router
from .routers.telegram_router import router as telegram_router
from .routers.today_router import router as today_router
from .services.prompt_customization import get_prompt_customization_service

# Langsmith startup serialization is noisy at DEBUG — suppress to WARNING
logging.getLogger("langsmith").setLevel(logging.WARNING)
# Anthropic client logs full request/response bodies at DEBUG — suppress to WARNING
logging.getLogger("anthropic").setLevel(logging.WARNING)
# httpx logs every HTTP request at DEBUG — suppress to WARNING
logging.getLogger("httpx").setLevel(logging.WARNING)


# --- START Inserted Environment & Path Setup ---
def add_project_root_to_path_for_local_dev():
    try:
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root_dir = os.path.dirname(current_script_dir)
        settings = get_settings()
        full_src_path = os.path.join(project_root_dir, settings.llm_agent_src_path)
        if os.path.isdir(full_src_path):
            if full_src_path not in sys.path:
                sys.path.insert(0, full_src_path)
            if project_root_dir not in sys.path:
                sys.path.insert(0, project_root_dir)
    except Exception as e:
        print(f"Error setting up sys.path for local dev: {e}", file=sys.stderr)

# Initialize settings and environment
settings = get_settings()

if settings.running_in_docker:
    load_dotenv(override=True) # In Docker, load .env from /app if present
else:
    project_root_for_env = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dotenv_path = os.path.join(project_root_for_env, '.env')
    if os.path.exists(dotenv_path):
        try:
            load_dotenv(dotenv_path, override=True)
        except PermissionError:
            pass  # .env unreadable (e.g. sandboxed test environments)
    add_project_root_to_path_for_local_dev()

# Re-read settings now that .env has been loaded (Settings was created before load_dotenv)
settings.reload_from_env()

# Allow CLARITY_ANTHROPIC_API_KEY as an alias so the .env doesn't pollute
# Claude Code sessions that share the same shell environment.
# On Fly.io, ANTHROPIC_API_KEY is set directly and this is a no-op.
_clarity_key = os.getenv("CLARITY_ANTHROPIC_API_KEY")
if _clarity_key and not os.getenv("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = _clarity_key
# --- END Inserted Environment & Path Setup ---

# --- Global Cache and Configuration ---
# Initialize a global ConfigLoader. This typically loads settings from a file (e.g., settings.yaml)
# and environment variables. It's loaded once when the application starts.
# Adjust 'settings_file_path' if your main config file is named differently or located elsewhere
# relative to the project root determined by ConfigLoader's internal logic.
try:
    # Assuming ConfigLoader can be instantiated without arguments if it has defaults,
    # or provide a path to your main settings/config YAML file if needed.
    # Based on ConfigLoader's likely structure, it might try to find 'config/settings.yaml'
    # from the project root.
    GLOBAL_CONFIG_LOADER = ConfigLoader()
except Exception as e:
    # Log this critical error; the application might not be able to start correctly.
    logging.critical(f"Failed to initialize GlobalConfigLoader: {e}", exc_info=True)
    # Depending on severity, you might want to exit or raise an error that FastAPI handles at startup
    GLOBAL_CONFIG_LOADER = None # Ensure it's defined even on failure to prevent NameErrors later

# Cache for active agent executors: (user_id, agent_id) -> AgentExecutor
# AgentExecutor type hint needs to be imported, e.g., from langchain.agents import AgentExecutor
# ACTIVE_AGENTS: Dict[Tuple[str, str], AgentExecutor] = {} # REMOVED - Per documentation, this is not used.

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")  # Set this in your .env or Fly secrets

@asynccontextmanager
async def lifespan(app: FastAPI):
    from .database.connection import get_database_manager
    from .database.supabase_client import get_supabase_manager
    from .services.background_tasks import get_background_task_service
    from .services.user_instructions_cache_service import (
        initialize_user_instructions_cache,
        shutdown_user_instructions_cache,
    )

    logger.info("Application startup: Initializing resources...")

    # Initialize database manager
    db_manager = get_database_manager()
    try:
        await db_manager.initialize()
    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}", exc_info=True)

    # Initialize Supabase manager
    supabase_manager = get_supabase_manager()
    await supabase_manager.initialize()

    # System config lives in git at data/config/system/ — no Storage pull needed.
    from pathlib import Path

    data_dir = Path(os.getenv("SANDBOX_DATA_DIR", "/data"))
    system_dir = data_dir / "config" / "system"

    # Seed workflow templates to local filesystem (idempotent)
    try:
        from .workflows.templates.seed import seed_workflow_templates

        count = await seed_workflow_templates(system_dir)
        logger.info("Seeded %d workflow template files", count)
    except Exception as e:
        logger.warning("Failed to seed workflow templates: %s", e)

    # Initialize template registry (reads from local filesystem)
    try:
        from .workflows.registry import initialize_template_registry

        def _user_dir_resolver(user_id: str) -> Path:
            return data_dir / "sandboxes" / user_id

        initialize_template_registry(system_dir, user_dir_resolver=_user_dir_resolver)
        logger.info("Template registry initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize template registry: {e}", exc_info=True)

    # Initialize cache services

    try:
        await initialize_user_instructions_cache()
        logger.info("User instructions cache service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize user instructions cache service: {e}", exc_info=True)

    # Initialize workflow checkpointer (shared by Deep Agent + workflows)
    try:
        from .workflows.checkpointer import initialize_workflow_checkpointer
        await initialize_workflow_checkpointer()
        logger.info("Workflow checkpointer initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize workflow checkpointer (non-fatal): {e}", exc_info=True)

    # Initialize and start background tasks
    background_service = get_background_task_service()
    await background_service.start_background_tasks()

    # Initialize Telegram bot (optional — only if TELEGRAM_BOT_TOKEN is set)
    telegram_bot = None
    if settings.telegram_bot_token:
        from .channels.telegram_bot import initialize_telegram_bot

        telegram_bot = initialize_telegram_bot(settings.telegram_bot_token)
        # Give the bot access to the database for channel lookups (SystemClient
        # bypasses RLS — needed because the bot has no user context)
        try:
            from chatServer.database.supabase_client import create_system_client

            telegram_bot.set_db_client(await create_system_client())
        except Exception:
            logger.warning("Supabase client not ready for Telegram bot — linking will fail until reconnected")
        # Set up webhook if URL is configured
        if settings.telegram_webhook_url:
            await telegram_bot.setup_webhook(settings.telegram_webhook_url)
        logger.info("Telegram bot initialized")
    else:
        logger.info("Telegram bot not configured (TELEGRAM_BOT_TOKEN not set)")

    yield # Application runs here

    logger.info("Application shutdown: Cleaning up resources...")

    # Shut down Telegram bot
    if telegram_bot:
        await telegram_bot.shutdown()

    # Stop background tasks
    await background_service.stop_background_tasks()

    # Shut down workflow checkpointer
    try:
        from .workflows.checkpointer import shutdown_workflow_checkpointer
        await shutdown_workflow_checkpointer()
        logger.info("Workflow checkpointer shut down successfully")
    except Exception as e:
        logger.error(f"Failed to shut down workflow checkpointer: {e}", exc_info=True)

    # Shut down template registry
    try:
        from .workflows.registry import shutdown_template_registry
        shutdown_template_registry()
        logger.info("Template registry shut down successfully")
    except Exception as e:
        logger.error(f"Failed to shut down template registry: {e}", exc_info=True)

    # Stop cache services
    try:
        await shutdown_user_instructions_cache()
        logger.info("User instructions cache service stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop user instructions cache service: {e}", exc_info=True)


    # Close database manager
    await db_manager.close()

# Create app with lifespan
app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(external_api_router)
app.include_router(email_agent_router)
app.include_router(oauth_router)
app.include_router(actions_router)
app.include_router(chat_history_router)
app.include_router(notifications_router)
app.include_router(session_open_router)
app.include_router(telegram_router)
app.include_router(today_router)
app.include_router(approvals_router)

# --- Logger setup ---
logger = get_logger(__name__)

@app.post("/api/chat")
async def chat_endpoint(
    chat_input: ChatRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
    pg_connection: psycopg.AsyncConnection = Depends(get_db_connection),
):
    """Chat endpoint that processes user messages through the Deep Agent runtime.

    Supports SSE streaming when ``Accept: text/event-stream`` is sent.
    """
    wants_stream = "text/event-stream" in request.headers.get("accept", "")
    if wants_stream:
        return await _handle_chat_stream(chat_input, user_id, pg_connection)
    return await _handle_chat(chat_input, user_id, pg_connection)


async def _handle_chat(
    chat_input: ChatRequest,
    user_id: str,
    pg_connection: psycopg.AsyncConnection,
) -> ChatResponse:
    """Non-streaming chat via Deep Agent runtime.

    Checkpointer manages conversation state — only the new message is passed.
    Messages are also saved to chat_message_history for the read API.
    """
    from .services.deep_agent_builder import (  # noqa: E501
        build_deep_agent,
        extract_agent_response,
        sync_user_files_after_invocation,
    )
    from .services.message_history_adapter import MessageHistoryAdapter

    if not chat_input.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    agent = await build_deep_agent(
        user_id=user_id,
        agent_name=chat_input.agent_name,
        session_id=chat_input.session_id,
        channel="web",
    )

    from .services.agent_callbacks import tool_call_logger

    user_msg = {"role": "user", "content": chat_input.message}
    config = {
        "configurable": {"thread_id": chat_input.session_id},
        "callbacks": [tool_call_logger],
    }

    result = await agent.ainvoke({"messages": [user_msg]}, config=config)
    response_text = extract_agent_response(result)

    # Fire-and-forget sync of user changes to durable storage
    asyncio.create_task(sync_user_files_after_invocation(user_id))

    # Persist to chat_message_history for the /api/chat-history/ read endpoint
    await MessageHistoryAdapter.save_messages(
        session_id=chat_input.session_id,
        messages=[user_msg, {"role": "assistant", "content": response_text}],
        pg_connection=pg_connection,
    )

    return ChatResponse(
        session_id=chat_input.session_id,
        response=response_text,
        error=None,
    )


async def _handle_chat_stream(
    chat_input: ChatRequest,
    user_id: str,
    pg_connection: psycopg.AsyncConnection,
):
    """SSE streaming chat via Deep Agent runtime.

    Checkpointer manages conversation state — only the new message is passed.
    Messages are also saved to chat_message_history for the read API.
    """
    from fastapi.responses import StreamingResponse

    from .services.deep_agent_builder import build_deep_agent, sync_user_files_after_invocation
    from .services.deep_agent_stream import deep_agent_stream_to_sse
    from .services.message_history_adapter import MessageHistoryAdapter

    if not chat_input.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    agent = await build_deep_agent(
        user_id=user_id,
        agent_name=chat_input.agent_name,
        session_id=chat_input.session_id,
        channel="web",
    )

    from .services.agent_callbacks import tool_call_logger

    user_msg = {"role": "user", "content": chat_input.message}
    config = {
        "configurable": {"thread_id": chat_input.session_id},
        "callbacks": [tool_call_logger],
    }

    # Save user message before streaming begins
    await MessageHistoryAdapter.save_messages(
        session_id=chat_input.session_id,
        messages=[user_msg],
        pg_connection=pg_connection,
    )

    async def _stream_and_persist():
        """Wrap the SSE stream to accumulate and persist the AI response."""
        accumulated_text = []
        async for sse_line in deep_agent_stream_to_sse(agent, {"messages": [user_msg]}, config=config):
            if sse_line.startswith("data: "):
                try:
                    payload = json.loads(sse_line[6:])
                    if payload.get("type") == "text_delta" and payload.get("text"):
                        accumulated_text.append(payload["text"])
                except (json.JSONDecodeError, KeyError):
                    pass
            yield sse_line

        # Persist the AI response after streaming completes
        if accumulated_text:
            ai_msg = {"role": "assistant", "content": "".join(accumulated_text)}
            await MessageHistoryAdapter.save_messages(
                session_id=chat_input.session_id,
                messages=[ai_msg],
                pg_connection=pg_connection,
            )

        # Fire-and-forget sync of user changes to durable storage
        asyncio.create_task(sync_user_files_after_invocation(user_id))

    return StreamingResponse(
        _stream_and_persist(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# --- API Endpoints for Prompt Customizations ---

@app.post("/api/agent/prompt_customizations/", response_model=PromptCustomization, tags=[PROMPT_CUSTOMIZATIONS_TAG])
async def create_prompt_customization(
    customization_data: PromptCustomizationCreate,
    user_id: str = Depends(get_current_user),
    db=Depends(get_user_scoped_client),
):
    """Create a new prompt customization."""
    prompt_service = get_prompt_customization_service()
    return await prompt_service.create_prompt_customization(
        customization_data=customization_data,
        user_id=user_id,
        supabase_client=db
    )

@app.get("/api/agent/prompt_customizations/{agent_name}", response_model=List[PromptCustomization], tags=[PROMPT_CUSTOMIZATIONS_TAG])  # noqa: E501
async def get_prompt_customizations_for_agent(
    agent_name: str,
    user_id: str = Depends(get_current_user),
    db=Depends(get_user_scoped_client),
):
    """Get prompt customizations for a specific agent."""
    prompt_service = get_prompt_customization_service()
    return await prompt_service.get_prompt_customizations_for_agent(
        agent_name=agent_name,
        user_id=user_id,
        supabase_client=db
    )

@app.put("/api/agent/prompt_customizations/{customization_id}", response_model=PromptCustomization, tags=[PROMPT_CUSTOMIZATIONS_TAG])  # noqa: E501
async def update_prompt_customization(
    customization_id: str,
    customization_data: PromptCustomizationCreate,
    user_id: str = Depends(get_current_user),
    db=Depends(get_user_scoped_client),
):
    """Update an existing prompt customization."""
    prompt_service = get_prompt_customization_service()
    return await prompt_service.update_prompt_customization(
        customization_id=customization_id,
        customization_data=customization_data,
        user_id=user_id,
        supabase_client=db
    )

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "clarity-chatserver"}

@app.get("/")
async def root():
    print("Root endpoint accessed.")
    return {"message": "Clarity Chat Server is running."}

# Example protected endpoint using Supabase for user tasks
# This is just an example, actual task management might be more complex
# and involve user authentication/authorization through JWT tokens passed from frontend
@app.get("/api/tasks")
async def get_tasks(request: Request, db=Depends(get_user_scoped_client)):
    print("Attempting to fetch tasks from Supabase.")
    try:
        # Example: Fetch tasks. In a real app, you'd filter by user_id from JWT.
        # For now, this fetches all tasks, assuming RLS is set up for direct access if needed,
        # or this endpoint is for admin/internal use.
        response = await db.table('tasks').select("*").execute()
        print(f"Supabase response: {response}")
        if response.data:
            return response.data
        else:
            # Handle cases where response.data might be None or empty, or an error occurred
            # Supabase client typically raises an exception for network/DB errors covered by the outer try-except
            # This handles cases where the query was successful but returned no data or unexpected structure
            if hasattr(response, 'error') and response.error:
                 print(f"Error fetching tasks: {response.error}")
                 raise HTTPException(status_code=500, detail=str(response.error.message if response.error.message else "Error fetching tasks"))  # noqa: E501
            return [] # Return empty list if no data and no specific error

    except HTTPException as e:
        # Re-raise HTTPExceptions directly
        raise e
    except Exception as e:
        print(f"An unexpected error occurred while fetching tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# To run this server (example using uvicorn):
# uvicorn chatServer.main:app --reload

# Placeholder for webhook endpoint from Supabase
@app.post("/api/supabase-webhook")
async def supabase_webhook(payload: SupabasePayload):
    print(f"Received Supabase webhook: Type={payload.type}, Table={payload.table}")
    # Process the webhook payload
    # Example: Invalidate a cache, notify clients via WebSockets, etc.
    if payload.type == "INSERT" and payload.table == "tasks":
        print(f"New task inserted: {payload.record}")
        # Potentially send a notification or update a real-time view

    # Add more specific handling based on type and table, e.g., using payload.webhook_schema

    return {"status": "received"}

# Example: If using the agent_loader directly (ensure paths are correct)
# This is highly conceptual and needs proper path management if used.
# from src.core.agent_loader import load_specific_agent, AgentType # Adjust import path

# @app.post("/api/agent/invoke")
# async def invoke_agent_endpoint(request_data: dict):
#     agent_name = request_data.get("agent_name", "assistant") # Default to assistant
#     user_input = request_data.get("user_input", "")
#     user_id = request_data.get("user_id", "default_user") # Get user_id if available

#     if not user_input:
#         raise HTTPException(status_code=400, detail="user_input is required")

#     try:
#         # Assuming load_specific_agent can take user_id for context/memory
#         agent_executor,_ = load_specific_agent(agent_name, AgentType.AUTONOMOUS, user_id=user_id)
#         # This is a simplified invocation. Real agents might need history, tools, etc.
#         response = await agent_executor.ainvoke({"input": user_input})
#         return {"response": response.get("output")}
#     except FileNotFoundError:
#         raise HTTPException(status_code=404, detail=f"Agent configuration for '{agent_name}' not found.")
#     except Exception as e:
#         logger.error(f"Error invoking agent '{agent_name}': {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Error invoking agent: {str(e)}")

# Define a protocol for what we expect from an agent executor
if __name__ == "__main__":
    import uvicorn  # noqa: E402

    from utils.logging_utils import get_logger as _init_logging  # noqa: E402
    # Logging configured via get_logger() — default DEBUG with noisy loggers quieted
    _init_logging("chatServer")
    print("Starting API server with Uvicorn for local development...")
    uvicorn.run(app, host="0.0.0.0", port=3001, access_log=False)
