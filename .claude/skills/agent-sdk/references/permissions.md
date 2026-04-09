# Permissions

## Evaluation Order

When Claude requests a tool, the SDK checks in this order:

1. **Hooks** — can allow, deny, or pass through
2. **Deny rules** — `disallowed_tools` and settings.json deny rules. Blocks even in `bypassPermissions`.
3. **Permission mode** — `bypassPermissions` approves everything that reaches here. `acceptEdits` approves file ops.
4. **Allow rules** — `allowed_tools` and settings.json allow rules
5. **`can_use_tool` callback** — runtime approval. Skipped in `dontAsk` mode (denied instead).

## Permission Modes

| Mode | Behavior |
|------|----------|
| `default` | Unmatched tools trigger `can_use_tool`; no callback = deny |
| `acceptEdits` | Auto-approves file edits (Edit, Write, mkdir, rm, mv, cp). Other tools follow default rules. |
| `dontAsk` | Anything not pre-approved by `allowed_tools` or rules is denied. `can_use_tool` never called. |
| `bypassPermissions` | All tools run. **`allowed_tools` does NOT constrain this.** Use `disallowed_tools` to block. Subagents inherit this and it cannot be overridden. |
| `plan` | No tool execution; Claude plans only. May use `AskUserQuestion`. |

## Patterns

### Locked-down headless agent

```python
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Glob", "Grep"],
    permission_mode="dontAsk",
)
```

### Trusted dev workflow

```python
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Edit", "Write", "Glob", "Grep", "Bash"],
    permission_mode="acceptEdits",
)
```

### Dynamic escalation

```python
q = query(prompt="Help me refactor", options=ClaudeAgentOptions(permission_mode="default"))
await q.set_permission_mode("acceptEdits")  # Escalate mid-session
async for message in q:
    ...
```

### Scoped tool rules

`allowed_tools` supports scoped rules: `"Bash(npm:*)"` allows only npm commands.

## `can_use_tool` Callback

```python
from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny

async def can_use_tool(tool_name, input_data, context):
    if tool_name == "AskUserQuestion":
        return await handle_questions(input_data)
    if tool_name == "Bash" and "rm -rf" in input_data.get("command", ""):
        return PermissionResultDeny(message="Destructive command blocked")
    return PermissionResultAllow(updated_input=input_data)
```

### Response types

| Response | Effect |
|----------|--------|
| `PermissionResultAllow(updated_input=input_data)` | Allow (can modify input) |
| `PermissionResultDeny(message="reason")` | Block; Claude sees the message |

### AskUserQuestion handling

When Claude needs clarification, it calls `AskUserQuestion`. Input contains `questions` array with `question`, `options`, `multiSelect`:

```python
async def can_use_tool(tool_name, input_data, context):
    if tool_name == "AskUserQuestion":
        answers = {}
        for q in input_data.get("questions", []):
            print(f"\n{q['header']}: {q['question']}")
            for i, opt in enumerate(q["options"]):
                print(f"  {i+1}. {opt['label']} - {opt['description']}")
            choice = input("Your choice: ").strip()
            try:
                idx = int(choice) - 1
                answers[q["question"]] = q["options"][idx]["label"]
            except (ValueError, IndexError):
                answers[q["question"]] = choice  # Free text
        return PermissionResultAllow(
            updated_input={"questions": input_data["questions"], "answers": answers}
        )
    return PermissionResultAllow(updated_input=input_data)
```

### Python quirk

`can_use_tool` requires streaming mode and a dummy `PreToolUse` hook:

```python
async def dummy_hook(input_data, tool_use_id, context):
    return {"continue_": True}

options = ClaudeAgentOptions(
    can_use_tool=my_callback,
    hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[dummy_hook])]},
)
```

## System Prompts

```python
# Minimal default (tool instructions only)
options = ClaudeAgentOptions()

# Full Claude Code prompt
options = ClaudeAgentOptions(
    system_prompt={"type": "preset", "preset": "claude_code"}
)

# Claude Code + custom append
options = ClaudeAgentOptions(
    system_prompt={"type": "preset", "preset": "claude_code", "append": "Follow PEP 8."}
)

# Fully custom (loses built-in guidelines)
options = ClaudeAgentOptions(system_prompt="You are a Python specialist...")
```

**CLAUDE.md requires `setting_sources`.** The preset does NOT load it automatically.

**Compaction-safe:** Put persistent rules in CLAUDE.md (re-injected every request), not the prompt (can be lost during compaction).
