"""Prompt customization service for handling prompt management logic."""

import logging
from typing import Any, List

from fastapi import HTTPException, status

try:
    from ..models.prompt_customization import PromptCustomization, PromptCustomizationCreate
except ImportError:
    from models.prompt_customization import PromptCustomization, PromptCustomizationCreate

logger = logging.getLogger(__name__)


class PromptCustomizationService:
    """Service for handling prompt customization operations."""

    def __init__(self):
        """Initialize the prompt customization service."""
        pass

    async def create_prompt_customization(
        self,
        customization_data: PromptCustomizationCreate,
        user_id: str,
        supabase_client: Any
    ) -> PromptCustomization:
        """Create a new prompt customization.

        Args:
            customization_data: The prompt customization data
            user_id: User ID
            supabase_client: Supabase client instance

        Returns:
            Created prompt customization

        Raises:
            HTTPException: If creation fails
        """
        try:
            response = await supabase_client.table("user_agent_prompt_customizations").insert({
                "user_id": user_id,
                "agent_name": customization_data.agent_name,
                "customization_type": customization_data.customization_type,
                "content": customization_data.content,
                "is_active": customization_data.is_active,
                "priority": customization_data.priority
            }).execute()

            if response.data:
                return response.data[0]
            else:
                error_msg = response.error.message if response.error else 'Unknown error'
                logger.error(f"Failed to create prompt customization: {error_msg}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create prompt customization"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating prompt customization: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    async def get_prompt_customizations_for_agent(
        self,
        agent_name: str,
        user_id: str,
        supabase_client: Any
    ) -> List[PromptCustomization]:
        """Get prompt customizations for a specific agent.

        Args:
            agent_name: Name of the agent
            user_id: User ID
            supabase_client: Supabase client instance

        Returns:
            List of prompt customizations

        Raises:
            HTTPException: If fetching fails
        """
        try:
            response = await supabase_client.table("user_agent_prompt_customizations") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("agent_name", agent_name) \
                .eq("is_active", True) \
                .order("priority", desc=False) \
                .execute()

            if response.data:
                return response.data
            return []
        except Exception as e:
            logger.error(f"Error fetching prompt customizations for agent {agent_name}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    async def update_prompt_customization(
        self,
        customization_id: str,
        customization_data: PromptCustomizationCreate,
        user_id: str,
        supabase_client: Any
    ) -> PromptCustomization:
        """Update an existing prompt customization.

        Args:
            customization_id: ID of the customization to update
            customization_data: Updated customization data
            user_id: User ID
            supabase_client: Supabase client instance

        Returns:
            Updated prompt customization

        Raises:
            HTTPException: If update fails or customization not found
        """
        try:
            # RLS will ensure the user can only update their own records.
            # We select user_id in the update to ensure it's part of the WHERE clause enforced by RLS implicitly.
            update_payload = customization_data.model_dump()
            update_payload["updated_at"] = "now()"  # Let database update timestamp

            response = await supabase_client.table("user_agent_prompt_customizations") \
                .update(update_payload) \
                .eq("id", customization_id) \
                .eq("user_id", user_id) \
                .execute()

            if response.data:
                return response.data[0]
            elif response.error and response.error.code == 'PGRST116':  # PGRST116: Row not found
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Prompt customization not found or access denied"
                )
            else:
                error_msg = response.error.message if response.error else 'Unknown error or no rows updated'
                logger.error(f"Failed to update prompt customization {customization_id}: {error_msg}")
                # If no data and no specific error, it might mean the record wasn't found or RLS prevented update without erroring differently.
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Prompt customization not found, access denied, or no changes made."
                )
        except HTTPException:  # Re-raise HTTP exceptions directly
            raise
        except Exception as e:
            logger.error(f"Error updating prompt customization {customization_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


# Global instance for use in main.py
_prompt_customization_service: PromptCustomizationService = None


def get_prompt_customization_service() -> PromptCustomizationService:
    """Get the global prompt customization service instance.

    Returns:
        Prompt customization service instance
    """
    global _prompt_customization_service
    if _prompt_customization_service is None:
        _prompt_customization_service = PromptCustomizationService()
    return _prompt_customization_service
