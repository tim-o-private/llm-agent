"""Prompt builder service — assembles agent system prompt from sections."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

CHANNEL_GUIDANCE = {
    "web": "User is on the web app. Markdown formatting is supported.",
    "telegram": "User is on Telegram. Keep responses concise. No complex markdown.",
    "scheduled": (
        "This is an automated scheduled run. No one is waiting for a response. "
        "Be thorough but don't ask follow-up questions — just do the work and report results."
    ),
}

MAX_INSTRUCTIONS_LENGTH = 2000

MEMORY_SECTION = (
    "You have long-term memory via the read_memory and save_memory tools.\n"
    "IMPORTANT: Before answering any question about the user's preferences, past conversations, "
    "ongoing projects, or anything you were previously told to remember — call read_memory FIRST. "
    "Do not guess from the conversation. Check your memory.\n"
    "When the user tells you something to remember, call save_memory immediately."
)


def build_agent_prompt(
    soul: str,
    identity: dict | None,
    channel: str,
    user_instructions: str | None,
    timezone: str | None = None,
    tool_names: list[str] | None = None,
) -> str:
    """Assemble the agent system prompt from layered sections.

    Args:
        soul: Behavioral philosophy from agent_configurations.soul.
        identity: Structured metadata {name, vibe, description} or None.
        channel: "web", "telegram", or "scheduled".
        user_instructions: Free-text user instructions or None.
        timezone: IANA timezone string (e.g. "America/New_York") or None.
        tool_names: List of available tool names for reference.

    Returns:
        Assembled system prompt string.
    """
    sections: list[str] = []

    # 1. Identity
    if identity:
        name = identity.get("name") or "an AI assistant"
        description = identity.get("description") or "a personal assistant"
        vibe = identity.get("vibe") or ""
        identity_line = f"You are {name} — {description}."
        if vibe:
            identity_line += f" {vibe}"
        sections.append(f"## Identity\n{identity_line}")

    # 2. Soul
    effective_soul = soul or "You are a helpful assistant."
    sections.append(f"## Soul\n{effective_soul}")

    # 3. Channel
    guidance = CHANNEL_GUIDANCE.get(channel, CHANNEL_GUIDANCE["web"])
    sections.append(f"## Channel\nYou are responding via {channel}. {guidance}")

    # 4. Current Time
    now = _get_current_time(timezone)
    sections.append(f"## Current Time\n{now}")

    # 5. Memory
    sections.append(f"## Memory\n{MEMORY_SECTION}")

    # 6. User Instructions
    if user_instructions:
        truncated = user_instructions[:MAX_INSTRUCTIONS_LENGTH]
        instructions_text = truncated
        if len(user_instructions) > MAX_INSTRUCTIONS_LENGTH:
            instructions_text += "\n(Instructions truncated at 2000 characters.)"
    else:
        instructions_text = "(No custom instructions set.)"
    instructions_text += (
        "\nThe user can change these by telling you things like "
        '"always do X" or "never do Y". '
        "When they do, use the update_instructions tool to persist the change."
    )
    sections.append(f"## User Instructions\n{instructions_text}")

    # 7. Tools
    if tool_names:
        tools_list = ", ".join(tool_names)
        sections.append(
            f"## Tools\nAvailable tools: {tools_list}\n"
            "Use tools when they help. Don't narrate routine tool calls."
        )

    return "\n\n".join(sections)


def _get_current_time(tz_name: str | None) -> str:
    """Format current datetime with optional timezone."""
    if tz_name:
        try:
            tz = ZoneInfo(tz_name)
            now = datetime.now(tz)
            return f"{now.strftime('%A, %B %d, %Y %I:%M %p')} ({tz_name})"
        except (KeyError, Exception):
            pass
    now = datetime.now(timezone.utc)
    return f"{now.strftime('%A, %B %d, %Y %I:%M %p')} (UTC)"
