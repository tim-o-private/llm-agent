# Interaction Patterns

> **Owner:** UX Designer
> **Status:** Baseline v1
> **Spec:** SPEC-030
> **Last updated:** 2026-02-26

This document is the contract for how Clarity's UI behaves. Frontend-dev implements against these rules. The UX reviewer checks PRs against them. When in doubt, simpler is better.

**Design philosophy reminder:** Clarity targets users with ADHD. Every pattern here optimizes for: calm & minimal, clear hierarchy, low friction, encouraging tone, predictable behavior.

---

## 1. Error States

Errors tell the user something went wrong and what to do next. Never just "Error occurred." Always: what happened + what to try.

### When to Use What

| Scenario | Pattern | Example |
|----------|---------|---------|
| Field-level validation failure | **Inline error** below the field | "Title is required. Add a title to save." |
| Form submission failure (server) | **Inline error** at top of form + toast | "Couldn't save your task. Check your connection and try again." |
| Page/section data failed to load | **Inline error** replacing content area | "Couldn't load your tasks. Try refreshing." with a "Refresh" button |
| Background action failure (toast notification) | **Toast (destructive)** | "Couldn't disconnect Gmail. Try again." |
| Unrecoverable crash | **Error boundary** | "Something went wrong. Refresh the page to continue." |

### Rules

1. **Never show raw error messages to users.** No stack traces, no HTTP status codes, no "TypeError: Cannot read property of undefined." Log those; show human copy.
2. **Every error message has two parts:** what went wrong (past tense) + what to do (imperative). Pattern: `"Couldn't [action]. [Recovery step]."`
3. **Inline errors are the default.** Use toasts only when the error relates to a background action the user didn't just trigger (or as a supplement to inline).
4. **Error boundary is the last resort.** Components should catch their own errors. The root ErrorBoundary is a safety net, not a design pattern.
5. **Errors are not scary.** Use `text-text-destructive` for the text, not red backgrounds. Keep the tone calm. "Couldn't" > "Failed to" > "Error:".

### Copy Templates

| Context | Template |
|---------|----------|
| Data fetch | "Couldn't load [thing]. Try refreshing." |
| Save/create | "Couldn't save [thing]. Check your connection and try again." |
| Delete | "Couldn't delete [thing]. Try again." |
| Auth failure | "Your session expired. Sign in again to continue." |
| Network | "You seem to be offline. Your changes will sync when you're back." |

### Component Reference

- **Inline errors:** Use `<ErrorMessage>` component (`role="alert"`, `text-text-destructive`)
- **Toasts:** Use `toast.error(title, description)` from `toast.tsx`
- **Error boundary:** `<ErrorBoundary>` wraps routes in `App.tsx`

---

## 2. Empty States

Empty states are an opportunity, not a gap. They tell the user what this area is for and how to get started. A blank screen is a bug.

### Rules

1. **Every list, table, or collection that can have zero items must render an EmptyState.** Returning `null` when empty is not acceptable.
2. **EmptyState has three parts:** icon (optional, adds warmth), heading (what this area is), description (how to populate it). Optional CTA button.
3. **Copy is encouraging and action-oriented.** Not "No data" or "Nothing here." Always: what could be here + how to put it there.
4. **EmptyState replaces the content area.** Centered vertically and horizontally within the space the content would occupy.

### Copy Templates

| Context | Heading | Description |
|---------|---------|-------------|
| Task list (no tasks) | "No tasks yet" | "Add your first task above to get started." |
| Conversation list (no chats) | "No conversations yet" | "Start a conversation with your coach to see it here." |
| Subtask list (no subtasks) | "No subtasks" | "Break this task into smaller steps." |
| Search results (no matches) | "No results" | "Try different search terms." |
| Integration (not connected) | "[Service] not connected" | "Connect your [service] account to unlock [benefit]." |

### Component Reference

- **Use:** `<EmptyState>` component (SPEC-030 FU-1) with `heading`, `description`, optional `icon` and `action` props.
- **Placement:** Centered in the container where the list/content would appear.
- **Colors:** `text-text-primary` for heading, `text-text-secondary` for description, `text-text-muted` for icon.

---

## 3. Loading States

Loading states prevent layout shift and reassure the user that content is coming. The goal is perceived performance — the page should feel fast even when it isn't.

### When to Use What

