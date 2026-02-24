"""Prompt builder service — assembles agent system prompt from sections."""

import re
import string
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

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

SESSION_OPEN_BOOTSTRAP_GUIDANCE = (
    "This is the first time you are meeting this user.\n"
    "No one typed anything yet — you are initiating.\n\n"
    "Your job is to introduce yourself and start learning about this person.\n\n"
    "Steps:\n"
    "1. Introduce yourself in one sentence — who you are and what you do for them.\n"
    "2. Ask one concrete, open-ended question to start learning about them.\n"
    "   Something like: 'What's eating your time right now?' or\n"
    "   'What's one thing you wish you could get off your plate?'\n"
    "3. Call create_memories to record your initial observations after they respond.\n\n"
    "Do NOT:\n"
    "- Call get_tasks, get_reminders, or search_gmail — there's nothing to find yet.\n"
    "- Ask about communication preferences or what tools they use.\n"
    "- List your features or capabilities.\n\n"
    "Learn about them from how they respond to you."
)

SESSION_OPEN_RETURNING_GUIDANCE = (
    "The user just returned to the app. {time_context}\n"
    "No one typed anything yet — you are deciding whether to initiate.\n\n"
    "Context from your tools (pre-fetched):\n"
    "$bootstrap_context\n\n"
    "Decision rules:\n"
    "- If nothing needs attention and it's been less than 30 minutes: "
    "respond with exactly: WAKEUP_SILENT\n"
    "- Otherwise: greet with a brief summary of what needs attention.\n\n"
    "If you greet: 2-4 sentences max. State facts from the context above. "
    "Don't call tools to re-fetch what's already in your prompt.\n"
    "Example: 'Morning! 2 tasks due today and a reminder at 3pm.'"
)

MAX_INSTRUCTIONS_LENGTH = 2000

ONBOARDING_SECTION = (
    "This appears to be your first interaction with this user.\n"
    "Their memory is empty and they have no custom instructions set.\n\n"
    "Your job is to introduce yourself and start learning about this person.\n\n"
    "Steps:\n"
    "1. Introduce yourself briefly using your identity.\n"
    "2. Ask one concrete, open-ended question to start learning.\n"
    "3. Call create_memories to record initial observations after they respond.\n\n"
    "Do NOT call get_tasks, get_reminders, or search_gmail — there's nothing to find.\n"
    "Do NOT ask about communication preferences or priorities.\n"
    "Learn those from how they respond to you."
)

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

def _format_time_context(last_message_at: datetime | None) -> str:
    if last_message_at is None:
        return "This is the first time opening this session."
    if last_message_at.tzinfo:
        ts = last_message_at.astimezone(timezone.utc)
    else:
        ts = last_message_at.replace(tzinfo=timezone.utc)
    elapsed = datetime.now(timezone.utc) - ts
    minutes = int(elapsed.total_seconds() / 60)
    if minutes < 2:
        return "Your last interaction was less than 2 minutes ago."
    if minutes < 60:
        return f"Your last interaction was {minutes} minutes ago."
    hours = minutes // 60
    return f"Your last interaction was {hours} hour{'s' if hours > 1 else ''} ago."


def _format_identity_str(identity: dict | None) -> str:
    """Format identity dict into a single line."""
    if not identity:
        return ""
    name = identity.get("name") or "an AI assistant"
    description = identity.get("description") or "a personal assistant"
    vibe = identity.get("vibe") or ""
    line = f"You are {name} — {description}."
    if vibe:
        line += f" {vibe}"
    return line


def _format_tool_guidance(tools: list | None, channel: str) -> str:
    """Collect prompt_section() from all tool classes."""
    if not tools:
        return ""
    seen_classes: set = set()
    guidance_lines: list[str] = []
    for tool in tools:
        tool_cls = type(tool)
        if tool_cls in seen_classes:
            continue
        seen_classes.add(tool_cls)
        try:
            if hasattr(tool_cls, "prompt_section"):
                section = tool_cls.prompt_section(channel)
                if section:
                    guidance_lines.append(section)
        except Exception:
            pass
    return "\n".join(guidance_lines)


def _format_instructions_str(user_instructions: str | None) -> str:
    """Format user instructions with fallback and hint text."""
    if user_instructions:
        truncated = user_instructions[:MAX_INSTRUCTIONS_LENGTH]
        text = truncated
        if len(user_instructions) > MAX_INSTRUCTIONS_LENGTH:
            text += "\n(Instructions truncated at 2000 characters.)"
    else:
        text = "(No custom instructions set.)"
    text += (
        "\nThe user can change these by telling you things like "
        '"always do X" or "never do Y". '
        "When they do, use the update_instructions tool to persist the change."
    )
    return text


def _format_memory_notes_str(memory_notes: str | None) -> str:
    """Format memory notes section."""
    if not memory_notes:
        return ""
    return f"These are your accumulated notes about this user:\n{memory_notes[:4000]}"


