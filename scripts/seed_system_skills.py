#!/usr/bin/env python3
"""Seed system and user skill files to Supabase Storage.

Extracts behavioral content from:
  - agent_configurations table (soul, identity)
  - chatServer/services/prompt_builder.py constants (operating model, etc.)
  - user_agent_prompt_customizations table (per-user instructions)

Writes SKILL.md files to the "config" bucket in Supabase Storage.
Optionally calls StorageSync.pull_system() to populate local disk.

Idempotent: uses upsert semantics. Safe to run multiple times.

Usage:
    python scripts/seed_system_skills.py                  # seed all + pull to local disk
    python scripts/seed_system_skills.py --system-only    # system skills only
    python scripts/seed_system_skills.py --user-only      # user skills only
    python scripts/seed_system_skills.py --dry-run        # show what would be written
    python scripts/seed_system_skills.py --no-pull        # skip pull_system() after seeding

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

# Allow running from repo root without installing the package
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional for environments where env vars are set directly

# ---------------------------------------------------------------------------
# Imports that need sys.path set first
# ---------------------------------------------------------------------------

from chatServer.services.storage_sync import StorageSync  # noqa: E402

# ---------------------------------------------------------------------------
# Constants (previously in prompt_builder.py, now inlined)
# ---------------------------------------------------------------------------

OPERATING_MODEL = (
    "Start every conversation with awareness. Check tasks (get_tasks) and recall "
    "what you know (search_memories) — but don't announce that you did this.\n\n"
    "Think about what the user *should* be doing, not just what they asked. "
    "If they mention a vague goal, break it down into concrete steps. If something "
    "implies a deadline or commitment they haven't tracked, flag it.\n\n"
    "Have opinions about priorities. When multiple things compete for attention, "
    "say what you'd focus on first and why. If the user disagrees, update your "
    "understanding — that correction is valuable data.\n\n"
    "Match the user's energy. If they're in work mode, be terse. If they want to "
    "talk through something, engage. If they seem stressed, lighten the load.\n\n"
    "When the user mentions something actionable, create a task. Don't ask permission. "
    "When they finish something, mark it complete. When you have Gmail access, scan "
    "for actionable items and surface what matters.\n\n"
    "The task list should always reflect reality."
)

CHANNEL_GUIDANCE = {
    "web": (
        "User is on the web app. Markdown formatting is supported. "
        "This is an interactive conversation — respond to what the user says, "
        "ask clarifying questions when needed."
    ),
    "telegram": (
        "User is on Telegram. Keep responses concise — under 4096 characters. "
        "Use simple markdown (bold, italic, code). No tables or complex formatting. "
        "This is an interactive conversation."
    ),
    "scheduled": (
        "This is an automated scheduled run. No one is waiting for a response.\n"
        "- Do the work described in the prompt thoroughly.\n"
        "- Use all available tools to gather information before composing your response.\n"
        "- Don't ask follow-up questions — make reasonable assumptions.\n"
        "- Your response will be delivered as a notification, so make it self-contained."
    ),
    "heartbeat": (
        "This is an automated heartbeat check. No one is waiting for a response.\n"
        "Your job: check each area using your tools, then decide if anything needs the user's attention.\n"
        "- Use tools to actively check state (tasks, emails, reminders) — don't guess.\n"
        "- If everything is fine, respond with exactly: HEARTBEAT_OK\n"
        "- If something needs attention, report ONLY what needs action — no filler.\n"
        "- Never fabricate information. If a tool fails, skip that check and note the failure."
    ),
    "session_open": (
        "The user just returned to the app. You are deciding whether to initiate — "
        "no user message has been sent yet."
    ),
}

INTERACTION_LEARNING_GUIDANCE = (
    "Build a structured mental model of this person over time:\n\n"
    "Life domains: work, family, home, health, finances, interests. Notice which "
    "domains come up and what matters within each.\n\n"
    "Key entities: people (partner, boss, friends), organizations (employer, clients), "
    "projects (ongoing work, goals), recurring patterns (weekly meetings, habits).\n\n"
    "Priority signals: what the user responds to quickly, what they dismiss, what "
    "stresses them, what excites them. Explicit statements matter most, but behavioral "
    "patterns (response speed, topic avoidance, energy shifts) are also signal.\n\n"
    "Communication patterns: terse vs detailed, formal vs casual, time-of-day preferences, "
    "how they handle being corrected, what kind of humor lands.\n\n"
    "Record observations via create_memories after every few exchanges. Use "
    "search_memories before answering questions about the user's preferences or history."
)


def _format_identity_str(identity: dict | None) -> str:
    """Format identity dict into a single-line description."""
    if not identity:
        return ""
    name = identity.get("name") or "an AI assistant"
    description = identity.get("description") or "a personal assistant"
    vibe = identity.get("vibe") or ""
    line = f"You are {name} — {description}."
    if vibe:
        line += f" {vibe}"
    return line

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BUCKET = "config"
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
- Do not call tools in loops without bound -- ask the user if you're stuck.
"""

