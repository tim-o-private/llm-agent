# SPEC-052: Approval Execution (Stage 3 -- Wiring Approved Cards to Real Effects)

> **Status:** Draft
> **Author:** spec-writer (Claude) on behalf of Tim
> **Created:** 2026-04-21
> **Vision:** [`docs/sdlc/visions/clarity-as-vault.md`](../visions/clarity-as-vault.md) -- Stage 3 (Approval lane)
> **Directive:** [`docs/sdlc/visions/clarity-as-vault-functional.md`](../visions/clarity-as-vault-functional.md) -- S6 (Approval lane: "Approved cards disappear from the lane; their execution + result flows into the activity log")
> **Stage:** Clarity-as-Vault Stage 3
> **Depends on:** SPEC-045 (approval_cards schema, ApprovalService, activity_log, VaultService), SPEC-050 (activity log API + panel for surfacing execution results)

---

## Goal

Remove the SPEC-045 "No Outbound Effects" contract. When a user approves an approval card, the system now executes the approved action -- sending an email, creating a calendar event, writing a workflow file, applying a config change, executing a file operation, or sending an outreach message -- and records the execution outcome on the card and in the activity log.

Stage 3 exit criterion from the vision: **"Do I trust its judgment enough to drain the lane daily?"** That requires execution to be reliable, idempotent, transparent about failures, and never silently double-execute.

This is a contract spec -- it defines the executor pattern, the schema extension, the per-card-type execution contract, and error handling semantics. It does not include PR-level breakdowns or Playwright scripts. The executor interface is the key architectural decision: it must be extensible so new card types can be added without modifying dispatch logic. [A11]

---

## Existing Infrastructure (what we reuse)

| Primitive | Location | What we use it for |
|-----------|----------|---------------------|
| `approval_cards` table | `supabase/migrations/20260420000001_create_approval_cards.sql` | Source of truth for card state. This spec adds execution columns. |
| `ApprovalService` | `chatServer/services/approval_service.py` | Approve/reject state machine. This spec extends `.approve()` to dispatch execution after the status flip. |
| `ActivityLogService` | `chatServer/services/activity_log_service.py` | Already wired for approval transitions. Execution results also emit here. |
| `VaultService` | `chatServer/services/vault_service.py` | `_resolve` + `update_body` for vault writes (`workflow_proposal`, `config_change`, `file_operation`). Path safety is enforced. |
| `GmailComposeService` | `chatServer/services/gmail_compose_service.py` | `send_reply()` for `email_draft` execution. Already used by `SendEmailReplyTool`. |
| `CalendarService` | `chatServer/services/calendar_service.py` | Read-only today. This spec requires a `create_event` method (new work). |
| `CalendarToolProvider` | `chatServer/tools/calendar_tools.py` | Multi-account credential resolution for Google Calendar. |
| `GmailToolProvider` / `BaseGmailComposeTool` | `chatServer/tools/gmail_compose_tools.py` | Multi-account credential resolution + scope checking for Gmail. |
| `ToolExecutionService` | `chatServer/services/tool_execution.py` | Existing post-approval tool executor. Reference pattern -- this spec introduces a parallel executor for approval_cards (different data shape, same spirit). |
| `PendingActionsService` | `chatServer/services/pending_actions.py` | Legacy approval queue. Not used by this spec -- approval_cards are the Clarity-as-Vault mechanism. Listed for contrast. |
| `TelegramBotService` | `chatServer/channels/telegram_bot.py` | Outbound messaging for `outreach` cards with `channel: 'telegram'`. |
| `approval_tiers` | `chatServer/security/approval_tiers.py` | Not directly used (approval is already granted by user click), but informs the trust model: execution happens because the user explicitly approved. |
| Scoped DB client | `chatServer/database/scoped_client.py` | `get_user_scoped_client` for reads, `create_system_client` for writes. [A8] |

---

## Schema Extension

The `approval_cards` table gains three columns to track execution state:

```sql
-- Migration: 20260XXX000001_approval_cards_execution_columns.sql

ALTER TABLE approval_cards
    ADD COLUMN IF NOT EXISTS executed_at    TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS execution_result JSONB,
    ADD COLUMN IF NOT EXISTS execution_error  TEXT;

COMMENT ON COLUMN approval_cards.executed_at IS
    'UTC timestamp of when execution was attempted. NULL = not yet executed. '
    'Set exactly once per card -- idempotency guard.';

COMMENT ON COLUMN approval_cards.execution_result IS
    'Structured result from the executor. Shape varies by card_type. '
    'Examples: {"message_id": "...", "thread_id": "..."} for email_draft, '
    '{"event_id": "..."} for calendar_hold, {"path": "..."} for vault writes.';

COMMENT ON COLUMN approval_cards.execution_error IS
    'Human-readable error message if execution failed. NULL = success or not yet attempted. '
    'A card with executed_at set and execution_error set is a recorded failure.';
```

No new RLS policies needed -- existing SELECT/UPDATE policies on `approval_cards` cover these columns.