| Scenario | Pattern | Example |
|----------|---------|---------|
| Page or section loading data | **Skeleton** replacing content area | Gray shimmer bars where tasks will appear |
| Button triggering an async action | **Spinner inside button** + disabled state | "Saving..." with small spinner |
| Modal loading its content | **Skeleton inside modal body** | Gray shimmer bars in the modal content area |
| Inline action (checkbox, toggle) | **Optimistic update** (no loading indicator) | Checkbox checks immediately; reverts on failure |
| Full-page navigation | **Nothing** (router handles it) | Instant page swap |

### Rules

1. **Skeletons for data loading. Spinners for action feedback.** Skeletons replace the layout where content will appear (prevents layout shift). Spinners are small, inline, and indicate "your click is being processed."
2. **Skeleton shape matches content shape.** A task list skeleton has 3-5 horizontal bars the same height as task cards. A card skeleton is a rounded rectangle. Don't use a generic centered spinner for data loading.
3. **No spinners longer than 5 seconds without explanation.** If an action takes >5s, show a message: "This is taking longer than usual..."
4. **Optimistic updates when safe.** Checking a task, toggling a setting, or reordering a list should feel instant. Update the UI immediately, sync in the background, revert on failure.
5. **Never show skeleton AND content simultaneously.** Skeleton → content (or skeleton → error). No partial states.
6. **Skeletons respect reduced motion.** When `prefers-reduced-motion: reduce`, skeletons render as static gray bars (no shimmer animation).

### Component Reference

- **Skeletons:** Use `<Skeleton>` component (SPEC-030 FU-1) with `variant="text"`, `variant="card"`, or `variant="list"`.
- **Spinners:** Use `<Spinner>` for button loading states only. Must have `role="status"` and `aria-label`.
- **Optimistic updates:** Handle in React Query's `onMutate` / Zustand stores. Revert on error.

---

## 4. Destructive Actions

Destructive actions cannot be undone. The user must confirm before anything is deleted, disconnected, or discarded.

### Rules

1. **Every destructive action requires a confirmation dialog.** No silent deletes. This includes: deleting tasks, disconnecting integrations, discarding unsaved changes, revoking tokens.
2. **Confirm dialog has a clear question and consequence.** Title: "Delete [thing]?" Description: "This can't be undone. [What will happen]."
3. **Confirm button uses destructive styling.** Red (`color="red"`, `variant="solid"`). Cancel button is `variant="soft"`, `color="gray"`.
4. **Cancel is the default (auto-focused) button.** Prevent accidental confirmation via Enter key.
5. **Confirm button label matches the action.** "Delete" not "OK". "Disconnect" not "Yes". "Discard" not "Confirm".

### Copy Templates

| Action | Title | Description | Confirm Label |
|--------|-------|-------------|---------------|
| Delete task | "Delete this task?" | "This will permanently delete the task and its subtasks." | "Delete" |
| Disconnect integration | "Disconnect [service]?" | "You'll stop receiving [what it does]. You can reconnect anytime." | "Disconnect" |
| Discard unsaved changes | "Discard changes?" | "You have unsaved changes that will be lost." | "Discard" |
| Clear conversation | "Clear this conversation?" | "All messages in this conversation will be removed." | "Clear" |

### Component Reference

- **Use:** `<ConfirmDialog>` component (SPEC-030 FU-1) with `title`, `description`, `confirmLabel`, `variant="destructive"`, `onConfirm`, `onCancel`.
- **Current anti-pattern to fix:** `window.confirm()` in `GenericModal.tsx` dirty state handling. Replace with `<ConfirmDialog>`.

---

## 5. Success Feedback

The user needs to know their action worked. But success feedback should be subtle — don't celebrate every save.

### When to Use What

| Scenario | Pattern | Example |
|----------|---------|---------|
| Inline action (check task, toggle, reorder) | **Visual state change only** | Checkbox fills, task moves, toggle slides |
| Form save / create | **Toast (success)** | "Task created" (auto-dismiss 2s) |
| Destructive action completed | **Toast (default)** | "Task deleted" (auto-dismiss 2s) |
| Multi-step process completed | **Toast (success) + state change** | "Gmail connected" + badge turns green |
| Copy to clipboard | **Tooltip or toast** | "Copied!" near the element |

### Rules

