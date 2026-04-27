# SPEC-056: Primitive Extensibility — Data-Driven Tool Registry & Workflow Tool Injection

> **Status:** Draft  
> **Author:** Claude (Spec Writer) on behalf of Tim  
> **Created:** 2026-04-27  
> **Vision:** `docs/product/VISION.md` — agents and workflows as composable, extensible primitives  
> **Depends On:** SPEC-036 (Workflow Engine), SPEC-043 (Deep Agents runtime), SPEC-048 (Workflow Editor)  
> **Downstream:** SPEC-055 (Agent Autonomy — tool request flow builds on the `agent_tools.status` primitive added here)

---

## Goal

Remove the structural barriers that prevent chat agents and background agents from extending the system's primitives (tools, workflows, skills). Specifically:

1. **Fix the critical bug** where workflows started from the UI or background jobs execute with **zero tools**.
2. **Replace hardcoded Python registries** with data-driven configuration where safe, while preserving the security boundary that prevents agents from escalating capabilities via arbitrary code execution.
3. **Make tool assignment requestable/grant-able** via a `status` column on `agent_tools`, enabling the tool request flow defined in SPEC-055.

Success looks like: a background briefing workflow can search Gmail, create tasks, and draft replies — using the exact same tool infrastructure as the chat agent. A user can approve a tool request, and the agent has it on the next run with no deploy.

---

## Security Boundary (Non-Negotiable)

> **Agents MUST NOT execute arbitrary code or instantiate arbitrary Python classes.**

This means:
- **Tool type → Python class mapping** stays in Python code, not the database.
- **Tool behavior** (table name, method, endpoint, payload schema) is fully data-driven via `tools.config` JSONB.
- **Approval tiers** move from hardcoded dict to DB column, but tier logic (what `auto` vs `requires_approval` means) stays in code.

---

## Existing Infrastructure

| Primitive | Location | Current State |
|-----------|----------|---------------|
| `TOOL_REGISTRY` | `src/core/agent_loader_db.py:39` | Hardcoded dict mapping `type` string → Python class |
| `TOOL_APPROVAL_DEFAULTS` | `chatServer/security/approval_tiers.py:38` | Hardcoded dict mapping tool name → `(tier, default)` |
| `load_tools_from_db()` | `src/core/agent_loader_db.py:231` | Fetches agent tools from DB, looks up class in `TOOL_REGISTRY`, instantiates |
| `WorkflowRunManager` | `chatServer/workflows/run_manager.py:26` | Hardcodes `register_service("deliver", deliver_briefing)` |
| `dispatch_workflow` | `chatServer/workflows/dispatch.py:18` | Accepts `tool_schemas` and `tool_executors` params, but callers pass empty collections |
| `GraphBuilder` | `chatServer/workflows/builder.py:48` | Accepts `service_registry` dict param, but never exposed to callers |
| `approval_tiers.py` | `chatServer/security/approval_tiers.py` | `get_tool_default_tier()` reads hardcoded dict; no DB fallback |
| `tool_execution.py` | `chatServer/services/tool_execution.py` | Post-approval executor; mirrors `load_tools_from_db` lookup logic |

---

## Acceptance Criteria

### Critical Bug: Workflow Tool Injection

- [ ] **AC-01:** `WorkflowRunManager` and `dispatch_workflow` receive the same tool schemas and executors that the chat agent uses for the target user. Workflows started from the UI editor (`workflow_editor_service.run_workflow`), background jobs (`handle_workflow`), and chat agent dispatch all share a single tool resolution path. [A1]
- [ ] **AC-02:** The tool resolution path (`ToolResolverService`, new) loads tools for a given `(user_id, agent_name)` by querying `agent_tools` + `tools` tables, instantiating via `load_tools_from_db()`, and returning `(tool_schemas, tool_executors)` suitable for both the Deep Agents runtime and the workflow `AnthropicEngine`. [A1]
- [ ] **AC-03:** No workflow execution path passes empty `tool_schemas=[]` or `tool_executors={}`. All existing call sites (`workflow_editor_service`, `job_handlers`, `today_router` if applicable) are updated to use `ToolResolverService`. [A1]

### Tool Registry Extensibility

- [ ] **AC-04:** A `@register_tool_type(db_type: str)` decorator exists in `chatServer/tools/registry.py`. All existing tool classes in `TOOL_REGISTRY` are migrated to use it. The legacy `TOOL_REGISTRY` dict is removed or becomes a read-only view of the decorator registry. [A1]
- [ ] **AC-05:** A new generic tool type `WebhookTool` is registered. Its `config` JSONB specifies `url`, `method`, `headers`, `payload_schema`, and `timeout`. The tool makes HTTP requests and returns the response body. This proves that new capabilities can be added via DB config alone, without new Python classes. [A1]
- [ ] **AC-06:** `tool_execution.py` (post-approval executor) uses the same decorator registry as `load_tools_from_db()`. No duplicate hardcoded mappings. [A1]

