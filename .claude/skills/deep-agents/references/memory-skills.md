# Memory and Skills Reference

## Skills

Skills are SKILL.md files loaded into the agent's context at startup. They extend the agent with domain knowledge and procedures.

### Loading Skills

```python
agent = create_deep_agent(
    skills=["/skills/", "/skills/research/my-skill"],  # paths relative to backend root
    backend=CompositeBackend(...),
)
```

- Path ending with `/` loads all SKILL.md files found under that directory
- `last source wins` precedence when multiple skills define the same name
- Subagents do NOT inherit parent's `skills` — specify explicitly

### SKILL.md Frontmatter Fields

```yaml
---
name: my-skill                 # required
description: "..."             # required, capped at 1024 characters
license: MIT                   # optional
compatibility: ">=0.5.0"       # optional
metadata:
  author: "..."                # optional
  version: "1.0.0"             # optional
allowed-tools:                 # optional — restrict which tools skill can use
  - read_file
  - write_file
---
```

Size constraint: SKILL.md files must be under 10 MB.

### Seeding Skills via StoreBackend

```python
from langchain_sdk import get_client
from deepagents.backends.utils import create_file_data

client = get_client()
await client.store.put_item(
    (org_id,),
    "/skills/research-skill/SKILL.md",
    create_file_data("---\nname: research\ndescription: ...\n---\n# Research\n..."),
)
```

## Memory (AGENTS.md)

`AGENTS.md` is the persistent memory file — the agent reads it at the start of each thread and writes to it to accumulate learnings across sessions.

```python
agent = create_deep_agent(
    memory=["/memories/AGENTS.md"],       # path(s) within backend
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            "/memories/": StoreBackend(
                namespace=lambda ctx: (ctx.runtime.context.user_id,),
                store=store,
            ),
        },
    ),
    store=store,
)
```

## Scoping Patterns

| Scope | Namespace | Contents |
|-------|-----------|----------|
| Agent-scoped | `(assistant_id,)` | Shared across all users of this agent |
| User-scoped | `(user_id,)` | Isolated per user |
| Org-scoped | `(org_id,)` | Policies applied across organization |

`ctx.runtime.server_info.assistant_id` requires deepagents>=0.5.0.

## Full Memory + Skills Example

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    system_prompt="You are a helpful assistant. Use AGENTS.md to remember things across sessions.",
    memory=["/memories/AGENTS.md"],
    skills=["/skills/"],
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            "/memories/": StoreBackend(
                namespace=lambda ctx: (ctx.runtime.context.user_id,),
                store=store,
            ),
            "/policies/": StoreBackend(
                namespace=lambda ctx: (ctx.runtime.context.org_id,),
                store=store,
            ),
        },
    ),
    store=store,
)
```

## Scheduled Memory Consolidation

Use LangGraph Platform crons to run memory consolidation periodically:

```python
from langgraph_sdk import get_client

client = get_client()
await client.crons.create(
    assistant_id="consolidation_agent",
    schedule="0 */6 * * *",  # every 6 hours
    input={"messages": [{"role": "user", "content": "Consolidate and organize memory."}]},
)
```

## Structured Output

```python
from pydantic import BaseModel

class Report(BaseModel):
    summary: str
    action_items: list[str]

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    response_format=Report,
)

result = agent.invoke({"messages": [...]})
report: Report = result["structured_response"]
```
