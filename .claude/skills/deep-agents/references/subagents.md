# Subagents Reference

## Overview

Subagents run in isolated context windows — they do NOT inherit the parent's tools, middleware, system_prompt, or skills. Everything must be specified explicitly.

The main agent spawns a subagent via the built-in `task` tool: `task(name="subagent-name", task="description of what to do")`.

## Imports

```python
from deepagents import create_deep_agent, CompiledSubAgent
```

## Dictionary-Based Subagent

```python
research_subagent = {
    "name": "research-agent",           # REQUIRED — used to call via task()
    "description": "Conducts in-depth research using web search",  # REQUIRED
    "system_prompt": "You are a thorough researcher...",           # REQUIRED
    "tools": [internet_search, summarize],                         # REQUIRED
    "model": "openai:gpt-5.2",          # optional — overrides parent model
    "middleware": [ToolRetryMiddleware(max_retries=3)],            # optional — does NOT inherit
    "interrupt_on": {"internet_search": True},                     # optional — overrides parent
    "skills": ["/skills/research/"],                               # optional — does NOT inherit
}

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    tools=[some_tool],
    subagents=[research_subagent],
)
```

## CompiledSubAgent (for custom LangGraph graphs)

```python
from deepagents import CompiledSubAgent

custom_subagent = CompiledSubAgent(
    name="data-analyzer",
    description="Specialized agent for complex data analysis",
    runnable=custom_graph,  # must be a compiled LangGraph graph (.compile() already called)
)

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    subagents=[custom_subagent],
)
```

## Context Propagation

Runtime context flows to subagents automatically when using `ainvoke` with a `context` parameter:

```python
result = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "..."}]},
    context={"user_id": user_id, "org_id": org_id},
)
```

## Default Subagent

Without specifying `subagents`, `create_deep_agent` includes a default general-purpose subagent that can be used for context isolation.

## Subagent Isolation Rules

| Property | Inherited? |
|----------|-----------|
| `tools` | No — must specify |
| `middleware` | No — must specify |
| `system_prompt` | No — must specify |
| `skills` | No — must specify |
| `model` | No — inherits parent model string by default if `model` not set on subagent dict |
| runtime context | Yes — propagated automatically |
| `interrupt_on` | Subagent's setting overrides parent's |