### State machine extension

The card lifecycle becomes:

```
pending --[approve]--> approved --[execute]--> approved (executed_at set)
                                           \-> approved (executed_at set, execution_error set)
pending --[reject]---> rejected
```

Key invariant: `executed_at` is set exactly once, at the first execution attempt. A card with `executed_at IS NOT NULL` is never re-executed automatically. This is the idempotency boundary.

---

## Executor Pattern

### Interface

Each card type maps to an executor -- a class that knows how to perform the real-world effect for that card shape. Executors are registered in a dispatch table keyed by `card_type`.

```python
# chatServer/services/approval_executors/__init__.py

from dataclasses import dataclass
from typing import Optional, Protocol

@dataclass
class ExecutionResult:
    """Returned by every executor."""
    success: bool
    result: Optional[dict] = None    # Structured output (varies by card_type)
    error: Optional[str] = None      # Human-readable error on failure
    activity_action: Optional[str] = None  # Override for the activity_log action text

class CardExecutor(Protocol):
    """Protocol that every card-type executor implements."""

    async def execute(
        self,
        card: dict,        # The full approval_cards row
        user_id: str,
    ) -> ExecutionResult:
        """Execute the approved action. Must be idempotent if called with the
        same card -- but the dispatcher already guards against double-execution
        via the executed_at check."""
        ...
```

### Dispatch table

```python
# chatServer/services/approval_executors/registry.py

from typing import Dict, Type
from . import CardExecutor

EXECUTOR_REGISTRY: Dict[str, Type[CardExecutor]] = {}

def register_executor(card_type: str):
    """Decorator to register an executor for a card_type."""
    def wrapper(cls: Type[CardExecutor]):
        EXECUTOR_REGISTRY[card_type] = cls
        return cls
    return wrapper

def get_executor(card_type: str) -> Type[CardExecutor]:
    """Look up the executor class for a card_type. Raises KeyError if missing."""
    return EXECUTOR_REGISTRY[card_type]
```

Registration happens at import time via the decorator:

```python
@register_executor("email_draft")
class EmailDraftExecutor:
    async def execute(self, card: dict, user_id: str) -> ExecutionResult: ...
```

### Adding a new card type

To add a new card type in a future spec:
1. Add the value to the `approval_card_type` enum (migration).
2. Write a class implementing `CardExecutor` and decorate it with `@register_executor("new_type")`.
3. Import the module in `approval_executors/__init__.py`.
4. Add the TypeScript payload type and discriminated union case.

No changes to the dispatch layer, no changes to `ApprovalService`. [A11]

### Dispatch flow (in ApprovalService.approve)

```python
# Pseudocode -- actual code lives in ApprovalService._transition after status flip

async def _execute_after_approve(self, card: dict, user_id: str) -> None:
    """Called after status='approved' is committed. Not called for rejections."""
    from .approval_executors.registry import EXECUTOR_REGISTRY

    card_type = card["card_type"]
    executor_cls = EXECUTOR_REGISTRY.get(card_type)

    if executor_cls is None:
        # No executor registered -- log and skip. This covers card types
        # whose executors haven't shipped yet (e.g. workflow_proposal in
        # Stage 5). Not an error.
        await self._record_execution(card, user_id, ExecutionResult(
            success=True,
            activity_action=f"Approved {card_type}: {card['title']} -- no executor registered (Stage 1 no-op)",
        ))
        return

    executor = executor_cls()
    result = await executor.execute(card, user_id)
    await self._record_execution(card, user_id, result)

async def _record_execution(self, card: dict, user_id: str, result: ExecutionResult) -> None:
    """Write executed_at + result/error to the card, and emit activity_log."""
    now = datetime.now(timezone.utc).isoformat()
    patch = {"executed_at": now}
    if result.result:
        patch["execution_result"] = result.result
    if result.error:
        patch["execution_error"] = result.error

    await self._db.table("approval_cards").update(patch).eq("id", card["id"]).execute()

    action_text = result.activity_action or self._describe_execution(card, result)
    await self._log.append(
        user_id=user_id,
        actor="approval-executor",
        action=action_text,
        status="done" if result.success else "failed",
        subject_path=_subject_path(card),
    )
```

### Idempotency contract

1. **Dispatch guard:** `_execute_after_approve` checks `card["executed_at"]` before proceeding. If non-null, the execution is skipped with a log warning. This prevents double-execution if the frontend retries the approve call or a network partition causes a duplicate.

2. **Executor-level idempotency:** Individual executors are encouraged but not required to be idempotent internally. The dispatch guard is the primary defense. Where external APIs provide idempotency keys (e.g. Gmail `threadId` + deduplication), executors should use them.

3. **Database guard:** The `executed_at` column acts as a soft lock. A concurrent approve race (two requests hitting `_execute_after_approve` simultaneously) is mitigated by checking `executed_at IS NULL` in the UPDATE's WHERE clause -- if zero rows are updated, the execution was already started by the other request.

---

## Per-Card-Type Execution Contracts

