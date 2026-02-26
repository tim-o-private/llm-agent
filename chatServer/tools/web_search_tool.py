"""Web search tool for agent integration.

Provides SearchWebTool for LangChain agents. Follows SPEC-016 verb_resource naming.
"""

import logging
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SearchWebInput(BaseModel):
    """Input schema for search_web tool."""

    query: str = Field(..., description="The search query to look up on the web", min_length=1, max_length=500)
    max_results: int = Field(5, ge=1, le=10, description="Number of results to return (1-10)")


class SearchWebTool(BaseTool):
    """Search the web for current information."""

    name: str = "search_web"
    description: str = (
        "Search the web for current information. "
        "Returns titles, URLs, and snippets. Use this when the user asks about "
        "current events, documentation, recent news, or anything requiring "
        "up-to-date web information."
    )
    args_schema: Type[BaseModel] = SearchWebInput

    user_id: str
    agent_name: Optional[str] = None

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        """Return behavioral guidance for the agent prompt."""
        return (
            "Web Search: Use search_web when the user asks about current events, "
            "documentation, recent news, product information, or anything that "
            "requires up-to-date information from the web. Do not guess at facts "
            "you are unsure about — search first."
        )

    def _run(self, query: str, max_results: int = 5) -> str:
        return "search_web requires async execution. Use _arun."

    async def _arun(self, query: str, max_results: int = 5) -> str:
        from ..services.web_search_service import WebSearchService

        try:
            service = WebSearchService()
            results = await service.search(query=query, max_results=max_results)

            if not results:
                return f'No results found for "{query}". Try rephrasing your search.'

            lines = [f'Found {len(results)} result(s) for "{query}":\n']
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                url = r.get("url", "")
                snippet = r.get("snippet", "")
                lines.append(f"{i}. **{title}**")
                if url:
                    lines.append(f"   {url}")
                if snippet:
                    lines.append(f"   {snippet}")
                lines.append("")

            return "\n".join(lines)

        except ValueError as e:
            return f"Invalid search query: {e}"
        except Exception as e:
            logger.error(f"search_web failed for user {self.user_id}: {e}")
            return "Web search is temporarily unavailable. Please try again later."
