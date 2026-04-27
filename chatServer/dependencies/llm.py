"""FastAPI dependency for LLM client injection.

Tests override with ``app.dependency_overrides[get_llm_client_dep]``.
"""

from typing import Any


def get_llm_client_dep() -> Any:
    """Return an async LLM client configured from environment variables.

    The concrete type (Anthropic or OpenAI) is determined by ``LLM_PROVIDER``.
    """
    from chatServer.services.llm_client import get_llm_client

    return get_llm_client()
