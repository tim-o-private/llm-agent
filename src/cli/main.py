import click
import os
import logging

# Add src to path for direct script execution (optional, depends on setup)
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from utils.config_loader import ConfigLoader
from core.context_manager import ContextManager
from core.llm_interface import LLMInterface

# --- Basic Logging Setup ---
# Configure this properly later based on settings
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration Loading ---
# Load configuration globally for the CLI application
# TODO: Consider making ConfigLoader a singleton or passing it via context
config_loader = ConfigLoader()

# --- CLI Command Group ---
@click.group()
def cli():
    """Local LLM Terminal Environment CLI."""
    pass

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
    help='Enable verbose logging.'
)
def ask(query: str, agent: str | None, verbose: bool):
    """Ask a question to the LLM, providing context from the specified agent."""
    
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled.")

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

# --- Entry Point ---
if __name__ == '__main__':
    cli()
