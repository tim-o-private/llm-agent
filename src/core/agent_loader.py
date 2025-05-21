import os
import logging
import yaml
from typing import List, Dict, Any, Optional, Type
from collections import defaultdict

from langchain_core.tools import BaseTool
from langchain_community.agent_toolkits.file_management.toolkit import FileManagementToolkit
from core.agents.customizable_agent import CustomizableAgentExecutor
from core.tools.search_tools import SafeDuckDuckGoSearchRun
from supabase import create_client as create_supabase_sync_client # MODIFIED to include AsyncClient
from .agents.customizable_agent import CustomizableAgentExecutor
from .tools.memory_tools import ManageLongTermMemoryTool

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
    user_id: str, 
    session_id: str, 
    config_loader: ConfigLoader, 
    log_level: int = logging.INFO,
    ltm_notes: Optional[str] = None, 
    explicit_custom_instructions: Optional[Dict[str, Any]] = None, 
) -> CustomizableAgentExecutor:
    """Loads agent configuration, tools, and initializes the agent executor."""
    current_logger = logging.getLogger(f"{__name__}.{agent_name}") # More specific logger name
    current_logger.setLevel(log_level)
    current_logger.info(f"Loading agent executor for agent: {agent_name}, user: {user_id}, session: {session_id}")

    if not config_loader:
        current_logger.error("ConfigLoader is not provided. Cannot load agent configuration.")
        raise ValueError("ConfigLoader is required to load agent configuration.")

    # 1. Load Agent Configuration YAML
    agent_config_file = get_agent_config_file_path(agent_name, config_loader)
    current_logger.debug(f"Attempting to load agent configuration from: {agent_config_file}")
    if not os.path.exists(agent_config_file):
        current_logger.error(f"Agent configuration file not found: {agent_config_file}")
        raise FileNotFoundError(f"Agent configuration file not found: {agent_config_file}")
    
    try:
        with open(agent_config_file, 'r') as f:
            agent_config_dict = yaml.safe_load(f)
        if not agent_config_dict:
            raise ValueError("Agent configuration file is empty or invalid.")
        current_logger.info(f"Successfully loaded agent configuration for '{agent_name}' from {agent_config_file}")
    except yaml.YAMLError as e:
        current_logger.error(f"Error parsing YAML for agent configuration {agent_config_file}: {e}", exc_info=True)
        raise ValueError(f"Error parsing agent configuration file: {e}")
    except Exception as e:
        current_logger.error(f"Unexpected error loading agent configuration {agent_config_file}: {e}", exc_info=True)
        raise

    # 2. Initialize Supabase Client (Sync client for LTM tool and initial LTM fetch here)
    # ManageLongTermMemoryTool uses a sync client for its _run method.
    # This client is also used here to fetch initial LTM notes.
    supabase_url = os.getenv("VITE_SUPABASE_URL") # Ensure these are the correct env var names
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        current_logger.error("Supabase URL or Service Key not configured. Cannot initialize LTM services.")
        # Depending on strictness, could raise error or allow agent to run without LTM tool/notes
        # For now, let's allow it but log an error. LTM tool will fail if instantiated without them.
        # The tool itself now raises an error if URL/key are missing, so this is a pre-check.
        # To prevent agent load failure, we might need to conditionally add the tool.
        # For now, let's assume they MUST be present for LTM features.
        raise ValueError("Supabase URL and Service Key must be configured for LTM.")

    sync_supabase_client: Optional[SupabaseSyncClient] = None
    try:
        # Ensure SupabaseSyncClient is imported: from supabase import Client as SupabaseSyncClient
        sync_supabase_client = create_supabase_sync_client(supabase_url, supabase_key) # CORRECTED to use the imported alias
        current_logger.info("Synchronous Supabase client initialized for LTM operations.")
    except Exception as e:
        current_logger.error(f"Failed to initialize synchronous Supabase client: {e}", exc_info=True)
        # Decide if agent can proceed without LTM or if this is a fatal error.
        # For now, let this be fatal if LTM is integral.
        raise ConnectionError(f"Failed to connect to Supabase for LTM: {e}")

    # --- Ensure agent_prompt.md exists in agent_data_dir --- START
    agent_data_dir_path = get_agent_data_dir(agent_name, config_loader, user_id)
    agent_prompt_file_path = os.path.join(agent_data_dir_path, "agent_prompt.md")
    if not os.path.exists(agent_prompt_file_path):
        try:
            # Ensure the directory exists
            os.makedirs(agent_data_dir_path, exist_ok=True)
            # Create an empty agent_prompt.md file
            with open(agent_prompt_file_path, 'w') as apf:
                apf.write("") # Write empty string
            current_logger.info(f"Created empty 'agent_prompt.md' at {agent_prompt_file_path} as it did not exist.")
        except Exception as e_create:
            current_logger.error(f"Failed to create 'agent_prompt.md' at {agent_prompt_file_path}: {e_create}", exc_info=True)
            # This might not be fatal, agent might still function but will log error on read attempt.
    # --- Ensure agent_prompt.md exists in agent_data_dir --- END

    # 3. Fetch Long-Term Memory (LTM) Notes if not overridden by parameter
    final_ltm_notes_content: Optional[str] = None
    if ltm_notes is not None:
        current_logger.info(f"Using LTM notes provided as parameter for agent '{agent_name}'.")
        final_ltm_notes_content = ltm_notes
    else:
        current_logger.info(f"Fetching LTM notes from DB for agent '{agent_name}', user '{user_id}'.")
        try:
            # Direct fetch using the sync client
            response = (sync_supabase_client.table("agent_long_term_memory")
                        .select("notes") # Corrected column name from design doc to match tool's table
                        .eq("user_id", user_id)
                        .eq("agent_id", agent_name) # Use agent_name as agent_id for LTM table
                        .limit(1)
                        .execute())
            if response.data and response.data[0].get("notes") is not None:
                final_ltm_notes_content = response.data[0]["notes"]
                current_logger.info(f"Successfully fetched LTM notes for agent '{agent_name}'. Length: {len(final_ltm_notes_content)}")
            else:
                current_logger.info(f"No LTM notes found in DB for agent '{agent_name}', user '{user_id}'.")
        except Exception as e:
            current_logger.error(f"Error fetching LTM notes from DB for agent '{agent_name}': {e}", exc_info=True)
            # Agent will proceed without LTM notes if fetch fails

    # 4. Load Tools
    tools_config = agent_config_dict.get("tools_config", {})
    loaded_tools = load_tools(agent_name, tools_config, config_loader, user_id)
    current_logger.info(f"Loaded {len(loaded_tools)} tools for agent '{agent_name}'.")

    # 5. Add ManageLongTermMemoryTool if Supabase is configured
    # (Supabase URL/Key check already performed above, tool raises error if not provided)
    try:
        current_logger.debug(f"Attempting to init LTM Tool. URL: '{supabase_url}', Key available: {bool(supabase_key and supabase_key.strip())}, UserID: {user_id}, AgentID: {agent_name}") # Debug print updated
        ltm_tool = ManageLongTermMemoryTool(
            user_id=user_id,
            agent_id=agent_name, # Ensure agent_id is passed
            supabase_url=supabase_url, 
            supabase_key=supabase_key
        )
        loaded_tools.append(ltm_tool)
        current_logger.info(f"Added ManageLongTermMemoryTool for agent '{agent_name}'.")
    except ValueError as ve:
        current_logger.error(f"Could not instantiate ManageLongTermMemoryTool for agent '{agent_name}' due to missing Supabase config: {ve}. LTM tool will not be available.")
        # This case should be rare now due to earlier checks, but good for safety.
    except Exception as e:
        current_logger.error(f"Unexpected error instantiating ManageLongTermMemoryTool for agent '{agent_name}': {e}", exc_info=True)

    # 6. Create CustomizableAgentExecutor
    # Pass the fetched (or parameterized) LTM notes and explicit instructions.
    current_logger.debug(f"Calling CustomizableAgentExecutor.from_agent_config for agent '{agent_name}'.")
    
    # --- Read system_prompt from file specified in config --- START
    system_prompt_content: Optional[str] = None
    prompt_config = agent_config_dict.get("prompt", {})
    system_message_file_name = prompt_config.get("system_message_file")

    if system_message_file_name:
        # Construct path relative to the agent's config directory
        # agent_config_file is the path to agent_config.yaml
        agent_config_dir_path = os.path.dirname(agent_config_file)
        system_message_file_path = os.path.join(agent_config_dir_path, system_message_file_name)
        current_logger.info(f"Attempting to load system prompt from: {system_message_file_path}")
        try:
            with open(system_message_file_path, 'r') as f:
                system_prompt_content = f.read()
            if not system_prompt_content.strip():
                current_logger.warning(f"System prompt file '{system_message_file_path}' is empty.")
                system_prompt_content = None # Treat as if not found
            else:
                current_logger.info(f"Successfully loaded system prompt from '{system_message_file_path}'. Length: {len(system_prompt_content)}")
        except FileNotFoundError:
            current_logger.error(f"System prompt file not found: {system_message_file_path}")
            # Raise error, as CustomizableAgentExecutor.from_agent_config expects system_prompt string in agent_config_dict
            # Or, we could modify from_agent_config to accept None and use a default.
            # For now, let's ensure it's loaded here or error out if config specifies it but not found.
            raise FileNotFoundError(f"System prompt file '{system_message_file_path}' specified in agent config but not found.")
        except Exception as e:
            current_logger.error(f"Error reading system prompt file '{system_message_file_path}': {e}", exc_info=True)
            raise
    else:
        current_logger.warning("No 'system_message_file' specified in agent config under 'prompt'. System prompt will be missing unless defined directly as 'system_prompt' key.")
        # Check if system_prompt is directly in agent_config_dict as a fallback
        system_prompt_content = agent_config_dict.get("system_prompt")
        if not system_prompt_content:
             current_logger.error("Neither 'prompt.system_message_file' nor a direct 'system_prompt' key was found in agent configuration.")
             # This will cause CustomizableAgentExecutor.from_agent_config to fail as it expects agent_config_dict to have 'system_prompt'
             # We will let that happen, or explicitly raise here.
             # For now, it will fail in the from_agent_config call if this is None.

    # Create a mutable copy of agent_config_dict to inject the loaded system_prompt if needed.
    # This is because CustomizableAgentExecutor.from_agent_config expects 'system_prompt' directly.
    final_agent_config_dict = agent_config_dict.copy()
    if system_prompt_content:
        final_agent_config_dict["system_prompt"] = system_prompt_content
    elif "system_prompt" not in final_agent_config_dict: # If not loaded and not already there
        current_logger.error("Fatal: system_prompt could not be loaded or found. Agent will likely fail to initialize.")
        # Let from_agent_config raise the error for clarity on where it's expected.

    try:
        agent_executor = CustomizableAgentExecutor.from_agent_config(
            agent_config_dict=final_agent_config_dict, # Pass the modified dict with system_prompt content
            tools=loaded_tools,
            user_id=user_id,
            session_id=session_id, # Pass session_id through
            ltm_notes_content=final_ltm_notes_content, # Pass the resolved LTM notes
            explicit_custom_instructions_dict=explicit_custom_instructions, # Pass through
            logger_instance=current_logger # Pass logger for consistent logging
        )
        current_logger.info(f"Successfully created CustomizableAgentExecutor for agent '{agent_name}'.")
        return agent_executor
    except Exception as e:
        current_logger.error(f"Failed to create CustomizableAgentExecutor for '{agent_name}': {e}", exc_info=True)
        raise

# Placeholder for other agent loading mechanisms if needed in future
# (e.g., different agent types, specific factory functions)
