# SPEC-044: Bwrap Sandbox Backend -- OS-Level Agent Isolation

> **Status:** Approved
> **Author:** Claude (spec-writer) + Tim (architecture direction)
> **Created:** 2026-04-09
> **Updated:** 2026-04-09
> **Supersedes:** SPEC-038 (bwrap Sandbox Provisioning), SPEC-039 (Security Boundary), SPEC-040 (Introspection Loop), SPEC-041 (Sandbox Wiring), SPEC-042 (Sandbox Config Authority)
> **Builds on:** SPEC-043 (Deep Agents Runtime -- implemented)
> **References:** Deep Agents `BaseSandbox` API (`.claude/skills/deep-agents/references/sandboxes.md`, `backends.md`)

---

## Goal

Replace the `ClarityBackend` / `ConfigService` runtime with a `BwrapBackend` that extends `deepagents.backends.sandbox.BaseSandbox`, giving every user's agent a real POSIX filesystem with OS-level namespace isolation via bubblewrap. This eliminates Supabase Storage as the hot path for every file read/write, replaces ~1,500 LOC of dead sandbox plumbing (SPECs 038-041) with ~150 LOC of adapter code, and gives the agent an `execute` tool for running bash commands inside the sandbox.

**Why this matters:** The current `ClarityBackend` implements all 6 `BackendProtocol` methods by calling Supabase Storage over HTTP on every operation -- slow, complex, and no isolation between users. `BaseSandbox` implements all 6 by delegating to a single `execute()` method that runs shell commands. Our existing `BwrapSandbox` class already has the bwrap subprocess logic. The new `BwrapBackend` is a thin adapter (~80-100 LOC) that wires `BwrapSandbox.execute()` to `BaseSandbox.execute()` and adds `upload_files()`/`download_files()` via direct host filesystem access through the bind mount.

**What the agent gains:**
- `execute` tool -- run bash commands inside the sandbox (system utilities, grep, python3)
- Kernel-enforced read-only `/system/` -- no SecurityBoundary class needed, the mount namespace prevents writes
- Per-user filesystem at `/user/` -- bind-mounted from `/data/sandboxes/{user_id}/`
- All BaseSandbox file tools (ls, read, write, edit, grep, glob) -- implemented via `execute()`, running `python3` and `grep` inside the namespace

---

## Acceptance Criteria

### FU-1: BwrapBackend (BaseSandbox subclass)

- [ ] **AC-01:** A `BwrapBackend` class in `chatServer/sandbox/bwrap_backend.py` extends `deepagents.backends.sandbox.BaseSandbox`. It implements the 4 abstract members: `execute()`, `upload_files()`, `download_files()`, and `id` property. All 6 `BackendProtocol` file operations (ls, read, write, edit, grep, glob) are inherited from `BaseSandbox` and require no custom implementation. [A14, A11]

- [ ] **AC-02:** `BwrapBackend.__init__` accepts `user_dir: Path`, `system_dir: Path`, and optionally `bwrap_path: str` (default: `"bwrap"`). It does NOT accept `tools_dir` -- tools run server-side via Python, not as CLI binaries inside bwrap. [A14]

- [ ] **AC-03:** `BwrapBackend.execute(command, *, timeout=None)` runs the command inside a bwrap namespace with `--unshare-all --die-with-parent --ro-bind {system_dir} /system --bind {user_dir} /user --tmpfs /tmp --dev /dev --proc /proc --chdir /user`. Returns `ExecuteResponse(output, exit_code, truncated)`. The method is synchronous (as required by BaseSandbox). Uses `subprocess.run()` with `capture_output=True` and `timeout` parameter. [A14]

- [ ] **AC-04:** `BwrapBackend.execute()` combines stdout and stderr into `ExecuteResponse.output`. Output is truncated at 1MB with `truncated=True` flag set. Timeout defaults to 120 seconds when not specified. Timed-out commands return exit_code=-1 with output `"[timed out]"`. [A14]

- [ ] **AC-05:** `BwrapBackend.upload_files(files)` writes files directly to the host filesystem at the paths relative to `user_dir` (which is bind-mounted into the namespace at `/user/`). Creates parent directories as needed. Returns `list[FileUploadResponse]` with per-file success/error. [A14]

- [ ] **AC-06:** `BwrapBackend.download_files(paths)` reads files from the host filesystem. Paths starting with `/user/` map to `user_dir`; paths starting with `/system/` map to `system_dir`. Returns `list[FileDownloadResponse]` with per-file content or error. [A14]

