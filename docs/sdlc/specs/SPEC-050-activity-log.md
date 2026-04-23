# SPEC-050: Agent Activity Log (S7)

> **Status:** Draft
> **Author:** spec-writer (Claude) on behalf of Tim
> **Created:** 2026-04-21
> **Vision:** [`docs/sdlc/visions/clarity-as-vault.md`](../visions/clarity-as-vault.md)
> **Directive:** [`docs/sdlc/visions/clarity-as-vault-functional.md`](../visions/clarity-as-vault-functional.md) (S7, ambient indicator notes in S1 and S6)
> **Stage:** Clarity-as-Vault Stage 1 (pull-model transparency surface)

---

## Goal

Ship the **agent activity log** defined as S7 in the functional directive -- the pull-model transparency surface. This is the append-only, immutable journal of everything the agent does, reachable from a persistent topbar indicator and from the Today "Agent" section. The user inspects, trusts, and audits agent behavior through this log.

SPEC-045 created the `activity_log` table, the `ActivityLogService` (append + list_recent), and wired writes on every approval transition. This spec adds the **read API** (with pagination, filtering, and search), the **activity log panel UI**, and **extends the topbar ambient indicator** from approvals-only to include activity counts ("watching 3 threads, 2 approvals").

The activity log is immutable from the user's perspective -- users can read and filter, never edit or delete entries. The agent can only append. This asymmetry is the trust guarantee: the log is a faithful, unforgeable record of agent behavior.

**Contrast with S4 run history:** workflow run history (SPEC-036 `workflow_runs`) shows workflow-level status. The activity log shows every individual action. One workflow run = one history entry + N activity log entries.

---

## Existing Infrastructure (what we reuse verbatim)

| Primitive | Location | What we use it for |
|-----------|----------|---------------------|
| `activity_log` table | `supabase/migrations/20260420000002_create_activity_log.sql` | Already exists with the correct schema. No migration needed. |
| RLS policies | `supabase/migrations/20260421000001_fix_approval_cards_activity_log_rls.sql` | Uses `public.is_record_owner(user_id)` for SELECT. INSERT is service-role only. |
| `ActivityLogService` | `chatServer/services/activity_log_service.py` | Append + `list_recent(user_id, limit)`. This spec extends it with pagination, filtering, search, and count methods. |
| `ApprovalService` activity writes | `chatServer/services/approval_service.py` | Every approval transition already emits an `activity_log` row. |
| `ApprovalsBadge` | `webApp/src/components/today/ApprovalsBadge.tsx` | Approvals-only badge in topbar. This spec extends it to an `AmbientIndicator` that shows both approvals and activity counts. |
| Auth dependency | `chatServer/dependencies/auth.py` (ES256 JWT) | Every endpoint resolves `user_id` from the JWT. |
| Scoped DB client | `chatServer/database/scoped_client.py` | `get_user_scoped_client` for reads, `create_system_client` for writes. [A8] |
| User-scoped tables registry | `chatServer/database/user_scoped_tables.py` | `activity_log` already registered. |
| React Query hooks pattern | `webApp/src/api/hooks/useApprovalsHooks.ts` | Pattern reference for the new activity hooks. [A4] |
| TypeScript types pattern | `webApp/src/api/types/today.ts` | Pattern reference for the new activity types. |
| TopBar | `webApp/src/components/navigation/TopBar.tsx` | Insertion point for the expanded ambient indicator. |

---

## Access Control Model

The activity log inherits the access control model established in SPEC-045:

1. **Read path:** All `GET /api/activity` endpoints use `Depends(get_current_user)` for auth and `get_user_scoped_client` for DB access. RLS enforces `public.is_record_owner(user_id)` -- user A cannot read user B's activity. [A8]
2. **Write path:** `INSERT` is service-role only (the existing RLS policy). No user-facing write endpoint exists. The `ActivityLogService.append()` method uses the system client. Users cannot forge, edit, or delete activity entries.
3. **Immutability:** No `UPDATE` or `DELETE` policies exist on `activity_log`. The table is append-only by RLS design. This spec does not add any mutation endpoints.