### 1. `email_draft` -- Send email via Gmail API

**Payload:** `{ to: string[], subject: string, body: string, thread_ref?: string }`

**Execution:**
- Resolve the user's Gmail credentials via `GmailToolProvider` (same path as `SendEmailReplyTool`).
- Check compose scope (`https://www.googleapis.com/auth/gmail.compose`). If missing, fail with a descriptive error.
- If `thread_ref` is present (reply to existing thread), use `GmailComposeService.send_reply(original_message_id=thread_ref, body=body, subject_override=subject)`.
- If `thread_ref` is absent (new email), use a new `GmailComposeService.send_new(to=to, subject=subject, body=body)` method (new work -- the existing service only supports replies).
- **Result:** `{ message_id: str, thread_id: str, to: str, subject: str }`
- **Error cases:** scope missing, credentials expired, Gmail API error, recipient validation failure.

**Existing code leveraged:** `GmailComposeService`, `GmailToolProvider._get_google_credentials`, `BaseGmailComposeTool._check_compose_scope`.

**New work:** `GmailComposeService.send_new()` for non-reply emails.

### 2. `calendar_hold` -- Create calendar event via Google Calendar API

**Payload:** `{ title: string, start_at: string, end_at: string, source_ref?: string }`

**Execution:**
- Resolve the user's Calendar credentials via `CalendarToolProvider`.
- Call a new `CalendarService.create_event(title, start_at, end_at, description?)` method (new work -- the existing service is read-only).
- **Result:** `{ event_id: str, html_link: str }`
- **Error cases:** credentials expired, Calendar API error, invalid time range, calendar write scope missing.

**Existing code leveraged:** `CalendarToolProvider.get_credentials()`, `CalendarService.__init__` (builds the Google API service object).

**New work:** `CalendarService.create_event()`. The `CalendarToolProvider` currently requests `calendar.readonly` scope -- this must be upgraded to `calendar.events` scope for write access. This is a scope change on the OAuth connection, which means existing users will need to re-authorize. Migration path: detect the missing scope at execution time and return a user-friendly error directing them to reconnect in Settings.

### 3. `outreach` -- Send message via specified channel

**Payload:** `{ recipient: string, message: string, channel: 'email' | 'telegram' | 'other' }`

**Execution:**
- **`channel: 'email'`**: Resolve Gmail credentials, send via `GmailComposeService.send_new(to=[recipient], subject="Message from Clarity", body=message)`. Same path as `email_draft` without `thread_ref`.
- **`channel: 'telegram'`**: Use `TelegramBotService.send_message(chat_id=recipient, text=message)`. Requires the recipient's Telegram chat_id to be stored (e.g. in an entity doc or contacts table). If the chat_id cannot be resolved, fail with a descriptive error.
- **`channel: 'other'`**: Not executed in Stage 3. Return a success result with `activity_action` noting "Outreach approved but channel 'other' has no executor -- manual follow-up needed."
- **Result:** `{ channel: str, recipient: str, sent: true }` (or channel-specific details like `message_id`).
- **Error cases:** recipient not resolvable, channel credentials missing, API errors.

**Existing code leveraged:** `GmailComposeService`, `TelegramBotService`.

### 4. `workflow_proposal` -- Write `.flow.md` file to vault

**Payload:** `{ filename: string, body: string, pattern_observed: string }`

**Execution:**
- Validate `filename` ends with `.flow.md` or `.md`. Reject other extensions.
- Target path: `_workflows/{filename}` under the user's vault root.
- Write via `VaultService.update_body(user_id, f"_workflows/{filename}", body)`. VaultService's `_resolve` enforces path containment -- no escape possible. [A12]
- If a file already exists at that path, do **not** overwrite. Return an error: "Workflow file already exists at _workflows/{filename}. Edit or delete the existing file first." This prevents accidental overwrites of user-edited workflows.
- **Result:** `{ path: str, bytes_written: int }`
- **Error cases:** path escape attempt (blocked by VaultService), file already exists, write failure.

**Existing code leveraged:** `VaultService.update_body`, `VaultService._resolve`.

### 5. `config_change` -- Apply diff to agent/skill markdown

**Payload:** `{ file_path: string, diff: string, summary: string }`

**Execution:**
- Read the current file via `VaultService.read_file(user_id, file_path)`.
- Apply the diff. Stage 3 uses a simple strategy: the `diff` field contains the complete new file content (not a unified diff). The executor writes the new content via `VaultService.update_body`. The rationale: unified diff application in Python is fragile against whitespace and context changes; storing the full proposed content in the payload is simpler and the diff preview in the UI already shows a rendered comparison. The `diff` field name is kept for backward compatibility with the SPEC-045 payload type, but its semantics are "proposed new content."
- **Result:** `{ path: str, previous_size: int, new_size: int }`
- **Error cases:** file not found (agent proposed a change to a file that was deleted), path escape (blocked by VaultService), write failure.

