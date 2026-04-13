# SPEC-030: UX Baseline & Interaction Standards

> **Status:** Draft
> **Author:** UX Designer Agent + Tim
> **Created:** 2026-02-26
> **Updated:** 2026-02-26

## Goal

Establish the interaction patterns and component quality floor that all current and future features must meet. This spec addresses gaps identified in the initial UX audit: inconsistent error/empty/loading states, accessibility holes, and undocumented interaction patterns. Without this baseline, each Phase 2 workstream (calendar, briefings, draft-reply) will re-invent these patterns independently, producing an incoherent product.

This is infrastructure, not polish. The deliverables are: reusable primitives, enforceable standards, and reference documentation that frontend-dev treats as a contract.

## Acceptance Criteria

### Interaction Patterns

- [ ] **AC-01:** A documented interaction patterns spec exists at `docs/ux/interaction-patterns.md` covering error states, empty states, loading states, destructive actions, success feedback, and form validation — with clear rules for when to use each variant (inline vs. toast vs. boundary). [F2]
- [ ] **AC-02:** Every component that fetches async data renders a skeleton loader (not a spinner) during loading, preventing layout shift. Spinner is reserved for inline action feedback only (button submitting, etc.). [ADHD: reduce visual noise]
- [ ] **AC-03:** Every component that can have zero items renders a standardized empty state with icon, message, and optional CTA — using a shared `EmptyState` primitive. [ADHD: encouraging, not blank]
- [ ] **AC-04:** Every destructive action (delete task, disconnect integration, discard changes) shows a confirmation dialog using a shared `ConfirmDialog` primitive. No silent deletes. [A12: safety rails]
- [ ] **AC-05:** Form validation errors appear inline below the field on blur, with full validation on submit. Error copy follows the pattern: "[What went wrong]. [What to do]." (e.g., "Title is required. Add a title to save.") [ADHD: clear next step]

### Accessibility

- [ ] **AC-06:** `Spinner.tsx` has `role="status"` and a configurable `aria-label` (default: "Loading"). [WCAG 2.1 AA: 4.1.2]
- [ ] **AC-07:** Chat message container and notification areas have `aria-live="polite"` so screen readers announce new content. [WCAG 2.1 AA: 4.1.3]
- [ ] **AC-08:** AppShell includes a visually-hidden "Skip to main content" link as the first focusable element, targeting the main content area. [WCAG 2.1 AA: 2.4.1]
- [ ] **AC-09:** All icon-only buttons (`IconButton` usages) have an `aria-label`. Any without are fixed. [WCAG 2.1 AA: 1.1.1]
- [ ] **AC-10:** All CSS animations respect `prefers-reduced-motion: reduce` — animations are disabled or replaced with instant transitions. Applied globally via a media query in `index.css`. [WCAG 2.1 AA: 2.3.3]
- [ ] **AC-11:** Every interactive element has a visible focus indicator. Audit confirms no component is missing `getFocusClasses()` or equivalent. [WCAG 2.1 AA: 2.4.7]

### Design Token Cleanup

- [ ] **AC-12:** Shadow tokens `shadow-neon` and `shadow-electric` are removed from `tailwind.config.js` and `card-system.css`. All usages are replaced with `shadow-glow` (subtle) or `shadow-elevated` (depth). [Design philosophy: calm & minimal]
- [ ] **AC-13:** Vibrant color tokens (`accent-electric`, `accent-neon`, `accent-glow`, `info-electric`, `success-electric`, `warning-glow`) are removed from `tailwind.config.js`. Usages in ColorSwatchPage are removed. The one usage in `TaskCard.tsx` (`info-electric` for priority 1) is replaced with `bg-info-subtle` or equivalent approved token. [Design philosophy: calm & minimal]
- [ ] **AC-14:** `card-system.css` is pruned: remove unused animation classes and shadow definitions that reference deleted tokens. Remaining effects use `shadow-glow` and `shadow-elevated` only. [Reduce dead CSS]

### Component Standardization

