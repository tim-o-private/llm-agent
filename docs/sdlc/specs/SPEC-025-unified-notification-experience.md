# SPEC-025: Unified Notification Experience

> **Status:** Draft
> **Author:** Tim + Claude (Product)
> **Created:** 2026-02-24
> **Updated:** 2026-02-24

## Goal

Unify the notification experience across web and Telegram so both channels feel like the same product. Today, web has a disconnected bell dropdown and a separate Pending Actions panel, while Telegram gets inline messages with buttons. The fix: everything renders inline in the chat stream. Kill the bell. Kill the Pending Actions panel. Introduce a three-tier notification type system (`agent_only`, `silent`, `notify`) that gives clear delivery semantics.

## Background

The notification system grew organically across three specs (SPEC-001, SPEC-002, SPEC-006) and two follow-ups (SPEC-021, SPEC-024). Each added a piece without a unified model:

- **SPEC-001** added the `notifications` table + bell dropdown
- **SPEC-002** added Telegram delivery with inline keyboards
- **SPEC-006** added heartbeat/digest notifications
- **SPEC-024** added feedback buttons (thumbs up/down)

Result: Telegram users get inline, immediate, interactive notifications. Web users get a passive bell dropdown they forget to check and a separate Pending Actions panel for approvals. Same product, different experiences.

Additionally, the approval flow is broken end-to-end. When a tool requires approval, the agent queues it in `pending_actions`, tells the user "your approval is needed," and then... nothing. The user has to discover the Pending Actions panel, approve, and the result goes into a void. The conversation doesn't continue. Nobody tells the agent it was approved.

See `docs/product/PRD-001-make-it-feel-right.md` Workstream 3 and the "Inline chat notifications" backlog item for product context.

## Design Decisions

### Three-tier notification types

| Type | Stored in DB | Chat stream | Telegram | Purpose |
|------|-------------|-------------|----------|---------|
| `agent_only` | No | No | No | Internal agent signals (heartbeat findings). Agent sees via memory/context. |
| `silent` | Yes | Yes | No | Background updates the user can see without being interrupted (processing status, FYI items). |
| `notify` | Yes | Yes | Yes | Things that need attention (action items, approval requests, reminders, digests). |

### Kill the bell dropdown

Notifications render inline in the chat stream, interleaved with messages by timestamp. The bell icon and its dropdown are removed entirely. If the user wants history, they scroll up.

### Kill the Pending Actions panel

Approval requests are `notify` notifications with `requires_approval = true`. They render inline in the chat stream with approve/reject buttons — the same pattern Telegram already uses. The separate `PendingActionsPanel` component and its polling are removed.

### Approvals are soft-blocking

When the agent needs approval, it creates a `notify` notification with inline buttons and continues the conversation. If the user ignores the approval and keeps chatting, the agent nudges conversationally: "Hey, scroll up and approve that request before I can do this." No blocking state machine. The `pending_actions` table is kept for execution tracking and audit, but it's no longer the primary approval queue.

### Client-side timeline merge (MVP)

Frontend merges messages + notifications into a single timeline sorted by `created_at`. Three separate data sources (chat messages, notifications, actions) composed client-side. Unified backend API endpoint is a future optimization. Notification polling reduced from 15s to 5s to match chat responsiveness.

## Acceptance Criteria

### Backend: Notification Types

- [ ] **AC-01:** `notifications` table has a new `type` column: `TEXT NOT NULL DEFAULT 'notify' CHECK (type IN ('agent_only', 'silent', 'notify'))`. Migration adds column with default for backward compatibility. [A8]
- [ ] **AC-02:** `notifications` table has a new `requires_approval` column: `BOOLEAN NOT NULL DEFAULT false`. [A8]
- [ ] **AC-03:** `notifications` table has a new nullable `pending_action_id` column: `UUID REFERENCES pending_actions(id)`. Links a notification to its execution record when approval is involved. [A9]
- [ ] **AC-04:** `NotificationService.notify_user()` accepts a `type` parameter (`agent_only`, `silent`, `notify`). Routing: `agent_only` = no DB storage, return immediately. `silent` = store in DB only. `notify` = store in DB + push to Telegram. [A1, A7]
- [ ] **AC-05:** `NotificationService.notify_user()` accepts `requires_approval` and `pending_action_id` parameters. When `requires_approval=True`, the notification metadata includes `tool_name`, `tool_args`, and `action_id` for frontend rendering. [A1]