---

## Acceptance Criteria

Each AC has a stable ID. UAT and Playwright scripts reference these directly. User-visible ACs MUST be queryable by ARIA role/label or stable `data-testid`.

### Activity log API

- [ ] **AC-01:** `GET /api/activity` returns a paginated list of the current user's activity log entries, ordered by `created_at DESC`. Response shape: `{ items: ActivityEntry[], total: number, has_more: boolean }`. Default page size is 50, max 100. [A1, A8]
- [ ] **AC-02:** `GET /api/activity` supports cursor-based pagination via `?before=<created_at ISO>` parameter. The `before` value is the `created_at` of the last entry on the current page. Responses include `has_more: true` when more entries exist before the cursor. [A14]
- [ ] **AC-03:** `GET /api/activity` supports filtering by workflow run: `?workflow_run_id=<uuid>`. When provided, returns only entries linked to that run. Returns an empty list (not 404) when no entries match.
- [ ] **AC-04:** `GET /api/activity` supports filtering by status: `?status=done|failed|awaiting_approval`. Multiple statuses can be comma-separated: `?status=done,failed`.
- [ ] **AC-05:** `GET /api/activity` supports text search: `?q=<search term>`. Searches across `action` and `actor` fields using case-insensitive `ILIKE '%term%'`. Combined with other filters via AND.
- [ ] **AC-06:** `GET /api/activity/count` returns `{ total: number, since_last_viewed: number }`. The `since_last_viewed` count uses a `last_activity_viewed_at` timestamp stored in `user_preferences`. Returns `total` as the full count of activity entries, `since_last_viewed` as entries with `created_at > last_activity_viewed_at`. [A1]
- [ ] **AC-07:** `POST /api/activity/mark-viewed` updates `user_preferences.last_activity_viewed_at` to the current UTC timestamp and returns `{ marked_at: string }`. This endpoint is called when the user opens the activity log panel.
- [ ] **AC-08:** All activity endpoints require authentication. Unauthenticated requests return 401. User B cannot read User A's activity log entries. [A8, A12]

### Topbar ambient indicator (expanded)

- [ ] **AC-09:** The topbar replaces the `ApprovalsBadge` with an `AmbientIndicator` component. The indicator shows two counts: pending approvals and new activity entries (since last viewed). Format: the approvals badge (bell icon + count, existing behavior) plus an activity badge (activity icon + count of unseen entries). Each badge is independently clickable. `aria-label` for the approvals badge remains `"<N> pending approvals"`. The activity badge has `aria-label="<N> new agent actions"`. [A14]
- [ ] **AC-10:** The activity count in the indicator reflects `since_last_viewed` from `GET /api/activity/count`. It polls every 30 seconds. When the count is 0, the activity badge renders with reduced opacity (same pattern as the existing approvals badge at count=0). The count updates immediately after `POST /api/activity/mark-viewed` succeeds (optimistic update). [A4]
- [ ] **AC-11:** Clicking the approvals badge scrolls the Today page's Approvals section into view (existing behavior, preserved). Clicking the activity badge opens the activity log panel (AC-12).

### Activity log panel

