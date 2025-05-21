import sys
import os
import logging # Added for log_level
from typing import Dict, Optional, Any, List # Added Optional and List here

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Request, status
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from supabase import acreate_client, AsyncClient

# NEW: Import for psycopg connection pool
import psycopg
from psycopg_pool import AsyncConnectionPool

# Correctly import ConfigLoader
from utils.config_loader import ConfigLoader

# Import agent_loader
from core import agent_loader
from core.agents.customizable_agent import CustomizableAgentExecutor # Added import

# For V2 Agent Memory System (New Approach)
from langchain.memory import ConversationBufferWindowMemory
from langchain_postgres import PostgresChatMessageHistory, PGEngine # NEW IMPORTS

# NEW: Import the custom async memory class
from core.memory.async_memory import AsyncPostgresBufferedWindowMemory

# --- START Inserted Environment & Path Setup ---
def add_project_root_to_path_for_local_dev():
    try:
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root_dir = os.path.dirname(current_script_dir)
        llm_agent_src_path_env = os.getenv("LLM_AGENT_SRC_PATH", "src")
        full_src_path = os.path.join(project_root_dir, llm_agent_src_path_env)
        if os.path.isdir(full_src_path):
            if full_src_path not in sys.path:
                sys.path.insert(0, full_src_path)
            if project_root_dir not in sys.path:
                sys.path.insert(0, project_root_dir)
    except Exception as e:
        print(f"Error setting up sys.path for local dev: {e}", file=sys.stderr)

if os.getenv("RUNNING_IN_DOCKER") == "true":
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
DEFAULT_LOG_LEVEL = logging.INFO # Or use a level from your config

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://clarity-webapp.fly.dev",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    agent_id: str
    message: str
    session_id: str # Added: session_id is now required

class ChatResponse(BaseModel):
    session_id: str
    response: str
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")  # Set this in your .env or Fly secrets

