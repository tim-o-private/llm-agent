# SPEC-025: Unified Notification Experience

> **Status:** Draft
> **Author:** Tim + Claude (Product)
> **Created:** 2026-02-24
> **Updated:** 2026-02-26

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

### Tool execution after approval (the executor gap)

Today, `PendingActionsService` accepts an optional `tool_executor` callable, but it is **never provided**. Both `actions.py` router and `chat.py` construct `PendingActionsService` without one. When a user clicks "Approve," the action is marked approved in the database but the tool never runs. The log says: _"No tool executor configured, action {id} marked approved but not executed."_

This is not a simple wiring fix. Tool classes are LangChain `BaseTool` subclasses that self-construct their DB clients inside `_arun()`. They need `user_id`, `agent_name`, `supabase_url`, and `supabase_key` at instantiation time, and their `_arun()` is normally called by the agent executor within a chat turn. When execution happens post-approval (outside a chat turn), there is no agent executor, no active LangChain chain, and the tool must not re-trigger the approval wrapper (which would create an infinite approval loop).

**Design: `ToolExecutionService` as standalone executor.** A new service that:
1. Looks up the tool class from `TOOL_REGISTRY` by matching `pending_actions.tool_name` against `tools.name` to get the `tools.type` value, then resolving the class.
2. Instantiates the tool with `user_id`, `agent_name` (from `pending_actions.context`), and Supabase credentials from settings.
3. Calls `_arun(**tool_args)` directly -- bypassing the LangChain agent executor and the approval wrapper entirely.
4. Returns the result to `PendingActionsService`, which stores it in `execution_result` and creates the follow-up notification.

**Why a service, not a lambda:** The executor needs DB access (to look up the tool type), config access (Supabase credentials), and must be testable in isolation. A closure or lambda passed into `PendingActionsService` would hide these dependencies. A proper service follows A1 (fat services) and is mockable in tests.

**Why bypass the wrapper:** The approval wrapper is applied by `wrap_tools_with_approval()` during chat processing. Post-approval execution is a separate path. The tool is instantiated fresh, without the wrapper, so there is no risk of re-triggering approval. This is safe because the approval check already happened -- the `pending_actions` row's status is `approved` by the time execution begins.

**Why not reuse the cached agent executor:** The executor cache is keyed by `(user_id, agent_name)` and carries LangChain state (memory, wrapped tools). Reaching into the cache to find a tool would couple the approval path to the chat path, create race conditions when the executor is mid-turn, and would still have the approval wrapper attached. Clean instantiation is simpler and safer.

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

### Backend: Post-Approval Tool Execution