- [ ] **AC-12:** The activity log renders as a slide-in panel from the right edge, overlaying the content area (same mechanical pattern as the existing ChatPanel slide-in). It has `role="complementary"` and `aria-label="Agent activity log"`. A close button with `aria-label="Close activity log"` dismisses it. Opening the panel triggers `POST /api/activity/mark-viewed`.
- [ ] **AC-13:** The panel header contains: a title "Activity Log", a search input with `aria-label="Search activity log"`, and filter controls for status (dropdown: All / Done / Failed / Awaiting approval) and workflow (dropdown populated from distinct `workflow_run_id` values in the loaded entries, plus "All workflows"). [A14]
- [ ] **AC-14:** Each activity entry renders as an `<article>` with `aria-label="Activity: <action text>"`. Entry layout:
    - Timestamp (JetBrains Mono per D4, relative format matching RecentSection -- "4 min ago", "2 hr ago")
    - Actor name (text, e.g. "approval-service", "today-composer")
    - Action text (plain prose, one sentence)
    - Status indicator: `done` = green dot, `failed` = red dot, `awaiting_approval` = amber dot. Each dot has `aria-label="Status: <status>"`.
    - Subject path (if present): rendered in JetBrains Mono as a clickable link. Clicking navigates to `/vault/<subject_path>`.
    - Workflow run link (if `workflow_run_id` present): rendered as a chip "Run: <short id>". Clicking navigates to the workflow run detail (placeholder link to `/vault/_workflows/_runs/<id>` until S4 ships).
    - Reasoning (if present): collapsed by default behind a "Why?" toggle button. Expanding reveals the reasoning text. This implements the "medium transparency" model from the functional directive -- reasoning is available but not visually dominant.
- [ ] **AC-15:** The entry list supports infinite scroll. When the user scrolls to the bottom and `has_more` is true, the next page is fetched using the `before` cursor. A loading indicator appears during fetch. [A14]
- [ ] **AC-16:** When the log is empty (no entries at all), the panel shows: "No agent activity yet. Actions will appear here as the agent works." When filters produce no results, the panel shows: "No matching entries. Try adjusting your filters."
- [ ] **AC-17:** Search is debounced (300ms). Typing in the search input updates the `q` parameter and refetches from the API. The search input has `type="search"` for native clear button support.

### Today "Agent" section integration

- [ ] **AC-18:** The Today page's Agent section (SPEC-045 AC-08) adds a "View activity log" link at the bottom of the section. Clicking it opens the activity log panel (same as clicking the topbar activity badge). The link has `aria-label="View full activity log"`.

### Cross-user isolation

- [ ] **AC-19:** Integration tests confirm that User A cannot read User B's activity log entries via `GET /api/activity` or `GET /api/activity/count`. The RLS policy enforces this without application-level filtering. [A8]

---

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/20260422000001_user_prefs_last_activity_viewed.sql` | Add `last_activity_viewed_at TIMESTAMPTZ` column to `user_preferences` (default NULL, meaning "never viewed"). |
| `chatServer/routers/activity_router.py` | `GET /api/activity`, `GET /api/activity/count`, `POST /api/activity/mark-viewed`. Thin routers delegating to services. [A1] |
| `webApp/src/api/hooks/useActivityHooks.ts` | `useActivityLog` (paginated, filtered), `useActivityCount`, `useMarkActivityViewed`. [A4] |
| `webApp/src/api/types/activity.ts` | `ActivityEntry`, `ActivityListResponse`, `ActivityCountResponse`, `ActivityFilters`. |
| `webApp/src/components/activity/ActivityPanel.tsx` | Slide-in panel container: header, search, filters, entry list. |
| `webApp/src/components/activity/ActivityEntry.tsx` | Single entry renderer: timestamp, actor, action, status dot, subject link, workflow link, reasoning toggle. |
| `webApp/src/components/activity/ActivityFilters.tsx` | Status dropdown + workflow dropdown + search input. |
| `webApp/src/components/activity/AmbientIndicator.tsx` | Combined topbar indicator: approvals badge + activity badge. Replaces `ApprovalsBadge` in the topbar. |
| `tests/unit/services/test_activity_log_service_extended.py` | Pagination, filtering, search, count methods. |
| `tests/integration/test_activity_api.py` | Auth, RLS, pagination, filtering, search, mark-viewed, cross-user isolation. |
| `tests/uat/playwright/test_spec_050_activity_log.py` | One Playwright function per user-visible AC. Written BEFORE frontend implementation. |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/activity_log_service.py` | Add `list_paginated`, `count`, `count_since` methods. Existing `append` and `list_recent` unchanged. |
| `chatServer/main.py` (or equivalent router registry) | Register `activity_router`. |
| `webApp/src/components/navigation/TopBar.tsx` | Replace `ApprovalsBadge` with `AmbientIndicator`. |
| `webApp/src/components/today/AgentSection.tsx` | Add "View activity log" link at the bottom. |
| `webApp/src/components/today/ApprovalsBadge.tsx` | Kept as-is (imported by `AmbientIndicator`). Not deleted -- the approvals portion of the indicator reuses it. |