def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    print("Authorization header:", auth_header)
    print("JWT secret (first 8 chars):", SUPABASE_JWT_SECRET[:8])  # For debug only, don't log full secret
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
        print("Decoded payload:", payload)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found in token")
        return user_id
    except JWTError as e:
        print("JWTError:", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# --- Auth Token Provider for Agent Loader ---
# This callable will be created within the request context to capture the token.
async def get_jwt_from_request_context(request_for_token: Request) -> Optional[str]:
    auth_header = request_for_token.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return None

# Global Supabase client instance
# Initialize as None, will be created on startup
supabase_client: AsyncClient | None = None

# NEW: Global PGEngine for langchain-postgres (SQLAlchemy based)
pg_engine_instance: Optional[PGEngine] = None

# NEW: Global psycopg AsyncConnectionPool
psycopg_async_pool: Optional[AsyncConnectionPool] = None

@app.on_event("startup")
async def startup_event():
    global supabase_client, pg_engine_instance, psycopg_async_pool # Added psycopg_async_pool
    supabase_url_env = os.getenv("VITE_SUPABASE_URL")
    supabase_key_env = os.getenv("SUPABASE_SERVICE_KEY")

    # Initialize supabase-py AsyncClient (if still needed for other parts like LTM, user auth, etc.)
    if supabase_url_env and supabase_key_env:
        try:
            print(f"Attempting to initialize Supabase async client with URL: {supabase_url_env} and Key: {'[REDACTED]' if supabase_key_env else None}")
            supabase_client_instance_val = await acreate_client(supabase_url_env, supabase_key_env) # Renamed var
            
            if isinstance(supabase_client_instance_val, AsyncClient):
                supabase_client = supabase_client_instance_val
                print("Supabase AsyncClient initialized successfully via acreate_client.")
            else:
                print(f"Supabase client initialized via acreate_client IS NOT AN ASYNCCLIENT. Type: {type(supabase_client_instance_val)}")
                supabase_client = None 
        except Exception as e:
            print(f"Error initializing Supabase async client (supabase-py): {e}", exc_info=True)
            supabase_client = None
    else:
        print("Supabase async client (supabase-py) not initialized due to missing URL or Key.")

    # NEW: Initialize PGEngine for langchain-postgres
    db_user = os.getenv("SUPABASE_DB_USER")
    db_password = os.getenv("SUPABASE_DB_PASSWORD")
    # Ensure this is the DB host, not the API host. Example: aws-0-us-east-1.pooler.supabase.com
    db_host_env = os.getenv("SUPABASE_DB_HOST") # Renamed to avoid conflict
    db_name_env = os.getenv("SUPABASE_DB_NAME", "postgres") # Renamed to avoid conflict
    db_port_env = os.getenv("SUPABASE_DB_PORT", "5432") # Renamed to avoid conflict

    if all([db_user, db_password, db_host_env, db_name_env, db_port_env]):
        # Using +asyncpg for asynchronous operations with langchain-postgres
        connection_string = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host_env}:{db_port_env}/{db_name_env}"
        logger.info(f"Attempting to initialize PGEngine with connection string: postgresql+asyncpg://{db_user}:[REDACTED]@{db_host_env}:{db_port_env}/{db_name_env}")
        try:
            # Use PGEngine.from_connection_string for sync initialization, async driver handles async ops
            pg_engine_instance = PGEngine.from_connection_string(url=connection_string)
            logger.info("PGEngine for langchain-postgres initialized successfully.")
            
            # Table creation for PostgresChatMessageHistory:
            # It's recommended to do this manually via SQL editor or a separate sync script
            # to avoid complexities with sync/async in app startup.
            # Example table name: "chat_message_history"
            # Schema typically: id SERIAL PRIMARY KEY, session_id TEXT NOT NULL, message JSONB NOT NULL, created_at TIMESTAMPTZ DEFAULT now()
            # Plus an index on session_id.
            # If PostgresChatMessageHistory.create_tables is used, it needs a sync connection.
            logger.info("PGEngine initialized. Ensure 'chat_message_history' table exists or is created separately.")

        except Exception as e:
            logger.error(f"Error initializing PGEngine for langchain-postgres: {e}", exc_info=True)
            pg_engine_instance = None
    else:
        missing_vars = [var for var, val in [("SUPABASE_DB_USER", db_user), ("SUPABASE_DB_PASSWORD", db_password), 
                                             ("SUPABASE_DB_HOST", db_host_env), ("SUPABASE_DB_NAME", db_name_env),
                                             ("SUPABASE_DB_PORT", db_port_env)] if not val]
        logger.error(f"PGEngine for langchain-postgres not initialized due to missing DB connection variables: {', '.join(missing_vars)}")
        pg_engine_instance = None

    # NEW: Initialize psycopg AsyncConnectionPool
    if all([db_user, db_password, db_host_env, db_name_env, db_port_env]):
        # Add sslmode=require for Supabase
        psycopg_conn_str = f"postgresql://{db_user}:{db_password}@{db_host_env}:{db_port_env}/{db_name_env}?sslmode=require"
        logger.info(f"Attempting to initialize psycopg AsyncConnectionPool with connection string: postgresql://{db_user}:[REDACTED]@{db_host_env}:{db_port_env}/{db_name_env}?sslmode=require")
        try:
            psycopg_async_pool = AsyncConnectionPool(conninfo=psycopg_conn_str, open=False) # open=False: pool doesn't open connections immediately
            await psycopg_async_pool.open()
            # NEW: Test the pool by acquiring a connection and running a simple query
            logger.info("Attempting to verify psycopg AsyncConnectionPool connectivity...")
            async with psycopg_async_pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    res = await cur.fetchone()
                    if res and res[0] == 1:
                        logger.info("psycopg AsyncConnectionPool connected and verified successfully.")
                    else:
                        logger.error("psycopg AsyncConnectionPool verification query failed or returned unexpected result.")
        except Exception as e:
            logger.error(f"Error initializing or verifying psycopg AsyncConnectionPool: {e}", exc_info=True) # Modified log message
            psycopg_async_pool = None
    else:
        logger.error(f"psycopg AsyncConnectionPool not initialized due to missing DB connection variables: {', '.join(missing_vars)}")
        psycopg_async_pool = None

@app.on_event("shutdown")
async def shutdown_event():
    global psycopg_async_pool
    if psycopg_async_pool:
        logger.info("Closing psycopg AsyncConnectionPool...")
        await psycopg_async_pool.close()
        logger.info("psycopg AsyncConnectionPool closed.")

# Dependency to get Supabase client (supabase-py AsyncClient)
async def get_supabase_client() -> AsyncClient:
    if supabase_client is None:
        print("Supabase client not available during request.") # Changed log message
        raise HTTPException(status_code=503, detail="Supabase client not available. Check server startup logs.")
    return supabase_client

# NEW: Dependency to get PGEngine
async def get_pg_engine() -> PGEngine:
    if pg_engine_instance is None:
        logger.error("PGEngine (langchain-postgres) not available during request. Check server startup logs.")
        raise HTTPException(status_code=503, detail="Postgres engine for chat history not available.")
    return pg_engine_instance