### Backend: Approval Flow Unification

- [ ] **AC-06:** `tool_wrapper.py` creates a notification (type=`notify`, `requires_approval=True`) instead of only inserting into `pending_actions`. It still inserts into `pending_actions` (for execution tracking), then creates the notification with `pending_action_id` linking to it. [A1, A12]
- [ ] **AC-07:** The tool wrapper return message changes from "STOP: ... Do NOT retry" to a softer message: "I've requested approval for '{tool_name}'. You'll see it in the chat — approve or reject when you're ready." The agent continues conversationally instead of halting. [A14]
- [ ] **AC-08:** Existing `POST /api/actions/{action_id}/approve` and `/reject` endpoints continue to work unchanged. The frontend calls these from inline buttons. [A1]
- [ ] **AC-09:** When an action is approved and executed via the existing endpoint, a follow-up `silent` notification is created: "Approved: {tool_name} — {brief result}". This closes the loop in the chat stream. [A7]

### Backend: Heartbeat Reclassification

- [ ] **AC-10:** Background task heartbeat findings that were previously stored as `category='heartbeat'` notifications are now type `agent_only` — they are NOT stored in the notifications table. The agent receives them via memory context only. [A14]

### Frontend: Inline Chat Notifications

- [ ] **AC-11:** The chat store (`useChatStore`) merges notifications into the message timeline. Messages and notifications are interleaved by `created_at` timestamp. Notification items have `sender: 'notification'` to distinguish from `user`/`ai`/`tool` messages. [A4]
- [ ] **AC-12:** A new `NotificationInlineMessage` component renders notifications in the chat stream. Shows: category-colored left border, title, body, timestamp. For notifications with existing feedback, shows selected state. For notifications without feedback, shows thumbs up/down buttons (reuse SPEC-024 logic). [A13]
- [ ] **AC-13:** A new `ApprovalInlineMessage` component renders approval notifications in the chat stream. Shows: tool name, truncated tool args (expandable), approve/reject buttons. On approve: calls `POST /api/actions/{action_id}/approve`, disables buttons, shows "Approved" state. On reject: same pattern. [A12, A13]
- [ ] **AC-14:** Notifications in the chat stream are auto-marked as read on render (via intersection observer or mount effect). No explicit "mark read" action needed. [A14]
- [ ] **AC-15:** Notification polling interval reduced from 15s to 5s to match chat message responsiveness. [A14]

### Frontend: Remove Old Surfaces

- [ ] **AC-16:** The `NotificationBadge` component (bell icon dropdown) is removed from the navigation header. [A14]
- [ ] **AC-17:** The `PendingActionsPanel` component is removed. Approval requests render inline via AC-13. [A14]
- [ ] **AC-18:** The `usePendingActions` and `usePendingCount` polling hooks are removed. Action data is fetched only when rendering an inline approval notification (on-demand via the existing approve/reject endpoints). [A4]

### Telegram: Alignment

- [ ] **AC-19:** Telegram notification delivery respects the `type` field. `agent_only` and `silent` notifications are NOT sent to Telegram. Only `notify` type triggers Telegram delivery. (Current behavior is approximately correct but must be explicit.) [A7]
- [ ] **AC-20:** Telegram approval requests include the same information as web inline approvals: tool name, truncated args, approve/reject buttons. The existing callback handler (`nfb_` prefix for feedback, `approve:`/`reject:` for actions) continues to work. [A7]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/2026MMDD000001_notification_types.sql` | Add `type`, `requires_approval`, `pending_action_id` columns |
| `webApp/src/components/ui/chat/NotificationInlineMessage.tsx` | Inline notification component for chat stream |
| `webApp/src/components/ui/chat/ApprovalInlineMessage.tsx` | Inline approval component for chat stream |
| `tests/chatServer/services/test_notification_types.py` | Tests for type-based routing |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/notification_service.py` | Add `type` param to `notify_user()`, route based on type |
| `chatServer/security/tool_wrapper.py` | Create notification + pending_action on approval queue, soften return message |
| `chatServer/services/pending_actions.py` | Add `notification_id` tracking (optional, for cross-reference) |
| `chatServer/channels/telegram_bot.py` | Respect `type` field, skip `agent_only`/`silent` |
| `chatServer/services/background_tasks.py` | Heartbeat findings → `agent_only` type |
| `chatServer/routers/actions_router.py` | On approve/reject, create follow-up `silent` notification |
| `webApp/src/stores/useChatStore.ts` | Merge notifications into message timeline |
| `webApp/src/api/hooks/useNotificationHooks.ts` | Reduce polling to 5s, add notification type to interface |
| `webApp/src/components/ui/chat/MessageBubble.tsx` | Route `notification`/`approval` senders to new components |
| `webApp/src/components/ChatPanelV1.tsx` | Remove references to old notification/action panels |

