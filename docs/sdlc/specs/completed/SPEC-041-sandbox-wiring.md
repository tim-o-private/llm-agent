# SPEC-041: Sandbox Wiring — End-to-End Integration

**Status:** In Progress  
**Branch:** feat/SPEC-033-conversation-handler  
**Depends on:** SPEC-038, SPEC-039, SPEC-040 (all on this branch)

## Problem

The bwrap sandbox, self-improvement service, and introspection workflow are implemented but not connected. Four gaps block end-to-end operation:

1. `ConfigService.delete()` missing — `SyncService` calls it (runtime `AttributeError` on file deletion sync)
2. `SelfImprovementService._get_proposal()` is in-memory only — proposals are lost on service restart
3. `SandboxProvisioner` is never instantiated in `main.py` — no sandbox is ever created
4. `apply_improvements.py` is a logging stub — proposals are never executed in the sandbox

## Goals

1. Fix `ConfigService.delete()` (blocking bug in `SyncService`)
2. Fix `SelfImprovementService._get_proposal()` DB fallback (restart safety)
3. Wire `SandboxProvisioner` into the app lifecycle (`main.py`)
4. Replace `apply_improvements.py` stub with real sandbox execution

## Out of Scope

- Per-session sandbox provisioning (normal conversations don't need the sandbox)
- UI for approving/rejecting proposals (existing notification flow handles this)
- Sandbox wiring into `ConversationHandler` (sandbox is workflow-only for now)

---

## FU-1: ConfigService.delete() + SelfImprovementService DB Fallback

**Files modified:**
- `chatServer/services/config_service.py`
- `chatServer/sandbox/self_improvement.py`
- `tests/chatServer/services/test_config_service.py`
- `tests/chatServer/sandbox/test_self_improvement.py`

**Acceptance Criteria:**

- `ConfigService` has an async `delete(path: str, user_id: str) -> None` method
  - Deletes `users/{user_id}/{path}` from the `config` bucket via Supabase Storage `.remove()`
  - Busts cache for that path (`_cache.pop(user_full, None)`)
  - Silently returns on 404 (file already gone)
  - Raises `StorageApiError` on all other errors
- `SelfImprovementService._get_proposal()` falls back to DB query when proposal not in `self._proposals`
  - Queries `config_change_proposals` table: `eq("id", proposal_id)`
  - If found, deserializes row into `ChangeProposal` and caches in `self._proposals`
  - If no DB client, returns `None` (existing in-memory-only behavior preserved)
- Tests:
  - `delete()` success path — Storage `.remove()` called with correct path, cache busted
  - `delete()` 404 — silent return, no exception
  - `delete()` non-404 error — exception propagated
  - `_get_proposal()` DB fallback — returns proposal from DB when not in memory
  - `_get_proposal()` DB miss — returns `None`
  - `_get_proposal()` no DB client — returns `None`

---

## FU-2: SandboxProvisioner App Lifecycle Wiring

**Files modified:**
- `chatServer/config/settings.py`
- `chatServer/sandbox/provisioner.py`
- `chatServer/main.py`
- `tests/chatServer/sandbox/test_provisioner.py`

**Acceptance Criteria:**

- `settings.py` has four new fields (pydantic `Field` with env var binding):
  - `BWRAP_ENABLED: bool = False`
  - `BWRAP_BASE_PATH: str = "/data/sandboxes"`
  - `BWRAP_SYSTEM_PATH: str = "/data/sandbox-system"`
  - `BWRAP_BINARY: str = "bwrap"`
- `provisioner.py` adds global instance management (identical pattern to `config_service.py`):
  - `_provisioner: Optional[SandboxProvisioner] = None`
  - `get_provisioner() -> SandboxProvisioner` — raises `RuntimeError` if not initialized
  - `initialize_provisioner(config_service=None) -> None` — builds `SandboxConfig` from settings, creates global `SandboxProvisioner`
  - `shutdown_provisioner() -> None` — calls `destroy_all()`, sets global to `None`
- `main.py` lifespan:
  - After `initialize_config_service()`: calls `await initialize_provisioner(config_service=get_config_service())`
  - Shutdown: calls `await shutdown_provisioner()` (guarded with `try/except`)
- When `BWRAP_ENABLED=false` (default): provisioner initializes, but `.provision()` raises `SandboxNotAvailableError` — callers catch this and degrade gracefully
- Tests:
  - `initialize_provisioner()` sets global, `get_provisioner()` returns it
  - `shutdown_provisioner()` calls `destroy_all()`, clears global
  - `get_provisioner()` before init raises `RuntimeError`

---

## FU-3: apply_improvements.py — Real Sandbox Execution

**Files modified:**
- `chatServer/workflows/nodes/apply_improvements.py`
- `chatServer/sandbox/self_improvement.py`
- `tests/chatServer/workflows/test_apply_improvements.py`
- `tests/chatServer/sandbox/test_self_improvement.py`

**Acceptance Criteria:**

- `apply_improvements.py` removes the MVP logging stub and:
  1. Imports and calls `get_provisioner()` — catches `RuntimeError` (not initialized) and `SandboxNotAvailableError`; returns `{"status": "sandbox_unavailable", "applied": [], "skipped": [], "failed": []}` on either
  2. Calls `provisioner.get_or_create(user_id)` to get a `BwrapSandbox`
  3. Constructs `GitTracker(user_dir)` from the sandbox's `_user_dir`
  4. Constructs `SelfImprovementService(security_boundary, disclosure_model, notification_service, db_client)` — pulls from workflow state context where available
  5. For each proposal in `state["proposals"]`:
     - Writes `proposal["content"]` to `user_dir / proposal["file_path"].lstrip("/")`
     - Calls `await service.propose_change(user_id, git_tracker, file_path, content, description, trust_tier)`
     - Appends to `applied` or `failed` list based on result
  6. Returns `{"status": "ok", "applied": [...], "skipped": [...], "failed": [...]}`
- `SelfImprovementService.approve_change()` calls `SyncService.sync_to_storage()` after marking approved (if `_sync_service` injected)
  - `SelfImprovementService.__init__` accepts optional `sync_service` parameter
- Tests mock `get_provisioner()` — do not require bwrap binary
- Tests cover:
  - Normal execution: proposals applied, results returned
  - `SandboxNotAvailableError`: graceful `sandbox_unavailable` response
  - `SyncService` called after `approve_change()`

---

## Verification

```bash
# All sandbox + workflow + config tests
pytest tests/chatServer/sandbox/ tests/chatServer/workflows/ tests/chatServer/services/test_config_service.py -v

# Server starts with BWRAP_ENABLED=false (default) without errors
# Check logs: "SandboxProvisioner initialized (enabled=False)"

# Integration (requires bwrap installed):
BWRAP_ENABLED=true pytest tests/integration/test_bwrap_sandbox.py -v
```
