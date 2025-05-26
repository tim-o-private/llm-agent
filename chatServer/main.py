import sys
import os
import logging # Added for log_level
from typing import Dict, Optional, Any, List, AsyncIterator # Added Optional and List here, NEW: AsyncIterator
from contextlib import asynccontextmanager # NEW IMPORT
import asyncio # NEW IMPORT
from datetime import datetime, timedelta, timezone # Added timezone

# Add parent directory to path for imports when running directly
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware


# Import models and protocols from extracted modules
try:
    # Try relative imports first (when imported as a module)
    from .models.chat import ChatRequest, ChatResponse
    from .models.prompt_customization import (
        PromptCustomizationBase,
        PromptCustomizationCreate,
        PromptCustomization,
    )
    from .models.webhook import SupabasePayload
    from .protocols.agent_executor import AgentExecutorProtocol
    from .config import (
        get_settings,
        SESSION_INSTANCE_TTL_SECONDS,
        SCHEDULED_TASK_INTERVAL_SECONDS,
        PROMPT_CUSTOMIZATIONS_TAG,
        CHAT_MESSAGE_HISTORY_TABLE_NAME,
        DEFAULT_LOG_LEVEL,
    )
    from .database import (
        DatabaseManager,
        get_db_connection,
        SupabaseManager,
        get_supabase_client,
    )
    from .dependencies import (
        get_current_user,
        get_jwt_from_request_context,
        get_agent_loader,
    )
except ImportError:
    # Fall back to absolute imports (when run directly)
    from chatServer.models.chat import ChatRequest, ChatResponse
    from chatServer.models.prompt_customization import (
        PromptCustomizationBase,
        PromptCustomizationCreate,
        PromptCustomization,
    )
    from chatServer.models.webhook import SupabasePayload
    from chatServer.protocols.agent_executor import AgentExecutorProtocol
    from chatServer.config import (
        get_settings,
        SESSION_INSTANCE_TTL_SECONDS,
        SCHEDULED_TASK_INTERVAL_SECONDS,
        PROMPT_CUSTOMIZATIONS_TAG,
        CHAT_MESSAGE_HISTORY_TABLE_NAME,
        DEFAULT_LOG_LEVEL,
    )
    from chatServer.database import (
        DatabaseManager,
        get_db_connection,
        SupabaseManager,
        get_supabase_client,
    )
    from chatServer.dependencies import (
        get_current_user,
        get_jwt_from_request_context,
        get_agent_loader,
    )

# Correctly import ConfigLoader
from utils.config_loader import ConfigLoader

# Import agent_loader
from core.agents.customizable_agent import CustomizableAgentExecutor # Added import

# For V2 Agent Memory System
from langchain_postgres import PostgresChatMessageHistory # PGEngine removed from here
import psycopg
from psycopg_pool import AsyncConnectionPool # NEW IMPORT

# NEW: Agent Executor Cache
from cachetools import TTLCache
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
        load_dotenv(dotenv_path, override=True)
    add_project_root_to_path_for_local_dev()
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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")  # Set this in your .env or Fly secrets

# --- START Moved Scheduled Task Definitions ---
async def deactivate_stale_chat_session_instances_task():
    """Periodically deactivates stale chat session instances."""
    try:
        from .database.connection import get_database_manager
    except ImportError:
        from chatServer.database.connection import get_database_manager
    
    while True:
        await asyncio.sleep(SCHEDULED_TASK_INTERVAL_SECONDS)
        logger.debug("Running task: deactivate_stale_chat_session_instances_task")
        
        db_manager = get_database_manager()
        if db_manager.pool is None:
            logger.warning("db_pool not available, skipping deactivation task cycle.")
            continue
        
        try:
            async with db_manager.pool.connection() as conn:
                async with conn.cursor() as cur:
                    threshold_time = datetime.now(timezone.utc) - timedelta(seconds=SESSION_INSTANCE_TTL_SECONDS)
                    await cur.execute(
                        """UPDATE chat_sessions 
                           SET is_active = false, updated_at = %s 
                           WHERE is_active = true AND updated_at < %s""",
                        (datetime.now(timezone.utc), threshold_time)
                    )
                    if cur.rowcount > 0:
                        logger.info(f"Deactivated {cur.rowcount} stale chat session instances.")
        except Exception as e:
            logger.error(f"Error in deactivate_stale_chat_session_instances_task: {e}", exc_info=True)

