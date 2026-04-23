# SPEC-047: File Detail View (S3)

> **Status:** Draft
> **Author:** spec-writer (Claude) on behalf of Tim
> **Created:** 2026-04-21
> **Vision:** [`docs/sdlc/visions/clarity-as-vault.md`](../visions/clarity-as-vault.md)
> **Directive:** [`docs/sdlc/visions/clarity-as-vault-functional.md`](../visions/clarity-as-vault-functional.md) (D1, D3, D4, D5, S3, S5 scope rules)
> **Depends on:** SPEC-046 (vault shell provides three-pane container, routing, breadcrumb), SPEC-045 (VaultService is the backend chokepoint)
> **Downstream:** SPEC-048 (workflow editor) specializes this spec's editor for `.flow.md` files
> **Stage:** Clarity-as-Vault Stage 1 (third buildable surface)

---

## Goal

Replace SPEC-046's read-only markdown preview (AC-14) with the full **file detail view** defined in the functional directive -- a CodeMirror 6 source editor with split-view rendered preview, a right-rail AI context panel, and inline suggest cards. This is what the user sees when they click a file in the vault browser.

The view is document-first: the editor and rendered preview own the center pane; AI context (summary, citations, backlinks, activity) lives in a right rail that never takes over the page (per S3 directive). Chat scoping follows S5 rules: the "ask about this" chip opens the chat rail bound to the current file.

This spec introduces CodeMirror 6 to the codebase. The editor component is designed as an extensible `<VaultEditor>` so that SPEC-048 (workflow editor) can compose it with workflow-specific chrome (run history, dry-run, diagram tabs) without forking the editor core.

Success looks like: the user navigates to `/vault/path/to/file.md`, sees a split view of source and rendered markdown, edits the source with changes persisting to disk via VaultService, sees an AI context rail with summary and backlinks, and can toggle between split/source-only/preview-only layouts.

---

## Existing Infrastructure (what we reuse verbatim)

| Primitive | Location | What we use it for |
|-----------|----------|---------------------|
| VaultService | `chatServer/services/vault_service.py` | Read, write, stat, path safety for every file operation |
| `GET /vault/file` | `chatServer/routers/vault_router.py` (SPEC-046 AC-22) | Fetch file content + mtime for the editor |
| `GET /vault/tree` | `chatServer/routers/vault_router.py` (SPEC-046 AC-21) | Backlinks computation (server-side grep for `[[filename]]`) |
| VaultShell three-pane layout | `webApp/src/layouts/AppShell.tsx` (SPEC-046 AC-01) | Editor renders in the center pane; chat rail is the right pane |
| Breadcrumb | `webApp/src/components/vault/Breadcrumb.tsx` (SPEC-046 AC-05) | Shows current file path; this spec adds save-status indicator beside it |
| ChatRail + scope binding | `webApp/src/components/vault/ChatRail.tsx` (SPEC-046 AC-19/20) | "Ask about this" chip opens chat scoped to the current file |
| `react-resizable-panels` | `webApp/package.json` (v3.0.2, activated by SPEC-046) | Split view within the center pane (source / preview sub-panels) |
| `remark-gfm` | `webApp/package.json` (v4.0.1) | GFM rendering in the preview pane |
| `@assistant-ui/react-markdown` | `webApp/src/components/assistantui/MarkdownText.tsx` | Existing markdown component pattern; preview pane builds a standalone pipeline |
| Auth dependency | `chatServer/dependencies/auth.py` | Every file endpoint resolves `user_id` from ES256 JWT |
| StorageSync | `chatServer/services/storage_sync.py` | Fire-and-forget sync on every vault write |

---

## Acceptance Criteria

Each AC has a stable ID. Playwright scripts reference these directly. User-visible ACs MUST be queryable by ARIA role/label or stable `data-testid`.

### Editor core

- [ ] **AC-01:** Navigating to `/vault/<path>.md` renders the file detail view in the center pane of the vault shell. The view contains: a header bar (breadcrumb + save status + layout toggle + action chips), a CodeMirror 6 editor panel, and a rendered markdown preview panel. The right rail shows AI context (summary, citations, backlinks, activity). The file tree (left pane from SPEC-046) remains visible. [D5, F1]
- [ ] **AC-02:** The editor uses CodeMirror 6 with the `@codemirror/lang-markdown` extension and `@codemirror/language-data` for fenced code block highlighting. Syntax highlighting is active. The editor is accessible: `role="textbox"` with `aria-label="Source editor for <filename>"`, supports keyboard navigation via CodeMirror defaults. [A14]
- [ ] **AC-03:** The editor loads the file content from `GET /vault/file?path=<rel_path>` via the `useVaultFile` hook (SPEC-046). The response `mtime` is stored for optimistic concurrency on save. [A4]
- [ ] **AC-04:** Edits in the editor are **not** auto-saved. A visible save-status indicator in the header bar shows one of three states: "Saved" (checkmark, green), "Unsaved changes" (dot, amber), or "Saving..." (spinner). The user saves explicitly via Cmd+S / Ctrl+S (keyboard shortcut) or a "Save" button in the header bar. [A14]
- [ ] **AC-05:** Save calls `PUT /vault/file` with the editor content and the last-known `mtime` as `If-Match`. On success (200), the save-status flips to "Saved" and the local mtime updates. On 409 (concurrent edit), a toast displays "File was modified elsewhere -- reload to see changes" with a "Reload" action that refetches. On 413 (file too large), a toast displays "File exceeds size limit." [A12]
- [ ] **AC-06:** Unsaved changes trigger a browser `beforeunload` prompt and a react-router navigation blocker (`useBlocker`) with a confirmation dialog: "You have unsaved changes. Discard?" [A14]