### Files to Remove/Deprecate

| File | Action |
|------|--------|
| `webApp/src/components/features/Notifications/NotificationBadge.tsx` | Remove (bell dropdown) |
| `webApp/src/components/features/Notifications/NotificationBadge.test.tsx` | Remove |
| `webApp/src/components/features/Confirmations/PendingActionsPanel.tsx` | Remove |
| `webApp/src/components/features/Confirmations/ActionCard.tsx` | Remove |
| `webApp/src/components/features/Confirmations/index.ts` | Remove |
| `webApp/src/api/hooks/useActionsHooks.ts` | Remove `usePendingActions`, `usePendingCount` (keep approve/reject mutations) |

### Out of Scope

- WebSocket/SSE for real-time delivery (future — 5s polling is acceptable for MVP)
- Unified backend API endpoint that returns messages + notifications in one call (future optimization)
- Notification preferences UI (separate backlog item)
- Notification history/archive view (if users want it post-bell-removal, future spec)
- Cross-channel sync (approve on TG, web updates in real-time — would need WebSocket)
- Approval timeout/auto-deny (agent nudges conversationally instead)

## Technical Approach

### 1. DB Migration

```sql
-- Add notification type system
ALTER TABLE notifications
ADD COLUMN type TEXT NOT NULL DEFAULT 'notify'
  CHECK (type IN ('agent_only', 'silent', 'notify')),
ADD COLUMN requires_approval BOOLEAN NOT NULL DEFAULT false,
ADD COLUMN pending_action_id UUID REFERENCES pending_actions(id);

-- Index for frontend polling (type-filtered)
CREATE INDEX idx_notifications_user_type
ON notifications (user_id, type, created_at DESC)
WHERE type IN ('silent', 'notify');
```

Default `'notify'` ensures all existing notifications continue to appear. `agent_only` rows won't be stored (filtered at service level), but the CHECK constraint includes it for completeness.

### 2. NotificationService Changes

```python
async def notify_user(
    self,
    user_id: str,
    title: str,
    body: str,
    category: str = "info",
    metadata: dict = None,
    type: str = "notify",           # NEW
    requires_approval: bool = False, # NEW
    pending_action_id: str = None,   # NEW
) -> Optional[str]:
    """
    Route notification based on type:
    - agent_only: no storage, no delivery. Return None.
    - silent: store in DB only. No Telegram.
    - notify: store in DB + push to Telegram.
    """
    if type == "agent_only":
        return None

    notification_id = await self._store_web_notification(
        user_id, title, body, category, metadata,
        type=type,
        requires_approval=requires_approval,
        pending_action_id=pending_action_id,
    )

    if type == "notify":
        await self._send_telegram_notification(user_id, title, body, category, notification_id)

    return notification_id
```

### 3. Tool Wrapper Changes

```python
# In wrapped_arun, when tier != AUTO_APPROVE:

# 1. Still queue in pending_actions (for execution tracking)
action_id = await context.pending_actions_service.queue_action(
    user_id=context.user_id,
    tool_name=tool_name,
    tool_args=kwargs,
    context={"session_id": context.session_id, "agent_name": context.agent_name}
)

# 2. NEW: Create notification with approval request
await context.notification_service.notify_user(
    user_id=context.user_id,
    title=f"Approval needed: {tool_name}",
    body=f"The agent wants to run {tool_name}. Review and approve or reject.",
    category="approval_needed",
    type="notify",
    requires_approval=True,
    pending_action_id=action_id,
    metadata={"tool_name": tool_name, "tool_args": kwargs, "action_id": action_id},
)

# 3. Softer return message — agent continues
return (
    f"I've requested approval for '{tool_name}'. "
    f"You'll see it in the chat — approve or reject when you're ready."
)
```

