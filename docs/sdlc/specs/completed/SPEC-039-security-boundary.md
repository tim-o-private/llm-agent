# SPEC-039: Security Boundary + Self-Improvement

> **Status:** Draft
> **Author:** Claude (Spec Writer)
> **Created:** 2026-04-06
> **Updated:** 2026-04-06
> **PRD:** Architecture Proposal (Phase 3, Items 11-12)
> **Architecture:** `docs/product/ARCHITECTURE-PROPOSAL-next-gen.md`, Sections Q3, Q5, Phase 3
> **Behavior Spec:** `docs/product/PRODUCT-BEHAVIOR-SPEC-next-architecture.md`, Sections 4, 5, 8

## Goal

Define and enforce the boundary between what the agent can and cannot modify about itself. The immutable layer (`/system/`) contains security-critical config — tool allowlists, trust tiers, auth scopes — enforced by kernel-level read-only bind mounts. The mutable layer (`/user/`) contains everything else — prompts, workflows, preferences, memory — that the agent can edit to improve over time. All mutable changes are git-tracked, produce diff-based notifications to the user, and can be rolled back automatically if behavioral metrics degrade.

This is the spec that makes self-improvement safe. The agent has real agency over its own behavior within boundaries that it literally cannot cross.

## Background

The product behavior spec (Section 4) defines two modification tiers:

**Everything except security** — agent can edit, user gets a tap-to-approve notification:
- Prompt tone, format, length, greeting style
- New workflow templates, scheduling rules
- How the agent categorizes input, response strategies
- Memory retention rules, learned preferences

**Security boundary** — agent cannot edit directly, requires explicit confirmation:
- Tool allowlists (which tools the agent can use)
- Approval tiers (what trust level per tool)
- Auth scopes (which services are connected)
- Sub-agent permissions

The critical insight: the boundary between these tiers is determined by **which files are being modified**, not by what the agent says it's doing. A read-only bind mount enforces this at the kernel level — no amount of prompt injection can override a mount flag.

### How HQ Does It (Reference)

In HQ, Tim's Claude Code sandbox user (`claude-sandbox`) has:
- ACL-restricted filesystem (can only access `/home/tim/github/`)
- `.env` files explicitly blocked
- Network restricted to Anthropic API + GitHub + npm
- GitHub branch protection on `main`

The bwrap sandbox applies the same principle in a multi-tenant server context: filesystem isolation via mount flags instead of ACLs, with Supabase Storage as the backup layer instead of GitHub.

### Relationship to Other Specs

| Spec | Relationship |
|------|-------------|
| **SPEC-038** (bwrap Sandbox) | Provisions the filesystem this spec defines rules for. SPEC-038 creates the mounts; this spec defines what goes where. |
| **SPEC-040** (Introspection Loop) | The primary consumer of self-improvement capabilities. The introspection loop reads from `/system/` (metrics, config) and writes to `/user/` (improvements). |
| **SPEC-034** (Capability Gateway) | Manages tool allowlists — the gateway reads allowlist config from `/system/security/`, which the agent cannot modify. |
| **SPEC-035** (Config Service) | Mutable changes sync back to Supabase Storage. Security config in Storage is also protected by server-side validation. |

## Dependencies

| Dependency | What It Provides | Status |
|-----------|-----------------|--------|
| SPEC-038 (bwrap Sandbox) | Filesystem provisioning, mount layout, run_command interface | Draft (this sprint) |
| SPEC-034 (Capability Gateway) | Tool allowlist enforcement, trust tier checking | Draft |
| SPEC-035 (Config Service) | Supabase Storage overlay, sync target | Draft (in progress) |
| SPEC-025 (Notifications) | `NotificationService` for diff-based change notifications | Complete |
| Product Behavior Spec Section 4 | Modification tiers, disclosure model | Complete |

## Acceptance Criteria

### FU-1: Filesystem Security Layout

