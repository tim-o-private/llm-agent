# SPEC-036: Workflow Engine — LangGraph-Based Graph Execution for chatServer

> **Status:** Draft
> **Author:** Claude (Spec Writer)
> **Created:** 2026-04-06
> **Updated:** 2026-04-06
> **PRD:** Architecture Proposal (Phase 2, Item 7)
> **Architecture:** `docs/product/ARCHITECTURE-PROPOSAL-next-gen.md`, Sections Q4, Q7

## Goal

Port HQ's LangGraph-based graph engine to chatServer for server-side multi-tenant workflow execution. The engine reads Markdown graph templates (same format as HQ), builds LangGraph `StateGraph` instances, and executes them via an `AnthropicEngine` that makes Anthropic Messages API calls (not `claude -p` subprocesses). State is checkpointed to Postgres per workflow run per user. The conversational agent dispatches workflows via the `dispatch_workflow` tool (stubbed in SPEC-033 AC-28), and running workflows stream progress back to the active chat session.

This is the infrastructure that powers SPEC-037's initial workflows (email triage, morning briefing, draft reply). The engine is generic — it doesn't know about email or calendars. It knows about templates, steps, engines, and gates.

## Background

HQ's orchestrator already implements the full graph lifecycle:
- **Template parser** (`registry.py`): Markdown with YAML frontmatter → `GraphTemplate`
- **Graph builder** (`builder.py`): Template + services → compiled `StateGraph`
- **Node factories** (`factory.py`): Closures for work, review, human-gate, complete nodes
- **Checkpointer** (`checkpointer.py`): Postgres-backed `AsyncPostgresSaver`
- **Human gates** (`human_gate.py`): LangGraph `interrupt_before` for approval flows
- **Execution engine** (`runner.py`): `ExecutionEngine` protocol, `ClaudePEngine` for `claude -p`

HQ is single-user (Tim), filesystem-local, and runs via `claude -p`. Clarity is multi-tenant, server-side, and runs via the Anthropic Messages API. The graph template format and builder logic port directly; the execution engine and state scoping change.

### Relationship to Other Specs

| Spec | Relationship |
|------|-------------|
| **SPEC-033** (Conversation Handler) | Defines the `dispatch_workflow` stub (AC-28–30). This spec implements the real dispatch. The ConversationHandler calls `dispatch_workflow` → engine starts a graph → progress streams back to the chat SSE connection. |
| **SPEC-034** (Capability Gateway) | Workflow steps that need tools call them through the gateway. The `AnthropicEngine` receives tool definitions from `gateway.get_tool_schemas()` and routes tool calls through `gateway.execute()`. |
| **SPEC-035** (Config Service) | Workflow templates are stored in Supabase Storage via the ConfigService overlay (`system/workflows/` + `users/{id}/workflows/`). |
| **SPEC-037** (Initial Workflows) | Defines the first three workflow templates that run on this engine. |

## Dependencies

| Dependency | What It Provides | Status |
|-----------|-----------------|--------|
| SPEC-033 (Conversation Handler) | `dispatch_workflow` stub, SSE streaming endpoint, Anthropic Messages API tool-loop | Draft |
| SPEC-034 (Capability Gateway) | `gateway.execute()`, `gateway.get_tool_schemas()`, trust tier enforcement | Draft |
| SPEC-035 (Config Service) | `config_service.read()` for loading templates from Supabase Storage | Draft |
| `langgraph` 1.1.6 | `StateGraph`, `interrupt()`, conditional edges | Add to requirements |
| `langgraph-checkpoint-postgres` | `AsyncPostgresSaver` for Postgres checkpointing | Add to requirements |
| `psycopg-pool` | `AsyncConnectionPool` for checkpointer connection management | Add to requirements |
| Existing `NotificationService` (SPEC-025) | Routing notifications to web + Telegram for human gates | Complete |
| Existing `PendingActionsService` | Queuing actions for user approval | Complete |
| Existing `jobs` table (SPEC-026) | Scheduling workflow runs via `JobService` | Complete |

## Acceptance Criteria

### FU-1: Template Parser + Registry

