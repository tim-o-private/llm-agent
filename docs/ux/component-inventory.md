# Component Inventory

> **Owner:** UX Designer
> **Status:** Baseline v1
> **Spec:** SPEC-030
> **Last updated:** 2026-02-26

Every reusable component in `webApp/src/components/ui/`. This is the reference for "what do we have" — check here before building something new.

Components are listed by category. Each entry includes: what it does, key props, when to use it, and what not to use it for.

---

## Buttons & Actions

### Button
**File:** `Button.tsx` | **Foundation:** Radix Themes `Button`

The primary interactive element. Wraps Radix Button with our focus system.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `variant` | `classic` \| `solid` \| `soft` \| `surface` \| `outline` \| `ghost` | `solid` | `solid` for primary actions, `soft` for secondary, `ghost` for tertiary |
| `size` | `1` \| `2` \| `3` \| `4` | `2` | Standard is `2` |
| `color` | Radix color | (accent) | Use sparingly. `red` for destructive only. |
| `disabled` | boolean | `false` | Applies opacity + removes focus ring |
| `asChild` | boolean | `false` | Compose with other elements (e.g., links) |

**Use for:** Any clickable action — form submits, CTAs, navigation triggers.
**Don't use for:** Icon-only buttons (use `IconButton`), floating actions (use `FAB`).

### IconButton
**File:** `IconButton.tsx` | **Foundation:** Wraps `Button`

Square button for icon-only actions. Inherits all Button behavior.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `variant` | `ghost` \| `soft` \| `surface` \| `outline` | `ghost` | Narrower set than Button |
| `size` | `1` \| `2` \| `3` | `2` | |
| `aria-label` | string | **required** | Must always be provided — icon-only buttons need text for screen readers |

**Use for:** Toolbar actions, close buttons, inline actions alongside text.
**Don't use for:** Primary page CTAs (use `Button` with text).

### FAB (Floating Action Button)
**File:** `FAB.tsx` | **Foundation:** Native `<button>`

Fixed-position button for the single most important action on a page.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `icon` | ReactNode | **required** | The icon to display |
| `aria-label` | string | **required** | Accessible name |
| `position` | `bottom-right` \| `bottom-left` \| `top-right` \| `top-left` | `bottom-right` | |
| `size` | `sm` \| `md` \| `lg` | `md` | |
| `tooltip` | string | — | Renders `sr-only` text + `title` attribute |

**Use for:** One per page max. Quick-add actions.
**Don't use for:** Secondary actions, anything that could be in a toolbar.

### DialogActionBar
**File:** `DialogActionBar.tsx` | **Foundation:** Radix `Flex` + `Button`

Horizontal row of action buttons for modal footers. Handles loading and disabled states per-button.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `actions` | `DialogAction[]` | **required** | Array of `{ label, onClick, variant?, color?, disabled?, loading?, type? }` |
| `align` | `start` \| `center` \| `end` | `end` | Right-aligned by default |
| `gap` | `1`-`5` | `3` | Spacing between buttons |

**Use for:** Modal/dialog footers with Save/Cancel or similar paired actions.
**Don't use for:** Inline form buttons (just use `Button` directly).

---

## Form Inputs

### Input
**File:** `Input.tsx` | **Foundation:** Radix Themes `TextField`

Single-line text input. Wraps Radix TextField with our focus system.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `error` | boolean | `false` | Turns border red |
| `color` | Radix color | — | Overridden to `red` when `error` is true |
| All Radix TextField.Root props | — | — | `placeholder`, `size`, `variant`, etc. |

**Use for:** All single-line text entry. Pair with `<Label>` above and `<ErrorMessage>` below.
**Don't use for:** Multi-line text (use `Textarea`), selections (use `Select`).

### Textarea
**File:** `Textarea.tsx` | **Foundation:** Radix Themes `TextArea`

Multi-line text input. Wraps Radix TextArea with our focus system.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| All Radix TextArea props | — | — | `placeholder`, `size`, `resize`, etc. |

**Use for:** Descriptions, notes, multi-line content.
**Don't use for:** Single-line inputs (use `Input`).

### Select
**File:** `Select.tsx` | **Foundation:** Radix Select primitive

Dropdown selection. Fully keyboard-navigable.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `value` / `defaultValue` | string | — | Controlled or uncontrolled |
| `onValueChange` | `(value: string) => void` | — | |
| `placeholder` | string | — | Shown when no value selected |
| `size` | `1` \| `2` \| `3` | `2` | |
| `variant` | `classic` \| `surface` \| `soft` \| `ghost` | `surface` | |

