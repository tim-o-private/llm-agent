import asyncio # Ensure asyncio is imported at the module level
import logging # Ensure logging is imported at the module level
from typing import Any, List, Tuple, Dict, Optional, Callable, Union
from langchain_core.agents import AgentAction, AgentFinish
from langchain.agents import BaseSingleActionAgent
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import BasePromptTemplate # For type hinting if needed
from langchain_core.tools import BaseTool
from langchain_core.callbacks import BaseCallbackManager
from pydantic import BaseModel, Field # Ensure BaseModel is imported for model_config

# Assuming PromptManagerService is in src.core.prompting
# Adjust import path as necessary based on your project structure
from core.prompting.prompt_manager import PromptManagerService 

class CustomizableAgent(BaseSingleActionAgent):
    llm: BaseLanguageModel
    tools: List[BaseTool]
    base_prompt_template: Any # Can be a string, or a Langchain PromptTemplate object
    prompt_manager: Optional[PromptManagerService] # Allow PromptManagerService to be None
    agent_name: str
    user_id: Optional[str] # Allow user_id to be None for CLI context
    # Output parser is implicitly part of how LLM output is handled or can be explicit

    # For Pydantic v2, model_config is a class attribute dictionary
    model_config = {
        'arbitrary_types_allowed': True
    }

    def __init__(
        self,
        llm: BaseLanguageModel,
        tools: List[BaseTool],
        base_prompt_template: Any, # e.g. a string path to a template or the template itself
        prompt_manager: Optional[PromptManagerService], # Updated type hint
        agent_name: str,
        user_id: Optional[str], # Updated type hint
        **kwargs: Any,
    ):
        # Pass all declared fields explicitly to super's kwargs for Pydantic validation
        # if BaseSingleActionAgent or its Pydantic ancestor expects them in the data dict.
        init_kwargs = {
            'llm': llm,
            'tools': tools,
            'base_prompt_template': base_prompt_template,
            'prompt_manager': prompt_manager,
            'agent_name': agent_name,
            'user_id': user_id,
            **kwargs  # Include any other kwargs passed through
        }
        super().__init__(**init_kwargs)
        # Assignments to self can remain as they are, as Pydantic v2 often validates
        # during __init__ based on the data passed to it, then attributes are set.
        # If super().__init__ already sets them via Pydantic model_post_init or similar,
        # these direct assignments might be redundant but usually harmless.
        self.llm = llm
        self.tools = tools
        self.base_prompt_template = base_prompt_template
        self.prompt_manager = prompt_manager
        self.agent_name = agent_name
        self.user_id = user_id

    @property
    def input_keys(self) -> List[str]:
        # Define based on what your agent expects. Usually 'input' and 'chat_history'.
        # agent_scratchpad is an intermediate step, typically handled by AgentExecutor.
        return ["input", "chat_history"] # Removed "agent_scratchpad"

    async def _construct_prompt_with_customizations(self, intermediate_steps: List[Tuple[AgentAction, str]], **kwargs: Any) -> str:
        """Constructs the full prompt including fetched customizations."""
        raw_base_prompt = str(self.base_prompt_template)
        applied_prompt = raw_base_prompt
        custom_instructions_str = ""

        # 2. Fetch customizations only if prompt_manager is available
        if self.prompt_manager and self.user_id: # Also ensure user_id is present for fetching
            customizations = await self.prompt_manager.get_customizations(agent_name=self.agent_name)
            for cust in customizations:
                if cust.get("customization_type") == "instruction_set" and cust.get("is_active", False):
                    content = cust.get("content", {})
                    if isinstance(content, dict) and "instructions" in content and isinstance(content["instructions"], list):
                        for instruction in content["instructions"]:
                            custom_instructions_str += f"- {instruction}\n"
        elif self.prompt_manager and not self.user_id:
            # Log if prompt_manager is present but user_id is missing for customization fetching
            # This scenario might be hit if agent_loader changes only remove PMS check but not user_id check for error
            logger = logging.getLogger(__name__) # Add import if not already present at top of file
            logger.warning(f"PromptManager available for {self.agent_name} but no user_id; cannot fetch dynamic customizations.")

        # 3. Apply customizations to the base prompt
        if custom_instructions_str:
            if "{{custom_instructions}}" in applied_prompt:
                applied_prompt = applied_prompt.replace("{{custom_instructions}}", custom_instructions_str)
            else:
                # Or prepend/append if no placeholder found
                applied_prompt = f"Custom Instructions:\n{custom_instructions_str}\n---\n{applied_prompt}"

        # 4. Format tools and intermediate steps (agent_scratchpad)
        # This is standard Langchain agent stuff. The exact formatting depends on the LLM.
        # For simplicity, this part is highly conceptual here.
        # A real implementation would use Langchain's prompt formatting utilities.
        
        # kwargs already contains input, chat_history from AgentExecutor
        # intermediate_steps is the agent_scratchpad
        
        # Simplified formatting for agent_scratchpad (intermediate_steps)
        scratchpad = ""
        for action, observation in intermediate_steps:
            scratchpad += f"Thought: {action.log}\nAction: {action.tool}\nAction Input: {action.tool_input}\nObservation: {observation}\n"

        # Example: Fill placeholders in the prompt string
        # This is a simplified example. A proper Langchain PromptTemplate would handle this better.
        final_prompt = applied_prompt
        if "{{input}}" in final_prompt and "input" in kwargs:
            final_prompt = final_prompt.replace("{{input}}", str(kwargs["input"])) 
        if "{{chat_history}}" in final_prompt and "chat_history" in kwargs:
            # chat_history is usually a list of BaseMessage objects. Convert to string.
            history_str = "\n".join([f"{msg.type}: {msg.content}" for msg in kwargs["chat_history"]])
            final_prompt = final_prompt.replace("{{chat_history}}", history_str)
        if "{{agent_scratchpad}}" in final_prompt:
            final_prompt = final_prompt.replace("{{agent_scratchpad}}", scratchpad)
        if "{{tools}}" in final_prompt:
            tools_description = "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools])
            final_prompt = final_prompt.replace("{{tools}}", tools_description)
        if "{{tool_names}}" in final_prompt:
            tool_names_str = ", ".join([tool.name for tool in self.tools])
            final_prompt = final_prompt.replace("{{tool_names}}", tool_names_str)
            
        # print(f"--- FINAL PROMPT ---\n{final_prompt}\n--------------------")
        return final_prompt

    async def aplan(
        self, intermediate_steps: List[Tuple[AgentAction, str]], **kwargs: Any
    ) -> Union[AgentAction, AgentFinish]:
        """Given input, decided what to do."""
        full_prompt = await self._construct_prompt_with_customizations(intermediate_steps, **kwargs)
        
        # Call LLM
        # The response from the LLM needs to be parsed into AgentAction or AgentFinish
        # This parsing logic is critical and depends on the LLM and expected output format.
        # Langchain often has specific output parsers for different agent types (e.g., ReAct, OpenAI Functions).
        # For a BaseSingleActionAgent, you need to implement this parsing logic.
        
        # llm_output = await self.llm.apredict(text=full_prompt, stop=["\nObservation:"]) # Example stop sequence
        # Use ainvoke instead of apredict as per deprecation warnings and potentially better async handling
        llm_response = await self.llm.ainvoke(input=full_prompt, stop=["\nObservation:"]) # Ensure correct params for ainvoke
        llm_output = llm_response.content # Assuming .content holds the string output, adjust if model returns structured output
        
        # print(f"--- LLM OUTPUT ---\n{llm_output}\n------------------")

        # Implement parsing of llm_output into AgentAction or AgentFinish
        # This is a placeholder for actual parsing logic.
        # A common pattern is to look for "Action:" and "Action Input:" or a final answer.
        if "Final Answer:" in llm_output:
            answer = llm_output.split("Final Answer:")[-1].strip()
            return AgentFinish({"output": answer}, log=llm_output)
        
        # Regex to find action and action input
        import re
        action_match = re.search(r"Action:\s*(.*?)\nAction Input:\s*(.*)", llm_output, re.DOTALL)
        if action_match:
            action_tool = action_match.group(1).strip()
            action_input = action_match.group(2).strip()
            return AgentAction(tool=action_tool, tool_input=action_input, log=llm_output)
        
        # If no clear action or final answer, might be a malformed response or direct reply
        # Depending on the agent's design, you might return AgentFinish or try to re-prompt/error.
        # For now, assume it's a direct answer if no specific action format is found.
        # print(f"Warning: Could not parse LLM output for action. Returning as direct answer: {llm_output}")
        return AgentFinish({"output": llm_output}, log=llm_output) # Fallback

    # Synchronous version that wraps the asynchronous one
    def plan(
        self, intermediate_steps: List[Tuple[AgentAction, str]], **kwargs: Any
    ) -> Union[AgentAction, AgentFinish]:
        """Synchronous wrapper for aplan."""
        try:
            # Try to run directly, assuming this is called from a non-async context primarily
            return asyncio.run(self.aplan(intermediate_steps, **kwargs))
        except RuntimeError as e:
            e_str = str(e).lower() # For case-insensitive matching
            # Check for specific RuntimeError messages indicating asyncio.run() issues
            is_problematic_run_error = False
            if "cannot be called from a running event loop" in e_str or \
               "no current event loop" in e_str or \
               "cannot run new tasks" in e_str or \
               "event loop is closed" in e_str:  # Ensure this condition is checked
                is_problematic_run_error = True

            if is_problematic_run_error:
                # Fallback: create and manage a new event loop
                # This is a more robust way for sync-over-async when asyncio.run() fails.
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    result = new_loop.run_until_complete(self.aplan(intermediate_steps, **kwargs))
                finally:
                    new_loop.close()
                return result
            else:
                # If it's a different RuntimeError, re-raise it.
                raise

    # Required for Langchain if you don't implement _plan_sync
    @property
    def return_stopped_response(self) -> bool:
        return False # Set to True if the LLM may commonly return a stop sequence that should be treated as a normal response. 