async def evict_inactive_executors_task():
    """Periodically evicts agent executors if no active session instances exist for them."""
    try:
        from .database.connection import get_database_manager
    except ImportError:
        from chatServer.database.connection import get_database_manager
    
    global AGENT_EXECUTOR_CACHE
    while True:
        await asyncio.sleep(SCHEDULED_TASK_INTERVAL_SECONDS + 30) # Stagger slightly from the other task
        logger.debug("Running task: evict_inactive_executors_task")
        
        db_manager = get_database_manager()
        if db_manager.pool is None or AGENT_EXECUTOR_CACHE is None:
            logger.warning("db_pool or AGENT_EXECUTOR_CACHE not available, skipping eviction task cycle.")
            continue

        keys_to_evict = []
        # Create a copy of keys to iterate over as cache might be modified
        current_cache_keys = list(AGENT_EXECUTOR_CACHE.keys())

        for user_id, agent_name in current_cache_keys:
            try:
                async with db_manager.pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """SELECT 1 FROM chat_sessions 
                               WHERE user_id = %s AND agent_name = %s AND is_active = true LIMIT 1""",
                            (user_id, agent_name)
                        )
                        active_session_exists = await cur.fetchone()
                        if not active_session_exists:
                            keys_to_evict.append((user_id, agent_name))
            except Exception as e:
                logger.error(f"Error checking active sessions for ({user_id}, {agent_name}): {e}", exc_info=True)
        
        for key in keys_to_evict:
            if key in AGENT_EXECUTOR_CACHE:
                del AGENT_EXECUTOR_CACHE[key]
                logger.info(f"Evicted agent executor for {key} due to no active sessions.")

# --- END Moved Scheduled Task Definitions ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from .database.connection import get_database_manager
        from .database.supabase_client import get_supabase_manager
    except ImportError:
        from chatServer.database.connection import get_database_manager
        from chatServer.database.supabase_client import get_supabase_manager
    
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

    # Start background tasks
    app.state.deactivate_task = asyncio.create_task(deactivate_stale_chat_session_instances_task())
    app.state.evict_task = asyncio.create_task(evict_inactive_executors_task())
    logger.info("Background tasks for session and cache cleanup started.")

    yield # Application runs here

    logger.info("Application shutdown: Cleaning up resources...")
    if hasattr(app.state, 'deactivate_task') and app.state.deactivate_task:
        app.state.deactivate_task.cancel()
        logger.info("Deactivate stale sessions task cancelling...")
        try:
            await app.state.deactivate_task
        except asyncio.CancelledError:
            logger.info("Deactivate stale sessions task successfully cancelled.")
    if hasattr(app.state, 'evict_task') and app.state.evict_task:
        app.state.evict_task.cancel()
        logger.info("Evict inactive executors task cancelling...")
        try:
            await app.state.evict_task
        except asyncio.CancelledError:
            logger.info("Evict inactive executors task successfully cancelled.")

    await db_manager.close()