### Split view layouts

- [ ] **AC-07:** Three layout modes are available, toggled via a segmented control in the header bar with `aria-label="Editor layout"`:
  - **Split** (default for `.md` files) -- source on left, rendered preview on right, using `react-resizable-panels` with a draggable divider. Default split: 50/50.
  - **Source only** -- full-width CodeMirror editor, preview hidden.
  - **Preview only** (read mode) -- full-width rendered markdown, editor hidden. Editor content is preserved in memory; switching back to split or source restores it.
  Each mode has a `data-testid="layout-<mode>"` on the active button. [D5]
- [ ] **AC-08:** `.flow.md` files default to source-only layout. All other `.md` files default to split. The user can override the default for the current session; the override does not persist. [S3, S4]
- [ ] **AC-09:** The rendered preview pane uses `react-markdown` with `remark-gfm` and `remark-wiki-link`. Wikilinks (`[[target]]` and `[[target|display]]`) render as `<a>` elements with `href="/vault/<target>.md"` and react-router navigation (no full-page reload). YAML frontmatter (delimited by `---`) is rendered in a styled `<pre>` block with JetBrains Mono at the top of the preview, not as body prose. [D4, D5]
- [ ] **AC-10:** In split mode, scrolling the editor scrolls the preview proportionally (percentage-based scroll sync). Scroll sync is approximate -- exact line mapping is a later enhancement. The user can scroll either pane independently; sync re-engages on the next editor scroll event. [A14]

### Header bar

- [ ] **AC-11:** The header bar is a `<div role="toolbar" aria-label="File actions">` above the editor/preview area. It contains (left to right): breadcrumb (from SPEC-046, showing full vault path), save-status indicator, layout segmented control, and action chips. [F2]
- [ ] **AC-12:** Three action chips in the header bar:
  - **History** (`data-testid="chip-history"`) -- Stage 1: disabled with tooltip "Coming soon." Wired in a later spec to git log for the file.
  - **Share** (`data-testid="chip-share"`) -- Stage 1: disabled with tooltip "Coming soon."
  - **Ask** (`data-testid="chip-ask"`) -- active. Clicking it opens the chat rail (SPEC-046 AC-03) scoped to the current file per S5 scope binding rules. The chat scope indicator reads "File: <filename>". If the user has selected text in the editor, the selection is included as quoted context in the chat input. [D3, S5]

### AI context rail (right sub-rail within the center pane)

- [ ] **AC-13:** The file detail view renders an AI context rail as a secondary panel on the right side of the center pane (not the chat rail -- this is a narrower, content-focused panel between the editor and the chat rail). It is collapsible via a toggle button. Collapsed state is persisted in `localStorage` per `file-detail-context-rail-collapsed`. When collapsed, a vertical "Context" label with a chevron remains visible. The rail has `aria-label="AI context for <filename>"`. [S3]
- [ ] **AC-14:** The AI context rail contains four sections in order, each as a `<section aria-labelledby="context-<name>">`:
  - **Summary** -- a one-to-three sentence auto-summary of the file content. Stage 1: computed client-side by extracting the first non-frontmatter paragraph (up to 280 characters). Agent-maintained summaries are a later enhancement.
  - **Citations** -- numbered list of outgoing wikilinks found in the document (`[[target]]`). Each citation shows a number badge, the target filename (JetBrains Mono, per D4), and is clickable (navigates to `/vault/<target>.md`). Empty state: "No outgoing links."
  - **Linked by** -- backlinks: other vault files that contain `[[this-filename]]`. Fetched from `GET /vault/backlinks?path=<rel_path>`. Each entry is clickable. Empty state: "No incoming links."
  - **Activity** -- recent activity timeline for this file. Stage 1: shows last-modified timestamp from file stat. Agent-maintained activity entries are a later enhancement. Empty state: "No recent activity."
- [ ] **AC-15:** The Citations section updates reactively as the user types in the editor. A debounced (500ms) scan of the editor content extracts `[[...]]` patterns and updates the citation list without a server round-trip. [A14]

### Inline suggest cards

- [ ] **AC-16:** The agent can insert suggest cards into the document flow. A suggest card is rendered as a styled block between document lines (not inside the CodeMirror editor -- in the preview pane only). Each card has:
  - A "Clarity suggests" label (no emoji, plain text).
  - A one-to-three sentence suggestion body.
  - Two action buttons: "Accept" and "Dismiss."
  - `role="region" aria-label="Suggestion: <truncated body>"`.
  Stage 1 data source: suggest cards are stored as entries in a `suggest_cards` array returned by `GET /vault/file/context?path=<rel_path>`. Accept/dismiss calls `POST /vault/file/suggest/{id}/accept` or `.../dismiss`. [S3, A12]
