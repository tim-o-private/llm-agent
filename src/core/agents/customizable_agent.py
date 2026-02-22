import logging  # Ensure logging is imported at the module level
import os
from typing import Any, Dict, List, Optional, Union

from langchain.agents import AgentExecutor

# from langchain.agents.format_scratchpad import format_to_openai_function_messages # Old formatter
from langchain.agents.format_scratchpad.tools import format_to_tool_messages  # New formatter
from langchain.agents.output_parsers import ToolsAgentOutputParser  # User's preferred parser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.tools import BaseTool

from utils.logging_utils import get_logger

# Assuming PromptManagerService is in src.core.prompting
# Adjust import path as necessary based on your project structure
# Removed: from core.prompting.prompt_manager import PromptManagerService # Not used by executor directly if CustomizableAgent is removed  # noqa: E501

logger = get_logger(__name__)

# Helper function for processing scratchpad data
# Ensure observations are not None or empty, as this can cause API errors with Gemini
def preprocess_intermediate_steps(intermediate_steps: List[tuple]) -> List[tuple]:
    processed_steps = []
    for i, (action, observation) in enumerate(intermediate_steps):
        logger.debug(f"[preprocess_intermediate_steps] Step {i} - Original Action: {action}")
        logger.debug(f"[preprocess_intermediate_steps] Step {i} - Original Observation: {observation!r}") # Added !r for more detail  # noqa: E501

        processed_observation = observation
        if observation is None or (isinstance(observation, str) and not observation.strip()):
            # Using a clear placeholder for empty or None observations
            processed_observation = "(Tool returned no output or an empty string)"
            logger.warning(f"[preprocess_intermediate_steps] Step {i} - Observation was None or empty, replaced with placeholder. Original: {observation!r}")  # noqa: E501

        logger.debug(f"[preprocess_intermediate_steps] Step {i} - Processed Observation: {processed_observation!r}")
        processed_steps.append((action, processed_observation))
    return processed_steps

class CustomizableAgentExecutor(AgentExecutor):
    model_config = {"arbitrary_types_allowed": True}

    @property
    def input_keys(self) -> List[str]:
        """Override to avoid AgentExecutor introspecting RunnableSequence for input_keys."""
        return ["input", "chat_history"]

    @classmethod
    def from_agent_config(
        cls,
        agent_config_dict: Dict[str, Any],
        tools: List[BaseTool],
        user_id: str,
        session_id: str,
        logger_instance: Optional[logging.Logger] = None,
    ) -> "CustomizableAgentExecutor":

        current_logger = logger_instance if logger_instance else logger
        agent_name_from_config = agent_config_dict.get('agent_name', 'UnknownAgent')
        current_logger.info(f"Creating CustomizableAgentExecutor for '{agent_name_from_config}' from config dictionary.")  # noqa: E501

        llm_config_dict = agent_config_dict.get('llm', {})
        if not llm_config_dict or not llm_config_dict.get('model'):
            raise ValueError("LLM model configuration is missing or incomplete in agent_config_dict.")

        provider = llm_config_dict.get('provider', 'gemini').lower()
        model_name = llm_config_dict.get('model', 'gemini-pro')
        temperature = float(llm_config_dict.get("temperature", 0.7))

        if provider == 'claude':
            from langchain_anthropic import ChatAnthropic
            anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
            if not anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not found for ChatAnthropic.")
            llm_instance = ChatAnthropic(
                model=model_name,
                anthropic_api_key=anthropic_api_key,
                temperature=temperature,
            )
        else:
            from langchain_google_genai import ChatGoogleGenerativeAI
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key:
                raise ValueError("GOOGLE_API_KEY not found for ChatGoogleGenerativeAI.")
            llm_instance = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=google_api_key,
                temperature=temperature,
            )
        current_logger.info(f"LLM instance created ({provider}): {model_name}")

        system_prompt = agent_config_dict.get('system_prompt')
        if not system_prompt:
            raise ValueError("'system_prompt' is missing in agent_config_dict.")

        current_logger.debug(f"System prompt for agent (first 200 chars): {system_prompt[:200]}")

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        if not hasattr(llm_instance, 'bind_tools'):
             raise AttributeError("The configured LLM instance does not support .bind_tools() which is needed for function calling agent.")  # noqa: E501
        llm_with_tools = llm_instance.bind_tools(tools, tool_choice="auto")

        agent_runnable = (
            RunnablePassthrough.assign(
                agent_scratchpad=lambda x: format_to_tool_messages(
                    preprocess_intermediate_steps(x.get("intermediate_steps", []))
                )
            )
            | prompt
            | llm_with_tools
            | ToolsAgentOutputParser()
        )

        instance = cls(
            agent=agent_runnable,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True
        )
        return instance

    async def ainvoke(self, input: Dict[str, Any], config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:  # noqa: E501
        if "chat_history" not in input:
             input["chat_history"] = []

        return await super().ainvoke(input, config, **kwargs)

# Helper function get_customizable_agent_executor might be reviewed later for redundancy
# if agent_loader.load_agent_executor is the sole and sufficient entry point.
# For now, keeping it but noting its dependency on the removed AgentConfig Pydantic model.
def get_customizable_agent_executor(
        agent_config_obj: Union[Dict[str, Any], Any],
        user_id_for_agent: str,
        session_id_for_agent: str,
        loaded_tools: List[BaseTool],
        logger_to_use: Optional[logging.Logger] = None
    ) -> CustomizableAgentExecutor:

    agent_config_data_dict: Dict[str, Any]
    if isinstance(agent_config_obj, dict):
        agent_config_data_dict = agent_config_obj
    else:
        logger_to_use_effective = logger_to_use if logger_to_use else logger
        logger_to_use_effective.error(f"get_customizable_agent_executor received non-dict agent_config_obj of type {type(agent_config_obj)}. This is deprecated. Expecting a dictionary.")  # noqa: E501
        if not hasattr(agent_config_obj, 'get'):
             raise TypeError(f"agent_config_obj must be a dictionary, got {type(agent_config_obj)}")
        agent_config_data_dict = agent_config_obj

    return CustomizableAgentExecutor.from_agent_config(
        agent_config_dict=agent_config_data_dict,
        tools=loaded_tools,
        user_id=user_id_for_agent,
        session_id=session_id_for_agent,
        logger_instance=logger_to_use
    )
