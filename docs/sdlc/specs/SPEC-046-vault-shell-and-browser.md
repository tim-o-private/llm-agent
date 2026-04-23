# SPEC-046: Vault Shell & Browser (S2 + AppShell rearchitecture)

> **Status:** Draft — gap analysis + implementation plan
> **Author:** Claude (2026-04-21)
> **Vision:** [`clarity-as-vault.md`](../visions/clarity-as-vault.md), [`clarity-as-vault-functional.md`](../visions/clarity-as-vault-functional.md)
> **Depends on:** SPEC-045 (Today surface — in progress on `spec/SPEC-045-today`)
> **Stage:** Clarity-as-Vault Stage 1 (second buildable surface, prerequisite for S3/S4)

---

## Problem Statement

The vision describes Clarity as a three-pane, Obsidian-like vault browser where Today is a rendered markdown file (`vault/today.md`) inside a file-first UI. What exists is a conventional SPA dashboard — `SideNav` with route links, `TopBar`, and routed pages. The Today implementation (SPEC-045) is well-built but lives inside the wrong container.

This spec bridges the gap: replace the current AppShell with a vault-first shell, build the vault browser (S2), and reframe Today as a specialized file renderer rather than a standalone page.

### What the vision specifies

From `clarity-as-vault-functional.md`:

- **S2 (Vault browser):** Three-pane file browser. Left = file tree with badges, pinned workflows, search. Middle = file grid + preview with breadcrumbs. Right = chat rail scoped to current folder.
- **D1:** Today is `vault/today.md` rendered with a specialized view — not a bespoke screen.
- **D3:** Chat is right-rail by default, Cmd+K anywhere, never a page.
- **D5:** Three-pane IA from wireframes is the directive; visual language uses existing Clarity tokens.

### What currently exists

| Component | Current state | Vision target |
|-----------|--------------|---------------|
| **AppShell** (`layouts/AppShell.tsx`) | 2-pane: SideNav (route links) + content area + ChatPanel slide-in | 3-pane: file tree + content + chat rail |
| **SideNav** (`components/navigation/SideNav.tsx`) | 5 NavLink items (Home, Vault, Workflows, etc.) | File tree (react-arborist) with folder hierarchy, badges, pinned workflows |
| **TopBar** (`components/navigation/TopBar.tsx`) | Logo + date + approvals badge + theme toggle + user menu | Same but with vault breadcrumbs replacing logo text |
| **Today** (`pages/Today.tsx`) | Standalone page at `/today` route, fetches from REST API | Specialized renderer for `today.md`, reached via file tree or default landing |
| **Chat** (`ChatPanel.tsx`) | Slide-in panel, global scope | Right rail (always visible when open), scoped to current folder/file |
| **Routes** (`App.tsx`) | `/today`, `/coach`, `/settings` — page-based routing | File-path routing (`/vault/*`), Today as default landing |
| **File tree** | Does not exist | react-arborist tree of vault contents |
| **File grid/preview** | Does not exist | Middle pane showing folder contents |
| **Cmd+K palette** | Does not exist | cmdk overlay for quick navigation |
| **react-resizable-panels** | Installed (v3.0.2), **unused** | Powers the three-pane resizable layout |

### What SPEC-045 built that we keep

All of these components are reusable — they just need a different container:

- 7 Today section components (HeaderSection, YourDaySection, ToDoSection, NotesSection, AgentSection, ApprovalsSection, RecentSection)
- 6 approval card components + CardShell + useCardEdit
- All React Query hooks (useTodayHooks, useApprovalsHooks)
- All TypeScript types (today.ts)
- ApprovalsBadge (moves from TopBar into new shell)
- SourceToggle (stays as-is)
- Backend services (VaultService, TodayService, ApprovalService — all untouched)

---

## Goal

Ship the vault-first AppShell (S2) so that:

1. The app feels like a file browser, not a dashboard
2. Today is the default landing but navigable from the file tree like any other file
3. The file tree shows the user's vault contents
4. Chat is a right rail scoped to context, not a global slide-in
5. The three-pane layout uses `react-resizable-panels` (already installed)
6. File paths are in the URL (`/vault/path/to/file.md`)

This is **not** the file detail view (S3) — clicking a non-Today file shows a read-only markdown preview. Full CodeMirror editing is SPEC-047.

---

## Acceptance Criteria

### Shell & layout

