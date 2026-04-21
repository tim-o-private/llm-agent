# SPEC-045: Today Surface (Vault dashboard, Stage 1)

> **Status:** Draft
> **Author:** spec-writer (Claude) on behalf of Tim
> **Created:** 2026-04-17
> **Updated:** 2026-04-17 (revised after Tim's OQ decisions)
> **Vision:** [`docs/sdlc/visions/clarity-as-vault.md`](../visions/clarity-as-vault.md)
> **Directive:** [`docs/sdlc/visions/clarity-as-vault-functional.md`](../visions/clarity-as-vault-functional.md) (D1–D5, S1, S6, S7 indicator)
> **Stage:** Clarity-as-Vault Stage 1 (first buildable surface)

---

## Goal

Replace the current task-list `TodayView.tsx` with the **Today surface** defined in the functional directive — the daily dashboard rendered from `today.md` inside the user's per-user bwrap vault, containing seven sections (header, your-day, to-do, notes, agent, approvals, recent) and surfaced alongside a single pending-approvals badge in the topbar.

This is the first surface of the Clarity-as-Vault rearchitecture. Shipping it forces resolution of (a) the `today.md` **on-disk** read/write path per D1, backed by the existing bwrap sandbox filesystem, (b) the approval lane placement per D2, (c) a minimal topbar ambient indicator, and (d) coupling the morning regeneration to the **existing workflow engine** rather than stubbing it. Stage 1 keeps the "no outbound effects" contract: approval cards render, approve/reject records state, but no email is sent, no calendar event is created, no workflow file is written. The full activity-log screen ships with S7; this spec emits to `activity_log` so that screen has data, but does not read from it.

Success looks like: the user opens `/`, sees today's day framed by the agent, captures a note that round-trips to `today.md` on disk (and syncs back to Supabase Storage via the existing `StorageSync`), reviews approval cards covering all six shapes from S6, and clicks "Regenerate Today" to dispatch a real workflow run that rewrites `today.md` in place.

---

## Existing Infrastructure (what we reuse verbatim)

This spec composes primitives that are already in the codebase. Nothing in this section is new work.

| Primitive | Location | What we use it for |
|-----------|----------|---------------------|
| Per-user vault dir | `/data/sandboxes/{user_id}/` (from SPEC-044) | Physical home for `today.md` and all vault files |
| bwrap sandbox backend | `chatServer/sandbox/bwrap.py`, `bwrap_backend.py` | How the agent writes vault files; the web write path does not run under bwrap but targets the same directory |
| Storage durability | `chatServer/services/storage_sync.py` — `StorageSync.hydrate_user`, `pull_system`, `sync_file` | Hydrate on first login; fire-and-forget sync on every vault write |
| System config seed dir | `data/config/system/` (git-tracked, copied into the runtime at `/data/config/system/` at deploy time, same as existing `agents/skills/workflows/` subdirs) | Where `templates/today.md` and `workflows/regenerate-today.md` live. **Note:** `StorageSync.pull_system()` exists but is not wired in `chatServer/main.py` (see comment at `main.py:130`). FU-1 puts seed files in git at `data/config/system/` directly; no bucket upload, no pull_system wiring in this spec. |
| Workflow engine (SPEC-036) | `chatServer/workflows/run_manager.py`, `registry.py`, `builder.py`, `engine.py` | Real dispatch of the regenerate-today workflow |
| `workflow_runs` table (SPEC-036 AC-16) | existing migration | Source of run-status for the regenerate button; no duplicate regeneration table needed |
| `workflow_events` table (SPEC-036 AC-21) | existing migration | Available for future push-based completion; Stage 1 uses polling |
| Scheduled workflow pattern (SPEC-036 AC-27/28, SPEC-037 AC-31) | `chatServer/services/job_handlers.py` + `JobService` | Morning cron-like regeneration uses a dedicated `handle_regenerate_today` handler (mirrors briefing pattern) which delegates to `dispatch_workflow`; user_preferences gains an enable flag + time-of-day |
| Auth dependency | `chatServer/dependencies/auth.py` (ES256 JWT) | Every Today/Approvals endpoint resolves `user_id` from the JWT — this is the access-control spine for the filesystem-backed vault |
| Scoped DB client | `chatServer/database/scoped_client.py` — `get_user_scoped_client`, `get_system_client` | Used for `approval_cards` and `activity_log` writes/reads per A8 |
| Existing ChatPanel | `webApp/src/components/ChatPanel.tsx` → `ChatPanelV2.tsx` | Consolidated in housekeeping (AC-26) |

Downstream specs (S2 vault browser, S3 file detail, S4 workflow editor) will reuse the `VaultService` introduced here as the canonical filesystem read/write layer.

---

## Access Control Model (filesystem-backed vault)

The vault has **no DB-level RLS** because the vault has no DB rows. Access control is a path-level invariant enforced by a single chokepoint:

1. Every HTTP request that touches vault content passes through the existing `get_current_user_id` dependency. The JWT is the sole authority for user identity.
2. `VaultService._resolve(user_id, rel_path)` computes the user's canonical vault root — `/data/sandboxes/{user_id}/` — and joins `rel_path` to it.
3. The joined path is resolved (`Path(...).resolve()`) and compared against the canonical root via a containment check (`resolved.is_relative_to(root)` in Python 3.9+, or equivalent `commonpath` check). A resolved path that escapes the root → `HTTPException(403)`.
4. Symlink traversal is blocked: `VaultService` walks each component with `lstat` and rejects any component that is a symlink. (Stage 1 hardening — see Edge Cases.)
5. Rel paths containing `\x00` or any component equal to `..`, and any absolute path, are rejected before resolution.
6. `VaultService` is the only code path that writes to `/data/sandboxes/` from the web API. The workflow engine writes via the agent's normal bwrap path; that path is already isolated by SPEC-044.

This model is weaker than DB RLS in exactly one way: a bug in `_resolve` leaks cross-user data without a secondary gate. We treat `_resolve` as a security-critical function — it gets its own unit test file and a negative test (AC-22) that must stay green.

The `approval_cards` and `activity_log` tables remain DB-backed with RLS per A8. They are system state (audit trail, not user-authored content) and require immutability guarantees the filesystem cannot provide.

---

## Stage 1 "No Outbound Effects" Contract

For any approval card approved in Stage 1:

- Status flips `pending` → `approved`, `decided_at` and `decided_by` set.
- An `activity_log` entry is written with `status='done'` and `action` describing what *would have* executed (e.g. "Approved email draft to bob@example.com — Stage 1 no-op, not sent").
- **No** outbound API call is made — no email send, no calendar insert, no file write to the vault from the approve path, no workflow authoring.
- The card leaves the lane and does not reappear unless the agent inserts a new row.

Rejections behave identically except status goes to `rejected` and the `action` describes the rejection.

The `workflow_proposal` card shape is a partial exception: its approval does **not** write the proposed `.flow.md` file in Stage 1. That writeback lands in the later "agent-authoring of workflows" spec (Stage 5 per vision doc). Downstream specs pick up execution by reading `approval_cards` rows with `status='approved'` and dispatching the real effect — this spec does not reserve an "executed_at" column, but a simple ALTER in a future migration will add one without breaking anything here.

---

## Acceptance Criteria

Each AC has a stable ID. UAT and Playwright scripts reference these directly. User-visible ACs MUST be queryable by ARIA role/label or stable `data-testid`.

### Navigation & landing

- [ ] **AC-01:** Visiting `/` (root, authenticated) renders the Today surface — not the legacy task list. `Route index` under the protected `AppShell` points at the new Today page. [F1, A14]
- [ ] **AC-02:** The page has a top-level landmark `<main aria-label="Today">` and an `<h1>` containing today's date in the user's locale. [F2]

### Today sections (S1)

- [ ] **AC-03:** The Today page renders seven labelled regions in order — `Header`, `Your day`, `To do`, `Notes`, `Agent`, `Approvals`, `Recent`. The Header region uses `<header>` (landmark role `banner`); the remaining six use `<section aria-labelledby="today-<name>">` with a heading of the same name. Each has a heading of the same name. Empty sections render an empty state message; they do not disappear. [F2]
- [ ] **AC-04:** The header section shows the date and a one-line framing sentence parsed from `today.md`. When the underlying file has no framing, an empty state "No framing yet — run today's briefing" is shown.
- [ ] **AC-05:** The `Your day` section lists calendar/meeting items parsed from the markdown. Each item is an `<li>` with item text and (if linked) a wikilink target rendered as a link. Empty state: "Nothing on your calendar today."
- [ ] **AC-06:** The `To do` section lists todo items as markdown task list items (`- [ ]` / `- [x]`). Each has an accessible checkbox with `aria-label` containing the item text. Checking/unchecking round-trips to `today.md` on disk via `VaultService.update_body`. Empty state: "No to-dos — the agent hasn't surfaced anything yet."
- [ ] **AC-07:** The `Notes` section has an input with `aria-label="Capture a note"` plus a submit control. Submitting a non-empty note appends it to the Notes section of `today.md` (as a bullet prefixed with an ISO timestamp) and returns the saved note in the response. The input clears on success. The file write goes through `VaultService.update_body` → `StorageSync.sync_file` (fire-and-forget). [A14]
- [ ] **AC-08:** The `Agent` section lists running / watching / recently-done / blocked items, grouped by status with sub-headings. Each item is a link to its deeper target. Stage 1 accepts "placeholder" links that route to `/vault/...` or `/workflows/...` paths even though those surfaces ship later.
- [ ] **AC-09:** The `Approvals` section renders approval cards per AC-12. Empty state: "Nothing awaiting approval."
- [ ] **AC-10:** The `Recent` section shows up to 10 recently-touched vault files, each as a link with filename (JetBrains Mono per D4) and last-edited time (relative, e.g. "4 min ago"). Data source: `VaultService.list_recent(user_id, limit=10)` using filesystem `mtime`, excluding `today.md` and paths under `_workflows/`, `_activity/`, `_runs/`. Empty state: "No recent activity."
- [ ] **AC-11:** The page has a "View source" toggle that swaps the rendered view for a monospace block containing the raw markdown for `today.md`. Toggling back returns to the rendered view with no data loss. [D1]

### Approval lane (S6 — card shapes + no-op Stage 1 execution)

- [ ] **AC-12:** The Approvals section renders zero or more approval cards. Six card shapes are supported, each with distinct region `role="region" aria-label="<Type> approval: <title>"`:
    - `email_draft` — to / subject / body preview; actions: Send, Edit, Reject
    - `calendar_hold` — title / proposed time window; actions: Confirm, Edit, Reject
    - `outreach` — recipient / message / rationale; actions: Send, Edit, Reject
    - `workflow_proposal` — proposed `.flow.md` filename + body preview + rationale; actions: Accept, Edit, Reject
    - `config_change` — file path + diff preview of proposed edit to an agent/skill markdown; actions: Approve, Reject
    - `file_operation` — operation (`move`/`rename`/`delete`), source path, target path (if any); actions: Approve, Reject
- [ ] **AC-13:** Clicking Approve / Send / Confirm / Accept on any card records the approval (status flips to `approved`, `decided_at` and `decided_by` set) and emits an `activity_log` entry per the "No Outbound Effects" contract above. The card disappears from the lane. No outbound API call is made. [A12]
- [ ] **AC-14:** Clicking Reject on any card records the rejection (status `rejected`, optional reason captured from a text input) and emits an `activity_log` entry. Rejected cards do not reappear without a new server-side insert.
- [ ] **AC-15:** Edit on a card (where applicable) opens an inline editor over the card body, lets the user modify editable fields of the `payload`, and saves back. The card remains `pending`. The edit is recorded in `activity_log`.

### Topbar ambient indicator (Stage 1 scope — approvals only)

- [ ] **AC-16:** The topbar shows a single live badge `Approvals` with `aria-label="<N> pending approvals"`. It reflects the count of `pending` rows in `approval_cards` for the current user. The count updates by polling every 15 seconds and is invalidated immediately after any approval mutation. Clicking the badge scrolls the Today page's Approvals section into view. The activity/agent-actions badge is deferred to S7. [A14]

### Regeneration via workflow engine (not a stub)

- [ ] **AC-17:** The header includes a "Regenerate Today" button. Clicking it calls `POST /today/regenerate`, which invokes `WorkflowRunManager.start_run(user_id, 'regenerate-today', {})` from SPEC-036. The endpoint returns 202 with the `run_id`. The workflow writes the regenerated `today.md` via the agent's normal bwrap file-write path; no separate write surface is introduced.
- [ ] **AC-18:** A seed workflow file `regenerate-today.md` ships under `/data/config/system/workflows/` (git-tracked at repo path `data/config/system/workflows/regenerate-today.md`, copied into runtime at deploy time). The template registry (SPEC-036 AC-04) merges it with any user-provided override at `/data/sandboxes/{user_id}/_workflows/regenerate-today.md`, following the existing shadow pattern.
- [ ] **AC-19:** The scheduled morning regeneration uses the existing job queue — a row is created in the `jobs` table with `job_type='regenerate_today'` (dedicated type so `fail_by_type` can cancel precisely without affecting unrelated workflow jobs) and `input={'template_name': 'regenerate-today'}`, handled by a new `handle_regenerate_today` job handler that delegates to `dispatch_workflow('regenerate-today', ...)` (mirrors the morning/evening briefing pattern). A new boolean `today_regeneration_enabled` column on `user_preferences` (default `false`) gates it; when set to `true`, the preferences update creates the first job (same pattern as SPEC-037 AC-31 email-triage). A TEXT column `today_regeneration_time` (default `'06:30'`, user-local) controls the daily time.
- [ ] **AC-20:** The Today UI detects completed regenerations by polling `GET /workflows/runs?template_name=regenerate-today&limit=1` on an interval (30s) and after the user clicks "Regenerate Today". When a newer `status='completed'` run is observed, the UI invalidates `useToday` and refetches. No SSE/websocket in Stage 1.

### Seeding (first-time user)

- [ ] **AC-21:** The first `GET /today` for a user whose sandbox has no `today.md` causes `VaultService` to seed the file from `/data/config/system/templates/today.md` (git-tracked at repo path `data/config/system/templates/today.md`, copied into runtime at deploy time). The seed contains all seven section headings with gentle empty-state prose. The user sees a populated template, not an empty screen.

### Path traversal protection

- [ ] **AC-22:** `VaultService._resolve` rejects any relative path that escapes the user's sandbox root. Handlers that accept a path (e.g. future `GET /today/source?path=...`) return HTTP 403 with a generic error on any escape attempt. Unit test `test_resolve_rejects_traversal` covers the negative matrix: `..` segments, absolute paths, symlinks, and `\x00` bytes. [A12]

### Auth + cross-user isolation

- [ ] **AC-23:** All Today and Approvals endpoints require authentication. Unauthenticated requests return 401. User B cannot read or mutate User A's `today.md`, approval_cards, or activity_log rows. Integration tests cover both filesystem isolation (via VaultService path resolution) and DB RLS (approvals, activity). [A8]

### Housekeeping

- [ ] **AC-24:** `@mui/material`, `@emotion/react`, `@emotion/styled` are removed from `webApp/package.json`. A grep for `@mui/` in `webApp/src/` returns zero matches. `pnpm install` and `pnpm build` still succeed.
- [ ] **AC-25:** `webApp/src/pages/TodayViewMockup.tsx` and the `/today-mockup` route are removed. The old task-list `TodayView.tsx` is deleted (archive not required — it's in git history).
- [ ] **AC-26:** `ChatPanel.tsx` and `ChatPanelV2.tsx` are consolidated to a single `ChatPanel.tsx` export. All callers (`AppShell`, `CoachPageV2`, etc.) import from the consolidated module. `ChatPanelV2.tsx` is deleted. Behavior is byte-for-byte equivalent to the current `V2`.

---

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/20260418000001_create_approval_cards.sql` | `approval_cards` table with card_type enum, payload JSONB, status, RLS |
| `supabase/migrations/20260418000002_create_activity_log.sql` | `activity_log` append-only table (INSERT via service role, SELECT by owner), RLS |
| `supabase/migrations/20260418000003_user_prefs_today_regen.sql` | Add `today_regeneration_enabled` (BOOL, default false) and `today_regeneration_time` (TEXT, default '06:30') to `user_preferences` |
| `chatServer/services/vault_service.py` | Filesystem read/write scoped to `/data/sandboxes/{user_id}/`. Contains `_resolve`, `read_file`, `update_body`, `list_recent`, `seed_if_missing`. Every write calls `StorageSync.sync_file` after success. |
| `chatServer/services/today_service.py` | Compose Today response: VaultService reads `today.md` → section parser → merge with pending approvals + recent activity. Notes append. To-do toggle. Regeneration dispatch (delegates to `WorkflowRunManager`). |
| `chatServer/services/approval_service.py` | CRUD over `approval_cards`. Approve/reject/edit state transitions. Emits `activity_log` entries on every transition. |
| `chatServer/services/activity_log_service.py` | Append-only writer + scoped reader for `activity_log`. |
| `chatServer/services/markdown_sections.py` | Pure functions: parse markdown-with-H2-sections into a dict, and patch a section back into the body without mangling other sections. Used by `today_service`. |
| `chatServer/routers/today_router.py` | `GET /today`, `POST /today/notes`, `POST /today/todo/toggle`, `POST /today/regenerate`, `GET /today/source`. Thin routers delegating to services. [A1] |
| `chatServer/routers/approvals_router.py` | `GET /approvals`, `GET /approvals/count`, `POST /approvals/{id}/approve`, `POST /approvals/{id}/reject`, `POST /approvals/{id}/edit`. [A1] |
| `data/config/system/templates/today.md` (seed, git-tracked) | Populated template with all seven section headings + empty-state prose. Copied into runtime at `/data/config/system/templates/today.md` at deploy time, same convention as existing `data/config/system/{agents,skills,workflows}` subdirs. |
| `data/config/system/workflows/regenerate-today.md` (seed, git-tracked) | `.flow.md` workflow template matching SPEC-036 format. Steps: gather context (calendar + inbox signals + recent activity), compose Today body, write to `today.md` via agent file-write tool. |
| `webApp/src/pages/Today.tsx` | New Today surface. Composes seven section components. |
| `webApp/src/components/today/HeaderSection.tsx` | Date + framing + Regenerate button |
| `webApp/src/components/today/YourDaySection.tsx` | Calendar/meeting items list |
| `webApp/src/components/today/ToDoSection.tsx` | Markdown task-list with checkboxes |
| `webApp/src/components/today/NotesSection.tsx` | Capture input + note list |
| `webApp/src/components/today/AgentSection.tsx` | Running/watching/recent/blocked groups |
| `webApp/src/components/today/ApprovalsSection.tsx` | Approvals container — renders cards per type |
| `webApp/src/components/today/approvals/EmailDraftCard.tsx` | email_draft shape |
| `webApp/src/components/today/approvals/CalendarHoldCard.tsx` | calendar_hold shape |
| `webApp/src/components/today/approvals/OutreachCard.tsx` | outreach shape |
| `webApp/src/components/today/approvals/WorkflowProposalCard.tsx` | workflow_proposal shape |
| `webApp/src/components/today/approvals/ConfigChangeCard.tsx` | config_change shape (diff preview) |
| `webApp/src/components/today/approvals/FileOperationCard.tsx` | file_operation shape |
| `webApp/src/components/today/RecentSection.tsx` | Recently touched docs list |
| `webApp/src/components/today/SourceToggle.tsx` | Rendered ↔ source toggle |
| `webApp/src/components/today/ApprovalsBadge.tsx` | Topbar badge for pending approvals count |
| `webApp/src/api/hooks/useTodayHooks.ts` | `useToday`, `useTodaySource`, `useAppendNote`, `useToggleTodo`, `useRegenerateToday`, `useRegenerationStatus` (poll workflow_runs). [A4] |
| `webApp/src/api/hooks/useApprovalsHooks.ts` | `useApprovals`, `useApprovalsCount`, `useApproveCard`, `useRejectCard`, `useEditCard`. [A4] |
| `webApp/src/api/types/today.ts` | `TodayResponse`, `ApprovalCard` tagged union, `ApprovalsCount`. |
| `tests/uat/playwright/test_spec_045_today_surface.py` | One Playwright function per user-visible AC. Written BEFORE frontend implementation. |
| `tests/unit/services/test_vault_service.py` | Path resolution (positive + negative matrix), read/write round-trip, sync_file invocation, seeding |
| `tests/unit/services/test_today_service.py` | Section composition, notes append, todo toggle, regenerate dispatch |
| `tests/unit/services/test_approval_service.py` | State transitions, activity_log emission, cross-user isolation |
| `tests/unit/services/test_activity_log_service.py` | Append, list_recent, RLS |
| `tests/unit/services/test_markdown_sections.py` | Parser + patch round-trip |
| `tests/integration/test_today_api.py` | Auth, filesystem isolation, notes/todo round-trips |
| `tests/integration/test_approvals_api.py` | Auth, RLS, approval state machine |
| `tests/integration/test_today_regeneration.py` | Regenerate endpoint dispatches a workflow run and returns its run_id; completion surfaces via `/workflows/runs` poll |

### Files to Modify

| File | Change |
|------|--------|
| `webApp/src/App.tsx` | Replace `TodayView` route (both `/today` and index) with `Today`. Remove `/today-mockup` route and `TodayViewMockup` import. |
| `webApp/src/components/navigation/TopBar.tsx` | Insert `ApprovalsBadge` between streak block and `ThemeToggle`. Wire to `useApprovalsCount`. |
| `webApp/src/components/ChatPanel.tsx` | Absorb `ChatPanelV2` body into this file. |
| `webApp/src/pages/CoachPageV2.tsx` | Update import from `ChatPanelV2` to `ChatPanel`. |
| `webApp/src/pages/TodayView.tsx` | Delete (AC-25). |
| `webApp/src/pages/TodayViewMockup.tsx` | Delete (AC-25). |
| `webApp/src/components/ChatPanelV2.tsx` | Delete (AC-26). |
| `webApp/package.json` | Remove `@mui/material`, `@emotion/react`, `@emotion/styled`. |
| `chatServer/main.py` (or equivalent router registry) | Register `today_router`, `approvals_router`. |
| `chatServer/services/job_handlers.py` | Verify `handle_workflow` already covers `template_name='regenerate-today'`; no change expected. Wire `user_preferences` update side-effect to create the first `jobs` row (reuse SPEC-037 pattern). |

### Out of Scope

- **S2 vault browser** — SPEC-046
- **S3 file detail + CodeMirror 6 editor** — SPEC-047. "View source" in AC-11 renders a read-only monospace block, not a full editor.
- **S4 workflow editor** — SPEC-048. The `regenerate-today.md` seed is authored by a human; user editing of it is deferred.
- **⌘K palette** — separate spec
- **Full activity log screen** (S7) — later spec; this spec emits to `activity_log` so S7 has data
- **Agent-authoring of workflow_proposal cards into `.flow.md` files** — Stage 5 per vision; the card shape ships here
- **Actual outbound execution of approved cards** — Stage 3; "No Outbound Effects" contract above is explicit
- **Real-time websocket updates** — polling suffices for Stage 1 (AC-16, AC-20)
- **Rich capture (voice, clipboard)** — Stage 2
- **Cross-device sync beyond what StorageSync already provides** — vision-level deferral
- **Any DB-backed vault store (e.g. `vault_documents` table)** — explicitly rejected per OQ-1 decision
- **Two-way sync with Obsidian edits made while the web app is offline** — see OQ-D

---

## Technical Approach

### 1. VaultService — the filesystem chokepoint

Single class, ~150 lines. Key methods:

```python
class VaultService:
    def __init__(self, storage_sync: StorageSync, data_dir: Path = Path("/data")):
        self._sync = storage_sync
        self._root = data_dir / "sandboxes"
        self._system = data_dir / "config" / "system"

    def _resolve(self, user_id: str, rel_path: str) -> Path:
        """Resolve rel_path against user's vault root. Raise 403 on escape."""
        user_root = (self._root / user_id).resolve(strict=False)
        if os.path.isabs(rel_path) or "\x00" in rel_path:
            raise HTTPException(403)
        candidate = (user_root / rel_path).resolve(strict=False)
        if not candidate.is_relative_to(user_root):
            raise HTTPException(403)
        # Walk components and reject any symlink
        probe = user_root
        for seg in candidate.relative_to(user_root).parts:
            probe = probe / seg
            if probe.is_symlink():
                raise HTTPException(403)
        return candidate

    async def read_file(self, user_id: str, rel_path: str) -> str: ...
    async def update_body(self, user_id: str, rel_path: str, new_body: str) -> None:
        """Write then fire-and-forget sync to Storage."""
        path = self._resolve(user_id, rel_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_body)
        asyncio.create_task(self._sync.sync_file(user_id, rel_path))

    async def seed_if_missing(self, user_id: str, rel_path: str, template_rel: str) -> None:
        """If rel_path doesn't exist under user_id, copy /data/config/system/<template_rel>."""

    async def list_recent(self, user_id: str, limit: int = 10, exclude: list[str] | None = None) -> list[RecentEntry]:
        """Walk the user sandbox, return most recently modified files by mtime,
        excluding `today.md` and paths under `_workflows/`, `_activity/`, `_runs/` by default."""
```

**Why this is acceptable without RLS:** the single attack surface is `_resolve`. It's unit-tested with a negative-cases matrix (AC-22). It is called from the Today, Approvals (for payload path references like config_change diffs), and regeneration routers. No other code constructs vault paths from untrusted input.

**Concurrency:** two simultaneous note captures from different tabs race. Stage 1 accepts last-write-wins on `today.md` with an `If-Match` header carrying the client's last-seen mtime; if server mtime differs, return 409. `useAppendNote` retries once with the fresh body, then toasts.

### 2. today_service composition

`GET /today` returns:

```ts
interface TodayResponse {
  date: string;
  header: { framing: string | null };
  your_day: Array<{ text: string; wikilink?: string }>;
  to_do: Array<{ line_id: string; text: string; checked: boolean }>;
  notes: Array<{ created_at: string; text: string }>;
  agent: {
    running: AgentItem[];
    watching: AgentItem[];
    recent: AgentItem[];
    blocked: AgentItem[];
  };
  approvals: ApprovalCard[];
  recent: Array<{ path: string; updated_at: string }>;
  source_mtime: string;
}
```

Implementation: read `today.md` → `markdown_sections.parse()` → hydrate each section (most just pass parsed strings; `approvals` joins from DB; `recent` comes from `VaultService.list_recent`). Section parser uses H2 headings as boundaries, recognizes seven known section names, preserves unknown sections (stored but not rendered).

**To-do line_id:** stable hash of (section, line-index, raw text). Used by `POST /today/todo/toggle` to locate the line to edit. If the file has been rewritten and the line_id no longer matches, return 409.

**Notes append:** read body → find Notes section → append `- [YYYY-MM-DDTHH:MM:SSZ] <text>` under it → write body back → trigger sync_file.

### 3. approval_cards schema

```sql
CREATE TYPE approval_card_type AS ENUM (
    'email_draft', 'calendar_hold', 'outreach',
    'workflow_proposal', 'config_change', 'file_operation'
);
CREATE TYPE approval_card_status AS ENUM ('pending', 'approved', 'rejected');

CREATE TABLE approval_cards (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    card_type     approval_card_type NOT NULL,
    title         TEXT NOT NULL,
    payload       JSONB NOT NULL,
    status        approval_card_status NOT NULL DEFAULT 'pending',
    rationale     TEXT,
    source_ref    TEXT,
    decided_at    TIMESTAMPTZ,
    decided_by    UUID REFERENCES auth.users(id),
    decision_note TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ON approval_cards(user_id, status, created_at DESC);
-- RLS: user SELECT/UPDATE own; INSERT via service role only (agent-side).
```

Payload shapes (TypeScript discriminated union in `api/types/today.ts`):

- `email_draft`: `{ to: string[]; subject: string; body: string; thread_ref?: string }`
- `calendar_hold`: `{ title: string; start_at: string; end_at: string; source_ref?: string }`
- `outreach`: `{ recipient: string; message: string; channel: 'email'|'telegram'|'other' }`
- `workflow_proposal`: `{ filename: string; body: string; pattern_observed: string }`
- `config_change`: `{ file_path: string; diff: string; summary: string }`
- `file_operation`: `{ operation: 'move'|'rename'|'delete'; source: string; target?: string }`

Service layer validates with a discriminated union before insert/update.

### 4. activity_log schema

```sql
CREATE TABLE activity_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    actor           TEXT NOT NULL,
    action          TEXT NOT NULL,
    subject_path    TEXT,
    workflow_run_id UUID REFERENCES workflow_runs(id) ON DELETE SET NULL,
    status          TEXT NOT NULL CHECK (status IN ('done','failed','awaiting_approval')),
    reasoning       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ON activity_log(user_id, created_at DESC);
-- RLS: user SELECT own. INSERT via service role.
```

Stage 1 writes to this on every approval transition. No Stage 1 read endpoint (per OQ-4 revised decision). S7 will add `GET /activity` when the full log screen ships.

### 5. Regeneration — real workflow dispatch, not a stub

**Endpoint:**

```python
# today_router.py
@router.post("/today/regenerate", status_code=202)
async def regenerate_today(user_id: UUID = Depends(get_current_user_id),
                            manager: WorkflowRunManager = Depends(get_run_manager)):
    run_id = await manager.start_run(
        user_id=str(user_id),
        template_name="regenerate-today",
        parameters={},
    )
    return {"run_id": run_id}
```

**Template:** `regenerate-today.md` ships in system config (SPEC-036 AC-04 shadow pattern). Illustrative structure:

```markdown
---
name: regenerate-today
description: Rebuild today.md from calendar, inbox signals, approvals, and recent activity
version: 1
default_gate_policy: none
---

## Parameters
| Parameter | Required | Description |
|-----------|----------|-------------|
| date | no | Target date (default: today, user local) |

## Steps

### step-1: Gather context
- **agent:** today-gather
- **depends_on:** []
- **tools:** [search_gmail, list_calendar_events]
- **description:** Collect today's calendar, last-24h important mail, recent vault activity.

### step-2: Compose Today
- **agent:** today-composer
- **depends_on:** [step-1]
- **tools:** [write_file]
- **description:** Produce a `today.md` body matching the seven-section layout and write it to today.md.
```

Final step uses the agent's normal bwrap `write_file` tool → writes `/user/today.md` inside the sandbox → which is `/data/sandboxes/{user_id}/today.md` on the host. No new write path.

**Morning schedule:** `user_preferences.today_regeneration_enabled` + `today_regeneration_time`. A preferences-update handler (existing pattern from SPEC-037 AC-31) creates the first job in `jobs` table with `job_type='regenerate_today'` and `input={template_name: 'regenerate-today'}`. A new `handle_regenerate_today` handler is registered in `background_tasks.py`; it delegates to `dispatch_workflow('regenerate-today', ...)` and self-schedules. Dedicated type (vs bare `workflow`) so `fail_by_type` can cancel precisely when the user toggles the feature off.

**UI completion signal:** `useRegenerationStatus` polls `GET /workflows/runs?template_name=regenerate-today&limit=1` every 30s. When the latest run's `completed_at` is newer than what the UI rendered, it invalidates the `useToday` query. Accepted latency: up to 30s after workflow completion. (SSE via `workflow_events` is available from SPEC-036 but requires wiring a client-side EventSource — deferred to a later spec where other surfaces also need push updates.)

### 6. Frontend composition

- React Query for all server state. Client-only state (source/rendered toggle, inline edit state) in component state.
- Polling: `useApprovalsCount` at 15s, `useRegenerationStatus` at 30s. Both invalidate on relevant mutations.
- Typography: Inter for UI, JetBrains Mono for filenames/paths/timestamps/diffs (D4).
- Every AC-covered element has ARIA role/label; Playwright scripts written first.

### 7. Dependencies

Existing: Supabase auth + RLS, `get_user_scoped_client`/`get_system_client`, React Query, `react-markdown` + `remark-gfm`, SPEC-036 workflow engine (`WorkflowRunManager`, template registry), SPEC-044 bwrap sandbox, `StorageSync`.

No new libraries. Downstream libraries (CodeMirror 6, cmdk, etc.) ship with later specs.

---

## Testing Requirements

### Unit Tests (required)

- `test_vault_service.py`: path resolution positive cases (valid nested paths), negative matrix (absolute paths, `..` segments, null bytes, symlink components), read/write round-trip, seed_if_missing copies from system, update_body fires StorageSync.sync_file.
- `test_markdown_sections.py`: parse preserves unknown sections; patch round-trip is idempotent; empty section body handled; ordering preserved.
- `test_today_service.py`: composition from parsed body + approvals + recent; notes append to correct section; todo toggle flips correct line; regeneration delegates to WorkflowRunManager.
- `test_approval_service.py`: pending → approved/rejected transitions; rejected doesn't reappear; activity_log entry emitted on every transition; cross-user 404.
- `test_activity_log_service.py`: append, ordering, RLS isolation.

### Integration Tests (required)

- `test_today_api.py`: auth required; User A cannot read User B's `today.md`; notes round-trip through disk and back; todo toggle round-trip; If-Match 409 on stale mtime.
- `test_approvals_api.py`: auth + RLS; full state machine; six card shapes accepted on insert (service role); edit persists payload; activity_log populated.
- `test_today_regeneration.py`: `POST /today/regenerate` returns run_id; the workflow run appears in `workflow_runs`; when the workflow completes, `/workflows/runs` poll returns it; preferences toggle creates a job.

### UI Acceptance Tests (Playwright — written BEFORE implementation)

Script: `tests/uat/playwright/test_spec_045_today_surface.py`. One function per user-visible AC. Selectors target ARIA role/label.

| AC | Flow / Service Test | UI Test (Playwright) |
|----|---------------------|---------------------|
| AC-01 | `test_ac_01_root_route_renders_today` | `test_ac_01_root_route_renders_today` |
| AC-02 | — | `test_ac_02_main_landmark_and_heading` |
| AC-03 | — | `test_ac_03_seven_sections_in_order` |
| AC-04 | `test_ac_04_header_framing` | `test_ac_04_header_framing` |
| AC-05 | — | `test_ac_05_your_day_list` |
| AC-06 | `test_ac_06_todo_roundtrip` | `test_ac_06_todo_checkbox_roundtrip` |
| AC-07 | `test_ac_07_note_capture_roundtrip` | `test_ac_07_note_capture_roundtrip` |
| AC-08 | — | `test_ac_08_agent_section_groups` |
| AC-09 | — | `test_ac_09_approvals_empty_state` |
| AC-10 | `test_ac_10_recent_from_mtime` | `test_ac_10_recent_list_renders` |
| AC-11 | — | `test_ac_11_source_toggle_roundtrip` |
| AC-12 | — | `test_ac_12_all_six_card_shapes_render` |
| AC-13 | `test_ac_13_approve_logs_no_execute` | `test_ac_13_approve_logs_no_execute` |
| AC-14 | `test_ac_14_reject_persists` | `test_ac_14_reject_persists` |
| AC-15 | `test_ac_15_edit_roundtrip` | `test_ac_15_edit_roundtrip` |
| AC-16 | `test_ac_16_approvals_count` | `test_ac_16_approvals_badge` |
| AC-17 | `test_ac_17_regenerate_dispatches_run` | `test_ac_17_regenerate_button_dispatches` |
| AC-18 | `test_ac_18_seed_workflow_registered` | — |
| AC-19 | `test_ac_19_preferences_toggle_creates_job` | — |
| AC-20 | `test_ac_20_completion_polled` | `test_ac_20_today_refetches_on_completion` |
| AC-21 | `test_ac_21_first_login_seeds_template` | `test_ac_21_first_login_populated` |
| AC-22 | `test_ac_22_resolve_rejects_traversal` | — |
| AC-23 | `test_ac_23_cross_user_forbidden` | — |
| AC-24 | CI check: `grep @mui webApp/src` returns nothing | — |
| AC-25 | CI check: no import of TodayView/TodayViewMockup | — |
| AC-26 | CI check: no import of ChatPanelV2 | — |

### Manual Verification (UAT)

1. Sign in as dev user with empty sandbox — verify Today renders seeded template.
2. Add a note — verify immediate appearance, reload → still there, inspect `/data/sandboxes/<uid>/today.md` on disk to confirm the bullet landed.
3. Check and uncheck a to-do — verify file contents flip between `- [ ]` and `- [x]`.
4. Toggle "View source" — verify raw markdown matches disk.
5. Seed each of six approval card types via SQL — verify all six render.
6. Approve one card → verify activity_log row + count badge decrement + card disappears.
7. Reject one card with reason → verify rejection persists.
8. Click "Regenerate Today" → verify `workflow_runs` row appears, runs to completion, and `today.md` on disk is rewritten. UI refetches within 30s.
9. Enable `today_regeneration_enabled` in preferences → verify a `jobs` row is created with `job_type='regenerate_today'`.
10. Sign in as second dev user — verify no cross-user leakage via any endpoint.
11. `curl` a vault-source endpoint with a path like `../../../etc/passwd` with a valid JWT → expect 403.
12. `grep -r "@mui" webApp/src` → expect nothing.

---

## Edge Cases

- **First login with no `today.md`:** `VaultService.seed_if_missing` copies `/data/config/system/templates/today.md` into `/data/sandboxes/{uid}/today.md` before first render. (AC-21.)
- **Sandbox dir doesn't exist yet for a new user:** `StorageSync.hydrate_user` runs on session open (existing wiring in `deep_agent_builder`). If a Today request races ahead of session open, `VaultService` creates the dir + seeds. Either path leaves the same file on disk.
- **Concurrent note captures from two tabs:** last-write-wins with `If-Match` on mtime. First write succeeds; second returns 409; client retries with fresh body; toast on second failure.
- **Symlink in user's vault:** rejected by `_resolve` (AC-22 guard). Agents should not create symlinks; if one appears, VaultService returns 403 on any request that touches it. Logged as warning for manual intervention.
- **Malformed markdown in `today.md`:** section parser falls back to "render body as-is under each section, none recognized." UI shows an error chip "Couldn't parse sections — open source to edit." No data loss.
- **`today.md` >1MB:** rendering truncates for display; disk copy untouched. Hard cap at 10MB on write — reject beyond that with 413.
- **StorageSync.sync_file fails:** logged as warning; local write is authoritative. Retry happens on next write to the same file (fire-and-forget pattern). Acceptable Stage 1 posture; a later spec can add a sync-queue.
- **Workflow engine unavailable when user clicks Regenerate:** endpoint returns 503; toast surfaces "Regeneration temporarily unavailable, try again shortly."
- **Scheduled regeneration collides with manual regenerate:** each creates a distinct workflow run with its own `run_id`. Whichever completes later wins the `today.md` contents (normal overwrite). Both are logged in `workflow_runs`.
- **Regeneration workflow fails mid-run:** `workflow_runs.status='failed'`. UI shows "Last regeneration failed — check logs" with a link to the run. No Today update.
- **Approval card payload missing a required field:** insert rejected by discriminated-union validator (500 service-side). Frontend cards that fail the client-side type guard log a warning and skip rendering; the lane does not crash.
- **User rejects then agent re-proposes the same thing:** allowed — it's a new card row with a fresh `id`. Rejection is about the row, not the underlying subject.
- **Rejected a card that the UI hasn't refreshed:** client tries to approve or edit → backend returns 409 + latest card state; UI reconciles.
- **User edited `today.md` directly in Obsidian between sessions:** per OQ-D, Stage 1 has no Obsidian integration. The hydrate no-op means local disk is authoritative once populated; edits made elsewhere won't sync back. Known limitation.

---

## Functional Units (for PR Breakdown)

### FU-1: Migrations + seeds (database-dev)
**Branch:** `feat/SPEC-045-migrations`
**ACs (prerequisites for):** AC-16, AC-19, AC-21, AC-23
- `approval_cards` + enums + RLS
- `activity_log` + RLS
- `user_preferences` columns for regeneration enable/time
- Seed files (`today.md` template, `regenerate-today.md` workflow) committed under `data/config/system/{templates,workflows}/` — git-tracked; copied into runtime `/data/config/system/` at deploy time (matching existing `data/config/system/{agents,skills,workflows}` convention). No bucket upload, no `StorageSync.pull_system()` wiring in this spec.

### FU-2: Backend services + API + workflow coupling (backend-dev)
**Branch:** `feat/SPEC-045-api`
**Depends on:** FU-1
**ACs:** AC-06/07 server paths, AC-13/14/15, AC-16 count endpoint, AC-17/18/19/20, AC-21, AC-22, AC-23
- `VaultService` (the security chokepoint)
- `markdown_sections` pure parser
- `today_service`, `approval_service`, `activity_log_service`
- `today_router`, `approvals_router`
- Preferences update wiring to create the jobs row (reuse SPEC-037 pattern)
- Full unit + integration test suite

### FU-3: Frontend Today + housekeeping (frontend-dev)
**Branch:** `feat/SPEC-045-ui`
**Depends on:** FU-2; Playwright scripts from UX agent land first
**ACs:** AC-01–AC-12, AC-13–AC-17 UI, AC-20 UI, AC-21 UI, AC-24, AC-25, AC-26
- `Today.tsx`, seven section components, six approval-card components, `SourceToggle`, `ApprovalsBadge`
- React Query hook modules
- Route swap in `App.tsx`; TopBar wired to badge
- Housekeeping bundled in (MUI removal, mockup/archive deletion, ChatPanel consolidation) — all touch the same package and deploy together

**Merge order:** FU-1 → FU-2 → FU-3. Linear, no parallelism.

---

## Open Questions (new, surfaced during rewrite)

### OQ-A. regenerate-today workflow — composer prompt quality

The seed workflow needs a concrete prompt for the composer step. The step must produce a seven-section markdown body, use wikilinks for entities, and respect the user's preferred framing tone. This is less a scope question than an "author the prompt" one — reasonable to punt to the implementer, but flagging that the workflow template's quality is load-bearing on the Stage 1 primary exit criterion ("does Today replace the inbox").

**Recommendation:** land the spec with a minimal composer prompt, then iterate the prompt in a follow-up PR against the kill criterion. Do not treat the prompt as frozen.

### OQ-B. `handle_workflow` job handler — does it already exist?

SPEC-036 AC-27 defined `handle_workflow` as a generic `job_type='workflow'` handler. I did not fully verify in the codebase that this exact handler is wired today — if it isn't, FU-2 grows by the size of that handler. A 10-minute grep during implementation-start will confirm.

**Recommendation:** implementer runs that grep before starting FU-2; if missing, add it as a line item.

### OQ-C. Completion signal — poll vs SSE

Stage 1 uses 30s polling against `GET /workflows/runs?template_name=regenerate-today&limit=1`. SPEC-036 AC-22 ships SSE injection of `workflow_event` messages for chat. Wiring an EventSource client just for the Regenerate button is over-scope for Stage 1. Acceptable latency is 30s.

**Recommendation:** polling now; revisit push when another surface (S7 activity log or S4 workflow editor) already needs EventSource.

### OQ-D. StorageSync hydrate cadence

`StorageSync.hydrate_user` is no-op when the user dir already has content ("local disk is source of truth once populated"). That means edits a user makes in Obsidian on another machine don't land back into the web app. Stage 1 has no Obsidian integration, so this is acceptable — but worth noting as a known limitation.

**Recommendation:** accept for Stage 1; document in manual UAT steps and edge cases. Two-way sync is a later spec.

---

## Vision/functional doc consistency notes (not blocking)

1. **`clarity-as-vault-functional.md` S7 Ambient Indicator** reads "Persistent ambient indicator in the topbar ('watching 3 threads, 2 approvals') opens the full log." Per the revised OQ-4 decision the Stage 1 topbar shows *only* approvals. Consider clarifying: "Stage 1 ships with approvals-only badge; the activity count ships with S7 once the full log screen exists."
2. **`clarity-as-vault.md` Stage 1 bullet** says "web app renders the vault." This spec renders `today.md` through a specialized view but does not ship the vault browser (S2). Consider clarifying: "web app renders Today; full vault browser ships with S2."

Both are doc nits; neither changes this spec.

---

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-26)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (filesystem chokepoint → API shapes → TypeScript types → ARIA selectors)
- [x] Technical decisions cite principles (A1, A4, A8, A12, A14; F1, F2; D1–D5)
- [x] Merge order is explicit and acyclic (FU-1 → FU-2 → FU-3)
- [x] Out-of-scope is explicit and enumerates downstream specs
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs (table)
- [x] Existing infrastructure section enumerates every reused primitive
- [x] Access control model spelled out for filesystem-backed storage (no hand-waving)
- [x] "No Outbound Effects" contract stated explicitly
- [x] New open questions surfaced with recommendations
