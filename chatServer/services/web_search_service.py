"""Web search service with swappable provider abstraction (DuckDuckGo or Tavily)."""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class WebSearchService:
    """Web search with swappable providers (DuckDuckGo or Tavily)."""

    PROVIDERS = ("duckduckgo", "tavily")

    def __init__(self, max_results: int = 10, provider: Optional[str] = None):
        self.max_results = max_results
        self.provider = provider or os.getenv("WEB_SEARCH_PROVIDER", "duckduckgo")
        if self.provider not in self.PROVIDERS:
            raise ValueError(f"Unknown search provider '{self.provider}'. Use: {self.PROVIDERS}")

    async def search(self, query: str, max_results: int | None = None) -> list[dict]:
        """Search and return normalized results.

        Returns:
            List of dicts with keys: title, url, snippet.
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty.")
        if len(query) > 500:
            raise ValueError("Search query must be 500 characters or fewer.")

        limit = min(max_results or self.max_results, 10)

        if self.provider == "tavily":
            return await self._search_tavily(query, limit)
        return await self._search_duckduckgo(query, limit)

    async def _search_duckduckgo(self, query: str, limit: int) -> list[dict]:
        from duckduckgo_search import DDGS

        try:
            ddgs = DDGS()
            results = ddgs.text(query, max_results=limit)
            return [
                {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
                for r in results
            ]
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            raise

    async def _search_tavily(self, query: str, limit: int) -> list[dict]:
        from tavily import TavilyClient

        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY environment variable is required when using Tavily provider.")
        try:
            client = TavilyClient(api_key=api_key)
            response = client.search(query=query, max_results=limit)
            return [
                {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
                for r in response.get("results", [])
            ]
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            raise
