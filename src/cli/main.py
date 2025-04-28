import click
import os
import logging
import yaml
from typing import List, Dict, Any

# Add src to path for direct script execution (optional, depends on setup)
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from utils.config_loader import ConfigLoader
from core.context_manager import ContextManager
from core.llm_interface import LLMInterface

# --- Langchain Agent Imports ---
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
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
    base_data_dir = config_loader.get('data.base_dir', 'data/')
    agent_data_dir = os.path.join(base_data_dir, config_loader.get('data.agents_dir', 'agents/'), agent_name)
    
    # Ensure agent data directory exists (for output, etc.)
    os.makedirs(agent_data_dir, exist_ok=True)
    agent_output_dir = os.path.join(agent_data_dir, 'output')
    os.makedirs(agent_output_dir, exist_ok=True)

    if "file_management" in tool_names:
        # Scope file management to the agent's *output* directory for safety
        logger.info(f"Loading FileManagementToolkit scoped to: {agent_output_dir}")
        # TODO: Allow selecting specific file tools (read, list etc.) if needed
        toolkit = FileManagementToolkit(root_dir=agent_output_dir)
        tools.extend(toolkit.get_tools())
    
    # TODO: Add loading for other tools (calendar, notes, etc.) based on tool_names

    logger.debug(f"Loaded tools for agent '{agent_name}': {[tool.name for tool in tools]}")
    return tools

