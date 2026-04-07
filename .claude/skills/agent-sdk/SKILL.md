---
name: agent-sdk
description: Claude Agent SDK patterns for the Clarity platform (Python). Use when building agents, subagents, custom tools, hooks, or skills that integrate Clarity with the Agent SDK. Covers query(), ClaudeSDKClient, AgentDefinition, HookMatcher, MCP servers, sessions, permissions, and hosting patterns.
---

# Claude Agent SDK — Skill Index (Python)

The Claude Agent SDK (`claude-agent-sdk`, formerly "Claude Code SDK") gives you Claude Code's autonomous agent loop as a library. Clarity uses it for PRD-003: orchestration-layer workflows where Clarity is the brain and Claude Code is the hands.

```
query(prompt, options)  →  async iterator of messages
                            ├── SystemMessage (init, compact_boundary)
                            ├── AssistantMessage (text + tool calls per turn)
                            ├── UserMessage (tool results fed back)
                            ├── StreamEvent (partial deltas, opt-in)
                            └── ResultMessage (final: result, cost, session_id)
```

## Reference Pages

| Topic | File | When to read |
|-------|------|-------------|
| Agents & subagents | [references/agents.md](references/agents.md) | Building agents, defining subagents, context isolation, `query()` vs `ClaudeSDKClient` |
| Hooks | [references/hooks.md](references/hooks.md) | Intercepting tool calls, blocking/modifying operations, audit logging, notifications |
| Custom tools | [references/tools.md](references/tools.md) | `@tool` decorator, `create_sdk_mcp_server`, external MCP servers, error handling |
| Skills & plugins | [references/skills-and-plugins.md](references/skills-and-plugins.md) | Loading filesystem skills, plugin structure, namespacing |
| Sessions | [references/sessions.md](references/sessions.md) | Resume, fork, continue, cross-host, `ClaudeSDKClient` multi-turn |
| Permissions | [references/permissions.md](references/permissions.md) | Permission modes, evaluation order, `can_use_tool`, scoped rules |
| Clarity integration | [references/clarity-integration.md](references/clarity-integration.md) | PRD-003 mapping, Capability Gateway, wiring Clarity services as SDK tools |
| Anti-patterns | [references/anti-patterns.md](references/anti-patterns.md) | Common mistakes with wrong/right code examples |

## Standards

These apply to all Agent SDK code in Clarity.

### Always do

1. **Set `max_turns` and `max_budget_usd`** on every production agent. Open-ended loops are expensive.
2. **Check `ResultMessage.subtype`** before reading `.result` — it's `None` on error subtypes.
3. **Catch exceptions inside custom tool handlers.** Uncaught exceptions kill the agent loop.
4. **Use `disallowed_tools`** (not `allowed_tools`) to block tools in `bypassPermissions` mode.
5. **Set `setting_sources=["project"]`** when you need CLAUDE.md or skills. The `claude_code` preset does NOT load them.
6. **Put persistent instructions in CLAUDE.md**, not the prompt. Prompts get compacted; CLAUDE.md is re-injected every request.
7. **Include `"Agent"` in parent's `allowed_tools`** when using subagents. Subagents are invoked via the Agent tool.
8. **Pass context explicitly** to subagents via the Agent tool's prompt string — they don't see the parent's conversation.

### Never do

1. **Don't include `Agent` in a subagent's `tools`.** Subagents cannot spawn sub-subagents.
2. **Don't assume `allowed_tools` constrains `bypassPermissions`.** It doesn't — every tool runs.
3. **Don't let tool handlers throw.** Return `{"is_error": True}` instead.
4. **Don't read `.result` without checking `.subtype == "success"`.**
5. **Don't use `can_use_tool` in Python without a dummy `PreToolUse` hook** that returns `{"continue_": True}`.

## ClaudeAgentOptions Quick Reference

| Option | Type | Default | Purpose |
|--------|------|---------|---------|
| `allowed_tools` | `list[str]` | `[]` | Pre-approve tools (no prompting) |
| `disallowed_tools` | `list[str]` | `[]` | Always deny (overrides everything) |
| `permission_mode` | `str` | `"default"` | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan` |
| `system_prompt` | `str \| dict` | minimal | Custom string or preset dict |
| `setting_sources` | `list[str]` | `[]` | `["project"]` loads CLAUDE.md + skills |
| `max_turns` | `int` | unlimited | Cap tool-use round trips |
| `max_budget_usd` | `float` | unlimited | Cap spend |
| `effort` | `str` | model default | `"low"`, `"medium"`, `"high"`, `"max"` |
| `model` | `str` | CC default | e.g. `"claude-sonnet-4-6"` |
| `cwd` | `str` | process cwd | Working directory for the agent |
| `resume` | `str` | — | Session ID to resume |
| `continue_conversation` | `bool` | `False` | Resume most recent session in cwd |
| `fork_session` | `bool` | `False` | Branch from resumed session |
| `mcp_servers` | `dict` | — | MCP server configs (see [tools.md](references/tools.md)) |
| `agents` | `dict[str, AgentDefinition]` | — | Subagent definitions (see [agents.md](references/agents.md)) |
| `hooks` | `dict[str, list[HookMatcher]]` | — | Event callbacks (see [hooks.md](references/hooks.md)) |
| `tools` | `list[str]` | all built-ins | Restrict which built-in tools are in context |
| `plugins` | `list[dict]` | — | Plugin paths (see [skills-and-plugins.md](references/skills-and-plugins.md)) |
| `can_use_tool` | `callable` | — | Runtime approval callback (see [permissions.md](references/permissions.md)) |
| `include_partial_messages` | `bool` | `False` | Enable `StreamEvent` messages |

## Message Types

```python
from claude_agent_sdk import (
    SystemMessage,      # init (session metadata), compact_boundary
    AssistantMessage,   # Claude's response: text blocks + tool_use blocks
    UserMessage,        # Tool results sent back to Claude
    ResultMessage,      # Always last: .subtype, .result, .session_id, .total_cost_usd
)
from claude_agent_sdk.types import StreamEvent  # Partial deltas (opt-in)
```

| ResultMessage subtype | Meaning | `.result` present? |
|----------------------|---------|-------------------|
| `success` | Task completed | Yes |
| `error_max_turns` | Hit turn limit | No |
| `error_max_budget_usd` | Hit budget limit | No |
| `error_during_execution` | API failure or cancelled | No |
