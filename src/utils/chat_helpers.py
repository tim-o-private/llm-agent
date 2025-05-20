import os
import json
import logging
from typing import TYPE_CHECKING, Dict, Tuple, Optional, Any

# Langchain imports needed by helper functions
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import message_to_dict, messages_from_dict
import click

# Import path helpers
from utils.path_helpers import get_agent_memory_dir, get_agent_data_dir

# Type checking imports to avoid circular dependency with main.py or other modules
if TYPE_CHECKING:
    from langchain.agents import AgentExecutor
    from utils.config_loader import ConfigLoader
    from core.agent_loader import load_agent_executor

# Get logger for this module
logger = logging.getLogger(__name__)

# --- Memory File Path Helpers ---

def get_memory_file_path(agent_name_for_mem: str, config_loader: 'ConfigLoader') -> str:
    """Calculates the file path for an agent's chat history JSON file."""
    memory_dir = get_agent_memory_dir(agent_name_for_mem, config_loader)
    return os.path.join(memory_dir, 'chat_history.json')

# --- Memory Management Helpers ---

def get_or_create_memory(
    agent_name: str, 
    agent_memories: Dict[str, ConversationBufferMemory], 
    config_loader: 'ConfigLoader'
) -> ConversationBufferMemory:
    """Gets existing memory from file or creates new memory for an agent."""
    if agent_name in agent_memories:
        logger.info(f"Reusing in-memory buffer for agent '{agent_name}'")
        return agent_memories[agent_name]

    # --- Load from file if exists ---
    memory_file = get_memory_file_path(agent_name, config_loader)
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
    logger.debug(f"Initialized memory for '{agent_name}' with {len(loaded_messages)} messages via ChatMessageHistory.")

    agent_memories[agent_name] = new_memory
    return new_memory

def save_agent_memory(agent_name_to_save: str, memory_to_save: ConversationBufferMemory, config_loader: 'ConfigLoader'):
    """Saves the chat history of a specific agent to its JSON file."""
    memory_file_to_save = get_memory_file_path(agent_name_to_save, config_loader)
    try:
        # Ensure memory directory exists
        os.makedirs(os.path.dirname(memory_file_to_save), exist_ok=True)

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

# --- Command Processing Helper ---

def process_user_command(
    user_input: str, 
    current_agent_name: str, 
    agent_executor: Optional['AgentExecutor'], 
    current_memory: Optional[ConversationBufferMemory], 
    agent_memories: Dict[str, ConversationBufferMemory],
    config_loader: 'ConfigLoader', 
    effective_log_level: int,
    show_tokens: bool
) -> Tuple[str, Optional['AgentExecutor'], Optional[ConversationBufferMemory], bool]:
    """Process user commands and return updated state.
    
    Args:
        user_input: The input command from the user.
        current_agent_name: The current agent's name.
        agent_executor: The current agent's executor.
        current_memory: The current agent's memory.
        agent_memories: A dictionary containing all agent memories.
        config_loader: The configuration loader for the session.
        effective_log_level: The effective logging level for the session.
        show_tokens: Flag indicating whether to show token usage.

    Returns:
        Tuple containing (current_agent_name, agent_executor, current_memory, exit_requested)
    """
    # Import here to avoid circular imports
    from core.agent_loader import load_agent_executor
    
    if user_input.lower() == '/exit':
        logger.info("Exit command received. Ending chat session.")
        click.echo("Exiting chat session.")
        return current_agent_name, agent_executor, current_memory, True  # Signal to exit
        
    elif user_input.lower() == '/summarize':
        logger.info("User requested session summary.")
        if agent_executor and current_memory and current_agent_name and config_loader:
            click.echo("\nGenerating session summary...")
            summary = generate_and_save_summary(
                agent_executor, current_memory, current_agent_name, config_loader
            )
            click.secho("\n--- Session Summary ---", fg="yellow", bold=True)
            click.secho(summary, fg="yellow")
            click.secho("--- End Summary ---\n", fg="yellow", bold=True)
        elif not config_loader:
            click.echo("Error: Cannot generate summary. ConfigLoader not available.", err=True)
        else:
            click.echo("Error: Cannot generate summary. Agent/memory not loaded.", err=True)
        return current_agent_name, agent_executor, current_memory, False
        
    elif user_input.lower().startswith('/agent '):
        new_agent_name = user_input[len('/agent '):].strip()
        if not new_agent_name:
            click.echo("Error: Please specify an agent name after /agent.")
            return current_agent_name, agent_executor, current_memory, False
        
        if new_agent_name == current_agent_name:
            click.echo(f"Already using agent: {current_agent_name}")
            return current_agent_name, agent_executor, current_memory, False

        try:
            # --- Save previous agent's memory BEFORE switching ---
            if current_memory and current_agent_name:
                logger.info(f"Switching agent. Saving current memory for '{current_agent_name}'...")
                save_agent_memory(current_agent_name, current_memory, config_loader)
            
            # --- Load new agent and memory ---
            new_memory = get_or_create_memory(new_agent_name, agent_memories, config_loader)
            # Pass the new_memory object and the callback handler to load_agent_executor
            new_executor = load_agent_executor(
                new_agent_name, 
                config_loader, 
                effective_log_level, 
                new_memory,
            )
            
            # Switch successful
            logger.info(f"Switching to agent: {new_agent_name}")
            click.echo(f"Switched to agent: {new_agent_name}")
            return new_agent_name, new_executor, new_memory, False
            
        except (FileNotFoundError, ValueError) as e:
            logger.warning(f"Failed to switch agent to '{new_agent_name}': {e}")
            click.echo(f"Error: Could not load agent '{new_agent_name}'. Staying with '{current_agent_name}'.", err=True)
        except Exception as e:
            logger.error(f"Unexpected error switching to agent '{new_agent_name}': {e}", exc_info=True)
            click.echo(f"Error: An unexpected error occurred switching to agent '{new_agent_name}'.", err=True)
        
        return current_agent_name, agent_executor, current_memory, False
    
    # Regular input to be processed by the agent
    if not agent_executor or not current_memory:
        click.echo("Error: Agent executor or memory not loaded. Cannot process query.", err=True)
        # Ensure we return the memory object even if executor is missing
        return current_agent_name, agent_executor, current_memory, False

    try:
        # --- Invoke directly. AgentExecutor handles memory now. ---
        # Revert to passing only the primary input. AgentExecutor should manage scratchpad.
        response = agent_executor.invoke({"input": user_input})

        output = response.get('output', 'Error: No output found.')

        # --- No manual save_context needed --- 

        # Use secho for colored output
        click.secho(f"{output}", fg='cyan')

        # --- Display Token Usage if flag is set ---
        if show_tokens:
            # Log the full response for debugging the first time
            logger.debug(f"Full agent response dictionary: {response}") 
            
            # Attempt to extract token usage (keys might vary based on LLM/Langchain version)
            token_usage = None
            if 'llm_output' in response and isinstance(response['llm_output'], dict):
                 # Standard Langchain location?
                 token_usage = response['llm_output'].get('token_usage') 
            elif 'usage_metadata' in response: 
                 # Another possible location (seen with some Google integrations)
                 token_usage = response.get('usage_metadata')

            if token_usage:
                # Format the token usage nicely 
                # Example: {'prompt_tokens': 50, 'completion_tokens': 100, 'total_tokens': 150}
                usage_str = ", ".join([f"{k.replace('_tokens','').capitalize()}: {v}" for k, v in token_usage.items()])
                click.secho(f"[Tokens: {usage_str}]", fg='bright_black') # Use dim color
            else:
                 # Log if usage info wasn't found where expected
                 logger.debug("Token usage information not found in response['llm_output']['token_usage'] or response['usage_metadata'].")

        # Agent processing complete, continue REPL loop
        return current_agent_name, agent_executor, current_memory, False
    except Exception as e:
        logger.error(f"Error during agent execution: {e}", exc_info=True)
        click.echo(f"Error processing query: {e}", err=True)
        
    return current_agent_name, agent_executor, current_memory, False