Children: `<SelectItem value="...">Label</SelectItem>`, `<SelectGroup>`, `<SelectLabel>`, `<SelectSeparator>`.

**Use for:** Picking one option from a predefined list.
**Don't use for:** Multi-select (not supported), free-text entry (use `Input`).

### Checkbox
**File:** `Checkbox.tsx` | **Foundation:** Radix Checkbox primitive

Single checkbox with check icon.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `checked` | boolean \| `'indeterminate'` | — | Radix checked state |
| `onCheckedChange` | function | — | |
| `srLabel` | string | `'Checkbox'` | Screen reader label. Always provide a meaningful one. |
| `disabled` | boolean | `false` | |

**Use for:** Boolean toggles, task completion, multi-select.
**Don't use for:** On/off settings (use `ToggleField`).

### ToggleField
**File:** `ToggleField.tsx` | **Foundation:** Radix Switch

Switch toggle with label and optional description. A complete form field.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `id` | string | **required** | Links label to switch via `htmlFor` |
| `label` | string | **required** | |
| `checked` | boolean | — | |
| `onChange` | `(checked: boolean) => void` | — | |
| `description` | string | — | Secondary text below label |

**Use for:** Settings, preferences, feature toggles.
**Don't use for:** One-off checkboxes in forms (use `Checkbox` + `Label`).

### Label
**File:** `Label.tsx` | **Foundation:** Native `<label>`

Form field label. Consistent sizing and color.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| All native label props | — | — | `htmlFor` to link to input |

Renders as `text-sm font-medium text-text-secondary` with `mb-1`.

**Use for:** Every form field needs a label. Always pair with an input.

---

## Layout & Containers

### Card
**File:** `Card.tsx` | **Foundation:** Native `<div>`

Simple content container with padding, border radius, and shadow.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `className` | string | — | Extend with additional styles |
| All native div props | — | — | |

Renders as `bg-ui-element-bg rounded-lg shadow p-6`.

**Use for:** Grouping related content — task cards, settings sections, info panels.
**Don't use for:** Modal content (use `Modal` or `GenericModal`), page-level layout.

### Modal
**File:** `Modal.tsx` | **Foundation:** Radix Dialog primitive

Simple overlay dialog. Centered, with close button.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `open` | boolean | — | Controlled open state |
| `onOpenChange` | `(open: boolean) => void` | — | |
| `title` | string | — | Dialog title (rendered as `Dialog.Title`) |
| `description` | string | — | Dialog description |
| `children` | ReactNode | — | Dialog body |

Fixed at `max-w-md`. Overlay is `bg-black/40`. Close button in top-right.

**Use for:** Simple dialogs with a title and action — confirmations, short forms.
**Don't use for:** Complex forms with loading/error states (use `GenericModal`).

### GenericModal
**File:** `GenericModal.tsx` | **Foundation:** Radix Dialog primitive

Enhanced modal with loading, error, and dirty state management. Registers with `useTaskViewStore` for keyboard shortcut suppression.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `isOpen` / `onOpenChange` | — | — | Same as Modal |
| `title` / `description` | — | — | Same as Modal |
| `size` | `sm` \| `md` \| `lg` \| `xl` | `md` | Controls max-width |
| `isDirty` | boolean | `false` | Shows confirm dialog on close if true |
| `modalId` | string | `'generic-modal'` | For keyboard shortcut management |
| `isLoading` | boolean | `false` | Shows spinner in body (will be skeleton post-SPEC-030) |
| `error` | string \| Error \| null | `null` | Shows error in body |
| `loadingMessage` | string | `'Loading...'` | Text next to spinner |

**Use for:** Any dialog with async content — task editing, settings, detail views.
**Don't use for:** Simple confirmations (use `ConfirmDialog` post-SPEC-030).
**Known issue:** Uses `window.confirm()` for dirty state. Will be replaced with `ConfirmDialog`.

---

## Feedback & Status

### ErrorMessage
**File:** `ErrorMessage.tsx` | **Foundation:** Native `<p>`

Inline error text. Renders nothing when children is falsy.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `children` | ReactNode | — | Error text. Renders `null` if falsy. |
| `id` | string | — | For `aria-describedby` linking to input |

