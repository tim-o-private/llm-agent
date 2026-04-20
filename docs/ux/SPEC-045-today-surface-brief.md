# SPEC-045 — Today Surface Visual + Interaction Brief

> **Status:** Draft for Tim's approval (review gate before Playwright contract freeze)
> **Spec:** [`docs/sdlc/specs/SPEC-045-today-surface.md`](../sdlc/specs/SPEC-045-today-surface.md)
> **Directive:** [`docs/sdlc/visions/clarity-as-vault-functional.md`](../sdlc/visions/clarity-as-vault-functional.md) (D1–D5, S1, S6, S7)
> **Author:** UX (Claude) · 2026-04-20
> **Precedent:** None — Today has no wireframe. Wireframes (`ClarityWireframes _standalone_.html`) cover S2–S5 only.

## 0. Design posture

Today is the daily front door. It needs to feel like opening a notebook on a desk, not a dashboard. The implications cascade:

- **Density is the enemy.** Seven sections on one page will tempt a grid. Resist. A single column, reading-width, with breathing room between sections is closer to the "calm and minimal, low friction" ADHD-target posture from `interaction-patterns.md`.
- **Signal that this is a file.** D4 typography (JetBrains Mono on filenames/paths/timestamps) does a lot of work here. The "View source" toggle (AC-11) is the honesty moment — toggling to raw markdown must feel like a second-nature affordance, not a hidden debug toy.
- **Approvals are the one sharp edge.** Six card shapes with distinct button semantics sit inside an otherwise quiet page. They should be visually louder than the surrounding sections but still subordinate to the page frame.

No new tokens, no new primitives. `EmptyState`, `Skeleton`, `ConfirmDialog` from SPEC-030 FU-1 are assumed available; everything else is already in `components/ui/`.

---

## 1. Page frame

Today lives inside the existing `AppShell` — `SideNav` on the left, `TopBar` on top, `ChatPanel` slide-in on the right (state in `useChatStore`). No layout change to the shell. The Today page occupies the main content area.

```
┌─────────┬──────────────────────────────────────────────────────┬────────┐
│ SideNav │  TopBar:  Clarity · <date> ············· [3] 🌓 👤   │  Chat  │
│         ├──────────────────────────────────────────────────────┤  Panel │
│  Home   │  <main aria-label="Today">                           │ (slide │
│  Vault  │                                                      │  -in,  │
│  Work   │    ┌────────────────────────────────────────────┐    │  right)│
│  flows  │    │  Header: Monday, April 20  · [Regenerate]  │    │        │
│  ...    │    │  "Light day — 2 drafts need a glance."     │    │        │
│         │    └────────────────────────────────────────────┘    │        │
│         │                                                      │        │
│         │    Your day    [§]                                   │        │
│         │    ...                                               │        │
│         │                                                      │        │
│         │  </main>                                             │        │
└─────────┴──────────────────────────────────────────────────────┴────────┘
```

**Content column:** centered in the main area, `max-w-3xl` (~768px) for comfortable prose width. Gutters scale with viewport; on <md breakpoints the column is full-width with `px-4`.

**Vertical rhythm:** each `<section>` gets `py-8` top/bottom; heading `mb-4`; body uses native component spacing. No card backgrounds — sections are separated by whitespace and a single muted `h2`. Only the approval cards inside the Approvals section get card chrome.

**"View source" toggle (AC-11):** a small `IconButton` in the top-right of the content column, paired with the section anchor set `[§]` below. Toggling swaps the rendered seven sections for a monospace block (JetBrains Mono, `bg-surface-1`, `p-6`, `rounded-md`) with the raw `today.md` text. The toggle control remains visible in source mode so the user can always get back.

**Regenerate Today (AC-17):** lives in the Header section, not globally — it belongs to the content, not the chrome. Rendered as `Button variant="soft"` with a refresh icon. When a regeneration run is in-flight (`useRegenerationStatus` returns `running`), swap to `"Regenerating…"` + inline `Spinner`, set `aria-busy="true"`. Latency up to 30s is acknowledged in copy via a secondary toast on click: `"Regenerating — Today will refresh within ~30s."`

### ApprovalsBadge placement in TopBar

