import click
import os
import logging
import yaml
import json
from typing import List, Dict, Any

# Add src to path for direct script execution (optional, depends on setup)
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from utils.config_loader import ConfigLoader
from core.context_manager import ContextManager
from core.llm_interface import LLMInterface

# --- Langchain Agent Imports ---
from langchain.memory import ConversationBufferMemory, ChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage, message_to_dict, messages_from_dict
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.agent_toolkits.file_management.toolkit import FileManagementToolkit
from langchain_core.tools import BaseTool

# --- Input Handling Imports ---
from prompt_toolkit import prompt as prompt_toolkit_prompt
from prompt_toolkit.history import InMemoryHistory

# --- Basic Logging Setup ---
# Set format only, level will be set dynamically
logging.basicConfig(format='[%(asctime)s] %(levelname)s [%(name)s] - %(message)s')
logger = logging.getLogger(__name__) # Get root logger or specific module logger

# --- Configuration Loading ---
# Load configuration globally for the CLI application
# TODO: Consider making ConfigLoader a singleton or passing it via context
config_loader = ConfigLoader()

# --- CLI Command Group ---
@click.group()
@click.option(
    '--log-level', 
    type=click.Choice(['debug', 'info', 'warning', 'error', 'critical'], case_sensitive=False),
    default='error',
    help='Set the logging level.'
)
@click.pass_context # Pass context to group function
def cli(ctx, log_level):
    """Local LLM Terminal Environment CLI."""
    # Set the initial log level based on the option
    level_name = log_level.upper()
    level = getattr(logging, level_name, logging.ERROR)
    logging.getLogger().setLevel(level) # Set level on root logger
    logger.info(f"Root logger level set to: {level_name}")

    # Store the chosen level in the context object to pass to subcommands
    # Subcommands can check this if they need specific level handling (e.g., --verbose override)
    ctx.obj = {'LOG_LEVEL': level}

# --- 'ask' Command ---
@cli.command()
@click.argument('query', type=str)
@click.option(
    '--agent', '-a',
    type=str,
    help='Specify the agent name for context loading.'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose logging (overrides --log-level).'
)
@click.pass_context # Pass context to command function
def ask(ctx, query: str, agent: str | None, verbose: bool):
    """Ask a single question to the LLM, providing context from the specified agent."""
    
    # Handle verbose override
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled (--verbose). Overriding log level.")
    else:
        # Set level based on group option if not verbose
        pass # Level already set by cli() group function
        # logging.getLogger().setLevel(ctx.obj['LOG_LEVEL']) # Alternative if not set by group

    logger.info(f"Received query: {query}")
    
    # Determine agent context
    agent_name = None
    if agent:
        # Use the provided name directly
        agent_name = agent
        logger.info(f"Using specified agent context: {agent_name}")
    else:
        logger.info("Agent not specified. Using global context only for now.")
        # For now, just load global context

    try:
        # Initialize core components
        logger.debug("Initializing ContextManager...")
        context_manager = ContextManager(config=config_loader)
        logger.debug("Initializing LLMInterface...")
        llm_interface = LLMInterface(config=config_loader)
        
        # Get context
        logger.debug(f"Loading context for agent: {agent_name}")
        raw_context, formatted_context = context_manager.get_context(agent_name=agent_name)
        logger.debug(f"Context loaded. Formatted length: {len(formatted_context)}")

        # Generate response
        logger.info("Sending query and context to LLM...")
        response = llm_interface.generate_text(prompt=query, system_context=formatted_context)
        logger.info("Received response from LLM.")

        # Print response
        click.echo("\nLLM Response:")
        click.echo("----------------------------------------")
        click.echo(response)
        click.echo("----------------------------------------")

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        click.echo(f"Error: {e}", err=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True) # Log traceback
        click.echo(f"An unexpected error occurred: {e}", err=True)

# --- Agent Loading Logic ---

def load_tools(tool_names: List[str], agent_name: str) -> List[BaseTool]:
    """Loads tool instances based on names specified in agent config."""
    tools = []
    # Get base paths from config using the .get() method
    base_data_dir = config_loader.get('data.base_dir', 'data/')
    base_config_dir = config_loader.get('config.base_dir', 'config/')
    agents_data_subdir = config_loader.get('data.agents_dir', 'agents/')
    agents_config_subdir = config_loader.get('config.agents_dir', 'agents/')

    # Agent-specific paths constructed using os.path.join
    agent_data_dir = os.path.join(base_data_dir, agents_data_subdir, agent_name)
    agent_config_dir = os.path.join(base_config_dir, agents_config_subdir, agent_name)
    
    # Ensure agent data directory exists
    os.makedirs(agent_data_dir, exist_ok=True)

    # --- Standard File Management Tool (Write Access to Data Dir) ---
    if "file_management" in tool_names:
        # Scope file management to the agent's *data* directory
        logger.info(f"Loading FileManagementToolkit (Read/Write) scoped to: {agent_data_dir}")
        toolkit = FileManagementToolkit(root_dir=agent_data_dir)
        tools.extend(toolkit.get_tools())

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

    logger.debug(f"Loaded tools for agent '{agent_name}': {[tool.name for tool in tools] if tools else 'None'}") # Handle empty list
    return tools

