"""Tests for chatServer.services.agent_config_loader — file-based agent config."""

import textwrap
from pathlib import Path

import pytest

from chatServer.services.agent_config_loader import AgentConfigLoader


@pytest.fixture
def system_dir(tmp_path):
    """Create a temp system dir with a sample agent config."""
    agent_dir = tmp_path / "agents" / "clarity"
    agent_dir.mkdir(parents=True)

    # Write agent.yaml
    yaml_content = textwrap.dedent("""\
        name: clarity
        description: "Your personal chief of staff"
        identity:
          name: Clarity
          vibe: "Opinionated, warm, and honest"
          description: "your personal chief of staff"
        llm:
          model: claude-sonnet-4-20250514
        soul_file: soul.md
        tools:
          - type: GetTasksTool
          - type: SearchGmailTool
        subagents:
          - name: researcher
            description: "Research a topic"
            system_prompt: "You are a research assistant."
    """)
    (agent_dir / "agent.yaml").write_text(yaml_content)
    (agent_dir / "soul.md").write_text("Be helpful and warm.")
    return tmp_path


class TestAgentConfigLoader:
    def test_load_returns_config_dict(self, system_dir):
        loader = AgentConfigLoader(system_dir)
        config = loader.load("clarity")

        assert config["agent_name"] == "clarity"
        assert config["soul"] == "Be helpful and warm."
        assert config["identity"]["name"] == "Clarity"
        assert config["identity"]["vibe"] == "Opinionated, warm, and honest"
        assert config["llm_config"]["model"] == "claude-sonnet-4-20250514"

    def test_load_returns_tools_list(self, system_dir):
        loader = AgentConfigLoader(system_dir)
        config = loader.load("clarity")

        assert len(config["tools"]) == 2
        assert config["tools"][0]["type"] == "GetTasksTool"
        assert config["tools"][1]["type"] == "SearchGmailTool"
        assert config["tools"][0]["is_active"] is True

    def test_load_returns_subagents(self, system_dir):
        loader = AgentConfigLoader(system_dir)
        config = loader.load("clarity")

        assert len(config["subagents"]) == 1
        assert config["subagents"][0]["name"] == "researcher"

    def test_load_caches_by_mtime(self, system_dir):
        loader = AgentConfigLoader(system_dir)
        config1 = loader.load("clarity")
        config2 = loader.load("clarity")
        assert config1 is config2  # same dict object — cache hit

    def test_load_invalidates_on_file_change(self, system_dir):
        loader = AgentConfigLoader(system_dir)
        config1 = loader.load("clarity")

        # Modify the file (changes mtime)
        yaml_path = system_dir / "agents" / "clarity" / "agent.yaml"
        import time
        time.sleep(0.05)  # ensure mtime changes
        content = yaml_path.read_text()
        yaml_path.write_text(content.replace("claude-sonnet-4-20250514", "claude-opus-4-20250514"))

        config2 = loader.load("clarity")
        assert config2["llm_config"]["model"] == "claude-opus-4-20250514"
        assert config1 is not config2  # cache miss — new object

    def test_load_alias_assistant_to_clarity(self, system_dir):
        """Agent name 'assistant' (DB name) resolves to 'clarity' directory."""
        loader = AgentConfigLoader(system_dir)
        config = loader.load("assistant")
        assert config["agent_name"] == "clarity"

    def test_load_missing_agent_raises(self, system_dir):
        loader = AgentConfigLoader(system_dir)
        with pytest.raises(FileNotFoundError, match="Agent config not found"):
            loader.load("nonexistent-agent")

    def test_load_missing_soul_file(self, system_dir):
        """Missing soul file produces empty soul string, not an error."""
        (system_dir / "agents" / "clarity" / "soul.md").unlink()
        loader = AgentConfigLoader(system_dir)
        config = loader.load("clarity")
        assert config["soul"] == ""

    def test_load_no_soul_file_key(self, system_dir):
        """agent.yaml without soul_file key results in empty soul."""
        yaml_path = system_dir / "agents" / "clarity" / "agent.yaml"
        content = yaml_path.read_text()
        yaml_path.write_text(content.replace("soul_file: soul.md\n", ""))
        loader = AgentConfigLoader(system_dir)
        config = loader.load("clarity")
        assert config["soul"] == ""

    def test_load_no_tools_key(self, system_dir):
        """agent.yaml without tools key results in empty tools list."""
        yaml_path = system_dir / "agents" / "clarity" / "agent.yaml"
        yaml_path.write_text(textwrap.dedent("""\
            name: minimal
            llm:
              model: claude-haiku-4-5-20251001
        """))
        loader = AgentConfigLoader(system_dir)
        config = loader.load("clarity")
        assert config["tools"] == []
        assert config["subagents"] == []