**Decision note:** The `diff` field stores complete new content rather than a unified diff patch. This is simpler and more reliable. The UI renders a visual diff by comparing the current file content against `payload.diff`. If a future spec needs true patch application (e.g. for concurrent edits), the executor can be swapped without changing the dispatch layer.

### 6. `file_operation` -- Move, rename, or delete vault files

**Payload:** `{ operation: 'move' | 'rename' | 'delete', source: string, target?: string }`

**Execution:**
- All paths are resolved through `VaultService._resolve` for containment safety.
- **`delete`**: `os.unlink(resolved_source)`. Fire-and-forget `StorageSync.sync_file` to reflect the deletion.
- **`move` / `rename`**: Resolve both `source` and `target` through `_resolve`. Use `shutil.move(resolved_source, resolved_target)`. Create target parent directories if needed. Sync both old and new paths.
- Reject operations on protected paths: `today.md`, anything under `_workflows/` (use the workflow_proposal card type for those), and the vault root itself.
- **Result:** `{ operation: str, source: str, target?: str }`
- **Error cases:** source not found, target already exists (for move/rename), path escape, protected path, write failure.

**Existing code leveraged:** `VaultService._resolve` for path safety, `StorageSync.sync_file` for durability.

**New work:** A `VaultService.move_file` and `VaultService.delete_file` method pair, encapsulating the path resolution + operation + sync pattern.

---

## Error Handling and Retry Semantics

### Execution failure recording

When an executor returns `ExecutionResult(success=False, error="...")`:

1. The `executed_at` column is still set (the attempt happened).
2. The `execution_error` column records the error message.
3. An `activity_log` entry is emitted with `status='failed'` and the error in `reasoning`.
4. The card remains in `status='approved'` -- it does not revert to `pending`.

### User-facing failure UX

The frontend renders execution status on approved cards that remain visible in a "recent" or "completed" section:

- **Executed successfully:** green check + timestamp + "Sent" / "Created" / "Written" label. Links to the result where applicable (e.g. link to the calendar event, link to the vault file).
- **Executed with error:** amber warning icon + error message + "Retry" button. Clicking Retry calls `POST /api/approvals/{id}/retry` (see below).
- **Not yet executed (executor missing):** neutral chip "No executor -- approved as record only."

### Retry endpoint

```
POST /api/approvals/{card_id}/retry
```

- Requires auth. Only the card owner can retry.
- Pre-conditions: `status='approved'`, `executed_at IS NOT NULL`, `execution_error IS NOT NULL`. Returns 409 otherwise.
- Clears `executed_at`, `execution_result`, `execution_error` (resets execution state).
- Re-dispatches `_execute_after_approve`.
- Returns the updated card.

This is the only way to re-execute a failed card. There is no automatic retry -- the user decides when to retry, after potentially fixing the underlying issue (reconnecting Gmail, correcting a path, etc.). [A12, A13]

### External API unavailability

When an external API (Gmail, Calendar) is unreachable or returns a transient error:

- The executor catches the exception and returns `ExecutionResult(success=False, error="Gmail API unavailable: <detail>")`.
- The card records the failure.
- The user sees the error in the activity log and on the card.
- The user can retry when the service recovers.

No automatic retry, no retry queue, no exponential backoff. Rationale: approval execution is user-initiated and low-volume (single-digit actions per day). The user is already looking at the screen. A retry button is simpler, more transparent, and avoids the complexity of background retry infrastructure. [A14]

---

## Integration with ApprovalService

### Changes to `approval_service.py`

The `_transition` method's approve path gains an execution dispatch step:

```python
async def _transition(self, user_id, card_id, new_status, decision_note):
    card = await self.get(user_id, card_id)
    # ... existing status flip logic ...

    # --- New: execution dispatch for approvals ---
    if new_status == "approved":
        await self._execute_after_approve(updated_card, user_id)

    return updated_card
```

The `_describe_action` method drops the "Stage 1 no-op, not sent" suffix. The activity_log entry for the approval itself still reads "Approved email_draft: ..." but the execution emits a second activity_log entry: "Sent email to bob@example.com (Re: Meeting follow-up)" or "Failed to send email to bob@example.com: Gmail scope missing."

### Separation of concerns

- **Approval activity_log entry** (existing): records that the user approved. Actor: `"user"`. Status: `"done"`.
- **Execution activity_log entry** (new): records what happened when the system executed. Actor: `"approval-executor"`. Status: `"done"` or `"failed"`.

Two entries per approved card. This separation means the activity log clearly distinguishes "the user decided" from "the system acted."

---

## Acceptance Criteria

### Schema and executor infrastructure

