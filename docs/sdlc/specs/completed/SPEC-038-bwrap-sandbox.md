# SPEC-038: bwrap Sandbox Provisioning

> **Status:** Draft
> **Author:** Claude (Spec Writer)
> **Created:** 2026-04-06
> **Updated:** 2026-04-06
> **PRD:** Architecture Proposal (Phase 3, Item 10)
> **Architecture:** `docs/product/ARCHITECTURE-PROPOSAL-next-gen.md`, Sections Q3 (Phase B), Q5, Phase 3

## Goal

Give each user's agent a real POSIX filesystem via bubblewrap (`bwrap`) Linux namespaces. This is the foundation that makes self-improvement possible — the agent can read and write config files using standard file tools (`cat`, `grep`, `sed`, `git`) instead of throwaway API wrappers. The filesystem has an immutable system layer (kernel-enforced read-only), a mutable user layer (git-versioned), and mounted CLI tool binaries. Credentials are never in the filesystem — they're injected per-subprocess via scoped environment variables.

This spec is **provider-agnostic**: it works anywhere you have unprivileged user namespaces and persistent disk. No Fly-specific or Hetzner-specific logic in application code.

## Background

Today, the agent's config lives in Supabase Storage (SPEC-035). The server reads it at session init and injects it into the prompt. The agent cannot modify its own config — it's read-only from the agent's perspective. This was an intentional design decision: "Don't build throwaway `write_config` API tools. The agent doesn't write config until it has a real filesystem."

Phase 3 is when the agent needs to write. The bwrap sandbox gives it a real filesystem with proper isolation — the same model that works in HQ (Claude Code + filesystem + git), adapted for a multi-tenant server context.

### Why bwrap, Not Docker

- **Lightweight:** Linux namespace sandbox, no daemon, no image layers, no container orchestration. Used by Flatpak — battle-tested.
- **No root required:** Unprivileged user namespaces (`sysctl kernel.unprivileged_userns_clone=1`) let the chatServer process create sandboxes without elevated privileges.
- **Precise mount control:** Read-only bind mounts are kernel-enforced. The agent literally cannot write to `/system/` — it's not a rule, it's physics.
- **No overhead:** No Docker socket, no image pulls, no layer caching. Namespace creation is ~10ms.

### Relationship to Other Specs

| Spec | Relationship |
|------|-------------|
| **SPEC-035** (Config Service) | Supabase Storage remains the backup/sync layer and file browser source. bwrap user trees sync back to Storage on commit. On first provision, the user tree is hydrated from Storage (SPEC-035 config data). |
| **SPEC-036** (Workflow Engine) | Workflows that need filesystem access (introspection loop, SPEC-040) run steps inside the bwrap namespace. The `AnthropicEngine` gains the ability to run tools inside the sandbox. |
| **SPEC-039** (Security Boundary) | Defines what's in `/system/` (immutable) vs `/user/` (mutable). This spec provisions the mounts; SPEC-039 defines the rules. |
| **SPEC-040** (Introspection Loop) | Runs inside the bwrap namespace, reading and writing to `/user/`. Depends on this spec for the filesystem to exist. |
| **SPEC-034** (Capability Gateway) | Gateway gains a `SandboxExecutor` mode: instead of calling tools as Python functions, it can invoke CLI tools inside the bwrap namespace. |

## Dependencies

| Dependency | What It Provides | Status |
|-----------|-----------------|--------|
| SPEC-035 (Config Service) | User config data in Supabase Storage to hydrate from | Draft (in progress) |
| SPEC-033 (Conversation Handler) | Agent tool-loop that invokes tools (now potentially inside sandbox) | Draft (in progress) |
| SPEC-034 (Capability Gateway) | Tool execution layer that routes to sandbox executors | Draft |
| `bwrap` binary | Bubblewrap sandbox creation | System package (`bubblewrap`) |
| Unprivileged user namespaces | `kernel.unprivileged_userns_clone=1` | Kernel config (verify on targets) |
| Persistent disk | Fly volume or block storage for user trees | Infrastructure config |
| `git` binary | Version tracking of user config trees | System package |