- [ ] **AC-15:** A reusable `EmptyState` component exists in `components/ui/` with props: `icon` (optional), `heading` (string), `description` (string), `action` (optional ReactNode for CTA button). Uses semantic tokens. [A10, F2]
- [ ] **AC-16:** A reusable `Skeleton` component exists in `components/ui/` with variants: `text` (single line), `card` (rectangle), `list` (repeated rows). Animated with CSS `shimmer` keyframe. Respects `prefers-reduced-motion`. [A10, F2]
- [ ] **AC-17:** A reusable `ConfirmDialog` component exists in `components/ui/` wrapping Radix Dialog, with props: `title`, `description`, `confirmLabel` (default: "Delete"), `cancelLabel` (default: "Cancel"), `variant` ("destructive" | "warning"), `onConfirm`, `onCancel`. [A10, F2]
- [ ] **AC-18:** Existing loading states are retrofitted: `TodayView` task list, `TaskDetailView`, `ConversationList`, `PrioritizeViewModal` use `Skeleton` instead of `Spinner` for data loading. `Spinner` usage is limited to inline action feedback (button loading states). [AC-02]

### Documentation

- [ ] **AC-19:** `docs/ux/interaction-patterns.md` exists and covers: error state rules, empty state rules, loading state rules, destructive action rules, success feedback rules, form validation rules. Each rule has a "when to use" decision tree and copy templates. [F2]
- [ ] **AC-20:** `docs/ux/component-inventory.md` exists listing every `components/ui/` primitive with: name, purpose, key props, variants, and "when to use / when not to use" guidance. [F2]
- [ ] **AC-21:** `docs/ux/accessibility-checklist.md` exists with a per-component checklist that frontend-dev and UX reviewer reference during implementation and review. [S1: done = verified]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `webApp/src/components/ui/EmptyState.tsx` | Reusable empty state component |
| `webApp/src/components/ui/Skeleton.tsx` | Reusable skeleton loader component |
| `webApp/src/components/ui/ConfirmDialog.tsx` | Reusable confirmation dialog component |
| `docs/ux/interaction-patterns.md` | Interaction pattern rules and copy templates |
| `docs/ux/component-inventory.md` | Component catalog with usage guidance |
| `docs/ux/accessibility-checklist.md` | Per-component accessibility checklist |

### Files to Modify

| File | Change |
|------|--------|
| `webApp/src/components/ui/Spinner.tsx` | Add `role="status"`, configurable `aria-label` |
| `webApp/src/components/ui/index.ts` | Export new components |
| `webApp/src/pages/TodayView.tsx` | Replace spinner with skeleton for task list loading |
| `webApp/src/components/features/TaskDetail/TaskDetailView.tsx` | Replace spinner with skeleton; add ConfirmDialog for delete |
| `webApp/src/components/features/Conversations/ConversationList.tsx` | Replace spinner with skeleton; add EmptyState |
| `webApp/src/components/features/PrioritizeView/PrioritizeViewModal.tsx` | Replace spinner with skeleton |
| `webApp/src/components/ChatPanelV2.tsx` | Add `aria-live="polite"` to message container |
| `webApp/src/components/ui/chat/NotificationInlineMessage.tsx` | Verify `aria-live` on notification container |
| `webApp/src/layouts/AppShell.tsx` | Add skip-to-main link; replace `shadow-neon`/`shadow-electric` with `shadow-glow`/`shadow-elevated` |
| `webApp/src/components/ui/TaskCard.tsx` | Replace `info-electric` with approved token |
| `webApp/src/pages/ColorSwatchPage.tsx` | Remove references to deleted tokens; update demo sections |
| `webApp/src/pages/DesignSystemPage.tsx` | Update if referencing deleted tokens |
| `webApp/src/styles/card-system.css` | Remove `shadow-neon`, `shadow-electric` definitions; prune unused animation classes |
| `webApp/src/styles/index.css` | Add global `prefers-reduced-motion` rule |
| `webApp/tailwind.config.js` | Remove `neon`/`electric` shadow tokens; remove vibrant color tokens |
| `webApp/src/utils/color-validation.ts` | Remove deleted tokens from `APPROVED_COLOR_TOKENS` |
| `webApp/src/components/ui/LayoutMockups.tsx` | Replace deleted shadow tokens |
| `webApp/src/pages/TodayViewMockup.tsx` | Replace deleted shadow tokens |

