# SPEC-048: Workflow Editor (S4)

> **Status:** Draft
> **Author:** spec-writer (Claude) on behalf of Tim
> **Created:** 2026-04-21
> **Vision:** [`docs/sdlc/visions/clarity-as-vault.md`](../visions/clarity-as-vault.md)
> **Directive:** [`docs/sdlc/visions/clarity-as-vault-functional.md`](../visions/clarity-as-vault-functional.md) (S4, D1, D4, D5)
> **Depends on:** SPEC-047 (VaultEditor, EditorPreviewSplit, save mechanics, frontmatter handling), SPEC-046 (vault shell, routing, file tree), SPEC-045 (VaultService backend chokepoint)
> **Downstream:** SPEC-054 (orchestration proposals) will use this editor for agent-authored workflows
> **Stage:** Clarity-as-Vault Stage 1 (fourth buildable surface)

---

## Goal

Ship the **workflow editor** (S4) defined in the functional directive -- a specialized file-detail view for `.flow.md` files under `_workflows/`. This reinforces the "workflows are files" principle from the vision doc: the workflow editor IS the file editor (SPEC-047), wrapped with workflow-specific panels and controls.

The architecture is a composition, not a fork:

- SPEC-047 defines `VaultEditor` (CodeMirror 6), `EditorPreviewSplit` (split view), `FileDetailView` (header bar, save mechanics, frontmatter handling).
- This spec wraps `VaultEditor` with three workflow-specific additions: a **workflow list panel** on the left, a **run history panel** on the right, and **workflow-specific toolbar buttons** (save, dry-run, run-now, validation status) in the header.
- When the user navigates to `/vault/_workflows/some-workflow.flow.md`, the vault content router (SPEC-046 `VaultContent`) detects the `_workflows/` path prefix and renders the workflow editor instead of the generic file detail view.

This spec does NOT duplicate the CodeMirror editor, save flow, frontmatter handling, or any other file-editing infrastructure from SPEC-047. It composes that infrastructure with workflow-specific context.

Success looks like: the user navigates to a workflow file, sees the source editor with workflow-specific chrome on both sides, can validate the workflow YAML, trigger a dry run or immediate run, and see the history of past runs with status indicators -- all without leaving the vault.

---

## Existing Infrastructure (what we reuse verbatim)

| Primitive | Location | What we use it for |
|-----------|----------|---------------------|
| VaultEditor | `webApp/src/components/vault/VaultEditor.tsx` (SPEC-047) | CodeMirror 6 source editor for the `.flow.md` file body |
| EditorPreviewSplit | `webApp/src/components/vault/EditorPreviewSplit.tsx` (SPEC-047) | Split view container; workflow files default to source-only (SPEC-047 AC-08) |
| MarkdownPreview | `webApp/src/components/vault/MarkdownPreview.tsx` (SPEC-047) | Preview tab renders the workflow prose |
| FileHeaderBar | `webApp/src/components/vault/FileHeaderBar.tsx` (SPEC-047) | Toolbar with breadcrumb, save status, layout toggle. This spec extends it with workflow-specific slots. |
| SaveStatus / useSaveFile | SPEC-047 | Save mechanics with mtime-based optimistic concurrency |
| extractFrontmatter | `webApp/src/lib/extractFrontmatter.ts` (SPEC-047) | Splits YAML frontmatter from body for validation |
| VaultService | `chatServer/services/vault_service.py` (SPEC-045) | Filesystem read/write for workflow files |
| VaultContent | `webApp/src/components/vault/VaultContent.tsx` (SPEC-046) | Content router that dispatches to the right view by path |
| VaultShell three-pane layout | `webApp/src/layouts/AppShell.tsx` (SPEC-046) | The workflow editor renders inside the center pane of the vault shell |
| WorkflowRunManager | `chatServer/workflows/run_manager.py` (SPEC-036) | `start_run()` dispatches workflow execution; `list_runs()` returns run history |
| TemplateRegistry | `chatServer/workflows/registry.py` (SPEC-036) | `list_templates()` lists available workflows; `get_template()` parses and validates a template |
| template_parser | `chatServer/workflows/template_parser.py` (SPEC-036) | Parses `.flow.md` format into `GraphTemplate` (validates frontmatter + step structure) |
| workflow_runs table | `supabase/migrations/20260407000001_create_workflow_runs.sql` (SPEC-036) | Stores run metadata: id, status, template_name, step_outputs, error, timestamps |
| WorkflowRunsService | `chatServer/services/workflow_runs_service.py` (SPEC-045) | Read-side service for workflow_runs table |
| GET /api/workflows/runs | `chatServer/routers/workflows_router.py` (SPEC-045) | Lists workflow runs filtered by template_name |
| GET /vault/tree | `chatServer/routers/vault_router.py` (SPEC-046) | Provides the file listing used to populate the workflow list panel |
| GET /vault/file | `chatServer/routers/vault_router.py` (SPEC-046) | Fetches file content + mtime |
| PUT /vault/file | `chatServer/routers/vault_file_router.py` (SPEC-047) | Saves file content with mtime concurrency check |
| Auth dependency | `chatServer/dependencies/auth.py` | ES256 JWT for all endpoints |
| Scoped DB client | `chatServer/database/scoped_client.py` | User-scoped access per A8 |
| ChatRail + scope binding | SPEC-049 | Chat scoped to the current workflow file |
| react-resizable-panels | `webApp/package.json` (activated by SPEC-046) | Sub-pane layout within the center pane |
| yaml (npm) | `webApp/package.json` (added by SPEC-047) | Client-side YAML parsing for validation |

---

## Acceptance Criteria

Each AC has a stable ID. Playwright scripts reference these directly. User-visible ACs MUST be queryable by ARIA role/label or stable `data-testid`.

### Routing and layout

