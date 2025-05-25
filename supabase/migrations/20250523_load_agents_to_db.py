import os
import yaml
import json
from supabase import create_client
from uuid import uuid4
from datetime import datetime

# --- CONFIGURE THESE ---
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL") or "https://your-project.supabase.co"
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or "your-service-role-key"
AGENT_CONFIG_PATH = "config/agents/assistant/agent_config.yaml"  # Path to your YAML config
SYSTEM_PROMPT_PATH = "config/agents/assistant/system_prompt.md"  # Path to your system prompt file (if separate)
AGENT_NAME = "assistant"  # Name of your agent

# --- Connect to Supabase ---
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# --- Load agent config YAML ---
with open(AGENT_CONFIG_PATH, "r") as f:
    agent_config = yaml.safe_load(f)

# --- Load system prompt ---
if os.path.exists(SYSTEM_PROMPT_PATH):
    with open(SYSTEM_PROMPT_PATH, "r") as f:
        system_prompt = f.read()
else:
    system_prompt = agent_config.get("system_prompt", "")

# --- Prepare agent_configurations row ---
agent_id = str(uuid4())
llm_config = agent_config.get("llm", {})
now = datetime.now(datetime.UTC).isoformat()

agent_row = {
    "id": agent_id,
    "agent_name": AGENT_NAME,
    "llm_config": llm_config,
    "system_prompt": system_prompt,
    "created_at": now,
    "updated_at": now,
}

# --- Insert agent_configurations row ---
print(f"Inserting agent configuration for '{AGENT_NAME}'...")
supabase.table("agent_configurations").insert(agent_row).execute()

# --- Prepare agent_tools rows ---
tools_config = agent_config.get("tools_config", {})
tool_rows = []
for order, (tool_name, tool_info) in enumerate(tools_config.items()):
    tool_type = tool_info.get("toolkit") or tool_info.get("tool_type") or "Unknown"
    # Exclude only toolkit/tool_type and tool_name from config, keep everything else
    tool_config = {k: v for k, v in tool_info.items() if k not in ("toolkit", "tool_type", "tool_name")}
    tool_row = {
        "id": str(uuid4()),
        "agent_id": agent_id,
        "tool_name": tool_name,
        "tool_type": tool_type,
        "tool_config": tool_config,
        "is_active": True,
        "order": order,
        "created_at": now,
        "updated_at": now,
    }
    tool_rows.append(tool_row)

# --- Add LTM tool if not present ---
if not any(row["tool_type"] == "ManageLongTermMemoryTool" for row in tool_rows):
    ltm_row = {
        "id": str(uuid4()),
        "agent_id": agent_id,
        "tool_name": "manage_long_term_memory",
        "tool_type": "ManageLongTermMemoryTool",
        "tool_config": {},  # Will be filled in at runtime
        "is_active": True,
        "order": len(tool_rows),
        "created_at": now,
        "updated_at": now,
    }
    tool_rows.append(ltm_row)

# --- Insert agent_tools rows ---
if tool_rows:
    print(f"Inserting {len(tool_rows)} tools for agent '{AGENT_NAME}'...")
    supabase.table("agent_tools").insert(tool_rows).execute()
else:
    print("No tools found in config to insert.")

print("Migration complete.")