### Out of Scope

- Mobile/responsive design — conscious deferral, separate spec when prioritized
- Typography scale / spacing token system — valuable but not blocking Phase 2
- Storybook or visual regression testing setup
- Redesigning existing page flows (TodayView layout, chat panel position)
- New feature UX (calendar UI, briefing display, draft-reply editor) — those belong in their respective specs, but will reference the patterns established here
- Keyboard shortcuts documentation — tracked separately

## Technical Approach

### New Primitives

**EmptyState** — simple presentational component:
- Renders centered icon (Heroicons, optional), heading, description, and optional CTA button
- Uses `text-text-secondary` for description, `text-text-primary` for heading
- See `frontend-patterns` skill for Radix + Tailwind component pattern

**Skeleton** — CSS-animated placeholder:
- Three variants: `text` (h-4 rounded bar), `card` (h-24 rounded rectangle), `list` (N repeated text skeletons with spacing)
- Uses existing `shimmer` keyframe from `tailwind.config.js`
- Wraps content in `prefers-reduced-motion` check — static gray bar when motion is reduced
- See `frontend-patterns` skill for animation patterns

**ConfirmDialog** — Radix Dialog wrapper:
- Reuses the existing Radix Dialog pattern from `Modal.tsx`
- Two variants: `destructive` (red confirm button) and `warning` (amber confirm button)
- Focus trap and keyboard support come free from Radix
- See `frontend-patterns` skill for modal overlay pattern

### Accessibility Fixes

- Spinner fix is a 2-line change (add `role` and `aria-label` props)
- `aria-live` regions: add attribute to the chat message scroll container in ChatPanelV2
- Skip link: absolute-positioned, visually hidden until focused, appears at top of viewport
- Reduced motion: single `@media (prefers-reduced-motion: reduce)` block in `index.css` that sets `animation-duration: 0.01ms !important; transition-duration: 0.01ms !important;` globally

### Token Cleanup

- Remove tokens from `tailwind.config.js` first
- Run build — find all compilation errors from missing classes
- Replace each usage: `shadow-neon` → `shadow-glow`, `shadow-electric` → `shadow-elevated`, vibrant colors → nearest approved semantic token
- Update `card-system.css` to remove orphaned definitions
- Update `color-validation.ts` approved list

### Dependencies

- No backend changes required
- No database changes required
- No API changes required
- Depends on: existing Radix Dialog, existing Tailwind config, existing `shimmer` keyframe

## Testing Requirements

### Unit Tests (required)

- `EmptyState.test.tsx` — renders heading, description, optional icon, optional CTA; CTA click fires handler
- `Skeleton.test.tsx` — renders text/card/list variants; respects count prop for list
- `ConfirmDialog.test.tsx` — renders title/description; confirm click fires handler; cancel click fires handler; Escape closes; focus trapped
- `Spinner.test.tsx` — update existing tests: verify `role="status"` present, verify `aria-label` renders

### Integration Tests (required for retrofitted components)

- `TodayView.test.tsx` — loading state renders skeleton, not spinner
- `ConversationList.test.tsx` — empty state renders EmptyState component with correct copy

### Accessibility Tests

- All new components: verify with `@testing-library/jest-dom` `toHaveAttribute('role', ...)`, `toHaveAttribute('aria-label', ...)`
- ChatPanelV2: verify message container has `aria-live="polite"`
- AppShell: verify skip link exists and is focusable

### AC-to-Test Mapping

| AC | Test Type | Test Function |
|----|-----------|--------------|
| AC-02 | Integration | `test_ac_02_skeleton_loaders_replace_spinners` |
| AC-03 | Unit | `test_ac_03_empty_state_component` |
| AC-04 | Unit | `test_ac_04_confirm_dialog` |
| AC-06 | Unit | `test_ac_06_spinner_accessibility` |
| AC-07 | Integration | `test_ac_07_aria_live_regions` |
| AC-08 | Integration | `test_ac_08_skip_to_main_link` |
| AC-15 | Unit | `test_ac_15_empty_state_props` |
| AC-16 | Unit | `test_ac_16_skeleton_variants` |
| AC-17 | Unit | `test_ac_17_confirm_dialog_behavior` |