### 4. Approval Result Notification

In `actions_router.py`, after `approve_action()` succeeds:

```python
await notification_service.notify_user(
    user_id=user.id,
    title=f"Approved: {action.tool_name}",
    body=f"Executed successfully." if result.success else f"Failed: {result.error}",
    category="agent_result",
    type="silent",  # Don't ping TG for the result — user already approved
)
```

### 5. Frontend Timeline Merge

In `useChatStore.ts`:

```typescript
// Extend ChatMessage interface
interface ChatMessage {
  id: string;
  text: string;
  sender: 'user' | 'ai' | 'tool' | 'notification' | 'approval';
  timestamp: Date;
  // Notification fields (when sender = 'notification' | 'approval')
  notification_id?: string;
  notification_category?: string;
  notification_feedback?: 'useful' | 'not_useful' | null;
  // Approval fields (when sender = 'approval')
  action_id?: string;
  action_tool_name?: string;
  action_tool_args?: Record<string, unknown>;
  action_status?: string; // pending, approved, rejected, executed
}
```

Merge logic: fetch notifications via existing hook, map to ChatMessage with `sender: 'notification'` (or `'approval'` if `requires_approval`), concat with chat messages, sort by timestamp.

### 6. Inline Components

**NotificationInlineMessage:** Renders with category-colored left border, title, body, feedback buttons. Reuses SPEC-024 feedback mutation hook. Auto-marks read on mount.

**ApprovalInlineMessage:** Renders with warning border, tool name, expandable args preview, approve/reject buttons. Calls existing `/api/actions/{action_id}/approve` or `/reject`. Disables buttons optimistically. Shows result state after resolution.

### Dependencies

- **SPEC-024** (notification feedback loop) — must be merged first. This spec builds on the feedback buttons and moves them inline.
- **SPEC-021/022** — already merged. Personality and bootstrap are prerequisite for the agent nudge behavior to feel right.

## Testing Requirements

### Unit Tests (required)

**Backend:**
- `notify_user(type='agent_only')` does not store in DB
- `notify_user(type='silent')` stores in DB, does NOT send Telegram
- `notify_user(type='notify')` stores in DB AND sends Telegram
- `notify_user(requires_approval=True)` stores with correct metadata
- Tool wrapper creates both pending_action AND notification on approval queue
- Tool wrapper returns soft message (not "STOP")
- Approve action creates follow-up `silent` notification
- Heartbeat findings use `agent_only` type

**Frontend:**
- `NotificationInlineMessage` renders title, body, feedback buttons
- `ApprovalInlineMessage` renders tool name, approve/reject buttons
- Approve button calls correct endpoint, shows loading then confirmed state
- Chat store merges notifications into timeline in correct order
- Bell dropdown component is removed (no import references)
- PendingActionsPanel is removed (no import references)

### AC-to-Test Mapping

| AC | Test Type | Test Function |
|----|-----------|---------------|
| AC-01 | Manual | Verify migration applied, columns exist |
| AC-02 | Manual | Verify column exists with default |
| AC-03 | Manual | Verify FK constraint |
| AC-04 | Unit | `test_notify_agent_only_not_stored`, `test_notify_silent_no_telegram`, `test_notify_sends_telegram` |
| AC-05 | Unit | `test_notify_approval_metadata` |
| AC-06 | Unit | `test_tool_wrapper_creates_notification_and_action` |
| AC-07 | Unit | `test_tool_wrapper_soft_message` |
| AC-08 | Unit | Existing approve/reject tests (unchanged) |
| AC-09 | Unit | `test_approve_creates_followup_notification` |
| AC-10 | Unit | `test_heartbeat_uses_agent_only_type` |
| AC-11 | Frontend | `test_chat_store_merges_notifications` |
| AC-12 | Frontend | `test_notification_inline_renders_feedback` |
| AC-13 | Frontend | `test_approval_inline_renders_buttons` |
| AC-14 | Frontend | `test_notification_auto_marked_read` |
| AC-15 | Manual | Verify polling interval in network tab |
| AC-16 | Frontend | `test_bell_dropdown_removed` (no imports of NotificationBadge) |
| AC-17 | Frontend | `test_pending_actions_panel_removed` |
| AC-18 | Frontend | `test_pending_hooks_removed` |
| AC-19 | Unit | `test_telegram_skips_silent_and_agent_only` |
| AC-20 | Unit | Existing Telegram approval test (unchanged) |