- [ ] **AC-01:** The `/system/` directory on disk contains a `security/` subdirectory with the following files: `tool_allowlist.yaml` (per-user tool permissions), `trust_tiers.yaml` (per-tool trust level defaults), `auth_scopes.yaml` (connected service scopes), `modification_policy.yaml` (which paths are mutable vs immutable). These files define the security boundary. [A12]
- [ ] **AC-02:** The `/system/` directory is mounted as a read-only bind mount in the bwrap namespace (SPEC-038 AC-02). Any attempt to write to any path under `/system/` from inside the namespace fails with `EROFS` (read-only filesystem). This is verified by integration tests. [A12]
- [ ] **AC-03:** The `modification_policy.yaml` file in `/system/security/` defines two sections: `immutable_paths` (list of glob patterns under `/system/` that are always read-only — redundant with the mount flag but serves as documentation and is used by the server-side validation layer) and `mutable_paths` (list of glob patterns under `/user/` that the agent can modify). [A12]
- [ ] **AC-04:** The `/user/` directory is organized into subdirectories matching the config overlay pattern: `agent/` (prompt definitions, personality), `workflows/` (custom workflow templates), `preferences/` (learned preferences, style profiles), `memory/` (agent's observations), `schedules/` (scheduling rules). All are mutable. [A13]
- [ ] **AC-05:** A `README.md` at `/user/README.md` explains the directory structure and what each subdirectory contains. This file is included in the initial hydration (SPEC-038 AC-07) and serves as documentation for the "Open the Hood" file browser (Phase 4). [A13]

### FU-2: Security-Boundary Config Files

- [ ] **AC-06:** `tool_allowlist.yaml` contains a list of tool entries, each with: `name` (tool name), `enabled` (boolean), `tier` (inform/recommend/act), `added_at` (ISO timestamp), `added_by` (user/system). The Capability Gateway (SPEC-034) reads this file to determine available tools. Default allowlist is seeded from the system layer and copied to the user's `/system/security/` path on provisioning. [A12]
- [ ] **AC-07:** `trust_tiers.yaml` contains per-tool trust tier overrides. Structure: `{tool_name: {tier: "inform|recommend|act", graduated_at: "ISO timestamp", graduated_by: "user|agent_proposed"}}`. Tools not listed inherit the system default tier. The gateway reads this alongside the allowlist. [A12]
- [ ] **AC-08:** `auth_scopes.yaml` lists connected services and their granted scopes: `{service_name: {connected: true, scopes: ["read", "send"], connected_at: "ISO timestamp"}}`. This is informational for the agent (it can read what services are available) but immutable (it can't grant itself new scopes). [A12]
- [ ] **AC-09:** All `/system/security/` files are owned and modified exclusively by the server process (outside the bwrap namespace). Changes to these files require an explicit user action through the approval flow — either via the web UI, Telegram inline approval, or the Phase 4 "Red Button" unlock. [A12]

### FU-3: Mutable Config + Git Tracking

- [ ] **AC-10:** Every file write in the `/user/` tree (via `SandboxContext.run_command()` or `write_file` tool) is automatically committed to the git repo with a descriptive message: `"Agent: {action} {file_path}"` where `action` is `updated`, `created`, or `deleted`. The commit author is `Clarity Agent <agent@clarity.app>`. [A14]
- [ ] **AC-11:** The git repo in `/user/` tracks all changes with full history. `git log --oneline` returns a human-readable changelog of all agent modifications. `git diff HEAD~1` shows the most recent change. `git revert {commit_sha}` rolls back a specific change. These commands are available to the agent via sandbox run_command and to the user via the file browser API (Phase 4). [A13]
- [ ] **AC-12:** A `ChangeTracker` service in `chatServer/sandbox/change_tracker.py` monitors the `/user/` git repo for new commits. After each commit, it extracts the diff (`git diff HEAD~1 HEAD`) and emits a `config_changed` event containing: `user_id`, `commit_sha`, `files_changed` (list of paths), `diff_text`, `timestamp`. [A14]
- [ ] **AC-13:** The `ChangeTracker` classifies each change by modification tier. Files under `agent/`, `workflows/`, `preferences/`, `memory/`, `schedules/` are `non_security` (tap-to-approve). Any file matching `modification_policy.yaml`'s `immutable_paths` globs is `security` (should never happen from inside the sandbox, but defense-in-depth). [A12]

### FU-4: Diff-Based Notifications

- [ ] **AC-14:** When the `ChangeTracker` detects a `non_security` change, it creates a notification via `NotificationService.notify_user()` with `type="silent"` (doesn't push to Telegram unless user has notifications enabled for config changes), `category="config_change"`. The notification body contains a human-readable summary of the change: what file was modified, a brief description of the diff, and the commit SHA for reference. [A7]
- [ ] **AC-15:** The notification includes a tap-to-approve UX: the user can `approve` (acknowledge the change — no-op, change is already applied), `revert` (trigger `git revert {commit_sha}` in the user tree), or `inspect` (link to the file browser / git diff view — Phase 4). For MVP, `approve` and `revert` are the two actions. [A12, F1]
- [ ] **AC-16:** Disclosure level varies by trust tier (product behavior spec Section 4.3). At **Inform** tier: full transparency notification for every change. At **Recommend** tier: aggregated notification (e.g., "I made 3 adjustments to how I handle your email triage"). At **Act** tier: silent, with periodic summary (monthly changelog digest). The disclosure level is read from the user's trust tier for the `self_improvement` capability. [A12]
- [ ] **AC-17:** The trust tier for `self_improvement` is configured in `trust_tiers.yaml` like any other capability. Default: `inform` (every change notified). Users can graduate to `recommend` or `act` through the standard trust graduation flow. [A12]

### FU-5: Modification Flow

- [ ] **AC-18:** The agent modifies config via standard file tools inside the sandbox. The modification flow is: (1) agent decides to change a file (e.g., adjust prompt tone), (2) agent calls `write_file` or `run_command("sed -i ...")` inside the sandbox, (3) SPEC-038 AC-27 auto-commits the change, (4) `ChangeTracker` detects the commit and emits notification, (5) user sees the change and can approve or revert. [A13, A14]
- [ ] **AC-19:** The agent can read its own git history to understand what it has changed: `run_command("git log --oneline -20")` returns recent changes, `run_command("git diff {sha1} {sha2}")` shows specific diffs. This enables the agent to answer user questions like "what have you changed recently?" conversationally. [A13]
- [ ] **AC-20:** When a user asks the agent about recent changes (e.g., "what did you change?", "show me your changelog"), the agent reads the git log from the sandbox and presents a human-readable summary. No special tool required — standard sandbox run_command with git commands. [A13]

### FU-6: Auto-Rollback

- [ ] **AC-21:** A `RollbackService` in `chatServer/sandbox/rollback.py` provides `async check_and_rollback(user_id: str)` that evaluates whether recent agent changes have degraded behavioral metrics. Called periodically (configurable, default: after every 10 agent interactions post-change) or on explicit user feedback indicating degradation. [A14]
- [ ] **AC-22:** Behavioral metrics for auto-rollback evaluation: (1) user satisfaction signals — explicit negative feedback via feedback buttons (SPEC-024), (2) interaction patterns — significant increase in user corrections or retries, (3) tool failure rate — increase in tool errors post-change. Metrics are compared against a baseline from the 7 days before the change. [A14]
- [ ] **AC-23:** When `RollbackService` identifies a causal commit (the most recent config change before metric degradation), it: (1) reverts the commit via `git revert {sha}` inside the sandbox, (2) syncs the revert to Supabase Storage, (3) notifies the user: `"I noticed my recent change to {file} wasn't working well. I've reverted it. Here's what I changed back: {diff summary}."` [A14]
- [ ] **AC-24:** Auto-rollback is conservative: it only triggers when metric degradation is statistically significant (>2 sigma from baseline) AND can be attributed to a specific commit (change happened within the degradation window). If degradation can't be attributed, it notifies the user without auto-reverting. [A14]
- [ ] **AC-25:** Manual rollback is always available: the user can revert any commit via the notification action (AC-15) or by asking the agent ("undo your last change"). The agent runs `git revert {sha}` in the sandbox. [A13]

### FU-7: Server-Side Security Validation

- [ ] **AC-26:** A `SecurityValidator` in `chatServer/sandbox/security_validator.py` provides a defense-in-depth layer. Before syncing any file from the sandbox to Supabase Storage (SPEC-038 AC-10), the validator checks that the file path is in the mutable layer (`/user/`). Any file matching immutable path patterns is rejected and logged at ERROR level. [A12]
- [ ] **AC-27:** The `SecurityValidator` also validates the content of security-adjacent files. If the agent modifies a file in `/user/` that references or imports security config (e.g., a workflow template that tries to set `gate_policy: none` on a step that the user has marked as requiring human approval), the validator flags it for review. This is a heuristic check, not a guarantee — the primary enforcement is the read-only mount. [A12]
- [ ] **AC-28:** Security config changes (tool allowlist, trust tiers, auth scopes) go through a dedicated `SecurityConfigService` in `chatServer/services/security_config_service.py`. This service runs OUTSIDE the sandbox (server-side), requires authenticated user context, and writes directly to the system layer on disk and in Supabase Storage. The agent cannot call this service from inside the sandbox. [A8, A12]
- [ ] **AC-29:** The `SecurityConfigService` supports agent-proposed changes: the agent can REQUEST a security change by creating a pending action (via the Capability Gateway, not by writing to `/system/`). Example: agent calls a `request_capability_upgrade` tool that creates a pending action: `"I'd like to graduate email sending from Recommend to Act tier. I've been sending emails with your approval for 2 weeks with no issues."` The user approves or rejects via the standard approval flow. [A12]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/sandbox/change_tracker.py` | `ChangeTracker` — monitors git commits, emits notifications |
| `chatServer/sandbox/rollback.py` | `RollbackService` — auto-rollback on metric degradation |
| `chatServer/sandbox/security_validator.py` | `SecurityValidator` — defense-in-depth path validation |
| `chatServer/services/security_config_service.py` | Server-side security config management (outside sandbox) |
| `chatServer/capabilities/executors/capability_upgrade.py` | `request_capability_upgrade` tool for agent-proposed security changes |
| `config/system/security/tool_allowlist.yaml` | Default tool allowlist template |
| `config/system/security/trust_tiers.yaml` | Default trust tier config |
| `config/system/security/auth_scopes.yaml` | Default auth scopes template |
| `config/system/security/modification_policy.yaml` | Immutable/mutable path classification |
| `config/user_template/README.md` | User directory documentation (hydrated on first provision) |
| `tests/chatServer/sandbox/test_change_tracker.py` | ChangeTracker unit tests |
| `tests/chatServer/sandbox/test_rollback.py` | RollbackService unit tests |
| `tests/chatServer/sandbox/test_security_validator.py` | SecurityValidator unit tests |
| `tests/chatServer/services/test_security_config_service.py` | SecurityConfigService unit tests |
| `tests/integration/test_security_boundary.py` | Integration: write to /system/ fails, write to /user/ succeeds + tracked |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/sandbox/manager.py` (SPEC-038) | Integrate `ChangeTracker` — start monitoring after provision |
| `chatServer/sandbox/sync.py` (SPEC-038) | Add `SecurityValidator` check before uploading files |
| `chatServer/capabilities/gateway.py` (SPEC-034) | Read allowlist from `/system/security/tool_allowlist.yaml` (via filesystem or config service) |
| `chatServer/services/pending_actions.py` | Support `capability_upgrade` tool for agent-proposed security changes |
| `chatServer/main.py` | Initialize `SecurityConfigService`, `ChangeTracker` in lifespan |

### Out of Scope

- **File browser UI for config inspection.** Phase 4 (SPEC-042+). This spec defines the data model; the UI reads it.
- **The Red Button.** Phase 4 feature that unlocks `/system/` for direct user editing. This spec treats `/system/` as always-immutable from the agent's perspective.
- **Sub-agent permissions.** Behavior spec mentions sub-agent permission capping. This is a future Capability Gateway feature — current scope is single-agent.
- **Content-based injection detection.** The `SecurityValidator` does path-based and basic content checks. Deep prompt injection detection (behavior spec Section 8) is a separate operational process, not part of this spec.
- **Approval UI for non-security changes.** MVP uses the existing notification infrastructure. The "tap-to-approve" is a notification action, not a dedicated approval panel. Phase 4 may add a richer review UX.

## Technical Approach

### 1. Filesystem Layout

```
bwrap namespace (per-user)
|-- /system/                          [ro bind mount -- kernel-enforced]
|   |-- agents/
|   |   +-- clarity/
|   |       |-- soul.md               # Agent personality (from SPEC-035)
|   |       +-- identity.json         # Agent identity config
|   |-- workflows/
|   |   |-- email-triage.md           # System workflow templates (SPEC-037)
|   |   |-- morning-briefing.md
|   |   |-- draft-reply.md
|   |   +-- prompts/                  # Step prompts for system workflows
|   |-- tools/
|   |   +-- definitions/              # Tool schema files (Capability Gateway)
|   |-- security/
|   |   |-- tool_allowlist.yaml       # What tools the agent can use
|   |   |-- trust_tiers.yaml          # Trust level per tool
|   |   |-- auth_scopes.yaml          # Connected services and scopes
|   |   +-- modification_policy.yaml  # Mutable vs immutable classification
|   +-- preferences/
|       +-- defaults.yaml             # System default preferences
|
|-- /user/                            [rw bind mount -- git-versioned]
|   |-- README.md                     # Directory structure docs
|   |-- agent/
|   |   |-- instructions.md           # User's standing instructions
|   |   |-- style_overrides.md        # Prompt tone/format preferences
|   |   +-- greeting.md               # Custom greeting/signoff style
|   |-- workflows/
|   |   +-- (custom templates)        # User-created or agent-created workflows
|   |-- preferences/
|   |   |-- communication.yaml        # Communication style preferences
|   |   |-- scheduling.yaml           # Scheduling rules
|   |   +-- triage_rules.yaml         # Email triage customizations
|   |-- memory/
|   |   |-- observations.md           # Agent's learned observations
|   |   +-- writing_style.md          # User's writing style profile
|   +-- schedules/
|       +-- weekly.yaml               # Custom scheduling rules
|
|-- /tools/                           [ro bind mount]
|   |-- gog                           # Google services CLI
|   |-- git                           # Version control
|   +-- (other CLI tools)
|
+-- /tmp/                             [rw tmpfs -- ephemeral scratch]
```

### 2. Modification Policy File

```yaml
# /system/security/modification_policy.yaml
# Defines which paths are mutable (agent-writable) vs immutable (server-only)
# The primary enforcement is the read-only bind mount on /system/.
# This file provides documentation and defense-in-depth validation.

immutable_paths:
  - "/system/**"           # Everything under /system/ is immutable

mutable_paths:
  - "/user/agent/**"       # Prompt definitions, personality overrides
  - "/user/workflows/**"   # Custom workflow templates
  - "/user/preferences/**" # Learned preferences, style profiles
  - "/user/memory/**"      # Agent observations, writing style
  - "/user/schedules/**"   # Scheduling rules

# Paths requiring elevated review (mutable, but changes trigger extra validation)
elevated_review:
  - "/user/workflows/**"   # New workflows can have side effects
```

### 3. ChangeTracker Implementation

```python
class ChangeTracker:
    """Monitors user git repo for new commits and emits notifications."""

    def __init__(
        self,
        notification_service: NotificationService,
        trust_tier_resolver: TrustTierResolver,
    ):
        self._notification_service = notification_service
        self._trust_tier_resolver = trust_tier_resolver
        self._last_seen_commits: dict[str, str] = {}  # user_id -> sha

    async def check_for_changes(self, user_id: str, user_dir: Path):
        """Called after sandbox operations. Detects new commits."""
        head = await self._get_head(user_dir)
        last_seen = self._last_seen_commits.get(user_id)

        if head == last_seen:
            return

        # Get new commits since last seen
        if last_seen:
            commits = await self._get_commits_since(user_dir, last_seen)
        else:
            commits = [await self._get_commit_info(user_dir, head)]

        for commit in commits:
            await self._process_commit(user_id, user_dir, commit)

        self._last_seen_commits[user_id] = head

    async def _process_commit(
        self, user_id: str, user_dir: Path, commit: CommitInfo
    ):
        """Classify change and emit appropriate notification."""
        diff = await self._get_diff(user_dir, commit.sha)
        tier = await self._trust_tier_resolver.get_tier(
            user_id, "self_improvement"
        )

        if tier == "act":
            # Silent -- aggregated in monthly digest
            await self._record_for_digest(user_id, commit, diff)
            return

        if tier == "recommend":
            # Aggregated notification
            await self._queue_for_aggregation(user_id, commit, diff)
            return

        # Inform tier -- full transparency
        summary = self._summarize_diff(diff)
        await self._notification_service.notify_user(
            user_id=user_id,
            body=f"I updated my configuration:\n\n{summary}\n\n"
                 f"Commit: {commit.sha[:8]}",
            notification_type="silent",
            category="config_change",
            metadata={
                "commit_sha": commit.sha,
                "files_changed": diff.files,
                "actions": ["approve", "revert"],
            },
        )
```

### 4. Auto-Rollback Logic

```python
class RollbackService:
    """Evaluates behavioral metrics and reverts harmful config changes."""

    async def check_and_rollback(self, user_id: str):
        """Called periodically after config changes."""
        user_dir = self._get_user_dir(user_id)

        # Get recent config change commits
        recent_changes = await self._get_recent_config_commits(
            user_dir, days=7
        )
        if not recent_changes:
            return

        # Get behavioral metrics
        baseline = await self._get_baseline_metrics(user_id, days=7)
        current = await self._get_current_metrics(
            user_id, since=recent_changes[0].timestamp
        )

        # Check for degradation
        degradation = self._detect_degradation(baseline, current)
        if not degradation.is_significant:
            return

        # Attribute to a specific commit
        causal_commit = self._find_causal_commit(
            recent_changes, degradation
        )
        if not causal_commit:
            # Can't attribute -- notify without auto-reverting
            await self._notify_unattributed_degradation(
                user_id, degradation
            )
            return

        # Auto-revert
        sandbox = await self._sandbox_manager.provision(user_id)
        await sandbox.run_command(
            f"git revert --no-edit {causal_commit.sha}"
        )

        # Sync revert to storage
        await self._sync_service.sync_to_storage(user_id)

        # Notify user
        diff_summary = await self._get_revert_summary(
            user_dir, causal_commit
        )
        await self._notification_service.notify_user(
            user_id=user_id,
            body=(
                f"I noticed my recent change to {causal_commit.files[0]} "
                f"wasn't working well -- {degradation.description}. "
                f"I've reverted it.\n\n{diff_summary}"
            ),
            notification_type="notify",
            category="auto_rollback",
        )
```

### 5. Security Config Service (Outside Sandbox)

```python
class SecurityConfigService:
    """Manages security-boundary config. Runs server-side, NOT inside sandbox."""

    async def update_allowlist(
        self, user_id: str, tool_name: str, enabled: bool, tier: str
    ):
        """Update a tool's allowlist entry. Requires authenticated user."""
        # Read current allowlist
        config_path = (
            self._system_dir / "security" / "tool_allowlist.yaml"
        )
        allowlist = yaml.safe_load(config_path.read_text())

        # Update entry
        allowlist[tool_name] = {
            "enabled": enabled,
            "tier": tier,
            "added_at": datetime.now(timezone.utc).isoformat(),
            "added_by": "user",
        }

        # Write to disk (server-side, not in sandbox)
        config_path.write_text(
            yaml.dump(allowlist, default_flow_style=False)
        )

        # Sync to Supabase Storage
        await self._config_service.write(
            f"security/tool_allowlist.yaml",
            user_id,
            yaml.dump(allowlist),
        )

    async def process_capability_request(
        self, user_id: str, request: CapabilityRequest
    ) -> PendingAction:
        """Agent requests a security change -- creates pending action."""
        return await self._pending_actions.queue_action(
            user_id=user_id,
            tool_name="capability_upgrade",
            tool_args={
                "requested_tool": request.tool_name,
                "requested_tier": request.requested_tier,
                "current_tier": request.current_tier,
                "justification": request.justification,
            },
            context={
                "usage_stats": await self._get_tool_usage_stats(
                    user_id, request.tool_name
                ),
            },
        )
```

## Blast Radius

### Direct Impact

| Component | Impact | Risk |
|-----------|--------|------|
| `chatServer/sandbox/` (SPEC-038) | Modified: ChangeTracker, SecurityValidator integration | **Medium** — must not break sandbox provisioning |
| `chatServer/capabilities/gateway.py` | Modified: reads allowlist from filesystem | **High** — affects every tool invocation |
| `chatServer/services/pending_actions.py` | Modified: new `capability_upgrade` action type | **Low** — additive |
| `chatServer/services/notification_service.py` | Consumer: config change notifications | **Low** — uses existing API |

### Indirect Impact

| Component | Impact | Risk |
|-----------|--------|------|
| SPEC-040 (Introspection Loop) | Primary consumer of self-improvement | **Medium** — must respect modification tiers |
| SPEC-037 workflow templates | Templates in `/system/` are immutable; user overrides in `/user/` | **Low** — overlay resolution unchanged |
| Frontend (Phase 4) | File browser reads git history for changelog view | **Low** — future consumer |

## Testing

| Test | Maps to AC | Type |
|------|-----------|------|
| Write to `/system/` fails with EROFS inside sandbox | AC-02 | Integration (`@sandbox`) |
| Write to `/user/` succeeds and creates git commit | AC-10 | Integration (`@sandbox`) |
| `modification_policy.yaml` correctly classifies paths | AC-03, AC-13 | Unit |
| ChangeTracker detects new commits | AC-12 | Unit |
| ChangeTracker emits notification for Inform tier | AC-14, AC-16 | Unit |
| ChangeTracker aggregates for Recommend tier | AC-16 | Unit |
| ChangeTracker silently records for Act tier | AC-16 | Unit |
| Notification includes approve/revert actions | AC-15 | Unit |
| Revert action runs `git revert` in sandbox | AC-15, AC-25 | Integration (`@sandbox`) |
| SecurityValidator rejects `/system/` paths | AC-26 | Unit |
| SecurityConfigService updates allowlist outside sandbox | AC-28 | Unit |
| Agent `request_capability_upgrade` creates pending action | AC-29 | Unit |
| RollbackService detects metric degradation | AC-22 | Unit |
| RollbackService reverts causal commit | AC-23 | Unit (mock sandbox) |
| RollbackService notifies without reverting when attribution fails | AC-24 | Unit |
| Full flow: agent writes, commit, notification, revert | AC-18, AC-15 | Integration (`@sandbox`) |

## Edge Cases

1. **Agent tries to symlink `/system/` content into `/user/`.** Symlinks from `/user/` pointing to `/system/` paths are readable (the mount is ro, not hidden). But the agent can't modify the target through the symlink — the kernel enforces ro on the target mount. No special handling needed.

2. **Agent creates a workflow template in `/user/workflows/` that references tools it doesn't have access to.** The workflow template is just a file — it's the Capability Gateway that enforces tool access at runtime. The template can reference any tool name; unauthorized ones will fail at runtime with a clear error.

3. **Rapid successive changes overwhelm notifications.** The ChangeTracker batches notifications with a 30-second debounce window. Multiple commits within the window produce a single aggregated notification.

4. **Auto-rollback reverts a change the user explicitly approved.** The user's explicit approval (via notification action) sets a `user_approved` flag on the commit metadata. Auto-rollback skips commits with `user_approved=true` — the user's judgment overrides the metric signal.

5. **Agent modifies `.gitignore` in `/user/` to exclude important files.** The SecurityValidator checks `.gitignore` changes and flags them in the notification. The agent shouldn't need to modify `.gitignore` — the default covers temporary files only.

6. **Trust tier graduation for `self_improvement`.** Starts at `inform`. If the user consistently approves changes without reverting, the agent can propose graduation to `recommend` via `request_capability_upgrade`. The agent cannot graduate itself.

## Resolved Decisions

1. **Notification vs blocking approval for non-security changes.** Decision: notification (non-blocking). The change is applied immediately; the user can revert after the fact. Rationale: blocking approval for every prompt tweak would make self-improvement useless — the agent would need user interaction for every small adjustment. The revert mechanism is the safety net.

2. **Per-user security config vs shared.** Decision: per-user. Each user's `/system/security/` is provisioned from defaults but can be customized by the server (e.g., when the user connects a new service, `auth_scopes.yaml` is updated). The agent cannot modify it, but the server can.

3. **Where does the agent propose security changes?** Decision: via the Capability Gateway, using a `request_capability_upgrade` tool. This keeps the agent's request in the normal tool-call flow (audited, gateway-enforced) rather than inventing a separate channel.

4. **Git author for agent commits.** Decision: `Clarity Agent <agent@clarity.app>`. A fixed author for all agent commits makes `git log --author="Clarity Agent"` a clean way to see only agent-initiated changes.

5. **Auto-rollback sensitivity.** Decision: conservative (>2 sigma degradation, attributable commit). False positive rollbacks would erode user trust in the self-improvement system. Better to miss a bad change and let the user revert manually than to auto-revert a good change.

## Decisions Requiring Your Input

1. **Notification channel for config changes.** The behavior spec says "tap-to-approve notification." **Option A:** Use the existing web notification system + Telegram inline buttons (consistent with SPEC-024/025). **Option B:** New dedicated "config changes" notification channel (cleaner UX, but more infrastructure). Recommendation: Option A for MVP.

2. **Monthly changelog digest format.** For Act-tier users who get silent changes with periodic summary: **Option A:** Monthly email digest (requires email capability). **Option B:** Monthly chat message from the agent. **Option C:** Available on-demand only ("what have you changed?"). Recommendation: Option C for MVP, graduate to B.

3. **Security config file format.** The spec uses YAML. **Option A:** YAML (human-readable, matches HQ conventions). **Option B:** JSON (more structured, easier for programmatic access). **Option C:** TOML (readable, well-typed). Recommendation: YAML — consistent with HQ, readable in file browser.