1. **Inline actions don't need toasts.** The visual state change IS the feedback. Checking a box, toggling a switch, or dragging a task is self-evident.
2. **Form submissions get a brief toast.** Success toasts auto-dismiss in 2 seconds. They confirm the save but don't demand attention.
3. **Success toasts use the `success` variant.** Green left border, standard success styling.
4. **Don't stack success toasts.** If multiple actions succeed rapidly (batch operations), show one summary toast.
5. **Success copy is past tense and concise.** "Task created" not "Your task has been successfully created!"

### Component Reference

- **Toasts:** `toast.success(title)` or `toast.success(title, description)` from `toast.tsx`. Duration: 2000ms default.

---

## 6. Form Validation

Forms validate on blur (field-level) and on submit (full form). Errors appear inline below the field. The goal: catch mistakes early without being annoying.

### Rules

1. **Validate on blur, not on every keystroke.** Real-time validation while typing is distracting (especially for users with ADHD). Wait until the user moves to the next field.
2. **Full validation on submit.** If any field fails, focus the first error field and show all errors inline.
3. **Error messages appear below the field** in `text-text-destructive`, size `text-sm`, with `role="alert"`.
4. **Error message pattern:** "[What's wrong]. [What to do]." Examples:
   - "Title is required. Add a title to save."
   - "Must be at least 3 characters. Add a few more."
   - "Invalid email format. Check for typos."
5. **Clear errors when the user fixes them.** When a field passes validation (on blur), remove its error immediately.
6. **Required fields are not marked with asterisks.** All fields are assumed required unless labeled "(optional)". This reduces visual noise.
7. **Use react-hook-form + Zod.** This is the established pattern. Don't invent custom validation.

### Technical Pattern

```
Form setup:     react-hook-form + zodResolver(schema)
Validation:     Zod schema (min/max/required/format)
Error display:  <ErrorMessage> below each field, linked via aria-describedby
Focus on error: form.setFocus(firstErrorField) on submit
```

### Component Reference

- **Validation:** Zod schema with `zodResolver` passed to `useForm`
- **Error display:** `<ErrorMessage id={fieldId + '-error'}>` below the field
- **Field linking:** `aria-describedby={fieldId + '-error'}` on the input
- **Existing example:** `TaskForm.tsx`, `AddTaskTray.tsx`

---

## 7. Approval Flows (Agent Tool Approval)

When an agent wants to perform an action that requires user consent (sending an email, modifying data, executing a tool above its trust tier), it creates an approval request. This is Clarity's core trust mechanism — the user stays in control without micro-managing.

### The Flow

```
Agent decides to use a tool that requires approval
    ↓
Backend creates pending_action (execution record) + notification (type: notify, requires_approval: true)
    ↓
Notification appears inline in chat timeline as an ApprovalInlineMessage
    ↓
Agent continues the conversation (soft-blocking, not hard-blocking)
    ↓
User reviews and approves or rejects
    ↓
On approve: tool executes → result fed back to agent → agent responds with outcome
On reject: agent is informed → agent acknowledges and adjusts
```

### Design Principles

1. **Approvals live in the conversation.** They appear inline in the chat stream, interleaved with messages by timestamp. Not in a separate panel, not behind a bell icon, not in a modal. The user encounters them naturally while chatting.

2. **Soft-blocking, not hard-blocking.** The agent doesn't halt when it needs approval. It says "I've requested approval for [tool]. Approve or reject when you're ready." and continues the conversation. If the user keeps chatting without approving, the agent nudges conversationally: "Hey, I still need your OK on that [tool] request before I can proceed." No state machine, no locked UI.

3. **Show what will happen.** The approval card shows the tool name and its arguments so the user knows exactly what they're approving. Arguments are truncated to 3 entries with an expandable "Show N more" toggle — enough to verify intent without overwhelming.

4. **One action per approval.** Each approval request is a separate inline card. Multiple pending approvals stack chronologically. The user can approve/reject in any order — no dependencies between them.

5. **Optimistic feedback.** When the user clicks Approve or Reject, the button state changes immediately (optimistic update). The actual API call happens in the background. If it fails, revert to pending with an error toast.

6. **Result closes the loop.** After approval and execution, the result appears in the approval card (see "One Card, Entire Lifecycle" below). The user sees the outcome without a separate notification fragmenting the timeline.

