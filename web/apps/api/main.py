import sys
import os
import logging # Added for log_level
from typing import Dict, Tuple # Added for typing the cache

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
# from typing import Any # No longer explicitly needed here with more specific types
from langchain.memory import ConversationBufferMemory # Added
from langchain.agents import AgentExecutor # Added for type hinting

# Assuming these are in the LLM_AGENT_SRC_PATH after sys.path modification
from core import agent_loader 
from utils.config_loader import ConfigLoader # Added

# Load environment variables (like the path to llm-agent src)
load_dotenv()

LLM_AGENT_SRC_PATH = os.getenv("LLM_AGENT_SRC_PATH")
if LLM_AGENT_SRC_PATH and LLM_AGENT_SRC_PATH not in sys.path:
    sys.path.insert(0, LLM_AGENT_SRC_PATH)

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

class ChatRequest(BaseModel):
    user_id: str 
    agent_id: str 
    message: str

class ChatResponse(BaseModel):
    reply: str

@app.post("/api/chat", response_model=ChatResponse)
async def handle_chat(request: ChatRequest) -> ChatResponse:
    print(f"Received chat request for user: {request.user_id}, agent: {request.agent_id}, message: \\'{request.message}\\'")

    if not LLM_AGENT_SRC_PATH:
        # This check is good, but also ensure GLOBAL_CONFIG_LOADER initialized
        raise HTTPException(status_code=500, detail="LLM_AGENT_SRC_PATH not configured in .env")
    
    if GLOBAL_CONFIG_LOADER is None:
        # If ConfigLoader failed to init, the app is in a bad state.
        raise HTTPException(status_code=500, detail="Critical configuration error: ConfigLoader not initialized.")

    agent_key = (request.user_id, request.agent_id)
    
    try:
        if agent_key not in ACTIVE_AGENTS:
            print(f"No active agent for {agent_key}. Creating a new one.")
            # Create new memory for this user/agent session
            # The ConversationBufferMemory will store the history in memory.
            # Langchain's memory objects have a `chat_memory` attribute (often a list of messages)
            # and can be configured with `return_messages=True` if the LLM/agent expects message objects.
            # For now, default setup should work with `load_agent_executor` expecting `input` and `chat_history`.
            new_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
            
            # Load/create the agent executor
            agent_executor = agent_loader.load_agent_executor(
                agent_name=request.agent_id,
                config_loader=GLOBAL_CONFIG_LOADER,
                log_level=DEFAULT_LOG_LEVEL,
                memory=new_memory, # Pass the newly created memory
                user_id=request.user_id
            )
            ACTIVE_AGENTS[agent_key] = agent_executor
            print(f"Agent for {agent_key} created and cached.")
        else:
            print(f"Using cached agent for {agent_key}.")
            agent_executor = ACTIVE_AGENTS[agent_key]

        # Process the message using the (potentially cached) agent executor
        # The agent_executor.ainvoke call expects a dictionary.
        # The `memory` object associated with the agent_executor will automatically
        # handle loading previous messages for the `chat_history` placeholder (if used in prompt)
        # and saving the current interaction.
        response = await agent_executor.ainvoke({"input": request.message})
        
        ai_reply = response.get("output", "Agent did not provide an output.")

    except FileNotFoundError as e:
        print(f"Agent configuration error for {request.agent_id} (User: {request.user_id}): {e}")
        raise HTTPException(status_code=500, detail=f"Agent configuration error for {request.agent_id}. Check server logs. {e}")
    except ImportError as e:
        print(f"Failed to import agent dependencies for {request.agent_id} (User: {request.user_id}): {e}")
        raise HTTPException(status_code=500, detail=f"Agent import error. Check server logs. {e}")
    except Exception as e:
        print(f"Error processing message with agent {request.agent_id} for user {request.user_id}: {e}")
        # Log the full exception for server-side debugging
        logging.error(f"Agent execution error for {agent_key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing message with agent. Check server logs. {str(e)}")

    return ChatResponse(reply=ai_reply)

if __name__ == "__main__":
    import uvicorn
    # Ensure logging is configured to see messages from the application
    logging.basicConfig(level=logging.INFO) 
    print("Starting API server with Uvicorn for local development...")
    uvicorn.run(app, host="0.0.0.0", port=3001) 