def load_agent_executor(agent_name: str, effective_log_level: int) -> AgentExecutor:
    """Loads agent configuration and creates an AgentExecutor."""
    # Determine executor verbosity based on overall log level
    executor_verbose = effective_log_level <= logging.DEBUG
    logger.info(f"Loading agent executor for: {agent_name} (verbose={executor_verbose})")
    base_config_dir = config_loader.get('config.base_dir', 'config/')
    agent_config_dir = os.path.join(base_config_dir, config_loader.get('config.agents_dir', 'agents/'), agent_name)
    meta_file_path = os.path.join(agent_config_dir, 'agent_meta.yaml')

    if not os.path.isdir(agent_config_dir) or not os.path.isfile(meta_file_path):
        raise FileNotFoundError(f"Agent configuration directory or meta file not found for '{agent_name}' at {agent_config_dir}")

    # Load agent meta configuration
    try:
        with open(meta_file_path, 'r') as f:
            agent_meta = yaml.safe_load(f)
        logger.debug(f"Loaded agent meta: {agent_meta}")
    except yaml.YAMLError as e:
        logger.error(f"Error parsing agent meta file {meta_file_path}: {e}")
        raise
    except IOError as e:
        logger.error(f"Error reading agent meta file {meta_file_path}: {e}")
        raise

    # --- Load LLM --- 
    # Use global LLM settings by default, override with agent specifics if provided
    llm_settings = {
        'model': config_loader.get('llm.model', 'gemini-1.5-flash'),
        'google_api_key': config_loader.get('GOOGLE_API_KEY'),
        'temperature': config_loader.get('llm.temperature', 0.7),
        # 'convert_system_message_to_human': True # Removed - likely deprecated/unnecessary
    }
    if agent_meta.get('model_parameters'):
        llm_settings.update(agent_meta['model_parameters'])
        logger.debug(f"Overriding LLM settings with agent specifics: {agent_meta['model_parameters']}")
    
    if not llm_settings.get('google_api_key'):
            raise ValueError("Google API Key not found. Please set GOOGLE_API_KEY in your .env file or settings.")

    llm = ChatGoogleGenerativeAI(**{k: v for k, v in llm_settings.items() if k != 'google_api_key'}, google_api_key=llm_settings['google_api_key']) 
    # llm = LLMInterface(config=config_loader).llm # Alternative using existing class?

    # --- Load Tools --- 
    tool_names = agent_meta.get('tools', [])
    tools = load_tools(tool_names, agent_name)

    # --- Load Static Context & Create Prompt --- 
    # Load base system prompt specified in meta file
    system_prompt_file = agent_meta.get('prompt', {}).get('system_message_file')
    if not system_prompt_file:
        raise ValueError(f"Agent '{agent_name}' meta file missing prompt.system_message_file")
    
    system_prompt_path = os.path.join(agent_config_dir, system_prompt_file)
    try:
        with open(system_prompt_path, 'r') as f:
            system_prompt_template = f.read()
        logger.debug(f"Loaded system prompt from: {system_prompt_path}")
    except IOError as e:
        logger.error(f"Error reading system prompt file {system_prompt_path}: {e}")
        raise

    # Load additional static context files (e.g., YAML, MD) using ContextManager
    logger.debug("Loading additional static context files...")
    context_manager = ContextManager(config=config_loader)
    # raw_static_context is dict like {'agent_static': {'file1': 'content1', 'file2': {...}}}
    # formatted_static_context is the formatted string version
    raw_static_context, formatted_static_context = context_manager.get_context(agent_name=agent_name)
    # We only need the agent-specific static context here, ignore global for the main prompt setup
    formatted_agent_config_context = ""
    if raw_static_context.get('agent_static'):
        # Re-format here for clarity, ensuring it only includes agent config files
        formatted_agent_config_context = context_manager._format_context(
            raw_static_context['agent_static'],
            f"Agent Background: {agent_name}" # Use a distinct title
        )
        logger.debug(f"Formatted agent background context:\n{formatted_agent_config_context}")
    else:
        logger.debug("No additional static context files found.")

    # Prepend additional context to the main system prompt template
    full_system_prompt = f"{formatted_agent_config_context}\n\n{system_prompt_template}".strip()
    logger.debug(f"Full system prompt content prepared.")

    # Gemini requires specific prompt structuring for tool use
    # We use MessagesPlaceholder for chat history and agent scratchpad
    prompt = ChatPromptTemplate.from_messages([
        ("system", full_system_prompt), # Use the combined prompt
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    logger.debug(f"Created ChatPromptTemplate for agent '{agent_name}'")

    # --- Create Agent --- 
    # Create a tool-calling agent specifically
    agent = create_tool_calling_agent(llm, tools, prompt)
    logger.debug("Created tool-calling agent.")

    # --- Create Agent Executor --- 
    # Pass memory when instantiating?
    # memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        # memory=memory, # Pass memory here?
        verbose=executor_verbose, # Set based on log level
        handle_parsing_errors=True # Handle cases where LLM output is not perfect
    )
    logger.info(f"Agent executor created for '{agent_name}'.")

    return agent_executor

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
    agent_memories: Dict[str, ConversationBufferMemory] = {} # Dictionary to hold memory per agent
    current_memory = None # Track the active memory object

    def get_or_create_memory(agent_name: str) -> ConversationBufferMemory:
        """Gets existing memory or creates new memory for an agent."""
        nonlocal agent_memories # Allow modification of the outer scope variable
        if agent_name not in agent_memories:
            logger.info(f"Creating new memory buffer for agent '{agent_name}'")
            agent_memories[agent_name] = ConversationBufferMemory(
                memory_key="chat_history", 
                return_messages=True
            )
        else:
            logger.info(f"Reusing existing memory buffer for agent '{agent_name}'")
        return agent_memories[agent_name]

    try:
        # Load initial agent, passing the determined level
        agent_executor = load_agent_executor(current_agent_name, effective_log_level)
        # Get or create initial memory
        current_memory = get_or_create_memory(current_agent_name)

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
                    # Validate and load new agent, passing the determined level
                    new_executor = load_agent_executor(new_agent_name, effective_log_level)
                    # Switch successful
                    current_agent_name = new_agent_name
                    agent_executor = new_executor
                    # Get or create memory for the switched agent
                    current_memory = get_or_create_memory(current_agent_name) 
                    logger.info(f"Switching to agent: {current_agent_name}")
                    click.echo(f"Switched to agent: {current_agent_name}")
                except (FileNotFoundError, ValueError, yaml.YAMLError, IOError) as e:
                    logger.warning(f"Failed to switch agent to '{new_agent_name}': {e}")
                    click.echo(f"Error: Could not load agent '{new_agent_name}'. Staying with '{current_agent_name}'.", err=True)
                except Exception as e:
                    logger.error(f"Unexpected error switching to agent '{new_agent_name}': {e}", exc_info=True)
                    click.echo(f"Error: An unexpected error occurred switching to agent '{new_agent_name}'.", err=True)
                finally:
                    continue # Go to next loop iteration for new prompt
            
            if not agent_executor or not current_memory:
                click.echo("Error: Agent executor or memory not loaded. Cannot process query.", err=True)
                continue

            # Pass user_input to the current AgentExecutor
            try:
                # Load context from the CURRENT agent's memory
                loaded_memory = current_memory.load_memory_variables({})
                logger.debug(f"Memory loaded for {current_agent_name}: {loaded_memory}")

                # Include chat history in the input dictionary
                response = agent_executor.invoke({
                    "input": user_input,
                    "chat_history": loaded_memory.get("chat_history", []) 
                })
                
                output = response.get('output', 'Error: No output found.')
                
                # Save context to the CURRENT agent's memory
                current_memory.save_context({"input": user_input}, {"output": output})
                logger.debug(f"Saved context for {current_agent_name}: input='{user_input}', output='{output[:50]}...'")

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
        # Cleanup if needed
        pass 

# --- Entry Point ---
if __name__ == '__main__':
    cli()
