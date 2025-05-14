import os
import logging
import yaml
from typing import List, Dict, Any, Optional, Type
from collections import defaultdict

from langchain.agents import AgentExecutor, create_tool_calling_agent, create_react_agent
from langchain_core.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.agent_toolkits.file_management.toolkit import FileManagementToolkit
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.memory import ConversationBufferMemory
# Added JSON import for potential future use, though not strictly needed for this change
import json 

from utils.config_loader import ConfigLoader
# from core.context_manager import ContextManager # Not currently used
from utils.path_helpers import (
    get_agent_data_dir, get_agent_config_dir, get_agent_config_file_path, 
    get_task_list_dir, get_memory_bank_dir, get_base_path, # Assuming get_agent_config_dir and get_task_list_dir are also here implicitly or imported elsewhere
)
# Remove the incorrect import
# from utils.file_parser import load_prompt_template_from_file 

# Type hint for callback handlers if needed
# Remove BaseCallbackHandler import if no longer needed
# from langchain_core.callbacks.base import BaseCallbackHandler 

logger = logging.getLogger(__name__)

# Mapping from symbolic scope names to path helper functions
SCOPE_TO_PATH_FUNC = {
    "AGENT_DATA": get_agent_data_dir,
    "AGENT_CONFIG": get_agent_config_dir,
    "TASK_LIST": get_task_list_dir,
    "MEMORY_BANK": lambda _agent_name, config, user_id=None: get_memory_bank_dir(config), # Use lambda to ignore agent_name
    "PROJECT_ROOT": lambda _agent_name, config, user_id=None: get_base_path(), # Project root doesn't depend on agent name
}

# --- Tool Loading --- 

TOOLKIT_MAPPING: Dict[str, Type[BaseTool]] = {
    "FileManagementToolkit": FileManagementToolkit,
    # Add other toolkits here as needed
}

SCOPE_MAPPING: Dict[str, callable] = {
    "PROJECT_ROOT": lambda config_loader=None, agent_name=None, user_id=None: get_base_path(), 
    "AGENT_DATA": lambda config_loader, agent_name, user_id=None: get_agent_data_dir(agent_name, config_loader, user_id=user_id), 
    "MEMORY_BANK": lambda config_loader, agent_name=None, user_id=None: get_memory_bank_dir(config_loader),
    "AGENT_CONFIG": lambda config_loader, agent_name, user_id=None: get_agent_config_dir(agent_name, config_loader), 
    "TASK_LIST": lambda config_loader, agent_name=None, user_id=None: get_task_list_dir(agent_name, config_loader) if agent_name else get_task_list_dir(None, config_loader) # Simplified example, might need better handling for optional agent_name
}

