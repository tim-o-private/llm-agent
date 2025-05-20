import os
import logging
import yaml
from typing import List, Dict, Any, Optional, Type, Callable, Awaitable
from collections import defaultdict
import uuid # Import the uuid module

from langchain.agents import AgentExecutor, create_tool_calling_agent, create_react_agent
from langchain_core.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.agent_toolkits.file_management.toolkit import FileManagementToolkit
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.callbacks.manager import get_openai_callback
from langchain.agents import ConversationalChatAgent
from langchain.memory import ConversationBufferMemory
from langchain_core.memory import BaseMemory
from core.memory.supabase_chat_history import SupabaseChatMessageHistory
from core.agents.customizable_agent import CustomizableAgent
from core.tools.prompt_tools import UpdateSelfInstructionsTool
from core.tools.search_tools import SafeDuckDuckGoSearchRun
from core.prompting.prompt_manager import PromptManagerService
from supabase import create_client as create_supabase_sync_client
import asyncio

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
    "DuckDuckGoSearchRun": SafeDuckDuckGoSearchRun,
    # Add other toolkits here as needed
}

SCOPE_MAPPING: Dict[str, callable] = {
    "PROJECT_ROOT": lambda config_loader=None, agent_name=None, user_id=None: get_base_path(), 
    "AGENT_DATA": lambda config_loader, agent_name, user_id=None: get_agent_data_dir(agent_name, config_loader, user_id=user_id), 
    "MEMORY_BANK": lambda config_loader, agent_name=None, user_id=None: get_memory_bank_dir(config_loader),
    "AGENT_CONFIG": lambda config_loader, agent_name, user_id=None: get_agent_config_dir(agent_name, config_loader), 
    "TASK_LIST": lambda config_loader, agent_name=None, user_id=None: get_task_list_dir(agent_name, config_loader) if agent_name else get_task_list_dir(None, config_loader),
    "STANDALONE": lambda config_loader=None, agent_name=None, user_id=None: None # For standalone tools that don't need a path
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

        # --- Get Scope Path (if not STANDALONE) --- 
        scope_path = "unknown"
        if scope_key != "STANDALONE":
            scope_func = SCOPE_MAPPING.get(scope_key)
            if not scope_func:
                logger.error(f"Invalid scope '{scope_key}' for toolkit '{toolkit_key}' in agent '{agent_name}'. Available scopes: {list(SCOPE_MAPPING.keys())}")
                continue
            try:
                # Pass necessary arguments based on scope function requirements
                if scope_key == "AGENT_DATA":
                    scope_path = scope_func(config_loader=config_loader, agent_name=agent_name, user_id=user_id)
                elif scope_key == "AGENT_CONFIG":
                    scope_path = scope_func(config_loader=config_loader, agent_name=agent_name)
                elif scope_key == "TASK_LIST":
                    try:
                        scope_path = scope_func(config_loader=config_loader)
                    except TypeError:
                        try: 
                            scope_path = scope_func(agent_name=agent_name, config_loader=config_loader)
                        except TypeError:
                            scope_path = scope_func()
                elif scope_key == "MEMORY_BANK":
                    scope_path = scope_func(config_loader=config_loader)
                else: # PROJECT_ROOT 
                    scope_path = scope_func()
            except Exception as e:
                logger.error(f"Error getting scope path for '{scope_key}' for toolkit '{toolkit_key}' in agent '{agent_name}': {e}", exc_info=True)
                continue
        else:
            scope_path = None # Standalone tools don't have a scope_path

        # --- Get Toolkit Class --- 
        tool_class = TOOLKIT_MAPPING.get(toolkit_key) # Changed from toolkit_class to tool_class for clarity
        if not tool_class:
            logger.error(f"Invalid toolkit/tool class key '{toolkit_key}' for agent '{agent_name}'. Available: {list(TOOLKIT_MAPPING.keys())}")
            continue

        # --- Instantiate Toolkit or Standalone Tool --- 
        # toolkit_instance = None # Renamed for clarity below
        
        if scope_key == "STANDALONE":
            # Handle standalone tools
            try:
                # Standalone tools are instantiated directly.
                # Their 'original_name' in config should match their conceptual name (e.g., 'duckduckgo_search')
                # The 'tool_name' from config is what the agent will call it.
                
                # We only need one instance per standalone tool class.
                # The loop over 'configs' for a standalone tool instance should ideally be just one config.
                if tool_class not in toolkit_instances: # Instantiate only once
                    standalone_tool_instance = tool_class()
                    toolkit_instances[tool_class] = standalone_tool_instance # Cache by class
                    logger.info(f"Instantiated standalone tool '{tool_class.__name__}'.")

                # Process each configuration for this standalone tool (e.g. setting name, description)
                for tool_name, tool_details in configs:
                    current_tool_instance = toolkit_instances[tool_class]
                    # We need to clone or ensure the tool instance is fresh for each specific agent config if names/descriptions differ
                    # For now, let's assume Langchain tools can have their name/description properties modified.
                    # A more robust way for standalone tools might be to instantiate them per config entry.
                    # However, DuckDuckGoSearchRun is simple.
                    
                    final_tool = current_tool_instance 
                    final_tool.name = tool_name # Agent's name for the tool
                    
                    description_override = tool_details.get('description')
                    if description_override:
                        final_tool.description = description_override
                    
                    # original_name in config for standalone tools helps to confirm it's the right tool
                    # but the instance itself is the tool.
                    loaded_tools.append(final_tool)
                    logger.info(f"Configured standalone tool '{final_tool.name}' (from class '{tool_class.__name__}') for agent '{agent_name}'.")

            except Exception as e:
                logger.error(f"Failed to instantiate or configure standalone tool '{toolkit_key}': {e}", exc_info=True)
            continue # Move to next instance_key (next toolkit or standalone tool class)
        
        # --- Existing Toolkit Logic (e.g., FileManagementToolkit) ---
        # This part remains largely the same for actual toolkits
        toolkit_instance = None
        try:
            if toolkit_key == "FileManagementToolkit":
                toolkit_instance = tool_class(root_dir=scope_path, selected_tools=original_names_list)
                logger.info(f"Instantiated toolkit '{toolkit_key}' for scope '{scope_key}' ({scope_path}) requesting tools: {original_names_list}")
            else:
                # Fallback for other toolkits - might need refinement based on their constructors
                toolkit_instance = tool_class() 
                logger.warning(f"Toolkit '{toolkit_key}' instantiated without specific scope/tool selection logic. Review if needed.")
            # Cache the toolkit instance if it's a toolkit (not a standalone tool already handled)
            # This caching by (toolkit_key, scope_key) might need review if multiple configs use the same toolkit but different scopes.
            # For now, it seems each instance_key is unique.
            toolkit_instances[instance_key] = toolkit_instance

        except Exception as e:
            logger.error(f"Failed to instantiate toolkit '{toolkit_key}' for scope '{scope_key}' with tools {original_names_list}: {e}", exc_info=True)
            continue

        if not toolkit_instance:
            continue
            
        try:
            available_tools_map = {t.name: t for t in toolkit_instance.get_tools()}
        except Exception as e:
             logger.error(f"Failed to get tools from toolkit instance {toolkit_key}/{scope_key}: {e}", exc_info=True)
             continue

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

# --- Placeholder for Auth Token Provider ---
# This needs to be properly implemented or passed from chatServer
# For now, it's a placeholder that would need to be correctly set up in the calling context (chatServer)
# to provide the actual user JWT token for the PromptManagerService.
# One way is to have chatServer pass an async callable that returns the token.
async def get_auth_token_placeholder() -> Optional[str]:
    logger.warning("Using placeholder auth token provider for PromptManagerService. This needs proper implementation.")
    # In a real scenario, this would come from the request context in chatServer
    # For agent_loader, if called outside a request, this is problematic.
    # If chatServer calls load_agent_executor, it should pass a real token provider.
    return os.getenv("SUPABASE_ANON_KEY") # Example: using anon key for testing, NOT FOR PRODUCTION

# --- Agent Loading --- 

def load_agent_executor(
    agent_name: str,
    config_loader: ConfigLoader,
    log_level: int,
    # memory: ConversationBufferMemory, # Old memory type, will be replaced if using Supabase
    base_memory_override: Optional[BaseMemory] = None, # Allow overriding memory for testing or specific cases
    user_id: Optional[str] = None,
    # New parameter for chatServer to pass its Supabase client if available and configured for async
    async_supabase_client: Optional[Any] = None, # AsyncClient type
    # New parameter for chatServer to pass a real auth token provider
    auth_token_provider_callable: Optional[Callable[[], Awaitable[Optional[str]]]] = None
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

    # --- Initialize Services (Supabase Client, PromptManagerService) ---
    # Supabase client for SupabaseChatMessageHistory (sync version for direct use here if async_supabase_client not passed)
    # chatServer should ideally pass its initialized async_supabase_client.
    # For CustomizableAgent and its tool, we need PromptManagerService.
    
    actual_auth_token_provider = auth_token_provider_callable if auth_token_provider_callable else get_auth_token_placeholder
    
    prompt_manager_service: Optional[PromptManagerService] = None
    chat_server_url = config_loader.get("chat_server_url", os.getenv("CHAT_SERVER_BASE_URL"))
    if not chat_server_url:
        logger.warning("CHAT_SERVER_BASE_URL not configured. PromptManagerService will not be available.")
    
    if chat_server_url and user_id: # PromptManagerService is user-specific due to token
        prompt_manager_service = PromptManagerService(
            base_url=chat_server_url,
            auth_token_provider=actual_auth_token_provider
        )
        logger.info(f"PromptManagerService initialized for agent {agent_name}, user {user_id}.")
    else:
        logger.warning(f"PromptManagerService not initialized for agent {agent_name} (URL: {chat_server_url}, UserID: {user_id}). CustomizableAgent might lack dynamic prompt features.")

    # --- 3. Determine Agent Class and Memory --- 
    agent_class_name = agent_config.get('agent_class', 'default') # e.g., 'default', 'CustomizableAgent'
    memory_type = agent_config.get('memory_type', 'buffer') # e.g., 'buffer', 'supabase_buffer'

    current_memory: BaseMemory
    if base_memory_override:
        current_memory = base_memory_override
        logger.info(f"Using overridden memory for agent {agent_name}.")
    elif memory_type == 'supabase_buffer' and user_id and async_supabase_client:
        # Ensure session_id is robustly generated or retrieved for the user
        # Create a namespace UUID (this can be a constant, well-known UUID)
        # For example, uuid.NAMESPACE_DNS or a custom one.
        # Let's define a custom namespace for our application sessions.
        APP_NAMESPACE_UUID = uuid.UUID('1b671a64-40d5-491e-99b0-da01ff1f3341') # Example fixed namespace

        # Create a name string that is unique for the user and agent combination
        session_name_for_uuid = f"user_{user_id}_agent_{agent_name}"
        
        # Generate a UUIDv5 for the session ID
        session_id_uuid = uuid.uuid5(APP_NAMESPACE_UUID, session_name_for_uuid)
        session_id = str(session_id_uuid) # Convert UUID object to string for storage/use

        current_memory = ConversationBufferMemory(
            chat_memory=SupabaseChatMessageHistory(
                supabase_client=async_supabase_client, 
                session_id=session_id, # Use the generated UUID string
                user_id=user_id
            ),
            memory_key="chat_history", 
            return_messages=True,
            input_key="input"  # Explicitly set the input key for memory
        )
        logger.info(f"Using SupabaseChatMessageHistory for agent {agent_name}, user {user_id}, session {session_id}.")
    else:
        if memory_type == 'supabase_buffer' and (not user_id or not async_supabase_client):
            logger.warning(f"Supabase memory type configured for '{agent_name}' but user_id or async_supabase_client is missing. Falling back to ConversationBufferMemory.")
        current_memory = ConversationBufferMemory(
            memory_key="chat_history", 
            return_messages=True,
            input_key="input"  # Explicitly set the input key for memory
        )
        logger.info(f"Using standard ConversationBufferMemory for agent {agent_name}.")

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

    # --- 4. Load Tools --- 
    tools_config = agent_config.get('tools_config', {})
    tools: List[BaseTool] = load_tools(agent_name, tools_config, config_loader, user_id=user_id)
    
    # Add UpdateSelfInstructionsTool if CustomizableAgent and prompt_manager is available
    if agent_class_name == 'CustomizableAgent' and prompt_manager_service:
        update_instr_tool = UpdateSelfInstructionsTool(prompt_manager=prompt_manager_service)
        tools.append(update_instr_tool)
        logger.info(f"Added UpdateSelfInstructionsTool for CustomizableAgent '{agent_name}'.")
    elif agent_class_name == 'CustomizableAgent' and not prompt_manager_service:
        logger.warning(f"CustomizableAgent '{agent_name}' configured, but PromptManagerService is not available. UpdateSelfInstructionsTool will not be added.")

    # --- 5. Load Prompt Template --- 
    prompt_template_config = agent_config.get('prompt', {})
    prompt_template_str: Optional[str] = None
    final_prompt_object_for_standard_agent: Optional[ChatPromptTemplate] = None

    # Determine prompt file path and load base content
    prompt_file_name = prompt_template_config.get('file')
    if prompt_file_name:
        # Try to load from agent-specific config directory first
        prompt_file_path = os.path.join(get_agent_config_dir(agent_name, config_loader), prompt_file_name)
        if not os.path.isfile(prompt_file_path):
            # Fallback to global prompts directory if specified in config_loader
            global_prompts_dir = config_loader.get(['paths', 'prompt_templates_dir'])
            if global_prompts_dir:
                prompt_file_path = os.path.join(get_base_path(), global_prompts_dir, prompt_file_name)
            else: # Fallback to a default prompts dir relative to project root or agent_loader.py
                prompt_file_path = os.path.join(get_base_path(), "config", "prompts", prompt_file_name)
        
        try:
            if not os.path.isfile(prompt_file_path):
                raise FileNotFoundError(f"Prompt template file '{prompt_file_name}' not found at attempted paths.")
            with open(prompt_file_path, 'r') as f:
                prompt_template_str = f.read()
            logger.info(f"Loaded prompt template for '{agent_name}' from: {prompt_file_path}")
        except FileNotFoundError as e:
            logger.error(f"Prompt template file error for agent '{agent_name}': {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading prompt template file for '{agent_name}': {e}", exc_info=True)
            raise
    elif 'template_string' in prompt_template_config:
        prompt_template_str = prompt_template_config['template_string']
        logger.info(f"Using inline prompt template string for '{agent_name}'.")
    else:
        # Default prompt if nothing is specified, this will differ for CustomizableAgent vs Standard
        if agent_class_name != 'CustomizableAgent': # Only apply this default for standard agents
            logger.warning(f"No prompt file or template_string specified for standard agent '{agent_name}'. Using a generic default.")
            prompt_template_str = "You are a helpful assistant." # A very basic default system message part

    if not prompt_template_str and agent_class_name != 'CustomizableAgent':
         raise ValueError(f"Prompt template string could not be determined for standard agent '{agent_name}'.")
    
    # --- Load Previous Session Summary (USER-SPECIFIC, for standard agents primarily) ---
    # CustomizableAgent might handle its own context/summary via memory or prompt construction.
    # This logic is primarily for standard agents that expect summaries in the prompt.
    # If CustomizableAgent also needs this, its _construct_prompt_with_customizations needs to be aware.

    base_prompt_for_customizable_agent: Any = prompt_template_str # Default to string content for CustomizableAgent

    if agent_class_name == 'CustomizableAgent':
        # CustomizableAgent expects a base prompt template.
        # It might load its own template if `prompt_template_str` is a path, or use it directly.
        # For now, pass the loaded string content.
        # The default below is a fallback if prompt_template_str is None (e.g. no config at all)
        # but CustomizableAgent should ideally always have a configured base_template.
        if not prompt_template_str:
             base_prompt_for_customizable_agent = prompt_template_config.get('base_template', "You are a helpful assistant. {{custom_instructions}}\\nTOOLS:\\n------\\n{{tools}}\\n\\nUSER INPUT:\\n--------------------\\n{{input}}\\n\\n{{agent_scratchpad}}")
        else:
            base_prompt_for_customizable_agent = prompt_template_str
        logger.info(f"Prepared base prompt template content for CustomizableAgent '{agent_name}'.")
    else: # Standard agent types (tool_calling, react)
        system_message_content = prompt_template_str # Use the loaded string as system message
        
        # --- Load Previous Session Summary (for standard agents) ---
        # This was the original location for summary loading logic.
        # Let's assume for now that CustomizableAgent handles its history/summary via its memory
        # and its own prompt construction, so this summary injection is for standard agents.
        if user_id: # Only load summary if user_id is present
            agent_data_dir = get_agent_data_dir(agent_name, config_loader, user_id=user_id)
            summary_file_path = os.path.join(agent_data_dir, 'session_log.md') # Standardized summary file
            previous_summary = ""
            try:
                if os.path.exists(summary_file_path):
                    os.makedirs(os.path.dirname(summary_file_path), exist_ok=True)
                    with open(summary_file_path, 'r') as f:
                        previous_summary = f.read()
                    if previous_summary:
                        logger.info(f"Loaded previous session summary for user '{user_id}' from {summary_file_path}")
                        # Prepend summary to the system message for standard agents
                        system_message_content = f"PREVIOUS SESSION SUMMARY FOR THIS USER:\\n{previous_summary}\\n\\n---\\n\\nCURRENT SESSION PROMPT:\\n{system_message_content}"
            except IOError as e:
                logger.warning(f"Could not read summary file {summary_file_path} for user '{user_id}': {e}")
            except Exception as e:
                logger.error(f"Unexpected error loading summary from {summary_file_path} for user '{user_id}': {e}", exc_info=True)

        human_message_content = prompt_template_config.get('human_message', "{input}") # Default human message
        
        try:
            final_prompt_object_for_standard_agent = ChatPromptTemplate.from_messages([
                ("system", system_message_content),
                MessagesPlaceholder(variable_name="chat_history"), # Already handled by memory
                ("human", human_message_content),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            logger.info(f"Using standard ChatPromptTemplate for agent '{agent_name}'.")
        except Exception as e:
            logger.error(f"Failed to create ChatPromptTemplate for standard agent '{agent_name}': {e}", exc_info=True)
            raise ValueError(f"Invalid prompt template structure for standard agent '{agent_name}'.")

    # --- 6. Create Agent --- 
    try:
        if agent_class_name == 'CustomizableAgent':
            # if not prompt_manager_service: # Allow running without PromptManagerService, e.g., for CLI testing
            #     logger.warning(f"PromptManagerService is not available for CustomizableAgent '{agent_name}'. Dynamic prompt features will be disabled.")
            #     # raise ValueError(f"Cannot create CustomizableAgent '{agent_name}' without a PromptManagerService.")

            if not user_id and prompt_manager_service: # User ID is needed if prompt manager is active
                 logger.warning(f"CustomizableAgent '{agent_name}' has PromptManagerService but no user_id. Dynamic prompt features may not work correctly.")
                 # raise ValueError(f"CustomizableAgent '{agent_name}' requires a user_id when PromptManagerService is active.")

            if not base_prompt_for_customizable_agent: # Check the correct variable
                raise ValueError(f"Base prompt template not loaded or configured for CustomizableAgent '{agent_name}'.")

            custom_agent = CustomizableAgent(
                llm=llm, # Pass the LLM
                tools=tools, # Pass the loaded tools
                base_prompt_template=base_prompt_for_customizable_agent, # Pass the specific prompt
                prompt_manager=prompt_manager_service, # Pass the service (can be None)
                agent_name=agent_name, # Pass the agent's name
                user_id=user_id # Pass the user ID (can be None)
            )
            # AgentExecutor.from_agent_and_tools expects 'agent' and 'tools'
            # The 'memory' is passed directly to AgentExecutor.
            # The 'handle_parsing_errors' and 'verbose' are also AgentExecutor args.
            agent_executor = AgentExecutor(
                agent=custom_agent, 
                tools=tools, # Tools are also passed to AgentExecutor
                memory=current_memory, 
                verbose=True, 
                handle_parsing_errors=True,
                max_iterations=agent_config.get("max_iterations", 15),
            )
            logger.info(f"CustomizableAgent '{agent_name}' initialized and wrapped in AgentExecutor.")
        else: # Default agent type (e.g., tool_calling or react)
            agent_type = agent_config.get('type', 'tool_calling') 
            if not final_prompt_object_for_standard_agent:
                raise ValueError("Prompt object not created for standard agent type.")

            if agent_type == 'tool_calling':
                created_agent = create_tool_calling_agent(llm, tools, final_prompt_object_for_standard_agent)
            elif agent_type == 'react':
                created_agent = create_react_agent(llm, tools, final_prompt_object_for_standard_agent)
            else:
                raise ValueError(f"Unsupported agent type: {agent_type} for agent '{agent_name}'")
            
            agent_executor = AgentExecutor(
                agent=created_agent, 
                tools=tools, 
                memory=current_memory, 
                verbose=True, 
                handle_parsing_errors=True
            )
            logger.info(f"Agent '{agent_name}' of type '{agent_type}' created.")

    except Exception as e:
        logger.error(f"Error creating agent '{agent_name}': {e}", exc_info=True)
        if prompt_manager_service: # Attempt to close if it was created
            asyncio.run(prompt_manager_service.close()) # Hacky, ideally manage lifecycle better
        raise

    logger.info(f"Agent executor for '{agent_name}' loaded successfully.")
    return agent_executor
