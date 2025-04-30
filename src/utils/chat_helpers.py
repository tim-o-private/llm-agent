import os
import json
import logging
from typing import TYPE_CHECKING

# Langchain imports needed by helper functions
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import message_to_dict

# Type checking imports to avoid circular dependency with main.py or other modules
if TYPE_CHECKING:
    from langchain.agents import AgentExecutor
    from utils.config_loader import ConfigLoader

# Get logger for this module
logger = logging.getLogger(__name__)

# Define config_loader globally ONLY for get_memory_file_path's current structure.
# Ideally, config_loader would be passed explicitly to get_memory_file_path as well.
# TODO: Refactor get_memory_file_path to accept config_loader instance.
try:
    # Attempt to import and instantiate ConfigLoader for the standalone helper
    # This might need adjustment based on project structure/entry points
    from utils.config_loader import ConfigLoader
    config_loader = ConfigLoader()
except ImportError:
    logger.warning("Could not import ConfigLoader in chat_helpers. May affect get_memory_file_path.")
    config_loader = None # Allow functions to degrade gracefully if needed

# --- Memory Handling Helpers ---

def get_memory_file_path(agent_name_for_mem: str) -> str:
    """Calculates the file path for an agent's chat history JSON file."""
    # TODO: This function currently relies on a globally loaded config_loader.
    # It should ideally accept config_loader as an argument for better testability
    # and explicit dependency management.
    if not config_loader:
        # Fallback or raise error if config_loader couldn't be imported/instantiated
        raise RuntimeError("ConfigLoader instance not available for get_memory_file_path.")

    agent_data_dir = os.path.join(
        config_loader.get('data.base_dir', 'data/'),
        config_loader.get('data.agents_dir', 'agents/'),
        agent_name_for_mem
    )
    memory_dir = os.path.join(agent_data_dir, 'memory')
    return os.path.join(memory_dir, 'chat_history.json')

def save_agent_memory(agent_name_to_save: str, memory_to_save: ConversationBufferMemory):
    """Saves the chat history of a specific agent to its JSON file."""
    # Note: This function calls get_memory_file_path, inheriting its dependency on global config_loader
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

# --- Session Summary Helper ---

def generate_and_save_summary(
    agent_executor: 'AgentExecutor',
    memory: ConversationBufferMemory,
    agent_name: str,
    config_loader: 'ConfigLoader' # Explicitly require config_loader here
) -> str:
    """Generates a session summary using the agent and saves it to a file."""
    if not agent_executor or not memory:
        logger.warning("Cannot generate summary: agent executor or memory not available.")
        return "" # Return empty if no agent/memory
    if not config_loader:
         logger.error("Cannot save summary: ConfigLoader instance not provided.")
         return "Error: Configuration loader unavailable."


    summary_prompt = (
        "You have been asked to summarize our session. Please begin by reviewing `session_log.md.`"
        "After reviewing, summarize our session and provide an update for the session log using the following headings:"
        "- **Key Topics Discussed:**"
        "- **Open Topics:**"
        "- **Decisions Made:**"
        "- **Agreed-upon Next Steps/Action Items:**"
        "This summary is for refreshing context at the start of our next session."
        "IMPORTANT: This response will be written to file by script and retrieved on startup." 
        "You do not need to include any introductory phrases like 'Okay, here is the summary...'"
    )

    summary_text = "Error: Could not generate summary." # Default error message
    try:
        logger.info(f"Requesting session summary from agent '{agent_name}'...")
        # Load history manually
        loaded_memory_vars = memory.load_memory_variables({})
        history_messages = loaded_memory_vars.get("chat_history", [])

        # Invoke agent with summary prompt and history
        response = agent_executor.invoke({
            "input": summary_prompt,
            "chat_history": history_messages
        })

        summary_text = response.get('output', 'Error: Agent did not provide summary output.')
        logger.info(f"Received summary from agent '{agent_name}'. Length: {len(summary_text)}")

        # --- Save the summary to a dedicated file ---
        agent_data_dir = os.path.join(
            config_loader.get('data.base_dir', 'data/'),
            config_loader.get('data.agents_dir', 'agents/'),
            agent_name,
            memory,
        )
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