- [ ] **AC-01:** Navigating to `/vault/_workflows/<name>.flow.md` renders the workflow editor view instead of the generic file detail view (SPEC-047). The vault content router (`VaultContent`) detects paths matching `_workflows/*.flow.md` and renders `WorkflowEditorView`. The vault shell's left pane (file tree from SPEC-046) remains visible. [F1, D5]
- [ ] **AC-02:** The workflow editor view uses a three-sub-pane layout within the vault shell's center pane (using `react-resizable-panels`): left sub-pane (workflow list, default 220px, min 160px, collapsible), center sub-pane (editor area, fills remaining space), right sub-pane (run history, default 280px, min 200px, collapsible). Each sub-pane has `aria-label` identifying its purpose. [D5, A14]
- [ ] **AC-03:** The workflow list sub-pane and run history sub-pane are each collapsible via toggle buttons. Collapsed state is stored in `localStorage` keys `workflow-editor-list-collapsed` and `workflow-editor-history-collapsed`. When collapsed, a vertical label ("Workflows" or "Run History") with a chevron remains visible. [A14]

### Workflow list panel (left sub-pane)

- [ ] **AC-04:** The workflow list panel has `<nav aria-label="Workflow list">` and displays all `.flow.md` files found under the user's `_workflows/` directory. Each entry shows: workflow name (parsed from the filename, e.g. `morning-briefing` from `morning-briefing.flow.md`), and the description from frontmatter (truncated to one line, 80 chars max). The currently open workflow is visually highlighted. [S4, D4]
- [ ] **AC-05:** Each workflow list entry shows a trigger summary (parsed from the workflow's frontmatter `triggers` field if present, or "Manual" if absent) and a "next run" countdown (computed from the `jobs` table if a scheduled job exists for this template_name, otherwise hidden). Trigger summary and next-run use JetBrains Mono per D4. [S4, D4]
- [ ] **AC-06:** The workflow list panel has a "+ New workflow" button at the bottom with `data-testid="new-workflow-btn"`. Clicking it creates a new `.flow.md` file in `_workflows/` via `POST /vault/workflows/new` with a seed template, navigates to the new file, and opens it in the editor. [S4, A12]
- [ ] **AC-07:** Clicking a workflow entry in the list navigates to `/vault/_workflows/<name>.flow.md` via react-router (SPA navigation, no full-page reload). The editor loads the clicked file. [A14]
- [ ] **AC-08:** The workflow list fetches its data from `GET /vault/workflows/list`. The response includes workflow name, description, trigger summary, and next-run time for each workflow. Data refreshes on mount, on navigation within `_workflows/`, and on 60s polling interval. [A4]

### Center editor area

- [ ] **AC-09:** The center editor area renders SPEC-047's `VaultEditor` (CodeMirror 6) with the workflow file content. The editor defaults to source-only layout per SPEC-047 AC-08. The user can switch to split or preview-only via the layout toggle (inherited from SPEC-047). All SPEC-047 save mechanics, keyboard shortcuts (Cmd+S), save-status indicator, and unsaved-changes blocker apply without modification. [D5]
- [ ] **AC-10:** The center editor area has a header bar (extending SPEC-047's `FileHeaderBar`) with two additional sections beyond the inherited breadcrumb/save-status/layout-toggle: a **validation status** indicator and a **workflow actions** group. The header bar has `role="toolbar" aria-label="Workflow actions"`. [F2]
- [ ] **AC-11:** The **validation status** indicator displays one of three states:
  - "Valid" (green checkmark, `data-testid="validation-valid"`) -- YAML frontmatter parses correctly, all required fields (`name`) present, all steps have `agent` and `description` fields.
  - "Invalid" (red X, `data-testid="validation-invalid"`) -- with a tooltip listing specific validation errors (e.g., "Missing 'name' in frontmatter", "Step 2: missing agent field").
  - "Checking..." (spinner, `data-testid="validation-checking"`) -- during async validation.
  Validation runs on a debounced (800ms) basis after each editor change, using client-side YAML parsing (`yaml` npm package) and the same field expectations as the server-side `template_parser.py`. No server round-trip for validation in Stage 1. [A14]
- [ ] **AC-12:** The **workflow actions** group contains two buttons:
  - **Dry run** (`data-testid="btn-dry-run"`, `aria-label="Dry run workflow"`) -- dispatches a dry run (see AC-14).
  - **Run now** (`data-testid="btn-run-now"`, `aria-label="Run workflow now"`) -- dispatches a live run (see AC-15).
  Both buttons are disabled when validation status is "Invalid" (with tooltip "Fix validation errors before running"). Both buttons show a loading spinner while a run is being dispatched. [S4, A12]

### Dry run and run-now mechanics

- [ ] **AC-13:** Before dispatching either a dry run or a live run, the editor auto-saves any unsaved changes (calls `PUT /vault/file` with current content + mtime). If the save fails (409 conflict or network error), the run is aborted and a toast displays "Save failed -- fix conflicts before running." [A14]
- [ ] **AC-14:** Clicking "Dry run" calls `POST /vault/workflows/dry-run` with `{ template_name: string }`. The backend parses the user's current `.flow.md` file via `template_parser.parse_template()`, validates all step references and parameter definitions, and returns a structured validation result: `{ valid: boolean, errors: string[], steps: Array<{ name: string, agent: string, depends_on: string[], tools: string[] }>, parameters: Array<{ name: string, required: boolean }> }`. No workflow execution occurs. The result is displayed in a modal dialog with `aria-label="Dry run results"`, showing the parsed step graph and any errors. [S4, A1]
- [ ] **AC-15:** Clicking "Run now" calls `POST /vault/workflows/run` with `{ template_name: string, parameters?: object }`. The backend delegates to `WorkflowRunManager.start_run(user_id, template_name, parameters)`. The endpoint returns 202 with `{ run_id: string }`. On success, a toast shows "Workflow started" and the run history panel (AC-18) refreshes to show the new run at the top. On failure (template not found, missing parameters, engine unavailable), an appropriate error toast is shown. [S4, A1, A12]
- [ ] **AC-16:** If the workflow template defines required parameters (parsed from the `## Parameters` table), clicking "Run now" opens a parameter input dialog (`aria-label="Workflow parameters"`) before dispatching. Each required parameter shows a text input with its name and description. Optional parameters show with their default values pre-filled. The dialog has "Run" and "Cancel" buttons. [S4, A14]

### Run history panel (right sub-pane)

- [ ] **AC-17:** The run history panel has `<section aria-label="Run history">` and displays past runs for the currently open workflow, fetched from `GET /api/workflows/runs/detailed?template_name=<name>&limit=25`. [S4]
- [ ] **AC-18:** Each run entry displays: timestamp (relative, e.g. "12 min ago", with full ISO timestamp in `title` attribute), status indicator (colored dot -- green for completed, red for failed, amber for running, grey for cancelled, blue for waiting_for_approval), duration (computed as `completed_at - started_at`, displayed as "42s" or "2m 18s"; shows "running" for in-progress runs), and current step name for running workflows. Each entry has `role="listitem"` and `aria-label="Run from <timestamp>, status: <status>"`. [S4, D4]
- [ ] **AC-19:** Clicking a run entry expands it inline to show: step outputs (from `step_outputs` JSONB), error message (if failed), and parameter values used. The expanded view has `aria-label="Run details for <run_id>"`. Only one run entry is expanded at a time. [S4]
- [ ] **AC-20:** The bottom of the run history panel shows a **last output preview** area with `aria-label="Last run output"`. For the most recent completed run, it displays the final step's output text (from `step_outputs`, last step by dependency order), truncated to 500 characters with a "Show full output" toggle. If no completed runs exist, shows "No completed runs yet." [S4]
- [ ] **AC-21:** The run history panel refreshes automatically: on mount, after dispatching a run (AC-15), and on a 15s polling interval while a run with status `running` or `pending` exists. When no active runs exist, polling interval relaxes to 60s. The `useWorkflowRuns` hook manages this adaptive polling via React Query's `refetchInterval`. [A4, A14]

### Workflow list data endpoint (new)

- [ ] **AC-22:** `GET /vault/workflows/list` returns `{ workflows: Array<{ name: string, filename: string, description: string, trigger_summary: string, next_run_at: string | null }> }`. Implementation: reads `_workflows/` directory via VaultService, parses YAML frontmatter of each `.flow.md` file for `name` and `description`, checks the `jobs` table for the next scheduled run per template_name. Auth required. Returns empty array if `_workflows/` does not exist. [A1, A8]

### New workflow creation endpoint

- [ ] **AC-23:** `POST /vault/workflows/new` accepts `{ name: string }` (alphanumeric + hyphens, 1-60 chars). Creates `_workflows/<name>.flow.md` with a seed template containing minimal valid frontmatter (`name`, `description: ""`, `version: 1`, `default_gate_policy: none`) and an empty steps section. Returns `{ path: string }` with the vault-relative path. Returns 409 if a file with that name already exists. Auth required. Path safety enforced by VaultService._resolve. [A1, A8, A12]

### Dry-run endpoint (new)

- [ ] **AC-24:** `POST /vault/workflows/dry-run` accepts `{ template_name: string }`. Reads the user's `.flow.md` via VaultService (user override checked first, then system dir per the TemplateRegistry shadow pattern), parses it with `template_parser.parse_template()`, and returns the structured validation result (AC-14 shape). Does not execute the workflow. Returns 404 if the template is not found. Returns 422 with error details if parsing fails. Auth required. [A1, A8]

### Run-now endpoint (new)

- [ ] **AC-25:** `POST /vault/workflows/run` accepts `{ template_name: string, parameters?: object }`. Delegates to `WorkflowRunManager.start_run(user_id, template_name, parameters)`. Returns 202 with `{ run_id: string }`. Returns 404 if template not found. Returns 422 if required parameters are missing (with `{ missing: string[] }`). Returns 503 if the workflow engine is unavailable. Auth required. [A1, A8, A12]

### Auth and isolation

- [ ] **AC-26:** All new endpoints require authentication. User B cannot list, create, dry-run, or execute User A's workflows. User B cannot see User A's run history. Integration tests cover cross-user isolation for every new endpoint. [A8]

### Accessibility

- [ ] **AC-27:** The workflow editor view is navigable by keyboard: Tab cycles between the three sub-panes (workflow list, editor, run history), then within each sub-pane's interactive elements. Arrow keys navigate workflow list entries and run history entries. Cmd+S saves (inherited from SPEC-047). The three-sub-pane layout uses `react-resizable-panels` keyboard resize support. [F2, A14]

---

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `webApp/src/components/vault/WorkflowEditorView.tsx` | Top-level workflow editor component. Composes three sub-panes: WorkflowListPanel, center editor (SPEC-047 VaultEditor + extended header bar), and RunHistoryPanel. |
| `webApp/src/components/vault/WorkflowListPanel.tsx` | Left sub-pane: lists workflows from `_workflows/`, shows trigger/next-run, "+ new" button. |
| `webApp/src/components/vault/RunHistoryPanel.tsx` | Right sub-pane: lists past runs, expandable detail, last-output preview. |
| `webApp/src/components/vault/RunHistoryEntry.tsx` | Single run entry with status dot, timestamp, duration, expandable detail. |
| `webApp/src/components/vault/WorkflowHeaderExtension.tsx` | Extends FileHeaderBar with validation status + dry-run/run-now buttons. Composed into the header bar via a slot/children prop from SPEC-047. |
| `webApp/src/components/vault/ValidationStatus.tsx` | Validation indicator: valid/invalid/checking states with tooltip for errors. |
| `webApp/src/components/vault/DryRunResultsDialog.tsx` | Modal dialog displaying parsed step graph and validation errors from dry-run. |
| `webApp/src/components/vault/ParameterInputDialog.tsx` | Modal dialog for entering required/optional workflow parameters before "Run now." |
| `webApp/src/components/vault/LastOutputPreview.tsx` | Bottom section of run history panel showing truncated last-run output. |
| `webApp/src/api/hooks/useWorkflowEditorHooks.ts` | `useWorkflowList`, `useWorkflowRuns` (adaptive polling), `useCreateWorkflow`, `useDryRun`, `useRunWorkflow`. [A4] |
| `webApp/src/api/types/workflowEditor.ts` | `WorkflowListItem`, `WorkflowRunEntry`, `DryRunResult`, `RunWorkflowRequest`, `RunWorkflowResponse`, `CreateWorkflowRequest` types. |
| `webApp/src/lib/validateWorkflowTemplate.ts` | Client-side validation of `.flow.md` content: parse YAML frontmatter, check required fields, validate step structure. Returns `{ valid: boolean, errors: string[] }`. Mirrors `template_parser.py` expectations. |
| `chatServer/routers/workflow_editor_router.py` | `GET /vault/workflows/list`, `POST /vault/workflows/new`, `POST /vault/workflows/dry-run`, `POST /vault/workflows/run`. Thin routers per A1. |
| `chatServer/services/workflow_editor_service.py` | List workflows with metadata, create from seed template, dry-run validation, run dispatch. Composes VaultService + TemplateRegistry + WorkflowRunManager. |
| `tests/unit/services/test_workflow_editor_service.py` | List workflows (parsing frontmatter, handling missing files), create workflow (seed template, name collision), dry-run (valid/invalid templates), run dispatch delegation. |
| `tests/integration/test_workflow_editor_api.py` | Auth required, cross-user isolation, list/create/dry-run/run round-trips, 409 on duplicate name, 422 on invalid template. |
| `tests/uat/playwright/test_spec_048_workflow_editor.py` | One Playwright function per user-visible AC. Written BEFORE frontend implementation. |
| `webApp/src/components/vault/WorkflowListPanel.test.tsx` | Renders workflow list, handles empty state, "+ new" button fires create. |
| `webApp/src/components/vault/RunHistoryPanel.test.tsx` | Renders runs, adaptive polling, expandable entries, last-output preview. |
| `webApp/src/lib/validateWorkflowTemplate.test.ts` | Valid template passes, missing name fails, missing agent in step fails, malformed YAML fails. |

### Files to Modify

| File | Change |
|------|--------|
| `webApp/src/components/vault/VaultContent.tsx` (SPEC-046) | Add path detection: when path matches `_workflows/*.flow.md`, render `WorkflowEditorView` instead of `FileDetailView`. |
| `webApp/src/components/vault/FileHeaderBar.tsx` (SPEC-047) | Add an optional `extension` slot (React node) that `WorkflowHeaderExtension` renders into. Default: empty. This keeps FileHeaderBar generic. |
| `chatServer/main.py` | Register `workflow_editor_router`. |
| `chatServer/services/workflow_runs_service.py` | Add `list_runs_detailed(template_name, limit)` method that also selects `step_outputs`, `parameters`, `started_at`, `completed_at` for the run detail expansion (AC-19). The existing `list_runs` method selects a subset of columns; the new method selects all. |
| `chatServer/routers/workflows_router.py` | Add `GET /api/workflows/runs/detailed` endpoint that delegates to `WorkflowRunsService.list_runs_detailed`. |

### Out of Scope

- **Workflow diagram view** -- the functional directive mentions an "Edit | Preview | Diagram" tab set. The diagram tab is explicitly deferred past Stage 1 per the functional doc ("markdown + preview only in Stage 1"). This spec ships Edit and Preview tabs only (inherited from SPEC-047's layout toggle).
- **Agent-authored workflows** -- SPEC-054 (orchestration proposals) covers the agent proposing new workflows via the approval lane. This spec's UI can display agent-authored workflows once they land as `.flow.md` files, but the authoring flow is out of scope.
- **Workflow scheduling UI** -- editing cron triggers, setting up scheduled jobs from the UI. Stage 1 scheduling is configured via `user_preferences` (SPEC-045) or direct DB edits. A scheduling UI is a later spec.
- **Workflow version history / diffing** -- git log for workflow files. Deferred alongside SPEC-047's History chip.
- **Real-time run progress streaming (SSE/WebSocket)** -- polling suffices for Stage 1 (AC-21). Push updates arrive when another surface also needs EventSource.
- **Workflow duplication / import / export** -- later spec.
- **Step-level execution controls** -- pause/resume/skip individual steps. The workflow engine (SPEC-036) supports gate-based approval, but step-level UI controls are deferred.
- **Trigger editing UI** -- the triggers field is visible and editable as YAML frontmatter in the source editor, but there is no structured trigger picker UI.
- **Non-.flow.md files in `_workflows/`** -- the workflow list panel only shows `.flow.md` files. Other files (e.g. `prompts/`) are accessible through the vault browser but not the workflow list.

---

## Technical Approach

### 1. Routing -- VaultContent path detection

`VaultContent` (SPEC-046) currently dispatches to `FileDetailView` for `.md` files. This spec adds a path check before that dispatch:

```tsx
// In VaultContent.tsx
const isWorkflowFile = path.startsWith('_workflows/') && path.endsWith('.flow.md');

if (isWorkflowFile) {
  return <WorkflowEditorView path={path} />;
}
// ... existing FileDetailView for other .md files
```

The detection is simple string matching. The `_workflows/` prefix is the convention from the vision doc. `.flow.md` is the file extension used by all existing workflow templates.

### 2. WorkflowEditorView -- composition over duplication

The `WorkflowEditorView` composes SPEC-047 components, adding workflow-specific panels on the sides:

```tsx
const WorkflowEditorView: React.FC<{ path: string }> = ({ path }) => {
  const templateName = extractTemplateName(path);
  // "morning-briefing" from "_workflows/morning-briefing.flow.md"

  return (
    <PanelGroup direction="horizontal" aria-label="Workflow editor">
      <Panel defaultSize={18} minSize={12} collapsible
             aria-label="Workflow list">
        <WorkflowListPanel currentPath={path} />
      </Panel>
      <PanelResizeHandle />
      <Panel defaultSize={55} minSize={30}>
        {/* Reuse SPEC-047 editor infrastructure */}
        <FileHeaderBar
          extension={
            <WorkflowHeaderExtension templateName={templateName} />
          }
        >
          {/* breadcrumb, save status, layout toggle -- inherited */}
        </FileHeaderBar>
        <EditorPreviewSplit
          path={path}
          defaultLayout="source"
        />
      </Panel>
      <PanelResizeHandle />
      <Panel defaultSize={27} minSize={15} collapsible
             aria-label="Run history">
        <RunHistoryPanel templateName={templateName} />
      </Panel>
    </PanelGroup>
  );
};
```

Key design choice: `WorkflowEditorView` does not re-implement the editor. It uses the same `EditorPreviewSplit` (which contains `VaultEditor` + `MarkdownPreview`) and the same `FileHeaderBar` as the generic file detail view. The only addition is the workflow-specific extension slot and the flanking panels.

### 3. FileHeaderBar extension slot

SPEC-047's `FileHeaderBar` is modified to accept an optional `extension` prop:

```tsx
interface FileHeaderBarProps {
  // ... existing props
  extension?: React.ReactNode;
}

// In FileHeaderBar render:
<div role="toolbar" aria-label="File actions">
  <Breadcrumb ... />
  <SaveStatus ... />
  <LayoutToggle ... />
  {/* Action chips: History, Share, Ask */}
  {extension}
</div>
```

For generic files, `extension` is undefined (no change to existing behavior). For workflow files, `WorkflowHeaderExtension` renders the validation indicator and action buttons.

### 4. Client-side validation -- `validateWorkflowTemplate`

A pure function that mirrors the server-side `template_parser.py` validation rules:

```typescript
interface ValidationResult {
  valid: boolean;
  errors: string[];
}

function validateWorkflowTemplate(content: string): ValidationResult {
  const errors: string[] = [];
  const { frontmatter, body } = extractFrontmatter(content);

  if (!frontmatter) {
    errors.push('Missing YAML frontmatter (must start with ---)');
    return { valid: false, errors };
  }

  let parsed: Record<string, unknown>;
  try {
    parsed = YAML.parse(frontmatter);
  } catch (e) {
    errors.push('Invalid YAML in frontmatter');
    return { valid: false, errors };
  }

  if (!parsed.name) {
    errors.push("Missing required field 'name' in frontmatter");
  }

  // Validate steps: look for ### step-N: Name pattern
  const stepPattern = /^###\s+step-\d+:\s+(.+)$/gm;
  const fieldPattern = /^-\s+\*\*(\w+):\*\*\s+(.+)$/gm;
  // ... extract step sections and check for 'agent' and 'description' fields

  return { valid: errors.length === 0, errors };
}
```

The function mirrors `template_parser.py`'s `_FRONTMATTER_RE`, `_STEP_HEADER_RE`, and `_FIELD_RE` patterns. Debounced at 800ms after each editor change to avoid validation churn during active typing.

### 5. Dry-run endpoint -- server-side parse + validate

```python
# workflow_editor_router.py
@router.post("/vault/workflows/dry-run")
async def dry_run_workflow(
    payload: DryRunRequest,
    user_id: str = Depends(get_current_user),
    service: WorkflowEditorService = Depends(get_workflow_editor_service),
):
    result = await service.dry_run(user_id, payload.template_name)
    return result
```

```python
# workflow_editor_service.py
class WorkflowEditorService:
    async def dry_run(self, user_id: str, template_name: str) -> dict:
        try:
            template = await self._registry.get_template(
                template_name, user_id
            )
        except TemplateNotFoundError:
            raise HTTPException(404, "Template not found")
        except TemplateParseError as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "steps": [],
                "parameters": [],
            }

        return {
            "valid": True,
            "errors": [],
            "steps": [
                {
                    "name": s.name,
                    "agent": s.agent,
                    "depends_on": s.depends_on,
                    "tools": s.tools,
                }
                for s in template.steps
            ],
            "parameters": [
                {
                    "name": p.name,
                    "required": p.required,
                    "description": p.description,
                }
                for p in template.parameters
            ],
        }
```

The dry run reuses `TemplateRegistry.get_template()` which already handles user-override shadowing and YAML + step parsing via `template_parser.py`. No new parsing logic needed on the server.

### 6. Run-now endpoint -- delegates to WorkflowRunManager

```python
@router.post("/vault/workflows/run", status_code=202)
async def run_workflow(
    payload: RunWorkflowRequest,
    user_id: str = Depends(get_current_user),
    service: WorkflowEditorService = Depends(get_workflow_editor_service),
):
    run_id = await service.run_workflow(
        user_id, payload.template_name, payload.parameters or {},
    )
    return {"run_id": run_id}
```

The service delegates to `WorkflowRunManager.start_run()`. This is the same code path used by `POST /today/regenerate` (SPEC-045 AC-17) and the `dispatch_workflow` tool. No new execution path.

### 7. Workflow list endpoint

Implementation reads `_workflows/` via VaultService, parses frontmatter of each `.flow.md` file, and checks the `jobs` table for next-scheduled runs:

```python
async def list_workflows(self, user_id: str) -> list[dict]:
    workflows_dir = "_workflows"
    try:
        entries = await self._vault.list_folder(user_id, workflows_dir)
    except HTTPException:
        return []  # _workflows/ does not exist

    result = []
    for entry in entries:
        if not entry["name"].endswith(".flow.md"):
            continue
        content = await self._vault.read_file(user_id, entry["path"])
        fm = self._parse_frontmatter_only(content)
        template_name = entry["name"].replace(".flow.md", "")
        next_run = await self._get_next_scheduled_run(
            user_id, template_name
        )
        result.append({
            "name": fm.get("name", template_name),
            "filename": entry["name"],
            "description": fm.get("description", ""),
            "trigger_summary": self._format_triggers(fm),
            "next_run_at": next_run,
        })
    return result
```

`_parse_frontmatter_only` extracts only the YAML frontmatter (does not parse steps -- faster for listing). `_get_next_scheduled_run` queries the `jobs` table for the next pending job with matching `template_name` in its input JSONB.

### 8. New workflow seed template

The `POST /vault/workflows/new` endpoint creates a minimal valid `.flow.md`:

```markdown
---
name: {user-provided-name}
description: ""
version: 1
default_gate_policy: none
---

# {User Provided Name}

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|

## Steps

### step-1: First step
- **agent:** (specify agent)
- **depends_on:** []
- **tools:** []
- **description:** Describe what this step does.
- **gate:** none
```

### 9. Run history -- adaptive polling

The `useWorkflowRuns` hook uses React Query with dynamic `refetchInterval`:

```typescript
function useWorkflowRuns(templateName: string) {
  return useQuery({
    queryKey: ['workflow-runs', templateName],
    queryFn: () => fetchWorkflowRuns(templateName, 25),
    refetchInterval: (query) => {
      const hasActiveRun = query.state.data?.some(
        (r: WorkflowRunEntry) =>
          r.status === 'running' || r.status === 'pending'
      );
      return hasActiveRun ? 15_000 : 60_000;
    },
    staleTime: 10_000,
  });
}
```

### 10. Extended WorkflowRunsService

The existing `WorkflowRunsService.list_runs()` selects a subset of columns (`_RUN_COLUMNS` = `id,template_name,status,current_step,error,started_at,completed_at,created_at`). The run history panel needs `step_outputs` and `parameters` for the expanded detail view (AC-19). A new method `list_runs_detailed()` selects all columns:

```python
_DETAILED_COLUMNS = (
    "id,template_name,status,current_step,error,"
    "parameters,step_outputs,started_at,completed_at,created_at"
)

async def list_runs_detailed(
    self,
    *,
    template_name: Optional[str] = None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    query = (
        self._db.table("workflow_runs")
        .select(_DETAILED_COLUMNS)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if template_name is not None:
        query = query.eq("template_name", template_name)
    result = await query.execute()
    return list(result.data or [])
```

A new router endpoint `GET /api/workflows/runs/detailed` exposes this. The existing `GET /api/workflows/runs` endpoint remains unchanged (used by SPEC-045's `useRegenerationStatus`).

### 11. Frontend types

```typescript
// api/types/workflowEditor.ts

export interface WorkflowListItem {
  name: string;
  filename: string;
  description: string;
  trigger_summary: string;
  next_run_at: string | null;
}

export interface WorkflowRunEntry {
  id: string;
  template_name: string;
  status: 'pending' | 'running' | 'waiting_for_approval'
    | 'completed' | 'failed' | 'cancelled';
  current_step: string;
  error: string | null;
  parameters: Record<string, unknown>;
  step_outputs: Record<string, string>;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface DryRunResult {
  valid: boolean;
  errors: string[];
  steps: Array<{
    name: string;
    agent: string;
    depends_on: string[];
    tools: string[];
  }>;
  parameters: Array<{
    name: string;
    required: boolean;
    description: string;
  }>;
}

export interface RunWorkflowRequest {
  template_name: string;
  parameters?: Record<string, unknown>;
}

export interface RunWorkflowResponse {
  run_id: string;
}

export interface CreateWorkflowRequest {
  name: string;
}

export interface CreateWorkflowResponse {
  path: string;
}
```

### 12. No new library additions

This spec introduces no new npm or Python packages. All required libraries are already installed by prior specs:

- `react-resizable-panels` (SPEC-046)
- `yaml` (SPEC-047)
- `codemirror` and extensions (SPEC-047)
- `react-markdown` + `remark-gfm` + `remark-wiki-link` (SPEC-047)
- Radix UI dialog primitives (existing)

---

## Testing Requirements

### Unit Tests (required)

- `test_workflow_editor_service.py`: list_workflows parses frontmatter, handles empty `_workflows/` dir, handles malformed frontmatter gracefully (returns entry with empty description); create_workflow generates valid seed template, rejects duplicate names (409), rejects invalid names (non-alphanumeric); dry_run returns parsed steps on valid template, returns errors on invalid template; run dispatches to WorkflowRunManager.
- `test_workflow_runs_service_detailed.py`: list_runs_detailed returns all columns including step_outputs and parameters; template_name filter works; limit applies.
- `validateWorkflowTemplate.test.ts`: valid template passes; missing frontmatter fails; malformed YAML fails; missing `name` fails; step missing `agent` fails; step missing `description` fails; empty steps section passes (valid, zero steps); multiple errors accumulated correctly.
- `WorkflowListPanel.test.tsx`: renders workflow entries, empty state ("No workflows -- create one"), "+ New workflow" button calls mutation, current workflow highlighted.
- `RunHistoryPanel.test.tsx`: renders run entries with correct status dots, expands/collapses entries, last output preview truncates at 500 chars, adaptive polling interval changes with active runs.
- `ValidationStatus.test.tsx`: renders three states correctly (valid/invalid/checking), tooltip shows errors on invalid.

### Integration Tests (required)

- `test_workflow_editor_api.py`:
  - `GET /vault/workflows/list`: auth required, returns workflow entries with metadata, empty for user with no `_workflows/`, cross-user isolation.
  - `POST /vault/workflows/new`: creates file on disk, returns path, 409 on duplicate, rejects invalid names, auth required.
  - `POST /vault/workflows/dry-run`: returns parsed steps for valid template, returns errors for invalid template, 404 for missing template, auth required.
  - `POST /vault/workflows/run`: returns 202 + run_id, workflow_runs row created, 404 for missing template, 422 for missing required parameters, auth required, cross-user isolation.
  - `GET /api/workflows/runs/detailed`: returns step_outputs and parameters, template_name filter, auth required.

### UI Acceptance Tests (Playwright -- written BEFORE implementation)

Script: `tests/uat/playwright/test_spec_048_workflow_editor.py`. One function per user-visible AC. Selectors target ARIA role/label or `data-testid`.

| AC | Flow / Service Test | UI Test (Playwright) |
|----|---------------------|---------------------|
| AC-01 | -- | `test_ac_01_workflow_route_renders_editor` |
| AC-02 | -- | `test_ac_02_three_sub_pane_layout` |
| AC-03 | -- | `test_ac_03_panels_collapsible` |
| AC-04 | -- | `test_ac_04_workflow_list_entries` |
| AC-05 | -- | `test_ac_05_trigger_and_next_run` |
| AC-06 | `test_create_workflow_endpoint` | `test_ac_06_new_workflow_button` |
| AC-07 | -- | `test_ac_07_list_click_navigates` |
| AC-08 | `test_list_workflows_endpoint` | `test_ac_08_workflow_list_fetches_data` |
| AC-09 | -- | `test_ac_09_editor_renders_source_default` |
| AC-10 | -- | `test_ac_10_extended_header_bar` |
| AC-11 | -- | `test_ac_11_validation_status_states` |
| AC-12 | -- | `test_ac_12_action_buttons_disabled_on_invalid` |
| AC-13 | -- | `test_ac_13_auto_save_before_run` |
| AC-14 | `test_dry_run_endpoint` | `test_ac_14_dry_run_dialog` |
| AC-15 | `test_run_workflow_endpoint` | `test_ac_15_run_now_dispatches` |
| AC-16 | -- | `test_ac_16_parameter_dialog` |
| AC-17 | -- | `test_ac_17_run_history_renders` |
| AC-18 | -- | `test_ac_18_run_entry_status_dots` |
| AC-19 | -- | `test_ac_19_run_entry_expandable` |
| AC-20 | -- | `test_ac_20_last_output_preview` |
| AC-21 | -- | `test_ac_21_adaptive_polling` |
| AC-22 | `test_list_workflows_endpoint` | -- |
| AC-23 | `test_create_workflow_endpoint` | -- |
| AC-24 | `test_dry_run_endpoint` | -- |
| AC-25 | `test_run_workflow_endpoint` | -- |
| AC-26 | `test_cross_user_isolation` | -- |
| AC-27 | -- | `test_ac_27_keyboard_navigation` |

### Manual Verification (UAT)

1. Navigate to `/vault/_workflows/regenerate-today.flow.md` -- verify the workflow editor renders with three sub-panes (workflow list, editor, run history).
2. Verify the workflow list shows all existing workflows (morning-briefing, evening-briefing, draft-reply, email-triage, regenerate-today).
3. Click a different workflow in the list -- verify SPA navigation, editor loads the new file.
4. Edit the currently open workflow (add a comment) -- verify save status changes to "Unsaved changes." Press Cmd+S -- verify it saves.
5. Verify validation status shows "Valid" for unmodified system workflows. Delete the `name` field from frontmatter -- verify status changes to "Invalid" with tooltip explaining the error.
6. Click "Dry run" on a valid workflow -- verify the dialog shows parsed steps and parameters.
7. Click "Run now" on `regenerate-today` -- verify toast "Workflow started", run appears at top of run history panel, status dot is amber (running).
8. Wait for run to complete -- verify status dot changes to green, duration appears, run history polling is working.
9. Click the completed run entry -- verify it expands to show step outputs.
10. Verify last output preview at bottom of run history shows the final step output.
11. Click "+ New workflow" -- verify new file created, navigated to it, editor shows seed template, validation status shows "Invalid" (agent field is placeholder).
12. Collapse the workflow list panel -- verify vertical "Workflows" label, reload page, verify collapsed state persists.
13. Collapse the run history panel -- same persistence check.
14. On a workflow with required parameters, click "Run now" -- verify parameter input dialog appears before dispatch.
15. Sign in as a second user -- verify no cross-user workflow or run history leakage.
16. `curl` the dry-run endpoint with a non-existent template -- verify 404.

---

## Edge Cases

- **`_workflows/` directory does not exist:** `GET /vault/workflows/list` returns an empty array. The workflow list panel shows "No workflows -- create your first." Creating a workflow via `POST /vault/workflows/new` creates the directory first.
- **Malformed YAML in a listed workflow:** `list_workflows` catches the parse error, sets `description` to "" and `trigger_summary` to "Parse error", and continues listing other workflows. The entry is still navigable; opening it shows the validation errors in the editor.
- **Workflow file changed on disk while editor is open (agent or Obsidian edit):** Same behavior as SPEC-047: next save attempt returns 409. User sees "File was modified elsewhere" toast with a Reload action.
- **Run-now on a workflow that the engine cannot find:** The `WorkflowRunManager` uses `TemplateRegistry.get_template()` which checks user dir then system dir. If the user just created the file but it has not been saved yet, the auto-save in AC-13 fires first. If the registry cache is stale (300s TTL), the file-on-disk read happens on cache miss.
- **Concurrent run dispatches (double-click):** The "Run now" button shows a loading spinner and is disabled during dispatch (AC-12). A second click is blocked.
- **Workflow with zero steps:** Valid per the template parser (empty steps list). Dry run returns `{ valid: true, steps: [], ... }`. Running it creates a workflow_runs row that immediately completes (the graph has no nodes).
- **Very long step output in history:** Step outputs are JSONB (unbounded). The inline expanded view truncates each step output to 2000 characters with "Show full" toggle. The last-output preview truncates to 500 characters.
- **Template name contains special characters:** `POST /vault/workflows/new` validates the name: only `[a-z0-9-]`, 1-60 chars. Rejects anything else with 422.
- **WorkflowRunManager unavailable (not initialized):** `POST /vault/workflows/run` catches `RuntimeError` from `get_template_registry()` or the manager and returns 503 "Workflow engine unavailable."
- **Run history for a workflow with no runs:** Panel shows "No runs yet. Click 'Run now' to start." Last output preview shows "No completed runs yet."
- **File tree shows `_workflows/` but also individual files:** The vault shell's file tree (SPEC-046) still shows the `_workflows/` folder and its contents. The workflow list panel is an additional, workflow-focused navigation surface. Clicking a `.flow.md` file in either surface navigates to the workflow editor.
- **System workflows vs user workflows:** The workflow list shows files from the user's `_workflows/` directory only. System workflows (in `/data/config/system/workflows/`) are not listed until the user creates a local override. However, the "Run now" and "Dry run" endpoints use TemplateRegistry which checks user then system, so a user can run system workflows even if they do not have local copies -- they just need to specify the template_name directly (e.g. via chat or API). The workflow list is a convenience surface for user-local files.
- **Auto-save fails before run dispatch:** The run is aborted entirely. Toast: "Save failed -- fix conflicts before running." The user must resolve the save conflict (reload) and try again.
- **Browser tab closed during a run:** The `workflow_runs` row persists in the DB with status `running`. On the next visit to the workflow editor, the run history panel shows the run. If the background task completed or failed, the status reflects that. If the server restarted mid-run, the status remains `running` (orphaned) -- a cleanup concern for a later spec.
- **Navigating away from workflow editor with unsaved changes:** The unsaved-changes blocker from SPEC-047 (AC-06) applies. The user sees the confirmation dialog before navigation proceeds.

---

## Functional Units (for PR Breakdown)

### FU-1: Backend -- workflow editor endpoints (backend-dev)
**Branch:** `feat/SPEC-048-api`
**Depends on:** SPEC-047 FU-2 (PUT /vault/file exists), SPEC-046 FU-1 (vault_router exists with list_folder)
**ACs:** AC-08, AC-14, AC-15, AC-16, AC-22, AC-23, AC-24, AC-25, AC-26
- `workflow_editor_service.py` (list, create, dry-run, run)
- `workflow_editor_router.py` (four endpoints)
- Extended `WorkflowRunsService.list_runs_detailed()` + detailed runs endpoint in `workflows_router.py`
- Unit tests + integration tests

### FU-2: Frontend -- workflow editor view + panels (frontend-dev)
**Branch:** `feat/SPEC-048-ui`
**Depends on:** FU-1, SPEC-047 FU-3 (VaultEditor, EditorPreviewSplit, FileHeaderBar exist)
**ACs:** AC-01 through AC-13, AC-17 through AC-21, AC-27
- `WorkflowEditorView`, `WorkflowListPanel`, `RunHistoryPanel`, `RunHistoryEntry`, `WorkflowHeaderExtension`, `ValidationStatus`, `LastOutputPreview`
- `validateWorkflowTemplate.ts` pure function
- `useWorkflowEditorHooks.ts` (React Query hooks with adaptive polling)
- Types in `workflowEditor.ts`
- VaultContent routing change
- FileHeaderBar extension slot modification
- Component tests + Playwright tests (written before implementation)

### FU-3: Frontend -- dry-run/run-now dialogs + parameter input (frontend-dev)
**Branch:** `feat/SPEC-048-dialogs`
**Depends on:** FU-2
**ACs:** AC-14 UI, AC-15 UI, AC-16
- `DryRunResultsDialog`, `ParameterInputDialog`
- Auto-save-before-run logic (AC-13)
- Playwright tests for dialog flows

**Merge order:** FU-1 -> FU-2 -> FU-3. Linear.

---

## Resolved Questions (2026-04-21, Tim approved all recommendations)

### OQ-A. System workflows in the workflow list — **RESOLVED: user-local only for Stage 1**

Show only files from the user's `_workflows/`. System workflows appear once overridden or seeded. A future spec can add a "built-in workflows" section.

### OQ-B. Trigger summary source — **RESOLVED: jobs table**

Show trigger info from the jobs table (AC-05). No `triggers` field in frontmatter. If no job exists, show "Manual."

### OQ-C. Seeding `_workflows/` for new users — **RESOLVED: no seeding**

The workflow editor works fine with an empty list (AC-06 provides the create path). System workflows are runnable without local copies. Seeding belongs in an onboarding spec.

---

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-27)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (VaultService -> API shapes -> TypeScript types -> ARIA selectors)
- [x] Technical decisions cite principles (A1, A4, A8, A12, A14; F1, F2; D4, D5)
- [x] Merge order is explicit and acyclic (FU-1 -> FU-2 -> FU-3)
- [x] Out-of-scope is explicit and enumerates deferred features
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs (table)
- [x] Existing infrastructure section enumerates every reused primitive
- [x] No duplication of SPEC-047 editor infrastructure (composition, not fork)
- [x] S4 functional directive features mapped: workflow list (AC-04/05), editor with save/dry-run/run-now (AC-09-16), run history (AC-17-21)
- [x] Diagram tab explicitly deferred per functional doc
- [x] New open questions surfaced with recommendations
- [x] No overlap with SPEC-045 (VaultService, regeneration reused), SPEC-046 (routing, file tree reused), SPEC-047 (editor components reused), or SPEC-049 (chat scoping reused)
