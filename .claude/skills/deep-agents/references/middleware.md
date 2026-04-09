# Middleware Reference

## Built-in Middleware (auto-configured by create_deep_agent)

| Middleware | Auto | Purpose |
|-----------|------|---------|
| `TodoListMiddleware` | Yes | Injects `write_todos` tool + planning system prompt |
| `FilesystemMiddleware` | Yes | Injects `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep` |
| `SubAgentMiddleware` | Yes | Injects `task` tool for spawning subagents |
| `SummarizationMiddleware` | Yes | Compresses history when approaching token limits |
| `AnthropicPromptCachingMiddleware` | Yes (Anthropic only) | Token optimization via prompt caching |
| `PatchToolCallsMiddleware` | Yes | Auto-repairs malformed tool call JSON |
| `MemoryMiddleware` | When `memory=` set | Cross-session memory via AGENTS.md |
| `SkillsMiddleware` | When `skills=` set | Loads SKILL.md files into context |

## LangChain Provider-Agnostic Middleware

All importable from `langchain.agents.middleware`:

```python
from langchain.agents.middleware import (
    SummarizationMiddleware,
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
    ToolCallLimitMiddleware,
    ModelFallbackMiddleware,
    PIIMiddleware,
    TodoListMiddleware,
    LLMToolSelectorMiddleware,
    ToolRetryMiddleware,
    ModelRetryMiddleware,
    LLMToolEmulator,
    ContextEditingMiddleware,
    ClearToolUsesEdit,
    ShellToolMiddleware,
    HostExecutionPolicy,
    FilesystemFileSearchMiddleware,
)
```

### Deep Agents-specific middleware

```python
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.subagents import SubAgentMiddleware
```

## Key Middleware Parameters

### SummarizationMiddleware

```python
SummarizationMiddleware(
    model="provider:model",          # or BaseChatModel
    trigger=ContextSize(...),        # token/message/fraction threshold
    keep=ContextSize(...),           # how much to preserve
    token_counter=None,              # custom counting function
    summary_prompt="...",            # custom prompt template
    trim_tokens_to_summarize=4000,   # default
)
```

### HumanInTheLoopMiddleware

```python
HumanInTheLoopMiddleware(
    interrupt_on={
        "tool_name": True,
        "other_tool": {"allowed_decisions": ["approve", "reject"]},
    }
)
# Requires checkpointer on the agent
```

### ModelCallLimitMiddleware

```python
ModelCallLimitMiddleware(
    thread_limit=100,   # max calls across all runs in thread
    run_limit=20,       # max calls per single invocation
    exit_behavior="end",  # "end" or "error"
)
```

### ToolCallLimitMiddleware

```python
ToolCallLimitMiddleware(
    tool_name="write_file",   # omit for global limit
    thread_limit=50,
    run_limit=10,
    exit_behavior="continue",  # "continue", "error", or "end"
)
```

### ModelFallbackMiddleware

```python
ModelFallbackMiddleware(
    first_model="openai:gpt-4o",
    "anthropic:claude-sonnet-4-6",   # sequential fallback chain
    "google:gemini-2.0-flash",
)
```

### PIIMiddleware

```python
PIIMiddleware(
    pii_type="email",                  # built-in: email, credit_card, ip, mac_address, url
    strategy="redact",                 # "block", "redact", "mask", "hash"
    detector=my_regex_or_function,     # custom: regex or fn returning [{text, start, end}]
    apply_to_input=True,
    apply_to_output=True,
    apply_to_tool_results=True,
)
```

### ToolRetryMiddleware

```python
ToolRetryMiddleware(
    max_retries=2,
    tools=["flaky_tool"],              # None = all tools
    retry_on=(NetworkError,),          # exception types or callable
    on_failure="return_message",       # "return_message" or "raise"
    backoff_factor=2.0,
    initial_delay=1.0,
    max_delay=60.0,
    jitter=True,
)
```

### LLMToolSelectorMiddleware

Reduces tool list shown to model before each call — useful when tool count is high:

```python
LLMToolSelectorMiddleware(
    model="anthropic:claude-haiku-3-5",
    system_prompt="...",
    max_tools=10,
    always_include=["write_todos", "task"],
)
```

### ContextEditingMiddleware

```python
ContextEditingMiddleware(
    edits=[
        ClearToolUsesEdit(
            trigger=100000,            # token threshold
            keep=3,                    # recent results preserved
            clear_at_least=0,
            clear_tool_inputs=False,
            exclude_tools=["read_file"],
            placeholder="[cleared]",
        )
    ],
    token_count_method="approximate",  # or "model"
)
```

### ShellToolMiddleware

```python
ShellToolMiddleware(
    workspace_root="/workspace",
    startup_commands=["pip install -r requirements.txt"],
    shutdown_commands=[],
    execution_policy=HostExecutionPolicy(),  # or DockerExecutionPolicy, CodexSandboxExecutionPolicy
    redaction_rules=[],
    shell_command=["bash"],
    env={"MY_VAR": "value"},
)
```

### FilesystemFileSearchMiddleware

```python
FilesystemFileSearchMiddleware(
    root_path="/workspace",
    use_ripgrep=True,
    max_file_size_mb=10,
)
# Injects: glob_search, grep_search tools
```
