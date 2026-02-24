# Prompt Engineering — Full Reference

Extended patterns, code examples, anti-patterns, and rationale for the llm-agent prompt system.

## Prompt Assembly Pipeline — In Detail

### The Two Paths

**Path A: DB Template (primary)**

```python
# prompt_builder.py — template path
if prompt_template:
    rendered = string.Template(prompt_template).safe_substitute(values)
    rendered = re.sub(r'## \w[\w ]*\n\s*\n', '', rendered)  # strip empty sections
    rendered = re.sub(r'\n{3,}', '\n\n', rendered).strip()   # collapse newlines
    return rendered
```

The template lives in `agent_configurations.prompt_template`. Example (current production for `assistant`):

```
## Identity
$identity

## Soul
$soul

## Operating Model
$operating_model

## Channel
You are responding via the current channel. $channel_guidance

## Current Time
$current_time

## What You Know
$memory_notes

## User Instructions
$user_instructions

## Tool Guidance
$tool_guidance

## Interaction Learning
$interaction_learning

## Session
$session_section
```

**Path B: Hardcoded Fallback**

Used when `prompt_template` is NULL. Mirrors the template exactly but in code:

```python
# prompt_builder.py — hardcoded path
sections: list[str] = []
if values["identity"]:
    sections.append(f"## Identity\n{values['identity']}")
sections.append(f"## Soul\n{values['soul']}")
if values["operating_model"]:
    sections.append(f"## How You Operate\n{values['operating_model']}")
# ... etc
return "\n\n".join(sections)
```

**Why two paths?** The template path was added in SPEC-019 so prompts could be iterated via DB updates without code deploys. The hardcoded path remains as a fallback for agents without a template row.

### Placeholder Resolution

All placeholders are computed in `_compute_section_values()`:

```python
{
    "identity":             _format_identity_str(identity),           # "{name} — {description}. {vibe}"
    "soul":                 soul or "You are a helpful assistant.",    # raw text from DB
    "operating_model":      OPERATING_MODEL if interactive else "",   # static constant
    "channel_guidance":     CHANNEL_GUIDANCE.get(channel, ...),       # static dict lookup
    "current_time":         _get_current_time(timezone),              # "Monday, February 24, 2026 ..."
    "memory_notes":         _format_memory_notes_str(memory_notes),   # "These are your accumulated notes..."
    "user_instructions":    _format_instructions_str(instructions),   # text + hint about update_instructions
    "tool_guidance":        _format_tool_guidance(tools, channel),    # aggregated prompt_section() calls
    "interaction_learning": INTERACTION_LEARNING_GUIDANCE if interactive else "",
    "session_section":      _format_session_str(channel, ...),        # onboarding/session_open/empty
}
```

### Channel-Conditional Behavior

| Section | web | telegram | scheduled | heartbeat | session_open |
|---------|-----|----------|-----------|-----------|--------------|
| Identity | Yes | Yes | Yes | Yes | Yes |
| Soul | Yes | Yes | Yes | Yes | Yes |
| Operating Model | Yes | Yes | No | No | Yes |
| Channel Guidance | Yes | Yes | Yes | Yes | Yes |
| Current Time | Yes | Yes | Yes | Yes | Yes |
| Memory Notes | If present | If present | If present | If present | If present |
| User Instructions | Yes | Yes | Yes | Yes | Yes |
| Tool Guidance | Yes | Yes | Yes | Yes | Yes |
| Interaction Learning | Yes | Yes | No | No | No |
| Session/Onboarding | If new user | If new user | No | No | Always |

## Writing Effective Soul Text

### Good Soul Examples

```
You manage things so the user doesn't have to hold it all in their head.

Be direct and practical. Skip pleasantries when the user is clearly in work mode.
Match their energy — brief for brief, thoughtful for thoughtful.

Have opinions about priorities when asked. "Everything is important" is never useful.

When you learn something about the user — preferences, context, how they like
things — save it to memory without being asked. You should know more about them
with each conversation.

Don't narrate your tool calls or explain what you're about to do. Just do it.
```