- [ ] **AC-01:** AppShell renders three resizable panes: left (file tree, default 240px), center (content), right (chat rail, default 320px, collapsible). Uses `react-resizable-panels`. Panes are keyboard-resizable and respect `min-size` constraints.
- [ ] **AC-02:** Left pane collapses to icon-width (48px) on screens < 768px or when user clicks collapse control. Icons: home (Today), folder (vault root), workflow, settings, chat, activity.
- [ ] **AC-03:** Right pane (chat rail) is collapsible via a toggle button. When collapsed, a vertical "Chat" affordance remains visible. ChatPanel renders inside the right pane, scoped to current context.
- [ ] **AC-04:** TopBar spans the full width above all three panes. Contains: breadcrumb (replaces "Clarity" logo text), ApprovalsBadge, ThemeToggle, UserMenu.
- [ ] **AC-05:** Breadcrumb shows the current vault path. Root shows "Today" or the folder/file name. Segments are clickable links to parent folders.

### File tree (left pane)

- [ ] **AC-06:** File tree renders the user's vault directory hierarchy using `react-arborist`. Folders expand/collapse. Files show type indicators (markdown, workflow, image). Badges show unread/pending counts where available.
- [ ] **AC-07:** Tree has a search input above it. Typing filters the tree to matching filenames (client-side filter of loaded tree data).
- [ ] **AC-08:** `today.md` is pinned at the top of the tree with a distinct icon, always visible regardless of folder expansion state.
- [ ] **AC-09:** `_workflows/` folder shows a pinned section below the tree with workflow names and status indicators.
- [ ] **AC-10:** Clicking a file in the tree navigates to `/vault/<path>`. Clicking `today.md` navigates to `/` (or `/vault/today.md` — same view).
- [ ] **AC-11:** Tree data is fetched from `GET /vault/tree` endpoint (new). Returns the recursive directory listing of the user's vault, excluding dot-files and `_activity/`, `_runs/` directories.

### Content pane (center)

- [ ] **AC-12:** When path is `/` or `/vault/today.md`, renders the existing Today page components (all SPEC-045 section components, unchanged).
- [ ] **AC-13:** When path is `/vault/<folder>/`, renders a file grid showing folder contents: filename, type chip, last modified, AI-status chip if available.
- [ ] **AC-14:** When path is `/vault/<file>.md`, renders a read-only markdown preview using `react-markdown` + `remark-gfm`. No editing in this spec (SPEC-047).
- [ ] **AC-15:** When path doesn't match a known file, renders a 404 empty state: "File not found in vault."
- [ ] **AC-16:** Breadcrumb updates reactively as navigation occurs.

### Routing

- [ ] **AC-17:** Routes restructured: `/` → Today (default landing), `/vault/*` → vault browser (file tree + content), `/settings` → settings. Old routes (`/today`, `/coach`, `/today-mockup`) redirect or are removed.
- [ ] **AC-18:** URL reflects current vault path. Browser back/forward navigates vault history correctly.

### Chat rail context scoping

- [ ] **AC-19:** Chat rail shows a scope indicator: "Today", "Folder: <name>", or "File: <name>" based on current navigation.
- [ ] **AC-20:** Chat context includes the current file/folder path so the agent can reference it.

### API (new endpoints)

- [ ] **AC-21:** `GET /vault/tree` returns the recursive directory listing of the user's vault. Response shape: `{ tree: TreeNode[] }` where `TreeNode = { name, path, type: 'file'|'folder', children?: TreeNode[], mtime, size }`. Filtered by VaultService path resolution (no escape). Excludes dot-files, `_activity/`, `_runs/`.
- [ ] **AC-22:** `GET /vault/file?path=<rel_path>` returns the content of a vault file. Uses VaultService._resolve for path safety. Returns `{ content: string, mtime: string, size: number }`.
- [ ] **AC-23:** `GET /vault/folder?path=<rel_path>` returns the contents of a vault folder (flat, one level). Returns `{ entries: FolderEntry[] }` where `FolderEntry = { name, path, type, mtime, size }`.

### Housekeeping

- [ ] **AC-24:** SideNav.tsx is replaced by the file tree. The old component is deleted.
- [ ] **AC-25:** `navConfig.ts` is deleted or replaced with vault-tree configuration.
- [ ] **AC-26:** `react-arborist` and `cmdk` are added to `webApp/package.json`.

---

## Technical Approach

### 1. New AppShell layout

Replace `layouts/AppShell.tsx` with a three-pane layout using `react-resizable-panels` (already installed, currently unused):