# NEW: Dependency to get a psycopg AsyncConnection
async def get_psycopg_aconnection() -> psycopg.AsyncConnection:
    if psycopg_async_pool is None:
        logger.error("psycopg AsyncConnectionPool not available. Check server startup logs.")
        raise HTTPException(status_code=503, detail="Database connection pool not available.")
    try:
        # The pool will manage when to actually establish the connection if not already open.
        # Using "async with" ensures the connection is returned to the pool.
        async with psycopg_async_pool.connection() as aconn:
            yield aconn
    except Exception as e:
        logger.error(f"Error getting a psycopg connection from pool: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Could not get database connection from pool.")


# Initialize PromptManagerService
# prompt_manager_service = PromptManagerService() # Removed problematic instantiation

# V2 Agent Memory: Server-side short-term session cache -- REMOVED
# server_session_cache: Dict[str, List[Dict[str, Any]]] = {} -- REMOVED
# MAX_CACHE_HISTORY_LENGTH = 50 -- REMOVED

# class ChatInput(BaseModel): # Definition moved up
# ... existing code ...

# Helper to serialize BaseMessage to dict for server_session_cache -- REMOVED
# def serialize_message_for_cache(message: BaseMessage) -> Dict[str, Any]: -- REMOVED
# ... (implementation removed) ...

# Helper to deserialize dict from cache to BaseMessage -- REMOVED
# def deserialize_message_from_cache(msg_dict: Dict[str, Any]) -> BaseMessage: -- REMOVED
# ... (implementation removed) ...

# --- Logger setup ---
# Ensure logger is available if not already globally configured
# This can be more sophisticated, e.g., using utils.logging_utils.get_logger
logger = logging.getLogger(__name__)
# Example: Set a basic config if no handlers are present
if not logger.handlers:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
# --- End Logger setup ---

