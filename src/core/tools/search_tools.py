import logging
from langchain_community.tools import DuckDuckGoSearchRun
from duckduckgo_search.exceptions import DuckDuckGoSearchException

logger = logging.getLogger(__name__)

class SafeDuckDuckGoSearchRun(DuckDuckGoSearchRun):
    """
    A wrapper around DuckDuckGoSearchRun that catches exceptions
    and returns a user-friendly error message.
    """
    def _run(self, query: str) -> str:
        try:
            return super()._run(query)
        except DuckDuckGoSearchException as e:
            logger.error(f"DuckDuckGoSearchRun failed: {e}")
            # Return a friendly message to the LLM
            return "DuckDuckGo search failed due to a technical issue (e.g., rate limit or network problem). Please try again later or ask for something else."
        except Exception as e:
            # Catch any other unexpected errors from the tool
            logger.error(f"An unexpected error occurred in DuckDuckGoSearchRun: {e}", exc_info=True)
            return "An unexpected error occurred while trying to search with DuckDuckGo. Please inform the user."

    # If you also use arun, you might want to implement _arun similarly:
    # async def _arun(self, query: str) -> str:
    #     try:
    #         return await super()._arun(query)
    #     except DuckDuckGoSearchException as e:
    #         logger.error(f"DuckDuckGoSearchRun (async) failed: {e}")
    #         return "DuckDuckGo search failed due to a technical issue (e.g., rate limit or network problem). Please try again later or ask for something else."
    #     except Exception as e:
    #         logger.error(f"An unexpected error occurred in DuckDuckGoSearchRun (async): {e}", exc_info=True)
    #         return "An unexpected error occurred while trying to search with DuckDuckGo. Please inform the user." 