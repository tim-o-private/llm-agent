from typing import Any, Dict, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# Assuming PromptManagerService is in src.core.prompting
# Adjust import path as necessary based on your project structure
from core.prompting.prompt_manager import PromptManagerService


class UpdateSelfInstructionsInput(BaseModel):
    agent_name: str = Field(description="The name of the agent whose instructions are to be updated.")
    instruction_change_proposal: Dict[str, Any] = Field(description="A dictionary representing the proposed changes or additions to instructions. Example: {'instructions': ['New instruction 1', 'New instruction 2']}")  # noqa: E501
    customization_type: str = Field(default='instruction_set', description="The type of customization, e.g., 'instruction_set'.")  # noqa: E501
    # customization_id: Optional[str] = Field(None, description="Optional ID of an existing customization to update. If None, a new one might be created or an existing one of type 'instruction_set' updated based on service logic.")  # noqa: E501

class UpdateSelfInstructionsTool(BaseTool):
    name: str = "update_self_instructions"
    description: str = (
        "Allows the agent to propose updates or additions to its own persistent instructions or behaviors. "
        "Use this to remember user preferences or adapt your core instructions over time. "
        "The 'instruction_change_proposal' should be a dictionary, typically with an 'instructions' key holding a list of strings."  # noqa: E501
    )
    args_schema: Type[BaseModel] = UpdateSelfInstructionsInput
    prompt_manager: PromptManagerService
    # user_id and agent_name will be implicitly handled by PromptManagerService context if needed,
    # or passed during tool construction if the service needs them explicitly per call.

    # This tool is async because PromptManagerService methods are async
    async def _arun(
        self,
        agent_name: str,
        instruction_change_proposal: Dict[str, Any],
        customization_type: str = 'instruction_set',
        # customization_id: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Use the tool asynchronously."""
        # In a multi-customization scenario, we might need to fetch existing, find the right one, then update.
        # For MVP, assume we add a new one or update the primary 'instruction_set' type.

        # Attempt to find an existing customization of this type for this agent
        existing_customizations = await self.prompt_manager.get_customizations(agent_name=agent_name)
        target_customization_id = None
        existing_content = {}

        for cust in existing_customizations:
            if cust.get("agent_name") == agent_name and cust.get("customization_type") == customization_type:
                target_customization_id = cust.get("id")
                existing_content = cust.get("content", {})
                break

        # Simple merge: overwrite or add. A more complex merge could be implemented.
        # For "instruction_set", if proposal has "instructions" list, replace/add.
        # This merge strategy needs to be robust.
        updated_content = existing_content.copy()
        if customization_type == 'instruction_set' and 'instructions' in instruction_change_proposal:
            # Example: replace instructions entirely, or append. For now, replace.
            updated_content["instructions"] = instruction_change_proposal["instructions"]
        else:
            # Generic update for other types or if proposal is structured differently
            updated_content.update(instruction_change_proposal)

        if target_customization_id:
            # Update existing
            # print(f"Updating customization ID: {target_customization_id} for agent {agent_name}")
            result = await self.prompt_manager.update_customization(
                customization_id=target_customization_id,
                agent_name=agent_name, # Required by Pydantic model on server, even if redundant
                customization_type=customization_type,
                content=updated_content,
                priority=0, # Keep existing or default priority
                is_active=True
            )
            if result:
                return f"Successfully updated instructions for agent '{agent_name}'. New content: {result.get('content')}"  # noqa: E501
            else:
                return f"Failed to update instructions for agent '{agent_name}'. The existing instruction set might not have been found or an error occurred."  # noqa: E501
        else:
            # Add new if no existing one of this type was found
            # print(f"Adding new customization for agent {agent_name}")
            result = await self.prompt_manager.add_customization(
                agent_name=agent_name,
                customization_type=customization_type,
                content=updated_content, # Use the merged/updated content
                priority=0,
                is_active=True
            )
            if result:
                return f"Successfully added new instructions for agent '{agent_name}'. Content: {result.get('content')}"
            else:
                return f"Failed to add new instructions for agent '{agent_name}'."

    # Synchronous version is not strictly needed if AgentExecutor handles async tools.
    # If required, it would need a synchronous version of PromptManagerService or run_in_executor.
    def _run(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError("update_self_instructions tool does not support synchronous execution.")
