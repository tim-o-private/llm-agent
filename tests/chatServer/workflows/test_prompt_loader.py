"""Tests for step prompt loader and builder integration."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.workflows.prompt_loader import load_step_prompt, make_prompt_loader


class TestLoadStepPrompt:
    @pytest.mark.asyncio
    async def test_loads_prompt_from_config(self):
        mock_config = MagicMock()
        mock_config.read = AsyncMock(return_value="# Test Prompt\nDo the thing.")

        result = await load_step_prompt(
            "email-triage", "categorize",
            config_service=mock_config, user_id="user-1",
        )

        assert result == "# Test Prompt\nDo the thing."
        mock_config.read.assert_called_once_with(
            "workflows/prompts/email-triage/categorize.md", "user-1"
        )

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        mock_config = MagicMock()
        mock_config.read = AsyncMock(return_value=None)

        result = await load_step_prompt(
            "email-triage", "nonexistent",
            config_service=mock_config, user_id="user-1",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_config_not_initialized(self):
        """When ConfigService isn't initialized, returns None gracefully."""
        result = await load_step_prompt(
            "email-triage", "categorize",
            config_service=None, user_id="user-1",
        )
        # Will try get_config_service() which raises RuntimeError
        # since we're in test context — should return None
        assert result is None


class TestMakePromptLoader:
    @pytest.mark.asyncio
    async def test_creates_callable_loader(self):
        mock_config = MagicMock()
        mock_config.read = AsyncMock(return_value="Prompt content")

        loader = make_prompt_loader(config_service=mock_config, user_id="u1")
        result = await loader("morning-briefing", "compose-briefing")

        assert result == "Prompt content"
        mock_config.read.assert_called_once_with(
            "workflows/prompts/morning-briefing/compose-briefing.md", "u1"
        )


class TestBuilderWithPromptLoader:
    @pytest.mark.asyncio
    async def test_step_node_passes_system_prompt(self):
        """Builder step nodes should pass loaded prompt as system_prompt to engine."""
        from chatServer.workflows.builder import GraphBuilder
        from chatServer.workflows.models import EngineResult
        from chatServer.workflows.template_parser import parse_template
        from chatServer.workflows.templates.email_triage import TEMPLATE

        tpl = parse_template(TEMPLATE, "email-triage")

        mock_engine = MagicMock()
        mock_engine.run = AsyncMock(return_value=EngineResult(output="test output"))

        async def fake_loader(template_name, step_name):
            if step_name == "fetch-emails":
                return "Custom fetch prompt"
            return None

        builder = GraphBuilder(prompt_loader=fake_loader)
        # Build just the node, don't compile the full graph
        node_fn = builder._make_step_node(tpl.steps[0], mock_engine, tpl)

        state = {
            "step_outputs": {},
            "parameters": {"hours_back": 12},
            "messages": [],
        }

        await node_fn(state)

        # Verify system_prompt was passed to engine.run
        mock_engine.run.assert_called_once()
        call_kwargs = mock_engine.run.call_args.kwargs
        assert call_kwargs["system_prompt"] == "Custom fetch prompt"

    @pytest.mark.asyncio
    async def test_step_node_falls_back_to_description(self):
        """When prompt loader returns None, step description is used."""
        from chatServer.workflows.builder import GraphBuilder
        from chatServer.workflows.models import EngineResult
        from chatServer.workflows.template_parser import parse_template
        from chatServer.workflows.templates.email_triage import TEMPLATE

        tpl = parse_template(TEMPLATE, "email-triage")

        mock_engine = MagicMock()
        mock_engine.run = AsyncMock(return_value=EngineResult(output="test"))

        async def empty_loader(template_name, step_name):
            return None

        builder = GraphBuilder(prompt_loader=empty_loader)
        node_fn = builder._make_step_node(tpl.steps[0], mock_engine, tpl)

        state = {"step_outputs": {}, "parameters": {}, "messages": []}
        await node_fn(state)

        call_kwargs = mock_engine.run.call_args.kwargs
        # Should use step description as system_prompt fallback
        assert "Search all connected Gmail" in call_kwargs["system_prompt"]
