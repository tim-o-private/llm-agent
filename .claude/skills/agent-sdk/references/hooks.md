# Hooks

Hooks intercept agent events with callback functions. They run in your process, not in the agent's context window — no token cost.

## Configuration

```python
from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Write|Edit", hooks=[my_callback])
        ]
    }
)
```

## Hook Events (Python SDK)

| Event | Fires when | Common use |
|-------|-----------|------------|
| `PreToolUse` | Before tool executes | Block, modify input, auto-approve |
| `PostToolUse` | After tool returns | Audit, log, add context |
| `PostToolUseFailure` | Tool execution fails | Error handling |
| `UserPromptSubmit` | Prompt submitted | Inject context |
| `Stop` | Agent finishes | Save state |
| `SubagentStart` | Subagent spawns | Track parallel work |
| `SubagentStop` | Subagent completes | Aggregate results |
| `PreCompact` | Before compaction | Archive transcript |
| `PermissionRequest` | Permission dialog would show | Custom permission handling |
| `Notification` | Agent status message | Forward to Slack/PagerDuty |

**Not available in Python:** `SessionStart`, `SessionEnd`, `TeammateIdle`, `TaskCompleted`, `ConfigChange`, `WorktreeCreate`, `WorktreeRemove` (TypeScript only).

## Callback Signature

```python
async def my_hook(
    input_data: dict,         # Event-specific: tool_name, tool_input, session_id, cwd, etc.
    tool_use_id: str | None,  # Correlates Pre/PostToolUse for same call
    context: Any,             # Reserved for future use
) -> dict:
    ...
```

All hook inputs share `session_id`, `cwd`, `hook_event_name`. Tool hooks add `tool_name`, `tool_input`. Subagent hooks add `agent_id`, `agent_type`.

## Return Values

| Return | Effect |
|--------|--------|
| `{}` | Allow the operation, no changes |
| `{"hookSpecificOutput": {"permissionDecision": "deny", ...}}` | Block the tool |
| `{"hookSpecificOutput": {"permissionDecision": "allow", "updatedInput": {...}}}` | Modify input and allow |
| `{"systemMessage": "..."}` | Inject context into conversation (model sees it) |
| `{"continue_": False}` | Stop the agent loop |
| `{"async_": True, "asyncTimeout": 30000}` | Fire-and-forget (don't block) |

**Priority:** deny > ask > allow. If any hook denies, the tool is blocked.

**`updatedInput` requires `permissionDecision: "allow"`.** Always return a new object; don't mutate the original.

## Matchers

`matcher` is a regex matched against the tool name:
- `"Write|Edit"` — fires for Write or Edit
- `"^mcp__"` — fires for all MCP tools
- Omit matcher — fires for every event of that type

Matchers filter by **tool name only**. To filter by file path, check `input_data["tool_input"]` inside the callback.

## Patterns

### Block dangerous operations

```python
async def protect_env_files(input_data, tool_use_id, context):
    file_path = input_data["tool_input"].get("file_path", "")
    if file_path.split("/")[-1] == ".env":
        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "deny",
                "permissionDecisionReason": "Cannot modify .env files",
            }
        }
    return {}
```

### Modify tool input (sandbox redirect)

```python
async def redirect_to_sandbox(input_data, tool_use_id, context):
    if input_data["tool_name"] == "Write":
        original_path = input_data["tool_input"].get("file_path", "")
        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "allow",
                "updatedInput": {
                    **input_data["tool_input"],
                    "file_path": f"/sandbox{original_path}",
                },
            }
        }
    return {}
```

### Block + inject context

```python
async def block_etc_writes(input_data, tool_use_id, context):
    file_path = input_data["tool_input"].get("file_path", "")
    if file_path.startswith("/etc"):
        return {
            "systemMessage": "System directories like /etc are protected.",
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "deny",
                "permissionDecisionReason": "Writing to /etc is not allowed",
            },
        }
    return {}
```

### Chain multiple hooks

Hooks execute in array order. Keep each focused on one responsibility:

```python
hooks={
    "PreToolUse": [
        HookMatcher(hooks=[rate_limiter]),
        HookMatcher(hooks=[authorization_check]),
        HookMatcher(hooks=[input_sanitizer]),
        HookMatcher(hooks=[audit_logger]),
    ]
}
```

### Fire-and-forget (async)

For side effects that shouldn't block the agent:

```python
async def async_logger(input_data, tool_use_id, context):
    asyncio.create_task(send_to_logging_service(input_data))
    return {"async_": True, "asyncTimeout": 30000}
```

Async hooks cannot block, modify, or inject context.

### Notification forwarding

```python
async def slack_notifier(input_data, tool_use_id, context):
    try:
        await asyncio.to_thread(send_slack_message, input_data.get("message", ""))
    except Exception as e:
        print(f"Slack notification failed: {e}")
    return {}

hooks={"Notification": [HookMatcher(hooks=[slack_notifier])]}
```

Notification types: `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog`.

### Subagent tracking

```python
async def subagent_tracker(input_data, tool_use_id, context):
    print(f"[SUBAGENT] Completed: {input_data['agent_id']}")
    print(f"  Transcript: {input_data['agent_transcript_path']}")
    return {}

hooks={"SubagentStop": [HookMatcher(hooks=[subagent_tracker])]}
```

## Troubleshooting

- **Hook not firing:** Event names are case-sensitive (`PreToolUse`, not `preToolUse`). Check matcher matches the tool name.
- **Matcher too broad:** Empty matcher matches ALL tools. Be explicit.
- **Modified input not applied:** `updatedInput` must be inside `hookSpecificOutput` with `permissionDecision: "allow"`.
- **systemMessage not in output:** It's added to the conversation for the model, not necessarily visible in SDK output.
