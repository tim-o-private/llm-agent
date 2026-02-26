# SPEC-007: Frontend Cleanup + Approval Toasts

> **Status:** Draft
> **Author:** Tim + Claude
> **Created:** 2026-02-18
> **Updated:** 2026-02-18

## Goal

Remove dead code and test pages, then add toast notifications for blocking approval requests. The frontend should be lean and only contain production features. Approval-needed notifications must be impossible to miss.

## Problem

Today, the frontend has:
- 8 test/demo pages that ship to production (DesignSystem, ColorSwatch, ModalTest, SelectTest, TodayViewMockup, DesignDemo, LayoutMockups, coach-v2)
- CoachPage that's just a thin wrapper around ChatPanel (which is already accessible via AppShell slide-out)
- ChatPanelV1 (legacy, unused — ChatPanel delegates to V2)
- Nav items pointing to nonexistent pages ("Focus") or test pages ("Today Mockup")
- No visible alert when the agent is blocked waiting for approval — the user has to notice the badge count changed

## Acceptance Criteria

### Cleanup
- [ ] AC-1: CoachPage.tsx and CoachPageV2.tsx deleted; `/coach` and `/coach-v2` routes removed
- [ ] AC-2: ChatPanelV1.tsx deleted
- [ ] AC-3: Test/demo pages deleted: DesignSystemPage, ColorSwatchPage, ModalTestPage, SelectTestPage, TodayViewMockup, DesignDemo, LayoutMockups
- [ ] AC-4: All routes for deleted pages removed from App.tsx
- [ ] AC-5: "Focus" and "Today Mockup" removed from navConfig; "Coach" nav item removed or repurposed
- [ ] AC-6: No dead imports remain (ESLint clean)

### Approval Toasts
- [ ] AC-7: When a new `approval_needed` notification arrives, a toast appears automatically
- [ ] AC-8: Toast includes the tool name and a button/link to approve or reject
- [ ] AC-9: Toast persists until dismissed (does not auto-hide) — approvals are blocking
- [ ] AC-10: Toast uses existing Radix Toast primitive (`components/ui/Toast.tsx`)
- [ ] AC-11: Multiple pending approvals show multiple toasts (or a stacked count)

### Notification Categories
- [ ] AC-12: `reminder` category renders correctly in NotificationBadge dropdown (from SPEC-006)
- [ ] AC-13: `digest` category renders correctly in NotificationBadge dropdown (from SPEC-006)
- [ ] AC-14: Each category has a distinct icon or color indicator

## Scope

### Files to Delete

| File | Reason |
|------|--------|
| `webApp/src/pages/CoachPage.tsx` | Thin wrapper, chat accessible from AppShell |
| `webApp/src/pages/CoachPageV2.tsx` | Test variant of above |
| `webApp/src/components/chat/ChatPanelV1.tsx` | Legacy, unused |
| `webApp/src/pages/DesignSystemPage.tsx` | Test page |
| `webApp/src/pages/ColorSwatchPage.tsx` | Test page |
| `webApp/src/pages/ModalTestPage.tsx` | Test page |
| `webApp/src/pages/SelectTestPage.tsx` | Test page |
| `webApp/src/pages/TodayViewMockup.tsx` | Test page |
| `webApp/src/components/ui/DesignDemo.tsx` | Test component |
| `webApp/src/pages/LayoutMockups.tsx` | Test page (if exists) |

### Files to Modify

| File | Change |
|------|--------|
| `webApp/src/App.tsx` | Remove routes for deleted pages |
| `webApp/src/layouts/navConfig.ts` | Remove "Coach", "Focus", "Today Mockup" nav items |
| `webApp/src/components/features/Notifications/NotificationBadge.tsx` | Add `reminder` and `digest` category rendering |
| `webApp/src/components/ui/Toast.tsx` | May need enhancement for persistent/actionable toasts |

### Files to Create

| File | Purpose |
|------|---------|
| `webApp/src/components/features/Notifications/ApprovalToast.tsx` | Toast component for approval-needed notifications |
| `webApp/src/hooks/useApprovalToast.ts` | Hook that watches for new approval_needed notifications and triggers toasts |

### Out of Scope

- Chat history sidebar (future — needs design work)
- Notification inbox page (badge dropdown is sufficient for now)
- Scheduled execution dashboard (future spec)
- Agent configuration UI (future spec)
- Notes integration in main nav (future)

## Technical Approach

### Unit 1: Delete Cruft

**Branch:** `feat/SPEC-007-cleanup`

Straightforward deletion:
1. Delete all files listed above
2. Remove routes from App.tsx
3. Remove nav items from navConfig
4. Remove any dead imports
5. Run `pnpm lint` and `pnpm build` to verify no broken references

### Unit 2: Approval Toasts

**Branch:** `feat/SPEC-007-approval-toasts`

**Implementation approach:**

Create a `useApprovalToast` hook that:
1. Uses `useUnreadCount()` or `useNotifications()` to detect new `approval_needed` notifications
2. Compares against previously-seen notification IDs (ref or state)
3. When a new approval notification appears, calls the toast API
4. Toast includes: tool name, agent name, and Approve/Reject buttons
5. Approve/Reject buttons call the existing actions API (`/api/actions/{id}/approve` or `/api/actions/{id}/reject`)
6. Toast dismisses on action

**Toast behavior:**
- Uses Radix Toast (`@radix-ui/react-toast`)
- `duration: Infinity` (persists until user acts)
- Stacks if multiple approvals pending
- Links to PendingActionsPanel for bulk management if > 3 pending

**Mount point:** Add `<ApprovalToastProvider>` in AppShell or App.tsx, alongside existing `<Toaster>`.

### Unit 3: Notification Categories

**Branch:** Can be part of Unit 2's branch.

In `NotificationBadge.tsx`, add category-specific rendering:
- `approval_needed`: warning icon, amber color
- `reminder`: clock icon, blue color
- `digest`: mail icon, green color
- `agent_result`: bot icon, default color
- `heartbeat`: pulse icon, muted color
- `error`: alert icon, red color

## Testing Requirements

### Unit Tests (Vitest)
- `test_approval_toast_appears_on_new_notification`
- `test_approval_toast_does_not_repeat_for_seen_notifications`
- `test_approve_button_calls_api_and_dismisses`
- `test_reject_button_calls_api_and_dismisses`
- `test_notification_categories_render_correct_icons`

### Manual Verification
- [ ] Build succeeds after deletions (`pnpm build`)
- [ ] No broken links in navigation
- [ ] Chat still accessible via AppShell slide-out toggle
- [ ] Create a pending action → toast appears → approve via toast → toast dismisses
- [ ] Check NotificationBadge dropdown shows reminder/digest categories with correct styling

## Functional Units (PR Breakdown)

1. **Unit 1:** Delete cruft (`feat/SPEC-007-cleanup`) — **frontend-dev**
2. **Unit 2:** Approval toasts + notification categories (`feat/SPEC-007-approval-toasts`) — **frontend-dev**

Both units are independent and could run in parallel, but they're small enough to do sequentially with one agent.

## Dependencies

- No backend changes required
- SPEC-006 should be merged first (or at least Unit 3) so `reminder` category notifications exist to test against
- If SPEC-006 isn't merged yet, category rendering can be tested with mock data
