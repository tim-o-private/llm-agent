"""Tests for llm_config.py — LLMConfig dataclass and get_llm_config factory."""

import os
from unittest.mock import patch

import pytest

from chatServer.config.llm_config import LLMConfig, get_llm_config


# ---------------------------------------------------------------------------
# LLMConfig dataclass
# ---------------------------------------------------------------------------

class TestLLMConfig:
    def test_client_kwargs_with_base_url(self):
        cfg = LLMConfig(provider="openai", base_url="https://api.example.com", api_key="k", default_model="m")
        assert cfg.client_kwargs == {"api_key": "k", "base_url": "https://api.example.com"}

    def test_client_kwargs_without_base_url(self):
        cfg = LLMConfig(provider="anthropic", base_url=None, api_key="k", default_model="m")
        assert cfg.client_kwargs == {"api_key": "k"}

    def test_deep_agent_prefix_anthropic(self):
        cfg = LLMConfig(provider="anthropic", base_url=None, api_key="", default_model="")
        assert cfg.deep_agent_prefix == "anthropic"

    def test_deep_agent_prefix_openai(self):
        cfg = LLMConfig(provider="openai", base_url=None, api_key="", default_model="")
        assert cfg.deep_agent_prefix == "openai"

    def test_frozen(self):
        cfg = LLMConfig(provider="anthropic", base_url=None, api_key="k", default_model="m")
        with pytest.raises(AttributeError):
            cfg.provider = "openai"


# ---------------------------------------------------------------------------
# get_llm_config — env-driven factory
# ---------------------------------------------------------------------------

class TestGetLlmConfig:
    @patch.dict(os.environ, {}, clear=True)
    def test_defaults_to_anthropic(self):
        cfg = get_llm_config()
        assert cfg.provider == "anthropic"
        assert cfg.default_model == "claude-sonnet-4-5-20250514"
        assert cfg.base_url is None
        assert cfg.api_key == ""

    @patch.dict(os.environ, {"LLM_PROVIDER": "openai"}, clear=True)
    def test_openai_provider_defaults(self):
        cfg = get_llm_config()
        assert cfg.provider == "openai"
        assert cfg.default_model == "kimi-k2.6"

    @patch.dict(os.environ, {"LLM_PROVIDER": "OpenAI"}, clear=True)
    def test_provider_case_insensitive(self):
        cfg = get_llm_config()
        assert cfg.provider == "openai"

    @patch.dict(os.environ, {"LLM_API_KEY": "primary-key"}, clear=True)
    def test_primary_api_key(self):
        cfg = get_llm_config()
        assert cfg.api_key == "primary-key"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "ant-key"}, clear=True)
    def test_fallback_to_anthropic_key(self):
        cfg = get_llm_config()
        assert cfg.api_key == "ant-key"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "oai-key"}, clear=True)
    def test_fallback_to_openai_key(self):
        cfg = get_llm_config()
        assert cfg.api_key == "oai-key"

    @patch.dict(os.environ, {
        "LLM_API_KEY": "primary",
        "ANTHROPIC_API_KEY": "ant",
        "OPENAI_API_KEY": "oai",
    }, clear=True)
    def test_primary_key_takes_precedence(self):
        cfg = get_llm_config()
        assert cfg.api_key == "primary"

    @patch.dict(os.environ, {"LLM_BASE_URL": "https://custom/v1"}, clear=True)
    def test_base_url(self):
        cfg = get_llm_config()
        assert cfg.base_url == "https://custom/v1"

    @patch.dict(os.environ, {"LLM_BASE_URL": ""}, clear=True)
    def test_empty_base_url_becomes_none(self):
        cfg = get_llm_config()
        assert cfg.base_url is None

    @patch.dict(os.environ, {"LLM_DEFAULT_MODEL": "gpt-4o"}, clear=True)
    def test_explicit_model_override(self):
        cfg = get_llm_config()
        assert cfg.default_model == "gpt-4o"