def load_tools(
    agent_name: str,
    tools_config: Dict[str, Dict[str, Any]], 
    config_loader: ConfigLoader,
    user_id: Optional[str] = None # Add user_id here if tools need user-specific paths
) -> List[BaseTool]:
    """Loads and configures tools based on agent's tools_config."""
    loaded_tools: List[BaseTool] = []
    # Group tool configs by the required toolkit instance (class_name, scope_symbol)
    required_instance_tools = defaultdict(lambda: {'configs': [], 'original_names': set()})

    if not tools_config:
        logger.warning(f"No tools_config found for agent '{agent_name}'. No tools will be loaded.")
        return []

    # First pass: Group configurations and collect required original names per instance
    for tool_name, tool_details in tools_config.items():
        toolkit_key = tool_details.get('toolkit')
        scope_key = tool_details.get('scope')
        original_name = tool_details.get('original_name')

        if not all([tool_name, toolkit_key, scope_key, original_name]):
            logger.error(f"Skipping invalid tool entry '{tool_name}' in {agent_name} config: {tool_details}. Missing required fields (toolkit, scope, original_name) or empty tool name key.")
            continue
        
        instance_key = (toolkit_key, scope_key)
        required_instance_tools[instance_key]['configs'].append((tool_name, tool_details))
        required_instance_tools[instance_key]['original_names'].add(original_name)

    # Second pass: Instantiate toolkits and configure tools
    toolkit_instances = {}
    for instance_key, instance_data in required_instance_tools.items():
        toolkit_key, scope_key = instance_key
        original_names_list = list(instance_data['original_names'])
        configs = instance_data['configs']

        # --- Get Scope Path --- 
        scope_func = SCOPE_MAPPING.get(scope_key)
        if not scope_func:
            # This check might be redundant if the first pass catches it, but safe to keep
            logger.error(f"Invalid scope '{scope_key}' for toolkit '{toolkit_key}' in agent '{agent_name}'. Available scopes: {list(SCOPE_MAPPING.keys())}")
            continue
        
        scope_path = "unknown"
        try:
            # Pass necessary arguments based on scope function requirements
            if scope_key == "AGENT_DATA":
                scope_path = scope_func(config_loader=config_loader, agent_name=agent_name, user_id=user_id)
            elif scope_key == "AGENT_CONFIG": # Handle AGENT_CONFIG path
                 scope_path = scope_func(config_loader=config_loader, agent_name=agent_name)
            elif scope_key == "TASK_LIST":    # Handle TASK_LIST path (might not need agent_name? depends on helper)
                 # Assuming get_task_list_dir might only need config_loader or be global
                 try:
                     scope_path = scope_func(config_loader=config_loader)
                 except TypeError:
                     try: 
                         scope_path = scope_func(agent_name=agent_name, config_loader=config_loader)
                     except TypeError:
                          scope_path = scope_func() # Try calling with no args
            elif scope_key == "MEMORY_BANK":
                scope_path = scope_func(config_loader=config_loader)
            else: # PROJECT_ROOT 
                scope_path = scope_func()
            
            # Ensure directory exists if it's supposed to be writable (optional, depends on tool use)
            # os.makedirs(scope_path, exist_ok=True) 
        except Exception as e:
            logger.error(f"Error getting scope path for '{scope_key}' for toolkit '{toolkit_key}' in agent '{agent_name}': {e}", exc_info=True)
            continue

        # --- Get Toolkit Class --- 
        toolkit_class = TOOLKIT_MAPPING.get(toolkit_key)
        if not toolkit_class:
            logger.error(f"Invalid toolkit '{toolkit_key}' for scope '{scope_key}' in agent '{agent_name}'. Available toolkits: {list(TOOLKIT_MAPPING.keys())}")
            continue

        # --- Instantiate Toolkit --- 
        toolkit_instance = None
        try:
            # Instantiate the toolkit with the determined root_dir and ALL required tools for this instance
            if toolkit_key == "FileManagementToolkit":
                toolkit_instance = toolkit_class(root_dir=scope_path, selected_tools=original_names_list)
                logger.info(f"Instantiated toolkit '{toolkit_key}' for scope '{scope_key}' ({scope_path}) requesting tools: {original_names_list}")
            else:
                # Fallback for other toolkits - might need refinement based on their constructors
                toolkit_instance = toolkit_class() 
                logger.warning(f"Toolkit '{toolkit_key}' instantiated without specific scope/tool selection logic. Review if needed.")
            toolkit_instances[instance_key] = toolkit_instance
        except Exception as e:
            logger.error(f"Failed to instantiate toolkit '{toolkit_key}' for scope '{scope_key}' with tools {original_names_list}: {e}", exc_info=True)
            continue # Skip processing tools for this failed instance

        # --- Configure and Add Individual Tools from this Instance --- 
        if not toolkit_instance:
            continue # Skip if instantiation failed
            
        try:
            available_tools_map = {t.name: t for t in toolkit_instance.get_tools()}
        except Exception as e:
             logger.error(f"Failed to get tools from toolkit instance {toolkit_key}/{scope_key}: {e}", exc_info=True)
             continue # Skip this instance if get_tools fails

        for tool_name, tool_details in configs:
            original_name = tool_details.get('original_name')
            description_override = tool_details.get('description')
            
            base_tool = available_tools_map.get(original_name)
            if not base_tool:
                logger.error(f"Tool '{original_name}' not found within instantiated toolkit '{toolkit_key}' for scope '{scope_key}'. Available: {list(available_tools_map.keys())}")
                continue # Skip this specific tool configuration
            
            # Apply Customizations (Name, Description)
            # IMPORTANT: Assume BaseTool properties (name, description) are mutable. If not, need to wrap/recreate.
            try:
                final_tool = base_tool # For now, modify in place
                final_tool.name = tool_name # Override the name
                
                # Apply description override ONLY if it exists AND does NOT contain the placeholder
                if description_override and '{scope_path}' not in description_override:
                     logger.debug(f"Applying description override for tool '{tool_name}' (without scope path).")
                     final_tool.description = description_override
                elif description_override:
                     logger.debug(f"Skipping description override for tool '{tool_name}' because it contains '{{scope_path}}' and formatting is disabled.")
                # else: no description override specified in config

                loaded_tools.append(final_tool)
                logger.info(f"Configured tool '{final_tool.name}' (originally '{original_name}') from '{toolkit_key}' scope '{scope_key}'.")
            except Exception as e:
                 logger.error(f"Error applying configuration to tool '{tool_name}' (from '{original_name}'): {e}", exc_info=True)

    return loaded_tools