CHAT_MESSAGE_HISTORY_TABLE_NAME = "chat_message_history" # Define globally or get from config

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    chat_input: ChatRequest, 
    request: Request, 
    user_id: str = Depends(get_current_user),
    psycopg_conn: psycopg.AsyncConnection = Depends(get_psycopg_aconnection), # NEW: Use psycopg connection
    # db_client: AsyncClient = Depends(get_supabase_client) # Keep if other parts need supabase-py client
):
    logger.info(f"Received chat request for agent {chat_input.agent_id} with session_id: {chat_input.session_id} from user {user_id}")

    if not chat_input.session_id:
        # This case should ideally not be reached if client ensures session_id is sent
        logger.error("session_id missing from chat_input")
        raise HTTPException(status_code=400, detail="session_id is required")

    session_id = chat_input.session_id

    # Initialize PostgresChatMessageHistory for the current session
    try:
        chat_memory = PostgresChatMessageHistory(
            CHAT_MESSAGE_HISTORY_TABLE_NAME, # Positional: table_name
            session_id,                      # Positional: session_id
            async_connection=psycopg_conn    # Keyword: Pass the raw psycopg async connection
        )
        # The messages will be loaded by AsyncPostgresBufferedWindowMemory automatically
        # await chat_memory.aadd_user_message(chat_input.message) # No, agent executor adds this
    except Exception as e:
        logger.error(f"Failed to initialize PostgresChatMessageHistory for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not initialize chat history: {e}")

    # Wrap the chat_memory in ConversationBufferWindowMemory
    # k is the number of past interactions (user + AI message) to keep in the window
    # We can make k configurable if needed
    # return_messages=True is important for the agent to get BaseMessage objects
    agent_short_term_memory = AsyncPostgresBufferedWindowMemory( # CHANGED to use the new async class
        chat_memory=chat_memory,
        k=50, # Keep last 50 messages (user + AI). Was MAX_CACHE_HISTORY_LENGTH. Can be configured.
        return_messages=True,
        memory_key="chat_history", # Must match the input variable in the agent's prompt
        input_key="input" # Must match the key for the user's input message
    )

    try:
        # Get JWT token for agent_loader if needed by any tools that require user context via API calls
        # This auth_token_provider now correctly uses the `request` from the endpoint context.
        auth_token_provider = lambda: get_jwt_from_request_context(request)

        agent_executor = agent_loader.load_agent_executor(
            user_id=user_id,
            agent_name=chat_input.agent_id,
            session_id=session_id, 
            config_loader=GLOBAL_CONFIG_LOADER,
            # auth_token_provider=auth_token_provider, # Not currently accepted by load_agent_executor
            # Pass the Supabase client if tools require it for direct DB ops not via API
            # supabase_client=db_client # If any tool directly uses the Python Supabase client for this user
        )
        
        # Ensure the loaded agent_executor is of the expected type and set its memory
        if not isinstance(agent_executor, CustomizableAgentExecutor):
            logger.error(f"Loaded agent is not a CustomizableAgentExecutor. Type: {type(agent_executor)}")
            raise HTTPException(status_code=500, detail="Agent loading failed to produce a compatible executor.")

        # Set the memory on the loaded agent executor
        agent_executor.memory = agent_short_term_memory

    except Exception as e:
        logger.error(f"Error loading agent executor for agent {chat_input.agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not load agent: {e}")

    try:
        # Include chat_history for the agent memory. Agent will get it from memory object.
        # The input to agent.ainvoke should match the agent's expected input keys.
        # Typically, this includes an "input" key for the user's message and any other keys
        # expected by the agent's prompt or memory system (e.g., "chat_history").
        # The ConversationBufferWindowMemory (with memory_key="chat_history" and input_key="input")
        # handles chat_history injection automatically when `agent_executor.ainvoke` is called
        # with the user's input under the key specified by `input_key` (here, "input").
        # For AsyncPostgresBufferedWindowMemory, aload_memory_variables will handle this.

        response_data = await agent_executor.ainvoke({"input": chat_input.message})
        ai_response_content = response_data.get("output", "No output from agent.")

        # Response should already be in the agent_short_term_memory (and thus PostgresChatMessageHistory)
        # because ConversationBufferWindowMemory automatically saves history.

        # CustomizableAgentExecutor is expected to return a dict that might include tool usage info.
        # Extract tool_name and tool_input if present in the response_data
        tool_name = response_data.get("tool_name")
        tool_input = response_data.get("tool_input")

        return ChatResponse(
            session_id=session_id, # Return the session_id used
            response=ai_response_content,
            tool_name=tool_name,
            tool_input=tool_input
        )

    except Exception as e:
        logger.error(f"Error during agent execution for session {session_id}: {e}", exc_info=True)
        # Optionally, save the error to chat history as an AIMessage or SystemMessage
        # await agent_short_term_memory.chat_memory.aadd_message(AIMessage(content=f"Error: {e}"))
        return ChatResponse(
            session_id=session_id,
            response="An error occurred processing your request.", # Generic error to client
            error=str(e) # Detailed error for logging or potential client display if desired
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


# --- Pydantic Models for Prompt Customizations ---
class PromptCustomizationBase(BaseModel):
    agent_name: str
    customization_type: str = 'instruction_set'
    content: Dict[str, Any] # JSONB content
    is_active: bool = True
    priority: int = 0

class PromptCustomizationCreate(PromptCustomizationBase):
    pass

class PromptCustomization(PromptCustomizationBase):
    id: str # UUID as string
    user_id: str # UUID as string
    created_at: Any # datetime, will be serialized to string
    updated_at: Any # datetime

    class Config:
        orm_mode = True # For Pydantic V1, or from_attributes = True for V2

# --- API Endpoints for Prompt Customizations ---
PROMPT_CUSTOMIZATIONS_TAG = "Prompt Customizations"

@app.post("/api/agent/prompt_customizations/", response_model=PromptCustomization, tags=[PROMPT_CUSTOMIZATIONS_TAG])
async def create_prompt_customization(
    customization_data: PromptCustomizationCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncClient = Depends(get_supabase_client) # This still uses supabase-py client
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
    db: AsyncClient = Depends(get_supabase_client) # This still uses supabase-py client
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
    db: AsyncClient = Depends(get_supabase_client) # This still uses supabase-py client
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
async def get_tasks(request: Request, db: AsyncClient = Depends(get_supabase_client)): # This still uses supabase-py client
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
class SupabasePayload(BaseModel):
    type: str
    table: str
    record: Optional[dict] = None
    old_record: Optional[dict] = None
    webhook_schema: Optional[str] = None # Renamed from schema to avoid conflict

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

if __name__ == "__main__":
    import uvicorn
    # Ensure logging is configured to see messages from the application
    logging.basicConfig(level=logging.DEBUG) 
    print("Starting API server with Uvicorn for local development...")
    uvicorn.run(app, host="0.0.0.0", port=3001) 