from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Tuple

# Required imports for agent logic
import logging
import os
from core import agent_loader # Assumes 'core' is in a location accessible via sys.path
from utils.config_loader import ConfigLoader # Assumes 'utils' is accessible
from langchain.memory import ConversationBufferMemory
from langchain.agents import AgentExecutor

# Placeholder for user authentication if needed later
# from ..dependencies import get_current_user 

router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
    # dependencies=[Depends(get_current_user)], # Uncomment if auth is added
    responses={404: {"description": "Not found"}},
)

# Local cache for active agent executors within this router: (user_id, agent_id) -> AgentExecutor
ROUTER_ACTIVE_AGENTS: Dict[Tuple[str, str], AgentExecutor] = {}
# Local ConfigLoader instance for this router
# Ideally, ConfigLoader is a singleton managed by the app, but for a quick fix:
try:
    ROUTER_CONFIG_LOADER = ConfigLoader()
except Exception as e:
    logging.critical(f"[ChatRouter] Failed to initialize ROUTER_CONFIG_LOADER: {e}", exc_info=True)
    ROUTER_CONFIG_LOADER = None

ROUTER_DEFAULT_LOG_LEVEL = logging.INFO


class ChatMessageIn(BaseModel):
    message: str
    userId: Optional[str] = None # Assuming userId might be used for context/logging
    sessionId: Optional[str] = None

class ChatMessageOut(BaseModel):
    agentResponse: str
    newSessionId: Optional[str] = None # Retaining for potential future session management

@router.post("/send_message", response_model=ChatMessageOut)
async def send_message_to_agent(payload: ChatMessageIn):
    """
    Receives a message from the user, passes it to an LLM agent,
    and returns the agent's response.
    """
    print(f"[ChatRouter] Received message: '{payload.message}' for user: {payload.userId}, session: {payload.sessionId}")

    if ROUTER_CONFIG_LOADER is None:
        raise HTTPException(status_code=500, detail="[ChatRouter] Critical configuration error: ConfigLoader not initialized.")

    # Use a default agent_id for now, e.g., "assistant" or "coach"
    # This should ideally come from the frontend or be configurable
    agent_id_to_use = os.getenv("DEFAULT_CHAT_AGENT_ID", "assistant") 
    user_id_to_use = payload.userId or "default_user" # Fallback if userId is not provided

    agent_key = (user_id_to_use, agent_id_to_use)
    ai_reply = "Error: Agent could not process the request."

    try:
        if agent_key not in ROUTER_ACTIVE_AGENTS:
            print(f"[ChatRouter] No active agent for {agent_key}. Creating a new one.")
            # For session-specific memory, ConversationBufferMemory would need to be loaded/saved
            # based on payload.sessionId. For now, new memory per agent load.
            # If sessionId is present, one might try to load existing memory here.
            new_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
            
            agent_executor = agent_loader.load_agent_executor(
                agent_name=agent_id_to_use,
                config_loader=ROUTER_CONFIG_LOADER,
                log_level=ROUTER_DEFAULT_LOG_LEVEL,
                memory=new_memory,
                user_id=user_id_to_use # Pass user_id for agent context
            )
            ROUTER_ACTIVE_AGENTS[agent_key] = agent_executor
            print(f"[ChatRouter] Agent for {agent_key} created and cached.")
        else:
            print(f"[ChatRouter] Using cached agent for {agent_key}.")
            agent_executor = ROUTER_ACTIVE_AGENTS[agent_key]

        # Invoke the agent
        # The input key (e.g., "input") should match what the agent expects
        response = await agent_executor.ainvoke({"input": payload.message})
        ai_reply = response.get("output", "Agent did not provide an output.")
        print(f"[ChatRouter] Agent response for {agent_key}: {ai_reply}")

    except FileNotFoundError as e:
        print(f"[ChatRouter] Agent configuration error for {agent_id_to_use} (User: {user_id_to_use}): {e}")
        # Sanitize error for client
        ai_reply = f"Error: Agent configuration not found for '{agent_id_to_use}'. Please contact support."
        # Consider raising HTTPException for specific client feedback if appropriate
        # raise HTTPException(status_code=500, detail=f"Agent configuration error for {agent_id_to_use}. {e}")
    except ImportError as e:
        print(f"[ChatRouter] Failed to import agent dependencies for {agent_id_to_use} (User: {user_id_to_use}): {e}")
        ai_reply = "Error: A problem occurred with the agent's setup. Please contact support."
        # raise HTTPException(status_code=500, detail=f"Agent import error. {e}")
    except Exception as e:
        print(f"[ChatRouter] Error processing message with agent {agent_id_to_use} for user {user_id_to_use}: {e}")
        logging.error(f"[ChatRouter] Agent execution error for {agent_key}: {e}", exc_info=True)
        ai_reply = f"Error: Could not process your message. Details: {str(e)}"
        # Consider a more generic message for the client unless debugging
        # ai_reply = "Sorry, I encountered an error. Please try again."
        # raise HTTPException(status_code=500, detail=f"Error processing message with agent. {str(e)}")
    
    # Retain sessionId for now, can be used for future stateful session management
    current_session_id = payload.sessionId 
    print(f"[ChatRouter] Sending response: '{ai_reply}' for session: {current_session_id}")
    return ChatMessageOut(agentResponse=ai_reply, newSessionId=current_session_id)

# Future: Add endpoint for fetching chat history
# @router.get("/history/{session_id}")
# async def get_chat_history(session_id: str):
#     # Logic to fetch history from Supabase based on session_id
#     return {"sessionId": session_id, "history": []} 