7. **The agent continues after resolution.** This is the most important principle. Approval is not a dead end — it's a pause in a conversation. After the tool executes (approved) or is cancelled (rejected), the result must feed back into the agent so it can respond naturally. The user asked the agent to do something; the agent should report the outcome, not go silent. The same applies to rejection — the agent should acknowledge it and adjust its plan. **An agent that goes silent after approval is broken.**

### One Card, Entire Lifecycle

The approval card is the single visual container for the full action lifecycle: request → user decision → execution result. The result does NOT appear as a separate notification in the web timeline — it folds into the same card. This prevents fragmentation and gives the user one glanceable summary per action.

```
PENDING:
┌──────────────────────────────────────────────────────┐
│ ⚠ Approval needed: delete_tasks                      │
│ ┌──────────────────────────────────────────────────┐ │
│ │ ids: ["test_task_id"]                            │ │
│ └──────────────────────────────────────────────────┘ │
│  [Approve]  [Reject]                                 │
└──────────────────────────────────────────────────────┘

RESOLVED (after approve + execution):
┌──────────────────────────────────────────────────────┐
│ ✓ delete_tasks — Approved                            │
│ ▸ Show arguments                                     │
│ Executed successfully.                    6 min ago  │
└──────────────────────────────────────────────────────┘
```

**Why not a separate follow-up notification?** The backend still creates a `silent` follow-up notification (for Telegram delivery and audit trail). But the web frontend suppresses it from the timeline when it shares a `pending_action_id` with an already-rendered approval card. The card itself shows the result. On Telegram, the follow-up still sends as a separate message — that's natural for the medium.

### States

| State | Border | Heading | Args | Actions | Result line |
|-------|--------|---------|------|---------|-------------|
| **Pending** | `border-l-warning-strong` | "Approval needed: `{tool_name}`" | Expanded (first 3 + "Show N more") | Approve + Reject buttons | — |
| **Approved (executing)** | `border-l-success-indicator` | "✓ {tool_name} — Approved" | Collapsed ("Show arguments") | Removed | "Running..." (if still executing) |
| **Approved (done)** | `border-l-success-indicator` | "✓ {tool_name} — Approved" | Collapsed | Removed | "Executed successfully." or result summary |
| **Approved (failed)** | `border-l-destructive` | "✓ {tool_name} — Approved" | Collapsed | Removed | "Failed: {error}" in `text-destructive` |
| **Rejected** | `border-l-ui-border` | "✗ {tool_name} — Rejected" | Collapsed | Removed | — |
| **Expired** | `border-l-ui-border` | "{tool_name} — Expired" | Collapsed | Removed | — |
| **Loading** | (same as pending) | (same as pending) | (same) | Buttons disabled, `opacity-50` | — |

**Key transitions:**
- Pending → Approved: optimistic on click (instant). Border shifts from warning to success. Args collapse. Buttons replaced with status + result.
- Pending → Rejected: optimistic on click. Border shifts to neutral. Args collapse.
- Args toggle: always available. Expanded by default when pending, collapsed after resolution.

### Copy

| Element | Text |
|---------|------|
| Pending heading | "Approval needed: `{tool_name}`" |
| Approved heading | "✓ {tool_name} — Approved" |
| Rejected heading | "✗ {tool_name} — Rejected" |
| Expired heading | "{tool_name} — Expired" |
| Result (success) | "Executed successfully." (or a brief summary if the backend provides one) |
| Result (failure) | "Failed: {error}" |
| Result (executing) | "Running..." |
| Agent message (on request) | "I've requested approval for '{tool_name}'. You'll see it in the chat — approve or reject when you're ready." |
| Agent nudge (if ignored) | Conversational, not formulaic. E.g., "Scroll up to approve that {tool_name} request when you get a chance." |
| Agent message (after approve) | Conversational report of what happened. E.g., "Done — I deleted 'Set up work tracking system'. You have 3 tasks left for today." |
| Agent message (after reject) | Acknowledgment + pivot. E.g., "Got it, I won't delete that. Want me to try something else?" |
| Approve button | "Approve" (with CheckCircle icon) |
| Reject button | "Reject" (with XCircle icon) |
| Args toggle (collapsed) | "Show arguments" / "Hide arguments" |

### Accessibility