```tsx
<div className="h-screen flex flex-col">
  <TopBar />
  <PanelGroup direction="horizontal" className="flex-1">
    <Panel defaultSize={15} minSize={3} collapsible>
      <FileTree />
    </Panel>
    <PanelResizeHandle />
    <Panel defaultSize={60} minSize={30}>
      <Outlet />  {/* routed content */}
    </Panel>
    <PanelResizeHandle />
    <Panel defaultSize={25} minSize={0} collapsible>
      <ChatRail />
    </Panel>
  </PanelGroup>
</div>
```

### 2. File tree component

New component `components/vault/FileTree.tsx` using `react-arborist`:

- Fetches tree data from `GET /vault/tree` via React Query (60s stale time)
- Pins `today.md` at top
- Pins `_workflows/` as a separate section
- Search input filters client-side
- Click navigates via react-router
- Keyboard nav via react-arborist defaults (arrow keys, enter to open)

### 3. Vault router

Replace page-based routing with vault-path routing:

```tsx
<Route element={<VaultShell />}>
  <Route index element={<TodayView />} />
  <Route path="vault/*" element={<VaultContent />} />
  <Route path="settings" element={<SettingsPage />} />
</Route>
```

`VaultContent` is a new component that reads the `*` param, determines if it's a file or folder, and renders accordingly (file → markdown preview, folder → file grid, `today.md` → Today components).

### 4. Backend vault endpoints

Three new endpoints in a new `vault_router.py`, all using existing `VaultService`:

- `GET /vault/tree` — recursive walk of user sandbox, returns `TreeNode[]`
- `GET /vault/file` — read a single file via `VaultService.read_file`
- `GET /vault/folder` — list a directory via a new `VaultService.list_folder` method

All use `get_current_user_id` dependency and `VaultService._resolve` for path safety.

### 5. Cmd+K palette (Stage 1 minimal)

Install `cmdk` (3kb). Bind to Cmd+K globally. Stage 1 scope: free-form input + recent files list. Full contextual suggestions deferred to later spec.

### 6. Chat rail refactor

Existing `ChatPanel` moves from a slide-in overlay to the right pane of the three-panel layout. Key change: add a scope indicator header and pass current vault path as context to the chat API.

---

## What changes vs. what's preserved from SPEC-045

### Preserved (no changes needed)

| Component | Why it's safe |
|-----------|--------------|
| All 7 Today section components | They render props; container doesn't matter |
| All 6 approval card components + CardShell | Same |
| All React Query hooks (useTodayHooks, useApprovalsHooks) | API calls unchanged |
| All TypeScript types | API shapes unchanged |
| SourceToggle | Stays inside Today view |
| All backend services | Untouched — new endpoints compose existing VaultService |
| All migrations + DB schema | Untouched |
| ApprovalsBadge | Moves position in TopBar but component unchanged |

### Changed

| Component | Change |
|-----------|--------|
| `layouts/AppShell.tsx` | Rewritten: 2-pane → 3-pane with react-resizable-panels |
| `components/navigation/SideNav.tsx` | Deleted, replaced by `components/vault/FileTree.tsx` |
| `components/navigation/TopBar.tsx` | Breadcrumb replaces logo text; same controls otherwise |
| `pages/Today.tsx` | Wrapper simplified — no longer wraps in `<main>`; parent layout provides the landmark |
| `components/ChatPanel.tsx` | Refactored from slide-in to right-pane; adds scope indicator |
| `App.tsx` | Routes restructured for vault-path routing |
| `stores/useChatStore.ts` | Adds `scope` field (current vault path) |

### New

| Component | Purpose |
|-----------|---------|
| `components/vault/FileTree.tsx` | react-arborist file tree |
| `components/vault/FolderGrid.tsx` | Folder contents grid view |
| `components/vault/FilePreview.tsx` | Read-only markdown preview for non-Today files |
| `components/vault/VaultContent.tsx` | Router dispatcher: path → Today / folder / file / 404 |
| `components/vault/Breadcrumb.tsx` | Vault path breadcrumb |
| `components/vault/ChatRail.tsx` | Scoped chat rail wrapper |
| `components/vault/CommandPalette.tsx` | Cmd+K via cmdk |
| `api/hooks/useVaultHooks.ts` | useVaultTree, useVaultFile, useVaultFolder |
| `api/types/vault.ts` | TreeNode, FolderEntry types |
| `chatServer/routers/vault_router.py` | GET /vault/tree, /vault/file, /vault/folder |