### Out of Scope

- **SSE / WebSocket for real-time updates** -- polling at 30s is consistent with SPEC-045's approach (AC-16, AC-20 there). Push updates revisit when another surface needs EventSource.
- **Agent-side activity writes beyond approval transitions** -- SPEC-052 (approval execution, Stage 3) and future workflow-step specs will write more activity entries. This spec's API is designed to accommodate any `actor`/`action`/`status` combination.
- **Activity log as a standalone route** -- per D2, the activity log is a panel reachable from Today and the topbar, not a dedicated route.
- **Editing or deleting activity entries** -- the log is immutable by design. No mutation endpoints.
- **Full-text search index** -- `ILIKE` is adequate for the expected data volume in Stage 1 (hundreds to low thousands of entries per user). A `pg_trgm` GIN index is noted as a future optimization (see Edge Cases).
- **Activity entries from workflow step execution** -- the schema supports it (the `workflow_run_id` FK exists), but the workflow engine does not yet emit activity entries. Downstream specs wire this.
- **Export / download of the activity log** -- deferred.
- **Activity log in the SPEC-046 vault shell** -- SPEC-046 AC-02 lists "activity" as an icon in the collapsed sidebar. The icon's click target will open the activity panel (same as the topbar badge). The wiring is trivial and lands in whichever spec ships second. If SPEC-046 ships first, the icon is a no-op placeholder. If this spec ships first, the topbar indicator works without the sidebar icon.

---

## Technical Approach

### 1. Extending ActivityLogService

The existing service has `append` and `list_recent`. This spec adds three methods:

```python
class ActivityLogService:
    # ... existing append and list_recent ...

    async def list_paginated(
        self,
        user_id: str,
        *,
        limit: int = 50,
        before: str | None = None,
        workflow_run_id: str | None = None,
        status: list[str] | None = None,
        q: str | None = None,
    ) -> tuple[list[dict], bool]:
        """Return (entries, has_more).

        Cursor-based pagination: ``before`` is an ISO timestamp; entries with
        ``created_at < before`` are returned. Filters compose via AND.
        """
        query = (
            self._user.table("activity_log")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit + 1)  # fetch one extra to determine has_more
        )
        if before:
            query = query.lt("created_at", before)
        if workflow_run_id:
            query = query.eq("workflow_run_id", workflow_run_id)
        if status:
            query = query.in_("status", status)
        if q:
            # OR across action and actor; Supabase PostgREST supports or()
            query = query.or_(
                f"action.ilike.%{q}%,actor.ilike.%{q}%"
            )

        resp = await query.execute()
        rows = list(getattr(resp, "data", None) or [])
        has_more = len(rows) > limit
        return rows[:limit], has_more

    async def count(self, user_id: str) -> int:
        """Total entries for the user."""
        resp = await (
            self._user.table("activity_log")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        c = getattr(resp, "count", None)
        return int(c) if c is not None else len(getattr(resp, "data", None) or [])

    async def count_since(self, user_id: str, since: str | None) -> int:
        """Entries created after ``since`` (ISO timestamp).

        If ``since`` is None (user has never viewed), returns the total count.
        """
        query = (
            self._user.table("activity_log")
            .select("id", count="exact")
            .eq("user_id", user_id)
        )
        if since:
            query = query.gt("created_at", since)
        resp = await query.execute()
        c = getattr(resp, "count", None)
        return int(c) if c is not None else len(getattr(resp, "data", None) or [])
```

### 2. Activity router

