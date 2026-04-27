"""LLM provider configuration.

Centralises provider, base URL, API key, and default model so the rest of
 the codebase can switch between Anthropic and OpenAI-compatible endpoints
without hard-coding vendor-specific values.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LLMConfig:
    provider: str          # "anthropic" | "openai"
    base_url: Optional[str]
    api_key: str
    default_model: str

    @property
    def client_kwargs(self) -> dict:
        kwargs: dict = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return kwargs

    @property
    def deep_agent_prefix(self) -> str:
        return "anthropic" if self.provider == "anthropic" else "openai"


def get_llm_config() -> LLMConfig:
    """Read LLM configuration from environment.

    Env vars (all optional unless otherwise noted):
      LLM_PROVIDER      – "anthropic" (default) or "openai"
      LLM_BASE_URL      – e.g. https://opencode.ai/zen/go/v1
      LLM_API_KEY       – primary key; falls back to ANTHROPIC_API_KEY / OPENAI_API_KEY
      LLM_DEFAULT_MODEL – model id, e.g. "claude-sonnet-4-5-20250514" or "kimi-k2.6"
    """
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    base_url = os.getenv("LLM_BASE_URL") or None

    api_key = (
        os.getenv("LLM_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    )

    default_model = os.getenv("LLM_DEFAULT_MODEL")
    if not default_model:
        default_model = (
            "claude-sonnet-4-5-20250514"
            if provider == "anthropic"
            else "kimi-k2.6"
        )

    return LLMConfig(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        default_model=default_model,
    )