---

## Library additions

| Library | Version | Size | Why |
|---------|---------|------|-----|
| `react-arborist` | latest | ~30kb | File tree with virtualization, keyboard nav, drag-drop |
| `cmdk` | latest | ~3kb | Cmd+K command palette, Radix-compatible |

`react-resizable-panels` (v3.0.2) is already installed but unused. This spec activates it.

`CodeMirror 6` is **not** added in this spec — deferred to SPEC-047 (file detail / S3).

---

## Scope

### Out of scope

- **S3 file detail editing (CodeMirror 6)** — SPEC-047. This spec renders files as read-only markdown preview.
- **S4 workflow editor** — SPEC-048.
- **Drag-drop file operations in the tree** — Stage 2.
- **File creation/deletion from the UI** — Stage 2 (file_operation approval cards handle this for now).
- **Full Cmd+K contextual suggestions** — minimal in this spec (search + recent files only).
- **Wikilink rendering in markdown preview** — needs `remark-wiki-link`; add in this spec if trivial, otherwise defer.
- **Real-time tree updates (SSE/WebSocket)** — tree refetches on navigation and on a 60s interval.

### Dependencies

- **SPEC-045** must be merged first — this spec reuses all Today components and backend services.
- **VaultService** from SPEC-045 is the backend chokepoint — new endpoints compose it, don't duplicate.

---

## Functional Units

### FU-1: Backend vault endpoints
**Branch:** `feat/SPEC-046-vault-api`
**ACs:** AC-21, AC-22, AC-23
- `vault_router.py` with three GET endpoints
- `VaultService.list_folder` method (new)
- `VaultService.list_tree` method (new, recursive walk)
- Unit tests for tree/folder listing
- Integration tests for auth + path safety

### FU-2: AppShell + file tree + routing
**Branch:** `feat/SPEC-046-vault-shell`
**Depends on:** FU-1
**ACs:** AC-01 through AC-18, AC-24, AC-25, AC-26
- New AppShell with react-resizable-panels
- FileTree component with react-arborist
- VaultContent router dispatcher
- FolderGrid, FilePreview, Breadcrumb components
- Route restructuring in App.tsx
- SideNav deletion
- Install react-arborist, cmdk

### FU-3: Chat rail + Cmd+K
**Branch:** `feat/SPEC-046-chat-rail`
**Depends on:** FU-2
**ACs:** AC-03, AC-19, AC-20
- ChatRail wrapper with scope indicator
- ChatPanel refactor (slide-in → pane)
- CommandPalette with cmdk
- useChatStore scope field

**Merge order:** FU-1 → FU-2 → FU-3

---

## Testing Requirements

### Unit tests
- `test_vault_tree.py`: recursive listing, excludes dot-files and `_activity/`, respects VaultService path safety
- `test_vault_folder.py`: flat listing, auth isolation

### Integration tests
- `test_vault_api.py`: auth required, cross-user isolation, path traversal blocked, tree/folder/file endpoints return correct data

### Playwright (written before implementation)
- `test_ac_01_three_pane_layout`: three resizable panes visible
- `test_ac_06_file_tree_renders`: tree shows vault contents
- `test_ac_10_tree_navigation`: clicking file navigates to `/vault/<path>`
- `test_ac_12_today_renders_in_vault`: `/` or `/vault/today.md` renders Today sections
- `test_ac_13_folder_grid`: folder path shows file grid
- `test_ac_14_file_preview`: markdown file shows rendered preview
- `test_ac_19_chat_scope`: chat rail shows correct scope indicator

---

## Risk Assessment

1. **Biggest risk: AppShell rewrite.** Every page loads through AppShell. The rewrite touches the layout root. Mitigation: SPEC-045 components are pure — they render props, don't depend on shell structure. The rewrite changes the container, not the contents.

2. **react-arborist learning curve.** First use in the codebase. Mitigation: well-documented library, used by VS Code extensions and Obsidian plugins. Tree data is simple (name, path, type, children).

3. **Route restructuring breaks bookmarks.** Old `/today` URLs stop working. Mitigation: add a redirect from `/today` → `/` in the route config.

4. **ChatPanel refactor breaks chat.** Moving from slide-in to pane changes the layout context. Mitigation: ChatPanel's internal logic (assistant-ui, message polling, heartbeat) is independent of its container. Only the outer wrapper changes.