# Re-assign app with the new lifespan
app = FastAPI(lifespan=lifespan)

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
    pg_connection: psycopg.AsyncConnection = Depends(get_db_connection), # NEW: Use pooled connection
    agent_loader_module = Depends(get_agent_loader), # NEW: Inject agent loader
    # db_client: AsyncClient = Depends(get_supabase_client) # Keep if other parts need supabase-py client
):
    logger.debug(f"Received chat request for agent {chat_input.agent_name} with session_id: {chat_input.session_id} from user {user_id}")

    if not chat_input.session_id:
        # This case should ideally not be reached if client ensures session_id is sent
        logger.error("session_id missing from chat_input")
        raise HTTPException(status_code=400, detail="session_id is required")

    session_id_for_history = chat_input.session_id # This is the activeChatId from client
    agent_name = chat_input.agent_name 

    try:
        # Initialize PostgresChatMessageHistory using the connection from the pool
        chat_memory = PostgresChatMessageHistory(
            CHAT_MESSAGE_HISTORY_TABLE_NAME,
            session_id_for_history, # Use the specific session_id for history
            async_connection=pg_connection # USE THE CONNECTION FROM THE POOL
        )

        # Fix for ConversationBufferWindowMemory async implementation
        from langchain.memory import ConversationBufferWindowMemory
        from typing import Dict, Any, List
        from langchain_core.messages import BaseMessage

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

        # Wrap the chat_memory in ConversationBufferWindowMemory
        agent_short_term_memory = AsyncConversationBufferWindowMemory(
            chat_memory=chat_memory,
            k=50, # Keep last 50 messages (user + AI). Was MAX_CACHE_HISTORY_LENGTH. Can be configured.
            return_messages=True,
            memory_key="chat_history", # Must match the input variable in the agent\'s prompt
            input_key="input" # Must match the key for the user\'s input message
        )

        try:
            # Get JWT token for agent_loader if needed by any tools that require user context via API calls
            auth_token_provider = lambda: get_jwt_from_request_context(request)

            # NEW: Check cache for existing agent executor
            cache_key = (user_id, agent_name) # MODIFIED: Cache key is now (user_id, agent_name)
            if cache_key in AGENT_EXECUTOR_CACHE:
                agent_executor = AGENT_EXECUTOR_CACHE[cache_key]
                logger.debug(f"Cache HIT for agent executor: key={cache_key}")
            else:
                logger.debug(f"Cache MISS for agent executor: key={cache_key}. Loading new executor.")
                agent_executor = agent_loader_module.load_agent_executor(
                    user_id=user_id,
                    agent_name=agent_name,
                    session_id=session_id_for_history,
                    log_level=DEFAULT_LOG_LEVEL
                )
                AGENT_EXECUTOR_CACHE[cache_key] = agent_executor # Store in cache
            
            # Check if agent_executor implements the required interface
            if not hasattr(agent_executor, 'ainvoke') or not hasattr(agent_executor, 'memory'):
                logger.error(f"Loaded agent does not implement required interface. Type: {type(agent_executor)}")
                raise HTTPException(status_code=500, detail="Agent loading failed to produce a compatible executor.")

            # CRITICAL: Ensure the cached/newly loaded executor uses the correct memory for THIS session_id_for_history
            agent_executor.memory = agent_short_term_memory

        except Exception as e:
            logger.error(f"Error loading or preparing agent executor for agent {agent_name}: {e}", exc_info=True) # MODIFIED: agent_name
            raise HTTPException(status_code=500, detail=f"Could not load agent: {e}")

        try:
            response_data = await agent_executor.ainvoke({"input": chat_input.message})
            ai_response_content = response_data.get("output", "No output from agent.")

            # Placeholder for tool_name and tool_input if we want to extract them
            # from response_data['intermediate_steps'] in the future.
            invoked_tool_name: Optional[str] = None
            invoked_tool_input: Optional[Dict[str, Any]] = None
            
            # Example of how one might extract the last tool call, if needed by client
            # if "intermediate_steps" in response_data and response_data["intermediate_steps"]:
            #     last_step = response_data["intermediate_steps"][-1]
            #     if isinstance(last_step, tuple) and len(last_step) > 0:
            #         action, observation = last_step
            #         if hasattr(action, 'tool'): invoked_tool_name = action.tool
            #         if hasattr(action, 'tool_input'): invoked_tool_input = action.tool_input

            chat_response_payload = ChatResponse(
                session_id=session_id_for_history, 
                response=ai_response_content,
                tool_name=invoked_tool_name, # Will be None for now
                tool_input=invoked_tool_input, # Will be None for now
                error=None
            )
            logger.info(f"Successfully processed chat. Returning to client: {chat_response_payload.model_dump_json(indent=2)}")
            return chat_response_payload
        except Exception as e:
            logger.error(f"Error during agent execution for session {session_id_for_history}: {e}", exc_info=True)
            # Construct and log the error response
            error_response_payload = ChatResponse(
                session_id=session_id_for_history,
                response="An error occurred processing your request.", 
                error=str(e)
            )
            logger.info(f"Error during agent execution. Returning to client: {error_response_payload.model_dump_json(indent=2)}")
            return error_response_payload
    except psycopg.Error as pe:
        logger.error(f"Database error (psycopg.Error) during chat_memory setup for session {session_id_for_history}: {pe}", exc_info=True)
        # Construct and log the error response
        db_error_payload = ChatResponse(
            session_id=session_id_for_history,
            response="A database error occurred during chat setup.",
            error=f"Database error: {str(pe)}"
        )
        logger.info(f"Database error. Returning to client: {db_error_payload.model_dump_json(indent=2)}")
        # Re-raise as HTTPException because this is a server infrastructure problem
        raise HTTPException(status_code=503, detail=f"Database error during chat setup: {pe}")
    except Exception as e:
        logger.error(f"Failed to process chat request before agent execution for session {session_id_for_history}: {e}", exc_info=True)
        # Construct and log the error response
        setup_error_payload = ChatResponse(
            session_id=session_id_for_history,
            response="An error occurred setting up the chat environment.",
            error=f"Setup error: {str(e)}"
        )
        logger.info(f"Setup error. Returning to client: {setup_error_payload.model_dump_json(indent=2)}")
        if isinstance(e, HTTPException): 
            raise
        raise HTTPException(status_code=500, detail=f"Could not process chat request: {e}")

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
    try:
        response = await db.table("user_agent_prompt_customizations").insert({
            "user_id": user_id,
            "agent_name": customization_data.agent_name,
            "customization_type": customization_data.customization_type,
            "content": customization_data.content,
            "is_active": customization_data.is_active,
            "priority": customization_data.priority
        }).execute()
        if response.data:
            return response.data[0]
        else:
            logging.error(f"Failed to create prompt customization: {response.error.message if response.error else 'Unknown error'}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create prompt customization")
    except Exception as e:
        logging.error(f"Error creating prompt customization: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/api/agent/prompt_customizations/{agent_name}", response_model=List[PromptCustomization], tags=[PROMPT_CUSTOMIZATIONS_TAG])
