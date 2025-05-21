from typing import List, Dict, Any
from supabase import Client as SupabaseClient
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict
import logging

logger = logging.getLogger(__name__)

class SupabaseChatMessageHistory(BaseChatMessageHistory):
    """
    Chat message history stored in a Supabase table.

    Args:
        supabase_client: Synchronous Supabase client.
        session_id: Arbitrary key that is used to store the messages
            of a single chat session.
        user_id: Identifier for the user associated with this chat session.
        table_name: The name of the Supabase table to store messages.
    """

    def __init__(
        self,
        supabase_client: SupabaseClient,
        session_id: str,
        user_id: str,
        table_name: str = "chat_message_history",
    ):
        self.client = supabase_client
        self.session_id = session_id
        self.user_id = user_id
        self.table_name = table_name

    @property
    def messages(self) -> List[BaseMessage]:  # type: ignore
        """Retrieve messages from Supabase"""
        try:
            response = (
                self.client.table(self.table_name)
                .select("message_data")
                .eq("session_id", self.session_id)
                .order("created_at", desc=False)
                .execute()
            )
            if response.data:
                items = [item["message_data"] for item in response.data]
                messages = messages_from_dict(items)
                return messages
            return []
        except Exception as e:
            logger.error(f"Error retrieving messages from Supabase for session {self.session_id}: {e}", exc_info=True)
            return []

    def add_messages(self, messages: List[BaseMessage]) -> None:
        """Append messages to the session in Supabase"""
        rows_to_insert = []
        for message in messages:
            rows_to_insert.append(
                {
                    "session_id": self.session_id,
                    "user_id": self.user_id,
                    "message_data": message_to_dict(message),
                    # 'created_at' will be set by Supabase default now()
                }
            )
        
        if not rows_to_insert:
            return

        try:
            response = self.client.table(self.table_name).insert(rows_to_insert).execute()
            if response.error:
                logger.error(
                    f"Error adding messages to Supabase for session {self.session_id}: {response.error.message}"
                )
            # Consider checking response.data or status_code if needed for more robust error handling
        except Exception as e:
            logger.error(
                f"Exception while adding messages to Supabase for session {self.session_id}: {e}", exc_info=True
            )

    def clear(self) -> None:
        """Clear messages from the session in Supabase"""
        try:
            response = (
                self.client.table(self.table_name)
                .delete()
                .eq("session_id", self.session_id)
                .execute()
            )
            if response.error:
                 logger.error(
                    f"Error clearing messages from Supabase for session {self.session_id}: {response.error.message}"
                )
        except Exception as e:
            logger.error(
                f"Exception while clearing messages from Supabase for session {self.session_id}: {e}", exc_info=True
            )

    # add_user_message and add_ai_message are provided by BaseChatMessageHistory
    # and internally call add_messages with a list of one message.
    # So, no need to override them unless specific logic is needed. 