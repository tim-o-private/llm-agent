import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import List

# Correctly import ConfigLoader
# For V2 Agent Memory System
import psycopg

# NEW: Agent Executor Cache
from cachetools import TTLCache
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

# Import agent_loader
from core.agents.customizable_agent import CustomizableAgentExecutor  # Added import
from utils.config_loader import ConfigLoader

from .config.constants import PROMPT_CUSTOMIZATIONS_TAG
from .config.settings import get_settings
from .database.connection import get_db_connection
from .database.supabase_client import get_supabase_client
from .dependencies.agent_loader import get_agent_loader
from .dependencies.auth import get_current_user
from .models.chat import ChatRequest, ChatResponse
from .models.prompt_customization import PromptCustomization, PromptCustomizationCreate
from .models.webhook import SupabasePayload
from .routers.actions import router as actions_router
from .routers.chat_history_router import router as chat_history_router
from .routers.email_agent_router import router as email_agent_router
from .routers.external_api_router import router as external_api_router
from .routers.notifications_router import router as notifications_router
from .routers.oauth_router import router as oauth_router
from .routers.telegram_router import router as telegram_router
from .services.chat import get_chat_service
from .services.prompt_customization import get_prompt_customization_service

# Cache for (user_id, agent_name) -> CustomizableAgentExecutor
AGENT_EXECUTOR_CACHE: TTLCache[tuple[str, str], CustomizableAgentExecutor] = TTLCache(maxsize=100, ttl=900)

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
    from .services.agent_config_cache_service import initialize_agent_config_cache, shutdown_agent_config_cache
    from .services.background_tasks import get_background_task_service
    from .services.tool_cache_service import initialize_tool_cache, shutdown_tool_cache
    from .services.user_instructions_cache_service import (
        initialize_user_instructions_cache,
        shutdown_user_instructions_cache,
    )

    global AGENT_EXECUTOR_CACHE
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

    # Initialize cache services
    try:
        await initialize_tool_cache()
        logger.info("Tool cache service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize tool cache service: {e}", exc_info=True)

    try:
        await initialize_agent_config_cache()
        logger.info("Agent config cache service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent config cache service: {e}", exc_info=True)

    try:
        await initialize_user_instructions_cache()
        logger.info("User instructions cache service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize user instructions cache service: {e}", exc_info=True)

    # Initialize and start background tasks
    background_service = get_background_task_service()
    background_service.set_agent_executor_cache(AGENT_EXECUTOR_CACHE)
    background_service.start_background_tasks()

    # Initialize Telegram bot (optional — only if TELEGRAM_BOT_TOKEN is set)
    telegram_bot = None
    if settings.telegram_bot_token:
        from .channels.telegram_bot import initialize_telegram_bot

        telegram_bot = initialize_telegram_bot(settings.telegram_bot_token)
        # Give the bot access to the database for channel lookups
        try:
            telegram_bot.set_db_client(supabase_manager.get_client())
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

    # Stop cache services
    try:
        await shutdown_user_instructions_cache()
        logger.info("User instructions cache service stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop user instructions cache service: {e}", exc_info=True)

    try:
        await shutdown_agent_config_cache()
        logger.info("Agent config cache service stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop agent config cache service: {e}", exc_info=True)

    try:
        await shutdown_tool_cache()
        logger.info("Tool cache service stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop tool cache service: {e}", exc_info=True)

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
app.include_router(telegram_router)

# --- Logger setup ---
# Ensure logger is available if not already globally configured
# This can be more sophisticated, e.g., using utils.logging_utils.get_logger
from utils.logging_utils import get_logger

logger = get_logger(__name__)

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    chat_input: ChatRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
    pg_connection: psycopg.AsyncConnection = Depends(get_db_connection),
    agent_loader_module = Depends(get_agent_loader),
):
    """Chat endpoint that processes user messages through agents."""
    chat_service = get_chat_service(AGENT_EXECUTOR_CACHE)
    return await chat_service.process_chat(
        chat_input=chat_input,
        user_id=user_id,
        pg_connection=pg_connection,
        agent_loader_module=agent_loader_module,
        request=request
    )

# V2 Agent Memory: API endpoint for batch archival of messages -- REMOVED (or to be re-evaluated)
# This was for client-side batching. With server-side per-turn history saving via PostgresChatMessageHistory,
# this specific endpoint's role might change or become redundant if the new history table
# serves as the complete, viewable chat log.
# For now, commenting out:
# class ArchiveMessagesPayload(BaseModel):
# ... (rest of the old archive endpoint code commented out or removed) ...

# Placeholder for PromptManagerService if not fully defined elsewhere for this snippet
# class PromptManagerService:
# ... existing code ...


# --- API Endpoints for Prompt Customizations ---

@app.post("/api/agent/prompt_customizations/", response_model=PromptCustomization, tags=[PROMPT_CUSTOMIZATIONS_TAG])
async def create_prompt_customization(
    customization_data: PromptCustomizationCreate,
    user_id: str = Depends(get_current_user),
    db = Depends(get_supabase_client) # This still uses supabase-py client
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
    db = Depends(get_supabase_client) # This still uses supabase-py client
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
    customization_data: PromptCustomizationCreate, # Re-use create model, user_id is fixed by RLS
    user_id: str = Depends(get_current_user), # Ensures user owns the record via RLS
    db = Depends(get_supabase_client) # This still uses supabase-py client
):
    """Update an existing prompt customization."""
    prompt_service = get_prompt_customization_service()
    return await prompt_service.update_prompt_customization(
        customization_id=customization_id,
        customization_data=customization_data,
        user_id=user_id,
        supabase_client=db
    )

@app.get("/")
async def root():
    print("Root endpoint accessed.")
    return {"message": "Clarity Chat Server is running."}

# Example protected endpoint using Supabase for user tasks
# This is just an example, actual task management might be more complex
# and involve user authentication/authorization through JWT tokens passed from frontend
@app.get("/api/tasks")
async def get_tasks(request: Request, db = Depends(get_supabase_client)): # This still uses supabase-py client
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
    import uvicorn
    # Ensure logging is configured to see messages from the application
    logging.basicConfig(level=logging.DEBUG)
    print("Starting API server with Uvicorn for local development...")
    uvicorn.run(app, host="0.0.0.0", port=3001)