# --- Agent Loading --- 

def load_agent_executor(
    agent_name: str,
    config_loader: ConfigLoader,
    log_level: int, # Keep log level for potential LLM/internal use
    memory: ConversationBufferMemory,
    user_id: Optional[str] = None # Added user_id parameter
) -> AgentExecutor:
    """Loads agent configuration, LLM, prompt, tools, and creates an AgentExecutor."""
    logger.info(f"Loading agent executor for: {agent_name}{f' (User: {user_id})' if user_id else ''}")

    # --- 1. Load Agent Configuration --- 
    try:
        # Construct the path to the agent's config file
        agent_config_path = get_agent_config_file_path(agent_name, config_loader)
        if not os.path.isfile(agent_config_path):
            raise FileNotFoundError(f"Agent configuration file not found at: {agent_config_path}")
        
        # Load the agent-specific YAML file
        with open(agent_config_path, 'r') as f:
            agent_config = yaml.safe_load(f)
        if not agent_config: # Handle empty or invalid YAML
             raise ValueError(f"Agent configuration file is empty or invalid: {agent_config_path}")
        
        logger.debug(f"Loaded agent config for '{agent_name}': {agent_config}")
    except FileNotFoundError:
        logger.error(f"Agent configuration file not found for agent: {agent_name}")
        raise
    except Exception as e:
        logger.error(f"Error loading agent configuration for '{agent_name}': {e}", exc_info=True)
        raise ValueError(f"Invalid configuration for agent '{agent_name}'.")

    # --- 2. Load LLM Configuration --- 
    try:
        llm_config = agent_config.get('llm', {}) # Get LLM specific settings
        global_llm_config = config_loader.get('llm', {}) # Get global LLM settings
        
        # Merge global and agent-specific LLM settings (agent overrides global)
        merged_llm_config = {**global_llm_config, **llm_config} 
        
        model_name = merged_llm_config.get('model', 'gemini-pro') # Default if not specified anywhere
        temperature = float(merged_llm_config.get('temperature', 0.7))
        api_key = config_loader.get('GOOGLE_API_KEY') # Get from global/env

        if not api_key:
            raise ValueError("Google API Key (GOOGLE_API_KEY) not found in configuration.")
            
        # Add safety settings if specified in agent config
        safety_settings = merged_llm_config.get('safety_settings')
        
        llm_params = {
            'model': model_name,
            'google_api_key': api_key,
            'temperature': temperature,
            # 'convert_system_message_to_human': True # REMOVED - Deprecated
        }
        if safety_settings:
            # TODO: Convert string keys/values from YAML to HarmCategory/HarmBlockThreshold enums
            # This requires importing them and having a mapping
            # Example: safety_settings_enum = {HarmCategory[k]: HarmBlockThreshold[v] for k, v in safety_settings.items()}
            # llm_params['safety_settings'] = safety_settings_enum
            logger.warning("Safety settings loading from config not fully implemented yet (enum conversion needed). Ignoring safety_settings for now.")
            # For now, just pass the raw dict, might error or be ignored by langchain
            # llm_params['safety_settings'] = safety_settings

        llm = ChatGoogleGenerativeAI(**llm_params)
        logger.info(f"Initialized LLM: {model_name} with temp={temperature}")
        # TODO: Set log level for LLM if possible/needed via langchain settings?

    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Error processing LLM configuration for '{agent_name}': {e}", exc_info=True)
        raise ValueError(f"Invalid LLM configuration for agent '{agent_name}'.")
    except Exception as e:
         logger.error(f"Unexpected error initializing LLM for '{agent_name}': {e}", exc_info=True)
         raise

    # --- 3. Load Prompt Template --- 
    # Check for direct system_prompt key first
    if 'system_prompt' in agent_config:
        prompt_template_str = agent_config['system_prompt']
        logger.info(f"Using direct 'system_prompt' key from config for agent '{agent_name}'.")
    else:
        # Fallback to checking the 'prompt' key (string or dict)
        prompt_config = agent_config.get('prompt', {})
        prompt_template_str = None

        if isinstance(prompt_config, str): # Simple case: prompt is just a filename
            prompt_file = prompt_config
            # Construct full path relative to agent config dir
            agent_config_dir = get_agent_config_dir(agent_name, config_loader)
            prompt_file_path = os.path.join(agent_config_dir, prompt_file)
            try:
                with open(prompt_file_path, 'r') as f:
                    prompt_template_str = f.read()
                logger.info(f"Loaded prompt template from file: {prompt_file_path}")
            except FileNotFoundError:
                logger.error(f"Prompt template file '{prompt_file_path}' not found for agent '{agent_name}'.")
                raise
            except Exception as e:
                logger.error(f"Error loading prompt template from '{prompt_file_path}' for agent '{agent_name}': {e}", exc_info=True)
                raise ValueError(f"Invalid prompt file '{prompt_file_path}' for agent '{agent_name}'.")
        elif isinstance(prompt_config, dict): # Structured prompt config
            # Check for inline template first
            if 'template' in prompt_config:
                prompt_template_str = prompt_config['template']
                logger.info(f"Using inline prompt template from config for agent '{agent_name}'.")
                # TODO: How to get input_variables if specified inline?
                # Maybe require explicit input_variables list in this case?
                # input_variables = prompt_config.get('input_variables', []) 
            # Fallback to system_message_file
            elif 'system_message_file' in prompt_config:
                prompt_file = prompt_config.get('system_message_file')
                # Construct full path relative to agent config dir
                agent_config_dir = get_agent_config_dir(agent_name, config_loader)
                prompt_file_path = os.path.join(agent_config_dir, prompt_file)
                try:
                    with open(prompt_file_path, 'r') as f:
                        prompt_template_str = f.read()
                    logger.info(f"Loaded prompt template from file specified in config: {prompt_file_path}")
                except FileNotFoundError:
                    logger.error(f"Prompt template file '{prompt_file_path}' (from config) not found for agent '{agent_name}'.")
                    raise
                except Exception as e:
                    logger.error(f"Error loading prompt template from '{prompt_file_path}' (from config) for agent '{agent_name}': {e}", exc_info=True)
                    raise ValueError(f"Invalid prompt file '{prompt_file_path}' (from config) for agent '{agent_name}'.")
            else:
                # Neither inline template nor system_message_file found in dict
                logger.error(f"Invalid prompt configuration for agent '{agent_name}'. Neither 'system_prompt' key nor valid 'prompt' config (string filename or dict with 'template'/'system_message_file') found.")
                raise ValueError(f"Invalid prompt configuration for agent '{agent_name}'.")
        else:
            logger.error(f"Invalid 'prompt' type in config for agent '{agent_name}': {type(prompt_config)}. Expected string or dict.")
            raise ValueError(f"Invalid prompt configuration type for agent '{agent_name}'.")

    # --- Load Previous Session Summary (USER-SPECIFIC) --- 
    # Use the MODIFIED get_agent_data_dir with user_id
    agent_data_dir = get_agent_data_dir(agent_name, config_loader, user_id=user_id)
    summary_file_path = os.path.join(agent_data_dir, 'session_log.md')
    previous_summary = ""
    try:
        if os.path.exists(summary_file_path):
            # Ensure the directory for user-specific summary is created if it doesn't exist
            # This should ideally be handled when saving, but good to ensure read doesn't fail if dir is missing.
            os.makedirs(os.path.dirname(summary_file_path), exist_ok=True)
            with open(summary_file_path, 'r') as f:
                previous_summary = f.read()
            if previous_summary:
                logger.info(f"Loaded previous session summary for user '{user_id}' from {summary_file_path}")
                prompt_template_str = f"PREVIOUS SESSION SUMMARY FOR THIS USER:\n{previous_summary}\n\n---\n\nCURRENT SESSION PROMPT:\n{prompt_template_str}"
    except IOError as e:
        logger.warning(f"Could not read summary file {summary_file_path} for user '{user_id}': {e}")
    except Exception as e:
        logger.error(f"Unexpected error loading summary from {summary_file_path} for user '{user_id}': {e}", exc_info=True)

    # --- Create PromptTemplate Instance --- 
    try:
        if not prompt_template_str:
            raise ValueError("Prompt template string could not be loaded or determined.")
        
        # Revert to creating a ChatPromptTemplate suitable for tool calling agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_template_str), # Use the loaded content as system message
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
    except Exception as e:
         logger.error(f"Failed to create PromptTemplate for agent '{agent_name}': {e}", exc_info=True)
         raise ValueError(f"Invalid prompt template structure for agent '{agent_name}'.")

    # --- 4. Load Tools --- 
    tools_config = agent_config.get('tools_config', {}) # Restore config usage
    
    tools = load_tools(agent_name, tools_config, config_loader, user_id=user_id)
    logger.info(f"Loaded {len(tools)} tools for agent '{agent_name}'{f' (User: {user_id})' if user_id else ''}: {[t.name for t in tools]}")

    # --- 5. Create Agent --- 
    try:
        # Switch back to create_tool_calling_agent
        agent = create_tool_calling_agent(llm, tools, prompt)
        logger.debug(f"Created tool-calling agent for '{agent_name}'")
    except Exception as e:
        logger.error(f"Failed to create tool-calling agent for '{agent_name}': {e}", exc_info=True)
        raise RuntimeError(f"Could not create agent '{agent_name}'.")

    # --- 6. Create Agent Executor --- 
    try:
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=memory,
            verbose=False, # Disable LangChain AgentExecutor verbose output
            handle_parsing_errors=True, # Add basic handling for parsing errors
            max_iterations=agent_config.get('max_iterations', 15), # Configurable max iterations
        )
        logger.info(f"Created Agent Executor for '{agent_name}'{f' (User: {user_id})' if user_id else ''}")
    except Exception as e:
        logger.error(f"Failed to create Agent Executor for '{agent_name}': {e}", exc_info=True)
        raise RuntimeError(f"Could not create agent executor for '{agent_name}'.")

    return agent_executor
