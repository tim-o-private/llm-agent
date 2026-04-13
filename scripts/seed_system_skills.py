#!/usr/bin/env python3
"""Seed skill files to Supabase Storage.

System config (skills, agents, workflows) is git-managed at data/config/system/.
This script uploads:
  - System skills to Storage (for legacy compatibility)
  - Per-user communication-preferences skills from user_agent_prompt_customizations

Idempotent: uses upsert semantics. Safe to run multiple times.

Usage:
    python scripts/seed_system_skills.py                  # seed all
    python scripts/seed_system_skills.py --system-only    # system skills only
    python scripts/seed_system_skills.py --user-only      # user skills only
    python scripts/seed_system_skills.py --dry-run        # show what would be written

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


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BUCKET = "config"
DESCRIPTION_MAX_CHARS = 1024

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
    *,
    dry_run: bool = False,
) -> list[str]:
    """Write all system-level skills. Returns list of paths written."""
    skills: list[tuple[str, str]] = [
        ("system/skills/interaction-learning/SKILL.md", build_interaction_learning_skill()),
        ("system/skills/tool-guidance/SKILL.md", build_tool_guidance_skill()),
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
) -> None:
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.", file=sys.stderr)
        sys.exit(1)

    from supabase import acreate_client, create_client

    print("Connecting to Supabase...")
    async_client = await acreate_client(supabase_url, service_key)

    # Sync client for DB reads (user customizations)
    sync_client = create_client(supabase_url, service_key)

    print("Fetching data...")
    customizations = fetch_user_customizations(sync_client) if not system_only else []

    if not system_only:
        print(f"  user_agent_prompt_customizations: {len(customizations)} active row(s)")

    if dry_run:
        print("\n[DRY RUN -- no writes will occur]\n")

    if not user_only:
        print("\nSeeding system skills...")
        written_system = await seed_system_skills(async_client, dry_run=dry_run)
        label = "would be " if dry_run else ""
        print(f"  {len(written_system)} system skill(s) {label}written")

    if not system_only:
        print("\nSeeding user skills...")
        written_user = await seed_user_skills(async_client, customizations, dry_run=dry_run)
        label = "would be " if dry_run else ""
        print(f"  {len(written_user)} user skill(s) {label}written")

    # System config (skills, agent configs, workflows) is git-managed.
    # No pull_system() needed — files are deployed with the code.

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed Supabase Storage with SKILL.md files for system and user skills"
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
    args = parser.parse_args()

    asyncio.run(
        main(
            dry_run=args.dry_run,
            system_only=args.system_only,
            user_only=args.user_only,
        )
    )
