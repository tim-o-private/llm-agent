# Clarity as Vault — Functional Description

**Status:** Functional companion to [`clarity-as-vault.md`](./clarity-as-vault.md). Describes what each UI surface *does* — not how it looks. Intended as the directive for the design pass.

**Authors:** Tim + Claude (2026-04-17)

**Related:** [vision](./clarity-as-vault.md) · [architecture](./clarity-as-vault-architecture.md) · Claude Design wireframes (scenes referenced inline)

---

## Framing decisions (before surfaces)

These resolve open questions from the wireframe pass before we describe surfaces.

### D1. Today is a rendered markdown file inside the vault

Today is not a bespoke screen. It is `vault/today.md` (or equivalent) rendered with a specialized view. The view styles known sections (header, your-day, to-do, notes, agent, approvals, recent) but the underlying content is markdown the user can open as a file. Editing Today through the rich view round-trips to markdown. Opening it through the file browser shows the raw markdown. This keeps "everything is a file" honest and means Today has no separate data model.

**Implication:** the vault browser is not home — Today is. The vault is reachable via sidebar, breadcrumb, and wikilink navigation, but default landing is Today.

### D2. Approvals and agent activity live on Today, not as separate screens

The approval lane is a section *on* Today. The agent activity log is a panel reachable from Today's agent section and from the topbar (persistent "ambient indicator" surfacing a count). No dedicated routes for either. This keeps the daily front door complete.

### D3. Chat is right-rail by default, ⌘K anywhere, never a page

Right-rail slide-in (already built — `ChatPanel`) is default. ⌘K opens a contextual overlay bound to the current surface. Bottom drawer and inline bubble are deferred past Stage 1. Chat is never a standalone route.

### D4. Typography

Inter for headings, body, and UI. JetBrains Mono for filenames, paths, timestamps, frontmatter, and citation metadata — the "this is a file" signal. No hand-drawn or cursive families. Reuses existing Radix + Tailwind token system.

### D5. Wireframe information architecture kept; visual language rebuilt

The wireframes' IA (3-pane vault, right-rail chat, citation rail, markdown-as-workflow, inline suggest cards) is the directive. The sketch aesthetic (dashed borders, jittered strokes, sticky annotations) is not — the design pass builds against existing Clarity visual tokens.

---

## Surfaces

Seven surfaces. Each entry: what it does, what the user can do to it, what the agent can do to it, and where the data lives.

### S1. Today (landing)

The daily dashboard over what the agent is running. Regenerated on schedule (morning), updated by workflow runs throughout the day.

**Sections rendered:**
- **Header** — date, one-line framing of the day ("Light calendar, 2 approvals waiting").
- **Your day** — today's calendar events, decisions flagged, meeting prep notes. Each item links to the source entity doc.
- **To do** — actionable items surfaced by the agent or captured by the user. Not a full task tracker — things the agent believes need doing today.
- **Notes** — input field for capture. New thoughts land here, then get routed to the right place on next agent tick.
- **Agent** — what's running, what it's watching, what it did since last look, what it's blocked on. Each line links deeper (into a workflow run, an entity doc, or the activity log).
- **Approvals** — pending actions awaiting user input. See S6.
- **Recent** — recently touched docs for fast return.

**User can:** edit any section inline (edits round-trip to markdown), add notes, drain approvals, click into anything, open the underlying markdown file, regenerate the whole page on demand.

**Agent can:** regenerate Today on schedule or trigger, update sections in-place as state changes, add items to any section via ambient update.

**Data:** `vault/today.md` (path TBD). Regeneration is a workflow run; the agent writes to the file.

**Replaces:** existing `webApp/src/pages/TodayView.tsx` (task list — unrelated). Existing component kept only as a pattern reference.

---

### S2. Vault browser — *wireframe Scene 1*

Three-pane file browser. Not the home — a drill-down surface reached via sidebar or deep link.

**Panes:**
- **Left: tree** — folder hierarchy including `_workflows/` and `inbox/`. Badges for counts (unread, new). Pinned workflows section below the tree. Search input above.
- **Middle: grid + preview** — file grid for the selected folder (type chip, AI-status chip, metadata). Clicking a file shows a preview pane below the grid. Breadcrumb bar across the top.
- **Right: chat rail** — scoped to current folder. Toggleable via header button or ⌘K.

**User can:** navigate folders, search, open files (opens in S3), create files and folders, pin workflows, drag-reorder (same pattern as existing task drag).

**Agent can:** write files to any folder, edit structure (with approval for destructive ops), surface status chips on files ("summarized," "watching," "draft ready").