async def get_prompt_customizations_for_agent(
    agent_name: str,
    user_id: str = Depends(get_current_user),
    db = Depends(get_supabase_client) # This still uses supabase-py client
):
    try:
        response = await db.table("user_agent_prompt_customizations") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("agent_name", agent_name) \
            .eq("is_active", True) \
            .order("priority", desc=False) \
            .execute()
        if response.data:
            return response.data
        return []
    except Exception as e:
        logging.error(f"Error fetching prompt customizations for agent {agent_name}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.put("/api/agent/prompt_customizations/{customization_id}", response_model=PromptCustomization, tags=[PROMPT_CUSTOMIZATIONS_TAG])
async def update_prompt_customization(
    customization_id: str,
    customization_data: PromptCustomizationCreate, # Re-use create model, user_id is fixed by RLS
    user_id: str = Depends(get_current_user), # Ensures user owns the record via RLS
    db = Depends(get_supabase_client) # This still uses supabase-py client
):
    try:
        # RLS will ensure the user can only update their own records.
        # We select user_id in the update to ensure it's part of the WHERE clause enforced by RLS implicitly.
        update_payload = customization_data.dict()
        update_payload["updated_at"] = "now()" # Let database update timestamp

        response = await db.table("user_agent_prompt_customizations") \
            .update(update_payload) \
            .eq("id", customization_id) \
            .eq("user_id", user_id) \
            .execute()
        
        if response.data:
            return response.data[0]
        elif response.error and response.error.code == 'PGRST116': # PGRST116: Row not found
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt customization not found or access denied")
        else:
            logging.error(f"Failed to update prompt customization {customization_id}: {response.error.message if response.error else 'Unknown error or no rows updated'}")
            # If no data and no specific error, it might mean the record wasn't found or RLS prevented update without erroring differently.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt customization not found, access denied, or no changes made.")
    except HTTPException: # Re-raise HTTP exceptions directly
        raise
    except Exception as e:
        logging.error(f"Error updating prompt customization {customization_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

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
                 raise HTTPException(status_code=500, detail=str(response.error.message if response.error.message else "Error fetching tasks"))
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