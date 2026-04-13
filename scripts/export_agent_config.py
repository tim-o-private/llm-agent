#!/usr/bin/env python3
"""Export agent configuration from Supabase to local YAML + Markdown files.

Reads the 'clarity' agent from agent_configurations, joins its active tools,
and writes:
  - data/config/system/agents/clarity/agent.yaml
  - data/config/system/agents/clarity/soul.md

Usage:
    python scripts/export_agent_config.py

Requires in .env (or environment):
    SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow running from repo root without installing the package
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import yaml  # noqa: E402


def main() -> None:
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_key:
        print(
            "Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.",
            file=sys.stderr,
        )
        sys.exit(1)

    from supabase import create_client

    print("Connecting to Supabase...")
    client = create_client(supabase_url, service_key)

    # ------------------------------------------------------------------
    # 1. Fetch agent configuration
    # ------------------------------------------------------------------
    # The primary agent is stored as "assistant" in the DB but maps to "clarity"
    # in the config export.
    db_agent_name = "assistant"
    print(f"Fetching '{db_agent_name}' agent configuration...")
    agent_result = (
        client.table("agent_configurations")
        .select("id, agent_name, soul, identity, llm_config")
        .eq("agent_name", db_agent_name)
        .single()
        .execute()
    )

    if not agent_result.data:
        print(f"Error: '{db_agent_name}' agent not found in agent_configurations.", file=sys.stderr)
        sys.exit(1)

    agent = agent_result.data
    agent_id = agent["id"]

    # identity may be a JSON string or already a dict
    identity = agent.get("identity") or {}
    if isinstance(identity, str):
        identity = json.loads(identity)

    llm_config = agent.get("llm_config") or {}
    if isinstance(llm_config, str):
        llm_config = json.loads(llm_config)

    soul_text = agent.get("soul") or ""

    print(f"  agent_id: {agent_id}")
    print(f"  identity: {identity}")
    print(f"  llm model: {llm_config.get('model', 'unknown')}")

    # ------------------------------------------------------------------
    # 2. Fetch active tools via join
    # ------------------------------------------------------------------
    print("Fetching active tools...")
    tools_result = (
        client.table("agent_tools")
        .select("tools(name, description, type, config)")
        .eq("agent_id", agent_id)
        .eq("is_active", True)
        .execute()
    )

    tools_data = []
    for row in tools_result.data or []:
        tool = row.get("tools")
        if not tool:
            continue
        tools_data.append(tool)

    print(f"  {len(tools_data)} active tool(s) found")

    # ------------------------------------------------------------------
    # 3. Build agent.yaml structure
    # ------------------------------------------------------------------
    agent_yaml = {
        "name": "clarity",
        "description": identity.get("description", ""),
        "identity": {
            "name": identity.get("name", "Clarity"),
            "vibe": identity.get("vibe", ""),
            "description": identity.get("description", ""),
        },
        "llm": {
            "model": llm_config.get("model", ""),
        },
        "soul_file": "soul.md",
        "tools": [],
        "subagents": [
            {
                "name": "researcher",
                "description": (
                    "Research a topic using web search, memory, and file tools. "
                    "Use for gathering information, fact-checking, or deep investigation."
                ),
                "system_prompt": (
                    "You are a research assistant. Use your tools to thoroughly "
                    "investigate the given topic. Summarize findings clearly with sources."
                ),
            },
        ],
    }

    for tool in sorted(tools_data, key=lambda t: t.get("name", "")):
        tool_entry: dict = {"type": tool["type"]}
        agent_yaml["tools"].append(tool_entry)

    # ------------------------------------------------------------------
    # 4. Write files
    # ------------------------------------------------------------------
    output_dir = _REPO_ROOT / "data" / "config" / "system" / "agents" / "clarity"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write agent.yaml
    agent_yaml_path = output_dir / "agent.yaml"
    with open(agent_yaml_path, "w") as f:
        yaml.dump(
            agent_yaml,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )
    print(f"\nWrote {agent_yaml_path}")

    # Write soul.md
    soul_path = output_dir / "soul.md"
    with open(soul_path, "w") as f:
        f.write(soul_text)
        if soul_text and not soul_text.endswith("\n"):
            f.write("\n")
    print(f"Wrote {soul_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