**Data:** live filesystem view of the user's vault (Obsidian-compatible markdown files + arbitrary assets). File operations go through the workflow runtime.

---

### S3. File detail — *wireframe Scene 2*

A single file, opened. Document-first; AI context lives in a right rail, never takes over the page.

**Layout:**
- **Collapsed sidebar** — icon-level nav (home, vault, workflows, settings, chat, activity).
- **Center: document body** — CodeMirror 6 source editor with split-view rendered preview (see editing pattern below). Read mode hides source and shows preview only. Breadcrumb and save status at top. History/share/ask chips.
- **Right rail: AI context** — auto-summary, numbered citations (filename + location, click to jump), "linked by" list (backlinks + workflows that reference this file), recent activity timeline, action buttons.
- **Inline suggest cards** — the agent can insert "✦ Clarity suggests" cards directly into the document flow (e.g. "runway-model.csv was updated 4 minutes ago — these numbers are now stale. Re-pull?"). Dismiss/accept inline.

**User can:** read, edit source with live preview, toggle preview on/off, click citations to jump to source, dismiss/accept suggestions, run actions, ask a scoped question via the "ask" chip (opens chat bound to this file).

**Agent can:** maintain the summary section, update citations as content changes, insert suggest cards, add to the activity timeline, write edits to the body with each edit logged.

**Data:** the markdown file. Citations, summaries, and activity are either derived at render time or stored in frontmatter/sidecar — a Stage 1 spec decision.

---

### S4. Workflow editor — *wireframe Scene 3*

Specialized file-detail view for `.flow.md` files under `_workflows/`. Reinforces "workflows are files."

**Layout:**
- **Left: workflow list** — all workflows in `_workflows/`, active triggers summary, "next run" countdown, "+ new workflow" button.
- **Center: markdown editor** — YAML frontmatter (name, triggers, context, tools) followed by prose body (steps, output template). Edit | preview | diagram tabs. Footer with save / dry-run / run-now buttons and validation status.
- **Right: run history** — list of past runs (timestamp, status dot, duration, source count, output path, warnings). Last-output preview at the bottom.

**User can:** create/edit workflows as markdown, trigger dry-runs, run now, view history, jump to a run's output file.

**Agent can:** author new workflows (via orchestration proposal — routed through approval lane), edit existing workflows ("make it run at 6am" in chat → an approval card proposing the edit), attach run entries to history.

**Data:** `.flow.md` files (YAML frontmatter + markdown body) plus run records (stored in DB or as append-only markdown in `_workflows/_runs/` — Stage 1 decision).

---

### S5. Chat — *wireframe Scene 4*

Always available, never a page. Three reachability paths in Stage 1:

**Right rail (default)** — existing `ChatPanel` slide-in. Scoped to the current surface (folder, file, workflow). Shows scope indicator in the header. Supports free conversation, slash commands (`/run`), and chip-suggested follow-ups.

**⌘K palette** — transient overlay. Opens anywhere. First row is always a free-form input. Suggestions below are context-aware (open file X, run workflow Y, summarize today). Dismisses on escape.

**Inline "ask about this" chip** — on file detail and Today sections, a chip opens chat with the selection already scoped.

**Scope binding rules:** chat opened from Today gets no file scope (broad intent). From a folder, scope is that folder. From a file, scope is that file. From a workflow, scope is that workflow. ⌘K inherits whatever surface it was launched from.

**Chat can:** answer questions, redirect the system (edit agent/workflow markdown via approval lane for structural changes, immediately for tone/copy), surface proposals, trigger workflow runs. It cannot take outbound actions in Stage 1 (read-only to the outside world).

**Built on:** existing `ChatPanel` + `@assistant-ui/react`. ⌘K is new (library: `cmdk`).

---

### S6. Approval lane

Not a separate screen. A persistent section on Today, drained by the user. Also surfaced as a count badge in the topbar ("2 pending") so it's visible from any surface.

**Card shapes — one per action type:**
- **Email draft** — to/subject/body preview, "send" / "edit" / "reject" actions, link to the thread-doc the draft belongs to.
- **Calendar hold** — proposed time + title, "confirm" / "edit" / "reject," link to the source that triggered it.
- **Outreach** — proposed message + recipient + rationale, same actions.
- **New workflow proposal** — proposed `.flow.md` content preview, "accept" (lands the file) / "edit" / "reject," rationale explaining what pattern the agent noticed.
- **Agent config change** — diff of the proposed edit to an agent markdown file, approve/reject.
- **File operation** — destructive moves/deletes, rename operations, etc.

**User can:** approve inline (executes immediately, result logged), edit before approving, reject with optional reason, ask about any card via the inline ask chip.

