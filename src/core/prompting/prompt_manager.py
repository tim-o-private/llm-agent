import asyncio
from typing import Any, Dict, List, Optional

import httpx


# Assuming Pydantic models from chatServer.main are available or redefined here
# For a real setup, these might be in a shared library or generated from OpenAPI spec
class PromptCustomization(Dict[str, Any]): # Simplified for client
    pass

class PromptManagerService:
    def __init__(self, base_url: str, auth_token_provider: callable):
        """
        Initializes the PromptManagerService.
        base_url: The base URL of the chatServer (e.g., http://localhost:8000).
        auth_token_provider: A callable that returns the current JWT auth token.
        """
        self.base_url = base_url.rstrip('/')
        self.auth_token_provider = auth_token_provider
        self.client = httpx.AsyncClient()

    async def _get_headers(self) -> Dict[str, str]:
        token_result = self.auth_token_provider()
        if asyncio.iscoroutine(token_result):
            token = await token_result
        else:
            token = token_result

        if not token:
            raise ValueError("Auth token is not available.")
        return {"Authorization": f"Bearer {token}"}

    async def get_customizations(self, agent_name: str) -> List[PromptCustomization]:
        """Fetches active prompt customizations for a given agent and user."""
        try:
            headers = await self._get_headers()
            response = await self.client.get(
                f"{self.base_url}/api/agent/prompt_customizations/{agent_name}",
                headers=headers
            )
            response.raise_for_status() # Raise an exception for HTTP errors
            return response.json()
        except httpx.HTTPStatusError:
            # print(f"HTTP error fetching customizations for {agent_name}: {e.response.status_code} - {e.response.text}") # Proper logging
            # Depending on desired behavior, could return empty list or re-raise a custom exception
            return []
        except Exception:
            # print(f"Error fetching customizations for {agent_name}: {e}") # Proper logging
            return []

    async def add_customization(self, agent_name: str, customization_type: str, content: Dict[str, Any], priority: int = 0, is_active: bool = True) -> Optional[PromptCustomization]:
        """Adds a new prompt customization for the agent and user."""
        payload = {
            "agent_name": agent_name,
            "customization_type": customization_type,
            "content": content,
            "is_active": is_active,
            "priority": priority
        }
        try:
            headers = await self._get_headers()
            response = await self.client.post(
                f"{self.base_url}/api/agent/prompt_customizations/",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError:
            # print(f"HTTP error adding customization for {agent_name}: {e.response.status_code} - {e.response.text}")
            return None
        except Exception:
            # print(f"Error adding customization for {agent_name}: {e}")
            return None

    async def update_customization(self, customization_id: str, agent_name: str, customization_type: str, content: Dict[str, Any], priority: int, is_active: bool) -> Optional[PromptCustomization]:
        """Updates an existing prompt customization."""
        payload = {
            "agent_name": agent_name, # Though agent_name is part of URL, sending in body for Pydantic model
            "customization_type": customization_type,
            "content": content,
            "is_active": is_active,
            "priority": priority
        }
        try:
            headers = await self._get_headers()
            response = await self.client.put(
                f"{self.base_url}/api/agent/prompt_customizations/{customization_id}",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError:
            # print(f"HTTP error updating customization {customization_id}: {e.response.status_code} - {e.response.text}")
            return None
        except Exception:
            # print(f"Error updating customization {customization_id}: {e}")
            return None

    async def close(self):
        await self.client.aclose()

# Example Usage (conceptual, depends on how auth_token_provider is implemented and how asyncio loop is managed):
# async def example_auth_provider():
#     # In a real app, this would fetch a valid JWT token
#     return "your_jwt_token_here"

# async def main():
#     manager = PromptManagerService(base_url="http://localhost:8000", auth_token_provider=example_auth_provider)
#     customizations = await manager.get_customizations(agent_name="test_agent")
#     print("Fetched Customizations:", customizations)
#
#     # new_cust = await manager.add_customization(
#     #     agent_name="test_agent",
#     #     customization_type="instruction_set",
#     #     content={"instructions": ["Always be polite", "Summarize in 3 sentences"]}
#     # )
#     # print("Added Customization:", new_cust)
#     await manager.close()

# if __name__ == "__main__":
# import asyncio
# asyncio.run(main())
