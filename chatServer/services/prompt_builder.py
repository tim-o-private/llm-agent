"""Prompt builder service — assembles agent system prompt from sections."""

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
    "This is the very first time you are meeting this user.\n"
    "No one typed anything yet — you are initiating the conversation.\n\n"
    "Your job:\n"
    "1. Introduce yourself warmly and briefly using your identity.\n"
    "2. Ask what their key priorities are and how they'd like to use you.\n"
    "3. Ask about communication preferences (concise vs detailed, formal vs casual).\n"
    "4. When they respond, use save_memory and update_instructions to record what you learn.\n\n"
    "One warm, natural opening message. Don't interrogate — you can learn more over time."
)

SESSION_OPEN_RETURNING_GUIDANCE = (
    "The user just returned to the app. {time_context}\n"
    "No one typed anything yet — you are deciding whether to initiate.\n\n"
    "Decision rules:\n"
    "- If the user was here less than 5 minutes ago AND nothing new is in flight: "
    "respond with exactly: WAKEUP_SILENT\n"
    "- Otherwise: check your tools (tasks, reminders, optionally emails), then greet "
    "with a brief summary of what needs attention.\n\n"
    "If you greet: 2-4 sentences max. State facts, don't ask questions.\n"
    "Example: 'Morning! 2 tasks due today and a reminder at 3pm.'\n"
    "If nothing is in flight but enough time has passed: say so briefly and offer to help."
)

MAX_INSTRUCTIONS_LENGTH = 2000

ONBOARDING_SECTION = (
    "This appears to be your first interaction with this user.\n"
    "Their memory is empty and they have no custom instructions set.\n\n"
    "Welcome the user warmly and help them get started:\n"
    "1. Introduce yourself briefly using your identity.\n"
    "2. Ask about their key priorities and how they'd like to use you.\n"
    "3. Ask about communication preferences (concise vs detailed, formal vs casual).\n"
    "4. After gathering answers, use save_memory to record what you learn.\n"
    "5. Use update_instructions to set initial standing instructions.\n\n"
    "Keep it conversational — you can learn more over time."
)

def _format_time_context(last_message_at: datetime | None) -> str:
    if last_message_at is None:
        return "This is the first time opening this session."
    ts = last_message_at.astimezone(timezone.utc) if last_message_at.tzinfo else last_message_at.replace(tzinfo=timezone.utc)
    elapsed = datetime.now(timezone.utc) - ts
    minutes = int(elapsed.total_seconds() / 60)
    if minutes < 2:
        return "Your last interaction was less than 2 minutes ago."
    if minutes < 60:
        return f"Your last interaction was {minutes} minutes ago."
    hours = minutes // 60
    return f"Your last interaction was {hours} hour{'s' if hours > 1 else ''} ago."


def build_agent_prompt(
    soul: str,
    identity: dict | None,
    channel: str,
    user_instructions: str | None,
    timezone: str | None = None,
    tools: list | None = None,
    memory_notes: str | None = None,
    last_message_at: datetime | None = None,
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

    # 5. What You Know (pre-loaded memory)
    if memory_notes:
        truncated_notes = memory_notes[:4000]
        sections.append(
            f"## What You Know\n"
            f"These are your accumulated notes about this user:\n{truncated_notes}"
        )

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

    # 7. Tool Guidance
    if tools:
        seen_classes = set()
        guidance_lines = []
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
                pass  # Never fail the prompt build for a single tool
        if guidance_lines:
            sections.append("## Tool Guidance\n" + "\n".join(guidance_lines))

    # 8. Session Open / Onboarding
    is_new_user = not memory_notes and not user_instructions
    if channel == "session_open":
        if is_new_user:
            sections.append(f"## Session Open\n{SESSION_OPEN_BOOTSTRAP_GUIDANCE}")
        else:
            time_context = _format_time_context(last_message_at)
            guidance = SESSION_OPEN_RETURNING_GUIDANCE.format(time_context=time_context)
            sections.append(f"## Session Open\n{guidance}")
    elif channel in ("web", "telegram") and is_new_user:
        sections.append(f"## Onboarding\n{ONBOARDING_SECTION}")

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