def load_agent_executor(agent_name: str, effective_log_level: int) -> AgentExecutor:
    """Loads agent configuration and creates an AgentExecutor (without attached memory)."""
    # Determine executor verbosity based on overall log level
    executor_verbose = effective_log_level <= logging.DEBUG
    logger.info(f"Loading agent executor for: {agent_name} (verbose={executor_verbose}). Memory will be handled manually.")
    base_config_dir = config_loader.get('config.base_dir', 'config/')
    agent_config_dir = os.path.join(base_config_dir, config_loader.get('config.agents_dir', 'agents/'), agent_name)
    config_file_path = os.path.join(agent_config_dir, 'agent_config.yaml')

    if not os.path.isdir(agent_config_dir) or not os.path.isfile(config_file_path):
        raise FileNotFoundError(f"Agent configuration directory or config file not found for '{agent_name}' at {agent_config_dir}")

    # Load agent meta configuration (now agent_config)
    agent_config = None # Initialize
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
    # llm = LLMInterface(config=config_loader).llm # Alternative using existing class?

    # --- Load Tools --- 
    tool_names = agent_config.get('tools', [])
    tools = load_tools(tool_names, agent_name)

    # --- Load Static Context & Create Prompt --- 
    # Load base system prompt specified in config file
    system_prompt_file = agent_config.get('prompt', {}).get('system_message_file')
    if not system_prompt_file:
        raise ValueError(f"Agent '{agent_name}' config file missing prompt.system_message_file")
    
    system_prompt_path = os.path.join(agent_config_dir, system_prompt_file)
    system_prompt_content = "" # Initialize
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
    raw_global_context, formatted_global_context = context_manager.get_context(agent_name=None) # Pass None for agent_name
    
    # Format the loaded agent_config dictionary itself as context
    # Exclude keys we don't want in the prompt (like 'prompt' itself)
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
    if formatted_agent_config: # Add formatted config details
        prompt_parts.append(formatted_agent_config)
    if system_prompt_content: # Add the main system prompt instructions
        prompt_parts.append(system_prompt_content)
        
    full_system_prompt = "\n\n".join(prompt_parts).strip()
    logger.debug(f"--- Full System Prompt for Agent '{agent_name}' START ---")
    logger.debug(full_system_prompt)
    logger.debug(f"--- Full System Prompt for Agent '{agent_name}' END ---")

    # Ensure the prompt isn't empty if context loading somehow failed
    if not full_system_prompt:
         logger.error(f"Context loading resulted in an empty system prompt for agent '{agent_name}'. Check context files and logs.")
         # Fallback to a minimal prompt or raise error?
         # For now, let's raise an error as this shouldn't happen.
         raise ValueError(f"Failed to construct a valid system prompt for agent '{agent_name}'. Context appears empty.")

    # Gemini requires specific prompt structuring for tool use
    # We use MessagesPlaceholder for chat history and agent scratchpad
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
        verbose=executor_verbose, 
        handle_parsing_errors=True # Re-enable error handling
    )
    logger.info(f"Agent executor created for '{agent_name}'.")

    return agent_executor

# --- Helper function to get memory file path (moved up for use in save) ---
def get_memory_file_path(agent_name_for_mem: str) -> str:
    agent_data_dir = os.path.join(
        config_loader.get('data.base_dir', 'data/'), 
        config_loader.get('data.agents_dir', 'agents/'), 
        agent_name_for_mem
    )
    memory_dir = os.path.join(agent_data_dir, 'memory')
    return os.path.join(memory_dir, 'chat_history.json')

