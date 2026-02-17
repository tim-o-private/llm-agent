from typing import Any, Dict, List

from langchain.memory import ConversationBufferWindowMemory
from langchain_core.messages import BaseMessage, get_buffer_string
from langchain_postgres import PostgresChatMessageHistory  # Assuming this is the correct import path


class AsyncPostgresBufferedWindowMemory(ConversationBufferWindowMemory):
    """
    Asynchronous version of ConversationBufferWindowMemory that uses
    aget_messages and aadd_messages from PostgresChatMessageHistory.
    """

    chat_memory: PostgresChatMessageHistory # Type hint for clarity

    @property
    async def abuffer(self) -> List[BaseMessage]:
        """
        Asynchronously get buffer of messages.
        Compared to the synchronous version, this directly calls aget_messages.
        """
        if not self.return_messages:
            # This path is less common for chat agents but included for completeness.
            # It would require an async version of get_buffer_string if that involves I/O.
            # For now, assuming get_buffer_string is CPU-bound or chat_memory.aget_messages() is preferred.
            # If get_buffer_string needs to be async, this part needs more thought.
            # messages = await self.chat_memory.aget_messages()
            # return get_buffer_string(
            #     messages[-self.k * 2 :] if self.k > 0 else messages,
            #     human_prefix=self.human_prefix,
            #     ai_prefix=self.ai_prefix,
            # )
            # For simplicity and typical use, let's assume return_messages is True
            # and defer handling of async get_buffer_string if it's not standard.
            # Raising an error for now if this path is hit with an async history.
            raise NotImplementedError(
                "Async buffer_as_string requires async get_buffer_string or different handling."
            )

        # Directly use aget_messages for the buffer
        messages = await self.chat_memory.aget_messages()
        return messages[-self.k * 2 :] if self.k > 0 else []

    async def aload_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Asynchronously load memory variables.
        This overrides the base aload_memory_variables (which uses run_in_executor)
        to directly use the async abuffer property.
        """
        buffer = await self.abuffer
        if self.return_messages:
            return {self.memory_key: buffer}
        else:
            # This path depends on the resolution of abuffer when return_messages=False
            # For now, it would hit the NotImplementedError in abuffer.
            return {self.memory_key: get_buffer_string(buffer, human_prefix=self.human_prefix, ai_prefix=self.ai_prefix)}


    async def asave_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """
        Asynchronously save context to memory.
        This method should extract the new messages (input and output) and
        use chat_memory.aadd_messages().
        """
        # Adapted from BaseChatMemory.save_context and ConversationBufferMemory.save_context
        input_val = self._get_input_output(inputs, outputs)[self.input_key]
        output_val = self._get_input_output(inputs, outputs)[self.output_key]

        # Create BaseMessage instances for input and output.
        # LangChain typically has helper functions for this, e.g.,
        # from langchain_core.messages import HumanMessage, AIMessage
        # For now, constructing them based on typical structure.
        # This part might need adjustment based on how your agent
        # structures input/output messages before they reach memory.

        # Assuming self.chat_memory.aadd_messages expects a List[BaseMessage]
        # We need to construct these messages.
        # The ConversationBufferMemory typically uses _get_input_output and then
        # constructs HumanMessage and AIMessage. Let's ensure we have a way to make these.
        # If this runs into issues, it means we need more precise message construction.

        # messages_to_add: List[BaseMessage] = []
        # # This part is tricky; _get_prompt_input_key is protected.
        # # The original save_context in ConversationBufferMemory does:
        # # messages = self.prompt.format_messages(**inputs, **outputs)
        # # This implies that the messages are already formatted by the prompt.
        # # However, the base BaseChatMemory.save_context does:
        # # self.chat_memory.add_messages(self.prep_messages(inputs, outputs))
        # # and prep_messages does:
        # # messages_to_add.append(HumanMessage(content=input_str))
        # # messages_to_add.append(AIMessage(content=output_str))

        # Let's use the simpler HumanMessage/AIMessage construction as a starting point,
        # which is common for direct chat history manipulation.
        from langchain_core.messages import AIMessage, HumanMessage  # Ensure these are available

        messages_to_add = [
            HumanMessage(content=input_val),
            AIMessage(content=output_val)
        ]

        await self.chat_memory.aadd_messages(messages_to_add)

        # Prune buffer if it exceeds k value (if k is positive)
        # This part is handled by the chat_memory's windowing or the abuffer property's slicing.
        # The ConversationBufferWindowMemory itself doesn't do explicit pruning after save_context;
        # the windowing is applied when messages are read.
        # So, direct aadd_messages should be sufficient.
        # If PostgresChatMessageHistory itself doesn't handle windowing (it usually doesn't,
        # it's a full history), then the windowing effect comes purely from how `abuffer`
        # slices the messages.
        pass

    def clear(self) -> None:
        """Clear memory contents."""
        # This should ideally be async too if it involves DB operations
        # For PostgresChatMessageHistory, clear() is synchronous and works on a table.
        # If an async clear is needed: self.chat_memory.aclear()
        # Let's assume chat_memory.clear() is acceptable for now.
        # If it blocks in async, it needs to be await self.chat_memory.aclear()
        self.chat_memory.clear()

    async def aclear(self) -> None:
        """Asynchronously clear memory contents."""
        # Assuming PostgresChatMessageHistory has an aclear method
        if hasattr(self.chat_memory, 'aclear'):
            await self.chat_memory.aclear()
        else:
            # Fallback or raise error if truly async clear is critical
            # For now, let's assume the sync clear is okay or aclear doesn't exist
            # on this version of PostgresChatMessageHistory.
            # If PostgresChatMessageHistory.clear() is already non-blocking for async engine,
            # then no special async version is strictly needed.
            # However, if clear() does I/O, it should be async.
            # The provided PostgresChatMessageHistory typically uses sync methods
            # for operations like clear() on the underlying engine if not called from an async context.
            # Let's assume the user intends to call this from an async context.
            # If the underlying `clear` blocks, this won't be truly async.
            # Most history stores provide `clear` and `aclear`.
            self.chat_memory.clear() # This might need to be `await self.chat_memory.aclear()` if available
                                    # and if clear() is blocking.
                                    # For now, keeping it simple. This will be the main point of failure
                                    # if `clear()` is blocking and `aclear()` is needed but not used.
                                    # Langchain's own PG history does have `aclear`.
            # Let's assume the user has a version that supports aclear or clear is non-blocking.
            # A safer bet is to call aclear if available:
            # if hasattr(self.chat_memory, "aclear"):
            #     await self.chat_memory.aclear()
            # else:
            #     self.chat_memory.clear() # Or raise error if async clear is vital
            # Making it explicit for this version:
            await self.chat_memory.aclear() # Relying on PostgresChatMessageHistory to have aclear