**Why this works:**
- First line establishes the core purpose — framing, not instructions
- "Match their energy" is adaptive behavior, not a rigid rule
- "Everything is important is never useful" gives a concrete anti-pattern
- "Don't narrate" is a behavioral constraint that shapes every interaction

### Anti-Pattern: Procedural Soul

```
# BAD — this is procedure, not philosophy
You are an assistant. When the user sends a message:
1. First check their tasks
2. Then check their emails
3. Summarize what you found
4. Ask if they need anything else
```

**Why this fails:** Soul is about character and judgment. Procedures go in Operating Model or Tool Guidance. A procedural soul makes the agent rigid and predictable in a bad way.

### Anti-Pattern: Vague Soul

```
# BAD — says nothing actionable
You are helpful, friendly, and professional. You always try your best
to assist the user with whatever they need.
```

**Why this fails:** Every AI agent is "helpful and professional." This constrains nothing and shapes no behavior. Good soul text creates clear preferences that trade off against something.

### Anti-Pattern: Contradictory Soul

```
# BAD — conflicting instructions
Always be concise. Provide thorough, detailed explanations for every topic.
Be proactive about suggesting actions. Wait for the user to ask before doing anything.
```

**Why this fails:** The agent will oscillate between behaviors unpredictably. Each directive should be compatible with the others. If there's tension, resolve it with context: "Be concise by default. Go deep when the user asks for explanation."

## Writing Tool Descriptions vs Tool Guidance

### Tool Description (`tools.description` column)

This is what the LLM sees next to the tool's JSON schema when deciding whether to call it. Keep it **factual, concise, and focused on capability**.

```
# GOOD
"Search Gmail messages. Supports Gmail search syntax (from:, subject:, after:, label:, etc)."

# BAD — behavioral instruction in a description
"Search Gmail messages. Always search before answering email questions. Use after: for time-based queries."
```

### Tool Guidance (`prompt_section()` method)

This is behavioral context injected into the system prompt. It tells the agent **when and why** to use the tool, not what the tool does.

```python
# GOOD — behavioral, contextual
@classmethod
def prompt_section(cls, channel: str) -> str | None:
    return (
        "Use search_gmail and get_gmail for email tasks. "
        "Search first to find messages, then get_gmail for full content. "
        "For time-based queries, use after:<unix_timestamp> not newer_than:Xh."
    )

# BAD — duplicates the tool description
@classmethod
def prompt_section(cls, channel: str) -> str | None:
    return "search_gmail searches Gmail messages using Gmail search syntax."
```

### Channel-Aware Tool Guidance

```python
@classmethod
def prompt_section(cls, channel: str) -> str | None:
    if channel in ("scheduled", "heartbeat"):
        return (
            "Check tasks systematically. Report only actionable items — "
            "don't pad with 'everything looks good' filler."
        )
    return (
        "Check get_tasks at conversation start to know what's active. "
        "When the user mentions something to do, create a task without asking."
    )
```

## Identity Configuration

The `identity` JSONB has three fields:

```json
{
  "name": "Clarity",
  "description": "a personal assistant for email, tasks, and reminders",
  "vibe": "direct and helpful"
}
```

Rendered as: `"You are Clarity — a personal assistant for email, tasks, and reminders. direct and helpful"`

**Guidelines:**
- `name`: Short, memorable. Used in greeting context.
- `description`: What the agent does. Starts lowercase (follows "You are {name} —").
- `vibe`: Optional. Adjective phrase that colors the identity line. Not a full sentence.

## Session & Onboarding Logic

### Decision Tree

```
channel == "session_open"?
  ├── Yes → is_new_user (no memory AND no instructions)?
  │     ├── Yes → SESSION_OPEN_BOOTSTRAP_GUIDANCE (show usefulness)
  │     └── No  → SESSION_OPEN_RETURNING_GUIDANCE (check elapsed time)
  └── No → channel in ("web", "telegram") AND is_new_user?
        ├── Yes → ONBOARDING_SECTION (first interactive message)
        └── No  → "" (no session section)
```

### Key Behaviors

