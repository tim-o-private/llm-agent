import sys
import os
import logging # Added for log_level
from typing import Dict, Tuple, Optional, Any, List # Added Optional and List here

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Request, status
from pydantic import BaseModel
# from typing import Any # No longer explicitly needed here with more specific types
# from langchain.memory import ConversationBufferMemory
from langchain_core.memory import BaseMemory # Ensure BaseMemory is imported
from langchain.agents import AgentExecutor # Added for type hinting
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from supabase import acreate_client, AsyncClient, create_client

# Correctly import ConfigLoader
from utils.config_loader import ConfigLoader

# Import agent_loader
from core import agent_loader

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
ACTIVE_AGENTS: Dict[Tuple[str, str], AgentExecutor] = {}
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

class ChatResponse(BaseModel):
    reply: str

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

@app.on_event("startup")
async def startup_event():
    global supabase_client
    supabase_url = os.getenv("VITE_SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if supabase_url and supabase_key:
        try:
            print(f"Attempting to initialize Supabase async client with URL: {supabase_url} and Key: {'[REDACTED]' if supabase_key else None}")
            # Use acreate_client and await it
            supabase_client_instance = await acreate_client(supabase_url, supabase_key)
            
            if isinstance(supabase_client_instance, AsyncClient):
                supabase_client = supabase_client_instance
                print("Supabase AsyncClient initialized successfully via acreate_client.")
            else:
                # This case should ideally not happen if acreate_client is correctly typed and works
                print(f"Supabase client initialized via acreate_client IS NOT AN ASYNCCLIENT. Type: {type(supabase_client_instance)}")
                supabase_client = None # Explicitly set to None
        except ImportError:
            print("Failed to import acreate_client. Falling back to create_client for now (might result in SyncClient).")
            # Fallback or further error handling if acreate_client doesn't exist
            try:
                supabase_client_instance = create_client(supabase_url, supabase_key)
                if isinstance(supabase_client_instance, AsyncClient):
                    supabase_client = supabase_client_instance
                    print("Supabase AsyncClient initialized successfully via create_client (fallback).")
                else:
                    print(f"Supabase client (fallback) IS NOT AN ASYNCCLIENT. Type: {type(supabase_client_instance)}")
                    supabase_client = None
            except Exception as fallback_e:
                print(f"Error initializing Supabase client via fallback create_client: {fallback_e}")
                import traceback
                traceback.print_exc()
                supabase_client = None
        except Exception as e:
            print(f"Error initializing Supabase client via acreate_client: {e}")
            import traceback
            traceback.print_exc() # This will print the full traceback to stderr
            supabase_client = None # Ensure it's None if initialization fails
    else:
        print("Supabase client not initialized due to missing URL or Key.")

# Dependency to get Supabase client
async def get_supabase_client() -> AsyncClient:
    if supabase_client is None:
        print("Supabase client not available during request.") # Changed log message
        raise HTTPException(status_code=503, detail="Supabase client not available. Check server startup logs.")
    return supabase_client

@app.post("/api/chat", response_model=ChatResponse)
async def handle_chat(
    chat_request: ChatRequest, # Renamed from request to avoid conflict with FastAPI Request
    fastapi_req: Request, # Inject FastAPI Request object to get headers for token
    user_id: str = Depends(get_current_user),
    db_client: AsyncClient = Depends(get_supabase_client) # Inject supabase client
) -> ChatResponse:
    print(f"Received chat request for user: {user_id}, agent: {chat_request.agent_id}, message: '{chat_request.message}'")
    llm_agent_src_path_env = os.getenv("LLM_AGENT_SRC_PATH")
    if not llm_agent_src_path_env:
        raise HTTPException(status_code=500, detail="LLM_AGENT_SRC_PATH not configured in .env")
    if GLOBAL_CONFIG_LOADER is None:
        raise HTTPException(status_code=500, detail="Critical configuration error: ConfigLoader not initialized.")

    agent_key = (user_id, chat_request.agent_id)
    try:
        # Define the auth token provider for this specific request
        async def current_request_auth_token_provider() -> Optional[str]:
            return await get_jwt_from_request_context(fastapi_req)

        if agent_key not in ACTIVE_AGENTS:
            print(f"No active agent for {agent_key}. Creating a new one.")
            # Note: base_memory_override is not typically set here unless specifically needed for a new agent.
            # The agent_loader will create the appropriate memory (Supabase or buffer) based on config.
            agent_executor = agent_loader.load_agent_executor(
                agent_name=chat_request.agent_id,
                config_loader=GLOBAL_CONFIG_LOADER,
                log_level=DEFAULT_LOG_LEVEL,
                user_id=user_id,
                async_supabase_client=db_client, # Pass the initialized async Supabase client
                auth_token_provider_callable=current_request_auth_token_provider # Pass the request-specific token provider
            )
            ACTIVE_AGENTS[agent_key] = agent_executor
            print(f"Agent for {agent_key} created and cached.")
        else:
            print(f"Using cached agent for {agent_key}.")
            agent_executor = ACTIVE_AGENTS[agent_key]
            # Potentially refresh/re-init PromptManagerService if token could expire and it's long-lived?
            # For now, assume PromptManagerService inside agent/tools handles token per call or is short-lived.

        response = await agent_executor.ainvoke({"input": chat_request.message})
        ai_reply = response.get("output", "Agent did not provide an output.")

    except FileNotFoundError as e:
        print(f"Agent configuration error for {chat_request.agent_id} (User: {user_id}): {e}")
        raise HTTPException(status_code=500, detail=f"Agent configuration error for {chat_request.agent_id}. Check server logs. {e}")
    except ImportError as e:
        print(f"Failed to import agent dependencies for {chat_request.agent_id} (User: {user_id}): {e}")
        raise HTTPException(status_code=500, detail=f"Agent import error. Check server logs. {e}")
    except Exception as e:
        print(f"Error processing message with agent {chat_request.agent_id} for user {user_id}: {e}")
        logging.error(f"Agent execution error for {agent_key}: {e}", exc_info=True)
        # Attempt to close PromptManagerService client if it was part of a failing agent
        # This is complex because the service is inside the agent.
        # Consider a finally block if agent_executor was successfully created but invoke failed.
        if agent_key in ACTIVE_AGENTS and hasattr(ACTIVE_AGENTS[agent_key], 'agent') and \
           hasattr(ACTIVE_AGENTS[agent_key].agent, 'prompt_manager') and ACTIVE_AGENTS[agent_key].agent.prompt_manager:
            try:
                print(f"Attempting to close PromptManagerService for {agent_key} due to error.")
                # Running an async function from sync error handler is tricky.
                # If load_agent_executor might raise before full setup, this might not be safe.
                # For now, this is a best-effort. A more robust solution would use FastAPI's background tasks or app shutdown events.
                # This won't work as-is from a synchronous exception handler if close() is async.
                # asyncio.create_task(ACTIVE_AGENTS[agent_key].agent.prompt_manager.close()) 
                # Better: if prompt_manager was passed to agent_loader, agent_loader itself could have a try/finally to close it.
                # For now, we rely on httpx.AsyncClient's own cleanup or OS to close sockets on process end.
                pass # Lifecycle management of PromptManagerService needs more thought for errors.
            except Exception as pm_close_err:
                print(f"Error trying to close PromptManagerService for {agent_key}: {pm_close_err}")
        raise HTTPException(status_code=500, detail=f"Error processing message with agent. Check server logs. {str(e)}")

    return ChatResponse(reply=ai_reply)

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
    db: AsyncClient = Depends(get_supabase_client)
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
    db: AsyncClient = Depends(get_supabase_client)
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
    db: AsyncClient = Depends(get_supabase_client)
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
async def get_tasks(request: Request, db: AsyncClient = Depends(get_supabase_client)):
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