**Agent can:** add cards. Never mutates approved/rejected state. Never retries a rejected proposal without a new signal.

**Behaviors:**
- Cards persist until drained. No auto-dismiss.
- Approval record is unforgeable (DB, not markdown).
- Approved cards disappear from the lane; their execution + result flows into the activity log.

**Stage 1 scope:** render the lane and card shapes; all approved actions execute as read-only log entries (not yet sending, creating, etc.) until Stage 3 wires real outbound execution.

---

### S7. Agent activity log

The pull-model transparency surface. Persistent ambient indicator in the topbar opens the full log. Stage 1 ships the indicator with an approvals count only (`N pending`); the activity count ("watching 3 threads") lands with S7 once the full activity log screen exists to drill into.

**Content:** append-only journal of agent actions. Each entry:
- Timestamp, workflow (if applicable), agent (which sub-agent/role).
- What was done — in plain prose, one sentence.
- What was touched — file paths, external refs.
- Optional reasoning (expandable, off by default — matches "medium transparency" from wireframe Q&A).
- Status — done / failed / awaiting approval.

**User can:** scroll, filter by workflow, search, click any entry to jump to the file it touched or the workflow run it belongs to. Cannot edit entries (immutable log).

**Agent can:** write entries only. The log is not user-editable and not a workflow state store.

**Data:** append-only markdown in `vault/_activity/` or DB — Stage 1 spec decision. Leaning markdown for portability and git-diff-ability.

**Contrast with run history (S4):** run history shows workflow-level status. Activity log shows every individual action. One workflow run = one history entry + N activity entries.

---

## What's deferred past Stage 1

- **Bottom drawer chat** (wireframe variant C) — revisit if right-rail feels wrong.
- **Inline bubble chat on selections** (wireframe variant D) — Stage 2+.
- **Workflow diagram view** (wireframe tab in S4) — markdown + preview only in Stage 1.
- **Wikilink graph visualization** — users get it via Obsidian.
- **Rich capture (voice, image, clipboard watchers)** — Stage 2.
- **Mobile beyond read-only** — vision-level deferral.
- **Agent-initiated workflow proposals** — the approval card shape ships in Stage 1; actual agent authoring of new workflows is Stage 5.

---

## Library additions required

Current `webApp/` stack (Radix Themes + Tailwind + assistant-ui + react-query + zustand + react-resizable-panels + @dnd-kit + react-markdown) covers most needs. Additions:

| Surface | Library | Why |
|---|---|---|
| All editing (Today, file detail, workflow) | **CodeMirror 6** | Markdown + YAML modes in one editor, per-file language config, source-mode matches "everything is a file" |
| Vault tree | **react-arborist** | Virtualization, keyboard nav, drag-drop for tree |
| ⌘K palette | **`cmdk`** | 3kb, industry standard, Radix-compatible |
| YAML frontmatter | **`yaml`** | Round-trips comments, stricter than js-yaml |
| Wikilinks in rendered markdown | **`remark-wiki-link`** | Plugin for existing remark pipeline |

### Editing pattern: source + rendered preview, side by side

One editor (CodeMirror 6) for every file. Rich rendering is a separate preview pane, not a mode. Three layouts:

- **Split view (default for prose)** — source on left, rendered markdown on right via existing `react-markdown` pipeline. Cursor-synced scrolling. Preview toggle in the header.
- **Source-only (default for workflows)** — `.flow.md` files open source-only, preview tab shows rendered output of the *most recent run* instead of the file.
- **Preview-only (read mode)** — non-edit contexts (citation jumps, backlinks) render the markdown without exposing source.

Rationale: WYSIWYG fights YAML frontmatter and hides the source that makes the vault portable to Obsidian. Split view gives newcomers the rendered view they expect without lying about what's being edited.

### Housekeeping

- **Remove MUI** (`@mui/material`, `@emotion/*`) — unused alongside Radix Themes + Tailwind, introduces design system conflicts.
- **Retire `TodayView.tsx`** (task list) — replace with the S1 surface.
- **Retire `TodayViewMockup.tsx`** — superseded.
- **Retire `ChatPanelV2.tsx` if unused** — consolidate to one ChatPanel.

---

## Next steps

1. Align on this functional description (open for pushback on D1–D5 and surface definitions).
2. Lock library choices (CodeMirror 6 confirmed as single editor; remaining picks are lower-risk).
3. Spec the first surface to build. Candidate: S1 (Today) — it forces D1, D2, and the today.md data model decision. S2 (Vault) is simpler but downstream.
4. UX agent writes Playwright acceptance scripts for S1 against the functional spec before frontend-dev implements.