# --- Helper function to save a single agent's memory ---
def save_agent_memory(agent_name_to_save: str, memory_to_save: ConversationBufferMemory):
    """Saves the chat history of a specific agent to its JSON file."""
    memory_file_to_save = get_memory_file_path(agent_name_to_save)
    memory_dir = os.path.dirname(memory_file_to_save)
    
    try:
        # Ensure memory directory exists
        os.makedirs(memory_dir, exist_ok=True)
        
        # Get messages and convert to list of dicts
        messages = memory_to_save.chat_memory.messages
        if not messages:
            logger.info(f"No history to save for agent '{agent_name_to_save}'. Skipping file write.")
            return # Return if no messages

        messages_as_dict_list = [message_to_dict(msg) for msg in messages]
        
        # Write to JSON file
        logger.info(f"Saving {len(messages)} messages for agent '{agent_name_to_save}' to {memory_file_to_save}")
        with open(memory_file_to_save, 'w') as f:
            json.dump(messages_as_dict_list, f, indent=2)
        logger.info(f"Successfully saved history for '{agent_name_to_save}'.")

    except IOError as e:
         logger.error(f"Failed to write memory file {memory_file_to_save} for agent '{agent_name_to_save}': {e}")
    except Exception as e:
         logger.error(f"Unexpected error saving memory for agent '{agent_name_to_save}': {e}", exc_info=True)

