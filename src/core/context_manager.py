import os
import logging
import yaml
from typing import Dict, List, Tuple
from utils.config_loader import ConfigLoader
from core.file_parser import read_markdown, read_yaml

# Configure logging
logger = logging.getLogger(__name__)

class ContextManager:
    """
    Gathers and formats context from global and agent-specific files.
    """
    def __init__(self, config: ConfigLoader):
        self.config = config
        self.base_data_dir = self.config.get('data.base_dir', 'data/')
        self.global_context_dir = os.path.join(
            self.base_data_dir, 
            self.config.get('data.global_context_dir', 'global_context/')
        )
        self.agents_dir = os.path.join(
            self.base_data_dir, 
            self.config.get('data.agents_dir', 'agents/')
        )

    def _read_context_files(self, directory: str) -> Dict[str, str | Dict]:
        """Reads all .md and .yaml/.yml files in a directory."""
        context_data = {}
        if not os.path.isdir(directory):
            logger.warning(f"Context directory not found: {directory}")
            return context_data
            
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if not os.path.isfile(filepath):
                continue
                
            base_name, extension = os.path.splitext(filename)
            
            try:
                if extension == '.md':
                    context_data[base_name] = read_markdown(filepath)
                elif extension in ['.yaml', '.yml']:
                    context_data[base_name] = read_yaml(filepath)
            except FileNotFoundError:
                # Should not happen if os.path.isfile is true, but defensive
                logger.warning(f"File disappeared while reading context: {filepath}")
            except (IOError, yaml.YAMLError) as e:
                logger.error(f"Error reading context file {filepath}: {e}")
                # Decide if we want to skip this file or raise
                # For now, log and skip
            except Exception as e:
                logger.error(f"Unexpected error reading context file {filepath}: {e}")
                # Log and skip
        return context_data

    def _format_context(self, context_data: Dict[str, str | Dict], section_title: str) -> str:
        """Formats context data into a Markdown string section."""
        formatted_string = f"## {section_title}\n\n"
        if not context_data:
            formatted_string += "No data found.\n"
            return formatted_string
            
        for key, content in context_data.items():
            formatted_key = key.replace('_', ' ').title()
            formatted_string += f"### {formatted_key}\n"
            if isinstance(content, dict):
                # Basic YAML dict formatting
                formatted_string += "```yaml\n"
                formatted_string += yaml.dump(content, default_flow_style=False)
                formatted_string += "```\n\n"
            else:
                # Assume string (Markdown content)
                formatted_string += f"{content}\n\n"
        return formatted_string

    def get_context(self, agent_name: str | None = None) -> Tuple[Dict, str]:
        """
        Gathers context from global and optional agent directories.

        Args:
            agent_name: The name of the agent subdirectory (e.g., 'agent_a') 
                        or None to load only global context.

        Returns:
            A tuple containing:
            - A dictionary with the raw context data ('global', 'agent').
            - A formatted string suitable for passing to the LLM.
        """
        raw_context = {'global': {}, 'agent': {}}
        formatted_context_parts = []

        # --- Load Global Context --- 
        logger.info(f"Loading global context from: {self.global_context_dir}")
        global_context_data = self._read_context_files(self.global_context_dir)
        raw_context['global'] = global_context_data
        if global_context_data:
            formatted_context_parts.append(
                self._format_context(global_context_data, "Global Context")
            )

        # --- Load Agent Context ---
        if agent_name:
            agent_dir = os.path.join(self.agents_dir, agent_name)
            logger.info(f"Loading agent context from: {agent_dir}")
            agent_context_data = self._read_context_files(agent_dir)
            raw_context['agent'] = agent_context_data
            if agent_context_data:
                 formatted_context_parts.append(
                    self._format_context(agent_context_data, f"Agent Context: {agent_name}")
                )
            else:
                # Log warning if agent specified but no context found
                logger.warning(f"Agent context directory specified ({agent_dir}) but no valid context files found.")
                # Add a note to the formatted context
                formatted_context_parts.append(f"## Agent Context: {agent_name}\n\nNo context files found for this agent.\n")
        
        # Combine formatted parts
        full_formatted_context = "\n".join(formatted_context_parts).strip()
        
        logger.debug(f"Raw context loaded: {raw_context}")
        logger.debug(f"Formatted context: \n{full_formatted_context}")

        return raw_context, full_formatted_context