- [ ] **AC-17:** Accepting a suggestion inserts the suggested text at the indicated document position (line number from the card's `target_line` field). The card disappears from the preview. Dismissing removes the card without modifying the document. Both actions are recorded in `activity_log`. [A12]

### YAML frontmatter handling

- [ ] **AC-18:** Files with YAML frontmatter (delimited by `---` on the first line and a closing `---`) display the frontmatter in the CodeMirror editor with YAML syntax highlighting (via `@codemirror/lang-yaml` activated within the fenced region). In the preview pane, frontmatter renders as a distinct styled block: monospace font (JetBrains Mono), muted background, key-value pairs displayed, separated from the body by a subtle divider. [D4]

### Save endpoint (new)

- [ ] **AC-19:** `PUT /vault/file` accepts `{ path: string, content: string, mtime: number }`. It calls `VaultService.update_body(user_id, path, content, expected_mtime=mtime)`. Returns `{ mtime: number }` on success. Returns 409 if mtime does not match (concurrent edit). Returns 413 if content exceeds 10MB. Returns 403 on path traversal. Returns 404 if the file does not exist (no create-via-PUT in Stage 1). Auth required. [A1, A8]

### Backlinks endpoint (new)

- [ ] **AC-20:** `GET /vault/backlinks?path=<rel_path>` returns `{ backlinks: Array<{ path: string, name: string }> }` -- all vault files that contain a wikilink `[[<filename>]]` where `<filename>` matches the stem of `rel_path` (e.g., for `notes/meeting.md`, matches `[[meeting]]` and `[[meeting|Meeting Notes]]`). Implementation: `VaultService.find_backlinks(user_id, rel_path)` walks the vault (reusing the `_walk_recent` pattern), reads each `.md` file, and greps for the wikilink pattern. Results are cached per-request (no persistent cache in Stage 1). Auth required. [A1, A8]

### File context endpoint (new)

- [ ] **AC-21:** `GET /vault/file/context?path=<rel_path>` returns AI context for a file: `{ summary: string | null, suggest_cards: SuggestCard[], activity: ActivityEntry[] }`. Stage 1: summary is null (client computes it), suggest_cards come from a `suggest_cards` table, activity comes from `activity_log` filtered by `subject_path`. Auth required. [A1]

### Suggest card endpoints (new)

- [ ] **AC-22:** `POST /vault/file/suggest/{id}/accept` and `POST /vault/file/suggest/{id}/dismiss` mutate the suggest card's status. Accept also returns the `{ text: string, target_line: number }` payload so the client can insert it into the editor. Dismiss returns 204. Both emit `activity_log` entries. Auth required. [A1, A12]

### Auth + isolation

- [ ] **AC-23:** All new endpoints require authentication. User B cannot read, write, or access suggest cards for User A's files. Integration tests cover path safety and cross-user isolation. [A8]

### Accessibility

- [ ] **AC-24:** The file detail view is navigable by keyboard: Tab moves between header bar controls, editor, preview, and context rail. Cmd+S saves. Escape from the editor returns focus to the header bar. The layout segmented control is operable via arrow keys. Screen readers announce save status changes via `aria-live="polite"` on the save-status indicator. [F2]

---

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/20260422000001_create_suggest_cards.sql` | `suggest_cards` table: id, user_id, file_path, target_line, text, body, status (pending/accepted/dismissed), created_at. RLS: user SELECT/UPDATE own; INSERT via service role. |
| `chatServer/services/file_context_service.py` | Backlinks computation, suggest card CRUD, file context composition. |
| `chatServer/routers/vault_file_router.py` | `PUT /vault/file`, `GET /vault/backlinks`, `GET /vault/file/context`, `POST /vault/file/suggest/{id}/accept`, `POST /vault/file/suggest/{id}/dismiss`. Thin router delegating to services. [A1] |
| `webApp/src/components/vault/VaultEditor.tsx` | Extensible CodeMirror 6 wrapper. Props: `content`, `onChange`, `language` (default markdown), `readOnly`. Exposes imperative handle for `getValue()`, `setValue()`, `getSelection()`. SPEC-048 composes this with workflow chrome. |
| `webApp/src/components/vault/EditorPreviewSplit.tsx` | Split view container using `react-resizable-panels`. Manages layout mode state (split/source/preview). Contains `VaultEditor` + `MarkdownPreview`. |
| `webApp/src/components/vault/MarkdownPreview.tsx` | Rendered markdown pane: `react-markdown` + `remark-gfm` + `remark-wiki-link` + frontmatter block. Renders suggest cards inline at their `target_line` positions. |
| `webApp/src/components/vault/FileDetailView.tsx` | Top-level file detail component. Composes header bar, `EditorPreviewSplit`, and `ContextRail`. Loaded by `VaultContent` (SPEC-046) when path matches a `.md` file. |
| `webApp/src/components/vault/FileHeaderBar.tsx` | Toolbar: breadcrumb slot, save status, layout toggle, action chips (History, Share, Ask). |
| `webApp/src/components/vault/ContextRail.tsx` | AI context right sub-rail: Summary, Citations, Linked by, Activity sections. Collapsible. |
| `webApp/src/components/vault/SuggestCard.tsx` | Single suggest card component with Accept/Dismiss actions. |
| `webApp/src/components/vault/FrontmatterBlock.tsx` | Styled `<pre>` block for YAML frontmatter in the preview pane. |
| `webApp/src/components/vault/SaveStatus.tsx` | Save-status indicator with three states + aria-live. |
| `webApp/src/components/vault/LayoutToggle.tsx` | Segmented control for split/source/preview layout modes. |
| `webApp/src/api/hooks/useFileDetailHooks.ts` | `useSaveFile`, `useBacklinks`, `useFileContext`, `useSuggestCardAction`. [A4] |
| `webApp/src/api/types/fileDetail.ts` | `SaveFileRequest`, `SaveFileResponse`, `BacklinksResponse`, `FileContextResponse`, `SuggestCard` types. |
| `webApp/src/lib/extractCitations.ts` | Pure function: scan markdown string for `[[...]]` patterns, return `Array<{ index: number, target: string, display: string }>`. |
| `webApp/src/lib/extractFrontmatter.ts` | Pure function: split a markdown string into `{ frontmatter: string | null, body: string }`. |
| `tests/unit/services/test_file_context_service.py` | Backlinks computation, suggest card state transitions. |
| `tests/integration/test_vault_file_api.py` | PUT /vault/file round-trip, auth, path safety, mtime conflict. |
| `tests/integration/test_vault_backlinks_api.py` | Backlinks endpoint, auth, cross-user isolation. |
| `tests/integration/test_vault_suggest_api.py` | Suggest card accept/dismiss, activity_log emission. |
| `tests/uat/playwright/test_spec_047_file_detail.py` | One Playwright function per user-visible AC. Written BEFORE frontend implementation. |

### Files to Modify

| File | Change |
|------|--------|
| `webApp/src/components/vault/VaultContent.tsx` (SPEC-046) | When path matches a `.md` file, render `FileDetailView` instead of the read-only `FilePreview`. `FilePreview` is deleted or kept as a fallback for non-markdown files. |
| `webApp/src/components/vault/ChatRail.tsx` (SPEC-046) | "Ask" chip sets scope to current file path. If editor selection exists, include as quoted context. |
| `webApp/src/components/vault/Breadcrumb.tsx` (SPEC-046) | Add a slot for save-status indicator beside the breadcrumb. |
| `webApp/package.json` | Add `codemirror`, `@codemirror/lang-markdown`, `@codemirror/lang-yaml`, `@codemirror/language-data`, `@codemirror/state`, `@codemirror/view`, `@codemirror/commands`, `@codemirror/search`, `@codemirror/autocomplete`, `react-markdown`, `remark-wiki-link`, `yaml` (YAML parser for frontmatter). |
| `chatServer/main.py` | Register `vault_file_router`. |
| `chatServer/services/vault_service.py` | Add `find_backlinks(user_id, rel_path)` method. |

### Out of Scope

- **Workflow editor specializations** -- SPEC-048. This spec builds the extensible `<VaultEditor>` component; SPEC-048 adds run history, dry-run, and diagram tabs for `.flow.md` files.
- **Agent-maintained summaries** -- Summary in the context rail is client-computed in Stage 1. Server-side LLM-generated summaries are a later enhancement.
- **Agent-maintained activity timeline** -- Activity section shows file stat in Stage 1. Rich per-action entries arrive when the agent writes to `activity_log` with `subject_path`.
- **Git history for files** -- History chip is disabled in Stage 1. Wired to `git log` in a later spec.
- **Share/export** -- Share chip is disabled in Stage 1.
- **File creation from the editor** -- PUT returns 404 for non-existent files. File creation flows through the vault browser or agent.
- **Cmd+K palette integration** -- Covered by SPEC-046. This spec's "Ask" chip uses the chat rail directly.
- **Non-markdown file rendering** -- `.json`, `.yaml`, `.csv`, images. Later spec. CodeMirror can handle source display of text files; binary files show a placeholder.
- **Collaborative editing / CRDT** -- Single-user optimistic concurrency via mtime. Multi-user real-time editing is a much later concern.
- **Scroll sync by line mapping** -- Stage 1 uses percentage-based scroll sync. Line-accurate mapping (via source-map) is a later enhancement.
- **Persistent layout preference** -- Layout mode resets on navigation. User-preferred default per file type is a later enhancement.

---

## Technical Approach

### 1. CodeMirror 6 integration -- `VaultEditor` component

The `VaultEditor` component wraps CodeMirror 6 as a controlled React component. Design decisions:

**Controlled vs uncontrolled:** The component is uncontrolled internally (CodeMirror manages its own state via `EditorState`) with an imperative handle for external access. This matches CodeMirror 6's architecture -- forcing React-controlled re-renders on every keystroke defeats CM6's efficient update mechanism. The parent passes initial `content` as a prop; subsequent changes are reported via `onChange(content: string)` callback. The parent tracks dirty state by comparing current content to the last-saved content.

```tsx
interface VaultEditorProps {
  content: string;
  onChange: (content: string) => void;
  language?: 'markdown' | 'yaml' | 'json';
  readOnly?: boolean;
  className?: string;
}

interface VaultEditorHandle {
  getValue(): string;
  setValue(content: string): void;
  getSelection(): string;
  focus(): void;
}

const VaultEditor = forwardRef<VaultEditorHandle, VaultEditorProps>(
  ({ content, onChange, language = 'markdown', readOnly = false, className }, ref) => {
    // ...
  }
);
```

**Extensions loaded:**
- `@codemirror/lang-markdown` with `@codemirror/language-data` for nested language highlighting
- `@codemirror/lang-yaml` (activated for frontmatter regions and `.yaml` files)
- `@codemirror/commands` (defaultKeymap, Cmd+S bound to save callback)
- `@codemirror/search` (Cmd+F find/replace)
- `@codemirror/view` (lineWrapping, drawSelection, highlightActiveLine)
- Theme: a custom theme matching Clarity's token system (bg, text, selection colors from Tailwind CSS variables). Dark/light mode follows the existing ThemeToggle.

**Why not ProseMirror / TipTap / Milkdown:** The functional directive explicitly specifies CodeMirror 6 for source editing with a separate preview pane. WYSIWYG editors fight YAML frontmatter and hide the source. Split view (source + preview) is the directive. CodeMirror 6 is the industry standard for source editing; it's what Obsidian uses internally.

**Extensibility for SPEC-048:** The `VaultEditor` component accepts optional additional extensions via a `extensions` prop (array of CM6 `Extension` objects). SPEC-048 will pass workflow-specific extensions (e.g., YAML schema validation, step highlighting). The component's imperative handle lets SPEC-048's parent read the current content for dry-run dispatch.

### 2. Split view -- `EditorPreviewSplit`

Uses `react-resizable-panels` (already installed and activated by SPEC-046) for the source/preview split within the center pane:

```tsx
<PanelGroup direction="horizontal" aria-label="Editor split view">
  {showEditor && (
    <Panel defaultSize={50} minSize={25}>
      <VaultEditor ref={editorRef} content={content} onChange={handleChange} />
    </Panel>
  )}
  {showEditor && showPreview && <PanelResizeHandle />}
  {showPreview && (
    <Panel defaultSize={50} minSize={25}>
      <MarkdownPreview content={content} suggestCards={suggestCards} />
    </Panel>
  )}
</PanelGroup>
```

Layout state is local to the component (React `useState`). Three modes:
- `split`: both panels visible (default for `.md`)
- `source`: editor panel only
- `preview`: preview panel only (read mode)

The `LayoutToggle` segmented control sets this state. `.flow.md` files default to `source`.

### 3. Markdown preview -- `MarkdownPreview`

The preview pane builds a standalone `react-markdown` pipeline (not reusing the `@assistant-ui/react-markdown` component, which is tightly coupled to the assistant-ui Thread context):

```tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkWikiLink from 'remark-wiki-link';

const MarkdownPreview: React.FC<{ content: string; suggestCards: SuggestCard[] }> = ({
  content,
  suggestCards,
}) => {
  const { frontmatter, body } = extractFrontmatter(content);

  return (
    <div className="vault-preview" aria-label="Rendered preview">
      {frontmatter && <FrontmatterBlock content={frontmatter} />}
      <ReactMarkdown
        remarkPlugins={[
          remarkGfm,
          [remarkWikiLink, {
            pageResolver: (name: string) => [name],
            hrefTemplate: (permalink: string) => `/vault/${permalink}.md`,
            aliasDivider: '|',
          }],
        ]}
        components={{
          a: WikiLinkAnchor,  // react-router Link for internal wiki links
          // ... heading, code, etc. with Clarity token styles
        }}
      >
        {body}
      </ReactMarkdown>
      {/* Suggest cards rendered after the body, grouped by target_line */}
    </div>
  );
};
```

**Wikilink rendering:** `remark-wiki-link` transforms `[[target]]` and `[[target|display]]` into anchor elements. The custom `WikiLinkAnchor` component detects wiki-originated links (by `href` starting with `/vault/`) and renders them as react-router `<Link>` elements for SPA navigation. External links use standard `<a target="_blank">`.

**Frontmatter rendering:** `extractFrontmatter` is a pure function that splits on the leading `---` delimiters. The `FrontmatterBlock` component renders the raw YAML in a `<pre>` with JetBrains Mono, muted background, and a "Frontmatter" label.

**Suggest cards in the preview:** Cards are rendered as positioned blocks after the nearest paragraph to their `target_line`. Since `react-markdown` does not expose line numbers in the rendered output, Stage 1 places suggest cards sequentially at the end of the preview body, ordered by `target_line`. Precise inline positioning (interleaved between rendered paragraphs) is a later enhancement.

### 4. AI context rail -- `ContextRail`

The context rail is a narrow panel (default 220px, min 180px) between the editor/preview area and the chat rail (which is the shell's right pane). It uses `react-resizable-panels` as a nested `PanelGroup` within the center pane:

```
Center pane layout:
+-------------------------------------------+
| FileHeaderBar (toolbar)                   |
+-------------------------------------------+
| EditorPreviewSplit    | ContextRail       |
| (source + preview)    | (summary, cites,  |
|                       |  backlinks, log)  |
+-------------------------------------------+
```

The context rail is collapsible. When collapsed, the editor/preview split takes the full center pane width.

**Data sources:**

- **Summary:** Client-side extraction of the first non-frontmatter paragraph, truncated to 280 chars. No server call.
- **Citations:** Client-side extraction of `[[...]]` patterns from editor content, debounced at 500ms. Uses `extractCitations` pure function.
- **Linked by (backlinks):** `GET /vault/backlinks?path=<rel_path>`. Fetched on mount and when the file path changes. Uses React Query with 60s stale time.
- **Activity:** `GET /vault/file/context?path=<rel_path>` returns `activity` array. Stage 1: file stat only. Uses React Query with 30s stale time.

### 5. Save flow

**Frontend:**

1. User edits content in CodeMirror. `onChange` fires, parent sets `isDirty = true`, save-status shows "Unsaved changes."
2. User presses Cmd+S or clicks Save.
3. `useSaveFile` mutation calls `PUT /vault/file` with `{ path, content, mtime }`.
4. On success: update local mtime, set `isDirty = false`, save-status shows "Saved."
5. On 409: toast with "File modified elsewhere" + Reload action. Reload refetches `GET /vault/file`, replaces editor content, clears dirty state.
6. On network error: toast with "Save failed -- try again." Save-status returns to "Unsaved changes."

**Backend:**

`PUT /vault/file` endpoint in `vault_file_router.py`:

```python
class SaveFileRequest(BaseModel):
    path: str = Field(..., min_length=1)
    content: str
    mtime: float

class SaveFileResponse(BaseModel):
    mtime: float

@router.put("/file", response_model=SaveFileResponse)
async def save_file(
    payload: SaveFileRequest,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    new_mtime = await vault.update_body(
        user_id, payload.path, payload.content, expected_mtime=payload.mtime,
    )
    return SaveFileResponse(mtime=new_mtime)
```

This reuses `VaultService.update_body` which already handles mtime checking, size limits, path safety, and StorageSync.

### 6. Backlinks -- `VaultService.find_backlinks`

New method on VaultService:

```python
async def find_backlinks(
    self, user_id: str, rel_path: str
) -> list[dict[str, str]]:
    """Find all vault files containing a wikilink to the given file."""
    user_root = self._user_root(user_id)
    if not user_root.exists():
        return []
    stem = Path(rel_path).stem  # "meeting" from "notes/meeting.md"
    pattern = re.compile(r"\[\[" + re.escape(stem) + r"(?:\|[^\]]+)?\]\]")
    return await asyncio.to_thread(
        self._grep_backlinks, user_root, rel_path, pattern
    )
```

Implementation walks the vault (reusing the same `os.walk` pattern as `_walk_recent`), reads each `.md` file, and checks for the wikilink pattern. Excludes `_activity/`, `_runs/`, hidden files, and the file itself.

**Performance:** For Stage 1 vaults (Tim's vault, likely < 500 files), a full walk is acceptable. For larger vaults, we add a file-content index in a later spec.

### 7. Suggest cards schema

```sql
CREATE TYPE suggest_card_status AS ENUM ('pending', 'accepted', 'dismissed');

CREATE TABLE suggest_cards (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    file_path    TEXT NOT NULL,
    target_line  INT NOT NULL DEFAULT 0,
    label        TEXT NOT NULL DEFAULT 'Clarity suggests',
    body         TEXT NOT NULL,
    suggested_text TEXT,
    status       suggest_card_status NOT NULL DEFAULT 'pending',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at   TIMESTAMPTZ
);
CREATE INDEX ON suggest_cards(user_id, file_path, status);
-- RLS: user SELECT/UPDATE own; INSERT via service role only (agent-side).
ALTER TABLE suggest_cards ENABLE ROW LEVEL SECURITY;
CREATE POLICY suggest_cards_select ON suggest_cards
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY suggest_cards_update ON suggest_cards
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY suggest_cards_insert ON suggest_cards
    FOR INSERT WITH CHECK (auth.role() = 'service_role');
```

- `file_path`: vault-relative path of the file this card belongs to.
- `target_line`: line number in the source where the suggestion applies.
- `body`: the suggestion explanation text ("runway-model.csv was updated...").
- `suggested_text`: the text to insert on accept (nullable -- some suggestions are informational).
- `label`: display label (default "Clarity suggests").

### 8. Frontend types

```typescript
// api/types/fileDetail.ts

export interface SaveFileRequest {
  path: string;
  content: string;
  mtime: number;
}

export interface SaveFileResponse {
  mtime: number;
}

export interface BacklinksResponse {
  backlinks: Array<{ path: string; name: string }>;
}

export interface SuggestCard {
  id: string;
  file_path: string;
  target_line: number;
  label: string;
  body: string;
  suggested_text: string | null;
  status: 'pending' | 'accepted' | 'dismissed';
  created_at: string;
}

export interface ActivityEntry {
  id: string;
  actor: string;
  action: string;
  status: string;
  created_at: string;
}

export interface FileContextResponse {
  summary: string | null;
  suggest_cards: SuggestCard[];
  activity: ActivityEntry[];
}
```

### 9. Library additions

| Package | Version | Size | Why |
|---------|---------|------|-----|
| `codemirror` | ^6.0 | meta-package | CodeMirror 6 core bundle |
| `@codemirror/lang-markdown` | ^6.0 | ~15kb | Markdown language support |
| `@codemirror/lang-yaml` | ^6.0 | ~8kb | YAML highlighting for frontmatter |
| `@codemirror/language-data` | ^6.0 | ~20kb | Fenced code block language detection |
| `@codemirror/state` | ^6.0 | ~30kb | Editor state management |
| `@codemirror/view` | ^6.0 | ~80kb | Editor view layer |
| `@codemirror/commands` | ^6.0 | ~10kb | Default keybindings, Cmd+S |
| `@codemirror/search` | ^6.0 | ~12kb | Find/replace |
| `@codemirror/autocomplete` | ^6.0 | ~15kb | Completion framework (used by SPEC-048) |
| `react-markdown` | ^10.1 | ~15kb | Standalone markdown renderer for preview pane |
| `remark-wiki-link` | ^2.0 | ~3kb | `[[wikilink]]` support in remark pipeline |
| `yaml` | ^2.0 | ~30kb | Round-trip YAML parsing for frontmatter display |

Total addition: ~240kb (pre-tree-shaking). CodeMirror 6 is modular; unused extensions are not bundled.

---

## Testing Requirements

### Unit Tests (required)

- `test_file_context_service.py`: backlinks computation (finds links, excludes self, handles `[[target|alias]]`), suggest card state transitions (accept/dismiss), activity log emission on transitions.
- `test_vault_service_backlinks.py`: `find_backlinks` returns correct results, excludes hidden files and system dirs, handles files with no links, handles broken encoding gracefully.
- `webApp/src/lib/extractCitations.test.ts`: extracts `[[target]]`, `[[target|display]]`, deduplicates, handles empty string, handles no links.
- `webApp/src/lib/extractFrontmatter.test.ts`: splits frontmatter correctly, handles no frontmatter, handles unclosed frontmatter, handles frontmatter-only file.
- `webApp/src/components/vault/VaultEditor.test.tsx`: renders with content, calls onChange on edit, imperative handle works, readOnly disables editing.
- `webApp/src/components/vault/MarkdownPreview.test.tsx`: renders markdown, renders wikilinks as router Links, renders frontmatter block, renders suggest cards.
- `webApp/src/components/vault/LayoutToggle.test.tsx`: three modes toggle correctly, correct data-testid on active button.
- `webApp/src/components/vault/SaveStatus.test.tsx`: three states render correctly, aria-live announces changes.

### Integration Tests (required)

- `test_vault_file_api.py`: PUT round-trip (save + re-read matches), auth required, 409 on stale mtime, 413 on oversized content, 403 on path traversal, 404 on non-existent file.
- `test_vault_backlinks_api.py`: returns correct backlinks, auth required, cross-user isolation, empty vault returns empty list.
- `test_vault_suggest_api.py`: accept flips status + returns payload, dismiss flips status + returns 204, activity_log entries emitted, cross-user 403.

### UI Acceptance Tests (Playwright -- written BEFORE implementation)

Script: `tests/uat/playwright/test_spec_047_file_detail.py`. One function per user-visible AC. Selectors target ARIA role/label or `data-testid`.

| AC | Flow / Service Test | UI Test (Playwright) |
|----|---------------------|---------------------|
| AC-01 | -- | `test_ac_01_file_detail_renders` |
| AC-02 | -- | `test_ac_02_editor_accessible` |
| AC-03 | `test_file_load_from_api` | `test_ac_03_editor_loads_content` |
| AC-04 | -- | `test_ac_04_save_status_states` |
| AC-05 | `test_save_roundtrip`, `test_save_conflict_409` | `test_ac_05_save_and_conflict` |
| AC-06 | -- | `test_ac_06_unsaved_navigation_blocker` |
| AC-07 | -- | `test_ac_07_layout_modes` |
| AC-08 | -- | `test_ac_08_flow_md_defaults_source` |
| AC-09 | -- | `test_ac_09_wikilinks_render_as_router_links` |
| AC-10 | -- | `test_ac_10_scroll_sync` |
| AC-11 | -- | `test_ac_11_header_toolbar` |
| AC-12 | -- | `test_ac_12_action_chips` |
| AC-13 | -- | `test_ac_13_context_rail_collapsible` |
| AC-14 | -- | `test_ac_14_context_rail_sections` |
| AC-15 | -- | `test_ac_15_citations_update_on_type` |
| AC-16 | `test_suggest_cards_render` | `test_ac_16_suggest_card_renders` |
| AC-17 | `test_suggest_accept_inserts`, `test_suggest_dismiss` | `test_ac_17_suggest_accept_dismiss` |
| AC-18 | -- | `test_ac_18_frontmatter_display` |
| AC-19 | `test_save_endpoint_roundtrip` | -- |
| AC-20 | `test_backlinks_endpoint` | -- |
| AC-21 | `test_file_context_endpoint` | -- |
| AC-22 | `test_suggest_accept_dismiss_endpoints` | -- |
| AC-23 | `test_cross_user_isolation` | -- |
| AC-24 | -- | `test_ac_24_keyboard_navigation` |

### Manual Verification (UAT)

1. Navigate to a markdown file from the vault tree -- verify editor loads with content, split view active.
2. Type in the editor -- verify save-status changes to "Unsaved changes," preview updates live.
3. Press Cmd+S -- verify save-status flips to "Saved," file on disk matches editor content.
4. Open the same file in two browser tabs, edit in one, save, then save in the other -- verify 409 toast with Reload action.
5. Toggle layout modes (split/source/preview) -- verify each mode shows the correct panels.
6. Add a `[[wikilink]]` in the editor -- verify it appears as a clickable link in preview, and the Citations section in the context rail updates.
7. Navigate to a file that is linked from another file -- verify the "Linked by" section shows the source file.
8. Click the "Ask" chip -- verify chat rail opens scoped to the current file.
9. Select text in the editor, then click "Ask" -- verify the selection appears as quoted context in the chat input.
10. Collapse and expand the context rail -- verify state persists across navigations.
11. Navigate away with unsaved changes -- verify the confirmation dialog appears.
12. Open a `.flow.md` file -- verify it defaults to source-only layout.
13. Open a file with YAML frontmatter -- verify frontmatter renders distinctly in the preview.
14. Seed a suggest card via SQL for the current file -- verify it renders in the preview with Accept/Dismiss buttons.
15. Accept a suggest card -- verify the suggested text appears in the editor and the card disappears.
16. Sign in as a second user -- verify no cross-user file access.

---

## Edge Cases

- **File not found (deleted between tree load and click):** `GET /vault/file` returns 404. UI shows "File not found in vault" empty state with a "Back to vault" link. Does not render the editor.
- **File is not markdown:** For `.yaml`, `.json`, `.txt` -- CodeMirror renders in source-only mode with appropriate language extension. Preview pane shows "Preview not available for this file type." For binary files -- show placeholder "Binary file -- cannot display." Stage 1 does not attempt to render images.
- **Very large file (>1MB):** CodeMirror handles large files but performance degrades. UI shows a warning banner: "Large file -- editing may be slow." Preview is disabled for files > 500KB (source-only forced). Save endpoint rejects > 10MB (existing VaultService cap).
- **Frontmatter is malformed:** `extractFrontmatter` fails to find closing `---`. Falls back to treating entire content as body (no frontmatter block in preview). No crash.
- **Concurrent edits from two tabs:** The `mtime` optimistic concurrency check catches this. Second save gets 409. User reloads to pick up the first tab's changes. No merge -- last-save-wins after reload.
- **Agent writes to file while user is editing:** Agent writes via bwrap (SPEC-044 path), which goes directly to disk. Next save from the UI gets 409 because mtime changed. User sees "File was modified elsewhere" toast.
- **Backlinks endpoint on a vault with many files:** `find_backlinks` reads every `.md` file. For 500 files at ~5KB average = ~2.5MB of reads. Acceptable for Stage 1. If latency exceeds 2s, a future spec adds an inverted index.
- **Wikilink to non-existent file:** Preview renders the link. Clicking it navigates to `/vault/<target>.md` which shows the "File not found" empty state. No error.
- **Suggest card for a line that no longer exists:** Accept still returns the `suggested_text`. The client inserts at the end of the document if `target_line` exceeds the document length. Toast: "Original position changed -- text inserted at end."
- **Network error during save:** Save-status returns to "Unsaved changes." Toast: "Save failed -- try again." Editor content is preserved (no data loss).
- **StorageSync failure after save:** Same as SPEC-045: logged as warning, local write is authoritative. Acceptable Stage 1 posture.
- **File with no content (0 bytes):** Editor renders empty. Preview shows empty. Save of empty content is allowed (writes empty string to disk).

---

## Functional Units (for PR Breakdown)

### FU-1: Migration + suggest cards schema (database-dev)
**Branch:** `feat/SPEC-047-migrations`
**ACs (prerequisites for):** AC-16, AC-17, AC-21, AC-22
- `suggest_cards` table with RLS
- Seed data script for manual testing (optional)

### FU-2: Backend endpoints -- save, backlinks, context, suggest (backend-dev)
**Branch:** `feat/SPEC-047-api`
**Depends on:** FU-1, SPEC-046 FU-1 (vault_router exists)
**ACs:** AC-05 server path, AC-19, AC-20, AC-21, AC-22, AC-23
- `VaultService.find_backlinks` method
- `file_context_service.py` (backlinks, suggest card CRUD, context composition)
- `vault_file_router.py` (PUT /vault/file, GET /vault/backlinks, GET /vault/file/context, suggest endpoints)
- Unit + integration tests

### FU-3: CodeMirror 6 editor + split view (frontend-dev)
**Branch:** `feat/SPEC-047-editor`
**Depends on:** FU-2, SPEC-046 FU-2 (VaultContent, shell layout exist)
**ACs:** AC-01, AC-02, AC-03, AC-04, AC-05 UI, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-18, AC-24
- Install CodeMirror 6 packages, `react-markdown`, `remark-wiki-link`, `yaml`
- `VaultEditor`, `EditorPreviewSplit`, `MarkdownPreview`, `FrontmatterBlock`
- `FileDetailView`, `FileHeaderBar`, `SaveStatus`, `LayoutToggle`
- `extractCitations`, `extractFrontmatter` pure functions
- `useSaveFile` hook
- Wire `VaultContent` to render `FileDetailView` for `.md` files
- Unit tests for components + pure functions
- Playwright tests (written before implementation)

### FU-4: AI context rail + suggest cards UI (frontend-dev)
**Branch:** `feat/SPEC-047-context-rail`
**Depends on:** FU-3
**ACs:** AC-13, AC-14, AC-15, AC-16, AC-17
- `ContextRail` with four sections
- `SuggestCard` component
- `useBacklinks`, `useFileContext`, `useSuggestCardAction` hooks
- Wire "Ask" chip to chat rail with file scope + selection context
- Playwright tests for context rail

**Merge order:** FU-1 -> FU-2 -> FU-3 -> FU-4. Linear.

---

## Resolved Questions (2026-04-21, Tim approved all recommendations)

### OQ-A. Context rail placement — **RESOLVED: sub-panel in center pane**

Keep context rail and chat rail separate. The context rail is file-specific reference material (always visible while editing); the chat rail is conversational (toggled on demand). If screen real estate is tight, the context rail collapses first.

### OQ-B. Scroll sync — **RESOLVED: percentage-based for Stage 1**

Ship percentage-based sync. Good enough for prose-heavy vault content. Source-map sync is a follow-up.

### OQ-C. Suggest card positioning — **RESOLVED: end-of-preview for Stage 1**

Suggest cards render at the end of the preview body, ordered by `target_line`. Precise inline positioning deferred. The card's `target_line` label ("Line 42") gives enough context.

### OQ-D. `react-markdown` dependency — **RESOLVED: add as direct dependency**

Separate from `@assistant-ui/react-markdown`. The two pipelines serve different purposes (document preview vs. chat rendering).

---

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-24)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (VaultService -> API shapes -> TypeScript types -> ARIA selectors)
- [x] Technical decisions cite principles (A1, A4, A8, A12, A14; F1, F2; D1, D3, D4, D5)
- [x] Merge order is explicit and acyclic (FU-1 -> FU-2 -> FU-3 -> FU-4)
- [x] Out-of-scope is explicit and enumerates downstream specs
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs (table)
- [x] Existing infrastructure section enumerates every reused primitive
- [x] Library additions enumerated with sizes and rationale
- [x] VaultEditor component designed for extensibility (SPEC-048 dependency)
- [x] S5 scope binding rules referenced for "Ask" chip
- [x] No overlap with SPEC-045 (VaultService reused, not duplicated) or SPEC-046 (shell/routing reused)
- [x] New open questions surfaced with recommendations
