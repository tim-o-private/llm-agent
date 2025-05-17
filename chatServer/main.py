import sys
import os
import logging # Added for log_level
from typing import Dict, Tuple, Optional # Added Optional here

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Request, status
from pydantic import BaseModel
# from typing import Any # No longer explicitly needed here with more specific types
from langchain.memory import ConversationBufferMemory # Added
from langchain.agents import AgentExecutor # Added for type hinting
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from supabase import create_client, AsyncClient

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

@app.post("/api/chat", response_model=ChatResponse)
async def handle_chat(
    request: ChatRequest,
    user_id: str = Depends(get_current_user)
) -> ChatResponse:
    print(f"Received chat request for user: {user_id}, agent: {request.agent_id}, message: '{request.message}'")
    llm_agent_src_path_env = os.getenv("LLM_AGENT_SRC_PATH")
    if not llm_agent_src_path_env:
        raise HTTPException(status_code=500, detail="LLM_AGENT_SRC_PATH not configured in .env")
    if GLOBAL_CONFIG_LOADER is None:
        raise HTTPException(status_code=500, detail="Critical configuration error: ConfigLoader not initialized.")

    agent_key = (user_id, request.agent_id)
    try:
        if agent_key not in ACTIVE_AGENTS:
            print(f"No active agent for {agent_key}. Creating a new one.")
            new_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
            agent_executor = agent_loader.load_agent_executor(
                agent_name=request.agent_id,
                config_loader=GLOBAL_CONFIG_LOADER,
                log_level=DEFAULT_LOG_LEVEL,
                memory=new_memory,
                user_id=user_id
            )
            ACTIVE_AGENTS[agent_key] = agent_executor
            print(f"Agent for {agent_key} created and cached.")
        else:
            print(f"Using cached agent for {agent_key}.")
            agent_executor = ACTIVE_AGENTS[agent_key]

        response = await agent_executor.ainvoke({"input": request.message})
        ai_reply = response.get("output", "Agent did not provide an output.")

    except FileNotFoundError as e:
        print(f"Agent configuration error for {request.agent_id} (User: {user_id}): {e}")
        raise HTTPException(status_code=500, detail=f"Agent configuration error for {request.agent_id}. Check server logs. {e}")
    except ImportError as e:
        print(f"Failed to import agent dependencies for {request.agent_id} (User: {user_id}): {e}")
        raise HTTPException(status_code=500, detail=f"Agent import error. Check server logs. {e}")
    except Exception as e:
        print(f"Error processing message with agent {request.agent_id} for user {user_id}: {e}")
        logging.error(f"Agent execution error for {agent_key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing message with agent. Check server logs. {str(e)}")

    return ChatResponse(reply=ai_reply)

# Global Supabase client instance
# Initialize as None, will be created on startup
supabase_client: AsyncClient | None = None

@app.on_event("startup")
async def startup_event():
    global supabase_client
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY"):
        try:
            supabase_client = await create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
            print("Supabase client initialized successfully.")
        except Exception as e:
            print(f"Error initializing Supabase client: {e}")
            supabase_client = None # Ensure it's None if initialization fails
    else:
        print("Supabase client not initialized due to missing URL or Key.")

# Dependency to get Supabase client
async def get_supabase_client() -> AsyncClient:
    if supabase_client is None:
        print("Supabase client not available.")
        raise HTTPException(status_code=503, detail="Supabase client not available")
    return supabase_client

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
    logging.basicConfig(level=logging.INFO) 
    print("Starting API server with Uvicorn for local development...")
    uvicorn.run(app, host="0.0.0.0", port=3001) 