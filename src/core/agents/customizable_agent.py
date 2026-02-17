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
# Removed: from core.prompting.prompt_manager import PromptManagerService # Not used by executor directly if CustomizableAgent is removed

logger = get_logger(__name__)

# Helper function for processing scratchpad data
# Ensure observations are not None or empty, as this can cause API errors with Gemini
def preprocess_intermediate_steps(intermediate_steps: List[tuple]) -> List[tuple]:
    processed_steps = []
    for i, (action, observation) in enumerate(intermediate_steps):
        logger.debug(f"[preprocess_intermediate_steps] Step {i} - Original Action: {action}")
        logger.debug(f"[preprocess_intermediate_steps] Step {i} - Original Observation: {observation!r}") # Added !r for more detail

        processed_observation = observation
        if observation is None or (isinstance(observation, str) and not observation.strip()):
            # Using a clear placeholder for empty or None observations
            processed_observation = "(Tool returned no output or an empty string)"
            logger.warning(f"[preprocess_intermediate_steps] Step {i} - Observation was None or empty, replaced with placeholder. Original: {observation!r}")

        logger.debug(f"[preprocess_intermediate_steps] Step {i} - Processed Observation: {processed_observation!r}")
        processed_steps.append((action, processed_observation))
    return processed_steps

class CustomizableAgentExecutor(AgentExecutor):
    # ... (existing class structure if any) ...

    @classmethod
    def from_agent_config(
        cls,
        agent_config_dict: Dict[str, Any],
        tools: List[BaseTool],
        user_id: str, # Retained, though not directly used in this method after CustomizableAgent removal, agent_loader uses it.
        session_id: str, # Retained, for consistency, though not directly used here.
        ltm_notes_content: Optional[str] = None,
        explicit_custom_instructions_dict: Optional[Dict[str, Any]] = None,
        logger_instance: Optional[logging.Logger] = None,
    ) -> "CustomizableAgentExecutor":

        current_logger = logger_instance if logger_instance else logger
        agent_name_from_config = agent_config_dict.get('agent_name', 'UnknownAgent')
        current_logger.info(f"Creating CustomizableAgentExecutor for '{agent_name_from_config}' from config dictionary.")

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

        base_prompt_str = agent_config_dict.get('system_prompt')
        if not base_prompt_str:
            raise ValueError("'system_prompt' is missing in agent_config_dict.")

        final_system_message_content = base_prompt_str

        if ltm_notes_content:
            ltm_section = f"\n\n--- BEGIN LONG-TERM MEMORY NOTES ---\n{ltm_notes_content}\n--- END LONG-TERM MEMORY NOTES ---"
            if "{{ltm_notes}}" in final_system_message_content:
                final_system_message_content = final_system_message_content.replace("{{ltm_notes}}", ltm_section)
            else:
                final_system_message_content = ltm_section + "\n\n" + final_system_message_content
        elif "{{ltm_notes}}" in final_system_message_content:
             final_system_message_content = final_system_message_content.replace("{{ltm_notes}}", "(No LTM notes for this session.)")

        if explicit_custom_instructions_dict:
            instr_parts = [f"{k.replace('_',' ').title()}: {v}" for k,v in explicit_custom_instructions_dict.items()]
            instr_block = "\n--- BEGIN CUSTOM INSTRUCTIONS ---\n" + "\n".join(instr_parts) + "\n--- END CUSTOM INSTRUCTIONS ---"
            if "{{custom_instructions}}" in final_system_message_content:
                final_system_message_content = final_system_message_content.replace("{{custom_instructions}}", instr_block)
            else:
                final_system_message_content += "\n" + instr_block
        elif "{{custom_instructions}}" in final_system_message_content:
             final_system_message_content = final_system_message_content.replace("{{custom_instructions}}", "(No explicit custom instructions for this session.)")

        current_logger.debug(f"Final system message content for agent: \n{final_system_message_content}")

        prompt = ChatPromptTemplate.from_messages([
            ("system", final_system_message_content),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        if not hasattr(llm_instance, 'bind_tools'):
             raise AttributeError("The configured LLM instance does not support .bind_tools() which is needed for function calling agent.")
        llm_with_tools = llm_instance.bind_tools(tools)

        agent_runnable = (
            RunnablePassthrough.assign(
                agent_scratchpad=lambda x: format_to_tool_messages(
                    preprocess_intermediate_steps(x.get("intermediate_steps", []))
                )
            )
            | prompt
            | llm_with_tools
            | ToolsAgentOutputParser() # User's preferred parser
        )

        return cls(
            agent=agent_runnable,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True
        )

    async def ainvoke(self, input: Dict[str, Any], config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        if "chat_history" not in input:
             input["chat_history"] = []

        return await super().ainvoke(input, config, **kwargs)

# Helper function get_customizable_agent_executor might be reviewed later for redundancy
# if agent_loader.load_agent_executor is the sole and sufficient entry point.
# For now, keeping it but noting its dependency on the removed AgentConfig Pydantic model.
def get_customizable_agent_executor(
        agent_config_obj: Union[Dict[str, Any], Any], # Modified to accept Dict or any (original was 'AgentConfig')
        user_id_for_agent: str,
        session_id_for_agent: str,
        ltm_notes: Optional[str],
        custom_instructions: Optional[Dict[str, Any]],
        loaded_tools: List[BaseTool],
        logger_to_use: Optional[logging.Logger] = None
    ) -> CustomizableAgentExecutor:

    agent_config_data_dict: Dict[str, Any]
    if isinstance(agent_config_obj, dict):
        agent_config_data_dict = agent_config_obj
    else:
        logger_to_use_effective = logger_to_use if logger_to_use else logger
        # The original AgentConfig Pydantic model is removed. This path indicates a caller error if not a dict.
        logger_to_use_effective.error(f"get_customizable_agent_executor received non-dict agent_config_obj of type {type(agent_config_obj)}. This is deprecated. Expecting a dictionary.")
        # Attempt to proceed if it's somehow dict-like, otherwise this will fail in from_agent_config.
        # This is for minimal disruption; ideally, callers should be updated.
        if not hasattr(agent_config_obj, 'get'):
             raise TypeError(f"agent_config_obj must be a dictionary, got {type(agent_config_obj)}")
        agent_config_data_dict = agent_config_obj # This is risky, assumes it's a dict-like object.

    return CustomizableAgentExecutor.from_agent_config(
        agent_config_dict=agent_config_data_dict,
        tools=loaded_tools,
        user_id=user_id_for_agent,
        session_id=session_id_for_agent,
        ltm_notes_content=ltm_notes,
        explicit_custom_instructions_dict=custom_instructions,
        logger_instance=logger_to_use
    )