```python
# chatServer/routers/activity_router.py

router = APIRouter(prefix="/api/activity", tags=["activity"])

@router.get("")
async def list_activity(
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
    limit: int = Query(default=50, ge=1, le=100),
    before: str | None = Query(default=None),
    workflow_run_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
):
    """Paginated, filterable activity log."""
    service = ActivityLogService(system_client=None, user_client=db)
    status_list = [s.strip() for s in status.split(",")] if status else None
    items, has_more = await service.list_paginated(
        user_id, limit=limit, before=before,
        workflow_run_id=workflow_run_id, status=status_list, q=q,
    )
    total = await service.count(user_id)
    return {"items": items, "total": total, "has_more": has_more}

@router.get("/count")
async def activity_count(
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    """Total entries + entries since last viewed."""
    service = ActivityLogService(system_client=None, user_client=db)
    total = await service.count(user_id)
    # Read last_activity_viewed_at from user_preferences
    prefs_resp = await db.table("user_preferences").select(
        "last_activity_viewed_at"
    ).eq("user_id", user_id).limit(1).execute()
    prefs = (getattr(prefs_resp, "data", None) or [{}])[0] if getattr(prefs_resp, "data", None) else {}
    since = prefs.get("last_activity_viewed_at")
    since_count = await service.count_since(user_id, since)
    return {"total": total, "since_last_viewed": since_count}

@router.post("/mark-viewed")
async def mark_viewed(
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    """Update last_activity_viewed_at to now."""
    now = datetime.now(timezone.utc).isoformat()
    await db.table("user_preferences").upsert(
        {"user_id": user_id, "last_activity_viewed_at": now},
        on_conflict="user_id",
    ).execute()
    return {"marked_at": now}
```

Note: the `activity_count` endpoint reads `user_preferences` in the router's dependency builder. Per A1, this is borderline -- reading a single preference field to compute the count is acceptable in a thin router, but if more logic accrues, extract to a service. The `list_activity` and `mark_viewed` endpoints are clean delegations.

### 3. Migration: user_preferences column

```sql
-- 20260422000001_user_prefs_last_activity_viewed.sql
ALTER TABLE user_preferences
    ADD COLUMN IF NOT EXISTS last_activity_viewed_at TIMESTAMPTZ;

COMMENT ON COLUMN user_preferences.last_activity_viewed_at IS
    'UTC timestamp of when the user last opened the activity log panel. '
    'NULL = never viewed. Used by GET /api/activity/count to compute '
    'since_last_viewed.';
```

No RLS change needed -- `user_preferences` already has row-level security scoped to the user.

### 4. TypeScript types

```ts
// webApp/src/api/types/activity.ts

export interface ActivityEntry {
  id: string;
  user_id: string;
  actor: string;
  action: string;
  subject_path: string | null;
  workflow_run_id: string | null;
  status: 'done' | 'failed' | 'awaiting_approval';
  reasoning: string | null;
  created_at: string;
}

export interface ActivityListResponse {
  items: ActivityEntry[];
  total: number;
  has_more: boolean;
}

export interface ActivityCountResponse {
  total: number;
  since_last_viewed: number;
}

export interface ActivityFilters {
  q?: string;
  status?: string;
  workflow_run_id?: string;
}
```

### 5. React Query hooks

```ts
// webApp/src/api/hooks/useActivityHooks.ts

const ACTIVITY_KEY = ['activity'] as const;
const ACTIVITY_COUNT_KEY = ['activity', 'count'] as const;

export function useActivityLog(filters: ActivityFilters = {}) {
  // Returns useInfiniteQuery for cursor-based pagination.
  // getNextPageParam extracts the created_at of the last item as `before`.
  // staleTime: 30_000 (match polling interval).
}

export function useActivityCount() {
  return useQuery<ActivityCountResponse>({
    queryKey: ACTIVITY_COUNT_KEY,
    queryFn: fetchActivityCount,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
}

export function useMarkActivityViewed() {
  // Mutation that calls POST /api/activity/mark-viewed.
  // onSuccess: optimistically set since_last_viewed to 0 in the
  // ACTIVITY_COUNT_KEY cache, then invalidate.
}
```

### 6. AmbientIndicator (topbar)

