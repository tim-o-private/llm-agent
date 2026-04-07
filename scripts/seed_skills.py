#!/usr/bin/env python3
"""Seed Supabase Storage with SKILL.md files from DB and prompt_builder constants.

Reads behavioral content from:
  - agent_configurations table (soul, identity, prompt_template)
  - user_agent_prompt_customizations table (per-user instructions)
  - chatServer/services/prompt_builder.py constants (OPERATING_MODEL, etc.)

Writes SKILL.md files to the "config" bucket via ConfigService:
  - system/skills/<skill-name>/SKILL.md   (read-only defaults)
  - users/<user_id>/skills/communication-preferences/SKILL.md  (user overrides)

Idempotent: uses upsert semantics. Safe to run multiple times.

Usage:
    python scripts/seed_skills.py
    python scripts/seed_skills.py --dry-run
    python scripts/seed_skills.py --user-skills-only
    python scripts/seed_skills.py --system-skills-only

Requires in .env (or environment):
    SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import textwrap
from pathlib import Path

from dotenv import load_dotenv

# Allow running from repo root without installing the package
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

load_dotenv()

# ---------------------------------------------------------------------------
# Imports that need sys.path set first
# ---------------------------------------------------------------------------

from chatServer.services.config_service import ConfigService  # noqa: E402
from chatServer.services.prompt_builder import (  # noqa: E402
    CHANNEL_GUIDANCE,
    INTERACTION_LEARNING_GUIDANCE,
    OPERATING_MODEL,
    _format_identity_str,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DESCRIPTION_MAX_CHARS = 1024
SAFETY_GUIDELINES_CONTENT = """\
# Safety Guidelines

Clarity operates within these safety boundaries.

## Core Principles

- **Never deceive** the user about your capabilities or what you're doing.
- **Always respect user autonomy.** Recommend, don't override.
- **Protect user data.** Never share personal information from memory with third parties.
- **Flag uncertainty.** When you don't know something, say so.
- **Minimal footprint.** Only take actions explicitly asked for or clearly implied.

## Action Boundaries

- Do not send emails, create events, or take external actions without user confirmation
  unless the user has explicitly granted standing permission.
- Never delete data (tasks, reminders, emails) without explicit confirmation.
- Do not store sensitive credentials in memory or logs.

## Tool Use

- Call tools to verify facts before asserting them.
- If a tool fails, report the failure rather than guessing.
- Do not call tools in loops without bound — ask the user if you're stuck.
"""

TOOL_GUIDANCE_PLACEHOLDER = """\
# Tool Guidance

> **Note:** Detailed tool guidance is populated dynamically by the prompt builder
> at runtime based on the active tool set and channel. This file is a placeholder.
>
> To add static tool guidance that should appear in all contexts, edit this file
> via the Clarity skill editor.

## Available Tool Categories

- **Email** — read, search, compose, and send emails via Gmail
- **Calendar** — view and create events via Google Calendar
- **Tasks** — create, update, complete, and search tasks
- **Reminders** — set and manage time-based reminders
- **Memory** — store and recall long-term observations about the user
- **Web search** — search the web for current information
- **Notifications** — send messages and alerts to the user

