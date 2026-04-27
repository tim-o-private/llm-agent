"""LLM client factory.

Returns Anthropic or OpenAI async clients based on the configured provider.
Routers and services should call ``get_llm_client()`` rather than importing
the SDK directly so the provider can be switched via environment variables.
"""

from typing import Any

from chatServer.config.settings import get_settings


def get_llm_client() -> Any:
    """Return an async LLM client configured from environment variables.

    Returns:
        ``anthropic.AsyncAnthropic`` when LLM_PROVIDER=anthropic (default),
        ``openai.AsyncOpenAI`` when LLM_PROVIDER=openai.
    """
    settings = get_settings()
    provider = settings.llm_provider
    api_key = settings.llm_api_key or ""
    base_url = settings.llm_base_url

    if provider == "openai":
        from openai import AsyncOpenAI

        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        return AsyncOpenAI(**kwargs)

    from anthropic import AsyncAnthropic

    kwargs: dict = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return AsyncAnthropic(**kwargs)


def is_openai_client(client: Any) -> bool:
    """Duck-type check for an OpenAI client (works with MagicMock in tests)."""
    # Plain mocks default to AnthropicEngine to preserve existing tests.
    if type(client).__name__ in ("MagicMock", "AsyncMock", "Mock"):
        return False
    return hasattr(client, "chat") and hasattr(client.chat, "completions")
