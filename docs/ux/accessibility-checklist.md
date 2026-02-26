# Accessibility Checklist

> **Owner:** UX Designer
> **Status:** Baseline v1
> **Spec:** SPEC-030
> **Target:** WCAG 2.1 AA
> **Last updated:** 2026-02-26

Use this checklist during development and UX review. Every component that ships must pass the applicable sections.

---

## Per-Component Checklist

For every new or modified interactive component, verify:

### Keyboard

- [ ] **Focusable:** Component can receive focus via Tab key
- [ ] **Focus visible:** Focus ring is visible (uses `getFocusClasses()` or equivalent)
- [ ] **Operable:** Primary action works with Enter or Space
- [ ] **Dismissible:** Escape closes overlays, menus, and tooltips
- [ ] **No keyboard trap:** User can Tab out of the component (unless it's a modal with intentional focus trap)
- [ ] **Logical tab order:** Focus moves in a predictable order (DOM order, left-to-right, top-to-bottom)

### Screen Reader

- [ ] **Accessible name:** Interactive elements have a visible label or `aria-label`
- [ ] **Role communicated:** Correct semantic HTML or ARIA `role` (e.g., `role="alert"` for errors, `role="status"` for loading)
- [ ] **State communicated:** Checked/unchecked, expanded/collapsed, disabled — conveyed via ARIA attributes or native HTML
- [ ] **Dynamic updates announced:** New content in live regions uses `aria-live="polite"` (or `"assertive"` for errors)
- [ ] **No phantom text:** Decorative icons have `aria-hidden="true"`; informational icons have `aria-label`

### Visual

- [ ] **Color contrast:** Text meets 4.5:1 (normal text) or 3:1 (large text, 18px+ or 14px+ bold) against its background
- [ ] **Not color-only:** Information conveyed by color also has a text label, icon, or pattern (e.g., error = red + error icon + error text)
- [ ] **Reduced motion:** Animations respect `prefers-reduced-motion: reduce` (disabled or replaced with instant transitions)
- [ ] **Zoom safe:** Content is readable at 200% browser zoom without horizontal scrolling

---

## Component-Specific Requirements

### Buttons (Button, IconButton, FAB)

| Requirement | Status | Notes |
|------------|--------|-------|
| `aria-label` on icon-only buttons | Required | `IconButton` and `FAB` must always have `aria-label` |
| Disabled state communicated | Built-in | HTML `disabled` attribute handles this |
| Loading state communicated | Verify | When showing spinner inside button, add `aria-busy="true"` or change label to "Saving..." |
| Focus ring visible | Built-in | Via `getFocusClasses()` |

### Forms (Input, Textarea, Select, Checkbox, ToggleField)

| Requirement | Status | Notes |
|------------|--------|-------|
| Label associated with input | Required | `<Label htmlFor={id}>` or `aria-label` |
| Error linked to input | Required | `aria-describedby={errorId}` on input, matching `id` on `ErrorMessage` |
| Error announced | Built-in | `ErrorMessage` has `role="alert"` |
| Required fields indicated | Convention | Don't mark required. Mark optional with "(optional)" suffix on label |
| Invalid state | Required | `aria-invalid="true"` when validation fails |

### Modals (Modal, GenericModal, ConfirmDialog)

| Requirement | Status | Notes |
|------------|--------|-------|
| Focus trapped inside modal | Built-in | Radix Dialog handles focus trap |
| Focus moves to modal on open | Built-in | Radix Dialog handles this |
| Focus returns to trigger on close | Built-in | Radix Dialog handles this |
| Escape closes modal | Built-in | Radix Dialog handles this |
| Title announced | Required | `Dialog.Title` must be present (even if visually hidden) |
| Background content inert | Built-in | Radix Dialog adds `aria-hidden` to rest of page |

### Loading (Spinner, Skeleton)

| Requirement | Status | Notes |
|------------|--------|-------|
| Spinner has `role="status"` | **Fix needed** | SPEC-030 AC-06 |
| Spinner has `aria-label` | **Fix needed** | SPEC-030 AC-06. Default: "Loading" |
| Skeleton has `aria-hidden="true"` | Required | Skeletons are decorative — screen readers should skip them |
| Loading state announced | Required | Container with spinner/skeleton should have `aria-busy="true"` |

### Errors (ErrorMessage, Toast)

| Requirement | Status | Notes |
|------------|--------|-------|
| Inline errors have `role="alert"` | Built-in | `ErrorMessage` does this |
| Toast errors announced | Built-in | Radix Toast has implicit `aria-live` |
| Error not color-only | Verify | Error text should accompany any red styling |

### Dynamic Content (Chat, Notifications)

| Requirement | Status | Notes |
|------------|--------|-------|
| Chat message container has `aria-live="polite"` | **Fix needed** | SPEC-030 AC-07 |
| Notification area has `aria-live="polite"` | Verify | `NotificationInlineMessage` has `role="status"` but check container |
| New messages don't steal focus | Required | `aria-live="polite"` waits for user pause before announcing |
| Approval status changes announced | Verify | `ApprovalInlineMessage` has `role="alert"` |

### Navigation (SideNav, TopBar, AppShell)

| Requirement | Status | Notes |
|------------|--------|-------|
| Skip-to-main-content link | **Fix needed** | SPEC-030 AC-08 |
| Nav has `role="navigation"` + `aria-label` | Built-in | SideNav has both |
| Current page indicated | Built-in | `aria-current="page"` on active nav item |
| Arrow key navigation in SideNav | Built-in | Up/down arrow keys with wrapping |

### Status Indicators (Badge, TaskStatusBadge)

| Requirement | Status | Notes |
|------------|--------|-------|
| Status text is readable (not icon-only) | Built-in | Both render text |
| Color not sole indicator | Built-in | Text label accompanies color |

---

## Page-Level Checklist

Before shipping a new page or major page change:

### Structure
- [ ] Page has an `<h1>` (one per page, describes the page purpose)
- [ ] Heading hierarchy is sequential (`h1` → `h2` → `h3`, no skipping)
- [ ] Landmark regions used: `<main>`, `<nav>`, `<header>`, `<aside>` where appropriate
- [ ] Skip-to-main-content link works (Tab from top of page, Enter skips to main content)

### Interactive Elements
- [ ] Every interactive element reachable via Tab
- [ ] Tab order follows visual layout (no unexpected jumps)
- [ ] No focus loss — after an interaction (close modal, delete item), focus moves to a logical place
- [ ] Custom keyboard shortcuts don't conflict with screen reader commands
- [ ] Custom keyboard shortcuts are suppressed when user is typing in an input/textarea

### Content
- [ ] Images have `alt` text (or `alt=""` + `aria-hidden="true"` if decorative)
- [ ] Links have descriptive text (not "click here" — prefer "View task details")
- [ ] Time-sensitive content has no hard time limit (or provides a way to extend)

---

## Testing Approach

### Automated (Run in CI)

- **axe-core / jest-axe:** Add `toHaveNoViolations()` to component tests for automated WCAG checks
- **ESLint plugin:** `eslint-plugin-jsx-a11y` catches missing `alt`, `aria-label`, form associations

### Manual (Per PR with UI changes)

1. **Keyboard walkthrough:** Tab through the feature without a mouse. Can you do everything?
2. **Screen reader spot-check:** Turn on VoiceOver (Mac) or NVDA (Windows). Navigate through the new feature. Are elements announced correctly?
3. **Zoom test:** Set browser zoom to 200%. Does the layout break?
4. **Reduced motion test:** Enable "Reduce motion" in OS accessibility settings. Do animations stop?
5. **Color contrast spot-check:** Use browser DevTools or a contrast checker on any new color combinations

### Tools

| Tool | Purpose | When |
|------|---------|------|
| axe DevTools (browser extension) | Full-page accessibility scan | During development |
| Lighthouse (Chrome DevTools) | Accessibility score + issues | Before PR |
| VoiceOver / NVDA | Screen reader testing | Manual review |
| WebAIM Contrast Checker | Verify color contrast ratios | When using new color combinations |
| `eslint-plugin-jsx-a11y` | Lint for common a11y mistakes | Automated in CI |

---

## Known Issues (Pre-SPEC-030)

Issues identified in the UX audit that SPEC-030 will fix:

| Issue | Component | AC |
|-------|-----------|-----|
| Spinner missing `role="status"` and `aria-label` | `Spinner.tsx` | AC-06 |
| Chat messages not in `aria-live` region | `ChatPanelV2.tsx` | AC-07 |
| No skip-to-main-content link | `AppShell.tsx` | AC-08 |
| Icon-only buttons may lack `aria-label` | Various | AC-09 |
| Animations don't respect `prefers-reduced-motion` | Global | AC-10 |
| Some components may lack focus indicators | Various | AC-11 |

---

## Quick Decision Guide

| "Do I need to..." | Answer |
|-------------------|--------|
| Add `aria-label` to this button? | Yes, if it has no visible text label |
| Add `role="alert"` to this error? | Yes, if it appears dynamically. Use `ErrorMessage` component. |
| Add `aria-live` to this container? | Yes, if content updates without a page load and the user should know |
| Add keyboard support? | Yes, if it's interactive. Clickable = Enter/Space. Escape = close. |
| Support reduced motion? | Yes, if it has CSS animations or transitions. Use the global media query. |
| Test with a screen reader? | Yes, if it's a new interactive feature. Quick VoiceOver walkthrough is enough. |