### Manual Verification (UAT)

- [ ] Agent requests tool approval — notification appears inline in chat with approve/reject buttons
- [ ] Click "Approve" — button disables, shows "Approved", follow-up notification appears in chat
- [ ] Click "Reject" — button disables, shows "Rejected"
- [ ] Agent continues conversation after approval request (no blocking)
- [ ] If user ignores approval and keeps chatting, agent nudges about pending approval
- [ ] Silent notification appears in chat stream without Telegram ping
- [ ] Heartbeat does NOT appear in chat stream (agent_only)
- [ ] Feedback buttons (thumbs up/down) work on inline notifications
- [ ] Bell icon is gone from navigation
- [ ] Pending Actions panel is gone
- [ ] Telegram still receives `notify` type notifications with feedback + approval buttons
- [ ] Timeline ordering is correct when messages and notifications interleave

## Edge Cases

- **Rapid-fire notifications while user is chatting:** Notifications merge into timeline by timestamp. If several arrive at once, they stack chronologically. No special grouping for MVP.
- **Approval expires while inline:** Approve button calls endpoint, gets "Action has expired" error. Display "Expired" state on the inline component. Agent can re-queue if needed.
- **User approves on Telegram, views web:** Web still shows "pending" until next poll (up to 5s). Acceptable for MVP. WebSocket would fix this (future).
- **Notifications from previous sessions:** Frontend only loads notifications for the current session timeframe (or last N). Old notifications scroll off naturally. No infinite scroll for MVP.
- **`agent_only` audit trail:** Since agent_only notifications aren't stored, they leave no DB trace. This is intentional — the agent stores relevant findings in memory. If audit is needed later, we add a separate `agent_events` table (future).
- **Migration backward compatibility:** Default `type='notify'` means all existing notifications keep appearing. No data loss.
- **Multiple approval requests queued:** Each renders as a separate inline notification. User can approve/reject in any order. No dependency between them.

## Functional Units (for PR Breakdown)

1. **FU-1:** Migration + backend notification types (`feat/SPEC-025-types`)
   - DB migration (type, requires_approval, pending_action_id)
   - NotificationService type routing
   - Heartbeat reclassification to agent_only
   - Telegram type filtering
   - Unit tests for type routing

2. **FU-2:** Approval flow unification (`feat/SPEC-025-approvals`)
   - Tool wrapper creates notification + pending_action
   - Softer agent return message
   - Follow-up notification on approve/reject
   - Unit tests for approval flow

3. **FU-3:** Frontend inline notifications (`feat/SPEC-025-inline`)
   - ChatMessage type expansion
   - NotificationInlineMessage component
   - ApprovalInlineMessage component
   - Chat store merge logic
   - Polling interval reduction
   - Auto-mark-read on render
   - Frontend tests

4. **FU-4:** Frontend cleanup (`feat/SPEC-025-cleanup`)
   - Remove NotificationBadge (bell dropdown)
   - Remove PendingActionsPanel + ActionCard
   - Remove usePendingActions/usePendingCount hooks
   - Remove all imports/references
   - Update navigation layout

Merge order: FU-1 → FU-2 → FU-3 → FU-4

FU-1 and FU-2 are backend-only and can be verified independently. FU-3 depends on FU-1 (type field for filtering). FU-4 depends on FU-3 (inline components must exist before removing old surfaces).

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-20)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (DB → service → frontend, DB → Telegram)
- [x] Technical decisions reference principles (A1, A4, A7, A8, A9, A12, A13, A14)
- [x] Merge order is explicit (FU-1 → FU-2 → FU-3 → FU-4)
- [x] Out-of-scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
