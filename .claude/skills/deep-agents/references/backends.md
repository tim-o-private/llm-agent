# Backends Reference

## Import Paths

```python
from deepagents.backends import (
    StateBackend,
    FilesystemBackend,
    LocalShellBackend,
    StoreBackend,
    CompositeBackend,
)
from deepagents.backends.protocol import (
    BackendProtocol,
    WriteResult,
    EditResult,
    LsResult,
    ReadResult,
    GrepResult,
    GlobResult,
)
from deepagents.backends.utils import create_file_data
```

## BackendProtocol — Required Methods

Implement all six methods to create a custom backend:

```python
class MyBackend:
    def ls(self, path: str) -> LsResult: ...
    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult: ...
    def grep(self, pattern: str, path: str | None = None, glob: str | None = None) -> GrepResult: ...
    def glob(self, pattern: str, path: str = "/") -> GlobResult: ...
    def write(self, file_path: str, content: str) -> WriteResult: ...
    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult: ...
```

Supporting types:
- `FileInfo(path, is_dir, size, modified_at)`
- `GrepMatch(path, line, text)`
- `FileData(content, encoding, created_at, modified_at)`

## Built-in Backends

| Backend | Persistence | Isolation | Use Case |
|---------|-------------|-----------|----------|
| `StateBackend()` | Single thread only | None | Dev/testing |
| `FilesystemBackend(root_dir, virtual_mode=False)` | Local disk | None | Direct filesystem access (dev only) |
| `LocalShellBackend(root_dir, env, timeout=120, max_output_bytes=100000)` | Local disk | None | Code execution dev |
| `StoreBackend(namespace, store=None)` | Cross-thread via LangGraph Store | Per namespace | Multi-user production |
| `CompositeBackend(default, routes)` | Mixed | Per route | Flexible path-based routing |

### Sandbox Backends (isolated execution)

| Backend | Package | Notes |
|---------|---------|-------|
| `ModalSandbox` | `langchain-modal` | ML/GPU workloads |
| `RunloopSandbox` | `langchain-runloop` | Disposable devboxes |
| `DaytonaSandbox` | `langchain-daytona` | Fast cold starts |
| `AgentCoreSandbox` | `langchain-agentcore-codeinterpreter` | AWS MicroVM isolation |

## StoreBackend — Namespace Factories

`namespace` is a `Callable[[BackendContext], tuple[str, ...]]`.

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

# Per-user isolation
StoreBackend(
    namespace=lambda ctx: (ctx.runtime.context.user_id,),
    store=store,
)

# Per-assistant (shared across all users of that assistant)
StoreBackend(
    namespace=lambda ctx: (ctx.runtime.server_info.assistant_id,),  # requires deepagents>=0.5.0
    store=store,
)

# Per-thread
StoreBackend(
    namespace=lambda ctx: (ctx.runtime.execution_info.thread_id,),
    store=store,
)

# Per-org
StoreBackend(
    namespace=lambda ctx: (ctx.runtime.context.org_id,),
    store=store,
)
```

## CompositeBackend — Path Routing

Routes specific path prefixes to different backends; everything else goes to `default`.

```python
backend = CompositeBackend(
    default=StateBackend(),
    routes={
        "/memories/": StoreBackend(namespace=lambda ctx: (ctx.runtime.context.user_id,), store=store),
        "/policies/": StoreBackend(namespace=lambda ctx: (ctx.runtime.context.org_id,), store=store),
    },
)
```

## FilesystemBackend

```python
FilesystemBackend(
    root_dir=".",          # absolute or relative path
    virtual_mode=False,    # if True, reads from disk but writes stay in memory
)
```

Warning: gives the agent direct access to the host filesystem. Use only in dev/sandboxed environments.

## Deprecated APIs

Do NOT use:
- Factory functions passed to `backend=` parameter
- `runtime` constructor argument on `StateBackend` or `StoreBackend`
- `files_update` field on result objects (now handled internally)
- `Command` wrapping in middleware responses