### Manual Verification (UAT)

- [ ] Load TodayView with slow network — skeleton loaders visible, no layout shift
- [ ] Delete a task — confirmation dialog appears with "Delete" / "Cancel"
- [ ] View empty conversation list — EmptyState with helpful message visible
- [ ] Tab through AppShell — skip link appears on first Tab press, jumps to main content
- [ ] Enable "reduce motion" in OS settings — all animations stop
- [ ] Use screen reader (VoiceOver/NVDA) on chat — new messages announced
- [ ] All interactive elements have visible focus ring when tabbed to
- [ ] No `shadow-neon` or `shadow-electric` visible anywhere in UI (inspect AppShell sidebar, chat panel)

## Edge Cases

- **Empty state with loading:** If data is loading, show skeleton. If data loaded and is empty, show EmptyState. Never show both simultaneously.
- **ConfirmDialog during navigation:** If user navigates away while dialog is open, dialog closes without action (no accidental confirm).
- **Skeleton with error:** If loading fails, skeleton transitions to error state (inline error or ErrorMessage), not to EmptyState.
- **Reduced motion + skeleton:** Skeleton still renders (gray bar) but shimmer animation doesn't play.
- **Multiple ConfirmDialogs:** Only one can be open at a time (Radix Dialog handles this via portal stacking).

## Functional Units (for PR Breakdown)

Each unit gets its own branch and PR. Units 1-3 are independent and can be developed in parallel. Unit 4 depends on Unit 1. Unit 5 depends on Units 1-3.

1. **FU-1: New primitives** (`feat/SPEC-030-primitives`)
   - Create `EmptyState.tsx`, `Skeleton.tsx`, `ConfirmDialog.tsx`
   - Unit tests for all three
   - Export from `components/ui/index.ts`
   - Domain: frontend-dev

2. **FU-2: Accessibility fixes** (`feat/SPEC-030-accessibility`)
   - Fix `Spinner.tsx` (role, aria-label)
   - Add `aria-live` to ChatPanelV2 message container
   - Add skip-to-main link in AppShell
   - Add `prefers-reduced-motion` global rule in `index.css`
   - Audit and fix icon-only buttons missing `aria-label`
   - Audit and fix focus indicators
   - Tests for all changes
   - Domain: frontend-dev

3. **FU-3: Token cleanup** (`feat/SPEC-030-token-cleanup`)
   - Remove `neon`/`electric` shadows from tailwind.config.js and card-system.css
   - Remove vibrant color tokens from tailwind.config.js
   - Replace all usages in AppShell, LayoutMockups, TodayViewMockup, ColorSwatchPage, DesignSystemPage, TaskCard
   - Update `color-validation.ts` approved list
   - Domain: frontend-dev

4. **FU-4: Retrofit existing components** (`feat/SPEC-030-retrofit`)
   - Replace Spinner with Skeleton in: TodayView, TaskDetailView, ConversationList, PrioritizeViewModal
   - Add EmptyState to: ConversationList, any other empty-capable lists
   - Add ConfirmDialog to: TaskCard delete action (and any other unguarded destructive actions found)
   - Integration tests
   - Depends on: FU-1
   - Domain: frontend-dev

5. **FU-5: UX documentation** (`feat/SPEC-030-ux-docs`)
   - Write `docs/ux/interaction-patterns.md`
   - Write `docs/ux/component-inventory.md`
   - Write `docs/ux/accessibility-checklist.md`
   - Depends on: FU-1, FU-2, FU-3 (docs reference final component APIs and token list)
   - Domain: UX designer (me)

**Merge order:** FU-1 → FU-4 (sequential). FU-2, FU-3 can merge independently. FU-5 merges last.

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-21)
- [x] Every AC maps to at least one functional unit
- [x] Technical decisions reference principles (F2, A10, A12, S1)
- [x] Merge order is explicit and acyclic
- [x] Out of scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
- [x] No backend or database changes required
- [x] Design philosophy (calm, ADHD-friendly) referenced in relevant ACs
