# SPEC-024: Notification Feedback Loop

> **Status:** Draft
> **Author:** Tim + Claude (Product)
> **Created:** 2026-02-24
> **Updated:** 2026-02-24

## Goal

Give users a zero-friction way to tell the agent whether its proactive notifications are useful. Two buttons — "Useful" / "Not useful" — on every proactive notification. Feedback is stored as memory, teaching the agent what to surface and what to suppress. This is the seed of the personalization flywheel described in the product vision.

## Background

The agent sends notifications via web and Telegram: heartbeat findings, email digests, reminders, proactive nudges. Users can read or dismiss them. There's no way to tell the agent "this was useful" or "stop bothering me with this." Without feedback, the agent's judgment can't improve. With feedback, it calibrates over time.

The design is deliberately primitive. Two buttons, stored as memory. No ML pipeline, no recommendation engine. The agent's own judgment + memory search is the personalization engine.

See `docs/product/PRD-001-make-it-feel-right.md` Workstream 3 for full product context.

## Acceptance Criteria

### Backend: Schema & API

- [ ] **AC-01:** `notifications` table has a new nullable `feedback` column: `TEXT CHECK (feedback IN ('useful', 'not_useful'))` and a `feedback_at` TIMESTAMPTZ column. Migration adds both columns. [A8]
- [ ] **AC-02:** New endpoint `POST /api/notifications/{notification_id}/feedback` accepts `{ "feedback": "useful" | "not_useful" }`, updates the notification row, and triggers memory storage. Requires auth. Returns 200 on success, 404 if notification not found or not owned by user. [A1, A8]
- [ ] **AC-03:** On feedback submission, the service stores a memory entry via `MemoryClient` with: `memory_type="core_identity"`, entity based on notification category, tags including `["feedback", category]`, and text describing what the user found useful or not useful. [A6]
- [ ] **AC-04:** Feedback can only be submitted once per notification. Subsequent calls to the endpoint for the same notification return 409 Conflict. [A14]

### Frontend: Web Notifications

- [ ] **AC-05:** Each notification in the web dropdown that has no existing feedback shows two icon buttons: thumbs up (useful) and thumbs down (not useful). Buttons appear inline, always visible (not hover-only — accessibility). [A13]
- [ ] **AC-06:** Clicking a feedback button fires the API call (AC-02), disables both buttons, and shows a brief confirmation state (e.g., button stays highlighted). No modal, no confirmation dialog. [A4]
- [ ] **AC-07:** Notifications that already have feedback show the selected button in its highlighted state. The other button is hidden or dimmed. [A13]

### Telegram: Inline Feedback

- [ ] **AC-08:** Proactive Telegram notifications (heartbeat findings, agent results) include an inline keyboard with two buttons: "Useful" and "Not useful". Callback data encodes notification ID and feedback value. [A7]
- [ ] **AC-09:** Telegram callback handler routes feedback button presses to the same feedback service used by the web endpoint (AC-02, AC-03). Responds with "Got it, thanks!" edit to the message. [A7]

### Agent Integration

- [ ] **AC-10:** Memory tool `prompt_section()` for web/telegram channels includes guidance: "When deciding what to surface proactively, recall past feedback. Use search_memories with tags ['feedback'] to check if the user has found similar notifications useful or not useful. Weight recent feedback more heavily." [A6]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/2026MMDD000001_notification_feedback.sql` | Add feedback columns to notifications table |
| `tests/chatServer/routers/test_notification_feedback.py` | Router unit tests |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/routers/notification_router.py` | Add feedback endpoint |
| `chatServer/services/notification_service.py` | Add `submit_feedback()` method with memory storage |
| `chatServer/services/telegram_service.py` | Add feedback inline keyboard to proactive notifications, handle callback |
| `chatServer/tools/memory_tools.py` | Update `prompt_section()` to include feedback recall guidance |
| `webApp/src/components/features/Notifications/NotificationBadge.tsx` | Add feedback buttons to notification items |
| `webApp/src/api/hooks/useNotificationHooks.ts` | Add `useSubmitNotificationFeedback` mutation hook |
| `tests/chatServer/services/test_notification_service.py` | Tests for feedback + memory storage |

### Out of Scope

- Implicit feedback (tracking opens vs. dismissals without explicit button click)
- Feedback analytics dashboard
- Weighted feedback scoring (all feedback is equally weighted for now)
- Feedback on chat messages (only on notifications)
- Aggregate feedback reports for the user ("you've found 80% useful")
- Background pruning of stale feedback memories (future spec)

## Technical Approach

### 1. DB Migration

```sql
ALTER TABLE notifications
ADD COLUMN feedback TEXT CHECK (feedback IN ('useful', 'not_useful')),
ADD COLUMN feedback_at TIMESTAMPTZ;

CREATE INDEX idx_notifications_user_feedback
ON notifications (user_id, feedback, created_at DESC)
WHERE feedback IS NOT NULL;
```

Existing RLS policy (`is_record_owner()`) already covers this — users can only update their own notifications.

### 2. Backend Endpoint

Per A1, thin router delegates to service:

```python
# notification_router.py
@router.post("/{notification_id}/feedback")
async def submit_feedback(
    notification_id: UUID,
    body: FeedbackRequest,  # { feedback: "useful" | "not_useful" }
    user=Depends(get_current_user),
    db=Depends(get_user_scoped_client),
):
    result = await notification_service.submit_feedback(
        db, notification_id, body.feedback, user.id
    )
    return result
```