- [ ] **AC-01:** Migration adds `executed_at` (TIMESTAMPTZ, nullable), `execution_result` (JSONB, nullable), and `execution_error` (TEXT, nullable) to `approval_cards`. Existing rows are unaffected (all three default to NULL).
- [ ] **AC-02:** An executor registry exists at `chatServer/services/approval_executors/`. New executors are registered via `@register_executor("card_type")` decorator. The registry is a dict, not a DB table. [A11]
- [ ] **AC-03:** `ApprovalService.approve()` dispatches execution after the status flip. If no executor is registered for the card type, the card is approved without execution and an activity_log entry notes "no executor registered."
- [ ] **AC-04:** Execution sets `executed_at` on the card exactly once. A second call to `_execute_after_approve` on the same card is a no-op (idempotency guard via `executed_at IS NOT NULL` check). [A12]
- [ ] **AC-05:** On execution success, `execution_result` is populated with a structured JSONB result. On failure, `execution_error` is populated with a human-readable message. Both `executed_at` is always set regardless of outcome.
- [ ] **AC-06:** Every execution (success or failure) emits an `activity_log` entry with `actor='approval-executor'`, appropriate `status`, and the execution detail in `action` text. This is distinct from the existing approval activity_log entry (actor `'user'`). [SPEC-050 integration]
- [ ] **AC-07:** `POST /api/approvals/{card_id}/retry` exists. Pre-conditions: card is `approved`, `executed_at` is set, `execution_error` is set. Clears execution columns and re-dispatches. Returns 409 if pre-conditions fail. Auth required. [A8, A13]

### Per-card-type executors

- [ ] **AC-08:** `email_draft` executor sends email via Gmail API. Uses `GmailComposeService`. Supports both reply (`thread_ref` present) and new email (`thread_ref` absent). Records `message_id` and `thread_id` in `execution_result`. Fails gracefully if compose scope is missing or credentials are expired.
- [ ] **AC-09:** `calendar_hold` executor creates a calendar event via Google Calendar API. Uses an extended `CalendarService.create_event()` method. Records `event_id` and `html_link` in `execution_result`. Fails gracefully if write scope is missing (directs user to reconnect).
- [ ] **AC-10:** `outreach` executor dispatches by channel: `'email'` sends via Gmail, `'telegram'` sends via `TelegramBotService`, `'other'` records approval without execution. Fails gracefully per channel.
- [ ] **AC-11:** `workflow_proposal` executor writes the proposed `.flow.md` file to `_workflows/{filename}` via `VaultService`. Refuses to overwrite an existing file. Records the written path in `execution_result`.
- [ ] **AC-12:** `config_change` executor reads the current file, writes the proposed new content from `payload.diff` via `VaultService.update_body`. Records previous and new file sizes in `execution_result`. Fails if the target file was deleted.
- [ ] **AC-13:** `file_operation` executor performs move/rename/delete via `VaultService`. All paths are resolved through `_resolve` for containment safety. Protected paths (`today.md`, `_workflows/`) are rejected. Records the operation in `execution_result`.

### Frontend execution status

- [ ] **AC-14:** Approved cards in the activity log and any "completed approvals" view show execution status: success (green check + result summary), failure (amber warning + error + retry button), or no-executor (neutral chip).
- [ ] **AC-15:** The retry button on failed cards calls `POST /api/approvals/{card_id}/retry` and updates the card state on success. A loading state is shown during retry.
- [ ] **AC-16:** The `_describe_action` method in `ApprovalService` no longer appends "Stage 1 no-op, not sent" for approved outbound cards.

### Safety and isolation

- [ ] **AC-17:** All vault writes (`workflow_proposal`, `config_change`, `file_operation`) go through `VaultService._resolve`. Path traversal attempts are blocked. Unit tests from SPEC-045 AC-22 remain green. [A12]
- [ ] **AC-18:** All DB operations use scoped clients per A8. Execution does not use raw `get_supabase_client`. Card updates use the user-scoped client. Activity_log inserts use the system client.
- [ ] **AC-19:** Cross-user isolation: User B cannot trigger execution of User A's approval cards. The approve endpoint resolves `user_id` from the JWT and filters by it. Integration tests cover this.