- [ ] **AC-01:** A `GraphTemplate` dataclass in `chatServer/workflows/models.py` represents a parsed graph template with fields: `name` (str), `description` (str), `version` (int), `parameters` (list of `ParameterDef`), `steps` (list of `StepDef`), and `default_gate_policy` (str). [A1]
- [ ] **AC-02:** A `StepDef` dataclass has fields: `name` (str), `agent` (str — maps to a prompt template, not a separate LLM agent), `depends_on` (list[str]), `description` (str), `tools` (list[str] — tool names available to this step), `gate` (str | None — name of gate definition), `gate_policy` (str — "none", "escalation-only", "human-required"), `input_schema` (dict | None), `output_schema` (dict | None). [A1]
- [ ] **AC-03:** A `TemplateParser` in `chatServer/workflows/template_parser.py` reads a Markdown file with YAML frontmatter and returns a `GraphTemplate`. The format matches HQ's graph templates: YAML frontmatter for metadata, `## Parameters` table, `### step-N: Name` sections with `- **key:** value` fields. Malformed templates produce clear `TemplateParseError` exceptions with the template name and line context. [A1]
- [ ] **AC-04:** A `TemplateRegistry` in `chatServer/workflows/registry.py` loads templates from the ConfigService overlay. System templates live at `workflows/{name}.md`; user templates at `workflows/{name}.md` in the user layer. User templates shadow system templates of the same name. The registry caches parsed templates with a 300s TTL (config changes are rare). [A1, A2]
- [ ] **AC-05:** `TemplateRegistry.list_templates(user_id)` returns available template names (merged system + user). `TemplateRegistry.get_template(name, user_id)` returns a `GraphTemplate` or raises `TemplateNotFoundError`. [A1]

### FU-2: AnthropicEngine + Graph Builder

