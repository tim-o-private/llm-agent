---
name: deep-agents
description: LangChain Deep Agents patterns for building production agents. Use when writing code that imports from `deepagents`, designing agent systems with pluggable filesystem backends, implementing middleware stacks, spawning subagents, streaming agent output, or integrating Deep Agents into Clarity's orchestration layer. Covers: create_deep_agent(), BackendProtocol, StoreBackend, middleware system, subagent spawning, streaming, human-in-the-loop, memory patterns, and sandbox backends.
---

# LangChain Deep Agents

Package: `deepagents` v0.5.0 (Beta, MIT, Python >=3.11)
Homepage: https://docs.langchain.com/oss/python/deepagents/overview
GitHub: https://github.com/langchain-ai/deepagents

```bash
pip install deepagents
uv add deepagents
```

Returns a compiled `CompiledStateGraph` (LangGraph) — all LangGraph primitives (`.stream()`, `.ainvoke()`, Studio, Platform) work on the result.

## Reference Pages

| Topic | File | When to read |
|-------|------|-------------|
| Backends & stores | [references/backends.md](references/backends.md) | BackendProtocol, StoreBackend, CompositeBackend, namespace factories, custom backends |
| Middleware | [references/middleware.md](references/middleware.md) | All built-in middleware classes, parameters, custom middleware |
| Subagents | [references/subagents.md](references/subagents.md) | SubAgent dict spec, CompiledSubAgent, task() tool, context propagation |
| Streaming | [references/streaming.md](references/streaming.md) | stream_mode options, event structure, subagent event namespacing |
| Sandboxes | [references/sandboxes.md](references/sandboxes.md) | Modal, Runloop, Daytona, AgentCore sandbox backends, file transfer |
| Memory & skills | [references/memory-skills.md](references/memory-skills.md) | Memory scoping, AGENTS.md, skills loading, SKILL.md format |

## Core API

### create_deep_agent()

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    name: str | None = None,
    model: str | BaseChatModel | None = None,       # default: "claude-sonnet-4-6"
    tools: Sequence[BaseTool | Callable | dict] | None = None,
    *,
    system_prompt: str | SystemMessage | None = None,
    backend: BackendProtocol | None = None,          # default: StateBackend()
    store: BaseStore | None = None,
    checkpointer: BaseCheckpointSaver | None = None, # REQUIRED for human-in-the-loop
    interrupt_on: dict | None = None,
    subagents: list[dict | CompiledSubAgent] | None = None,
    skills: list[str] | None = None,
    memory: list[str] | None = None,
    context_schema: type | None = None,
    response_format: type[BaseModel] | None = None,  # structured output
)
# Returns: CompiledStateGraph
```

Model format: `"provider:model"` string or `BaseChatModel` instance.
Supported providers: Anthropic, OpenAI, Google, Azure, AWS Bedrock, OpenRouter, Fireworks, Baseten, Ollama.

### Invocation

```python
# Single-turn
result = agent.invoke({"messages": [{"role": "user", "content": "..."}]})

# With thread (required for checkpointing, human-in-the-loop)
result = agent.invoke(
    {"messages": [{"role": "user", "content": "..."}]},
    config={"configurable": {"thread_id": "some-id"}},
)

# Async
result = await agent.ainvoke(...)

# Structured output result key
result["structured_response"]  # when response_format= is set
```

## Built-in Tools

These are injected automatically based on middleware:

| Tool | Middleware | Description |
|------|-----------|-------------|
| `write_todos` | `TodoListMiddleware` | Task planning/decomposition |
| `ls` | `FilesystemMiddleware` | List directory contents |
| `read_file` | `FilesystemMiddleware` | Read file with offset+limit |
| `write_file` | `FilesystemMiddleware` | Write/create file |
| `edit_file` | `FilesystemMiddleware` | String-replace edit |
| `glob` | `FilesystemMiddleware` | Pattern-based file search |
| `grep` | `FilesystemMiddleware` | Regex content search |
| `execute` | Sandbox backends only | Run shell commands |
| `task` | `SubAgentMiddleware` | Spawn subagent |

## Minimal Example

```python
from deepagents import create_deep_agent

def get_weather(city: str) -> str:
    """Return current weather for a city."""
    return f"Sunny, 72°F in {city}"

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    tools=[get_weather],
    system_prompt="You are a helpful assistant.",
)

result = agent.invoke({"messages": [{"role": "user", "content": "Weather in NYC?"}]})
```

## Tool Registration

Any Python callable with type hints and a docstring works. LangChain `BaseTool` and `@tool`-decorated functions also accepted.

```python
from langchain.tools import tool

@tool
def search(query: str) -> str:
    """Search the web for information."""
    return search_api(query)

agent = create_deep_agent(tools=[search, my_plain_callable])
```

## Streaming

```python
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "..."}]},
    stream_mode=["updates", "messages", "custom"],
    subgraphs=True,
    version="v2",
):
    # chunk["type"] is "updates", "messages", or "custom"
    # chunk["ns"] is () for main agent, ("tools:<id>",) for subagent
    ...
```

See [references/streaming.md](references/streaming.md) for event structure details.

## Human-in-the-Loop

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

agent = create_deep_agent(
    tools=[sensitive_tool],
    checkpointer=MemorySaver(),           # REQUIRED
    interrupt_on={"sensitive_tool": True},
)

thread = {"configurable": {"thread_id": "t1"}}
result = agent.invoke(input, config=thread, version="v2")

# result.interrupts[0].value contains action_requests and review_configs
# Resume:
agent.invoke(Command(resume={"decisions": ["approve"]}), config=thread, version="v2")
```

`interrupt_on` values: `True`, `False`, or `{"allowed_decisions": ["approve", "edit", "reject"]}`.

## Standards

### Always do

1. **Set a `thread_id`** whenever using `checkpointer` or needing human-in-the-loop.
2. **Use `StoreBackend` with namespace factories** for multi-tenant deployments — never `StateBackend` in production serving multiple users.
3. **Pass `checkpointer=MemorySaver()` (or persistent saver)** when using `interrupt_on`.
4. **Provide type hints and docstrings** on all tool callables — the agent uses them to understand the tool.
5. **Use `backend.upload_files()` before invoking** when seeding a sandbox with source code or data.
6. **Read `version="v2"`** when streaming — required for unified event format.

### Never do

1. **Don't use `StateBackend` for multi-user** — files are not isolated between threads.
2. **Don't put secrets in sandbox environments** — they can be read/exfiltrated via context injection.
3. **Don't skip `checkpointer` with `interrupt_on`** — human-in-the-loop silently fails without it.
4. **Don't expect subagents to inherit** the parent's `tools`, `middleware`, or `skills` — they must be specified explicitly.
5. **Don't use the deprecated `runtime` constructor arg** on `StateBackend`/`StoreBackend`.

## Vs. Claude Agent SDK

Deep Agents adds on top of LangGraph: virtual filesystem with pluggable backends, composable middleware, long-term memory via Store, and sandbox-as-tool pattern. Use Deep Agents when you need multi-backend filesystems, middleware composition, or model-agnostic support. Use Claude Agent SDK when tight Claude Code integration (hooks, permissions, CLAUDE.md) is the priority. See the [comparison page](https://docs.langchain.com/oss/python/deepagents/comparison).