## Acceptance Criteria

### FU-1: Filesystem Layout + bwrap Invocation

- [ ] **AC-01:** A `SandboxManager` class in `chatServer/sandbox/manager.py` provides `async provision(user_id: str) -> SandboxContext` that creates (or reattaches to) a bwrap namespace for the given user. Returns a `SandboxContext` with the namespace's PID, mount paths, and methods for running commands inside it. [A1, A14]
- [ ] **AC-02:** The bwrap namespace mounts four paths: `/system/` (read-only bind mount from shared system defaults on disk), `/user/` (read-write bind mount from user's persistent directory), `/tools/` (read-only bind mount for CLI tool binaries — `gog`, search tools, `git`, standard coreutils), `/tmp/` (read-write tmpfs, 256MB limit, cleared on namespace teardown). [A14]
- [ ] **AC-03:** The system defaults directory on disk (`{data_dir}/system/`) is populated from Supabase Storage's `/system/` prefix on server startup. It is shared across all user namespaces as a read-only bind mount. The server refreshes it periodically (every 3600s) or on explicit deploy signal. [A2]
- [ ] **AC-04:** Each user's persistent directory (`{data_dir}/users/{user_id}/`) is a git repository. On first provision for a new user, the directory is created, `git init` is run, and a `.gitignore` (excluding `/tmp/`, `*.pyc`, `__pycache__/`) and initial commit are created. [A14]
- [ ] **AC-05:** The bwrap invocation uses these flags: `--unshare-all` (new namespaces for mount, PID, network, etc.), `--share-net` (allow network for tool invocations — controlled by Capability Gateway, not network namespace), `--die-with-parent` (namespace dies if chatServer process dies), `--ro-bind {system_dir} /system`, `--bind {user_dir} /user`, `--ro-bind {tools_dir} /tools`, `--tmpfs /tmp`, `--dev /dev`, `--proc /proc`. No `--new-session` (allows signal forwarding for cancellation). [A14]
- [ ] **AC-06:** The bwrap binary path is configurable via `BWRAP_PATH` env var (default: `/usr/bin/bwrap`). The `SandboxManager` validates on startup that the binary exists, is executable, and that unprivileged user namespaces are enabled (reads `/proc/sys/kernel/unprivileged_userns_clone`). Startup fails with a clear error if either check fails. [A14]

### FU-2: Hydration + Persistence

- [ ] **AC-07:** On first provision for a user (empty user directory), `SandboxManager` hydrates the user tree from Supabase Storage. It downloads all files from `/users/{user_id}/` in the config bucket and writes them to `{data_dir}/users/{user_id}/`. After hydration, an initial git commit records the state: `"Initial hydration from Supabase Storage"`. [A3]
- [ ] **AC-08:** If the user directory already exists and contains a git repo, hydration is skipped — the local filesystem is the source of truth. The Supabase Storage data is a backup, not the primary. [A14]
- [ ] **AC-09:** A `SyncService` in `chatServer/sandbox/sync.py` provides `async sync_to_storage(user_id: str)` that pushes the current state of the user's config tree to Supabase Storage. It diffs the local tree against the last synced commit (stored as a tag `last-synced`) and uploads only changed files. Deletions are propagated. After sync, the tag is updated. [A3]
- [ ] **AC-10:** `sync_to_storage()` is called automatically after every git commit in the user tree (triggered by a post-commit hook or by the `SandboxManager` after detecting new commits). It is also callable manually via an internal API for forced sync. [A14]
- [ ] **AC-11:** If Supabase Storage is unreachable during sync, the failure is logged at WARNING level and the sync is retried on the next commit. The local git repo is always the source of truth — sync failures don't block agent operations. [A14]
- [ ] **AC-12:** User tree persistence relies on the underlying durable disk (Fly volume / Hetzner block storage). The disk must survive process restarts. If the disk is lost (catastrophic failure), the user tree can be rehydrated from Supabase Storage by deleting the local directory and re-provisioning (AC-07 handles this case). [A14]

### FU-3: Command Invocation Inside Sandbox

- [ ] **AC-13:** `SandboxContext` provides `async run_command(command: str, env: dict[str, str] | None = None, timeout: float = 30.0, cwd: str = "/user") -> CommandResult` that runs a shell command inside the bwrap namespace. Returns `CommandResult(stdout: str, stderr: str, exit_code: int, timed_out: bool)`. [A1]
- [ ] **AC-14:** The `run_command()` method spawns the command as a subprocess inside a fresh bwrap invocation with the same mounts (per-command isolation). Each invocation gets an identical mount layout. [A14]
- [ ] **AC-15:** Environment variables passed to `run_command()` via the `env` parameter are set in the subprocess environment. This is the credential injection mechanism — OAuth tokens are passed as env vars per-invocation, scoped to the specific tool being run. Env vars are never written to the filesystem or included in git commits. [A12]
- [ ] **AC-16:** Command invocation respects the `timeout` parameter. If the command exceeds the timeout, the subprocess is killed (SIGTERM, then SIGKILL after 5s), and `CommandResult.timed_out` is set to `True`. Default timeout is 30 seconds; maximum configurable timeout is 300 seconds. [A14]
- [ ] **AC-17:** stdout and stderr are captured with a 1MB size limit each. If output exceeds the limit, it is truncated with a `[truncated]` marker. This prevents a runaway command from consuming server memory. [A14]

### FU-4: Lifecycle Management

- [ ] **AC-18:** `SandboxManager` maintains a registry of active sandboxes keyed by `user_id`. `provision()` returns the existing `SandboxContext` if one is already active for the user. Only one sandbox per user is active at a time. [A1]
- [ ] **AC-19:** `SandboxContext` provides `async teardown()` that: (1) syncs to Supabase Storage (best-effort), (2) kills any running subprocesses in the namespace, (3) releases the namespace. The user directory on disk is NOT deleted — it persists for the next session. [A14]
- [ ] **AC-20:** Sandbox lifecycle is tied to agent connection lifetime. For interactive sessions (user chatting), the sandbox is provisioned on first tool invocation that needs filesystem access and torn down when the session ends (or after an idle timeout of 30 minutes). For autonomous agents (scheduled workflows), the sandbox lives for the duration of the workflow run. [A14]
- [ ] **AC-21:** On chatServer startup, `SandboxManager` scans `{data_dir}/users/` for existing user directories and verifies git repo integrity (`git fsck --quick`). Corrupted repos are logged at ERROR level but not automatically deleted — manual intervention required. [A14]
- [ ] **AC-22:** On chatServer shutdown (lifespan shutdown hook), all active sandboxes are torn down gracefully: sync, kill subprocesses, release namespaces. A 10-second grace period is allowed for sync operations. [A14]

### FU-5: Capability Gateway Integration

- [ ] **AC-23:** The Capability Gateway (SPEC-034) gains a `SandboxExecutor` mode. When a tool is marked as `execution_mode: "sandbox"` in its definition, the gateway routes invocation to `SandboxContext.run_command()` instead of calling a Python function. The tool's CLI command template is defined in its tool definition file. [A6]
- [ ] **AC-24:** Tool definitions support a `cli_command` field that specifies how to invoke the tool inside the sandbox. Example: `cli_command: "gog gmail search --query '{query}' --max-results {max_results}"`. Parameters from the tool call are interpolated into the command template (with shell escaping via `shlex.quote()`). [A6]
- [ ] **AC-25:** For tools that require credentials (e.g., `gog` for Gmail), the gateway retrieves the user's OAuth token from the token store and passes it as an environment variable (e.g., `GOOGLE_ACCESS_TOKEN`) to the `run_command()` call. The token is never written to the filesystem. [A12]
- [ ] **AC-26:** The `SandboxExecutor` can also invoke the agent's native file tools: `read_file`, `write_file`, `list_files`, `search_files` map to `cat`, standard write operations, `ls`/`find`, and `grep` inside the sandbox respectively. These are internal tools — available to the agent when it has sandbox access, scoped to `/user/` (mutable) and `/system/` (read-only). [A6, A13]
- [ ] **AC-27:** After any `write_file` operation in the sandbox, the gateway checks if the written file is in the `/user/` tree and if so, automatically stages and commits it: `git -C /user add {file} && git -C /user commit -m "Agent: updated {file}"`. This ensures all changes are tracked. [A14]

### FU-6: Infrastructure Verification

- [ ] **AC-28:** A `scripts/verify_bwrap.sh` script tests bwrap functionality on the current host: creates a minimal namespace with ro-bind + rw-bind mounts, writes to the rw mount, verifies the ro mount rejects writes, verifies mount isolation (host filesystem not visible inside namespace). Exits 0 on success, 1 with diagnostic output on failure. [S1]
- [ ] **AC-29:** The Dockerfile for chatServer installs the `bubblewrap` package and `git`. The `kernel.unprivileged_userns_clone=1` sysctl is documented as a host requirement (not set in the Dockerfile — it's a kernel parameter). [A14]
- [ ] **AC-30:** A `BWRAP_ENABLED` environment variable (default `false`) gates sandbox functionality. When `false`, the `SandboxManager` returns a `NoopSandboxContext` that raises `SandboxNotAvailableError` on any `run_command()` call. This allows the chatServer to run on hosts without bwrap (development, CI) while Phase 3 features degrade gracefully. [A14]
- [ ] **AC-31:** Integration tests for sandbox functionality are gated behind a `@pytest.mark.sandbox` marker that checks for bwrap availability. CI runs these tests only on Linux runners with bwrap installed. [S1]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/sandbox/__init__.py` | Package init |
| `chatServer/sandbox/manager.py` | `SandboxManager` — provision, teardown, registry |
| `chatServer/sandbox/context.py` | `SandboxContext` — run_command, mount info, lifecycle |
| `chatServer/sandbox/sync.py` | `SyncService` — bidirectional sync with Supabase Storage |
| `chatServer/sandbox/models.py` | `CommandResult`, `SandboxConfig`, `MountSpec` dataclasses |
| `chatServer/sandbox/noop.py` | `NoopSandboxContext` — graceful degradation when bwrap unavailable |
| `chatServer/capabilities/executors/sandbox_executor.py` | `SandboxExecutor` — routes tool calls to bwrap namespace |
| `scripts/verify_bwrap.sh` | Host verification script for bwrap + unprivileged userns |
| `tests/chatServer/sandbox/test_manager.py` | SandboxManager unit tests |
| `tests/chatServer/sandbox/test_context.py` | SandboxContext run_command tests |
| `tests/chatServer/sandbox/test_sync.py` | SyncService tests |
| `tests/chatServer/sandbox/test_sandbox_executor.py` | Capability Gateway sandbox routing tests |
| `tests/integration/test_bwrap_sandbox.py` | Integration: provision, run_command, verify mounts, teardown |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/main.py` | Initialize `SandboxManager` in lifespan; shutdown all sandboxes on exit |
| `chatServer/config/settings.py` | Add `bwrap_enabled`, `bwrap_path`, `sandbox_data_dir`, `sandbox_idle_timeout` settings |
| `chatServer/capabilities/gateway.py` (SPEC-034) | Add `SandboxExecutor` routing for `execution_mode: "sandbox"` tools |
| `Dockerfile` | Install `bubblewrap` and `git` packages |
| `requirements.txt` | No new Python dependencies (uses `asyncio.subprocess`) |

### Out of Scope

- **Network isolation inside sandbox.** We use `--share-net` and rely on the Capability Gateway to control what the agent can access. Network-level sandboxing (iptables, network namespaces) is future hardening.
- **Resource limits (cgroups).** CPU/memory limits for sandbox processes. Future optimization — current scale (single user) doesn't need it.
- **Multi-user disk quotas.** All users share the persistent disk. Quota enforcement is future scope.
- **Sandbox migration between hosts.** If a user moves between servers (scaling), their sandbox is re-provisioned from Supabase Storage. No live migration.
- **CLI tool version management.** `/tools/` mount contains whatever is installed on the host. Version pinning is infrastructure config, not application logic.
- **Git remote push.** The user tree's git repo is local-only. Supabase Storage is the remote backup, not a git remote. Actual git remote (GitHub, etc.) is future scope.

## Technical Approach

### 1. bwrap Invocation

```python
class SandboxManager:
    """Provisions and manages per-user bwrap namespaces."""

    def __init__(self, config: SandboxConfig):
        self._config = config
        self._active: dict[str, SandboxContext] = {}
        self._lock = asyncio.Lock()

    async def provision(self, user_id: str) -> SandboxContext:
        async with self._lock:
            if user_id in self._active:
                self._active[user_id].touch()  # Reset idle timer
                return self._active[user_id]

            user_dir = self._config.data_dir / "users" / user_id
            system_dir = self._config.data_dir / "system"
            tools_dir = self._config.tools_dir

            # Hydrate if needed
            if not user_dir.exists():
                await self._hydrate_from_storage(user_id, user_dir)

            ctx = SandboxContext(
                user_id=user_id,
                user_dir=user_dir,
                system_dir=system_dir,
                tools_dir=tools_dir,
                bwrap_path=self._config.bwrap_path,
                sync_service=self._sync_service,
            )
            self._active[user_id] = ctx
            return ctx
```

### 2. Command Invocation

```python
class SandboxContext:
    """Represents an active sandbox for a user."""

    async def run_command(
        self,
        command: str,
        env: dict[str, str] | None = None,
        timeout: float = 30.0,
        cwd: str = "/user",
    ) -> CommandResult:
        bwrap_cmd = [
            self._bwrap_path,
            "--unshare-all",
            "--share-net",
            "--die-with-parent",
            "--ro-bind", str(self._system_dir), "/system",
            "--bind", str(self._user_dir), "/user",
            "--ro-bind", str(self._tools_dir), "/tools",
            "--tmpfs", "/tmp",
            "--dev", "/dev",
            "--proc", "/proc",
            "--chdir", cwd,
            "--",
            "/bin/sh", "-c", command,
        ]

        proc_env = {**os.environ}
        if env:
            proc_env.update(env)

        proc = await asyncio.create_subprocess_exec(
            *bwrap_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=proc_env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            return CommandResult(
                stdout=self._truncate(stdout.decode()),
                stderr=self._truncate(stderr.decode()),
                exit_code=proc.returncode,
                timed_out=False,
            )
        except asyncio.TimeoutError:
            proc.terminate()
            await asyncio.sleep(5)
            if proc.returncode is None:
                proc.kill()
            return CommandResult(
                stdout="", stderr="[timed out]",
                exit_code=-1, timed_out=True,
            )
```

### 3. Hydration from Supabase Storage

```python
async def _hydrate_from_storage(self, user_id: str, user_dir: Path):
    """Download user config from Supabase Storage to local disk."""
    user_dir.mkdir(parents=True, exist_ok=True)

    config_service = get_config_service()
    paths = await config_service.list_paths("", user_id)

    for path_info in paths:
        if path_info.source != "user":
            continue  # Only hydrate user-layer files
        content = await config_service.read(path_info.path, user_id)
        if content is not None:
            local_path = user_dir / path_info.path
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text(content)

    # Initialize git repo
    await self._run_local(f"git -C {user_dir} init")
    await self._run_local(f"git -C {user_dir} add -A")
    await self._run_local(
        f'git -C {user_dir} commit -m "Initial hydration from Supabase Storage" --allow-empty'
    )
```

### 4. Sync Back to Storage

```python
class SyncService:
    """Syncs user config tree changes back to Supabase Storage."""

    async def sync_to_storage(self, user_id: str):
        user_dir = self._data_dir / "users" / user_id

        # Get changed files since last sync
        last_synced = await self._get_last_synced_commit(user_dir)
        head = await self._get_head_commit(user_dir)

        if last_synced == head:
            return  # Nothing to sync

        diff_range = f"{last_synced}..{head}" if last_synced else "HEAD"
        changed = await self._get_changed_files(user_dir, diff_range)

        config_service = get_config_service()
        for file_path, change_type in changed:
            if change_type == "D":
                await config_service.delete(file_path, user_id)
            else:
                content = (user_dir / file_path).read_text()
                await config_service.write(file_path, user_id, content)

        # Update sync tag
        await self._run_local(
            f"git -C {user_dir} tag -f last-synced {head}"
        )
```

### 5. Credential Injection Pattern

Credentials never touch the filesystem. The Capability Gateway injects them per-subprocess:

```python
# In SandboxExecutor
async def execute_tool(
    self, tool_name: str, params: dict, ctx: ExecutionContext
) -> str:
    # Get credentials from token store (server-side, never in LLM context)
    creds = await self._token_store.get(ctx.user_id, tool_name)

    # Build env vars for this specific invocation
    tool_env = {}
    if creds and creds.access_token:
        tool_env["GOOGLE_ACCESS_TOKEN"] = creds.access_token
    if creds and creds.refresh_token:
        tool_env["GOOGLE_REFRESH_TOKEN"] = creds.refresh_token

    # Run CLI tool inside sandbox with scoped env
    command = self._build_command(tool_name, params)
    result = await ctx.sandbox.run_command(command, env=tool_env, timeout=60.0)

    if result.exit_code != 0:
        return f"Tool error: {result.stderr}"
    return result.stdout
```

## Blast Radius

### Direct Impact

| Component | Impact | Risk |
|-----------|--------|------|
| `chatServer/main.py` | Modified: SandboxManager lifecycle in lifespan | **Medium** — startup/shutdown ordering matters |
| `chatServer/capabilities/gateway.py` | Modified: SandboxExecutor routing | **High** — touches every tool invocation path |
| `chatServer/config/settings.py` | Modified: new settings | **Low** |
| `Dockerfile` | Modified: install bwrap + git | **Medium** — image size increase, build verification |
| Deployment infrastructure | New: persistent disk provisioning | **High** — requires Fly volume or Hetzner block storage |

### Indirect Impact

| Component | Impact | Risk |
|-----------|--------|------|
| SPEC-035 ConfigService | Now has a consumer that writes back (SyncService) | **Medium** — sync conflicts possible |
| SPEC-034 Capability Gateway | Gains new invocation mode | **Medium** — must not break existing Python executor mode |
| SPEC-036 Workflow Engine | Workflow steps may run inside sandbox | **Low** — opt-in via tool definition |

### Infrastructure Requirements

| Requirement | Where | Risk |
|------------|-------|------|
| `bubblewrap` package | Dockerfile + host | **Low** — widely packaged |
| `kernel.unprivileged_userns_clone=1` | Host kernel | **High** — must verify on Fly Machines |
| Persistent disk (>=10GB) | Fly volume / Hetzner block | **Medium** — provisioning is manual |
| `git` | Dockerfile + host | **Low** — standard package |

## Testing

| Test | Maps to AC | Type |
|------|-----------|------|
| SandboxManager provisions new user (creates dir, inits git) | AC-01, AC-04 | Unit |
| SandboxManager returns existing context for active user | AC-18 | Unit |
| bwrap mounts are correct (ro/rw verified) | AC-02, AC-05 | Integration (`@sandbox`) |
| `/system/` rejects writes inside namespace | AC-02 | Integration (`@sandbox`) |
| `/user/` accepts writes inside namespace | AC-02 | Integration (`@sandbox`) |
| Hydration downloads from Storage, creates git repo | AC-07 | Unit (mock Storage) |
| Hydration skipped when user dir exists | AC-08 | Unit |
| run_command() returns stdout/stderr/exit_code | AC-13 | Integration (`@sandbox`) |
| run_command() respects timeout, kills subprocess | AC-16 | Integration (`@sandbox`) |
| run_command() truncates oversized output | AC-17 | Unit |
| run_command() injects env vars without writing to disk | AC-15 | Integration (`@sandbox`) |
| SyncService uploads changed files only | AC-09 | Unit (mock Storage) |
| SyncService handles Storage unavailability gracefully | AC-11 | Unit (mock Storage) |
| Teardown syncs, kills procs, releases namespace | AC-19 | Integration (`@sandbox`) |
| SandboxExecutor routes tool call to bwrap run_command | AC-23, AC-24 | Unit |
| SandboxExecutor injects credentials as env vars | AC-25 | Unit |
| Auto-commit on write_file | AC-27 | Integration (`@sandbox`) |
| NoopSandboxContext raises when bwrap disabled | AC-30 | Unit |
| verify_bwrap.sh passes on supported hosts | AC-28 | Script test |

## Edge Cases

1. **User directory exists but git repo is corrupted.** `SandboxManager` detects via `git fsck --quick` on startup. Logs ERROR, does not auto-repair. Admin must manually delete and let hydration recreate.

2. **Supabase Storage unreachable during hydration.** First provision fails with a clear error: `"Cannot hydrate user config: Storage unreachable. The agent will operate without sandbox capabilities."` Agent falls back to non-sandbox mode for this session.

3. **Disk full.** `run_command()` returns an error from the OS. `SandboxManager` logs the disk usage and raises `SandboxDiskFullError`. The agent should surface this to the user.

4. **Concurrent run_command() calls for same user.** Safe — each `run_command()` is a separate subprocess. Multiple commands can run inside the same namespace concurrently. Git operations should be serialized (via a per-user lock) to avoid conflicts.

5. **Agent tries to write to `/system/`.** Kernel rejects the write. The command fails with a permission error. The agent sees the error and should understand the path is read-only. This is SPEC-039's enforcement mechanism.

6. **Server crash mid-sync.** The local git repo is the source of truth. On restart, the sync tag is stale — next sync will re-upload files that may already be in Storage. This is idempotent (overwrite with same content).

7. **Long-lived autonomous agent.** The sandbox stays active for the entire workflow duration. Idle timeout does NOT apply to workflows in progress — only to interactive sessions with no user activity.

## Resolved Decisions

1. **Per-command bwrap vs long-lived namespace.** Decision: start with per-command bwrap invocations (simpler, no namespace management). Each `run_command()` creates a fresh bwrap process with the same mounts. The overhead (~10ms per invocation) is acceptable for agent tool calls. Long-lived namespaces are a future optimization if needed.

2. **Git auto-commit granularity.** Decision: one commit per `write_file` tool call. Fine-grained commits make `git log` useful as a changelog. Squashing is a future file browser feature if the history gets noisy.

3. **Network inside sandbox.** Decision: `--share-net` (shared network namespace). The Capability Gateway controls external access, not the network namespace. This simplifies the implementation — tools that need HTTP (e.g., `gog`) work without network tunneling. Future hardening can add network namespace isolation.

4. **System defaults refresh.** Decision: periodic pull from Supabase Storage (hourly). System defaults change only on deploy. An explicit refresh endpoint is available for immediate propagation.

5. **Sync direction.** Decision: local to Storage (one-way after hydration). The local git repo is always the source of truth for active users. Storage is a backup. Two-way sync (Storage to local on external edit) is a Phase 4 feature (file browser writes go to Storage, then propagate to sandbox).

## Decisions Requiring Your Input

1. **Persistent disk sizing.** Each user's config tree is small (~1-10MB). But git history grows over time. **Option A:** 10GB shared volume (supports ~100 active users). **Option B:** 50GB (supports ~500 users with generous history). **Option C:** Per-user volumes (clean isolation, higher infra complexity). Recommendation: Option A for MVP, monitor and scale.

2. **bwrap on Fly Machines — needs a spike.** The architecture proposal flagged this as an open question. Unprivileged user namespaces may not work on Fly's infrastructure. **Before implementing this spec,** we need a spike: deploy a test Machine that runs `bwrap --ro-bind / / --dev /dev --proc /proc ls` and confirm it works. If it doesn't, the fallback is `--cap-add SYS_ADMIN` (requires Fly config change) or running bwrap as a privileged operation in the Dockerfile.

3. **`/tools/` mount contents.** What CLI tools should be available? Minimum: `gog`, `git`, coreutils (`cat`, `grep`, `sed`, `find`, `ls`). Should we also include `jq`, `curl` (for tools that need HTTP), `python3` (for complex data processing)? Recommendation: minimal set (gog, git, coreutils, jq) — add more as tools need them.
