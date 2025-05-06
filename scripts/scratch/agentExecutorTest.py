import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.outputs import LLMResult
from langchain_core.callbacks.base import BaseCallbackHandler
from typing import Any, Dict, List, Optional, Union
import logging

# --- Setup ---
# Set up basic logging to see callback outputs clearly
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Ensure GOOGLE_API_KEY is set in your environment
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    logger.error("Error: GOOGLE_API_KEY environment variable not set.")
    exit()

# Initialize the LLM
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-preview-0417", google_api_key=api_key)
simple_prompt = "Hello, world!"

# --- Minimal Callback Handler ---
class MetadataCapturingHandler(BaseCallbackHandler):
    """Captures and prints metadata from on_llm_end."""
    captured_metadata: Optional[Dict[str, Any]] = None

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        logger.info("--- Callback: on_llm_end triggered ---")
        # response.generations is a list of lists of Generations
        # We are interested in the first generation of the first list
        if response.generations and response.generations[0]:
            first_generation = response.generations[0][0]
            logger.info(f"Callback: Generation type: {type(first_generation)}")
            # The generation object might have the message object
            if hasattr(first_generation, 'message'):
                 message = first_generation.message
                 logger.info(f"Callback: Message type: {type(message)}")
                 if hasattr(message, 'usage_metadata'):
                    self.captured_metadata = message.usage_metadata
                    logger.info(f"Callback: Captured usage_metadata: {self.captured_metadata}")
                 else:
                     logger.warning("Callback: Message object lacks 'usage_metadata'.")
            # Or generation_info might contain it (less likely for usage_metadata)
            elif hasattr(first_generation, 'generation_info') and first_generation.generation_info:
                 logger.info(f"Callback: Checking generation_info: {first_generation.generation_info}")
                 # Try to find usage metadata within generation_info if necessary (depends on LLM implementation)
            else:
                logger.warning("Callback: Generation object lacks 'message' or 'generation_info'.")

        # Check llm_output as well, as it sometimes holds raw response data
        if response.llm_output:
            logger.info(f"Callback: llm_output keys: {response.llm_output.keys()}")
            # Example check if usage data is directly in llm_output (adjust key if needed)
            if 'usage_metadata' in response.llm_output:
                 logger.info(f"Callback: Found usage_metadata in llm_output: {response.llm_output['usage_metadata']}")
            elif 'token_usage' in response.llm_output:
                 logger.info(f"Callback: Found token_usage in llm_output: {response.llm_output['token_usage']}")

        else:
             logger.warning("Callback: No llm_output in response.")
        logger.info("--- Callback: on_llm_end finished ---")

# Instantiate the handler
metadata_handler = MetadataCapturingHandler()


# --- Test 1: Direct LLM Invocation ---
print("\n--- Test 1: Direct LLM Call ---")
try:
    direct_response = llm.invoke([HumanMessage(content=simple_prompt)])
    print(f"Direct Response Type: {type(direct_response)}")
    print(f"Direct Response usage_metadata: {direct_response.usage_metadata}")
except Exception as e:
    print(f"Error during direct call: {e}")

# --- Test 2: LLM Call within AgentExecutor ---
print("\n--- Test 2: AgentExecutor Call with Callback ---")

# Minimal prompt for a tool-calling agent
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create agent (no actual tools needed for this test)
agent = create_tool_calling_agent(llm, tools=[], prompt=prompt)

# Memory for the agent
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Create AgentExecutor
agent_executor = AgentExecutor(
    agent=agent,
    tools=[],
    memory=memory,
    verbose=False # Keep agent verbose off to focus on callback logs
)

try:
    # Invoke the agent executor WITH the callback handler
    agent_response_dict = agent_executor.invoke(
        {"input": simple_prompt},
        config={"callbacks": [metadata_handler]} # Pass handler here
    )

    print(f"AgentExecutor Invoke Result Keys: {agent_response_dict.keys()}")
    print(f"AgentExecutor Invoke Output: {agent_response_dict.get('output')}")

    # Check the message stored in memory again
    if memory.chat_memory.messages:
        last_message_in_memory = memory.chat_memory.messages[-1]
        print(f"Last Message in Agent Memory Type: {type(last_message_in_memory)}")
        if isinstance(last_message_in_memory, AIMessage):
            print(f"Last Message in Agent Memory usage_metadata: {last_message_in_memory.usage_metadata}")
        else:
             print("Last message in memory was not an AIMessage.")
    else:
        print("Agent memory is empty after invoke.")

    # Check what the callback captured
    print(f"Metadata captured by Callback Handler: {metadata_handler.captured_metadata}")

except Exception as e:
    print(f"Error during AgentExecutor call: {e}")

print("\n--- Test Complete ---") 