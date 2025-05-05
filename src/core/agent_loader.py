import os
import logging
import yaml
from typing import List, Dict, Any
from collections import defaultdict

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.agent_toolkits.file_management.toolkit import FileManagementToolkit
from langchain.memory import ConversationBufferMemory

from utils.config_loader import ConfigLoader
from core.context_manager import ContextManager
from utils.path_helpers import (
    get_agent_data_dir, get_agent_config_dir, get_agent_config_file_path, 
    get_task_list_dir, get_memory_bank_dir, get_base_path
)

logger = logging.getLogger(__name__)

# Mapping from symbolic scope names to path helper functions
SCOPE_TO_PATH_FUNC = {
    "AGENT_DATA": get_agent_data_dir,
    "AGENT_CONFIG": get_agent_config_dir,
    "TASK_LIST": get_task_list_dir,
    "MEMORY_BANK": lambda _agent_name, config: get_memory_bank_dir(config), # Use lambda to ignore agent_name
    "PROJECT_ROOT": lambda _agent_name, config: get_base_path(), # Project root doesn't depend on agent name
}

def load_tools(tools_config: Dict[str, Dict[str, Any]], agent_name: str, config_loader: ConfigLoader) -> List[BaseTool]:
    """Loads and configures tool instances based on the tools_config dictionary from agent config."""
    loaded_tools = []
    # Group configs by the toolkit instance they require (toolkit_cls, scope_symbol)
    # This avoids creating the same toolkit multiple times
    toolkit_instances_needed = defaultdict(list)
    for final_tool_name, config in tools_config.items():
        toolkit_cls_name = config.get('toolkit')
        scope_symbol = config.get('scope')
        if not toolkit_cls_name or not scope_symbol:
            logger.warning(f"Skipping tool '{final_tool_name}' due to missing 'toolkit' or 'scope' in config.")
            continue
        # Key by (class name, scope symbol) to group requirements for the same toolkit instance
        instance_key = (toolkit_cls_name, scope_symbol)
        toolkit_instances_needed[instance_key].append((final_tool_name, config))

    # Instantiate toolkits and collect tools
    instantiated_toolkits = {}
    base_tools_map = {}

    for (toolkit_cls_name, scope_symbol), configs_for_instance in toolkit_instances_needed.items():
        logger.debug(f"Processing toolkit instance: {toolkit_cls_name} scoped to {scope_symbol}")
        
        # Get the actual toolkit class (only FileManagementToolkit supported for now)
        if toolkit_cls_name != "FileManagementToolkit":
            logger.warning(f"Unsupported toolkit class '{toolkit_cls_name}' specified for scope {scope_symbol}. Skipping.")
            continue
        toolkit_cls = FileManagementToolkit

        # Resolve the scope symbol to an actual path
        path_func = SCOPE_TO_PATH_FUNC.get(scope_symbol)
        if not path_func:
            logger.warning(f"Unknown scope symbol '{scope_symbol}' for toolkit {toolkit_cls_name}. Skipping.")
            continue
        
        scope_path = "unknown" # Initialize scope_path
        try:
            # The lambda functions now handle the argument mismatch correctly
            # No need for the explicit if scope_symbol == "PROJECT_ROOT" check here anymore
            scope_path = path_func(agent_name, config_loader)
                
            os.makedirs(scope_path, exist_ok=True) # Ensure directory exists
            logger.info(f"Instantiating {toolkit_cls_name} scoped to '{scope_symbol}' ({scope_path})")
        except Exception as e:
            logger.error(f"Error resolving or creating path for scope '{scope_symbol}' (Path: {scope_path}): {e}. Skipping toolkit.")
            continue

        # Determine required original tools for this instance
        # Collect all unique `original_name`s needed from this toolkit instance
        required_original_names = set()
        for _final_tool_name, config in configs_for_instance:
            original_name = config.get('original_name')
            if original_name:
                required_original_names.add(original_name)
            else:
                # If original_name is missing, we can't map it. Log a warning.
                logger.warning(f"Tool config for '{_final_tool_name}' is missing 'original_name'. Cannot load this tool.")
        
        if not required_original_names:
            logger.warning(f"No valid tool configurations with 'original_name' found for {toolkit_cls_name} scoped to {scope_symbol}. Skipping toolkit instance.")
            continue

        # Instantiate the toolkit with the specific tools needed
        try:
            toolkit_instance = toolkit_cls(
                root_dir=scope_path,
                selected_tools=list(required_original_names) # Pass only the needed base tools
            )
            # Store the instance if needed elsewhere, though maybe not necessary
            instantiated_toolkits[(toolkit_cls_name, scope_symbol)] = toolkit_instance
            
            # Get the base tools from the instance and map them by original name
            base_tools = toolkit_instance.get_tools()
            for tool in base_tools:
                # Map by (toolkit_cls_name, scope_symbol, original_tool_name)
                base_tools_map[(toolkit_cls_name, scope_symbol, tool.name)] = tool
                logger.debug(f" Retrieved base tool: {tool.name} from {toolkit_cls_name}/{scope_symbol}")

        except Exception as e:
            logger.error(f"Failed to instantiate or get tools from {toolkit_cls_name} scoped to {scope_path}: {e}")
            # Continue to next toolkit instance if one fails
            continue

    # Configure and add tools to the final list based on the original config
    for final_tool_name, config in tools_config.items():
        toolkit_cls_name = config.get('toolkit')
        scope_symbol = config.get('scope')
        original_name = config.get('original_name')

        # Find the corresponding base tool we retrieved earlier
        base_tool_key = (toolkit_cls_name, scope_symbol, original_name)
        base_tool = base_tools_map.get(base_tool_key)

        if base_tool:
            # Clone or modify the base tool
            # NOTE: Modifying in place might affect other tools if not careful,
            # but LangChain tools are often just dataclasses. Let's modify name/desc directly.
            configured_tool = base_tool # Start with the base tool
            
            # Override name
            configured_tool.name = final_tool_name
            
            # Override description if provided
            if 'description' in config:
                # Format description with scope path if placeholder exists
                scope_path = "unknown" # Default
                path_func = SCOPE_TO_PATH_FUNC.get(scope_symbol)
                if path_func:
                    try:
                        # Call the path_func (lambda handles args) to get path for description
                        scope_path = path_func(agent_name, config_loader)
                    except Exception:
                        pass # Keep default "unknown"
                
                configured_tool.description = config['description'].format(scope_path=scope_path)
            
            logger.debug(f"Adding configured tool: '{configured_tool.name}' (Original: {original_name}, Scope: {scope_symbol})")
            loaded_tools.append(configured_tool)
        else:
            # Log if we couldn't find the base tool (e.g., due to earlier errors)
            if toolkit_cls_name and scope_symbol and original_name: # Only log if config was valid
                logger.warning(f"Could not find base tool for config: {final_tool_name} (Toolkit: {toolkit_cls_name}, Scope: {scope_symbol}, Original: {original_name})")

    logger.info(f"Final loaded tools for agent '{agent_name}': {[tool.name for tool in loaded_tools] if loaded_tools else 'None'}")
    return loaded_tools