Use `search_memories` before answering questions about the user's history.
Use `create_memories` to store new observations worth keeping.
"""


# ---------------------------------------------------------------------------
# SKILL.md builders
# ---------------------------------------------------------------------------


def _frontmatter(name: str, description: str) -> str:
    """Build YAML frontmatter block. Truncates description to 1024 chars."""
    desc = description.strip().replace("\n", " ")
    desc = textwrap.shorten(desc, width=DESCRIPTION_MAX_CHARS, placeholder="...")
    return f"---\nname: {name}\ndescription: >\n  {desc}\n---\n\n"


def build_soul_skill(soul: str) -> str:
    content = soul.strip() if soul else "(No soul content configured.)"
    fm = _frontmatter(
        "clarity-soul",
        "Core behavioral philosophy for the Clarity agent. "
        "Defines personality, values, and relationship with the user.",
    )
    return fm + "# Clarity Soul\n\n" + content + "\n"


def build_identity_skill(identity: dict | None) -> str:
    fm = _frontmatter(
        "clarity-identity",
        "Structured identity metadata for the Clarity agent: name, description, and vibe.",
    )
    lines = ["# Clarity Identity\n"]
    if identity:
        name = identity.get("name") or "Clarity"
        description = identity.get("description") or "a personal AI assistant"
        vibe = identity.get("vibe") or ""
        lines.append(f"**Name:** {name}\n")
        lines.append(f"**Description:** {description}\n")
        if vibe:
            lines.append(f"**Vibe:** {vibe}\n")
        lines.append(f"\n**One-liner:** {_format_identity_str(identity)}\n")
    else:
        lines.append("*(No identity configured — using defaults.)*\n")
    return fm + "\n".join(lines)


def build_operating_model_skill() -> str:
    fm = _frontmatter(
        "operating-model",
        "How Clarity operates across conversations: proactive awareness, priority reasoning, "
        "energy matching, and action bias.",
    )
    return fm + "# Operating Model\n\n" + OPERATING_MODEL.strip() + "\n"


def build_channel_guidance_skill() -> str:
    fm = _frontmatter(
        "channel-guidance",
        "Per-channel behavioral guidance for Clarity: web, Telegram, scheduled runs, "
        "heartbeat checks, and session-open contexts.",
    )
    sections = ["# Channel Guidance\n"]
    for channel, guidance in CHANNEL_GUIDANCE.items():
        sections.append(f"## {channel.replace('_', ' ').title()}\n\n{guidance.strip()}\n")
    return fm + "\n".join(sections)


def build_interaction_learning_skill() -> str:
    fm = _frontmatter(
        "interaction-learning",
        "Guidelines for building a structured mental model of the user over time: "
        "life domains, key entities, priority signals, and communication patterns.",
    )
    return fm + "# Interaction Learning\n\n" + INTERACTION_LEARNING_GUIDANCE.strip() + "\n"


def build_tool_guidance_skill() -> str:
    fm = _frontmatter(
        "tool-guidance",
        "Static tool guidance for Clarity. Dynamic per-channel sections are injected "
        "by the prompt builder at runtime.",
    )
    return fm + TOOL_GUIDANCE_PLACEHOLDER


def build_safety_guidelines_skill() -> str:
    fm = _frontmatter(
        "safety-guidelines",
        "Core safety boundaries and behavioral constraints for the Clarity agent.",
    )
    return fm + SAFETY_GUIDELINES_CONTENT


def build_communication_preferences_skill(instructions: str, agent_name: str) -> str:
    fm = _frontmatter(
        "communication-preferences",
        f"User-specific communication preferences and custom instructions for {agent_name}.",
    )
    return (
        fm
        + "# Communication Preferences\n\n"
        + instructions.strip()
        + "\n"
    )


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


async def fetch_agent_config(client) -> dict | None:
    """Fetch the first row from agent_configurations."""
    response = await asyncio.to_thread(
        lambda: client.table("agent_configurations")
        .select("soul, identity, prompt_template, agent_name")
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


async def fetch_user_customizations(client) -> list[dict]:
    """Fetch active rows from user_agent_prompt_customizations."""
    response = await asyncio.to_thread(
        lambda: client.table("user_agent_prompt_customizations")
        .select("user_id, agent_name, instructions, is_active")
        .eq("is_active", True)
        .execute()
    )
    return response.data or []


# ---------------------------------------------------------------------------
# Seeding functions
# ---------------------------------------------------------------------------


SYSTEM_SKILLS: list[tuple[str, str]] = []  # filled in seed_system_skills()


async def seed_system_skills(
    config: ConfigService,
    agent_row: dict | None,
    *,
    dry_run: bool = False,
) -> list[str]:
    """Write all system-level skills. Returns list of paths written."""
    soul = (agent_row or {}).get("soul") or ""
    identity = (agent_row or {}).get("identity")

    skills: list[tuple[str, str]] = [
        ("skills/clarity-soul/SKILL.md", build_soul_skill(soul)),
        ("skills/clarity-identity/SKILL.md", build_identity_skill(identity)),
        ("skills/operating-model/SKILL.md", build_operating_model_skill()),
        ("skills/channel-guidance/SKILL.md", build_channel_guidance_skill()),
        ("skills/interaction-learning/SKILL.md", build_interaction_learning_skill()),
        ("skills/tool-guidance/SKILL.md", build_tool_guidance_skill()),
        ("skills/safety-guidelines/SKILL.md", build_safety_guidelines_skill()),
    ]

    written = []
    for path, content in skills:
        if dry_run:
            print(f"  [dry-run] would write system/{path} ({len(content)} chars)")
        else:
            await config.write_system(path, content)
            print(f"  ✓ system/{path}")
        written.append(f"system/{path}")

    return written


async def seed_user_skills(
    config: ConfigService,
    customizations: list[dict],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Write communication-preferences SKILL.md for each active user customization."""
    written = []
    for row in customizations:
        user_id = row.get("user_id", "")
        agent_name = row.get("agent_name", "clarity")
        instructions = (row.get("instructions") or "").strip()
        if not instructions or not user_id:
            continue

        path = "skills/communication-preferences/SKILL.md"
        content = build_communication_preferences_skill(instructions, agent_name)

        if dry_run:
            print(f"  [dry-run] would write users/{user_id}/{path} ({len(content)} chars)")
        else:
            await config.write(path, user_id, content)
            print(f"  ✓ users/{user_id}/{path}")
        written.append(f"users/{user_id}/{path}")

    return written


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main(
    *,
    dry_run: bool = False,
    system_only: bool = False,
    user_only: bool = False,
) -> None:
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
        sys.exit(1)

    # Import here to avoid polluting the module namespace with optional deps
    from supabase import acreate_client, create_client  # noqa: F401

    print("Connecting to Supabase…")
    # Use async client for ConfigService (it uses asyncio.to_thread for storage)
    async_client = await acreate_client(supabase_url, service_key)
    config = ConfigService(async_client)
    await config.ensure_bucket()

    # Sync client for simple DB reads (avoids async complexity in lambdas)
    sync_client = create_client(supabase_url, service_key)

    print("Fetching data…")
    agent_row = await fetch_agent_config(sync_client) if not user_only else None
    customizations = await fetch_user_customizations(sync_client) if not system_only else []

    if agent_row:
        print(f"  agent_configurations: found row (agent_name={agent_row.get('agent_name')})")
    else:
        print("  agent_configurations: no rows — using empty soul/identity")

    print(f"  user_agent_prompt_customizations: {len(customizations)} active row(s)")

    if dry_run:
        print("\n[DRY RUN — no writes will occur]\n")

    if not user_only:
        print("\nSeeding system skills…")
        written_system = await seed_system_skills(config, agent_row, dry_run=dry_run)
        print(f"  {len(written_system)} system skill(s) {'would be ' if dry_run else ''}written")

    if not system_only:
        print("\nSeeding user skills…")
        written_user = await seed_user_skills(config, customizations, dry_run=dry_run)
        print(f"  {len(written_user)} user skill(s) {'would be ' if dry_run else ''}written")

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Supabase Storage with SKILL.md files")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be written without writing")
    parser.add_argument("--system-skills-only", action="store_true", help="Only write system-level skills")
    parser.add_argument("--user-skills-only", action="store_true", help="Only write user-level skills")
    args = parser.parse_args()

    asyncio.run(
        main(
            dry_run=args.dry_run,
            system_only=args.system_skills_only,
            user_only=args.user_skills_only,
        )
    )
