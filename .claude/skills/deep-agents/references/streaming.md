# Streaming Reference

Requires LangGraph >= 1.1. Always pass `version="v2"` for the unified event format.

## stream() Signature

```python
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "..."}]},
    stream_mode="updates",          # or "messages", "custom", or a list
    subgraphs=True,                 # enable subagent event streaming
    version="v2",                   # REQUIRED for unified format
    config={"configurable": {"thread_id": "t1"}},  # optional
):
    ...
```

`stream_mode` options: `"updates"`, `"messages"`, `"custom"`, or a list combining them.

## Chunk Structure (v2)

Every chunk:

```python
{
    "type": str,       # "updates", "messages", or "custom"
    "ns": tuple,       # namespace — see below
    "data": ...,       # mode-specific payload
}
```

## Namespace Identification

| `chunk["ns"]` value | Source |
|---------------------|--------|
| `()` | Main agent |
| `("tools:abc123",)` | Subagent spawned via task() |
| `("tools:abc123", "model_request:def456")` | Model node inside that subagent |

Detect subagent events: `any(s.startswith("tools:") for s in chunk["ns"])`

## Data Payloads by Mode

### "updates" mode

```python
chunk["data"]  # dict: node_name → state updates

# Detect subagent spawn (main agent's model_request node):
for node_name, state in chunk["data"].items():
    for msg in state.get("messages", []):
        for tc in getattr(msg, "tool_calls", []):
            if tc["name"] == "task":
                print(f"Spawning subagent: {tc['args']}")

# Detect subagent completion (main agent's tools node):
for node_name, state in chunk["data"].items():
    for msg in state.get("messages", []):
        if getattr(msg, "type", None) == "tool":
            print(f"Subagent result: {msg.content}")
```

### "messages" mode

```python
token, metadata = chunk["data"]

# Streaming text token
token.content         # str — the token text
token.type            # "ai", "tool", etc.
token.tool_call_chunks  # partial tool call info
token.name            # tool name if type == "tool"
```

### "custom" mode

```python
chunk["data"]  # arbitrary dict emitted via get_stream_writer()
```

Emit custom events from inside a tool:

```python
from langgraph.config import get_stream_writer

def my_tool(task: str) -> str:
    """Do a long task with progress reporting."""
    writer = get_stream_writer()
    writer({"status": "starting", "progress": 0})
    # ... do work ...
    writer({"status": "done", "progress": 100})
    return result
```
