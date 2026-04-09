# Sandboxes Reference

Sandboxes implement `SandboxBackendProtocol` (extends `BackendProtocol`) and additionally provide an `execute` tool for arbitrary shell commands. The `BaseSandbox` class builds all filesystem operations on top of a single `execute()` method.

## Installation

```bash
pip install langchain-modal         # Modal
pip install langchain-runloop       # Runloop
pip install langchain-daytona       # Daytona
pip install langchain-agentcore-codeinterpreter  # AgentCore (AWS)
```

## Providers

| Provider | Package | Strength | Notes |
|----------|---------|----------|-------|
| Modal | `langchain-modal` | ML/GPU workloads | App must exist first |
| Runloop | `langchain-runloop` | Disposable devboxes | Simple SDK |
| Daytona | `langchain-daytona` | Fast cold starts, snapshots | Thread-scoped TTL pattern |
| AgentCore | `langchain-agentcore-codeinterpreter` | AWS MicroVM isolation | Python/Code Interpreter |

## Provider Examples

### Modal

```python
import modal
from langchain_modal import ModalSandbox

app = modal.App.lookup("your-app")
modal_sandbox = modal.Sandbox.create(app=app)
backend = ModalSandbox(sandbox=modal_sandbox)

result = backend.execute("echo hello")
modal_sandbox.terminate()
```

### Runloop

```python
from runloop_api_client import RunloopSDK
from langchain_runloop import RunloopSandbox

client = RunloopSDK(bearer_token="API_KEY")
devbox = client.devbox.create()
backend = RunloopSandbox(devbox=devbox)

result = backend.execute("python --version")
devbox.shutdown()
```

### Daytona

```python
from daytona import Daytona
from langchain_daytona import DaytonaSandbox

sandbox = Daytona().create()
backend = DaytonaSandbox(sandbox=sandbox)

result = backend.execute("python --version")
sandbox.stop()
```

### AgentCore

```python
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
from langchain_agentcore_codeinterpreter import AgentCoreSandbox

interpreter = CodeInterpreter(region="us-west-2")
interpreter.start()
backend = AgentCoreSandbox(interpreter=interpreter)

result = backend.execute("python3 --version")
interpreter.stop()
```

## Execute Result

```python
result = backend.execute("command_string")
result.output       # str — stdout/stderr
result.exit_code    # int
# Large outputs are auto-truncated with a notice to the agent
```

## File Transfer

```python
# Upload files to sandbox before agent runs
backend.upload_files([
    ("path/in/sandbox/file.py", b"file_contents"),
    ("data.csv", b"name,value\na,1\n"),
])

# Download artifacts after agent finishes
results = backend.download_files(["output.txt", "/src/index.py"])
for result in results:
    if result.content is not None:
        print(f"{result.path}: {result.content.decode()}")
    else:
        print(f"Failed: {result.error}")
```

## Lifecycle Scoping Patterns

### Thread-scoped (default)
Each thread gets its own sandbox, created on first run, reused on follow-up turns, destroyed when thread ends or TTL expires.

### Assistant-scoped
All threads share one sandbox. Files/packages persist across conversations. Requires TTL or manual cleanup.

### Thread-scoped with TTL (Daytona example)

```python
from langchain_core.utils.uuid import uuid7
from daytona import CreateSandboxFromSnapshotParams, Daytona

client = Daytona()
thread_id = str(uuid7())

try:
    sandbox = client.find_one(labels={"thread_id": thread_id})
except Exception:
    params = CreateSandboxFromSnapshotParams(
        labels={"thread_id": thread_id},
        auto_delete_interval=3600,  # TTL in seconds
    )
    sandbox = client.create(params)

backend = DaytonaSandbox(sandbox=sandbox)
```

## Deployment Patterns

### Pattern 1: Sandbox as Tool (Recommended)
Agent runs on host/server, calls sandbox tools via provider APIs. Benefits: instant agent code updates, API keys stay external, sandbox failures don't affect agent state, pay per execution time only.

### Pattern 2: Agent in Sandbox
Agent runs inside sandbox. Requires deepagents-cli in Docker image, network infrastructure. Trade-off: API keys inside sandbox (security risk).

```dockerfile
FROM python:3.11
RUN pip install deepagents-cli
```

## Security

- Never put secrets inside a sandbox — they can be read/exfiltrated via context injection attacks
- Sandboxes isolate from host but don't protect against prompt injection
- Block sandbox network access when not needed
- Use `PIIMiddleware` to redact sensitive patterns in tool outputs
- Enable human-in-the-loop for sensitive sandbox operations if secrets must be injected
