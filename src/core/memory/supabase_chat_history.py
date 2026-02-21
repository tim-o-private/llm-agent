from typing import List

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict

from supabase import AsyncClient
from utils.logging_utils import get_logger

# Get a logger for this module
logger = get_logger(__name__)

class SupabaseChatMessageHistory(BaseChatMessageHistory):
    """Chat message history stored in a Supabase PostgREST table."""

    def __init__(
        self,
        supabase_client: AsyncClient,
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

    async def aget_messages(self) -> List[BaseMessage]:  # type: ignore
        """Retrieve messages asynchronously from Supabase"""
        logger.debug(f"Retrieving messages for session_id: {self.session_id}")
        try:
            response = await self.client.table(self.table_name)\
                .select("role, content, additional_kwargs, message_idx")\
                .eq(self.session_id_column, self.session_id)\
                .order(self.message_idx_column, desc=False)\
                .execute()

            logger.debug(f"Supabase select response for messages: {response}")

            if response.data:
                items = []
                for m_data in response.data:
                    additional_kwargs = m_data.get("additional_kwargs") or {}
                    content_val = m_data.get("content", "")
                    message_dict = {
                        "type": m_data["role"].lower(),
                        "data": {
                            "content": content_val,
                            "additional_kwargs": additional_kwargs,
                        }
                    }
                    if m_data["role"].lower() == "tool" and "name" in additional_kwargs:
                         message_dict["data"]["name"] = additional_kwargs["name"]
                    items.append(message_dict)

                loaded_messages = messages_from_dict(items)
                logger.info(f"Successfully retrieved and parsed {len(loaded_messages)} messages for session_id: {self.session_id}")  # noqa: E501
                return loaded_messages
            else:
                logger.info(f"No messages found in DB for session_id: {self.session_id}")
                return []
        except Exception as e:
            logger.error(f"Error retrieving messages from Supabase for session_id {self.session_id}: {e}", exc_info=True)  # noqa: E501
            return [] # Return empty list on error to prevent breaking agent flow

    async def add_message(self, message: BaseMessage) -> None:
        """Append the message to the record in Supabase"""

        # Determine the next message index by fetching current messages asynchronously
        current_messages = await self.aget_messages() # Use the new async method
        next_idx = len(current_messages)
        logger.debug(f"Current message count for session {self.session_id} is {next_idx}. Adding new message at this index.")  # noqa: E501

        message_dict = messages_to_dict([message])[0]

        role = message_dict["type"]
        content = message_dict["data"]["content"]
        additional_kwargs = message_dict["data"].get("additional_kwargs", {})

        if role.lower() == "tool" and "name" in message_dict["data"]:
            additional_kwargs["name"] = message_dict["data"]["name"]

        insert_payload = {
            self.session_id_column: self.session_id,
            self.message_idx_column: next_idx,
            "role": role,
            "content": content,
            "additional_kwargs": additional_kwargs if additional_kwargs else None,
        }

        try:
            logger.info(f"Attempting to save message to DB. Session ID: {self.session_id}, Index: {next_idx}, Role: {role}, Payload: {insert_payload}")  # noqa: E501
            response = await self.client.table(self.table_name).insert(insert_payload).execute()
            logger.info(f"Message saved for session_id={self.session_id}, idx={next_idx}. Response: {response}")
            if response.data:
                logger.debug(f"Supabase insert response data: {response.data}")
            if hasattr(response, 'error') and response.error:
                 logger.error(f"Supabase insert returned an error: {response.error}")

        except Exception as e:
            logger.error(f"Error adding message to Supabase for session_id={self.session_id}, idx={next_idx}: {e}", exc_info=True)  # noqa: E501
            # No longer using traceback.print_exc() as logger.error with exc_info=True handles it

    def clear(self) -> None:
        """Clear session messages from Supabase"""
        # print("WARNING: SupabaseChatMessageHistory.clear is currently synchronous and will likely fail with AsyncClient.")  # noqa: E501
        raise NotImplementedError("Synchronous clear method is not compatible with AsyncClient. Refactor needed.")
        # try:
        #     self.client.table(self.table_name).delete().eq( # This would need await
        #         self.session_id_column, self.session_id
        #     ).execute() # This would need await
        # except Exception as e:
        #     # print(f"Error clearing messages: {e}")
        #     pass