The `AmbientIndicator` composes two badges side by side:

- **Approvals badge:** the existing `ApprovalsBadge` component, unchanged in behavior. Bell icon + pending count.
- **Activity badge:** new. Uses an activity/pulse icon (Radix `ActivityLogIcon` or `LightningBoltIcon`). Shows the `since_last_viewed` count. Clicking opens the activity panel.

Both badges share the same visual pattern: icon + optional count badge, reduced opacity at zero.

```tsx
// webApp/src/components/activity/AmbientIndicator.tsx
export const AmbientIndicator: React.FC = () => {
  const { data: activityCount = { total: 0, since_last_viewed: 0 } } =
    useActivityCount();
  const jumpToApprovals = /* existing navigation logic */;
  const openActivityPanel = /* toggle activity panel state */;

  return (
    <div className="flex items-center gap-1">
      <ApprovalsBadge onJump={jumpToApprovals} />
      <ActivityBadge
        count={activityCount.since_last_viewed}
        onClick={openActivityPanel}
      />
    </div>
  );
};
```

Panel open/close state is managed in a Zustand store (`useActivityStore`) with a single boolean `isOpen`. This follows A4 -- panel visibility is client-only state, not server state.

### 7. ActivityPanel layout

```
+--------------------------------------------------+
| Activity Log                          [X] Close  |
|--------------------------------------------------|
| [Search activity log...        ]                 |
| Status: [All v]  Workflow: [All v]               |
|--------------------------------------------------|
| 4 min ago  today-composer                 [done]  |
| Regenerated today.md from morning signals        |
| today.md                                         |
| Run: a1b2c3                                      |
|                                        [> Why?]  |
|--------------------------------------------------|
| 12 min ago  approval-service           [done]    |
| Approved email_draft: Weekly update to team...   |
|--------------------------------------------------|
| ...                                              |
| [Loading more...]                                |
+--------------------------------------------------+
```

Entries are rendered as `<article>` elements inside an `<ol>` (ordered by time). The list uses `overflow-y: auto` with scroll event detection for infinite scroll (intersection observer on a sentinel element at the bottom).

### 8. Dependencies

Existing: Supabase auth + RLS, `get_user_scoped_client`/`create_system_client`, React Query (`useInfiniteQuery`), Radix icons, Zustand (for panel state).

No new libraries.

---

## Testing Requirements

### Unit Tests (required)

- `test_activity_log_service_extended.py`:
  - `list_paginated` returns correct entries in descending order.
  - `list_paginated` with `before` cursor returns only older entries.
  - `list_paginated` with `workflow_run_id` filter returns only matching entries.
  - `list_paginated` with `status` filter (single and comma-separated) returns only matching entries.
  - `list_paginated` with `q` search returns entries matching action or actor.
  - `list_paginated` with combined filters (AND semantics).
  - `has_more` is `true` when more entries exist, `false` at the end.
  - `count` returns the total entry count.
  - `count_since` with a timestamp returns only newer entries.
  - `count_since` with `None` returns the total count.
  - Existing `append` and `list_recent` tests remain passing (no regression).

### Integration Tests (required)

- `test_activity_api.py`:
  - `GET /api/activity` requires auth (401 without JWT).
  - `GET /api/activity` returns entries for the authenticated user only (cross-user isolation).
  - `GET /api/activity?limit=2` returns at most 2 entries with correct `has_more`.
  - `GET /api/activity?before=<ts>` returns only entries older than the cursor.
  - `GET /api/activity?workflow_run_id=<uuid>` returns only matching entries.
  - `GET /api/activity?status=done,failed` returns only matching entries.
  - `GET /api/activity?q=regenerate` returns entries matching the search term.
  - `GET /api/activity/count` returns correct `total` and `since_last_viewed`.
  - `POST /api/activity/mark-viewed` updates the timestamp; subsequent `GET /api/activity/count` returns `since_last_viewed: 0`.
  - User B cannot read User A's activity via any endpoint.

