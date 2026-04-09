# Agents & Subagents

## Entry Points

### `query()` — one-shot or resumable

```python
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

async for message in query(
    prompt="Fix the bug in auth.py",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Edit", "Bash"],
        permission_mode="acceptEdits",
    ),
):
    if isinstance(message, ResultMessage) and message.subtype == "success":
        print(message.result)
```

### `ClaudeSDKClient` — multi-turn, session-aware

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async with ClaudeSDKClient(options=ClaudeAgentOptions(...)) as client:
    await client.query("Analyze the auth module")
    async for message in client.receive_response():
        print(message)

    # Second call automatically continues the same session
    await client.query("Now refactor it to use JWT")
    async for message in client.receive_response():
        print(message)
```

Use `query()` for single tasks and CI. Use `ClaudeSDKClient` for multi-turn conversations.

## Agent Loop

A **turn** is one Claude response with tool calls + SDK executing those tools + feeding results back.

1. Claude receives prompt + system prompt + tool definitions + conversation history
2. Claude responds with text and/or `tool_use` blocks
3. SDK executes each tool, collects results
4. Results fed back as `UserMessage`
5. Repeat until Claude produces text-only response (no tool calls)

Context accumulates across turns. Repeated prefixes are prompt-cached. When context approaches limits, the SDK compacts (summarizes) older history.

### Cost tracking

```python
if isinstance(message, ResultMessage):
    if message.total_cost_usd is not None:  # Can be None on error paths
        print(f"Cost: ${message.total_cost_usd:.4f}")
    print(f"Turns: {message.num_turns}")
    print(f"Session: {message.session_id}")
```

## Subagents

Subagents isolate context, run in parallel, and apply specialized instructions. The main agent delegates via the `Agent` tool; only the subagent's final message returns.

```python
from claude_agent_sdk import AgentDefinition

options = ClaudeAgentOptions(
    allowed_tools=["Read", "Grep", "Glob", "Agent"],  # Agent tool required
    agents={
        "code-reviewer": AgentDefinition(
            description="Security and quality code reviewer.",
            prompt="You are a code review specialist...",
            tools=["Read", "Grep", "Glob"],
            model="sonnet",
        ),
        "test-runner": AgentDefinition(
            description="Runs and analyzes test suites.",
            prompt="You are a test execution specialist...",
            tools=["Bash", "Read", "Grep"],
        ),
    },
)
```

### AgentDefinition fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `description` | `str` | Yes | Claude uses this to decide when to invoke |
| `prompt` | `str` | Yes | System prompt for the subagent |
| `tools` | `list[str]` | No | Subset of available tools; omit = inherit all |
| `model` | `str` | No | `"sonnet"`, `"opus"`, `"haiku"`, `"inherit"` |
| `skills` | `list[str]` | No | Skill names to make available |
| `mcp_servers` | `list` | No | MCP servers by name or inline config |

### Subagent rules

- **Cannot spawn sub-subagents.** Don't include `Agent` in a subagent's `tools`.
- **Fresh context.** Subagents don't see the parent's conversation.
- **Inherit CLAUDE.md** (if `setting_sources` includes `"project"`), but NOT the parent's system prompt or skills (unless listed in `AgentDefinition.skills`).
- **Tool name was renamed** from `"Task"` to `"Agent"` in v2.1.63.

### What subagents inherit

| Receives | Does NOT receive |
|----------|-----------------|
| Own system prompt (`AgentDefinition.prompt`) | Parent's conversation history |
| Agent tool's prompt string | Parent's system prompt |
| Project CLAUDE.md (via `setting_sources`) | Skills (unless in `AgentDefinition.skills`) |
| Tool definitions (inherited or subset) | Tool results from parent's context |

The ONLY channel from parent → subagent is the Agent tool's prompt string. Include file paths, error messages, and decisions explicitly.

### Common tool combinations

| Use case | Tools |
|----------|-------|
| Read-only analysis | `Read`, `Grep`, `Glob` |
| Test execution | `Bash`, `Read`, `Grep` |
| Code modification | `Read`, `Edit`, `Write`, `Grep`, `Glob` |
| Full access | Omit `tools` field (inherits all) |

### Dynamic agent factory

```python
def create_reviewer(strictness: str) -> AgentDefinition:
    is_strict = strictness == "strict"
    return AgentDefinition(
        description="Security code reviewer",
        prompt=f"You are a {'strict' if is_strict else 'balanced'} security reviewer...",
        tools=["Read", "Grep", "Glob"],
        model="opus" if is_strict else "sonnet",
    )
```

### Detecting subagent invocation

```python
if hasattr(message, "content") and message.content:
    for block in message.content:
        if getattr(block, "type", None) == "tool_use" and block.name in ("Task", "Agent"):
            print(f"Subagent invoked: {block.input.get('subagent_type')}")

if hasattr(message, "parent_tool_use_id") and message.parent_tool_use_id:
    print("  (running inside subagent)")
```

### Resuming subagents

1. Capture `session_id` from the first query's `ResultMessage`
2. Extract `agentId` from message content (regex: `r"agentId:\s*([a-f0-9-]+)"`)
3. Resume: `options=ClaudeAgentOptions(resume=session_id)`
4. Reference in prompt: `f"Resume agent {agent_id} and ..."`

Subagent transcripts persist independently and survive main conversation compaction.
