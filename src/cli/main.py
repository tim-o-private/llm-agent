import click
import os
import logging
import yaml
from typing import Dict
from langchain.memory import ConversationBufferMemory
from prompt_toolkit import prompt as prompt_toolkit_prompt
from prompt_toolkit.history import InMemoryHistory
# Hack. Remove after packaging.
import sys
from utils.config_loader import ConfigLoader
from core.agent_loader import load_agent_executor
from utils.chat_helpers import (
    save_agent_memory,
    generate_and_save_summary,
    get_or_create_memory,
    process_user_command
)

# --- Basic Logging Setup ---
# Set format only, level will be set dynamically
logging.basicConfig(format='[%(asctime)s] %(levelname)s [%(name)s] - %(message)s')
logger = logging.getLogger(__name__) # Get root logger or specific module logger

# --- CLI Command Group ---
@click.group(invoke_without_command=True)
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

    # Create a context object if it doesn't exist
    ctx.ensure_object(dict)
    
    # Store the chosen level and config_loader in the context object
    ctx.obj['LOG_LEVEL'] = level
    ctx.obj['config_loader'] = ConfigLoader()
    
    # If no command is specified, run the chat command
    if ctx.invoked_subcommand is None:
        ctx.invoke(chat)

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
@click.option(
    '--show-tokens', '-t',
    is_flag=True,
    default=False, # Default to not showing tokens
    help='Display token usage after each agent response.'
)
@click.pass_context # Pass context to command function
def chat(ctx, agent: str, verbose: bool, show_tokens: bool):
    """Start an interactive chat session (REPL) with an agent."""
    
    effective_log_level = logging.DEBUG if verbose else ctx.obj['LOG_LEVEL']
    if verbose:
        # Note: We set the root logger level here, affecting all modules
        logging.getLogger().setLevel(effective_log_level)
        logger.debug("Verbose logging enabled (--verbose). Overriding log level.")
    # Otherwise, the level set by the cli group function is used.

    logger.info(f"Starting chat session with agent: {agent}")
    click.echo(f"Starting interactive chat with agent '{agent}'. Type /exit to quit.")
    click.echo("Other commands: /agent <name>, /summarize")

    # Get config_loader from context
    config_loader = ctx.obj.get('config_loader')
    if not config_loader:
        logger.error("ConfigLoader not available in context.")
        click.echo("Error: Configuration not available.", err=True)
        return

    current_agent_name = agent
    agent_executor = None
    agent_memories: Dict[str, ConversationBufferMemory] = {}
    current_memory = None

    try:
        # --- Load initial agent and memory ---
        # 1. Get/Create memory first
        current_memory = get_or_create_memory(current_agent_name, agent_memories, config_loader)
        # 2. Load executor, passing the created memory object
        agent_executor = load_agent_executor(
            current_agent_name, 
            config_loader, 
            effective_log_level, 
            current_memory,
        )

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

            # Process user commands and regular input
            current_agent_name, agent_executor, current_memory, exit_requested = process_user_command(
                user_input, current_agent_name, agent_executor, current_memory, 
                agent_memories, config_loader, effective_log_level,
                show_tokens=show_tokens # Pass the flag value
            )
            
            if exit_requested:
                break

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Ending chat session.")
        click.echo("\nExiting chat session.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during chat: {e}", exc_info=True)
        click.echo(f"\nAn unexpected error occurred: {e}", err=True)
    finally:
        # --- Generate and Save Final Summary ---
        if agent_executor and current_memory and current_agent_name and config_loader:
             logger.info("Generating final session summary before exit...")
             click.echo("\nGenerating final session summary...")
             # Use imported helper
             summary = generate_and_save_summary(
                 agent_executor, current_memory, current_agent_name, config_loader
             )
             # Only print if summary generation didn't return an error message starting with "Error:"
             if summary and not summary.startswith("Error:"):
                 click.secho("\n--- Final Session Summary ---", fg="yellow", bold=True)
                 click.secho(summary, fg="yellow")
                 click.secho("--- End Summary ---\n", fg="yellow", bold=True)
             elif summary: # Print error if summary generation failed but returned something
                 click.secho(f"\n{summary}\n", fg="red") # Print summary generation errors in red
             # Otherwise, if summary is empty, log warning handled in helper
        elif not config_loader:
             logger.warning("Could not generate final summary: ConfigLoader not available.")

        # --- Save all memories on exit using the helper function ---
        logger.info("Chat session ending. Saving chat histories...")
        for agent_name_to_save, memory_to_save in agent_memories.items():
             # Use imported helper
             save_agent_memory(agent_name_to_save, memory_to_save, config_loader) # Call helper
        
        logger.info("Finished saving chat histories.")
        pass # Keep the pass here

# --- Entry Point ---
if __name__ == '__main__':
    cli()