---

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/20260XXX000001_approval_cards_execution_columns.sql` | Add `executed_at`, `execution_result`, `execution_error` columns. |
| `chatServer/services/approval_executors/__init__.py` | `CardExecutor` protocol, `ExecutionResult` dataclass, module imports for registration. |
| `chatServer/services/approval_executors/registry.py` | `EXECUTOR_REGISTRY` dict, `@register_executor` decorator, `get_executor` lookup. |
| `chatServer/services/approval_executors/email_draft.py` | `EmailDraftExecutor` -- send via Gmail API. |
| `chatServer/services/approval_executors/calendar_hold.py` | `CalendarHoldExecutor` -- create event via Calendar API. |
| `chatServer/services/approval_executors/outreach.py` | `OutreachExecutor` -- dispatch by channel. |
| `chatServer/services/approval_executors/workflow_proposal.py` | `WorkflowProposalExecutor` -- write .flow.md to vault. |
| `chatServer/services/approval_executors/config_change.py` | `ConfigChangeExecutor` -- apply proposed content to vault file. |
| `chatServer/services/approval_executors/file_operation.py` | `FileOperationExecutor` -- move/rename/delete via VaultService. |
| `webApp/src/api/types/today.ts` (extend) | Add `executed_at`, `execution_result`, `execution_error` to `ApprovalCardBase`. |
| `webApp/src/components/today/approvals/ExecutionStatus.tsx` | Execution status indicator component (success/failure/retry/no-executor). |
| `tests/unit/services/test_approval_executors.py` | Unit tests for each executor (mocked external APIs). |
| `tests/unit/services/test_approval_execution_dispatch.py` | Dispatch logic, idempotency guard, registry lookup, retry. |
| `tests/integration/test_approval_execution_api.py` | End-to-end: approve card -> execution columns populated, retry flow, cross-user isolation. |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/approval_service.py` | Add `_execute_after_approve`, `_record_execution`. Modify `_transition` to dispatch execution on approve. Remove "Stage 1 no-op" suffix from `_describe_action`. |
| `chatServer/services/calendar_service.py` | Add `create_event(title, start_at, end_at, description?)` method. |
| `chatServer/services/gmail_compose_service.py` | Add `send_new(to, subject, body)` method for non-reply emails. |
| `chatServer/services/vault_service.py` | Add `move_file(user_id, source_rel, target_rel)` and `delete_file(user_id, rel_path)` methods. |
| `chatServer/routers/approvals_router.py` | Add `POST /{card_id}/retry` endpoint. |
| `chatServer/tools/calendar_tools.py` | Update `CalendarToolProvider` to note that `calendar.events` scope is needed for write operations (scope check helper). |
| `webApp/src/api/types/today.ts` | Extend `ApprovalCardBase` with execution fields. |
| `webApp/src/api/hooks/useApprovalsHooks.ts` | Add `useRetryCard` mutation hook. |
| `webApp/src/components/today/approvals/*.tsx` | Add `ExecutionStatus` rendering to each card component for approved cards. |

### Out of Scope

- **Agent-initiated workflow proposals** (Stage 5) -- the `workflow_proposal` executor writes the file, but the agent does not yet autonomously create these cards. That's Transaction #5.
- **Automatic retry / retry queue** -- manual retry only. [A14]
- **Unified diff application** -- `config_change` uses full-content replacement, not patch application.
- **Calendar event updates or deletions** -- Stage 3 creates events only. Update/delete is a future card type.
- **Email attachments** -- `GmailComposeService.send_new` supports plain text only in Stage 3.
- **Outreach to channels beyond email and Telegram** -- `channel: 'other'` is approved-but-not-executed.
- **SSE/WebSocket for execution status updates** -- polling is consistent with SPEC-045 and SPEC-050 approach.
- **Batch approval** ("approve all") -- each card is approved individually.
- **Legacy `pending_actions` integration** -- the old approval system (`pending_actions` table, `PendingActionsService`, `ToolExecutionService`) remains for the existing agent-loop tool approval flow. `approval_cards` are the Clarity-as-Vault mechanism. The two systems coexist until the legacy system is deprecated in a later spec.

---

## Technical Approach

### 1. Executor module structure

```
chatServer/services/approval_executors/
    __init__.py          # CardExecutor protocol, ExecutionResult, imports
    registry.py          # EXECUTOR_REGISTRY, @register_executor, get_executor
    email_draft.py       # EmailDraftExecutor
    calendar_hold.py     # CalendarHoldExecutor
    outreach.py          # OutreachExecutor
    workflow_proposal.py # WorkflowProposalExecutor
    config_change.py     # ConfigChangeExecutor
    file_operation.py    # FileOperationExecutor
```

Each executor module is self-contained. The `__init__.py` imports all six executor modules to trigger registration. This keeps the dispatch table populated without requiring explicit wiring.

### 2. Credential resolution for external APIs

Executors that call external APIs (Gmail, Calendar) need the user's OAuth credentials. These are resolved through the existing provider pattern:

```python
# In EmailDraftExecutor
from chatServer.tools.gmail_compose_tools import BaseGmailComposeTool
from chatServer.tools.gmail_tools import GmailToolProvider

async def _get_gmail_credentials(self, user_id: str, account: str):
    """Resolve Gmail credentials for the user. Account is derived from the
    user's connected Gmail (first connected account if not specified in payload)."""
    provider = await GmailToolProvider.get_provider_for_account(user_id, account, "user")
    return await provider._get_google_credentials()
```

The `account` (email address to send from) is not currently in the `email_draft` payload. Two options:
- **Option A:** Extend the payload with an `account` field. The agent populates it when creating the card.
- **Option B:** Use the user's first connected Gmail account by default.

This spec recommends Option B for Stage 3 (most users have one account) with the payload extension deferred to when multi-account sending is needed. The executor resolves `account` by looking up the user's Gmail connections.

### 3. CalendarService.create_event (new method)

```python
def create_event(
    self,
    title: str,
    start_at: str,
    end_at: str,
    description: str = "",
) -> dict:
    """Create a calendar event. Returns {event_id, html_link}."""
    event_body = {
        "summary": title,
        "start": {"dateTime": start_at},
        "end": {"dateTime": end_at},
    }
    if description:
        event_body["description"] = description

    result = self.service.events().insert(
        calendarId="primary", body=event_body
    ).execute()

    return {
        "event_id": result.get("id"),
        "html_link": result.get("htmlLink"),
    }
```