### Data-Driven Approval Tiers

- [ ] **AC-07:** Migration adds `approval_tier VARCHAR(50)` to `tools` table. Values: `auto`, `requires_approval`, `user_configurable`. [A8, A12]
- [ ] **AC-08:** Migration populates `approval_tier` from the existing `TOOL_APPROVAL_DEFAULTS` hardcoded dict, keyed by `tools.name`. All 23 canonical tools get correct tiers. [A8]
- [ ] **AC-09:** `get_tool_default_tier(tool_name)` in `approval_tiers.py` reads from DB first, falling back to `DEFAULT_UNKNOWN_TIER` only if no row exists. The hardcoded `TOOL_APPROVAL_DEFAULTS` dict is removed or becomes a fallback seed. [A8]
- [ ] **AC-10:** `tool_wrapper.py` uses `get_tool_default_tier()` (now DB-backed) when determining whether to auto-execute or queue a pending action. No behavioral change for existing tools. [A12]

### Tool Assignment Request/Grant

- [ ] **AC-11:** Migration adds `status VARCHAR(20)` to `agent_tools` with values `granted` (default), `pending`, `revoked`. Backfill existing rows to `granted`. [A8]
- [ ] **AC-12:** `load_tools_from_db()` only loads tools where `agent_tools.status = 'granted'` (or `NULL` for backward compatibility). Pending or revoked tools are excluded from the agent's tool set. [A8]
- [ ] **AC-13:** `ToolCacheService` (`_fetch_tools_for_agent`) filters by `status = 'granted'` or `status IS NULL`. [A8]
- [ ] **AC-14:** The tool request flow from SPEC-055 AC-08–10 operates by creating `agent_tools` rows with `status = 'pending'`. Grant sets `status = 'granted'`; revoke sets `status = 'revoked'`. [F3]

### Workflow Service Node Extensibility

- [ ] **AC-15:** `WorkflowRunManager` no longer hardcodes `register_service("deliver", deliver_briefing)` in `__init__`. Instead, it accepts an optional `service_registry: dict[str, Callable]` parameter. [A1]
- [ ] **AC-16:** System service nodes (e.g., `deliver_briefing`) are registered in a module-level `DEFAULT_SERVICE_REGISTRY` dict. `WorkflowRunManager` uses this as the default when no custom registry is provided. [A1]
- [ ] **AC-17:** Future specs can add new service nodes by adding entries to `DEFAULT_SERVICE_REGISTRY` without modifying `WorkflowRunManager.__init__`. [A1]

---

## Files to Create

| File | Purpose |
|------|---------|
| `chatServer/services/tool_resolver_service.py` | Resolve tools for `(user_id, agent_name)` → `(schemas, executors, instantiated_tools)` |
| `chatServer/tools/registry.py` | `@register_tool_type` decorator + `get_tool_class(db_type)` lookup |
| `chatServer/tools/webhook_tool.py` | Generic `WebhookTool` implementation |
| `supabase/migrations/20260427000001_tool_extensibility.sql` | Add `tools.approval_tier`, `agent_tools.status`; seed tiers for canonical tools |
| `tests/unit/services/test_tool_resolver_service.py` | Tool resolution, caching, status filtering |
| `tests/unit/tools/test_registry.py` | Decorator registration, lookup, fallback |
| `tests/unit/tools/test_webhook_tool.py` | Webhook execution, config parsing, error handling |

## Files to Modify

| File | Change |
|------|--------|
| `src/core/agent_loader_db.py` | Replace `TOOL_REGISTRY` dict with import from `chatServer/tools/registry.py`. Update `load_tools_from_db()` to filter by `agent_tools.status`. |
| `chatServer/security/approval_tiers.py` | Replace `TOOL_APPROVAL_DEFAULTS` with DB query. Keep `DEFAULT_UNKNOWN_TIER`. |
| `chatServer/security/tool_wrapper.py` | No structural change; uses `get_tool_default_tier()` which now reads DB. |
| `chatServer/services/tool_execution.py` | Replace hardcoded `TOOL_REGISTRY` import with `get_tool_class()` from registry. |
| `chatServer/services/tool_cache_service.py` | Add `status` filter to `_fetch_tools_for_agent` and `_fetch_all_tools`. |
| `chatServer/workflows/run_manager.py` | Remove hardcoded `register_service("deliver")`. Accept `service_registry` param. Use `DEFAULT_SERVICE_REGISTRY` fallback. |
| `chatServer/workflows/dispatch.py` | Use `ToolResolverService` to build tools before calling `WorkflowRunManager`. |
| `chatServer/services/workflow_editor_service.py` | Use `ToolResolverService` instead of empty `tool_schemas=[]`. |
| `chatServer/services/job_handlers.py` | Use `ToolResolverService` instead of empty `tool_schemas=[]`. |
| `chatServer/services/scheduled_execution_service.py` | Use `ToolResolverService` for scheduled agent runs if not already. |
| `chatServer/services/deep_agent_builder.py` | Use `ToolResolverService` or ensure `load_tools_from_db` path is consistent. |