### UI Acceptance Tests (Playwright -- written BEFORE implementation)

Script: `tests/uat/playwright/test_spec_050_activity_log.py`. One function per user-visible AC. Selectors target ARIA role/label.

| AC | Flow / Service Test | UI Test (Playwright) |
|----|---------------------|---------------------|
| AC-01 | `test_ac_01_paginated_list` | -- |
| AC-02 | `test_ac_02_cursor_pagination` | -- |
| AC-03 | `test_ac_03_filter_by_workflow` | -- |
| AC-04 | `test_ac_04_filter_by_status` | -- |
| AC-05 | `test_ac_05_text_search` | -- |
| AC-06 | `test_ac_06_count_endpoint` | -- |
| AC-07 | `test_ac_07_mark_viewed` | -- |
| AC-08 | `test_ac_08_cross_user_forbidden` | -- |
| AC-09 | -- | `test_ac_09_ambient_indicator_renders` |
| AC-10 | -- | `test_ac_10_activity_count_updates` |
| AC-11 | -- | `test_ac_11_badge_click_targets` |
| AC-12 | -- | `test_ac_12_panel_opens_and_closes` |
| AC-13 | -- | `test_ac_13_search_and_filters` |
| AC-14 | -- | `test_ac_14_entry_layout` |
| AC-15 | -- | `test_ac_15_infinite_scroll` |
| AC-16 | -- | `test_ac_16_empty_states` |
| AC-17 | -- | `test_ac_17_search_debounce` |
| AC-18 | -- | `test_ac_18_agent_section_link` |
| AC-19 | `test_ac_19_cross_user_isolation` | -- |

### Manual Verification (UAT)