### 4. GmailComposeService.send_new (new method)

```python
def send_new(
    self,
    to: list[str],
    subject: str,
    body: str,
) -> dict:
    """Send a new email (not a reply). Returns {message_id, thread_id, to, subject}."""
    mime_message = email.mime.text.MIMEText(body, "plain")
    mime_message["To"] = ", ".join(to)
    mime_message["Subject"] = subject

    raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("ascii")

    sent = self.service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()

    return {
        "message_id": sent.get("id"),
        "thread_id": sent.get("threadId"),
        "to": ", ".join(to),
        "subject": subject,
    }
```

### 5. VaultService extensions

```python
async def delete_file(self, user_id: str, rel_path: str) -> None:
    """Delete a file. Raises 404 if not found, 403 on path escape."""
    path = self._resolve(user_id, rel_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    path.unlink()
    if self._sync is not None:
        try:
            asyncio.create_task(self._sync.sync_file(user_id, rel_path))
        except Exception:
            logger.warning("Failed to schedule sync_file for %s", rel_path)

async def move_file(self, user_id: str, source_rel: str, target_rel: str) -> None:
    """Move/rename a file within the user's vault. Both paths go through _resolve."""
    source = self._resolve(user_id, source_rel)
    target = self._resolve(user_id, target_rel)
    if not source.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if target.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Target file already exists",
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))
    if self._sync is not None:
        try:
            asyncio.create_task(self._sync.sync_file(user_id, source_rel))
            asyncio.create_task(self._sync.sync_file(user_id, target_rel))
        except Exception:
            logger.warning("Failed to schedule sync for move %s -> %s", source_rel, target_rel)
```

### 6. Frontend execution status

The `ExecutionStatus` component renders based on the card's execution columns:

- `executed_at === null`: no indicator (card was just approved, execution in flight or pending).
- `executed_at !== null && execution_error === null`: green check + "Sent" / "Created" / "Written" + relative timestamp.
- `executed_at !== null && execution_error !== null`: amber warning + error text + "Retry" button.
- No executor registered (inferred from `executed_at !== null && execution_result` containing the no-executor flag): neutral chip.

The component is generic and rendered inside each card type's component for approved cards.

---

## Dependencies

| Dependency | Status | What this spec needs from it |
|------------|--------|------------------------------|
| SPEC-045 | Shipped (Stage 1) | `approval_cards` table, `ApprovalService`, `ActivityLogService`, `VaultService`, `StorageSync` |
| SPEC-050 | Draft | `GET /api/activity` for the user to see execution results in the activity log panel |
| Gmail OAuth connection | Existing | `GmailToolProvider`, compose scope, `GmailComposeService` |
| Calendar OAuth connection | Existing (read-only) | Needs write scope upgrade (`calendar.events`). Existing users must re-authorize. |
| Telegram bot | Existing | `TelegramBotService.send_message` for outreach channel |

---

## Testing Requirements

### Unit Tests

- `test_approval_executors.py`: One test class per executor. Mock external APIs (Gmail, Calendar, Telegram). Verify:
  - Success path returns correct `ExecutionResult` with structured `result`.
  - Failure path returns `ExecutionResult(success=False, error=...)`.
  - Vault-writing executors go through `VaultService._resolve` (mock VaultService, verify path safety).
  - `workflow_proposal` refuses to overwrite existing files.
  - `file_operation` rejects protected paths.
  - `config_change` reads current file before writing.

- `test_approval_execution_dispatch.py`:
  - Registry lookup works for all six card types.
  - Unknown card type skips execution gracefully.
  - Idempotency guard: second dispatch on same card is a no-op.
  - `_record_execution` writes the correct columns.
  - Retry clears execution columns and re-dispatches.
  - Retry rejects cards that are not in the failed-execution state.

### Integration Tests

- `test_approval_execution_api.py`:
  - Approve an `email_draft` card -> `executed_at` is set, `execution_result` contains `message_id`. (Mock Gmail API at HTTP level.)
  - Approve a `workflow_proposal` card -> file exists in the vault at the expected path.
  - Approve a `file_operation` (delete) -> file is gone from the vault.
  - Retry a failed card -> execution columns reset, new attempt made.
  - Cross-user isolation: User B cannot retry User A's card.
  - Auth: unauthenticated retry returns 401.

### Manual Verification (UAT)

1. Seed an `email_draft` card. Approve it. Verify email arrives in the recipient's inbox. Verify `execution_result` on the card. Verify activity log shows both "Approved" and "Sent" entries.
2. Seed a `calendar_hold` card. Approve it. Verify the event appears in Google Calendar. Verify `execution_result` contains `html_link`.
3. Seed a `workflow_proposal` card. Approve it. Verify `_workflows/{filename}` exists in the vault.
4. Seed a `file_operation` (delete) card. Approve it. Verify the file is gone.
5. Disconnect Gmail, then approve an `email_draft` card. Verify the card shows `execution_error`. Click Retry after reconnecting. Verify the email sends.
6. Approve the same card twice (double-click race). Verify only one email is sent (idempotency guard).
7. Check the activity log panel (SPEC-050). Verify execution results and failures are surfaced clearly.