## Out of Scope

- **Agent behavior / prompt changes** — SPEC-055 covers autonomy, action journal, heartbeat v2.
- **New tool types requiring new Python classes** — still require code deploy + `@register_tool_type`. The security boundary is preserved.
- **Dynamic class loading from DB** — rejected. See Security Boundary above.
- **Skills extensibility** — system skills remain read-only; user skills are already writable via vault. No schema changes needed.
- **Channel extensibility** — Tim confirmed channels are intentionally not extensible for now.

---

## Technical Approach

### 1. Tool Resolver Service

```python
class ToolResolverService:
    def __init__(self, db_client, settings):
        self.db = db_client
        self.settings = settings

    async def resolve_for_agent(self, user_id: str, agent_name: str):
        # 1. Fetch tools from DB (filtered by status=granted)
        # 2. Call load_tools_from_db() to instantiate
        # 3. Build tool_schemas (OpenAI/Anthropic format) and tool_executors (name -> fn)
        return (tool_schemas, tool_executors, instantiated_tools)
```

Callers (`WorkflowRunManager`, `dispatch_workflow`, chat handler) use this instead of building tools ad-hoc.

### 2. `@register_tool_type` Decorator

```python
# chatServer/tools/registry.py
_registry: dict[str, Type] = {}

def register_tool_type(db_type: str):
    def decorator(cls: Type):
        _registry[db_type] = cls
        return cls
    return decorator

def get_tool_class(db_type: str) -> Type | None:
    return _registry.get(db_type)
```

Migration: add `@register_tool_type("SearchGmailTool")` to each tool class, then remove the old dict.

### 3. `WebhookTool`

```python
@register_tool_type("WebhookTool")
class WebhookTool(BaseTool):
    # config-driven: url, method, headers, payload_schema, timeout
    # validates payload against schema, makes HTTP request, returns response
```

### 4. Approval Tier Migration

```sql
ALTER TABLE tools ADD COLUMN approval_tier VARCHAR(50);

UPDATE tools SET approval_tier = 'auto' WHERE name = 'search_gmail';
-- ... etc for all 23 canonical tools
```

`approval_tiers.py` becomes:

```python
async def get_tool_default_tier(tool_name: str, db_client=None):
    if db_client:
        row = await db_client.table("tools").select("approval_tier").eq("name", tool_name).single()
        if row.data:
            return ApprovalTier(row.data["approval_tier"])
    return DEFAULT_UNKNOWN_TIER
```

### 5. Service Registry Pattern

```python
# chatServer/workflows/services.py
DEFAULT_SERVICE_REGISTRY = {
    "deliver": deliver_briefing,
    # future entries added here
}

# run_manager.py
class WorkflowRunManager:
    def __init__(self, ..., service_registry=None):
        self.builder = GraphBuilder()
        for name, fn in (service_registry or DEFAULT_SERVICE_REGISTRY).items():
            self.builder.register_service(name, fn)
```

---

## Functional Units (for PR Breakdown)

1. **Unit 1:** Schema migration + `@register_tool_type` + `WebhookTool` (`feat/SPEC-056-registry`)
2. **Unit 2:** `ToolResolverService` + workflow tool injection fixes (`feat/SPEC-056-tools`)
3. **Unit 3:** Data-driven approval tiers (`feat/SPEC-056-tiers`)
4. **Unit 4:** `agent_tools.status` + service registry extensibility (`feat/SPEC-056-status`)
5. **Unit 5:** Tests + integration (`feat/SPEC-056-tests`)

Merge order: 1 → 3 → 4 → 2 → 5

---

## Edge Cases

- **Missing `approval_tier` for custom tools:** Default to `requires_approval` (fail-safe).
- **Status column NULL after migration:** Treated as `granted` for backward compatibility.
- **WebhookTool with invalid config:** Returns error string; does not raise unhandled exception.
- **ToolResolverService called for agent with no tools:** Returns empty lists; workflow runs as pure LLM.
- **Circular dependency between registry and tool classes:** Registry module must not import tool classes at module level. Tool classes import registry.

---

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-17)
- [x] Every AC maps to at least one functional unit
- [x] Cross-domain boundaries: schema → backend → workflow engine
- [x] Security boundary explicit (no dynamic class loading)
- [x] Merge order explicit and acyclic
- [x] Out-of-scope explicit
- [x] Edge cases documented
- [x] Testing requirements map to ACs