- [ ] **AC-21:** A new `ToolExecutionService` class in `chatServer/services/tool_execution.py` provides a `execute_tool(user_id, tool_name, tool_args, agent_name)` method. It resolves the tool's Python class via `TOOL_REGISTRY`, instantiates the `BaseTool` subclass with the required context (`user_id`, `agent_name`, `supabase_url`, `supabase_key`), calls `_arun(**tool_args)`, and returns the string result. Tools are instantiated **without** the approval wrapper. [A1, A6]
- [ ] **AC-22:** `ToolExecutionService` resolves tool class by querying `tools` table: `SELECT type FROM tools WHERE name = :tool_name`. The `type` value is the key into `TOOL_REGISTRY`. If the tool name is not found in the DB or the type is not in the registry, execution fails with a clear error. [A3, A6]
- [ ] **AC-23:** `ToolExecutionService` handles tool config from the `tools` table: for tools that require DB config (Gmail tools with `tool_class`, CRUDTool with `table_name`/`method`), the service reads `tools.config` JSONB and passes it to the constructor. This mirrors the existing `load_tools_from_db()` instantiation logic. [A6]
- [ ] **AC-24:** `PendingActionsService` is constructed with a `tool_executor` callable in the `actions.py` router. The `_build_pending_actions_service()` helper creates a `ToolExecutionService` and passes its `execute_tool` method as the `tool_executor` parameter. [A1]
- [ ] **AC-25:** When `approve_action()` succeeds with a tool executor, the `pending_actions` row transitions through `pending` -> `approved` -> `executed` (on success) or `approved` -> `executed` with error (on failure). The `execution_result` JSONB column stores the tool output or error. [A8]
- [ ] **AC-26:** Execution failures do NOT propagate as HTTP 500 to the user. The approve endpoint returns success with `execution_error` in the response body, and the follow-up notification (AC-09) includes the error message. The user sees "Approved: {tool_name} -- Failed: {error}" in the chat stream. [A1]

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
| `chatServer/services/tool_execution.py` | Standalone tool executor for post-approval execution |
| `tests/chatServer/services/test_tool_execution.py` | Tests for tool resolution, instantiation, and execution |
| `tests/chatServer/services/test_notification_types.py` | Tests for type-based routing |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/notification_service.py` | Add `type` param to `notify_user()`, route based on type |
| `chatServer/security/tool_wrapper.py` | Create notification + pending_action on approval queue, soften return message |
| `chatServer/services/pending_actions.py` | Add `notification_id` tracking (optional, for cross-reference) |
| `chatServer/routers/actions.py` | Wire `ToolExecutionService` into `_build_pending_actions_service()` |
| `chatServer/channels/telegram_bot.py` | Respect `type` field, skip `agent_only`/`silent` |
| `chatServer/services/background_tasks.py` | Heartbeat findings → `agent_only` type |
| `chatServer/routers/actions.py` | On approve/reject, create follow-up `silent` notification (already done in current code) |
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

### 7. Post-Approval Tool Execution (`ToolExecutionService`)

The core problem: tools need to be executed outside the LangChain agent loop, after the user approves. The `ToolExecutionService` handles resolution, instantiation, and direct invocation.

```python
# chatServer/services/tool_execution.py
"""
Standalone tool executor for post-approval execution.

Resolves a tool by name, instantiates the BaseTool subclass with user context,
and calls _arun() directly — bypassing the LangChain agent executor and the
approval wrapper.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ToolExecutionService:
    """
    Executes tools by name outside the LangChain agent loop.

    Used by PendingActionsService after user approval. Instantiates tool
    classes from TOOL_REGISTRY with proper user context.
    """

    def __init__(self, db_client):
        self.db = db_client

    async def execute_tool(
        self,
        tool_name: str,
        tool_args: dict,
        user_id: str,
        agent_name: Optional[str] = None,
    ) -> str:
        """
        Execute a tool by name.

        1. Look up tool type from `tools` table by name
        2. Resolve Python class from TOOL_REGISTRY
        3. Instantiate with user context (no approval wrapper)
        4. Call _arun(**tool_args) directly
        """
        from ..config.settings import settings
        from src.core.agent_loader_db import TOOL_REGISTRY

        # Step 1: Resolve tool type from DB
        result = await self.db.table("tools") \
            .select("type, config") \
            .eq("name", tool_name) \
            .single() \
            .execute()

        if not result.data:
            raise ToolExecutionError(f"Tool '{tool_name}' not found in tools table")

        tool_type = result.data["type"]
        tool_config = result.data.get("config") or {}

        # Step 2: Resolve Python class
        tool_class = TOOL_REGISTRY.get(tool_type)
        if tool_class is None:
            raise ToolExecutionError(
                f"Tool type '{tool_type}' for '{tool_name}' not in TOOL_REGISTRY"
            )

        # Step 3: Build constructor kwargs
        constructor_kwargs = {
            "user_id": user_id,
            "agent_name": agent_name,
            "supabase_url": settings.SUPABASE_URL,
            "supabase_key": settings.SUPABASE_SERVICE_ROLE_KEY,
            "name": tool_name,
            "description": f"Post-approval execution of {tool_name}",
        }

        # Merge tool-specific config (same pattern as load_tools_from_db)
        if tool_config:
            constructor_kwargs.update(tool_config)

        # Step 4: Instantiate and execute
        try:
            tool_instance = tool_class(**constructor_kwargs)
        except Exception as e:
            raise ToolExecutionError(
                f"Failed to instantiate tool '{tool_name}' (class {tool_class.__name__}): {e}"
            ) from e

        try:
            result = await tool_instance._arun(**tool_args)
            logger.info(f"Post-approval execution of '{tool_name}' succeeded for user {user_id}")
            return result
        except Exception as e:
            logger.error(f"Post-approval execution of '{tool_name}' failed: {e}")
            raise ToolExecutionError(
                f"Tool '{tool_name}' execution failed: {e}"
            ) from e


class ToolExecutionError(Exception):
    """Raised when post-approval tool execution fails."""
    pass
```

**Wiring in `actions.py` router:**

```python
# In _build_pending_actions_service:
def _build_pending_actions_service(db: UserScopedClient):
    from ..services.audit_service import AuditService
    from ..services.pending_actions import PendingActionsService
    from ..services.tool_execution import ToolExecutionService

    audit_service = AuditService(db)
    tool_exec_service = ToolExecutionService(db)

    async def tool_executor(tool_name: str, tool_args: dict, user_id: str):
        return await tool_exec_service.execute_tool(
            tool_name=tool_name,
            tool_args=tool_args,
            user_id=user_id,
        )

    return PendingActionsService(
        db_client=db,
        tool_executor=tool_executor,
        audit_service=audit_service,
    )
```

The `tool_executor` callable signature matches what `PendingActionsService.approve_action()` already expects (line 168): `await self.tool_executor(tool_name=..., tool_args=..., user_id=...)`. No changes to the `PendingActionsService` interface are needed.

**Why this is safe:**
- The tool is instantiated fresh, without `wrap_tools_with_approval()`. No approval re-trigger.
- The `_arun()` method creates its own `UserScopedClient` internally (standard tool pattern), so RLS is properly enforced for the user's data.
- `ToolExecutionService` uses the same `TOOL_REGISTRY` and instantiation pattern as `load_tools_from_db()`, keeping tool resolution consistent.
- The `pending_actions.context` JSONB already stores `agent_name` — the router passes it through.

**Failure modes:**
- Tool name not in `tools` table: `ToolExecutionError` with clear message. Action stays `approved`, never transitions to `executed`.
- Tool type not in `TOOL_REGISTRY`: Same behavior. Suggests a DB/code mismatch (should not happen if migrations are consistent).
- Tool instantiation fails (bad config): `ToolExecutionError`. Stored in `execution_result.error`.
- Tool `_arun()` raises: Caught by `PendingActionsService.approve_action()` existing `except Exception` block (line 183). Status set to `executed` with error.
- All failures create a follow-up notification (AC-09/AC-26) so the user sees the error in the chat stream.

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
- `ToolExecutionService.execute_tool()` resolves tool class from DB and `TOOL_REGISTRY`
- `ToolExecutionService` instantiates tool with correct user context (no approval wrapper)
- `ToolExecutionService` returns tool output on success
- `ToolExecutionService` raises `ToolExecutionError` for unknown tool name
- `ToolExecutionService` raises `ToolExecutionError` for unregistered tool type
- `ToolExecutionService` raises `ToolExecutionError` on `_arun()` failure (with original error chained)
- `_build_pending_actions_service()` provides `tool_executor` to `PendingActionsService`
- End-to-end: approve action -> tool executes -> `execution_result` stored -> follow-up notification created
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
| AC-21 | Unit | `test_execute_tool_resolves_and_runs`, `test_execute_tool_no_wrapper` |
| AC-22 | Unit | `test_execute_tool_unknown_name`, `test_execute_tool_unregistered_type` |
| AC-23 | Unit | `test_execute_tool_passes_config` |
| AC-24 | Unit | `test_build_service_provides_executor` |
| AC-25 | Unit | `test_approve_action_transitions_to_executed` |
| AC-26 | Unit | `test_approve_action_execution_error_not_500` |
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
- [ ] Click "Approve" — button disables, shows "Approved", **tool actually executes**, follow-up notification appears with execution result
- [ ] Click "Approve" on a tool that fails execution — follow-up notification shows "Failed: {error}" (not HTTP 500)
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
- **Tool removed from registry between queue and approval:** If the tool type is no longer in `TOOL_REGISTRY` (code deployed between queue and approve), `ToolExecutionService` raises `ToolExecutionError`. The user sees "Approved: {tool_name} -- Failed: Tool type not in TOOL_REGISTRY" in the follow-up notification. The agent can re-queue if the tool is restored.
- **Tool config changed between queue and approval:** The tool is instantiated with current DB config at execution time, not the config at queue time. This is correct — if the tool's config was updated (e.g., API key rotation), the execution should use the latest config.
- **Long-running tool execution on approval:** `_arun()` is awaited in the request handler. If the tool takes >30s (e.g., complex Gmail search), the HTTP request may time out. For MVP, this is acceptable — the action transitions to `executed` in the background via the DB update. Future: move execution to a background task / job queue (SPEC-026).
- **Approval of tool that was originally auto-approved:** This should not happen (auto-approved tools execute immediately in the chat turn), but if a `pending_actions` row exists for one (e.g., due to a tier change), the executor handles it normally.

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

5. **FU-5:** Post-approval tool execution (`feat/SPEC-025-tool-executor`)
   - `ToolExecutionService` class (tool resolution, instantiation, direct `_arun()`)
   - `ToolExecutionError` exception class
   - Wire `ToolExecutionService` into `actions.py` router's `_build_pending_actions_service()`
   - Pass `agent_name` from `pending_actions.context` to executor
   - Unit tests: tool resolution, instantiation, execution success/failure, unknown tool, missing registry entry
   - Integration with existing `PendingActionsService.approve_action()` flow (no interface changes)

Merge order: FU-1 → FU-2 → FU-5 → FU-3 → FU-4

FU-1 and FU-2 are backend-only and can be verified independently. FU-5 depends on FU-2 (the approval flow must create `pending_actions` rows with proper context). FU-5 is pure backend and can be verified before frontend work begins. FU-3 depends on FU-1 (type field for filtering) and benefits from FU-5 (approve button actually executes the tool, so the follow-up notification has real content). FU-4 depends on FU-3 (inline components must exist before removing old surfaces).

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-26)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (DB → service → frontend, DB → Telegram, DB → tool executor)
- [x] Technical decisions reference principles (A1, A3, A4, A6, A7, A8, A9, A12, A13, A14)
- [x] Merge order is explicit (FU-1 → FU-2 → FU-5 → FU-3 → FU-4)
- [x] Out-of-scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
- [x] Post-approval execution path avoids approval re-trigger (no wrapper on fresh tool instance)
- [x] Failure modes documented with user-visible behavior
