"""File-based agent configuration loader.

Reads agent config from YAML files on disk instead of the database.
System config is git-managed at data/config/system/ and deployed with the code.

Config location: data/config/system/agents/{agent_name}/agent.yaml
Soul file:       data/config/system/agents/{agent_name}/soul.md (referenced by agent.yaml)

Caches parsed config with mtime-based invalidation — file edits during dev
take effect without restart.
"""

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Agent name mapping: DB uses "assistant", runtime uses "clarity"
_AGENT_NAME_ALIASES = {
    "assistant": "clarity",
}


class AgentConfigLoader:
    """Loads agent configuration from YAML files with mtime-based caching."""

    def __init__(self, system_dir: Path):
        self._system_dir = system_dir
        self._cache: dict[str, tuple[dict[str, Any], float]] = {}  # name -> (config, mtime)

    def load(self, agent_name: str) -> dict[str, Any]:
        """Load agent config by name. Returns dict with soul, identity, llm, tools, subagents."""
        # Resolve aliases (e.g., "assistant" -> "clarity")
        dir_name = _AGENT_NAME_ALIASES.get(agent_name, agent_name)
        agent_dir = self._system_dir / "agents" / dir_name
        yaml_path = agent_dir / "agent.yaml"

        if not yaml_path.exists():
            raise FileNotFoundError(
                f"Agent config not found: {yaml_path}. "
                f"Ensure data/config/system/agents/{dir_name}/ exists."
            )

        # Check mtime for cache invalidation
        current_mtime = yaml_path.stat().st_mtime
        cached = self._cache.get(dir_name)
        if cached and cached[1] == current_mtime:
            return cached[0]

        # Parse YAML
        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

        # Read soul file if referenced
        soul = ""
        soul_file = raw.get("soul_file")
        if soul_file:
            soul_path = agent_dir / soul_file
            if soul_path.exists():
                soul = soul_path.read_text(encoding="utf-8").strip()
            else:
                logger.warning("Soul file not found: %s", soul_path)

        # Build config dict matching the shape _build_agent() expects
        config = {
            "agent_name": raw.get("name", dir_name),
            "soul": soul,
            "identity": raw.get("identity"),
            "llm_config": raw.get("llm", {}),
            "tools": [
                {
                    "name": t.get("name", ""),
                    "type": t.get("type", ""),
                    "description": t.get("description", ""),
                    "config": t.get("config", {}),
                    "is_active": True,
                }
                for t in raw.get("tools", [])
            ],
            "subagents": raw.get("subagents", []),
        }

        self._cache[dir_name] = (config, current_mtime)
        logger.info("Loaded agent config from %s (%d tools)", yaml_path, len(config["tools"]))
        return config


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

_loader: AgentConfigLoader | None = None


def get_agent_config_loader() -> AgentConfigLoader:
    """Get or create the global AgentConfigLoader instance."""
    global _loader
    if _loader is None:
        data_dir = Path(os.getenv("SANDBOX_DATA_DIR", "/data"))
        system_dir = data_dir / "config" / "system"
        _loader = AgentConfigLoader(system_dir)
    return _loader