def load_agent_executor(agent_name: str, config_loader: ConfigLoader, effective_log_level: int, memory: ConversationBufferMemory) -> AgentExecutor:
    """Loads agent configuration and creates an AgentExecutor integrated with memory."""
    # Determine executor verbosity based on overall log level
    executor_verbose = effective_log_level <= logging.DEBUG
    logger.info(f"Loading agent executor for: {agent_name} (verbose={executor_verbose}) with provided memory.")
    
    # Get agent config file path using helper
    config_file_path = get_agent_config_file_path(agent_name, config_loader)
    agent_config_dir = get_agent_config_dir(agent_name, config_loader)

    if not os.path.isdir(agent_config_dir) or not os.path.isfile(config_file_path):
        raise FileNotFoundError(f"Agent configuration directory or config file not found for '{agent_name}' at {agent_config_dir}")

    # Load agent meta configuration
    agent_config = None
    try:
        with open(config_file_path, 'r') as f:
            agent_config = yaml.safe_load(f)
        logger.debug(f"Loaded agent config: {agent_config}")
    except yaml.YAMLError as e:
        logger.error(f"Error parsing agent config file {config_file_path}: {e}")
        raise
    except IOError as e:
        logger.error(f"Error reading agent config file {config_file_path}: {e}")
        raise

    # --- Load LLM --- 
    # Use global LLM settings by default, override with agent specifics if provided
    llm_settings = {
        'model': config_loader.get('llm.model', 'gemini-1.5-flash'),
        'google_api_key': config_loader.get('GOOGLE_API_KEY'),
        'temperature': config_loader.get('llm.temperature', 0.7),
    }
    if agent_config.get('model_parameters'):
        llm_settings.update(agent_config['model_parameters'])
        logger.debug(f"Overriding LLM settings with agent specifics: {agent_config['model_parameters']}")
    
    if not llm_settings.get('google_api_key'):
        raise ValueError("Google API Key not found. Please set GOOGLE_API_KEY in your .env file or settings.")

    llm = ChatGoogleGenerativeAI(**{k: v for k, v in llm_settings.items() if k != 'google_api_key'}, google_api_key=llm_settings['google_api_key']) 

    # --- Load Tools --- 
    # Read the new tools_config structure
    agent_tools_config = agent_config.get('tools_config', {}) 
    logger.debug(f"Tools config found for '{agent_name}': {list(agent_tools_config.keys())}")
    if not isinstance(agent_tools_config, dict):
        logger.error(f"'tools_config' in {config_file_path} must be a dictionary (mapping). Found: {type(agent_tools_config)}")
        agent_tools_config = {} # Use empty config to prevent crash
        
    tools = load_tools(agent_tools_config, agent_name, config_loader) # Pass the config dict

    # --- Load Static Context & Create Prompt --- 
    # Check if agent uses system_prompt directly from YAML or a file
    system_prompt_content = ""
    if 'system_prompt' in agent_config:
        system_prompt_content = agent_config['system_prompt']
        logger.debug(f"Using inline system prompt from agent_config.yaml for '{agent_name}'")
    elif agent_config.get('prompt', {}).get('system_message_file'):
        # Load base system prompt specified in config file
        system_prompt_file = agent_config['prompt']['system_message_file']
        system_prompt_path = os.path.join(agent_config_dir, system_prompt_file)
        try:
            with open(system_prompt_path, 'r') as f:
                system_prompt_content = f.read()
            logger.debug(f"Loaded system prompt from file: {system_prompt_path}")
        except IOError as e:
            logger.error(f"Error reading system prompt file {system_prompt_path}: {e}")
            raise # Re-raise the error as it's critical
    else:
         # Raise error if neither inline prompt nor file path is provided
         error_msg = f"Agent '{agent_name}' config file must contain either 'system_prompt' string or 'prompt.system_message_file' path."
         logger.error(error_msg)
         raise ValueError(error_msg)

    # Load ONLY global context using ContextManager
    logger.debug("Loading global context...")
    context_manager = ContextManager(config=config_loader)
    raw_global_context, formatted_global_context = context_manager.get_context(agent_name=None)
    
    # Format the loaded agent_config dictionary itself as context
    # Exclude keys we don't want in the prompt
    config_to_format = {k: v for k, v in agent_config.items() if k not in [
        'prompt', 'model_parameters', 'tools', 'tools_config', 'name', 
        'description', 'system_prompt', 'llm_config_key', 'data' # Also exclude 'data' if present
    ]}
    formatted_agent_config = ""
    if config_to_format:
        logger.debug(f"Formatting agent config details: {config_to_format.keys()}")
        formatted_agent_config = context_manager._format_context(
            config_to_format, 
            f"Agent Configuration: {agent_name}"
        )
    
    # --- Combine global context, agent config, and system prompt --- 
    prompt_parts = []
    # Decide order - System prompt first is common
    if system_prompt_content:
        prompt_parts.append(system_prompt_content)
    if formatted_global_context:
        prompt_parts.append(formatted_global_context)
    if formatted_agent_config:
        prompt_parts.append(formatted_agent_config)
        
    full_system_prompt = "\n\n---\n\n".join(prompt_parts).strip() # Use separator for clarity
    logger.debug(f"--- Full System Prompt for Agent '{agent_name}' START ---")
    logger.debug(full_system_prompt)
    logger.debug(f"--- Full System Prompt for Agent '{agent_name}' END ---")

    # Ensure the prompt isn't empty
    if not full_system_prompt:
         logger.error(f"Context loading resulted in an empty system prompt for agent '{agent_name}'. Check context files and logs.")
         raise ValueError(f"Failed to construct a valid system prompt for agent '{agent_name}'. Context appears empty.")

    # Gemini requires specific prompt structuring for tool use
    prompt = ChatPromptTemplate.from_messages([
        ("system", full_system_prompt), 
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    logger.debug(f"Created ChatPromptTemplate for agent '{agent_name}'")

    # --- Create Agent --- 
    agent = create_tool_calling_agent(llm, tools, prompt)
    logger.debug("Created tool-calling agent.")

    # --- Create Agent Executor --- 
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        memory=memory,
        verbose=executor_verbose, 
        handle_parsing_errors=True
    )
    logger.info(f"Agent executor created for '{agent_name}' and linked with memory.")

    return agent_executor
