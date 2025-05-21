import json
from typing import Type, Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, root_validator
from supabase import create_client, Client as SupabaseClient
#from supabase.lib.client_options import ClientOptions

from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun

import logging # UPDATED to relative import
# from core.db.supabase_client import get_supabase_client # For async client, if tool runs async

logger = logging.getLogger(__name__)

class ManageLongTermMemoryToolInput(BaseModel):
    operation: str = Field(description="The operation to perform: 'save', 'retrieve', or 'clear'.")
    data: Optional[str] = Field(None, description="The data to save (for 'save' operation).")

class ManageLongTermMemoryTool(BaseTool):
    name: str = "manage_long_term_memory"
    description: str = (
        "Manages the agent's long-term memory. "
        "Use 'retrieve' to get current LTM notes. "
        "Use 'save' with 'data' to update/overwrite LTM notes. "
        "Use 'clear' to erase LTM notes."
    )
    args_schema: Type[BaseModel] = ManageLongTermMemoryToolInput
    
    user_id: str
    agent_id: str # Made agent_id a required field
    supabase_url: str
    supabase_key: str
    
    _db_client: Optional[SupabaseClient] = None

    # Pydantic V2 uses model_post_init for initialization logic after fields are set
    def model_post_init(self, __context: Any) -> None:
        # super().model_post_init(__context) # BaseTool likely doesn't have this, and not needed for our logic.
        
        # Fields should be validated by Pydantic automatically as they are required.
        # This explicit check can ensure they are also non-empty if that's a requirement beyond just being present.
        if not self.user_id or not self.agent_id or not self.supabase_url or not self.supabase_key:
            raise ValueError("user_id, agent_id, supabase_url, and supabase_key are required and must be non-empty for ManageLongTermMemoryTool.")
        
        try:
            self._db_client = create_client(self.supabase_url, self.supabase_key)
            logger.info(f"ManageLongTermMemoryTool: Supabase client initialized for user {self.user_id}, agent {self.agent_id}")
        except Exception as e:
            logger.error(f"ManageLongTermMemoryTool: Failed to initialize Supabase client for user {self.user_id}, agent {self.agent_id}: {e}", exc_info=True)
            self._db_client = None

    def _run(self, operation: str, data: Optional[str] = None) -> str:
        if self._db_client is None:
            logger.error(f"ManageLongTermMemoryTool: Supabase client not initialized for user {self.user_id}, agent {self.agent_id}. Cannot perform operation '{operation}'.")
            return "Error: Long-term memory service is not available due to configuration error."

        logger.info(f"ManageLongTermMemoryTool: User '{self.user_id}', Agent '{self.agent_id}', Operation '{operation}'")

        try:
            if operation == "retrieve":
                response = (self._db_client.table("agent_long_term_memory")
                            .select("notes")
                            .eq("user_id", self.user_id)
                            .eq("agent_id", self.agent_id) # Use agent_id here
                            .limit(1)
                            .execute())
                if response.data:
                    notes = response.data[0].get("notes", "")
                    logger.info(f"ManageLongTermMemoryTool: Retrieved notes. Length: {len(notes)}")
                    return notes if notes else "No long-term memory notes found."
                return "No long-term memory notes found."
            
            elif operation == "save":
                if data is None:
                    return "Error: No data provided for 'save' operation."
                
                # Upsert ensures that if a record exists, it's updated, otherwise it's inserted.
                response = (self._db_client.table("agent_long_term_memory")
                            .upsert({
                                "user_id": self.user_id,
                                "agent_id": self.agent_id, # Use agent_id here
                                "notes": data,
                                "updated_at": "now()" # Use database's now() function
                            }, on_conflict="user_id, agent_id") # Specify conflict columns
                            .execute())
                
                # Basic check for successful upsert (actual success depends on RLS and DB state)
                if response.data or (response.status_code >= 200 and response.status_code < 300): # Check for successful HTTP status
                    logger.info(f"ManageLongTermMemoryTool: Saved notes. Data length: {len(data)}")
                    return "Long-term memory notes saved successfully."
                else:
                    logger.error(f"ManageLongTermMemoryTool: Failed to save notes. Response: {response.error.message if response.error else 'No error message'}")
                    return f"Error saving long-term memory notes: {response.error.message if response.error else 'Unknown error'}"

            elif operation == "clear":
                response = (self._db_client.table("agent_long_term_memory")
                            .delete()
                            .eq("user_id", self.user_id)
                            .eq("agent_id", self.agent_id) # Use agent_id here
                            .execute())
                # Check for successful deletion or if no record existed (which is also a success for 'clear')
                if response.data or (response.status_code >= 200 and response.status_code < 300):
                    logger.info("ManageLongTermMemoryTool: Cleared notes (or no notes existed to clear).")
                    return "Long-term memory notes cleared successfully."
                else:
                    logger.error(f"ManageLongTermMemoryTool: Failed to clear notes. Response: {response.error.message if response.error else 'No error message'}")
                    return f"Error clearing long-term memory notes: {response.error.message if response.error else 'Unknown error'}"
            
            else:
                return f"Error: Unknown operation '{operation}'. Valid operations are 'retrieve', 'save', 'clear'."

        except Exception as e:
            logger.error(f"ManageLongTermMemoryTool: Error during operation '{operation}' for user '{self.user_id}', agent '{self.agent_id}': {e}", exc_info=True)
            return f"Error during memory operation: {e}"

    async def _arun(self, operation: str, data: Optional[str] = None) -> str:
        # For now, just wrapping the sync version. Consider a true async implementation if performance critical.
        # Note: Supabase Python client's async operations are still maturing.
        # This might require an async version of the Supabase client if available and different.
        # For current supabase-py, the client itself is sync, so direct async DB calls aren't standard.
        return self._run(operation, data) 