---

## Edge Cases

- **Double-click on Approve button:** Frontend debounces. Backend idempotency guard (`executed_at IS NOT NULL` check) prevents double execution. Second request returns the already-executed card without re-dispatching.
- **Approve while external API is down:** Execution fails, `execution_error` is recorded. Card stays approved. User retries later. No silent failure.
- **Gmail compose scope missing:** Executor checks scope before sending. Returns a descriptive error: "Gmail compose permission missing. Reconnect Gmail in Settings > Integrations to enable sending." The card is not retried automatically.
- **Calendar write scope missing:** Same pattern. Error directs user to reconnect with write permissions.
- **Vault file deleted between card creation and approval:** `config_change` executor reads the file, gets 404, returns error. `file_operation` (delete) executor gets 404, returns error (file already gone -- arguably success, but recording the discrepancy is safer).
- **workflow_proposal target file already exists:** Executor refuses to overwrite. Error: "File already exists. Delete or rename the existing file first."
- **file_operation on a protected path (today.md, _workflows/):** Executor checks a blocklist before operating. Returns error.
- **outreach with channel='other':** Approved but not executed. Activity log notes manual follow-up needed.
- **Concurrent retry requests:** Same idempotency guard as approve -- the first retry clears `executed_at` and dispatches; the second finds `executed_at` is null (execution in flight) and the dispatch guard handles it. Worst case: two executions of the same action. This is acceptable at Stage 3 volumes.
- **Card payload missing required fields:** Executor validates payload before execution. Returns a structured error listing the missing fields.
- **Very large email body or file content:** Gmail API has its own limits (25MB for attachments, though we send plain text). VaultService has a 10MB write cap. Executors do not add their own size limits beyond what the underlying services enforce.
- **Executor throws an unhandled exception:** The dispatch wrapper catches all exceptions from `executor.execute()`, records them as `execution_error`, and emits a failed activity_log entry. The system never crashes on a bad executor.

---

## Constraints on Earlier Specs

For SPEC-045 and SPEC-050 to avoid boxing out this spec:

1. **SPEC-045 must not make `status` transitions terminal.** The current implementation allows `pending -> approved` and `pending -> rejected` but does not prevent further updates to `approved` rows (for `execution_*` columns). This is already the case -- the UPDATE RLS policy allows the user to update their own cards with no status restriction.

2. **SPEC-045's `_describe_action` suffix ("Stage 1 no-op, not sent") must be removable.** This spec removes it. The method's current structure (checking `card_type in outbound_types`) makes this a one-line change.

3. **SPEC-050's activity log must display entries with `actor='approval-executor'`.** The current schema and UI are actor-agnostic -- any actor string renders correctly. No change needed.

4. **The `approval_card_status` enum must not gain an `'executed'` value.** Execution is orthogonal to approval status. An approved card that executed successfully is still `status='approved'` with `executed_at` set. This avoids complicating the state machine and the frontend's existing `pending/approved/rejected` filter logic.

---

## Resolved Questions (2026-04-21, Tim approved all recommendations)

### 1. Calendar write scope — **RESOLVED: detect at execution time, graceful error**

Detect missing `calendar.events` scope at execution time and show a "reconnect" error. Only affects users who actually approve calendar_hold cards.

### 2. Email account resolution — **RESOLVED: first connected account**

Use the user's first (or only) connected Gmail account. Defer multi-account `account` field to when needed.

### 3. Legacy pending_actions — **RESOLVED: coexist, consolidate later**

`pending_actions` (tool-level) and `approval_cards` (Clarity-as-Vault) coexist. Consolidation deferred to a future spec.

### 4. config_change diff semantics ��� **RESOLVED: keep field name, semantics = complete proposed content**

`payload.diff` contains the complete proposed new file content. UI renders visual diff by comparing current vs. proposed. Field name kept for backward compatibility with SPEC-045 types.

---

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-19)
- [x] Every AC maps to a clear implementation unit
- [x] Every cross-domain boundary has a contract (executor protocol, DB schema, API endpoint, TypeScript types)
- [x] Technical decisions cite principles (A8, A11, A12, A13, A14)
- [x] Out-of-scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
- [x] Existing infrastructure section enumerates every reused primitive
- [x] Executor pattern is extensible -- new card types need one new file, no dispatch changes
- [x] Idempotency guarantees are explicit at two levels (dispatch guard + DB guard)
- [x] Error handling semantics are explicit (no automatic retry, user-driven retry only)
- [x] Dependencies on SPEC-045 and SPEC-050 are explicit
- [x] Constraints on earlier specs are documented to prevent boxing out
- [x] Decisions requiring input are surfaced with recommendations