- [ ] **AC-07:** `BwrapBackend.id` returns a deterministic string based on the user_dir path (e.g., `"bwrap:{user_dir}"`). [A14]

- [ ] **AC-08:** Python3 is available inside the bwrap namespace via `--ro-bind /usr /usr` (bind-mounts the host's `/usr` directory read-only). This is required because BaseSandbox's read, write, edit, and glob operations run `python3 -c "..."` inside the sandbox. `/bin` and `/lib` are also bind-mounted read-only for shell and shared libraries. [A14]

- [ ] **AC-09:** Unit tests in `tests/chatServer/sandbox/test_bwrap_backend.py` cover: execute returns correct ExecuteResponse format, execute handles timeout, upload_files writes to host filesystem, download_files reads from host filesystem, id property format. All tests mock `subprocess.run` -- no real bwrap needed. [S1]

### FU-2: Storage Sync Utility

- [ ] **AC-10:** A `StorageSync` class in `chatServer/services/storage_sync.py` provides three async methods: `hydrate_user(user_id)`, `sync_file(user_id, relative_path)`, and `pull_system()`. Uses Supabase Storage client directly (no ConfigService dependency). [A1, A14]

- [ ] **AC-11:** `hydrate_user(user_id)` downloads all files from Supabase Storage bucket `config` at prefix `users/{user_id}/` to `/data/sandboxes/{user_id}/`. Creates directories as needed. No-ops if the target directory already has files (local disk is source of truth once populated). [A14]

- [ ] **AC-12:** `pull_system()` downloads all files from Supabase Storage bucket `config` at prefix `system/` to `/data/config/system/`. Overwrites existing files (system config is authoritative from Storage). [A14]

- [ ] **AC-13:** `sync_file(user_id, relative_path)` uploads a single file from `/data/sandboxes/{user_id}/{relative_path}` to Supabase Storage at `users/{user_id}/{relative_path}`. Fire-and-forget -- logs WARNING on failure but never raises. [A14]

- [ ] **AC-14:** A `scripts/pull_config.py` CLI script calls `pull_system()` (no args) or `hydrate_user(user_id)` (with `--user USER_ID`). Requires `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` env vars. [A14]

- [ ] **AC-15:** Unit tests in `tests/chatServer/services/test_storage_sync.py` cover: hydrate downloads files to correct paths, hydrate skips when dir has content, pull_system overwrites, sync_file uploads correctly, sync_file logs on failure. All tests mock the Supabase storage client. [S1]

### FU-3: System Skill Seeding

- [ ] **AC-16:** Content from `agent_configurations.soul` column is extracted and written to Supabase Storage at `system/skills/clarity-soul/SKILL.md` with YAML frontmatter (`name`, `description`). [A2]

- [ ] **AC-17:** Content from `agent_configurations.identity` column (JSON) is extracted, formatted as markdown, and written to `system/skills/clarity-identity/SKILL.md`. [A2]

- [ ] **AC-18:** Safety guidelines, tool guidance, operating model, and channel guidance content from the existing `prompt_builder.py` constants are written as separate skill files: `system/skills/safety-guidelines/SKILL.md`, `system/skills/tool-guidance/SKILL.md`, `system/skills/operating-model/SKILL.md`, `system/skills/channel-guidance/SKILL.md`. [A2]

- [ ] **AC-19:** Existing `user_agent_prompt_customizations` rows are converted to user-layer skill files at `users/{user_id}/skills/communication-preferences/SKILL.md` in Supabase Storage. [A13]

- [ ] **AC-20:** A `scripts/seed_system_skills.py` script performs all seeding. Idempotent (uses upsert via `file_options={"upsert": "true"}`). Can be run multiple times safely. [S1]

- [ ] **AC-21:** After seeding completes, `pull_system()` is called to populate `/data/config/system/` on the local host, making skills available to bwrap namespaces immediately. [A14]

### FU-4: Builder Integration + Dead Code Cleanup

- [ ] **AC-22:** `deep_agent_builder.py` section 5 ("Create ClarityBackend") is replaced with BwrapBackend construction: `BwrapBackend(user_dir=Path(f"/data/sandboxes/{user_id}"), system_dir=Path("/data/config/system"))`. The 25-line try/except fallback is removed. [A1, A14]

- [ ] **AC-23:** Before constructing BwrapBackend, the builder calls `await StorageSync(...).hydrate_user(user_id)` to ensure the user's sandbox directory exists and is populated. [A14]

- [ ] **AC-24:** After the agent turn completes (in the caller -- chat endpoint, telegram handler, scheduled execution), changed files in the user's sandbox dir are synced back to Supabase Storage via `StorageSync.sync_file()`. Detection uses directory mtime comparison (snapshot before invoke, scan after). [A14]

- [ ] **AC-25:** The following files are deleted:
  - `chatServer/services/deep_agent_backend.py` (ClarityBackend -- replaced by BwrapBackend)
  - `chatServer/services/config_service.py` (Supabase Storage overlay -- replaced by StorageSync)
  - `chatServer/sandbox/security_boundary.py` (path classification -- bwrap mount namespace handles this)
  - `chatServer/sandbox/self_improvement.py` (proposal/approval flow -- killing for now)
  - `chatServer/sandbox/git_tracker.py` (git versioning -- killing for now)
  - `chatServer/sandbox/disclosure.py` (disclosure model -- killing)
  - `chatServer/sandbox/changelog.py` (change logging -- killing)
  - `chatServer/sandbox/credential_injector.py` (credential injection -- killing)
  - `chatServer/sandbox/sync.py` (old sync service -- replaced by StorageSync)
  - `chatServer/sandbox/provisioner.py` (old provisioner -- replaced by StorageSync.hydrate_user)
  - `chatServer/sandbox/hydrator.py` (old hydrator -- replaced by StorageSync.hydrate_user)
  - `chatServer/sandbox/models.py` (CommandResult etc. -- BwrapBackend uses ExecuteResponse)
  - `chatServer/services/langchain_tool_bridge.py` (dead code -- Deep Agents accepts BaseTool natively)
  - `chatServer/services/prompt_builder.py` (content extracted to skill files in FU-3)
  - `scripts/seed_skills.py` (replaced by seed_system_skills.py)
  - `chatServer/workflows/nodes/gather_metrics.py` (introspection loop -- killing)
  - `chatServer/workflows/nodes/apply_improvements.py` (introspection loop -- killing)
  - `chatServer/workflows/templates/introspection.py` (introspection loop -- killing)
  - `chatServer/routers/introspection_router.py` (introspection loop -- killing)
  - All associated test files for deleted source files [A14]

- [ ] **AC-26:** `chatServer/main.py` lifespan changes:
  - Remove `initialize_config_service()` and `shutdown_config_service()` calls
  - Remove `initialize_provisioner()` and `shutdown_provisioner()` calls
  - Remove `initialize_template_registry(get_config_service())` call
  - Remove introspection router registration (`app.include_router(introspection_router)`)
  - Add: on startup, if `/data/config/system/` is empty or missing, call `StorageSync.pull_system()` [A14]

- [ ] **AC-27:** `chatServer/services/background_tasks.py` removes the `handle_introspection` handler registration. `chatServer/services/job_handlers.py` removes the `handle_introspection` function. [A14]

- [ ] **AC-28:** `chatServer/channels/telegram_bot.py` proposal approval/rejection callbacks are updated to remove references to SecurityBoundary, SelfImprovementService, DisclosureModel, GitTracker, SyncService, and get_provisioner. The proposal flow is removed entirely (consistent with killing self_improvement.py). [A14]

- [ ] **AC-29:** `chatServer/routers/proposals.py` is deleted (proposal approval API -- no longer needed without self-improvement flow). Its router registration in `main.py` is removed. [A14]

- [ ] **AC-30:** `chatServer/sandbox/__init__.py` is updated to export only `BwrapBackend` and `BwrapSandbox`. [A14]

- [ ] **AC-31:** `chatServer/sandbox/bwrap.py` removes the `tools_dir` constructor parameter and the `--ro-bind tools /tools` mount from `_build_bwrap_args()`. Tools run server-side via Python, not as CLI binaries inside bwrap. [A14]

- [ ] **AC-32:** `chatServer/workflows/registry.py` and `chatServer/workflows/prompt_loader.py` are updated to read templates from local disk (`/data/config/system/`) instead of ConfigService. The `initialize_template_registry(config_service)` function is replaced with `initialize_template_registry(system_dir: Path)`. `chatServer/workflows/templates/seed.py` is updated to write template files to local disk (or removed if templates are seeded via `pull_system()` from Storage). [A14]

- [ ] **AC-33:** All imports of deleted modules are removed from all files in `chatServer/`. Verified by `ruff check` passing with no import errors. [S1]

### FU-5: Dockerfile + Fly.io Deployment

- [ ] **AC-34:** `chatServer/Dockerfile` installs `bubblewrap` package via `apt-get install -y bubblewrap`. [A14]

- [ ] **AC-35:** `chatServer/Dockerfile` creates `/data/config/system/` and `/data/sandboxes/` directories. [A14]

- [ ] **AC-36:** `BWRAP_ENABLED` environment variable (default: `true` in Docker, `false` locally) gates sandbox functionality. When `false`, `deep_agent_builder.py` passes `backend=None` to `create_deep_agent()` (same fallback as current failure path). When `true`, constructs BwrapBackend. [A14]

- [ ] **AC-37:** A `scripts/verify_bwrap.sh` script tests bwrap functionality: creates a minimal namespace, writes to rw mount, verifies ro mount rejects writes, verifies host filesystem not visible. Exits 0/1 with diagnostic output. [S1]

- [ ] **AC-38:** Integration tests for sandbox functionality are gated behind `@pytest.mark.sandbox` marker that checks for bwrap availability. CI runs these tests only on Linux with bwrap installed. `conftest.py` gets the marker registration. [S1]

---

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/sandbox/bwrap_backend.py` | `BwrapBackend(BaseSandbox)` -- adapter, ~80-100 LOC |
| `chatServer/services/storage_sync.py` | `StorageSync` -- thin Supabase Storage utility, ~60 LOC |
| `scripts/pull_config.py` | CLI to pull system/user config from Storage |
| `scripts/seed_system_skills.py` | Extract DB content to Storage skill files |
| `scripts/verify_bwrap.sh` | Host bwrap verification script |
| `tests/chatServer/sandbox/test_bwrap_backend.py` | BwrapBackend unit tests |
| `tests/chatServer/services/test_storage_sync.py` | StorageSync unit tests |
| `tests/integration/test_bwrap_sandbox.py` | Integration tests (`@sandbox` marker) |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/deep_agent_builder.py` | Replace ClarityBackend with BwrapBackend construction (section 5) |
| `chatServer/main.py` | Remove ConfigService/provisioner/introspection init; add system config pull |
| `chatServer/services/background_tasks.py` | Remove `handle_introspection` registration |
| `chatServer/services/job_handlers.py` | Remove `handle_introspection` function |
| `chatServer/channels/telegram_bot.py` | Remove proposal approval/rejection flow |
| `chatServer/sandbox/__init__.py` | Update exports |
| `chatServer/sandbox/bwrap.py` | Remove tools_dir parameter and /tools mount |
| `chatServer/Dockerfile` | Install bubblewrap, create /data/ dirs |
| `chatServer/workflows/registry.py` | Replace ConfigService with local disk reads |
| `chatServer/workflows/prompt_loader.py` | Replace ConfigService with local disk reads |
| `chatServer/workflows/templates/seed.py` | Update or remove (templates seeded via pull_system) |
| `chatServer/config/settings.py` | Add `BWRAP_ENABLED` setting |

### Files to Delete

| File | Reason |
|------|--------|
| `chatServer/services/deep_agent_backend.py` | ClarityBackend replaced by BwrapBackend |
| `chatServer/services/config_service.py` | Supabase Storage overlay replaced by StorageSync |
| `chatServer/sandbox/security_boundary.py` | Kernel-enforced mount namespace replaces this |
| `chatServer/sandbox/self_improvement.py` | Killing proposal/approval flow |
| `chatServer/sandbox/git_tracker.py` | Killing git versioning |
| `chatServer/sandbox/disclosure.py` | Killing disclosure model |
| `chatServer/sandbox/changelog.py` | Killing change logging |
| `chatServer/sandbox/credential_injector.py` | Killing credential injection |
| `chatServer/sandbox/sync.py` | Replaced by StorageSync |
| `chatServer/sandbox/provisioner.py` | Replaced by StorageSync.hydrate_user |
| `chatServer/sandbox/hydrator.py` | Replaced by StorageSync.hydrate_user |
| `chatServer/sandbox/models.py` | BwrapBackend uses ExecuteResponse from deepagents |
| `chatServer/services/langchain_tool_bridge.py` | Dead code |
| `chatServer/services/prompt_builder.py` | Content moves to skill files |
| `scripts/seed_skills.py` | Replaced by seed_system_skills.py |
| `chatServer/workflows/nodes/gather_metrics.py` | Introspection loop killed |
| `chatServer/workflows/nodes/apply_improvements.py` | Introspection loop killed |
| `chatServer/workflows/templates/introspection.py` | Introspection loop killed |
| `chatServer/routers/introspection_router.py` | Introspection loop killed |
| `chatServer/routers/proposals.py` | Proposal flow killed |
| All associated test files | Tests for deleted code |

### Out of Scope

- **Network isolation inside sandbox.** Using `--share-net` (if needed) or no network. BaseSandbox file operations don't need network.
- **Resource limits (cgroups).** CPU/memory limits for sandbox processes. Future optimization.
- **Self-improvement / proposal flow.** Killed entirely. Agent can write to `/user/` directly. Approval flow is a future rebuild.
- **Git versioning of user config.** Killed. Simple file writes for now. Git tracking is a future addition.
- **Introspection loop.** Killed entirely. Rebuild as a simpler workflow when needed.
- **Persistent disk sizing / provisioning.** Infrastructure concern, not application code.
- **Concurrent session handling.** Single session per user is the current model. Locking is future scope.
- **Config browser API.** Frontend for browsing sandbox files. Separate spec.

---

## Technical Approach

### 1. BwrapBackend Architecture

`BaseSandbox` does the heavy lifting. It implements all 6 BackendProtocol methods by running shell commands via `execute()`. Our `BwrapBackend` only needs to implement 4 things:

```python
from deepagents.backends.sandbox import BaseSandbox
from deepagents.backends.protocol import (
    ExecuteResponse, FileUploadResponse, FileDownloadResponse,
)

class BwrapBackend(BaseSandbox):
    def __init__(self, user_dir: Path, system_dir: Path, bwrap_path: str = "bwrap"):
        self._user_dir = user_dir
        self._system_dir = system_dir
        self._bwrap_path = bwrap_path

    def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse:
        """Run command inside bwrap namespace. Synchronous (subprocess.run)."""
        bwrap_args = [
            self._bwrap_path, "--unshare-all", "--die-with-parent",
            "--ro-bind", str(self._system_dir), "/system",
            "--bind", str(self._user_dir), "/user",
            "--ro-bind", "/usr", "/usr",     # python3, coreutils
            "--ro-bind", "/bin", "/bin",      # /bin/sh
            "--ro-bind", "/lib", "/lib",      # shared libs
            "--ro-bind", "/lib64", "/lib64",  # shared libs (64-bit)
            "--tmpfs", "/tmp",
            "--dev", "/dev", "--proc", "/proc",
            "--chdir", "/user",
            "--", "/bin/sh", "-c", command,
        ]
        try:
            result = subprocess.run(
                bwrap_args, capture_output=True,
                timeout=timeout or 120, text=True,
            )
            output = self._truncate(result.stdout + result.stderr)
            return ExecuteResponse(
                output=output, exit_code=result.returncode,
                truncated=len(output) >= _MAX_OUTPUT,
            )
        except subprocess.TimeoutExpired:
            return ExecuteResponse(output="[timed out]", exit_code=-1)

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        """Write directly to host filesystem (bind-mounted into namespace)."""
        # Map /user/... paths to user_dir, /system/... to system_dir
        ...

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """Read from host filesystem."""
        ...

    @property
    def id(self) -> str:
        return f"bwrap:{self._user_dir}"
```

**Key design decision: sync `execute()`.** `BaseSandbox.execute()` is sync. The `aexecute()` default does `asyncio.to_thread(self.execute)`, so it runs in a thread pool. Using `subprocess.run()` (blocking) is correct here -- it runs in the thread that `to_thread` gives us. This is simpler and more reliable than the current `ClarityBackend._run_async()` hack that spawns a `ThreadPoolExecutor` to bridge async/sync.

**Key design decision: bind-mount `/usr`, `/bin`, `/lib`.** BaseSandbox's `read`, `write`, `edit`, and `glob` all run `python3 -c "..."` inside the sandbox. The `grep` implementation uses `/usr/bin/grep`. These must be available inside the namespace. Read-only bind-mounts of the host's system directories provide them without copying anything.

### 2. Storage Sync

Thin utility with no overlay logic, no caching. Just download/upload to Supabase Storage:

```python
class StorageSync:
    def __init__(self, supabase_client, data_dir: Path = Path("/data")):
        self._storage = supabase_client.storage
        self._data_dir = data_dir
    
    async def hydrate_user(self, user_id: str) -> None:
        """Download user files from Storage to local sandbox dir."""
        target = self._data_dir / "sandboxes" / user_id
        if any(target.iterdir()) if target.exists() else False:
            return  # Already populated
        ...
    
    async def pull_system(self) -> None:
        """Download system config from Storage to local config dir."""
        ...
    
    async def sync_file(self, user_id: str, relative_path: str) -> None:
        """Upload a changed file back to Storage (fire-and-forget)."""
        ...
```

### 3. Skill Seeding

Extract content from database and `prompt_builder.py` into SKILL.md files with YAML frontmatter:

```markdown
---
name: clarity-soul
description: Core behavioral philosophy -- personality, values, interaction style
---

# Clarity Soul

[content from agent_configurations.soul column]
```

### 4. Dead Code Removal Strategy

The deletion list is large but the dependency graph is clean:

1. `ClarityBackend` is only imported in `deep_agent_builder.py` -- replace import
2. `ConfigService` is imported in `main.py` (init/shutdown), `provisioner.py`, `hydrator.py`, `sync.py`, `prompt_loader.py`, `registry.py`, `telegram_bot.py` -- all either deleted or modified
3. Sandbox modules (`security_boundary`, `self_improvement`, `disclosure`, `git_tracker`, etc.) are imported by each other and by `deep_agent_builder.py`, `telegram_bot.py`, `proposals.py`, `apply_improvements.py` -- cascade through deletion
4. Introspection files (`gather_metrics`, `apply_improvements`, `introspection.py` template, `introspection_router`) -- referenced in `main.py`, `background_tasks.py`, `job_handlers.py` -- clean removal

The `workflows/` engine itself (`registry.py`, `run_manager.py`, `dispatch.py`, `prompt_loader.py`, `graph_builder.py`) stays but loses the `introspection` template. `prompt_loader.py` and `registry.py` need their `config_service` dependency updated or removed.

### 5. Deployment

Dockerfile changes are minimal: `apt-get install -y bubblewrap` and `mkdir -p /data/config/system /data/sandboxes`. Fly Machines run Firecracker VMs with full Linux kernels that support user namespaces.

### Dependencies

| Dependency | What It Provides | Status |
|-----------|-----------------|--------|
| SPEC-043 (Deep Agents Runtime) | `create_deep_agent()`, `BaseSandbox` integration | Implemented |
| `deepagents` v0.5.0 | `BaseSandbox`, `ExecuteResponse`, `BackendProtocol` | Installed |
| `bwrap` binary | Bubblewrap sandbox creation | System package |
| Unprivileged user namespaces | `kernel.unprivileged_userns_clone=1` | Kernel config |
| Supabase Storage | Durable config storage (cold path) | Available |

---

## Blast Radius

### Direct Impact

| Component | Impact | Risk |
|-----------|--------|------|
| `chatServer/services/deep_agent_builder.py` | Modified: section 5 replaced | **Medium** -- core agent construction path |
| `chatServer/main.py` | Modified: lifespan cleanup | **Medium** -- startup/shutdown ordering |
| `chatServer/channels/telegram_bot.py` | Modified: proposal flow removed | **Low** -- removing dead flow |
| `chatServer/Dockerfile` | Modified: install bubblewrap | **Low** -- one apt-get |
| 20+ files deleted | Deleted: dead code cleanup | **Low** -- no callers outside the deletion set |

### Indirect Impact

| Component | Impact | Risk |
|-----------|--------|------|
| `chatServer/workflows/` | Loses introspection template + ConfigService dependency | **Medium** -- `prompt_loader.py` and `registry.py` need ConfigService removed |
| `chatServer/routers/proposals.py` | Deleted | **Low** -- proposal API has no frontend callers |
| Agent file tools | Now run shell commands in bwrap instead of HTTP to Storage | **High** -- behavioral change, needs verification |
| Supabase Storage bucket `config` | Becomes cold-path backup, not hot-path runtime | **Low** -- data stays, access pattern changes |

### Services That Touch Deleted Code

| Service | Current Use | After This Spec |
|---------|-------------|-----------------|
| `deep_agent_builder.py` | Imports ClarityBackend, SecurityBoundary, SelfImprovementService, DisclosureModel, ConfigService | Imports BwrapBackend, StorageSync |
| `telegram_bot.py` | Proposal approve/reject callbacks | Callbacks removed |
| `main.py` lifespan | ConfigService init/shutdown, provisioner init/shutdown | StorageSync.pull_system on startup |
| `background_tasks.py` | Introspection job handler | Handler removed |

---

## Testing Requirements

### Unit Tests (required)

| Test File | Covers | Maps to AC |
|-----------|--------|-----------|
| `tests/chatServer/sandbox/test_bwrap_backend.py` | execute(), upload_files(), download_files(), id, timeout | AC-01 to AC-09 |
| `tests/chatServer/services/test_storage_sync.py` | hydrate_user(), pull_system(), sync_file() | AC-10 to AC-15 |
| `tests/chatServer/services/test_deep_agent_builder.py` | Updated to test BwrapBackend construction | AC-22, AC-23 |

### Integration Tests (gated)

| Test File | Covers | Marker |
|-----------|--------|--------|
| `tests/integration/test_bwrap_sandbox.py` | Full bwrap: mount verification, ro/rw, execute, python3 availability | `@pytest.mark.sandbox` |

### AC-to-Test Mapping

| AC | Test | Type |
|----|------|------|
| AC-01 | `test_bwrap_backend_extends_base_sandbox` | Unit |
| AC-02 | `test_bwrap_backend_init_params` | Unit |
| AC-03 | `test_execute_runs_in_namespace` | Unit (mock subprocess) |
| AC-04 | `test_execute_combines_stdout_stderr`, `test_execute_truncates_output`, `test_execute_timeout` | Unit |
| AC-05 | `test_upload_files_writes_to_user_dir` | Unit |
| AC-06 | `test_download_files_reads_user_and_system` | Unit |
| AC-07 | `test_id_property` | Unit |
| AC-08 | `test_python3_available_in_namespace` | Integration (`@sandbox`) |
| AC-10 | `test_hydrate_user_downloads_files` | Unit (mock Storage) |
| AC-11 | `test_hydrate_skips_populated_dir` | Unit |
| AC-12 | `test_pull_system_overwrites` | Unit (mock Storage) |
| AC-13 | `test_sync_file_uploads`, `test_sync_file_logs_on_failure` | Unit (mock Storage) |
| AC-22 | `test_builder_creates_bwrap_backend` | Unit |
| AC-25 | Verified by `ruff check` + `pytest --collect-only` passing | CI |
| AC-32 | `test_template_registry_reads_from_disk` | Unit |
| AC-34 | `scripts/verify_bwrap.sh` runs in Docker build | Integration |

### Manual Verification (UAT)

- [ ] Run `pnpm dev`, send a chat message, verify agent responds (basic functionality preserved)
- [ ] Check chatserver logs for "Built deep agent" with "BwrapBackend" (not "ClarityBackend")
- [ ] Verify no import errors in logs on startup
- [ ] Verify `scripts/verify_bwrap.sh` passes on deployment target

---

## Edge Cases

1. **bwrap binary not found.** `subprocess.run` raises `FileNotFoundError`. `BwrapBackend.execute()` catches and returns `ExecuteResponse(output="bwrap not found", exit_code=-1)`. When `BWRAP_ENABLED=false`, BwrapBackend is never constructed.

2. **User sandbox dir doesn't exist.** `hydrate_user()` creates it. If Storage is empty too (new user), an empty directory is created -- the agent starts with system skills only.

3. **Supabase Storage unreachable during hydration.** `hydrate_user()` raises -- the builder catches and falls back to `backend=None` (agent works without file tools, same as today's failure path).

4. **Agent writes to `/system/` inside bwrap.** Kernel rejects the write (`--ro-bind`). BaseSandbox returns an error result. The agent sees a permission error and should understand the path is read-only.

5. **Large file output.** `execute()` truncates at 1MB (matches existing bwrap.py behavior). `ExecuteResponse.truncated` is set to `True`.

6. **Python3 not available in bwrap.** If `/usr/bin/python3` doesn't exist on the host, BaseSandbox's file operations fail with "python3: not found". The Dockerfile must ensure Python is installed (it already is -- `python:3.12-slim-bullseye` base image).

7. **Concurrent `hydrate_user()` calls for same user.** Both write to the same directory. File writes are atomic at the OS level. Second call no-ops because directory already has content.

8. **`/lib64` doesn't exist on some architectures.** The bwrap arg builder should conditionally include `--ro-bind /lib64 /lib64` only if `/lib64` exists on the host.

9. **Fly Machine replacement.** Local disk is lost. On next startup, `pull_system()` repopulates system config. User dirs are rehydrated from Storage on next session. In-flight writes from the previous machine are lost -- acceptable for MVP.

---

## Functional Units

### FU-1: BwrapBackend (BaseSandbox subclass)

**ACs:** AC-01 through AC-09
**Branch:** `feat/SPEC-044-bwrap-backend`
**Domain:** backend-dev
**Creates:** `chatServer/sandbox/bwrap_backend.py`, `tests/chatServer/sandbox/test_bwrap_backend.py`
**Modifies:** `chatServer/sandbox/bwrap.py` (remove tools_dir), `chatServer/sandbox/__init__.py`
**Dependencies:** None -- standalone

### FU-2: Storage Sync Utility

**ACs:** AC-10 through AC-15
**Branch:** `feat/SPEC-044-storage-sync`
**Domain:** backend-dev
**Creates:** `chatServer/services/storage_sync.py`, `scripts/pull_config.py`, `tests/chatServer/services/test_storage_sync.py`
**Dependencies:** None -- standalone. Parallelizable with FU-1.

### FU-3: System Skill Seeding

**ACs:** AC-16 through AC-21
**Branch:** `feat/SPEC-044-skill-seeding`
**Domain:** backend-dev
**Creates:** `scripts/seed_system_skills.py`
**Dependencies:** FU-2 (uses StorageSync for pull_system at end)
**Note:** This is a one-time migration script, not ongoing code. The skill files in Storage become the authoritative source after seeding.

### FU-4: Builder Integration + Dead Code Cleanup

**ACs:** AC-22 through AC-33
**Branch:** `feat/SPEC-044-builder-integration`
**Domain:** backend-dev
**Creates:** Nothing
**Modifies:** `deep_agent_builder.py`, `main.py`, `background_tasks.py`, `job_handlers.py`, `telegram_bot.py`, `workflows/registry.py`, `workflows/prompt_loader.py`
**Deletes:** 20+ files (see AC-25, AC-29)
**Dependencies:** FU-1 + FU-2 (needs BwrapBackend and StorageSync to exist)

### FU-5: Dockerfile + Deployment Verification

**ACs:** AC-34 through AC-38
**Branch:** `feat/SPEC-044-deployment`
**Domain:** deployment-dev
**Creates:** `scripts/verify_bwrap.sh`, `tests/integration/test_bwrap_sandbox.py`
**Modifies:** `chatServer/Dockerfile`, `chatServer/config/settings.py`
**Dependencies:** FU-4 (needs builder wired up)

### Merge Order

```
FU-1 ─┬─→ FU-4 ──→ FU-5
FU-2 ─┤
FU-3 ─┘
```

FU-1 and FU-2 can parallelize. FU-3 depends on FU-2. FU-4 depends on FU-1 + FU-2. FU-5 depends on FU-4.

---

## Resolved Decisions

1. **sync `execute()` via `subprocess.run()`.** BaseSandbox requires sync `execute()`. Its `aexecute()` does `asyncio.to_thread(self.execute)`. `BwrapBackend.execute()` is a **new sync implementation** using `subprocess.run()` — it does NOT wrap the existing async `BwrapSandbox.execute()`. The old async method in `bwrap.py` becomes unused; `BwrapBackend` contains its own bwrap arg construction and subprocess invocation. This is simpler and more correct than bridging async/sync.

2. **No git tracking.** User config changes are written to disk and synced to Storage. No git init, no commit tracking. Git is future scope when we rebuild the self-improvement flow.

3. **No self-improvement / proposal flow.** The entire approve/reject/disclose flow is killed. The agent writes directly to `/user/`. Trust model changes are a separate future spec.

4. **Bind-mount host system dirs for Python/coreutils.** Rather than installing a separate Python inside the sandbox or using a custom rootfs, bind-mount `/usr`, `/bin`, `/lib` read-only. This gives the agent access to all host tools but prevents modification. Acceptable security tradeoff for MVP.

5. **Supabase Storage stays as cold backup.** Storage is not removed. System config is managed there and pulled to local disk. User config is hydrated from Storage on first session and synced back after changes. The hot path is local disk, not HTTP.

6. **`BWRAP_ENABLED=false` as local dev default.** Developers without bwrap (macOS, Windows) get the existing `backend=None` fallback. Production defaults to `true`.

---

## Resolved Input Decisions

1. **Workflow engine → local disk (Option A).** `registry.py` and `prompt_loader.py` read templates from `/data/config/system/workflows/` instead of ConfigService. Templates pulled by `pull_system()`. This was the original design intent.

2. **Proposal API (`/api/proposals`).** Frontend review confirmed zero frontend callers — no imports, hooks, or API calls referencing proposals anywhere in `webApp/src/`. Delete the router entirely (AC-29).

3. **`/lib64` — runtime check.** Conditionally include `--ro-bind /lib64 /lib64` only if `/lib64` exists on the host. One `if` statement in `_build_bwrap_args()`.

4. **Post-turn sync — mtime comparison (Option A).** Snapshot directory mtimes before agent turn, scan for changes after. Simple, catches everything.

---

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-38)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (BwrapBackend implements BaseSandbox)
- [x] Technical decisions reference principles from architecture-principles skill
- [x] Merge order is explicit and acyclic
- [x] Out-of-scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