TOOL_GUIDANCE_PLACEHOLDER = """\
# Tool Guidance

> **Note:** Detailed tool guidance is populated dynamically by the prompt builder
> at runtime based on the active tool set and channel. This file is a placeholder.
>
> To add static tool guidance that should appear in all contexts, edit this file
> via the Clarity skill editor.

## Available Tool Categories

- **Email** -- read, search, compose, and send emails via Gmail
- **Calendar** -- view and create events via Google Calendar
- **Tasks** -- create, update, complete, and search tasks
- **Reminders** -- set and manage time-based reminders
- **Memory** -- store and recall long-term observations about the user
- **Web search** -- search the web for current information
- **Notifications** -- send messages and alerts to the user

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
        lines.append("*(No identity configured -- using defaults.)*\n")
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
# DB helpers (use sync client for simplicity in a script)
# ---------------------------------------------------------------------------


def fetch_agent_config(client) -> dict | None:
    """Fetch the first row from agent_configurations."""
    response = (
        client.table("agent_configurations")
        .select("soul, identity, prompt_template, agent_name")
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def fetch_user_customizations(client) -> list[dict]:
    """Fetch active rows from user_agent_prompt_customizations."""
    response = (
        client.table("user_agent_prompt_customizations")
        .select("user_id, agent_name, instructions, is_active")
        .eq("is_active", True)
        .execute()
    )
    return response.data or []


# ---------------------------------------------------------------------------
# Upload helper
# ---------------------------------------------------------------------------


async def _upload(async_client, path: str, content: str) -> None:
    """Upload a single file to the config bucket with upsert."""
    bucket = async_client.storage.from_(BUCKET)
    content_type = "text/markdown" if path.endswith(".md") else "text/plain"
    await bucket.upload(
        path=path,
        file=content.encode("utf-8"),
        file_options={"upsert": "true", "content-type": content_type},
    )


# ---------------------------------------------------------------------------
# Seeding functions
# ---------------------------------------------------------------------------


async def seed_system_skills(
    async_client,
    agent_row: dict | None,
    *,
    dry_run: bool = False,
) -> list[str]:
    """Write all system-level skills. Returns list of paths written."""
    soul = (agent_row or {}).get("soul") or ""
    identity = (agent_row or {}).get("identity")

    skills: list[tuple[str, str]] = [
        ("system/skills/clarity-soul/SKILL.md", build_soul_skill(soul)),
        ("system/skills/clarity-identity/SKILL.md", build_identity_skill(identity)),
        ("system/skills/operating-model/SKILL.md", build_operating_model_skill()),
        ("system/skills/channel-guidance/SKILL.md", build_channel_guidance_skill()),
        ("system/skills/interaction-learning/SKILL.md", build_interaction_learning_skill()),
        ("system/skills/tool-guidance/SKILL.md", build_tool_guidance_skill()),
        ("system/skills/safety-guidelines/SKILL.md", build_safety_guidelines_skill()),
    ]

    written = []
    for path, content in skills:
        if dry_run:
            print(f"  [dry-run] would write {path} ({len(content)} chars)")
        else:
            await _upload(async_client, path, content)
            print(f"  wrote {path}")
        written.append(path)

    return written


async def seed_user_skills(
    async_client,
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

        path = f"users/{user_id}/skills/communication-preferences/SKILL.md"
        content = build_communication_preferences_skill(instructions, agent_name)

        if dry_run:
            print(f"  [dry-run] would write {path} ({len(content)} chars)")
        else:
            await _upload(async_client, path, content)
            print(f"  wrote {path}")
        written.append(path)

    return written


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main(
    *,
    dry_run: bool = False,
    system_only: bool = False,
    user_only: bool = False,
    no_pull: bool = False,
) -> None:
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.", file=sys.stderr)
        sys.exit(1)

    from supabase import acreate_client, create_client

    print("Connecting to Supabase...")
    async_client = await acreate_client(supabase_url, service_key)

    # Sync client for simple DB reads
    sync_client = create_client(supabase_url, service_key)

    print("Fetching data...")
    agent_row = fetch_agent_config(sync_client) if not user_only else None
    customizations = fetch_user_customizations(sync_client) if not system_only else []

    if agent_row:
        print(f"  agent_configurations: found row (agent_name={agent_row.get('agent_name')})")
    elif not user_only:
        print("  agent_configurations: no rows -- using empty soul/identity")

    if not system_only:
        print(f"  user_agent_prompt_customizations: {len(customizations)} active row(s)")

    if dry_run:
        print("\n[DRY RUN -- no writes will occur]\n")

    if not user_only:
        print("\nSeeding system skills...")
        written_system = await seed_system_skills(async_client, agent_row, dry_run=dry_run)
        label = "would be " if dry_run else ""
        print(f"  {len(written_system)} system skill(s) {label}written")

    if not system_only:
        print("\nSeeding user skills...")
        written_user = await seed_user_skills(async_client, customizations, dry_run=dry_run)
        label = "would be " if dry_run else ""
        print(f"  {len(written_user)} user skill(s) {label}written")

    # AC-21: pull system config to local disk after seeding
    if not no_pull and not dry_run and not user_only:
        print("\nPulling system config to local disk...")
        storage_sync = StorageSync(supabase_url, service_key)
        await storage_sync.pull_system()
        print("  System config pulled to /data/config/system/")

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed Supabase Storage with SKILL.md files from DB and prompt_builder constants"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be written without writing",
    )
    parser.add_argument(
        "--system-only",
        action="store_true",
        help="Only write system-level skills",
    )
    parser.add_argument(
        "--user-only",
        action="store_true",
        help="Only write user-level skills",
    )
    parser.add_argument(
        "--no-pull",
        action="store_true",
        help="Skip pull_system() after seeding (default: pull to /data/config/system/)",
    )
    args = parser.parse_args()

    asyncio.run(
        main(
            dry_run=args.dry_run,
            system_only=args.system_only,
            user_only=args.user_only,
            no_pull=args.no_pull,
        )
    )
