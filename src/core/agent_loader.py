import os
import logging
import yaml
from typing import List, Dict, Any

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.agent_toolkits.file_management.toolkit import FileManagementToolkit
from langchain.memory import ConversationBufferMemory

from utils.config_loader import ConfigLoader
from core.context_manager import ContextManager
from utils.path_helpers import get_agent_data_dir, get_agent_config_dir, get_agent_config_file_path, get_task_list_dir

logger = logging.getLogger(__name__)

def load_tools(tool_names: List[str], agent_name: str, config_loader: ConfigLoader) -> List[BaseTool]:
    """Loads tool instances based on names specified in agent config."""
    tools = []
    
    # Get agent-specific paths using helper functions
    agent_data_dir = get_agent_data_dir(agent_name, config_loader)
    agent_config_dir = get_agent_config_dir(agent_name, config_loader)
    task_list_dir = get_task_list_dir(agent_name, config_loader)
    # Ensure agent data directory exists
    os.makedirs(agent_data_dir, exist_ok=True)
    # Ensure task list directory exists
    os.makedirs(task_list_dir, exist_ok=True)

    # --- Standard File Management Tool (Write Access to Data Dir) ---
    if "file_management" in tool_names:
        logger.info(f"Loading FileManagementToolkit (Read/Write) scoped to: {agent_data_dir}")
        toolkit = FileManagementToolkit(root_dir=agent_data_dir)
        tools.extend(toolkit.get_tools())
    
    if "task_list_management" in tool_names:
        logger.info(f"Loading TaskListManagementToolkit (Read/Write) scoped to: {task_list_dir}")
        toolkit = FileManagementToolkit(root_dir=task_list_dir, selected_tools=["read_file", "write_file"])
        task_tools = toolkit.get_tools()
        # Rename tools for clarity and to avoid collisions
        renamed_task_tools = []
        for tool in task_tools:
            if tool.name == "read_file":
                tool.name = "read_task_list_file"
                tool.description = f"Reads a file from the agent's task list directory ({task_list_dir}). Use for accessing task details."
            elif tool.name == "write_file":
                tool.name = "write_task_list_file"
                tool.description = f"Writes a file to the agent's task list directory ({task_list_dir}). Use for creating or updating tasks."
            renamed_task_tools.append(tool)
        tools.extend(renamed_task_tools)

    # --- Read-Only Config Access Tool ---
    if "read_config_tool" in tool_names:
        logger.info(f"Loading FileManagementToolkit (Read-Only) scoped to: {agent_config_dir}")
        if not os.path.isdir(agent_config_dir):
             logger.warning(f"Agent config directory not found for read_config_tool: {agent_config_dir}")
        else:
            read_toolkit = FileManagementToolkit(
                root_dir=agent_config_dir,
                selected_tools=["read_file"]
            )
            config_tools = read_toolkit.get_tools()
            if config_tools and config_tools[0].name == "read_file":
                 config_tools[0].name = "read_agent_configuration_file"
                 config_tools[0].description = f"Reads a file from the agent's configuration directory ({agent_config_dir}). Use this to read instructions, prompts, or metadata specific to the current agent."
            tools.extend(config_tools)

    # TODO: Add loading for other tools (calendar, notes, etc.) based on tool_names

    logger.debug(f"Loaded tools for agent '{agent_name}': {[tool.name for tool in tools] if tools else 'None'}")
    return tools

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
    tool_names = agent_config.get('tools', [])
    tools = load_tools(tool_names, agent_name, config_loader)

    # --- Load Static Context & Create Prompt --- 
    # Load base system prompt specified in config file
    system_prompt_file = agent_config.get('prompt', {}).get('system_message_file')
    if not system_prompt_file:
        raise ValueError(f"Agent '{agent_name}' config file missing prompt.system_message_file")
    
    system_prompt_path = os.path.join(agent_config_dir, system_prompt_file)
    system_prompt_content = ""
    try:
        with open(system_prompt_path, 'r') as f:
            system_prompt_content = f.read()
        logger.debug(f"Loaded system prompt from: {system_prompt_path}")
    except IOError as e:
        logger.error(f"Error reading system prompt file {system_prompt_path}: {e}")
        raise

    # Load ONLY global context using ContextManager
    logger.debug("Loading global context...")
    context_manager = ContextManager(config=config_loader)
    raw_global_context, formatted_global_context = context_manager.get_context(agent_name=None)
    
    # Format the loaded agent_config dictionary itself as context
    # Exclude keys we don't want in the prompt
    config_to_format = {k: v for k, v in agent_config.items() if k not in ['prompt', 'model_parameters', 'tools']}
    formatted_agent_config = ""
    if config_to_format:
        logger.debug(f"Formatting agent config details: {config_to_format.keys()}")
        formatted_agent_config = context_manager._format_context(
            config_to_format, 
            f"Agent Configuration: {agent_name}"
        )
    
    # --- Combine global context, agent config, and system prompt --- 
    prompt_parts = []
    if formatted_global_context:
        prompt_parts.append(formatted_global_context)
    if formatted_agent_config:
        prompt_parts.append(formatted_agent_config)
    if system_prompt_content:
        prompt_parts.append(system_prompt_content)
        
    full_system_prompt = "\n\n".join(prompt_parts).strip()
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