1. Sign in as dev user. Seed several activity_log rows via SQL (varying actor, status, workflow_run_id, reasoning). Verify `GET /api/activity` returns them in descending order.
2. Open the app. Verify the topbar shows both an approvals badge and an activity badge. The activity badge shows the count of unseen entries.
3. Click the activity badge. Verify the panel slides in from the right, displays entries, and the activity count in the topbar drops to 0.
4. Type in the search box. Verify debounced search filters entries (entries not matching disappear, matching entries remain).
5. Use the status filter dropdown. Verify only entries with the selected status appear.
6. Scroll to the bottom of the entry list. Verify more entries load (if available) with a loading indicator.
7. Click a subject_path link in an entry. Verify navigation to `/vault/<path>`.
8. Click the "Why?" toggle on an entry with reasoning. Verify the reasoning text expands.
9. Close and reopen the panel. Verify the "new" count stays at 0 (mark-viewed persisted).
10. In the Today Agent section, click "View activity log". Verify the panel opens.
11. Sign in as a second user. Verify no cross-user leakage -- the activity log is empty (or shows only that user's entries).

---

## Edge Cases

- **No activity entries exist (new user):** `GET /api/activity` returns `{ items: [], total: 0, has_more: false }`. `GET /api/activity/count` returns `{ total: 0, since_last_viewed: 0 }`. Panel shows the "No agent activity yet" empty state (AC-16).
- **User has never opened the activity log (`last_activity_viewed_at` is NULL):** `count_since(user_id, None)` returns the total count. Every entry is "unseen." The topbar badge shows the full count.
- **Very large log (10,000+ entries):** cursor-based pagination ensures constant-time page fetches (the `idx_activity_log_user_created` index covers the query). UI uses `useInfiniteQuery` and renders only visible entries. No full-count query on every page fetch -- `total` is fetched once on panel open and not updated per page.
- **Search on large logs:** `ILIKE` without a trigram index scans all rows for the user. Acceptable at Stage 1 volumes. If search becomes slow (>500ms for a single user's entries), add a `pg_trgm` GIN index on `(action, actor)` in a follow-up migration. The API contract does not change.
- **Concurrent activity writes during pagination:** cursor-based pagination is stable -- new entries appended after the page was fetched won't shift the cursor. The user sees a "new entries" indicator (the topbar badge increments) and can scroll to the top or close/reopen the panel.
- **`workflow_run_id` references a deleted run:** the FK is `ON DELETE SET NULL`. Entries whose `workflow_run_id` was nullified by a cascade render without the "Run: ..." chip. No crash, no error.
- **Search term contains SQL-special characters (`%`, `_`):** the Supabase PostgREST client handles escaping for `ilike` filters. Validate in integration tests that `%` in the search term does not produce unexpected matches.
- **Panel open during network loss:** React Query's error/retry behavior surfaces a toast. The panel keeps showing cached entries. New entries don't load until connectivity returns.
- **Multiple tabs:** each tab polls independently. `mark-viewed` in one tab writes the timestamp; the other tab's next poll picks up the updated count. Acceptable eventual consistency.
- **Filter combination returns no results:** panel shows "No matching entries. Try adjusting your filters." (AC-16). The "total" in the response still reflects the unfiltered count so the user knows entries exist.
- **`user_preferences` row doesn't exist yet for a new user:** `mark_viewed` uses `upsert` with `on_conflict="user_id"`, creating the row if missing. `activity_count` reads from `user_preferences` and defaults to `None` when no row exists, which `count_since` handles as "return total."

---

## Functional Units (for PR Breakdown)

### FU-1: Migration + backend service extension (database-dev / backend-dev)
**Branch:** `feat/SPEC-050-activity-api`
**ACs:** AC-01 through AC-08, AC-19
- Migration: `last_activity_viewed_at` column on `user_preferences`
- `ActivityLogService` extensions: `list_paginated`, `count`, `count_since`
- `activity_router.py`: three endpoints
- Register router in `chatServer/main.py`
- Unit tests: `test_activity_log_service_extended.py`
- Integration tests: `test_activity_api.py`

### FU-2: Frontend activity panel + ambient indicator (frontend-dev)
**Branch:** `feat/SPEC-050-activity-ui`
**Depends on:** FU-1; Playwright scripts land first
**ACs:** AC-09 through AC-18
- TypeScript types: `activity.ts`
- React Query hooks: `useActivityHooks.ts`
- Zustand store: `useActivityStore.ts` (panel open/close)
- Components: `AmbientIndicator`, `ActivityPanel`, `ActivityEntry`, `ActivityFilters`
- TopBar modification: swap `ApprovalsBadge` for `AmbientIndicator`
- AgentSection modification: add "View activity log" link
- Playwright tests: `test_spec_050_activity_log.py`

**Merge order:** FU-1 then FU-2. Linear, no parallelism.

---

## Resolved Questions (2026-04-21, Tim approved all recommendations)

### OQ-A. Panel vs. route — **RESOLVED: panel per D2**

Slide-in panel, not a dedicated route. Sidebar icon opens the panel. Revisit if UAT shows the panel feels cramped.

### OQ-B. Polling interval — **RESOLVED: 30s**

Activity count polls at 30s (informational, not actionable like approvals at 15s). One-line change if users want faster.

### OQ-C. Badge number semantics — **RESOLVED: since_last_viewed (Option A)**

"Unread" model. "Watching N threads" (Option B) deferred until workflow engine surfaces live run counts.

### Panel width — **RESOLVED: 480px**

### Activity icon — **RESOLVED: Radix ActivityLogIcon**

---

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-19)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (DB schema -> API response shapes -> TypeScript types -> ARIA selectors)
- [x] Technical decisions cite principles (A1, A4, A8, A12, A14; D2, D4)
- [x] Merge order is explicit and acyclic (FU-1 then FU-2)
- [x] Out-of-scope is explicit and enumerates downstream specs
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs (table)
- [x] Existing infrastructure section enumerates every reused primitive
- [x] Access control model spelled out (immutable log, service-role INSERT, user SELECT only)
- [x] Dependency on SPEC-045 schema and service is explicit
- [x] Dependency on SPEC-046 shell is noted with graceful fallback
- [x] Future extensibility for SPEC-052 and workflow-step activity writes is addressed
- [x] New open questions surfaced with recommendations
