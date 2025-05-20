from typing import List, Optional, Any
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict
from supabase import Client, PostgrestAPIResponse
import json

class SupabaseChatMessageHistory(BaseChatMessageHistory):
    """Chat message history stored in a Supabase PostgREST table."""

    def __init__(
        self,
        supabase_client: Client,
        session_id: str,
        user_id: str, # For RLS, though direct use here depends on how client is configured
        table_name: str = "agent_chat_messages",
        session_id_column: str = "session_id",
        message_idx_column: str = "message_idx",
        # Other columns are derived from Langchain message structure
    ):
        self.client = supabase_client
        self.session_id = session_id
        self.user_id = user_id # Store for context, though RLS is key
        self.table_name = table_name
        self.session_id_column = session_id_column
        self.message_idx_column = message_idx_column

    @property
    def messages(self) -> List[BaseMessage]:  # type: ignore
        """Retrieve messages from Supabase"""
        try:
            response: PostgrestAPIResponse = (
                self.client.table(self.table_name)
                .select("role, content, additional_kwargs, message_idx") # Select relevant message data
                .eq(self.session_id_column, self.session_id)
                .order(self.message_idx_column, desc=False)
                .execute()
            )
            if response.data:
                # Reconstruct Langchain messages. Assumes stored role and content are compatible.
                # The `type` field in `messages_to_dict` needs to be mapped to `role`.
                # And `data` in `messages_from_dict` needs to map to `content`.
                items = []
                for i, m_data in enumerate(response.data):
                    # Convert Supabase row to a dict that messages_from_dict expects
                    # We stored `role` and `content` directly.
                    # `additional_kwargs` from Supabase should map to `additional_kwargs` in the message dict.
                    # The actual structure from `messages_to_dict` is a list of dicts like:
                    # {'type': 'human', 'data': {'content': 'foo', 'additional_kwargs': {}}} 
                    # We need to map our flat Supabase structure back to this.
                    
                    # If additional_kwargs is None or an empty dict from DB, ensure it's an empty dict for lc
                    additional_kwargs = m_data.get("additional_kwargs") or {}

                    # Check if content is a string, if not, try to dump it as json for tool messages
                    # This primarily handles the case where content might be structured (e.g. tool call output)
                    # and was stored as JSONB in additional_kwargs, but simple string content is common.
                    content_val = m_data.get("content", "")

                    # Langchain messages_from_dict expects type (role) and data.content
                    # The actual conversion logic might need to be more robust depending on how
                    # exactly different message types (AIMessage, HumanMessage, ToolMessage) serialize.
                    # For now, a generic mapping for Human/AI/System messages:
                    message_dict = {
                        "type": m_data["role"].lower(), # Ensure lowercase role for type mapping
                        "data": {
                            "content": content_val,
                            "additional_kwargs": additional_kwargs if additional_kwargs is not None else {},
                        }
                    }
                    # For tool messages, the name might be in additional_kwargs
                    if m_data["role"].lower() == "tool" and "name" in additional_kwargs:
                         message_dict["data"]["name"] = additional_kwargs["name"] # Langchain expects name for ToolMessage

                    items.append(message_dict)
                
                return messages_from_dict(items)
            else:
                return []
        except Exception as e:
            # print(f"Error retrieving messages: {e}") # Consider proper logging
            return []

    def add_message(self, message: BaseMessage) -> None:
        """Append the message to the record in Supabase"""
        # Determine the next message index
        current_messages = self.messages # This triggers a select
        next_idx = len(current_messages)

        # Convert Langchain message to a dict that can be inserted into Supabase
        # messages_to_dict returns a list of dicts, we take the first (and only)
        message_dict = messages_to_dict([message])[0]
        
        role = message_dict["type"] # e.g. 'human', 'ai'
        content = message_dict["data"]["content"]
        additional_kwargs = message_dict["data"].get("additional_kwargs", {})

        # For tool messages, LangChain stores the tool_call_id in additional_kwargs
        # and the 'name' of the tool at the top level of the message's data dict.
        # We need to ensure 'name' is preserved if it exists.
        if role.lower() == "tool" and "name" in message_dict["data"]:
            additional_kwargs["name"] = message_dict["data"]["name"]

        try:
            self.client.table(self.table_name).insert(
                {
                    self.session_id_column: self.session_id,
                    self.message_idx_column: next_idx,
                    "role": role,
                    "content": content,
                    "additional_kwargs": additional_kwargs if additional_kwargs else None, # Ensure None if empty
                    # timestamp is handled by default value in DB
                }
            ).execute()
        except Exception as e:
            # print(f"Error adding message: {e}") # Consider proper logging
            pass # Or raise

    def clear(self) -> None:
        """Clear session messages from Supabase"""
        try:
            self.client.table(self.table_name).delete().eq(
                self.session_id_column, self.session_id
            ).execute()
        except Exception as e:
            # print(f"Error clearing messages: {e}") # Consider proper logging
            pass # Or raise 