Insert between the streak block and `ThemeToggle` (the spec already directs this in the Files to Modify table). Visual treatment:

- **Shape:** `Button variant="ghost" size="2"` wrapping a `Badge` count. Whole control is clickable → scrolls the Approvals section into view with `scrollIntoView({ behavior: "smooth", block: "start" })` and sets URL hash `#today-approvals` (keyboard-reachable, shareable).
- **Label:** icon (`BellIcon` from Radix icons) + count. When count = 0, render the icon alone with `opacity-60` and `aria-label="No pending approvals"`; don't hide the control (it's a reassuring "nothing's hiding" signal).
- **Count rendering:** `1`–`9` show the digit; `10+` shows `9+` to prevent TopBar width churn. `color="amber"` when count ≥ 1 (matches `warning` semantic), `color="gray"` at 0.
- **Live updates:** polled at 15s per AC-16; the count is derived from `useApprovalsCount`. Badge uses `aria-live="polite"` on its wrapper so screen readers hear changes without stealing focus.

```
…Streak: N/A   [🔔 3]  🌓  👤          ← aria-label="3 pending approvals"
…Streak: N/A   [🔔]    🌓  👤          ← aria-label="No pending approvals"
```

**Open question:** streak is a stub (`N/A`) today. The badge is the only topbar element that *does* something on Today. I'd recommend hiding the streak stub entirely until it has content, but that's outside scope — leaving it.

---

## 2. Seven sections — order, hierarchy, empty states

Order is fixed by AC-03: **Header → Your day → To do → Notes → Agent → Approvals → Recent.** Each section is a `<section aria-labelledby="today-<name>-heading">` containing an `<h2 id="today-<name>-heading">` and body content. Empty sections do NOT disappear (AC-03). This is load-bearing — the page should feel stable in shape regardless of content.

| # | Section | Primary components | Empty state copy |
|---|---------|--------------------|------------------|
| 1 | Header (`header`, not a section per se — uses `h1`) | `Heading` (Radix) for date, prose for framing, `Button` for Regenerate | "No framing yet — run today's briefing." (AC-04) |
| 2 | Your day (`your-day`) | Plain `<ul>` with `<li>` for items; wikilinks become Radix `Link` | "Nothing on your calendar today." |
| 3 | To do (`to-do`) | `Checkbox` per item + `Label`; list rendered as markdown-native `- [ ]` semantics | "No to-dos — the agent hasn't surfaced anything yet." |
| 4 | Notes (`notes`) | `Input` with submit `IconButton`; below, a `<ul>` of captured notes | "No notes yet — capture one above." |
| 5 | Agent (`agent`) | Four `<h3>` sub-groups (Running / Watching / Recently done / Blocked) each with a `<ul>` of links | "Agent is idle." (per group: `"Nothing running."` / `"Nothing to watch."` / `"Nothing recent."` / `"Nothing blocked."`) |
| 6 | Approvals (`approvals`) | Stack of approval cards, one per row | "Nothing awaiting approval." (AC-09) |
| 7 | Recent (`recent`) | `<ul>` of links; filename in JetBrains Mono, relative time in muted Mono | "No recent activity." (AC-10) |

**Heading style:** `h2` at `text-lg font-medium text-text-secondary`, `tracking-tight`. Intentionally *quieter* than body — the section labels are signposts, not shouted headers. The `h1` (date) is the single bold beat of the page.

**Empty state primitive:** lightweight — do NOT use the SPEC-030 `EmptyState` component for every empty section. That component is centered-full-height and appropriate only when the section is otherwise *the whole page*. For Today sections, empty states are a single muted paragraph (`text-sm text-text-muted italic`). The `<section>` still takes up its normal vertical rhythm so the page frame doesn't jump as content arrives.

**"View source" toggle:** a single `IconButton` with `aria-label="View source"` (toggles to `"View rendered"`) docked top-right of the content column, above the Header section. Icon: `CodeIcon`. When engaged, all seven `<section>`s are replaced by a single `<pre class="font-mono …">` containing the raw file body. No editing in source view for Stage 1 per AC-11 and the S3 deferral.

### Section-by-section notes

