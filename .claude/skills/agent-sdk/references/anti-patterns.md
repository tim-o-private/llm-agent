# Anti-Patterns

Common mistakes when using the Agent SDK, with wrong/right examples.

## 1. `allowed_tools` doesn't constrain `bypassPermissions`

```python
# WRONG: Bash, Write, Edit, etc. all still run
options = ClaudeAgentOptions(
    allowed_tools=["Read"],
    permission_mode="bypassPermissions",
)

# RIGHT: Use disallowed_tools to block in bypass mode
options = ClaudeAgentOptions(
    permission_mode="bypassPermissions",
    disallowed_tools=["Bash"],
)
```

## 2. `Agent` in subagent tools

Subagents cannot spawn sub-subagents. The call will fail.

```python
# WRONG
AgentDefinition(tools=["Read", "Agent"])

# RIGHT
AgentDefinition(tools=["Read", "Grep", "Glob"])
```

## 3. Uncaught exceptions in tool handlers

```python
# WRONG: Kills the agent loop
@tool("risky", "...", {"x": str})
async def risky(args):
    response = await client.get(args["x"])
    return {"content": [{"type": "text", "text": response.text}]}

# RIGHT: Catch and return is_error
@tool("risky", "...", {"x": str})
async def risky(args):
    try:
        response = await client.get(args["x"])
        return {"content": [{"type": "text", "text": response.text}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": str(e)}], "is_error": True}
```

## 4. Reading `.result` without checking subtype

```python
# WRONG: result is None on error subtypes
print(message.result)

# RIGHT
if message.subtype == "success":
    print(message.result)
else:
    print(f"Stopped: {message.subtype}")
```

## 5. Persistent instructions in prompt

```python
# WRONG: May be lost during compaction
options = ClaudeAgentOptions(
    system_prompt="Always use PEP 8 and run tests before finishing."
)

# RIGHT: Put it in CLAUDE.md and load via setting_sources
options = ClaudeAgentOptions(setting_sources=["project"])
```

## 6. Forgetting `setting_sources` for skills

```python
# WRONG: Skills won't load
options = ClaudeAgentOptions(allowed_tools=["Skill"])

# RIGHT
options = ClaudeAgentOptions(
    setting_sources=["project"],
    allowed_tools=["Skill"],
)
```

## 7. `can_use_tool` without dummy hook (Python)

```python
# WRONG: Callback never fires
options = ClaudeAgentOptions(can_use_tool=my_callback)

# RIGHT: Need a PreToolUse hook to keep stream open
async def dummy_hook(input_data, tool_use_id, context):
    return {"continue_": True}

options = ClaudeAgentOptions(
    can_use_tool=my_callback,
    hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[dummy_hook])]},
)
```

## 8. `updatedInput` without `permissionDecision`

```python
# WRONG: Input modification ignored
return {"hookSpecificOutput": {"updatedInput": new_input}}

# RIGHT: Must include permissionDecision: "allow"
return {
    "hookSpecificOutput": {
        "hookEventName": input_data["hook_event_name"],
        "permissionDecision": "allow",
        "updatedInput": new_input,
    }
}
```

## 9. Formatting cost without None guard

```python
# WRONG: Crashes on error paths where total_cost_usd is None
print(f"Cost: ${message.total_cost_usd:.4f}")

# RIGHT
if message.total_cost_usd is not None:
    print(f"Cost: ${message.total_cost_usd:.4f}")
```

## 10. Expecting `claude_code` preset loads CLAUDE.md

```python
# WRONG: CLAUDE.md not loaded
options = ClaudeAgentOptions(
    system_prompt={"type": "preset", "preset": "claude_code"}
)

# RIGHT: Must also set setting_sources
options = ClaudeAgentOptions(
    system_prompt={"type": "preset", "preset": "claude_code"},
    setting_sources=["project"],
)
```