**SESSION_OPEN_RETURNING_GUIDANCE** has a silence rule:
- < 5 minutes since last message AND nothing new → respond `WAKEUP_SILENT`
- Otherwise → greet with brief status

This prevents the agent from spamming greetings on every tab focus.

**ONBOARDING_SECTION** fires only when:
- Channel is interactive (web/telegram)
- Both `memory_notes` and `user_instructions` are empty (truly new user)
- The user sent an actual message (not session_open)

## Testing Prompts

### Via clarity-dev MCP (recommended)

```python
# From Claude Code — sends a real message through the full pipeline
chat_with_clarity(message="what's on my plate today?", agent_name="assistant")
```

This exercises the complete path: config fetch → tool loading → prompt assembly → LLM call → response.

### Via Direct DB Update

```sql
-- Change soul text (takes effect after cache expires or server restart)
UPDATE agent_configurations
SET soul = 'New soul text here', updated_at = NOW()
WHERE agent_name = 'assistant';
```

### Via Logging

Add temporary logging to `build_agent_prompt()`:

```python
import logging
logger = logging.getLogger(__name__)

def build_agent_prompt(...) -> str:
    # ... assembly ...
    logger.info("Assembled prompt length: %d chars", len(result))
    logger.debug("Full prompt:\n%s", result)
    return result
```

Check `logs/chatserver.log` for output.

## Migration Patterns for Prompt Changes

### Soul Update

```sql
-- Migration: YYYYMMDDHHMMSS_update_assistant_soul.sql
UPDATE agent_configurations
SET soul = $$
Your new soul text here.
Multi-line is fine — use dollar-quoting.
$$,
    updated_at = NOW()
WHERE agent_name = 'assistant';
```

### Template Update

```sql
UPDATE agent_configurations
SET prompt_template = $$## Identity
$identity

## Soul
$soul

## New Section
$new_placeholder

## Operating Model
$operating_model
$$,
    updated_at = NOW()
WHERE agent_name = 'assistant';
```

**Remember:** If you add a new `$placeholder`, you must also add its computation in `_compute_section_values()` in prompt_builder.py.

### Tool Description Update

```sql
UPDATE tools
SET description = 'New description here',
    updated_at = NOW()
WHERE name = 'tool_name';
```

## Common Prompt Engineering Tasks

### Reducing Verbosity

The most common prompt engineering task. Approaches:
1. **Soul:** Add "Don't narrate your tool calls" or "Lead with the answer, not the process"
2. **Operating model:** Remove "announce" language. Replace "Tell the user..." with "Do X."
3. **Tool guidance:** Remove explanatory text. "Use search_gmail for email" not "When the user asks about email, you should consider using the search_gmail tool to look up..."

### Improving Tool Usage

When the agent doesn't use a tool it should:
1. **Check tool description** — is it clear when to use it?
2. **Add/improve `prompt_section()`** — behavioral trigger: "When the user mentions X, use tool_name"
3. **Check Operating Model** — for proactive tools, add "check X at conversation start"

When the agent overuses a tool:
1. **Add negative guidance** in `prompt_section()`: "Only use X when the user explicitly asks"
2. **Check if multiple tools overlap** — consolidate descriptions to reduce ambiguity

### Adding a New Agent

1. Insert `agent_configurations` row with `agent_name`, `soul`, `identity`, `llm_config`
2. Link tools via `agent_tools` join table
3. Optionally set `prompt_template` (or NULL for hardcoded fallback)
4. Add channel-appropriate guidance if the agent operates on non-standard channels

## Evaluation Heuristics

When reviewing a prompt change, ask:

1. **Does the assembled prompt read coherently?** Sections should flow, not feel like a checklist.
2. **Is there redundancy?** The same instruction in soul AND operating model AND tool guidance wastes tokens and creates ambiguity about which one "wins."
3. **Are constraints testable?** "Be helpful" isn't testable. "Don't ask more than one question per response" is.
4. **Does it degrade gracefully?** What happens when memory is empty? When tools fail? When the user sends a one-word message?
5. **Token budget?** The assembled prompt shouldn't exceed ~2000 tokens for interactive channels. Longer prompts slow response time and crowd out conversation context.