- Approval card has `role="alert"` — screen readers announce it when it appears
- Approve/Reject buttons have `aria-label="Approve action"` / `aria-label="Reject action"`
- Disabled buttons during mutation prevent double-submit
- After resolution (approved/rejected/expired), the status text replaces the buttons — screen readers get the final state

### Notifications (Non-Approval)

Regular notifications (agent observations, status updates, feedback requests) also appear inline in the chat timeline. They follow a simpler pattern:

| Element | Behavior |
|---------|----------|
| **Visual** | Left border colored by category (brand = heartbeat, warning = approval, info = result, destructive = error, neutral = info) |
| **Content** | Title (bold) + body + relative timestamp |
| **Feedback** | Thumbs up/down buttons (per SPEC-024). Already-voted state dims the unselected thumb. |
| **Auto-read** | Marked as read on mount — no explicit "mark read" action needed |
| **Accessibility** | `role="status"` + `aria-label` with notification title |

### When to Create Notifications vs. Chat Messages

| Signal | Type | Channel |
|--------|------|---------|
| Agent internal finding (heartbeat) | `agent_only` | Memory only — not stored, not shown |
| Background status update (processing complete, sync done) | `silent` | Chat stream only — no Telegram |
| Something that needs attention (approval, reminder, digest) | `notify` | Chat stream + Telegram |
| Agent's conversational response | Regular chat message | Chat stream (+ Telegram echo if linked) |

---

## 8. Agent Continuation (Never Dead-End the Agent)

This is a cross-cutting principle that applies to every interaction involving the agent. **Any time the agent's execution is interrupted or deferred, the result must feed back into the agent so it can continue the conversation.**

### Why This Matters

Clarity is a conversational agent. The user talks to it, it does things, it reports back. If the agent goes silent after an action completes, the conversation feels broken. The user is left wondering: "Did it work? What happened? Is it still thinking?" This is especially harmful for ADHD users who rely on clear closure and explicit next steps.

### The Pattern

```
Agent's turn is interrupted (approval needed, background job, external callback)
    ↓
Interruption resolves (user approves, job finishes, callback arrives)
    ↓
Result is fed back to agent as a system/follow-up message
    ↓
Agent responds conversationally: reports outcome, suggests next steps
```

### Where This Applies

| Interruption | Resolution trigger | What feeds back to agent |
|-|-|-|
| **Tool approval** | User clicks Approve/Reject | Tool execution result or rejection reason |
| **Background job** | Job completes (email sync, heartbeat) | Job output summary |
| **External callback** | Webhook or OAuth callback | Callback payload |
| **Scheduled task** | Timer fires (morning briefing) | Pre-computed context |

### Implementation Mechanism

The simplest approach: after resolution, the frontend sends a follow-up chat message on behalf of the system. The message is prefixed to distinguish it from user input:

```
[System: Action 'delete_tasks' was approved and executed. Result: Task deleted successfully.]
```

The agent receives this as input on its next turn and responds naturally:

```
Done — I deleted 'Set up work tracking system'. You've got 3 tasks left today.
```

This works because:
- The agent's conversation memory already tracks context (it remembers requesting the approval)
- A chat message is the natural interface — no new infrastructure needed
- The frontend already has the result from the approve API response
- It works for both web and Telegram channels

### Anti-Patterns

| Anti-pattern | Why it's wrong |
|-|-|
| Agent goes silent after tool approval | User has no closure, no confirmation, no next step |
| Result only shown in a notification | Notifications are informational; the agent should *respond* |
| Agent re-asks what the user wanted | Conversation memory should retain the original request |
| Multiple system messages for one action | One message per resolution, one agent response |

---

## Decision Tree

When adding a new interaction, ask:

```
Does this component fetch data?
  → Yes: Add skeleton loader (loading) + inline error (error) + EmptyState (empty)
  → No: continue

Does this component accept user input?
  → Yes: Add validation (blur + submit) with inline ErrorMessage
  → No: continue

Can the user destroy data from here?
  → Yes: Add ConfirmDialog before the action
  → No: continue

Does this involve the agent doing something on the user's behalf?
  → Yes, requires user consent: Approval flow (inline card, approve/reject buttons)
  → Yes, auto-approved: Regular notification (silent type, FYI)
  → No: continue

Does this action have a meaningful result?
  → Yes, it's inline (toggle/check): Visual state change only
  → Yes, it's a form save: Toast success
  → Yes, it's destructive: Toast default
  → No: No feedback needed
```