Renders as `role="alert"`, `text-sm text-text-destructive mt-1`.

**Use for:** Form field validation errors, inline error messages.
**Don't use for:** Page-level errors (use a larger error display), background errors (use toast).

### Toast
**File:** `toast.tsx` | **Foundation:** Radix Toast primitive

Global notification system. Imperative API — call from anywhere.

**API:**
```typescript
toast.success('Task created')
toast.success('Task created', 'It will appear in your list.')
toast.error('Couldn\'t save task', 'Check your connection.')
toast.default('Settings updated')
```

| Variant | Styling | Use When |
|---------|---------|----------|
| `success` | Green border | Action succeeded |
| `destructive` | Red border | Action failed |
| `default` | Accent border | Neutral notification |

Auto-dismiss: 2000ms. Max 5 visible. Swipe to dismiss.

**Use for:** Feedback on completed actions (save, delete, connect).
**Don't use for:** Inline errors (use `ErrorMessage`), persistent messages, empty states.

### Spinner
**File:** `Spinner.tsx` | **Foundation:** SVG

Animated loading indicator.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `size` | number | `24` | Width/height in px |
| `className` | string | — | Additional classes |

**Post-SPEC-030:** Will have `role="status"` and `aria-label` prop.

**Use for:** Inline action feedback only — inside buttons, next to "Saving..." text.
**Don't use for:** Data loading (use `Skeleton` post-SPEC-030). Layout-level loading.

### Badge
**File:** `Badge.tsx` | **Foundation:** Radix Themes `Badge`

Small status indicator label.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `variant` | `solid` \| `soft` \| `surface` \| `outline` | `soft` | |
| `size` | `1` \| `2` \| `3` | `2` | |
| `color` | Radix color | — | Full Radix color palette |

**Use for:** Status labels, category tags, counts.
**Don't use for:** Task-specific statuses (use `TaskStatusBadge`).

### TaskStatusBadge
**File:** `TaskStatusBadge.tsx` | **Foundation:** Native `<span>`

Task-specific status pill with hardcoded statuses and semantic colors.

| Status | Color | Label |
|--------|-------|-------|
| `upcoming` | info (blue) | "Upcoming" |
| `in-progress` | warning (amber) | "In Progress" |
| `completed` | success (green) | "Completed" |
| `skipped` | neutral (gray) | "Skipped" |
| `due` | destructive (red) | "Due" |

**Use for:** Task status display in lists and detail views.
**Don't use for:** Generic status indicators (use `Badge`).

### CoachCard
**File:** `CoachCard.tsx` | **Foundation:** `Card` + `Button`

Suggestion card from the AI coach. Shows a recommendation with accept/dismiss actions.

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `title` | string | `'AI Coach Suggestion'` | |
| `suggestion` | ReactNode | **required** | The suggestion content |
| `onAccept` / `onDismiss` | function | — | Optional action handlers |
| `acceptLabel` / `dismissLabel` | string | `'Accept'` / `'Dismiss'` | |

**Use for:** Agent-generated suggestions that need user response.
**Don't use for:** Static informational content (use `Card`).

---

## Overlays & Tooltips

### Tooltip
**File:** `tooltip.tsx` | **Foundation:** Radix Tooltip primitive

Hover/focus tooltip. Appears after a short delay.

Exported parts: `TooltipProvider`, `Tooltip`, `TooltipTrigger`, `TooltipContent`.

```tsx
<Tooltip>
  <TooltipTrigger asChild>
    <IconButton aria-label="Settings">...</IconButton>
  </TooltipTrigger>
  <TooltipContent>Settings</TooltipContent>
</Tooltip>
```

**Use for:** Explaining icon-only buttons, showing full text on truncated content.
**Don't use for:** Essential information (tooltips aren't keyboard-discoverable on mobile). Error messages. Instructions.

---

## Primitives Coming in SPEC-030

These components don't exist yet. They will be created in FU-1.

### EmptyState (planned)
Centered message for empty collections. Icon + heading + description + optional CTA.

### Skeleton (planned)
Animated placeholder for loading data. Variants: `text`, `card`, `list`. Shimmer animation (CSS).

### ConfirmDialog (planned)
Confirmation dialog for destructive actions. Wraps Modal with destructive/warning styling.

---

## Chat Components

Located in `components/ui/chat/`. These are specialized for the chat timeline.

### MessageBubble
**File:** `chat/MessageBubble.tsx`

