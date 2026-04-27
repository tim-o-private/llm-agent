"""Tests for llm_client.py — get_llm_client factory and is_openai_client duck-typing."""

from unittest.mock import MagicMock, patch

import pytest

from chatServer.services.llm_client import get_llm_client, is_openai_client


# ---------------------------------------------------------------------------
# is_openai_client — the load-bearing routing decision
# ---------------------------------------------------------------------------

class TestIsOpenaiClient:
    def test_plain_mock_returns_false(self):
        assert is_openai_client(MagicMock()) is False

    def test_object_with_chat_completions_returns_true(self):
        class OpenAILike:
            class _Chat:
                completions = object()
            chat = _Chat()

        assert is_openai_client(OpenAILike()) is True

    def test_object_without_chat_returns_false(self):
        class Bare:
            pass

        assert is_openai_client(Bare()) is False

    def test_anthropic_style_client_returns_false(self):
        class AnthropicLike:
            messages = object()

        assert is_openai_client(AnthropicLike()) is False

    def test_real_openai_class_detected(self):
        """Simulate a class whose name isn't Mock and has chat.completions."""

        class FakeOpenAI:
            class _Chat:
                completions = object()
            chat = _Chat()

        assert is_openai_client(FakeOpenAI()) is True

    def test_mock_subclass_names_return_false(self):
        for name in ("MagicMock", "AsyncMock", "Mock"):
            obj = type(name, (), {"chat": type("C", (), {"completions": True})})()
            assert is_openai_client(obj) is False


# ---------------------------------------------------------------------------
# get_llm_client — factory
# ---------------------------------------------------------------------------

class TestGetLlmClient:
    @patch("chatServer.services.llm_client.get_settings")
    def test_openai_provider(self, mock_get_settings):
        settings = MagicMock()
        settings.llm_provider = "openai"
        settings.llm_api_key = "sk-test"
        settings.llm_base_url = None
        mock_get_settings.return_value = settings

        client = get_llm_client()
        assert type(client).__name__ == "AsyncOpenAI"

    @patch("chatServer.services.llm_client.get_settings")
    def test_anthropic_provider(self, mock_get_settings):
        settings = MagicMock()
        settings.llm_provider = "anthropic"
        settings.llm_api_key = "sk-ant-test"
        settings.llm_base_url = None
        mock_get_settings.return_value = settings

        client = get_llm_client()
        assert type(client).__name__ == "AsyncAnthropic"

    @patch("chatServer.services.llm_client.get_settings")
    def test_default_is_anthropic(self, mock_get_settings):
        settings = MagicMock()
        settings.llm_provider = "anthropic"
        settings.llm_api_key = ""
        settings.llm_base_url = None
        mock_get_settings.return_value = settings

        client = get_llm_client()
        assert type(client).__name__ == "AsyncAnthropic"

    @patch("chatServer.services.llm_client.get_settings")
    def test_base_url_passed_to_openai(self, mock_get_settings):
        settings = MagicMock()
        settings.llm_provider = "openai"
        settings.llm_api_key = "sk-test"
        settings.llm_base_url = "https://custom.endpoint/v1"
        mock_get_settings.return_value = settings

        client = get_llm_client()
        assert str(client.base_url).rstrip("/").endswith("/v1")

    @patch("chatServer.services.llm_client.get_settings")
    def test_base_url_passed_to_anthropic(self, mock_get_settings):
        settings = MagicMock()
        settings.llm_provider = "anthropic"
        settings.llm_api_key = "sk-ant-test"
        settings.llm_base_url = "https://custom.anthropic/v1"
        mock_get_settings.return_value = settings

        client = get_llm_client()
        assert "custom.anthropic" in str(client.base_url)
