# Sessions

Sessions persist conversation history to disk. Resume to continue with full context — files read, analysis done, decisions made.

## Three Modes

| Mode | Finds session by | Use when |
|------|-----------------|----------|
| `continue_conversation=True` | Most recent in cwd | One conversation at a time |
| `resume=session_id` | Specific ID | Multiple sessions, specific recovery |
| `fork_session=True` + `resume` | Branches from ID | Explore alternatives (original unchanged) |

## Capture Session ID

```python
session_id = None
async for message in query(prompt="Analyze auth module", options=options):
    if isinstance(message, ResultMessage):
        session_id = message.session_id
```

## Resume

```python
async for message in query(
    prompt="Now fix the issues you found",
    options=ClaudeAgentOptions(resume=session_id),
):
    ...
```

## Continue (Most Recent)

```python
options = ClaudeAgentOptions(continue_conversation=True)
```

## Fork

```python
options = ClaudeAgentOptions(resume=session_id, fork_session=True)
# Fork gets its own session_id; original unchanged
```

## Multi-Turn with ClaudeSDKClient

`ClaudeSDKClient` tracks session IDs internally:

```python
async with ClaudeSDKClient(options=ClaudeAgentOptions(...)) as client:
    await client.query("Analyze auth module")
    async for message in client.receive_response():
        print(message)

    await client.query("Now refactor it")  # Same session automatically
    async for message in client.receive_response():
        print(message)
```

## Streaming Output

Enable real-time text/tool deltas:

```python
from claude_agent_sdk.types import StreamEvent

options = ClaudeAgentOptions(include_partial_messages=True)

async for message in query(prompt="Explain databases", options=options):
    if isinstance(message, StreamEvent):
        event = message.event
        if event.get("type") == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta":
                print(delta.get("text", ""), end="", flush=True)
```

**Limitations:** StreamEvent not emitted with extended thinking (`max_thinking_tokens`). Structured output appears only in `ResultMessage.structured_output`.

## Storage

Files at `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`. The `<encoded-cwd>` replaces non-alphanumeric chars with `-`.

**Mismatched `cwd` = session not found.** Most common cause of "fresh session instead of resumed."

## Cross-Host Resume

Sessions are local. Two options:
1. Move the `.jsonl` file to the same path on the new host
2. Capture key results as application state, pass into a fresh session's prompt (more robust)

## Session Utilities

```python
from claude_agent_sdk import list_sessions, get_session_messages, get_session_info

sessions = await list_sessions(cwd="/path/to/project")
messages = await get_session_messages(session_id)
info = await get_session_info(session_id)
await rename_session(session_id, "auth-refactor")
await tag_session(session_id, "reviewed")
```