**Header.** `h1` carries the date in the user's locale (AC-02). Framing sentence sits immediately below as a `<p class="text-text-secondary">`. Regenerate button is right-aligned on the same row as the date on `md+`, wraps below on mobile. No card chrome.

**Your day.** Each item is a `<li>` with two slots: item text (Inter), and wikilink target (JetBrains Mono, rendered as `Link` with `size="2"`). If an item is timestamped (e.g., "10:00 — Standup"), the time portion is Mono to signal "this is a pulled fact from a file."

**To do.** Markdown task-list rendered semantically: each `<li>` contains a `Checkbox` (`srLabel={item.text}`) followed by the text. Checking the box optimistically toggles + calls `useToggleTodo`; revert on failure. Completed items get `line-through text-text-muted`. No re-ordering in Stage 1 — the file order wins.

**Notes.** The capture pattern is the spiciest interaction on the page. Design:

```
┌─────────────────────────────────────────────────────┐
│  [ Capture a note                              ] ↵  │   ← Input + IconButton (submit)
└─────────────────────────────────────────────────────┘

    · 2026-04-20 09:14  Think about the onboarding copy
    · 2026-04-20 08:47  Reminder: call Meredith re: invoice
```

Input spans full column width. `Enter` submits; `Shift+Enter` inserts newline (via `Textarea` upgrade if we later allow multi-line — Stage 1 is single-line). Submit clears the input optimistically; on failure, restore input text and `toast.error("Couldn't save note. Try again.")`. Existing notes render below with timestamp in Mono + muted, text in Inter.

**Agent.** Four sub-groupings, each an `<h3>` + `<ul>`. Use a single column, not a 2×2 grid — reading flow beats symmetry here. Stage 1 items link to placeholder `/vault/…` / `/workflows/…` routes (AC-08); those routes 404 today, that's fine.

**Approvals.** The section the page revolves around. Details in §3.

**Recent.** Filename in Mono (`text-sm`), relative time in Mono muted (`text-xs text-text-muted`). Up to 10 rows (AC-10). Visual restraint — this is the closing note of the page, not its centerpiece.

---

## 3. Six approval card shapes

Every card has the same outer container:

```
┌─ <Card className="border-l-4 border-l-<accent>"> ─────────────────────────┐
│  ⓘ  <card_type_label>                                                     │
│  <title>                                                                  │
│  ─────                                                                    │
│  <body: type-specific fields>                                             │
│  ─────                                                                    │
│  [primary]  [secondary]  [Reject]                                         │
└───────────────────────────────────────────────────────────────────────────┘
```

- Outer: `Card` primitive, `p-5`, rounded, with a 4px left border colored per type (see below). This borrows from `ApprovalInlineMessage`'s idiom in chat (§7 of interaction-patterns) so the two surfaces rhyme.
- Type label: a `Badge variant="soft"` at the top, color-matched to the left border. Label is the human form of the type (e.g., "Email draft", "Calendar hold").
- Title: `h3 text-base font-medium`. This is the AC-12 accessible name source (`aria-label="<Type> approval: <title>"` on the card `role="region"`).
- Body: type-specific — see per-shape below.
- Action row: right-aligned, `Flex gap="2"`. Primary action first (tempting but we accept it — ADHD users benefit from obvious defaults). Reject always last, `variant="soft" color="gray"` — never red, because rejecting is a non-destructive clarifying action, not a delete.

**Accent colors (left border + type badge):**

| Shape | Accent | Rationale |
|-------|--------|-----------|
| `email_draft` | `blue` (info) | outbound comms — neutral |
| `calendar_hold` | `violet` | time commitment, distinct from comms |
| `outreach` | `blue` (info) | same family as email_draft |
| `workflow_proposal` | `amber` (warning-ish) | structural change to the system |
| `config_change` | `amber` | same family as workflow_proposal |
| `file_operation` | `red` (destructive) | moves/deletes are the one truly destructive shape |

Only `file_operation` uses red, and even there: the color is on the left border and type badge; the Approve button is a solid `color="red"` (true destructive styling per interaction-patterns §4), and we *do* want the ConfirmDialog gate from §4 for `delete` operations specifically. `move`/`rename` get approved inline without a confirm.

### Per-shape body + actions