# --- 'chat' Command (REPL) ---
@cli.command()
@click.option(
    '--agent', '-a',
    type=str,
    default='assistant', # Default agent for chat mode
    help='Specify the initial agent name for the chat session.'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose logging (overrides --log-level).'
)
@click.pass_context # Pass context to command function
def chat(ctx, agent: str, verbose: bool):
    """Start an interactive chat session (REPL) with an agent."""
    
    # Determine effective log level
    effective_log_level = logging.DEBUG if verbose else ctx.obj['LOG_LEVEL']
    if verbose:
        # Note: We set the root logger level here, affecting all modules
        logging.getLogger().setLevel(effective_log_level)
        logger.debug("Verbose logging enabled (--verbose). Overriding log level.")
    # Otherwise, the level set by the cli group function is used.

    logger.info(f"Starting chat session with agent: {agent}")
    click.echo(f"Starting interactive chat with agent '{agent}'. Type /exit to quit.")
    click.echo("Other commands: /agent <name>")

    current_agent_name = agent
    agent_executor = None
    agent_memories: Dict[str, ConversationBufferMemory] = {} 
    current_memory = None 

    def get_or_create_memory(agent_name: str) -> ConversationBufferMemory:
        """Gets existing memory from file or creates new memory for an agent."""
        nonlocal agent_memories # Allow modification of the outer scope variable
        
        if agent_name in agent_memories:
            logger.info(f"Reusing in-memory buffer for agent '{agent_name}'")
            return agent_memories[agent_name]

        # --- Load from file if exists ---
        memory_file = get_memory_file_path(agent_name)
        loaded_messages = []
        if os.path.isfile(memory_file):
            logger.info(f"Attempting to load chat history for '{agent_name}' from {memory_file}")
            try:
                with open(memory_file, 'r') as f:
                    data = json.load(f)
                    loaded_messages = messages_from_dict(data)
                logger.info(f"Successfully loaded {len(loaded_messages)} messages for '{agent_name}'.")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON from {memory_file}: {e}. Starting with empty history.")
                loaded_messages = [] # Reset on error
            except IOError as e:
                logger.error(f"Failed to read memory file {memory_file}: {e}. Starting with empty history.")
                loaded_messages = [] # Reset on error
            except Exception as e: # Catch other potential errors during loading/conversion
                 logger.error(f"Unexpected error loading memory from {memory_file}: {e}. Starting with empty history.", exc_info=True)
                 loaded_messages = [] # Reset on error
        else:
             logger.info(f"No memory file found at {memory_file} for agent '{agent_name}'. Starting with empty history.")

        # --- Create memory instance using ChatMessageHistory --- 
        # 1. Create history object with loaded messages
        chat_history = ChatMessageHistory(messages=loaded_messages)
        # 2. Create buffer memory, passing the history object
        new_memory = ConversationBufferMemory(
            memory_key="chat_history", 
            return_messages=True,
            chat_memory=chat_history # Pass the initialized history
        )
        logger.debug(f"Initialized memory for '{agent_name}' with {len(loaded_messages)} messages via ChatMessageHistory.") # Updated log

        agent_memories[agent_name] = new_memory
        return new_memory

    try:
        # --- Load initial agent and memory ---
        # 1. Get/Create memory first
        current_memory = get_or_create_memory(current_agent_name)
        # 2. Load executor (now doesn't take memory)
        agent_executor = load_agent_executor(current_agent_name, effective_log_level)

    except (FileNotFoundError, ValueError, yaml.YAMLError, IOError) as e:
        logger.error(f"Failed to load initial agent '{current_agent_name}': {e}")
        click.echo(f"Error: Could not load agent '{current_agent_name}'. Please check configuration.", err=True)
        return # Exit if initial agent fails
    except Exception as e:
        logger.error(f"Unexpected error loading initial agent '{current_agent_name}': {e}", exc_info=True)
        click.echo(f"Error: An unexpected error occurred loading agent '{current_agent_name}'.", err=True)
        return

    # --- REPL Setup ---
    session_history = InMemoryHistory()

    try:
        while True:
            try:
                # Get user input using prompt_toolkit with history
                user_input = prompt_toolkit_prompt(
                    f"({current_agent_name}) > ", 
                    history=session_history,
                    # TODO: Add completer for commands like /agent?
                )
            except EOFError:
                # Handle Ctrl+D as exit
                logger.info("EOF received. Ending chat session.")
                click.echo("Exiting chat session.")
                break

            if not user_input:
                continue # Ignore empty input

            if user_input.lower() == '/exit':
                logger.info("Exit command received. Ending chat session.")
                click.echo("Exiting chat session.")
                break
            
            if user_input.lower().startswith('/agent '):
                new_agent_name = user_input[len('/agent '):].strip()
                if not new_agent_name:
                    click.echo("Error: Please specify an agent name after /agent.")
                    continue
                
                if new_agent_name == current_agent_name:
                    click.echo(f"Already using agent: {current_agent_name}")
                    continue

                try:
                    # --- Load new agent and memory --- 
                    # 1. Get/Create memory for the NEW agent first
                    new_memory = get_or_create_memory(new_agent_name)
                    # 2. Load executor for the NEW agent (doesn't take memory)
                    new_executor = load_agent_executor(new_agent_name, effective_log_level) 
                    
                    # --- Save previous agent's memory BEFORE switching ---
                    if current_memory and current_agent_name:
                         logger.info(f"Switching agent. Saving current memory for '{current_agent_name}'...")
                         save_agent_memory(current_agent_name, current_memory)
                    # --------------------------------------------------

                    # Switch successful
                    current_agent_name = new_agent_name
                    agent_executor = new_executor
                    current_memory = new_memory 
                    logger.info(f"Switching to agent: {current_agent_name}")
                    click.echo(f"Switched to agent: {current_agent_name}")
                except (FileNotFoundError, ValueError, yaml.YAMLError, IOError) as e:
                    logger.warning(f"Failed to switch agent to '{new_agent_name}': {e}")
                    click.echo(f"Error: Could not load agent '{new_agent_name}'. Staying with '{current_agent_name}'.", err=True)
                except Exception as e:
                    logger.error(f"Unexpected error switching to agent '{new_agent_name}': {e}", exc_info=True)
                    click.echo(f"Error: An unexpected error occurred switching to agent '{new_agent_name}'.", err=True)
                finally:
                    continue 
            
            if not agent_executor or not current_memory:
                click.echo("Error: Agent executor or memory not loaded. Cannot process query.", err=True)
                continue

            # Pass user_input to the current AgentExecutor
            try:
                # --- Manually load variables from memory --- 
                loaded_memory_vars = current_memory.load_memory_variables({}) 
                logger.debug(f"Manually loaded memory for {current_agent_name}: {loaded_memory_vars}")

                # --- Manually pass chat_history to invoke --- 
                response = agent_executor.invoke({
                    "input": user_input, 
                    "chat_history": loaded_memory_vars.get("chat_history", []) # Pass history
                }) 
                
                output = response.get('output', 'Error: No output found.')
                
                # --- Manually save context back to memory object --- 
                current_memory.save_context({"input": user_input}, {"output": output})
                logger.debug(f"Manually saved context for {current_agent_name}: input='{user_input}', output='{output[:50]}...'")

                click.echo(f"\n{output}")
            except Exception as e:
                logger.error(f"Error during agent execution: {e}", exc_info=True)
                click.echo(f"Error processing query: {e}", err=True)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Ending chat session.")
        click.echo("\nExiting chat session.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during chat: {e}", exc_info=True)
        click.echo(f"\nAn unexpected error occurred: {e}", err=True)
    finally:
        # --- Save all memories on exit using the helper function ---
        logger.info("Chat session ending. Saving chat histories...")
        for agent_name_to_save, memory_to_save in agent_memories.items():
             save_agent_memory(agent_name_to_save, memory_to_save) # Call helper
        
        logger.info("Finished saving chat histories.")
        pass 

# --- Entry Point ---
if __name__ == '__main__':
    cli()