- [ ] **AC-06:** An `AnthropicEngine` class in `chatServer/workflows/engine.py` implements a `run()` method with signature: `async def run(self, prompt: str, tools: list[dict], system_prompt: str | None = None) -> EngineResult`. It makes a single Anthropic Messages API call (tool-loop, same pattern as SPEC-033's ConversationHandler) and returns `EngineResult(output: str, tool_calls: list[ToolCallRecord], token_usage: TokenUsage)`. [A14]
- [ ] **AC-07:** The `AnthropicEngine` is user-scoped: constructed with `user_id`, `gateway` (CapabilityGateway from SPEC-034), and `anthropic_client`. Tool definitions come from `gateway.get_tool_schemas(user_id)` filtered to only the tools listed in the step's `tools` field. Tool calls are dispatched via `gateway.execute(user_id, tool_name, params)`. [A12]
- [ ] **AC-08:** The `AnthropicEngine` respects per-step model configuration: `model` (default `claude-sonnet-4-5-20250514`), `max_tokens` (default 4096), `temperature` (default 0.5). Steps that do classification or triage use a cheaper model; steps that generate content use a more capable one. Model override is per-step in the template's step definition. [A14]
- [ ] **AC-09:** A `GraphBuilder` in `chatServer/workflows/builder.py` takes a `GraphTemplate` + `AnthropicEngine` + `NotificationService` and produces a `CompiledStateGraph`. Each step becomes a node. `depends_on` determines edges. Steps with `gate_policy: "human-required"` have `interrupt_before` set, pausing execution until user approval. [A1]
- [ ] **AC-10:** The `GraphBuilder` creates a LangGraph `StateGraph` with a shared `WorkflowState` TypedDict: `messages` (list — conversation history per step), `step_outputs` (dict[str, str] — accumulated results keyed by step name), `parameters` (dict — user-provided inputs), `current_step` (str), `status` (str — "running", "waiting_for_approval", "completed", "failed", "cancelled"). [A1]
- [ ] **AC-11:** Each step node is a closure that: (1) assembles a prompt from the step's `description` + prior step outputs from `state["step_outputs"]` + the step's input schema, (2) calls `engine.run()` with the prompt and step-scoped tools, (3) writes the result to `state["step_outputs"][step_name]`, (4) updates `state["current_step"]`. [A1]

### FU-3: Postgres Checkpointer + Workflow Run Manager

- [ ] **AC-12:** A `WorkflowCheckpointer` in `chatServer/workflows/checkpointer.py` wraps `AsyncPostgresSaver` from `langgraph-checkpoint-postgres`. It manages a `psycopg` `AsyncConnectionPool` scoped to the chatServer's existing Postgres connection (reusing `SUPABASE_DB_*` env vars). Pool lifecycle is managed in `main.py` lifespan (opened on startup, closed on shutdown). [A3]
- [ ] **AC-13:** Checkpoint table names are prefixed with `workflow_` to avoid collision with other LangGraph users. The checkpointer's `setup()` is called on startup to create/migrate tables if they don't exist. [A3]
- [ ] **AC-14:** A `WorkflowRunManager` in `chatServer/workflows/run_manager.py` provides: `start_run(user_id, template_name, parameters) -> run_id`, `get_run_status(run_id) -> WorkflowRunStatus`, `cancel_run(run_id)`, `list_runs(user_id, status_filter?) -> list[WorkflowRunStatus]`. [A1]
- [ ] **AC-15:** `start_run()` validates the template exists, validates required parameters are provided, creates a unique `thread_id` (UUID), compiles the graph with the checkpointer and interrupt points, and launches execution as a background `asyncio.Task`. Returns the `run_id` immediately (non-blocking). [A1, A14]
- [ ] **AC-16:** A `workflow_runs` table tracks run metadata: `id` (UUID PK), `user_id` (UUID FK), `template_name` (TEXT), `thread_id` (TEXT — LangGraph thread_id), `status` (TEXT — pending/running/waiting_for_approval/completed/failed/cancelled), `parameters` (JSONB), `step_outputs` (JSONB), `current_step` (TEXT), `error` (TEXT), `started_at` (TIMESTAMPTZ), `completed_at` (TIMESTAMPTZ), `created_at` (TIMESTAMPTZ DEFAULT NOW()). RLS enabled with `is_record_owner(user_id)`. [A8, A9]
- [ ] **AC-17:** `cancel_run()` sets the run status to `cancelled` and cancels the background asyncio task. If the graph is waiting at an interrupt, the cancellation is immediate. If a step is mid-execution (Anthropic API call in flight), the call is cancelled and the step output is discarded. [A14]

### FU-4: dispatch_workflow Tool Implementation

- [ ] **AC-18:** The `dispatch_workflow` tool (stubbed in SPEC-033 AC-28) is implemented with the real schema: `{"name": "dispatch_workflow", "description": "Start a multi-step workflow. Available workflows: email-triage, morning-briefing, draft-reply.", "input_schema": {"type": "object", "properties": {"workflow_name": {"type": "string", "description": "Name of the workflow template"}, "parameters": {"type": "object", "description": "Input parameters for the workflow"}}, "required": ["workflow_name"]}}`. [A6]
- [ ] **AC-19:** When invoked, `dispatch_workflow` calls `WorkflowRunManager.start_run(user_id, workflow_name, parameters)` and returns a status message: `"Started workflow '{name}' (run_id: {id}). I'll keep you updated on progress."` If the template doesn't exist, it returns: `"Unknown workflow '{name}'. Available workflows: {list}."` If required parameters are missing, it returns a clear error listing missing params. [A14]
- [ ] **AC-20:** The `dispatch_workflow` tool is registered as a capability executor in the Capability Gateway (SPEC-034 pattern), not as a handler-internal tool. It appears in the agent's tool definitions and goes through standard gateway execution. Tool definition file at `system/tools/dispatch_workflow.md` with `required_tier: inform` (dispatching is safe — the workflow itself enforces gates). [A6, A12]

### FU-5: Progress Streaming + Human Gate Integration

- [ ] **AC-21:** Running workflows emit progress events to the user's active chat session. Events are written to a `workflow_events` Postgres table: `id` (SERIAL), `run_id` (UUID FK → workflow_runs), `user_id` (UUID), `event_type` (TEXT — "step_started", "step_completed", "approval_required", "workflow_completed", "workflow_failed", "status_update"), `data` (JSONB — step name, output preview, etc.), `created_at` (TIMESTAMPTZ DEFAULT NOW()). RLS with `is_record_owner(user_id)`. [A8]
- [ ] **AC-22:** The ConversationHandler's SSE stream (SPEC-033) includes workflow events. A background task polls `workflow_events` for new rows (by `user_id`, since last seen `id`) and injects them into the SSE stream as `{"type": "workflow_event", "run_id": "...", "event_type": "...", "data": {...}}`. Polling interval: 2 seconds. [A1]
- [ ] **AC-23:** When a workflow step has `gate_policy: "human-required"`, the graph pauses via LangGraph's `interrupt()`. The node before the interrupt writes an `approval_required` event. A `pending_action` is created via `PendingActionsService.queue_action()` with `tool_name: "workflow_gate"`, `tool_args: {run_id, step_name, description, preview}`, and `context: {template_name, current_step}`. [A12]
- [ ] **AC-24:** When the user approves the pending action (via existing approval flow — web button or Telegram inline), the `WorkflowRunManager.resume_run(run_id, approval_data)` method is called. This updates the LangGraph state via `compiled_graph.aupdate_state(thread_config, {"approval": approval_data})` and re-invokes the graph, resuming from the interrupt point. [A12]
- [ ] **AC-25:** When the user rejects a pending action for a workflow gate, the run status is set to `cancelled` and a `workflow_failed` event is emitted with reason `"User rejected approval at step '{step_name}'"`. [A14]
- [ ] **AC-26:** Workflow completion writes a `workflow_completed` event with the final step outputs. The ConversationHandler picks this up and can present the result conversationally (e.g., "Your morning briefing is ready: ..."). [A1]

### FU-6: Scheduling Integration

- [ ] **AC-27:** A `handle_workflow` async handler in `chatServer/services/job_handlers.py` accepts a job dict with `input: {user_id, template_name, parameters}` and calls `WorkflowRunManager.start_run()`. Registered as handler for `job_type = 'workflow'`. [A1, A11]
- [ ] **AC-28:** Scheduled workflows are created via `JobService.create(job_type='workflow', input={template_name, parameters}, user_id=..., scheduled_for=...)`. The handler self-schedules the next occurrence on completion (same pattern as SPEC-028 briefing handlers). [A1]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/workflows/__init__.py` | Package init |
| `chatServer/workflows/models.py` | `GraphTemplate`, `StepDef`, `ParameterDef`, `WorkflowState`, `EngineResult`, `WorkflowRunStatus` |
| `chatServer/workflows/template_parser.py` | Markdown+YAML → `GraphTemplate` parser |
| `chatServer/workflows/registry.py` | Template loading from ConfigService with caching |
| `chatServer/workflows/engine.py` | `AnthropicEngine` — Anthropic Messages API execution |
| `chatServer/workflows/builder.py` | `GraphBuilder` — template → compiled `StateGraph` |
| `chatServer/workflows/checkpointer.py` | `WorkflowCheckpointer` — wraps `AsyncPostgresSaver` |
| `chatServer/workflows/run_manager.py` | `WorkflowRunManager` — start, monitor, cancel, resume runs |
| `chatServer/workflows/progress.py` | Progress event emission + SSE injection |
| `chatServer/capabilities/executors/workflow.py` | `dispatch_workflow` capability executor |
| `supabase/migrations/2026MMDD000001_create_workflow_tables.sql` | `workflow_runs` + `workflow_events` tables, RLS, indexes |
| `tests/chatServer/workflows/test_template_parser.py` | Parser unit tests |
| `tests/chatServer/workflows/test_registry.py` | Registry unit tests |
| `tests/chatServer/workflows/test_engine.py` | AnthropicEngine unit tests |
| `tests/chatServer/workflows/test_builder.py` | GraphBuilder unit tests |
| `tests/chatServer/workflows/test_run_manager.py` | RunManager unit tests |
| `tests/chatServer/workflows/test_progress.py` | Progress streaming tests |
| `tests/chatServer/capabilities/executors/test_workflow.py` | dispatch_workflow executor tests |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/main.py` | Initialize `WorkflowCheckpointer` pool in lifespan; start progress polling task |
| `chatServer/services/job_handlers.py` | Add `handle_workflow` handler + registration |
| `chatServer/services/background_tasks.py` | Register `handle_workflow` handler with `JobRunnerService` |
| `chatServer/services/pending_actions.py` | Add `workflow_gate` to recognized tool names for approval routing |
| `requirements.txt` | Add `langgraph>=1.1.6`, `langgraph-checkpoint-postgres`, `psycopg-pool` |
| `chatServer/requirements.txt` | Same additions |
| `chatServer/database/user_scoped_tables.py` | Add `workflow_runs`, `workflow_events` |

### Out of Scope

- **Workflow template authoring.** Users don't create templates in this spec — templates are system-defined (SPEC-037 creates the first three). User template customization is Phase 3+.
- **Daemon integration / ClaudePEngine.** The daemon uses `ClaudePEngine` (subprocess-based). This spec only implements `AnthropicEngine` (API-based). Daemon integration is Phase 5 (SPEC-045+).
- **Workflow template UI.** No frontend for browsing/editing templates. This is Phase 4 (file browser).
- **Model routing optimization.** Per-step model selection is supported (AC-08) but cost optimization (Haiku for classification, Sonnet for generation) is left to template authors in SPEC-037.
- **Parallel step execution.** Steps run sequentially based on dependency order. Parallel execution of independent steps is a future optimization.
- **Workflow versioning.** Templates are identified by name, not name+version. Version field exists in the template but is informational only.
- **Cross-workflow state sharing.** Each workflow run is independent. No shared state between runs.

## Technical Approach

### 1. Template Format (compatible with HQ)

```markdown
---
name: email-triage
description: Scheduled email processing — read inbox, categorize, surface important
version: 1
default_gate_policy: none
---

# Email Triage

Process recent emails, categorize by urgency, and surface items needing attention.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| hours_back | no | How many hours of email to process (default: 12) |
| max_emails | no | Maximum emails to process (default: 20) |

## Steps

### step-1: Fetch and Categorize
- **agent:** email-classifier
- **depends_on:** []
- **tools:** [search_gmail, get_gmail]
- **description:** Search recent emails, read content, categorize each as urgent/actionable/informational/ignorable.
- **gate:** none

### step-2: Summarize and Surface
- **agent:** briefing-composer
- **depends_on:** [step-1]
- **tools:** [create_memories]
- **description:** From categorized emails, compose a summary. Store important items as memories for future reference.
- **gate:** none
```

**Parsing notes:** The parser reads YAML frontmatter via `yaml.safe_load`. Step sections are parsed by regex matching `### step-N: Name` headers and extracting key-value fields (`- **key:** value`). The `tools` field uses YAML list syntax `[tool1, tool2]`. This matches HQ's format exactly — `sdlc-full-cycle.md` and `light-cycle.md` use this structure.

### 2. AnthropicEngine (replaces ClaudePEngine)

```python
class AnthropicEngine:
    """Execute workflow steps via Anthropic Messages API."""

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        gateway: CapabilityGateway,
        user_id: str,
    ):
        self._client = client
        self._gateway = gateway
        self._user_id = user_id

    async def run(
        self,
        prompt: str,
        tools: list[str],
        system_prompt: str | None = None,
        model: str = "claude-sonnet-4-5-20250514",
        max_tokens: int = 4096,
        temperature: float = 0.5,
    ) -> EngineResult:
        # 1. Get tool schemas filtered to step's allowed tools
        all_schemas = await self._gateway.get_tool_schemas(self._user_id)
        step_schemas = [s for s in all_schemas if s["name"] in tools]

        # 2. Run tool-loop (same pattern as ConversationHandler)
        messages = [{"role": "user", "content": prompt}]
        total_usage = TokenUsage(0, 0)
        tool_calls = []

        for _ in range(15):  # max tool iterations per step
            response = await self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "",
                messages=messages,
                tools=step_schemas if step_schemas else NOT_GIVEN,
            )
            total_usage += response.usage

            if response.stop_reason == "end_turn":
                output = extract_text(response)
                return EngineResult(output=output, tool_calls=tool_calls, token_usage=total_usage)

            if response.stop_reason == "tool_use":
                # Execute tool calls through gateway
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await self._gateway.execute(
                            self._user_id, block.name, block.input
                        )
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result.content})
                        tool_calls.append(ToolCallRecord(block.name, block.input, result.content))

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

        return EngineResult(output="[Max iterations reached]", tool_calls=tool_calls, token_usage=total_usage)
```

**Key difference from HQ's `ClaudePEngine`:** No subprocess, no `claude -p` binary. Direct API calls with tool routing through the Capability Gateway. This means:
- No subprocess management on the server
- Direct token/cost tracking from API response
- Tool calls enforced by the gateway's allowlist + trust tiers
- No dependency on the `claude` CLI binary

### 3. Graph Builder

```python
class GraphBuilder:
    """Build a LangGraph StateGraph from a GraphTemplate."""

    def build(
        self,
        template: GraphTemplate,
        engine: AnthropicEngine,
        notification_service: NotificationService,
    ) -> tuple[CompiledStateGraph, list[str]]:
        """Returns (compiled_graph, interrupt_node_names)."""

        graph = StateGraph(WorkflowState)
        interrupt_nodes = []

        for step in template.steps:
            node_fn = self._make_step_node(step, engine)
            graph.add_node(step.name, node_fn)

            if step.gate_policy == "human-required":
                # Add gate node that interrupts
                gate_fn = self._make_gate_node(step, notification_service)
                gate_name = f"{step.name}_gate"
                graph.add_node(gate_name, gate_fn)
                interrupt_nodes.append(gate_name)

        # Wire edges from depends_on
        for step in template.steps:
            if not step.depends_on:
                graph.add_edge(START, step.name)
            else:
                for dep in step.depends_on:
                    dep_step = self._find_step(template, dep)
                    if dep_step and dep_step.gate_policy == "human-required":
                        graph.add_edge(f"{dep}_gate", step.name)
                    else:
                        graph.add_edge(dep, step.name)

            if step.gate_policy == "human-required":
                graph.add_edge(step.name, f"{step.name}_gate")

        # Terminal nodes → END
        terminal_steps = self._find_terminal_steps(template)
        for step in terminal_steps:
            if step.gate_policy == "human-required":
                graph.add_edge(f"{step.name}_gate", END)
            else:
                graph.add_edge(step.name, END)

        compiled = graph.compile(
            checkpointer=self._checkpointer,
            interrupt_before=interrupt_nodes,
        )
        return compiled, interrupt_nodes
```

### 4. Progress Streaming Architecture

The architecture proposal (Section 6, Open Question #1) identified three options for streaming workflow progress to the chat. This spec uses **option (a): Postgres-backed event table with polling**.

```
Workflow step completes
  → WorkflowRunManager writes to workflow_events table
  → Background polling task reads new events per user
  → Injects into active SSE stream as workflow_event messages
```

**Why Postgres polling, not in-memory event bus:** The chatServer may restart during a workflow run. Postgres events survive restarts. The checkpointer already ensures the graph state survives; the event table ensures progress visibility survives too. Polling at 2s interval is acceptable for workflow progress (these are multi-minute operations, not real-time chat).

**Why not Postgres LISTEN/NOTIFY:** Adds connection management complexity (dedicated listener connection). Polling is simpler and sufficient at our scale (single user, <10 concurrent runs).

**SSE injection:** The ConversationHandler's SSE stream generator (SPEC-033 AC-12) is extended to interleave workflow events between message events. When no user message is being processed, the stream remains open and emits workflow events as they arrive. When a user message IS being processed, workflow events are queued and emitted after the message response completes.

### 5. Checkpointer Setup

Reuses HQ's pattern from `checkpointer.py`:

```python
class WorkflowCheckpointer:
    """Manages the Postgres checkpointer lifecycle."""

    def __init__(self, database_url: str):
        self._db_url = database_url
        self._pool: AsyncConnectionPool | None = None
        self._saver: AsyncPostgresSaver | None = None

    async def setup(self):
        self._pool = AsyncConnectionPool(
            self._db_url,
            kwargs={"prepare_threshold": None, "autocommit": True},
            open=False,
        )
        await self._pool.open()
        self._saver = AsyncPostgresSaver(self._pool)
        await self._saver.setup()

    async def shutdown(self):
        if self._pool:
            await self._pool.close()

    @property
    def saver(self) -> AsyncPostgresSaver:
        if not self._saver:
            raise RuntimeError("Checkpointer not initialized")
        return self._saver
```

**`prepare_threshold=None`** is critical — HQ discovered that without it, psycopg3's automatic statement preparation causes "prepared statement already exists" errors across runs.

### 6. dispatch_workflow Integration

The tool becomes a capability executor (SPEC-034 pattern):

```python
# chatServer/capabilities/executors/workflow.py
async def dispatch_workflow(params: dict, ctx: ExecutionContext) -> str:
    run_manager = get_workflow_run_manager()
    template_name = params["workflow_name"]
    workflow_params = params.get("parameters", {})

    try:
        run_id = await run_manager.start_run(
            user_id=ctx.user_id,
            template_name=template_name,
            parameters=workflow_params,
        )
        return f"Started workflow '{template_name}' (run_id: {run_id}). I'll keep you updated on progress."
    except TemplateNotFoundError:
        available = await run_manager.list_templates(ctx.user_id)
        return f"Unknown workflow '{template_name}'. Available workflows: {', '.join(available)}."
    except MissingParameterError as e:
        return f"Missing required parameters for '{template_name}': {e.missing_params}"
```

Tool definition file (`system/tools/dispatch_workflow.md`):

```markdown
---
name: dispatch_workflow
description: >
  Start a multi-step workflow. Use this for complex tasks that require
  multiple steps like email triage, composing briefings, or drafting replies.
required_tier: inform
min_grantable_tier: inform
default_granted_tier: act
executor: workflow.dispatch_workflow
credential_type: null
data_source: null
parameters:
  type: object
  properties:
    workflow_name:
      type: string
      description: Name of the workflow template (e.g., email-triage, morning-briefing, draft-reply)
    parameters:
      type: object
      description: Input parameters for the workflow (varies by template)
  required: [workflow_name]
---

Dispatch a multi-step workflow for complex tasks. The workflow runs in
the background and streams progress updates to the chat.
```

### 7. Human Gate Flow (detailed)

```
1. Graph execution reaches a step with gate_policy: "human-required"
2. Step executes normally (LLM call + tools)
3. After step completes, the gate node runs:
   a. Writes step output preview to workflow_events (event_type: "approval_required")
   b. Creates a pending_action via PendingActionsService:
      - tool_name: "workflow_gate"
      - tool_args: {run_id, step_name, output_preview}
      - context: {template_name, step_description}
   c. Calls LangGraph interrupt() — graph execution pauses
4. User sees notification (web + Telegram) with step output and approve/reject buttons
5a. User approves → PendingActionsService marks approved → resume_run() called
    → graph.aupdate_state() with approval data → graph re-invoked → continues to next step
5b. User rejects → cancel_run() called → run marked cancelled → workflow_failed event emitted
```

## Blast Radius

### New Infrastructure

| Component | Impact | Risk |
|-----------|--------|------|
| `chatServer/workflows/` package | New code — 9 files | Medium — new subsystem, well-isolated |
| `workflow_runs` table | New table + RLS | Low — no existing data affected |
| `workflow_events` table | New table + RLS | Low — no existing data affected |
| LangGraph checkpoint tables | Auto-created by `AsyncPostgresSaver.setup()` | Low — namespaced with `workflow_` prefix |
| `langgraph` + dependencies | New Python dependencies | Medium — adds `langchain-core` as transitive dep |

### Modified Existing Components

| File | Impact | Risk |
|------|--------|------|
| `chatServer/main.py` | Add checkpointer lifecycle, progress polling task | **HIGH** — startup/shutdown path |
| `chatServer/services/job_handlers.py` | Add `handle_workflow` handler | Low — additive |
| `chatServer/services/background_tasks.py` | Register new handler | Low — additive |
| `chatServer/services/pending_actions.py` | Recognize `workflow_gate` tool name | Low — additive to existing switch |
| `requirements.txt` / `chatServer/requirements.txt` | Add 3 packages | Medium — dependency footprint |
| `chatServer/database/user_scoped_tables.py` | Add 2 tables | Low — additive |

### Existing Components NOT Modified

| Component | Why Kept |
|-----------|----------|
| `ConversationHandler` (SPEC-033) | Calls `dispatch_workflow` via gateway — no handler changes |
| `CapabilityGateway` (SPEC-034) | Workflow executor registered like any other — no gateway changes |
| `ConfigService` (SPEC-035) | Templates loaded via standard `read()` — no service changes |
| `NotificationService` | Called by gate nodes — interface unchanged |
| `PendingActionsService` | Called for approval flow — interface unchanged (just new tool_name) |
| `JobService` / `JobRunnerService` | New handler registered — core unchanged |

## Testing Requirements

### Unit Tests (required)

**Template Parser (`test_template_parser.py`):**
- `test_parse_valid_template` — full template → `GraphTemplate` with correct steps
- `test_parse_template_missing_frontmatter` → `TemplateParseError`
- `test_parse_template_missing_required_fields` → `TemplateParseError` with field name
- `test_parse_step_tools_list` — `[search_gmail, get_gmail]` → list of strings
- `test_parse_step_depends_on` — dependency relationships preserved
- `test_parse_step_gate_policy` — all three values recognized

**Registry (`test_registry.py`):**
- `test_list_templates_system_only` — returns system templates
- `test_list_templates_user_shadows_system` — user template overrides system
- `test_get_template_not_found` → `TemplateNotFoundError`
- `test_cache_ttl` — template not re-fetched within TTL

**AnthropicEngine (`test_engine.py`):**
- `test_run_simple_prompt` — no tools, single API call, returns output
- `test_run_with_tools` — tool call dispatched through mock gateway
- `test_run_max_iterations` — stops after 15 iterations
- `test_run_model_override` — per-step model is used
- `test_run_gateway_error_propagated` — tool execution error returned to LLM

**GraphBuilder (`test_builder.py`):**
- `test_build_linear_graph` — A → B → C, no gates
- `test_build_with_human_gate` — A → A_gate (interrupt) → B
- `test_build_with_dependencies` — step-2 depends_on [step-1]
- `test_build_terminal_node_to_end` — last step connects to END

**RunManager (`test_run_manager.py`):**
- `test_start_run_returns_id` — valid template + params → run_id
- `test_start_run_unknown_template` → `TemplateNotFoundError`
- `test_start_run_missing_params` → `MissingParameterError`
- `test_cancel_run` — sets status to cancelled
- `test_get_run_status` — returns current status
- `test_resume_run_after_interrupt` — approval resumes graph

**dispatch_workflow executor (`test_workflow.py`):**
- `test_dispatch_valid_workflow` — returns success message with run_id
- `test_dispatch_unknown_workflow` — returns available workflows list
- `test_dispatch_missing_params` — returns missing params error

### Integration Tests

- `test_full_workflow_lifecycle` — start → step executes → completes → events emitted
- `test_workflow_with_human_gate` — start → interrupt → approve → resume → complete
- `test_workflow_scheduling` — create job → handler fires → run starts

### AC-to-Test Mapping

| AC | Test | Notes |
|----|------|-------|
| AC-01, AC-02 | `test_parse_valid_template`, models tests | Dataclass structure |
| AC-03 | `test_parse_*` suite | Parser correctness |
| AC-04, AC-05 | `test_list_templates_*`, `test_get_template_*` | Registry operations |
| AC-06 | `test_run_simple_prompt`, `test_run_with_tools` | Engine execution |
| AC-07 | `test_run_with_tools` | Gateway integration |
| AC-08 | `test_run_model_override` | Per-step model config |
| AC-09, AC-10, AC-11 | `test_build_*` suite | Graph construction |
| AC-12, AC-13 | Checkpointer setup test | Pool + saver lifecycle |
| AC-14–17 | `test_*_run_*` suite | Run management |
| AC-18, AC-19, AC-20 | `test_dispatch_*` suite | Tool implementation |
| AC-21, AC-22, AC-26 | `test_full_workflow_lifecycle` | Progress events |
| AC-23, AC-24, AC-25 | `test_workflow_with_human_gate` | Gate flow |
| AC-27, AC-28 | `test_workflow_scheduling` | Job integration |

### Manual Verification (UAT)

- [ ] Start chatServer with workflow engine initialized (check logs for "Workflow checkpointer initialized")
- [ ] Send "run email triage" → agent calls `dispatch_workflow` → returns started message
- [ ] Verify `workflow_runs` row created with status=running
- [ ] Verify `workflow_events` rows appear as steps complete
- [ ] Verify SSE stream includes `workflow_event` messages
- [ ] For a gated workflow: verify pending_action created, approve it, verify workflow resumes
- [ ] Cancel a running workflow → verify status=cancelled
- [ ] Schedule a workflow via jobs table → verify it fires at scheduled time

## Edge Cases

- **Template not found in ConfigService:** `TemplateNotFoundError` with available template list. The `dispatch_workflow` tool surfaces this to the agent conversationally.
- **Anthropic API rate limit during workflow step:** Step fails, error recorded in step output. Workflow marks step as failed. The job handler's retry mechanism resumes from the failed step's checkpoint (not from the beginning), preserving completed step outputs.
- **Checkpointer connection pool exhausted:** `start_run` fails with connection error. Tool returns "Workflow engine is busy, please try again in a moment."
- **Workflow runs while user is offline:** Events accumulate in `workflow_events` table. When the user reconnects, all pending events are delivered in order via the SSE stream.
- **Multiple concurrent workflow runs:** Each run has its own `thread_id` in the checkpointer. Runs are independent. Events are tagged by `run_id` for disambiguation.
- **Server restart during workflow:** Checkpointed state survives. On restart, the `WorkflowRunManager` queries `workflow_runs` for status=running rows and resumes from the last completed step's checkpoint — not from the beginning. Completed steps are not re-executed. Only the failed/interrupted step is retried.
- **Step exceeds token budget:** `AnthropicEngine` has a per-step token limit (via `max_tokens`). If the LLM response is truncated, the step completes with partial output. No special handling — the next step works with whatever output was produced.
- **Human gate approval timeout:** Pending actions have 24h default expiry. If not approved in time, the pending action expires and the workflow run is marked as `failed` with reason "Approval timed out".

## Functional Units (for PR Breakdown)

### FU-1: Template Parser + Registry + Models (backend-dev)
**ACs:** AC-01, AC-02, AC-03, AC-04, AC-05
**Depends on:** SPEC-035 (ConfigService for template loading)

Parse templates, cache them, expose via registry. Pure data transformation — no LLM calls, no DB writes.

### FU-2: AnthropicEngine + GraphBuilder (backend-dev)
**ACs:** AC-06, AC-07, AC-08, AC-09, AC-10, AC-11
**Depends on:** FU-1, SPEC-034 (CapabilityGateway for tool execution)

Build and execute graphs. Core engine logic.

### FU-3: Checkpointer + RunManager + DB Tables (database-dev + backend-dev)
**ACs:** AC-12, AC-13, AC-14, AC-15, AC-16, AC-17
**Depends on:** FU-2

State persistence and run lifecycle management.

### FU-4: dispatch_workflow Implementation (backend-dev)
**ACs:** AC-18, AC-19, AC-20
**Depends on:** FU-3

Replace SPEC-033's stub with real implementation.

### FU-5: Progress Streaming + Human Gates (backend-dev)
**ACs:** AC-21, AC-22, AC-23, AC-24, AC-25, AC-26
**Depends on:** FU-3, FU-4

Event emission, SSE injection, pending_action integration.

### FU-6: Job Scheduling Integration (backend-dev)
**ACs:** AC-27, AC-28
**Depends on:** FU-3

Wire workflow runs into the universal job queue.

### Merge Order

```
FU-1 → FU-2 → FU-3 → FU-4 → FU-5
                 └────→ FU-6
```

FU-5 and FU-6 can run in parallel after FU-3.

## Resolved Decisions

1. **Progress polling at 2s interval — accepted.** Postgres polling is sufficient for MVP. Workflow steps are multi-minute operations; 2s latency on progress events is invisible to the user.

2. **Retry failed step, not entire workflow.** On server restart or step failure, the checkpointer preserves state up to the last completed step. The `WorkflowRunManager` resumes from the failed step's checkpoint, not from the beginning. This is the primary value of checkpointing — don't discard completed work.

3. **Per-step model override — confirmed.** Default Sonnet for generation/composition steps, Haiku for classification/categorization steps. SPEC-037 uses this: email triage `categorize` step runs on Haiku, all other steps on Sonnet.

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-28)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (dispatch_workflow schema, workflow_event format, gate → pending_action shape)
- [x] Technical decisions reference architecture principles (A1, A2, A3, A6, A8, A9, A11, A12, A14)
- [x] Merge order is explicit and acyclic
- [x] Out-of-scope is explicit (7 items)
- [x] Edge cases documented with expected behavior (8 cases)
- [x] Testing requirements map to ACs
- [x] Dependencies documented with status
- [x] Blast radius assessed for all new and modified files
- [x] HQ patterns cited where ported (template format, checkpointer, engine protocol)