Button styling legend: **P** = `variant="solid"` (primary), **S** = `variant="soft"` (secondary), **R** = `variant="soft" color="gray"` (reject).

---

**`email_draft`** — border: blue, badge: "Email draft"

```
To:       bob@example.com, alice@example.com
Subject:  Re: Q2 invoicing
──────────
> Body preview (first ~6 lines, Inter, text-sm)
> Collapsed after ~6 lines with "Show full draft" toggle
──────────
[ Send ]P   [ Edit ]S   [ Reject ]R
```

Fields rendered: `to[]` (Mono, comma-joined, truncated with tooltip beyond 3 addresses), `subject` (Inter, medium weight), `body` preview.

Edit (AC-15) opens inline: subject becomes an `Input`, body becomes a `Textarea` (`rows=8`), a `[Save]P [Cancel]S` row replaces the normal action row. Save calls `useEditCard`; card stays `pending`. Escape cancels.

Reject inline-editor: on `Reject` click, reveal a small `Input` `placeholder="Optional reason"` + `[ Confirm reject ]` — same pattern as below. Submitting with empty reason is allowed.

---

**`calendar_hold`** — border: violet, badge: "Calendar hold"

```
Title:     Deep work — client proposal
When:      Tue Apr 22 · 09:00–11:00  (2h)       ← Mono
──────────
source_ref: <Gmail thread link or inbox signal>
──────────
[ Confirm ]P   [ Edit ]S   [ Reject ]R
```

Start/end times in Mono. Duration computed client-side in parens. Edit opens title as `Input` and start/end as `<input type="datetime-local">` pair.

---

**`outreach`** — border: blue, badge: "Outreach"

```
To:        @meredith on telegram                ← channel chip + recipient
Channel:   telegram                             ← small muted line
──────────
> Proposed message (first ~5 lines, Inter)
──────────
Rationale:  <one-line prose, text-text-secondary italic>
──────────
[ Send ]P   [ Edit ]S   [ Reject ]R
```

`channel` (`email|telegram|other`) renders as a small `Badge variant="outline"` beside the recipient. Edit opens message as `Textarea`.

---

**`workflow_proposal`** — border: amber, badge: "Workflow proposal"

```
Filename:    _workflows/weekly-invoice-chase.flow.md    ← Mono, text-sm
──────────
Pattern:     <one-line rationale of what the agent noticed>
──────────
▸ Preview                                                ← expandable
  <.flow.md body in a monospace block, collapsed by default>
──────────
[ Accept ]P   [ Edit ]S   [ Reject ]R
```

Accept is the primary but **does not write the file in Stage 1** per the No Outbound Effects contract — the spec is explicit. The card disappears from the lane and `activity_log` records the approval; a future stage wires actual file writeback. Edit (AC-15) opens filename + body as `Input` + `Textarea (rows=12, font-mono)`.

---

**`config_change`** — border: amber, badge: "Config change"

```
File:       agents/today-composer.md                     ← Mono
Summary:    Add "respect user's framing tone" to system prompt
──────────
▸ Diff                                                   ← expandable, default collapsed
  @@ -12,3 +12,5 @@
  - You produce a short summary.
  + You produce a short summary.
  + Match the user's preferred framing tone (terse vs. warm).
──────────
[ Approve ]P   [ Reject ]R
```

No Edit on this shape — editing a proposed diff is its own UX problem, and the spec's `AC-12` actions for `config_change` are Approve + Reject only. Diff rendered in monospace, `+ ` green text, `- ` red text, unchanged muted. Collapsed by default because many diffs will be one line and many will be twenty.

---

**`file_operation`** — border: red, badge: "File operation" (destructive visual family)

```
Operation:   delete                                      ← Badge color="red" variant="solid"
Source:      _archive/2023-notes.md                      ← Mono
Target:      —                                           ← only present for move/rename
──────────
[ Approve ]P·destructive   [ Reject ]R
```

Approve button is `variant="solid" color="red"` for `delete` operations; `variant="solid"` default for `move`/`rename`. For `delete`, clicking Approve opens a `ConfirmDialog` (interaction-patterns §4 — "delete" is the model destructive action). Title: `"Delete this file?"` Description: `"This will remove {source}. Stage 1 records the approval; the file isn't actually deleted yet."` Confirm label: `"Approve delete"`.