### 3. Memory Storage

When feedback is submitted, the service:

1. Updates notification row (feedback + feedback_at)
2. Reads notification category and title for context
3. Calls `MemoryClient.call_tool("store_memory", {...})`:

```python
text = (
    f"User marked a '{category}' notification as {feedback}. "
    f"Notification was about: {title}. "
    f"{'Continue surfacing similar items.' if feedback == 'useful' else 'Reduce priority for similar items.'}"
)
await memory_client.call_tool("store_memory", {
    "text": text,
    "memory_type": "core_identity",
    "entity": f"notification_preference",
    "scope": "global",
    "tags": ["feedback", category, feedback]
})
```

### 4. Frontend Buttons

Add to the notification item component:

- Two `IconButton` components (thumbs up / thumbs down) using existing icon library
- Mutation hook: `useSubmitNotificationFeedback` wrapping `POST /api/notifications/{id}/feedback`
- Optimistic update: disable buttons immediately on click, show selected state
- Error handling: re-enable buttons if API call fails

### 5. Telegram Integration

Reuse the existing inline keyboard pattern from the approval system:

```python
# When sending proactive notification via Telegram
keyboard = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(
        text="Useful",
        callback_data=f"nfb_{notification_id}_useful"
    ),
    InlineKeyboardButton(
        text="Not useful",
        callback_data=f"nfb_{notification_id}_not_useful"
    )
]])
```

Callback handler parses `nfb_{id}_{feedback}`, calls `notification_service.submit_feedback()`, edits message with "Got it, thanks!"

### 6. Agent Prompt Integration

Update `CreateMemoriesTool.prompt_section()` to include feedback recall guidance. The agent should search for feedback memories before deciding whether to surface a notification type.

### Dependencies

- SPEC-022 (personality rewrite) should land first — the feedback recall guidance in prompt_section builds on the structured memory conventions.
- No hard blockers. Memory client and notification service both exist.

## Testing Requirements

### Unit Tests (required)

- `test_notification_service.py`: `submit_feedback` updates notification row
- `test_notification_service.py`: `submit_feedback` calls memory client with correct entry
- `test_notification_service.py`: `submit_feedback` returns 409 on duplicate feedback
- `test_notification_feedback.py`: Router returns 200 on valid feedback
- `test_notification_feedback.py`: Router returns 404 on non-existent notification
- `test_notification_feedback.py`: Router returns 401 without auth

### Frontend Tests

- `NotificationBadge` renders feedback buttons for notifications without feedback
- `NotificationBadge` shows selected state for notifications with feedback
- Mutation hook calls correct endpoint with correct payload

### AC-to-Test Mapping

| AC | Test Type | Test Function |
|----|-----------|--------------|
| AC-01 | Manual | Verify migration applied, columns exist |
| AC-02 | Unit | `test_feedback_endpoint_success`, `test_feedback_endpoint_not_found` |
| AC-03 | Unit | `test_feedback_stores_memory` |
| AC-04 | Unit | `test_feedback_duplicate_returns_409` |
| AC-05 | Frontend | `test_feedback_buttons_rendered` |
| AC-06 | Frontend | `test_feedback_button_click_fires_mutation` |
| AC-07 | Frontend | `test_feedback_already_submitted_shows_state` |
| AC-08 | Unit | `test_telegram_notification_includes_feedback_keyboard` |
| AC-09 | Unit | `test_telegram_feedback_callback_stores_feedback` |
| AC-10 | Unit | `test_memory_prompt_section_includes_feedback_guidance` |

### Manual Verification (UAT)

- [ ] Receive a notification on web
- [ ] Click "Useful" — verify button highlights, other button dims
- [ ] Check DB: notification has feedback='useful' and feedback_at set
- [ ] Check memory: feedback entry exists with correct tags
- [ ] Receive a notification on Telegram
- [ ] Click "Useful" button — verify message edits to "Got it, thanks!"
- [ ] Verify same DB and memory updates

## Edge Cases

- **Notification without a category:** Use "general" as default for memory entry tags.
- **Memory server unavailable:** Feedback is still stored in notifications table (DB update succeeds). Memory storage logged as warning but doesn't block the response. User gets 200, memory is best-effort.
- **User clicks feedback very quickly after notification arrives:** No race condition — feedback is idempotent (single column update).
- **Notification already read when feedback is given:** No conflict — read status and feedback are independent columns.
- **Telegram bot not linked:** Web feedback buttons still work. Telegram buttons are only added when sending via Telegram.

## Functional Units (for PR Breakdown)

1. **FU-1:** Migration + backend service + tests (`feat/SPEC-024-backend`)
   - DB migration
   - Notification service feedback method
   - Router endpoint
   - Memory integration
   - Unit tests

2. **FU-2:** Frontend buttons + hooks (`feat/SPEC-024-frontend`)
   - Notification item feedback buttons
   - Mutation hook
   - Visual states

3. **FU-3:** Telegram integration + prompt guidance (`feat/SPEC-024-telegram`)
   - Inline keyboard on proactive notifications
   - Callback handler
   - Memory tool prompt_section update

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-10)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (DB → API → Frontend, DB → Telegram)
- [x] Technical decisions reference principles (A1, A4, A6, A7, A8, A13, A14)
- [x] Merge order is explicit (FU-1 → FU-2 + FU-3 in parallel)
- [x] Out-of-scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
