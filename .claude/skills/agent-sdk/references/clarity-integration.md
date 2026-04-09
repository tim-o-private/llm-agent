# Clarity Integration

How Clarity (llm-agent) integrates with the Agent SDK for PRD-003.

## Architecture Fit

Clarity currently uses LangChain AgentExecutor. PRD-003 replaces this with the Agent SDK for orchestration-layer workflows where Clarity is the "brain" and Claude Code is the "hands."

The SDK gives Clarity:
- **Built-in tools** (Read, Edit, Bash, Grep, Glob) without implementing tool execution
- **Subagents** for parallel task decomposition
- **Sessions** for multi-turn workflows
- **Hooks** for audit, safety rails, and integration with existing services

## Capability Gateway Mapping

Clarity's planned Capability Gateway maps to the SDK's permission + hook system:

| Clarity concept | Agent SDK equivalent |
|----------------|---------------------|
| Capability Gateway | `allowed_tools` + `disallowed_tools` + hooks |
| Trust tiers (Inform/Recommend/Act) | `permission_mode` + `can_use_tool` callback |
| Tool approval defaults | `allowed_tools` list |
| Sandbox boundary | `PreToolUse` hooks + `disallowed_tools` |

## Exposing Clarity Services as SDK Tools

Clarity's existing services become SDK custom tools:

```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool(
    "search_memories",
    "Search the user's stored memories and notes",
    {"query": str, "limit": int},
)
async def search_memories(args: dict) -> dict:
    results = await memory_service.search(
        user_id=current_user_id,
        query=args["query"],
        limit=args.get("limit", 10),
    )
    return {"content": [{"type": "text", "text": format_results(results)}]}

clarity_tools = create_sdk_mcp_server(
    name="clarity",
    version="1.0.0",
    tools=[search_memories, create_reminder, list_tasks, ...],
)
```

## Session Integration with chat_sessions

Store Agent SDK session IDs in Clarity's DB for resume:

```python
# After query completes
if isinstance(message, ResultMessage):
    await chat_session_service.update(
        session_id=clarity_session_id,
        agent_sdk_session_id=message.session_id,
    )

# On next user message
sdk_session_id = await chat_session_service.get_sdk_session_id(clarity_session_id)
if sdk_session_id:
    options = ClaudeAgentOptions(resume=sdk_session_id)
```

## Hook Integration with Notification Service

```python
async def clarity_notification_hook(input_data, tool_use_id, context):
    await notification_service.create(
        user_id=current_user_id,
        type="agent_status",
        message=input_data.get("message", ""),
        channel="web",
    )
    return {}

options = ClaudeAgentOptions(
    hooks={"Notification": [HookMatcher(hooks=[clarity_notification_hook])]}
)
```

## Subagent Mapping for Orchestration

PRD-003 envisions Clarity orchestrating specialized agents:

```python
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Edit", "Bash", "Grep", "Glob", "Agent"],
    agents={
        "code-writer": AgentDefinition(
            description="Writes and modifies code files.",
            prompt="You are a code implementation specialist...",
            tools=["Read", "Edit", "Write", "Grep", "Glob"],
        ),
        "test-runner": AgentDefinition(
            description="Runs tests and analyzes failures.",
            prompt="You are a test execution specialist...",
            tools=["Bash", "Read", "Grep"],
            model="sonnet",
        ),
        "reviewer": AgentDefinition(
            description="Reviews code changes for quality and security.",
            prompt="You are a code review specialist...",
            tools=["Read", "Grep", "Glob"],
            model="sonnet",
        ),
    },
    mcp_servers={"clarity": clarity_tools},
    max_turns=50,
    max_budget_usd=5.00,
)
```

## Hosting Pattern

Clarity's chatServer runs on Fly.io. Agent SDK sessions would run as:
- **Hybrid pattern** — ephemeral containers hydrated from Clarity's chat_sessions, spinning down after idle timeout
- Session files persisted to Supabase Storage (MVP) or volume mounts
- `max_budget_usd` enforced per-user to prevent runaway costs