This is intentionally a bit verbose — the file-operation shape ships in Stage 1 but executes nothing, which could encourage sloppy approvals. Keep the friction so users build the right habit now.

---

### Reject-with-reason pattern (shared)

When Reject is clicked on any shape, the button row is replaced by:

```
[ Input placeholder="Optional reason for rejection" ]  [ Confirm reject ]  [ Cancel ]
```

`Confirm reject` calls `useRejectCard` with the reason (empty string allowed). `Cancel` restores the normal action row. This reuses existing `Input` + `Button` primitives; no new component needed.

---

## 4. States matrix

Per-section behavior for the four interaction states. References interaction-patterns.md rather than re-inventing:

| Section | Empty | Loading | Error | Interacting |
|---------|-------|---------|-------|-------------|
| Header | "No framing yet — run today's briefing." | `Skeleton variant="text"` for date + framing line | "Couldn't load Today. Try refreshing." + `[Refresh]` button | Regenerate button → `Spinner` + `"Regenerating…"`, `aria-busy="true"` |
| Your day | "Nothing on your calendar today." | `Skeleton variant="list"` (3 rows) | — (inherits page-level error) | N/A (read-only) |
| To do | "No to-dos — the agent hasn't surfaced anything yet." | `Skeleton variant="list"` (3 rows) | — | Checkbox is optimistic (§3 loading rules #4); revert + `toast.error("Couldn't update. Try again.")` on failure |
| Notes | "No notes yet — capture one above." | `Skeleton variant="list"` (2 rows) for existing notes; input always interactive | Input stays; `ErrorMessage` below input on save failure + `toast.error` | Input shows submit `Spinner` on pending; clear on success |
| Agent | Four sub-group emptys (see §2) | `Skeleton variant="list"` per sub-group (1 row each) | — | N/A (read-only, links) |
| Approvals | "Nothing awaiting approval." | `Skeleton variant="card"` (2 cards) | Per-card error via `toast.error` on approve/reject failure; card stays pending | Approve/Reject optimistic per §7 of interaction-patterns; card fades out over ~200ms on success (respecting `prefers-reduced-motion`) |
| Recent | "No recent activity." | `Skeleton variant="list"` (4 rows) | — | N/A (read-only) |

**Page-level error:** if `useToday` fails entirely, the main content area (not the shell) renders a centered `ErrorMessage` + `[Refresh]` button. The seven sections are suppressed. This matches interaction-patterns §1 row "Page/section data failed to load."

**Loading initial render:** skeleton all seven sections simultaneously — avoids the "sections pop in one by one" feel. `aria-busy="true"` on `<main>` during initial load.

**Reduced motion:** all transitions (card fade-out on approve, skeleton shimmer) respect `prefers-reduced-motion: reduce` per accessibility-checklist. Skeletons become static gray; card approvals snap rather than fade.

---

## 5. Typography + tokens

Per D4. No new tokens. Existing Radix token set is complete for this page.

| Element | Family | Size | Weight | Color |
|---------|--------|------|--------|-------|
| H1 (date) | Inter | `text-2xl` | 600 | `text-text-primary` |
| Framing sentence | Inter | `text-base` | 400 | `text-text-secondary` |
| H2 (section) | Inter | `text-lg` | 500 | `text-text-secondary` (muted — signpost, not shout) |
| H3 (agent sub-groups, approval-card title) | Inter | `text-base` | 500 | `text-text-primary` |
| Body prose | Inter | `text-sm` / `text-base` | 400 | `text-text-primary` |
| Note / todo text | Inter | `text-sm` | 400 | `text-text-primary` (or muted + strikethrough when done) |
| Empty state copy | Inter | `text-sm` italic | 400 | `text-text-muted` |
| Filenames / paths | JetBrains Mono | `text-sm` | 400 | `text-text-primary` (link blue when clickable) |
| Timestamps (relative) | JetBrains Mono | `text-xs` | 400 | `text-text-muted` |
| Timestamps (ISO in notes) | JetBrains Mono | `text-xs` | 400 | `text-text-muted` |
| Diffs (config_change) | JetBrains Mono | `text-xs` | 400 | `+` rows `text-success-strong`, `-` rows `text-destructive-strong`, context `text-text-muted` |
| Source view (AC-11) | JetBrains Mono | `text-sm` | 400 | `text-text-primary` on `bg-surface-1` |
| Card type badge | Inter | `text-xs` | 500 | matches accent via Radix `Badge color=<accent>` |

Font-family is set globally via Tailwind's `font-sans` (Inter) and `font-mono` (JetBrains Mono) keys — already configured in the webApp per my read of existing code. No `@font-face` additions needed.

---

## 6. ARIA landmarks — pre-declaration for Playwright

Playwright selectors target ARIA role/label (spec's testing convention). Freezing these here so the Playwright pass in Task #5 has an unambiguous contract. When `frontend-dev` later implements, these are the selectors that MUST match.

### Page frame

| Element | Selector contract | Spec ref |
|---------|-------------------|----------|
| Main region | `<main aria-label="Today">` | AC-02 |
| Page heading (date) | `<h1>` inside `<main>`, text = locale date string | AC-02 |
| View source toggle | `IconButton` with `aria-label="View source"` (toggles to `"View rendered"`) | AC-11 |
| Source view block | `<pre role="region" aria-label="Today source (markdown)">` | AC-11 |
| Regenerate button | `<button aria-label="Regenerate Today">` (label visible as "Regenerate Today") | AC-17 |
| Approvals badge | `<button aria-label="N pending approvals">` (or `"No pending approvals"` when zero) | AC-16 |

### Sections

Each section: `<section aria-labelledby="today-<slug>-heading">` with `<h2 id="today-<slug>-heading">Label</h2>`. Slugs:

| Slug | Heading | Spec ref |
|------|---------|----------|
| `header` | (no `h2` — this is the area above section 2; uses page `h1`) | AC-04 |
| `your-day` | "Your day" | AC-03, AC-05 |
| `to-do` | "To do" | AC-03, AC-06 |
| `notes` | "Notes" | AC-03, AC-07 |
| `agent` | "Agent" | AC-03, AC-08 |
| `approvals` | "Approvals" | AC-03, AC-09 |
| `recent` | "Recent" | AC-03, AC-10 |

### Interactive elements per section

- **To do (AC-06):** each `<li>` has `<input type="checkbox" aria-label="<item text>">`. Checked state reflects file state.
- **Notes (AC-07):** input has `aria-label="Capture a note"`; submit is `<button aria-label="Save note">`. Existing notes are a `<ul aria-label="Captured notes">`.
- **Agent (AC-08):** each sub-group is `<div role="group" aria-labelledby="today-agent-<status>-heading">` with `<h3 id="today-agent-<status>-heading">`. Statuses: `running`, `watching`, `recent`, `blocked`.
- **Approvals (AC-12):** each card is `<div role="region" aria-label="<Type label> approval: <title>">`. Action buttons: `aria-label="<Primary action>"` (e.g., `"Send"`, `"Confirm"`, `"Accept"`, `"Approve"`), `aria-label="Edit"`, `aria-label="Reject"`.
- **Recent (AC-10):** `<ul aria-label="Recently touched files">` with each `<li>` containing a `<a>` (filename) + `<time>` element.

### Dynamic regions

- TopBar badge count: wrapper `aria-live="polite"` so count changes are announced on the 15s poll.
- Approvals section: `aria-live="polite"` on the container so newly-inserted cards are announced but don't steal focus.
- Toast region already handled globally.

---

## 7. Open questions for Tim

These are the design calls I want your sign-off on before freezing Playwright. My recommendation is listed with each.

### OQ-1. Reject button styling — gray soft vs. destructive red

Interaction-patterns §4 reserves red for "cannot be undone" actions. Rejecting an approval is reversible (the agent can re-propose), so red would be miscalibrated. I've specified **gray soft** for all Reject buttons across all six shapes.

**Recommendation:** accept gray-soft Reject. (Alternative would be to use red for Reject on the two destructive-family shapes, `config_change` and `file_operation`, but I think that over-signals — the destructiveness lives in Approve for those, not Reject.)

### OQ-2. `file_operation` delete — inline approve vs. ConfirmDialog gate

The spec allows Stage 1 to approve a delete inline (since nothing actually deletes). I've specified an extra `ConfirmDialog` for `delete` operations only, to train the habit before Stage 3 wires real execution.

**Recommendation:** keep the ConfirmDialog. The friction cost is ~1 click; the habit cost of approving real deletes without confirmation later is much higher.

### OQ-3. Inline note capture — single-line `Input` vs. multi-line `Textarea`

The spec says "an input with `aria-label="Capture a note"`" — ambiguous on single vs. multi-line. Notes in practice will range from "call Meredith" (single-line) to half-paragraph thoughts.

**Recommendation:** start with a **single-line `Input`** that grows to a `Textarea` on focus-with-content-above-X-chars (or on Shift+Enter). Keeps the default state quiet; upgrades on demand. Stage 2 could introduce real rich capture. If you want to punt complexity, single-line only is fine for Stage 1.

### OQ-4. Approvals section card chrome — `Card` primitive vs. bare `<article>` with border

I've specified the existing `Card` primitive (with left accent border). The alternative is a minimal `<article>` with just a left border, no shadow, no background fill — closer to the "single column reading document" posture of the rest of the page. `Card` is heavier visually and makes the lane pop more.

**Recommendation:** `Card` primitive. Approvals are the one place Today *should* pop — they're the section users must drain. Use visual weight where attention is warranted.

### OQ-5. "View source" toggle — sticky vs. inline

If users toggle to source to check something mid-page, scrolling back to find the toggle is annoying. The toggle could be sticky (fixed to top-right of the content column on scroll).

**Recommendation:** **non-sticky** for Stage 1. Keep the page frame minimal. If this becomes a real pain point in UAT, promote to sticky in a follow-up. (Sticky elements are a common source of a11y zoom-safety issues and I don't want to land one speculatively.)

### OQ-6. TopBar Approvals badge when count = 0 — show or hide?

The spec says "topbar shows a single live badge `Approvals` with aria-label='<N> pending approvals'." When N=0 the badge still exists to confirm "nothing's hiding." That's the spec; I've implemented it.

**Recommendation:** keep it always-visible at reduced opacity. If you'd rather hide it entirely at 0 for a cleaner bar, I'll adjust — but the page is calmer than the chrome, and a tiny muted bell is not noisy.

---

## 8. Riskiest design calls (for your awareness)

If any of these turn out wrong, Playwright tests written against them will need rewriting. Flagging explicitly:

1. **Card accent color palette (§3).** I've mapped six shapes to four colors. If you want all six visually distinct, we'd need two more. I think four is correct — the pairs (email_draft / outreach both outbound-comms; workflow_proposal / config_change both system-structure) are semantically linked and should share visual family.

2. **Reject-with-reason inline vs. modal.** I've specified inline (input replaces action row). Alternative is a small modal. Inline is less ceremonious, which is right for a "reversible clarifying action." If you think rejection reasons will commonly be a paragraph, modal would be more appropriate.

3. **Single column vs. two-column layout.** I've specified a single centered column at `max-w-3xl`. On wide monitors this will feel narrow. Two columns (e.g., Header + Approvals left, other sections right) would use horizontal space better but break reading flow and confuse the "Today is a rendered markdown file" metaphor. Single column is my recommendation but worth flagging.

4. **Approvals section placement — 6th vs. 1st.** The spec fixes order; this is locked. But worth noting: putting Approvals 6th (below Notes and Agent) de-prioritizes them on the page. The TopBar badge exists precisely so approvals remain visible from other surfaces, and the "drain the lane" behavior relies on the user actually scrolling to it. If it turns out users miss approvals, we move them up in a follow-up spec — don't break the spec's AC-03 order here.

---

## 9. What happens next

On your approval (or revision), this brief becomes the source of truth for:

1. **Playwright ARIA contract** — Task #5 will translate §6 into `tests/uat/playwright/test_spec_045_today_surface.py`, one test per user-visible AC. No UI is implemented until those tests exist and are red.
2. **Frontend implementation (FU-3)** — `frontend-dev` builds against the Playwright tests. Any new visual decision that isn't in this brief is out-of-scope and needs a separate approval.

No implementation until approval. No Playwright until approval.