# --- Session Summary Helper ---

def generate_and_save_summary(
    agent_executor: 'AgentExecutor',
    memory: ConversationBufferMemory,
    agent_name: str,
    config_loader: 'ConfigLoader'
) -> str:
    """Generates a session summary using the agent and saves it to a file."""
    if not agent_executor or not memory:
        logger.warning("Cannot generate summary: agent executor or memory not available.")
        return "" # Return empty if no agent/memory
    if not config_loader:
         logger.error("Cannot save summary: ConfigLoader instance not provided.")
         return "Error: Configuration loader unavailable."


    summary_prompt = (
        "You have been asked to summarize our session based on our conversation history. "
        "Please summarize our session using the following headings:\n"
        "- **Key Topics Discussed:**\n"
        "- **Open Topics:**\n"
        "- **Decisions Made:**\n"
        "- **Agreed-upon Next Steps/Action Items:**\n"
        "This summary is for refreshing context at the start of our next session."
        "IMPORTANT: This response will be written to file by script and retrieved on startup." 
        "You do not need to include any introductory phrases like 'Okay, here is the summary...'"
    )

    summary_text = "Error: Could not generate summary." # Default error message
    try:
        logger.info(f"Requesting session summary from agent '{agent_name}'...")
        # --- Invoke directly for summary. AgentExecutor handles memory. ---
        response = agent_executor.invoke({"input": summary_prompt})

        summary_text = response.get('output', 'Error: Agent did not provide summary output.')
        logger.info(f"Received summary from agent '{agent_name}'. Length: {len(summary_text)}")

        # --- Save the summary to a dedicated file ---
        agent_data_dir = get_agent_data_dir(agent_name, config_loader)
        summary_file_path = os.path.join(agent_data_dir, 'session_log.md')

        try:
            os.makedirs(os.path.dirname(summary_file_path), exist_ok=True) # Ensure directory exists
            with open(summary_file_path, 'w') as f:
                f.write(summary_text)
            logger.info(f"Saved session summary to: {summary_file_path}")
        except IOError as e:
            logger.error(f"Failed to write session summary file {summary_file_path}: {e}")
            # Don't overwrite summary_text here, we still want to return what the agent generated

    except Exception as e:
        logger.error(f"Error generating or saving session summary for agent '{agent_name}': {e}", exc_info=True)
        # Keep the default error message in summary_text

    return summary_text