Single message in the chat thread. Renders differently based on sender type (user/ai/system).

### MessageInput
**File:** `chat/MessageInput.tsx`

Text input + send button for composing chat messages. Has `aria-label` on input and button.

### MessageHeader
**File:** `chat/MessageHeader.tsx`

Chat panel header with title and connection status indicator (green/yellow/gray dot).

### NotificationInlineMessage
**File:** `chat/NotificationInlineMessage.tsx`

Inline notification rendered within the chat timeline. Agent observations, status updates, and informational messages.

| Prop | Type | Notes |
|------|------|-------|
| `message` | `ChatMessage` | Must have `sender: 'notification'` |

**Visual:** Left border colored by category (`heartbeat` = brand, `approval_needed` = warning, `agent_result` = info, `error` = destructive, `info` = neutral). Title + body + relative timestamp.

**Feedback:** Thumbs up/down buttons from SPEC-024. Selected state highlights chosen thumb, dims the other.

**Behavior:** Auto-marks notification as read on mount. Has `role="status"` + `aria-label`.

**Use for:** Any non-approval notification the agent sends to the user.
**Don't use for:** Approval requests (use `ApprovalInlineMessage`), regular chat messages.

### ApprovalInlineMessage
**File:** `chat/ApprovalInlineMessage.tsx`

Inline approval request in the chat timeline. This is Clarity's core trust mechanism — the user approves agent actions from within the conversation.

| Prop | Type | Notes |
|------|------|-------|
| `message` | `ChatMessage` | Must have `sender: 'approval'` with `action_id`, `action_tool_name`, `action_tool_args` |

**Lifecycle (one card, full action lifecycle):**
- **Pending:** Warning border. Tool name + expanded args + Approve/Reject buttons.
- **Approved (executing):** Success border. Heading: "✓ {tool} — Approved". Args collapsed. Result: "Running..."
- **Approved (done):** Success border. Result: "Executed successfully." or summary.
- **Approved (failed):** Destructive border. Result: "Failed: {error}".
- **Rejected:** Neutral border. Heading: "✗ {tool} — Rejected". Args collapsed.
- **Expired:** Neutral border. Heading: "{tool} — Expired". Args collapsed.

**Tool arguments:** Monospace `<pre>` block. Expanded when pending, collapsed after resolution. Toggle: "Show arguments" / "Hide arguments".

**Result folding:** The follow-up `silent` notification (created by backend on execution) is suppressed from the web timeline when it shares a `pending_action_id` with this card. The result is shown inside the card itself. On Telegram, the follow-up sends as a separate message.

**Behavior:** Optimistic state update on approve/reject. Calls `POST /api/actions/{action_id}/approve` or `/reject`. Auto-marks notification as read on mount. Has `role="alert"` + `aria-label`.

**Use for:** Any agent tool that requires user consent before execution.
**Don't use for:** Informational notifications (use `NotificationInlineMessage`), agent messages.

See `docs/ux/interaction-patterns.md` section 7 for the complete approval flow design.

---

## Not Exported (Internal / Demo)

These files exist in `components/ui/` but are not part of the public component API:

| File | Status | Notes |
|------|--------|-------|
| `DesignDemo.tsx` | Demo | Development/testing only |
| `LayoutMockups.tsx` | Demo | Layout exploration mockups |
| `ThemeToggle.tsx` | Internal | Used only in TopBar |
| `TaskCard.tsx` | Exported but specialized | Tightly coupled to task domain — not a reusable primitive |

---

## Quick Reference: Which Component?

| I need to... | Use |
|-------------|-----|
| Show a clickable action | `Button` (with text) or `IconButton` (icon only) |
| Collect text input | `Input` (single line) or `Textarea` (multi-line) |
| Pick from a list | `Select` with `SelectItem` children |
| Toggle on/off | `ToggleField` (with label) or `Checkbox` (standalone) |
| Show grouped content | `Card` |
| Show a dialog | `Modal` (simple) or `GenericModal` (with loading/error) |
| Show an error | `ErrorMessage` (inline) or `toast.error()` (background) |
| Show success | `toast.success()` |
| Show a status label | `Badge` (generic) or `TaskStatusBadge` (tasks) |
| Explain an icon | `Tooltip` around the icon button |
| Quick-add action | `FAB` (one per page max) |
| Show modal footer buttons | `DialogActionBar` |
| Show an AI suggestion | `CoachCard` |