def _format_session_str(
    channel: str,
    memory_notes: str | None,
    user_instructions: str | None,
    last_message_at: datetime | None,
    bootstrap_context: str | None = None,
) -> str:
    """Format session open / onboarding section."""
    is_new_user = not memory_notes and not user_instructions
    if channel == "session_open":
        if is_new_user:
            return SESSION_OPEN_BOOTSTRAP_GUIDANCE
        time_context = _format_time_context(last_message_at)
        result = SESSION_OPEN_RETURNING_GUIDANCE.format(time_context=time_context)
        return string.Template(result).safe_substitute(bootstrap_context=bootstrap_context or "")
    if channel in ("web", "telegram") and is_new_user:
        return ONBOARDING_SECTION
    return ""


def _compute_section_values(
    soul: str,
    identity: dict | None,
    channel: str,
    user_instructions: str | None,
    timezone: str | None,
    tools: list | None,
    memory_notes: str | None,
    last_message_at: datetime | None,
    bootstrap_context: str | None = None,
) -> dict[str, str]:
    """Compute all placeholder values for prompt assembly."""
    return {
        "identity": _format_identity_str(identity),
        "soul": soul or "You are a helpful assistant.",
        "operating_model": OPERATING_MODEL if channel in ("web", "telegram") else "",
        "channel_guidance": CHANNEL_GUIDANCE.get(channel, CHANNEL_GUIDANCE["web"]),
        "current_time": _get_current_time(timezone),
        "memory_notes": _format_memory_notes_str(memory_notes),
        "user_instructions": _format_instructions_str(user_instructions),
        "tool_guidance": _format_tool_guidance(tools, channel),
        "interaction_learning": INTERACTION_LEARNING_GUIDANCE if channel in ("web", "telegram") else "",
        "bootstrap_context": bootstrap_context or "",
        "session_section": _format_session_str(channel, memory_notes, user_instructions, last_message_at, bootstrap_context),
    }


def build_agent_prompt(
    soul: str,
    identity: dict | None,
    channel: str,
    user_instructions: str | None,
    timezone: str | None = None,
    tools: list | None = None,
    memory_notes: str | None = None,
    last_message_at: datetime | None = None,
    prompt_template: str | None = None,
    bootstrap_context: str | None = None,
) -> str:
    """Assemble the agent system prompt from layered sections.

    Args:
        soul: Behavioral philosophy from agent_configurations.soul.
        identity: Structured metadata {name, vibe, description} or None.
        channel: "web", "telegram", "scheduled", "heartbeat", or "session_open".
        user_instructions: Free-text user instructions or None.
        timezone: IANA timezone string (e.g. "America/New_York") or None.
        tools: List of instantiated tool objects (will call prompt_section() on each).
        memory_notes: LTM notes string or None. Used for onboarding detection.
        last_message_at: Timestamp of most recent message in session. Used by
            session_open channel to format time context for the agent.
        prompt_template: string.Template with $placeholder syntax from
            agent_configurations.prompt_template. None = use hardcoded assembly.

    Returns:
        Assembled system prompt string.
    """
    # Compute all section values used by both paths
    values = _compute_section_values(
        soul=soul,
        identity=identity,
        channel=channel,
        user_instructions=user_instructions,
        timezone=timezone,
        tools=tools,
        memory_notes=memory_notes,
        last_message_at=last_message_at,
        bootstrap_context=bootstrap_context,
    )

    # Template path: substitute placeholders and strip empty sections
    if prompt_template:
        rendered = string.Template(prompt_template).safe_substitute(values)
        # Remove sections that are just a header with empty content
        rendered = re.sub(r'## \w[\w ]*\n\s*\n', '', rendered)
        # Collapse triple+ newlines to double
        rendered = re.sub(r'\n{3,}', '\n\n', rendered).strip()
        return rendered

    # Hardcoded assembly path (fallback when no DB template)
    sections: list[str] = []

    if values["identity"]:
        sections.append(f"## Identity\n{values['identity']}")
    sections.append(f"## Soul\n{values['soul']}")
    if values["operating_model"]:
        sections.append(f"## How You Operate\n{values['operating_model']}")
    sections.append(f"## Channel\nYou are responding via {channel}. {values['channel_guidance']}")
    sections.append(f"## Current Time\n{values['current_time']}")
    if values["memory_notes"]:
        sections.append(f"## What You Know\n{values['memory_notes']}")
    sections.append(f"## User Instructions\n{values['user_instructions']}")
    if values["tool_guidance"]:
        sections.append(f"## Tool Guidance\n{values['tool_guidance']}")
    if values["interaction_learning"]:
        sections.append(f"## Interaction Learning\n{values['interaction_learning']}")
    if values["session_section"]:
        # Pick the right header based on channel
        header = "Session Open" if channel == "session_open" else "Onboarding"
        sections.append(f"## {header}\n{values['session_section']}")

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
