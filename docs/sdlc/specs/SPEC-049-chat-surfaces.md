# SPEC-049: Chat Surfaces (S5 -- right rail, Cmd+K palette, inline ask chip)

> **Status:** Draft
> **Author:** spec-writer (Claude) on behalf of Tim
> **Created:** 2026-04-21
> **Vision:** [`docs/sdlc/visions/clarity-as-vault.md`](../visions/clarity-as-vault.md)
> **Directive:** [`docs/sdlc/visions/clarity-as-vault-functional.md`](../visions/clarity-as-vault-functional.md) (D3, S5; chat integration notes in S1, S2, S3, S4)
> **Depends on:** SPEC-046 (vault shell provides the three-pane layout and right-pane container), SPEC-045 (existing ChatPanel, useChatStore)
> **Stage:** Clarity-as-Vault Stage 1

---

## Goal

Ship the three reachability paths for chat defined in the functional directive (D3, S5): the right-rail scoped chat panel (refactored from the existing slide-in into the SPEC-046 right pane), the Cmd+K command palette (new, `cmdk`), and the inline "ask about this" chip (new component consumed by S1/S3). None of these paths are standalone pages -- chat is always a mode layered over the current surface.

This spec also defines and implements the **scope binding contract** -- the rules governing what context chat inherits based on where it was opened. Every other surface (S1 Today, S2 vault browser, S3 file detail, S4 workflow editor) consumes this contract; it is defined here and only here.

Stage 1 chat can answer questions, redirect the system (edit agent/workflow markdown via approval lane for structural changes, immediately for tone/copy), surface proposals, and trigger workflow runs. It cannot take outbound actions (emails, calendar events, etc.) per the Stage 1 read-only contract.

Success looks like: from any surface in the app, the user can reach the agent in one gesture (Cmd+K or click), and the agent knows what the user is looking at without being told.

---

## Existing Infrastructure (what we reuse verbatim)

| Primitive | Location | What we use it for |
|-----------|----------|---------------------|
| ChatPanel | `webApp/src/components/ChatPanel.tsx` | Current chat implementation using `@assistant-ui/react`. Refactored in-place -- same internal logic, new container and scope awareness. |
| useChatStore | `webApp/src/stores/useChatStore.ts` | Zustand store for chat state (messages, session, panel open/close). Extended with `scope` field. |
| @assistant-ui/react | `webApp/package.json` (installed) | Thread rendering, Composer, external store runtime. Unchanged. |
| MessageHeader | `webApp/src/components/ui/chat/MessageHeader.tsx` | Chat header component. Extended with scope indicator. |
| react-resizable-panels | `webApp/package.json` (installed, activated by SPEC-046) | Three-pane layout. Chat rail is the right pane. |
| ChatRequest model | `chatServer/models/chat.py` | `agent_name`, `message`, `session_id`. Extended with optional `scope` field. |
| POST /api/chat | `chatServer/main.py` | Chat endpoint. Passes scope to agent context when present. |
| VaultService | `chatServer/services/vault_service.py` (SPEC-045) | Path resolution for scope validation. |
| TopBar | `webApp/src/components/navigation/TopBar.tsx` | Hosts the Cmd+K keyboard shortcut hint. |
| ConversationList | `webApp/src/components/features/Conversations/ConversationList.tsx` | Existing conversation switcher inside ChatPanel. Preserved. |
| ApprovalsBadge | `webApp/src/components/today/ApprovalsBadge.tsx` | TopBar badge. Unaffected. |

---

## Scope Binding Contract

This is the canonical definition of chat scope. Other specs (S1, S2, S3, S4) reference this table by spec number.

### Scope types

| Scope type | Value shape | When assigned |
|------------|-------------|---------------|
| `global` | `{ type: 'global' }` | Default fallback. No specific file/folder context. |
| `today` | `{ type: 'today' }` | User is on the Today surface (`/` or `/vault/today.md`). Broad intent -- no file scope. |
| `folder` | `{ type: 'folder', path: string }` | User is viewing a folder in the vault browser. `path` is the relative vault path (e.g. `projects/`). |
| `file` | `{ type: 'file', path: string }` | User is viewing a specific file. `path` is the relative vault path (e.g. `notes/standup.md`). |
| `workflow` | `{ type: 'workflow', path: string }` | User is in the workflow editor viewing a `.flow.md` file. `path` is the relative vault path. |

### Scope resolution rules

| Surface | Route pattern | Resolved scope |
|---------|--------------|----------------|
| Today | `/` or `/vault/today.md` | `{ type: 'today' }` |
| Vault browser (folder) | `/vault/<folder>/` | `{ type: 'folder', path: '<folder>/' }` |
| Vault browser (file) | `/vault/<file>.md` | `{ type: 'file', path: '<file>.md' }` |
| Workflow editor | `/vault/_workflows/<name>.flow.md` | `{ type: 'workflow', path: '_workflows/<name>.flow.md' }` |
| Settings / other | `/settings`, etc. | `{ type: 'global' }` |

### Scope inheritance rules

1. **Right rail** inherits scope from the current route, updated reactively on navigation.
2. **Cmd+K palette** inherits the scope that was active when it was opened. If the user navigates while the palette is open (unlikely given its transient nature), scope does not update until the next open.
3. **Inline "ask about this" chip** sets the scope explicitly to the item it is attached to (the file for S3, or `today` for S1 sections). If the chip is on a Today section, scope is `{ type: 'today' }`. If the chip is on a file detail view, scope is `{ type: 'file', path: '<file>' }`.

### How scope reaches the agent

The `ChatRequest` model gains an optional `scope` field. The frontend serializes the current `ChatScope` into the request. The backend injects it into the agent's system prompt context so the agent knows what the user is looking at. The agent never needs to ask "which file are you referring to?" when scope is set.

```python
# chatServer/models/chat.py — extended
class ChatRequest(BaseModel):
    agent_name: str
    message: str
    session_id: str
    scope: Optional[dict] = None  # ChatScope serialized as dict
```

The backend reads `scope` and prepends context to the system prompt:

```python
# In build_deep_agent or the chat handler:
if chat_input.scope:
    scope_type = chat_input.scope.get("type", "global")
    scope_path = chat_input.scope.get("path")
    if scope_type == "file" and scope_path:
        context = f"The user is currently viewing the file: {scope_path}"
    elif scope_type == "folder" and scope_path:
        context = f"The user is currently browsing the folder: {scope_path}"
    elif scope_type == "workflow" and scope_path:
        context = f"The user is currently editing the workflow: {scope_path}"
    elif scope_type == "today":
        context = "The user is on the Today dashboard."
    # Inject as additional context in the agent's system prompt
```

---

## Acceptance Criteria

Each AC has a stable ID. UAT and Playwright scripts reference these directly. User-visible ACs MUST be queryable by ARIA role/label or stable `data-testid`.

### Scope binding

- [ ] **AC-01:** `useChatStore` exposes a `scope` field of type `ChatScope` (discriminated union defined in `api/types/chat.ts`). The scope is updated reactively when the route changes, following the scope resolution rules table above. [A4]
- [ ] **AC-02:** The `scope` field is serialized into every `POST /api/chat` request body as `scope: { type, path? }`. The backend `ChatRequest` model accepts the optional `scope` field. [A1]
- [ ] **AC-03:** The backend chat handler injects scope context into the agent's system prompt. When `scope.type` is `file`, the file's content (up to 4000 chars) is included in context. When `scope.type` is `folder`, the folder listing is included. When `scope.type` is `workflow`, the workflow file content is included. When `scope.type` is `today`, no file content is injected (broad intent). [A14]

### Right rail (ChatPanel refactor)

- [ ] **AC-04:** ChatPanel renders inside the SPEC-046 right pane (not as a slide-in overlay). The panel fills the right pane's full height. The SPEC-046 collapse/expand toggle controls visibility. No separate open/close button exists on the panel itself. [F2]
- [ ] **AC-05:** The chat header displays a scope indicator below the title showing the current scope: "Today" (when scope is `today`), "Folder: <name>" (when scope is `folder`), "File: <name>" (when scope is `file`), "Workflow: <name>" (when scope is `workflow`), or no indicator (when scope is `global`). The indicator has `aria-label="Chat scope: <description>"`. [A14]
- [ ] **AC-06:** When the user navigates to a different surface (e.g., from Today to a file), the scope indicator updates within one render cycle. Chat history is preserved -- navigation does not clear messages or reset the session. [A4]
- [ ] **AC-07:** The ConversationList (existing conversation switcher) remains functional inside the refactored ChatPanel. Starting a new conversation or switching conversations works as before. [A14]

### Cmd+K palette

- [ ] **AC-08:** Pressing Cmd+K (Mac) or Ctrl+K (Windows/Linux) from any authenticated surface opens a modal command palette overlay. The palette is an accessible dialog with `role="dialog"` and `aria-label="Command palette"`. Pressing Escape dismisses it. Clicking outside the palette dismisses it. [F2]
- [ ] **AC-09:** The palette's first row is always a free-form text input with `aria-label="Ask or search..."` and placeholder text "Ask Clarity anything...". The input is auto-focused on open. [F2]
- [ ] **AC-10:** Below the input, the palette shows a context-aware suggestion list. Suggestions include: recently accessed vault files (from `useVaultHooks` or `useTodayHooks` recent data), available workflows (if vault tree data is loaded), and a "Chat about <current scope>" option reflecting the active scope. Each suggestion is a selectable item with `role="option"`. [A4]
- [ ] **AC-11:** Typing in the input filters the suggestion list. Items matching the query text (fuzzy match on filename or title) are shown; non-matching items are hidden. If no items match, a single option "Ask: <query>" is shown, which sends the query as a chat message. [A14]
- [ ] **AC-12:** Selecting a file suggestion navigates to `/vault/<path>` and closes the palette. Selecting "Ask: <query>" or pressing Enter on the free-form input sends the query as a chat message to the right rail (opening it if collapsed) with the scope captured at palette-open time, then closes the palette. [A4]
- [ ] **AC-13:** The Cmd+K shortcut does not fire when the user is focused in the chat Composer input, a form input, or any `<textarea>`. A guard checks `document.activeElement` tag name and skips the shortcut if the focus is inside an editable field (except when Cmd+K is the explicit binding). [A14]
- [ ] **AC-14:** The palette renders above all other content at `z-index` higher than the three-pane layout. It is horizontally centered, vertically positioned at ~20% from top, with `max-width: 640px`. Styled with existing Tailwind tokens (`bg-ui-bg`, `border-ui-border`, `shadow-elevated`). [F2]
- [ ] **AC-15:** The `cmdk` library is added to `webApp/package.json`. The palette component uses `cmdk`'s `Command`, `Command.Input`, `Command.List`, `Command.Item`, and `Command.Empty` primitives. [A14]

### Inline "ask about this" chip

- [ ] **AC-16:** An `AskChip` component is exported from `webApp/src/components/chat/AskChip.tsx`. It accepts props: `scope: ChatScope` (required), `label?: string` (default "Ask about this"), `prompt?: string` (optional pre-filled message). It renders a `<button>` with `aria-label="Ask about this"` (or the custom label) and an icon (chat bubble). [F2]
- [ ] **AC-17:** Clicking the AskChip opens the right-rail chat (if collapsed), sets the chat scope to the chip's `scope` prop, and optionally pre-fills the Composer input with the `prompt` prop value. The user can then edit the pre-filled text or send it as-is. [A4]
- [ ] **AC-18:** The AskChip component does not import or depend on any surface-specific module (Today, file detail, etc.). It is a self-contained, reusable primitive. Surface components pass the appropriate `ChatScope` when rendering it. [A14]
- [ ] **AC-19:** The Today surface (SPEC-045 `ApprovalsSection`, `AgentSection`) renders an AskChip next to approval cards and agent activity items. The chip's scope is `{ type: 'today' }`. Clicking it opens chat scoped to Today. [A14]

### Keyboard navigation and accessibility

- [ ] **AC-20:** The Cmd+K palette supports full keyboard navigation: arrow keys move between suggestions, Enter selects the highlighted suggestion, Escape closes the palette. Focus is trapped inside the dialog while open (no Tab-out to underlying content). [F2]
- [ ] **AC-21:** The right-rail chat panel has `<aside role="complementary" aria-label="Chat">` as its outermost landmark. The scope indicator is a `<p>` within the header, not a heading. [F2]
- [ ] **AC-22:** The AskChip has a visible focus ring (`:focus-visible` outline) consistent with other interactive elements in the design system. [F2]

### Edge cases

- [ ] **AC-23:** Opening Cmd+K while the right rail is already open and contains an in-progress message: the palette opens normally, does not disrupt the in-progress message. If the user sends a query from the palette, it appends to the existing conversation. [A14]
- [ ] **AC-24:** Rapid navigation (e.g., clicking through multiple folders quickly) updates the scope indicator without creating stale scope state. The scope is derived from the current route, not from navigation events. A `useMemo` or equivalent derives scope from `useLocation().pathname`. [A4]
- [ ] **AC-25:** If the backend does not recognize the `scope` field (e.g., older server version), the chat request still succeeds -- `scope` is optional and the backend ignores unknown fields gracefully. [A14]

---

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `webApp/src/api/types/chat.ts` | `ChatScope` discriminated union type, `ChatScopeType` string literal union. Canonical type definition referenced by all chat-related modules. |
| `webApp/src/hooks/useChatScope.ts` | Hook that derives `ChatScope` from `useLocation().pathname` using the scope resolution rules. Single source of truth for scope derivation. |
| `webApp/src/components/chat/CommandPalette.tsx` | Cmd+K palette built on `cmdk`. Contains `Command.Input`, `Command.List`, `Command.Item`, keyboard shortcut registration, and scope capture logic. |
| `webApp/src/components/chat/AskChip.tsx` | Inline "ask about this" chip. Reusable across all surfaces. |
| `webApp/src/components/chat/ScopeIndicator.tsx` | Displays the current chat scope as a label with an icon. Used in the ChatPanel header and optionally in the palette. |
| `webApp/src/components/chat/ChatRail.tsx` | Thin wrapper around ChatPanel that lives in the SPEC-046 right pane. Passes scope from `useChatScope` into ChatPanel. Provides the `<aside>` landmark. |
| `tests/uat/playwright/test_spec_049_chat_surfaces.py` | Playwright test functions for user-visible ACs. Written BEFORE frontend implementation. |

### Files to Modify

| File | Change |
|------|--------|
| `webApp/package.json` | Add `cmdk` dependency. |
| `webApp/src/stores/useChatStore.ts` | Add `scope: ChatScope` field and `setScope(scope: ChatScope)` action. |
| `webApp/src/components/ChatPanel.tsx` | Accept `scope` prop. Pass scope to `MessageHeader` for indicator. Include scope in `onNew` handler's fetch body. Remove slide-in container styling (container is now provided by ChatRail/SPEC-046 right pane). |
| `webApp/src/components/ui/chat/MessageHeader.tsx` | Accept optional `scope: ChatScope` prop. Render `ScopeIndicator` below the title when scope is present and not `global`. |
| `chatServer/models/chat.py` | Add `scope: Optional[dict] = None` to `ChatRequest`. |
| `chatServer/main.py` | Pass `chat_input.scope` to `build_deep_agent` or inject scope context into the system prompt within `_handle_chat` / `_handle_chat_stream`. |
| `chatServer/services/deep_agent_builder.py` | Accept optional `scope` parameter. When present, prepend scope-aware context to the system prompt. For `file` and `workflow` scopes, read the file content (up to 4KB) via VaultService and include it. |
| `webApp/src/layouts/AppShell.tsx` | (Modified by SPEC-046 to be three-pane.) This spec wires ChatRail into the right pane instead of raw ChatPanel. Registers the Cmd+K global keyboard listener. |
| `webApp/src/components/navigation/TopBar.tsx` | Add a subtle Cmd+K shortcut hint (e.g., a pill showing "Cmd+K" in the right section, visible on desktop only). |
| `webApp/src/components/today/ApprovalsSection.tsx` | Render `AskChip` next to approval cards with `scope={{ type: 'today' }}`. |
| `webApp/src/components/today/AgentSection.tsx` | Render `AskChip` next to agent items with `scope={{ type: 'today' }}`. |
| `webApp/src/App.tsx` | Mount `CommandPalette` inside the authenticated layout (rendered once, globally). |

### Out of Scope

- **Bottom drawer chat** -- wireframe variant C, deferred past Stage 1 (functional doc: "What's deferred").
- **Inline bubble chat on text selections** -- wireframe variant D, Stage 2+.
- **Slash commands in chat** (`/run`, `/summarize`) -- mentioned in functional doc S5 but deferred. Stage 1 chat is free-form text only.
- **Full contextual suggestions in Cmd+K** (e.g., "run workflow Y", "summarize today") -- Stage 1 ships search + recent files + "ask" fallback. Rich action suggestions are Stage 2.
- **Chat session per-scope isolation** -- architecture open question #9 in the vision doc. Stage 1 uses a single persistent session regardless of scope changes. A scope change does not create a new conversation.
- **File content injection for `today` scope** -- Today is a synthesized view, not a raw file to inject. The agent already has access to Today's data via the workflow engine.
- **Wikilink rendering in chat responses** -- deferred to when `remark-wiki-link` is added in S3.
- **SSE streaming for chat** -- the existing `POST /api/chat` supports SSE via `Accept: text/event-stream` header, but the assistant-ui runtime does not yet use it. Streaming is orthogonal to this spec.
- **S3 file detail surface** -- SPEC-047. That spec will render `AskChip` with file scope; the chip component is defined here.
- **S4 workflow editor surface** -- SPEC-048. That spec will render `AskChip` with workflow scope.

---

## Technical Approach

### 1. ChatScope type system

Defined once in `api/types/chat.ts`, imported everywhere:

```typescript
// webApp/src/api/types/chat.ts
export type ChatScopeType = 'global' | 'today' | 'folder' | 'file' | 'workflow';

export type ChatScope =
  | { type: 'global' }
  | { type: 'today' }
  | { type: 'folder'; path: string }
  | { type: 'file'; path: string }
  | { type: 'workflow'; path: string };
```

### 2. useChatScope hook -- scope derivation from route

Single hook, single source of truth. No component should compute scope independently.

```typescript
// webApp/src/hooks/useChatScope.ts
import { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import type { ChatScope } from '@/api/types/chat';

export function useChatScope(): ChatScope {
  const { pathname } = useLocation();

  return useMemo(() => {
    // Today
    if (pathname === '/' || pathname === '/vault/today.md') {
      return { type: 'today' };
    }

    // Vault paths
    if (pathname.startsWith('/vault/')) {
      const relPath = pathname.slice('/vault/'.length);

      // Workflow files
      if (relPath.startsWith('_workflows/') && relPath.endsWith('.flow.md')) {
        return { type: 'workflow', path: relPath };
      }

      // Folder (ends with /)
      if (relPath.endsWith('/')) {
        return { type: 'folder', path: relPath };
      }

      // File
      if (relPath.length > 0) {
        return { type: 'file', path: relPath };
      }
    }

    return { type: 'global' };
  }, [pathname]);
}
```

This hook is consumed by `ChatRail` (which passes scope to ChatPanel) and captured by `CommandPalette` on open.

### 3. Zustand store extension

Minimal addition to `useChatStore`:

```typescript
// Added to ChatStore interface
scope: ChatScope;
setScope: (scope: ChatScope) => void;

// Added to create()
scope: { type: 'global' } as ChatScope,
setScope: (scope) => set({ scope }),
```

`ChatRail` calls `setScope` when `useChatScope()` changes. The store is the bridge between route-derived scope and ChatPanel's message-send logic.

### 4. ChatPanel refactor

Changes to `ChatPanel.tsx` are surgical:

1. **Remove container styling** -- the outer `div` loses `shadow-lg`, `border-l`, and slide-in animation classes. The container is now provided by the SPEC-046 right pane.
2. **Accept `scope` prop** -- passed down from `ChatRail`.
3. **Pass scope to MessageHeader** -- renders `ScopeIndicator`.
4. **Include scope in fetch body** -- the `onNew` callback serializes `useChatStore.getState().scope` into the `POST /api/chat` body.

Internal logic (assistant-ui runtime, heartbeat, message polling, error boundary, ConversationList) is unchanged.

### 5. ChatRail wrapper

Thin component that lives in the SPEC-046 right pane:

```tsx
// webApp/src/components/chat/ChatRail.tsx
export const ChatRail: React.FC = () => {
  const scope = useChatScope();
  const setScope = useChatStore((s) => s.setScope);

  useEffect(() => {
    setScope(scope);
  }, [scope, setScope]);

  return (
    <aside role="complementary" aria-label="Chat" className="h-full flex flex-col">
      <ChatPanel scope={scope} />
    </aside>
  );
};
```

### 6. ScopeIndicator component

Pure presentational:

```tsx
// webApp/src/components/chat/ScopeIndicator.tsx
const SCOPE_LABELS: Record<ChatScopeType, (scope: ChatScope) => string | null> = {
  global: () => null,
  today: () => 'Today',
  folder: (s) => `Folder: ${(s as { path: string }).path.replace(/\/$/, '').split('/').pop()}`,
  file: (s) => `File: ${(s as { path: string }).path.split('/').pop()}`,
  workflow: (s) => `Workflow: ${(s as { path: string }).path.split('/').pop()?.replace('.flow.md', '')}`,
};

export const ScopeIndicator: React.FC<{ scope: ChatScope }> = ({ scope }) => {
  const label = SCOPE_LABELS[scope.type](scope);
  if (!label) return null;

  return (
    <p
      className="text-xs text-text-muted font-mono truncate"
      aria-label={`Chat scope: ${label}`}
    >
      {label}
    </p>
  );
};
```

Integrated into `MessageHeader` below the title.

### 7. Cmd+K palette (cmdk)

The `cmdk` library provides unstyled, composable command menu primitives. We style with Tailwind.

```tsx
// webApp/src/components/chat/CommandPalette.tsx (simplified structure)
import { Command } from 'cmdk';

export const CommandPalette: React.FC = () => {
  const [open, setOpen] = useState(false);
  const scopeAtOpen = useRef<ChatScope>({ type: 'global' });
  const currentScope = useChatScope();

  // Register global keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        const tag = (document.activeElement as HTMLElement)?.tagName;
        if (tag === 'TEXTAREA' || tag === 'INPUT') {
          // Allow Cmd+K even in inputs -- it's an intentional override
          // But skip if inside chat composer to avoid conflict
          if ((document.activeElement as HTMLElement)?.closest('[data-testid="composer"]')) {
            return;
          }
        }
        e.preventDefault();
        scopeAtOpen.current = currentScope;
        setOpen(true);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [currentScope]);

  const handleSendAsChat = (query: string) => {
    // Set scope to what was captured at open time
    useChatStore.getState().setScope(scopeAtOpen.current);
    // Open chat rail if collapsed
    // Trigger message send via store
    setOpen(false);
  };

  return (
    <Command.Dialog
      open={open}
      onOpenChange={setOpen}
      label="Command palette"
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]"
    >
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50" onClick={() => setOpen(false)} />
      <div className="relative w-full max-w-[640px] bg-ui-bg border border-ui-border rounded-lg shadow-elevated">
        <Command.Input
          placeholder="Ask Clarity anything..."
          aria-label="Ask or search..."
          className="w-full px-4 py-3 text-base bg-transparent border-b border-ui-border outline-none"
        />
        <Command.List className="max-h-[300px] overflow-y-auto p-2">
          <Command.Empty>
            {/* Rendered when no items match -- shows "Ask: <query>" */}
          </Command.Empty>
          <Command.Group heading="Recent files">
            {/* Items from useVaultHooks or useTodayHooks recent data */}
          </Command.Group>
          <Command.Group heading="Actions">
            <Command.Item>Chat about {scopeLabel}</Command.Item>
          </Command.Group>
        </Command.List>
      </div>
    </Command.Dialog>
  );
};
```

**Key design decisions:**

- `Command.Dialog` handles focus trapping and Escape dismissal natively.
- Scope is captured into a ref at open time, not read continuously.
- "Ask" fallback uses the chat store's `addMessage` to inject the user message and opens the rail.
- Suggestion data comes from React Query caches (recent files from `useToday`, vault tree from `useVaultTree` if loaded). No new API calls on palette open.

### 8. AskChip component

Minimal, self-contained:

```tsx
// webApp/src/components/chat/AskChip.tsx
interface AskChipProps {
  scope: ChatScope;
  label?: string;
  prompt?: string;
}

export const AskChip: React.FC<AskChipProps> = ({
  scope,
  label = 'Ask about this',
  prompt,
}) => {
  const setScope = useChatStore((s) => s.setScope);
  const setChatPanelOpen = useChatStore((s) => s.setChatPanelOpen);

  const handleClick = () => {
    setScope(scope);
    setChatPanelOpen(true);
    // If prompt is provided, pre-fill the composer.
    // assistant-ui does not expose a direct "set composer text" API,
    // so we use a store field that the Composer reads on mount.
    if (prompt) {
      useChatStore.getState().setPendingPrompt(prompt);
    }
  };

  return (
    <button
      onClick={handleClick}
      className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-text-muted hover:text-text-primary bg-ui-element-bg hover:bg-ui-interactive-bg-hover border border-ui-border rounded-md transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-primary"
      aria-label={label}
    >
      <ChatBubbleIcon className="w-3 h-3" />
      {label}
    </button>
  );
};
```

**Pre-fill mechanism:** `useChatStore` gains a `pendingPrompt: string | null` field. When non-null, the ChatPanel's Composer integration reads it on the next render, populates the input, and clears the field. This avoids coupling AskChip to assistant-ui internals.

### 9. Backend scope context injection

The scope context is injected as a prefix to the system prompt, not as a separate message. This ensures the agent has the context without polluting the conversation history.

```python
# chatServer/services/deep_agent_builder.py — in build_deep_agent()
def _build_scope_context(scope: dict | None, vault_service: VaultService, user_id: str) -> str:
    """Build a scope context string from the chat scope."""
    if not scope:
        return ""

    scope_type = scope.get("type", "global")
    scope_path = scope.get("path")

    parts = []
    if scope_type == "today":
        parts.append("The user is on the Today dashboard.")
    elif scope_type == "file" and scope_path:
        parts.append(f"The user is viewing the file: {scope_path}")
        try:
            content = vault_service.read_file_sync(user_id, scope_path)
            # Truncate to 4000 chars to stay within prompt budget
            if len(content) > 4000:
                content = content[:4000] + "\n... [truncated]"
            parts.append(f"File content:\n```\n{content}\n```")
        except Exception:
            pass  # File read failure is non-fatal
    elif scope_type == "folder" and scope_path:
        parts.append(f"The user is browsing the folder: {scope_path}")
    elif scope_type == "workflow" and scope_path:
        parts.append(f"The user is editing the workflow: {scope_path}")
        try:
            content = vault_service.read_file_sync(user_id, scope_path)
            if len(content) > 4000:
                content = content[:4000] + "\n... [truncated]"
            parts.append(f"Workflow definition:\n```\n{content}\n```")
        except Exception:
            pass
    else:
        return ""

    return "\n".join(parts)
```

The context string is prepended to the existing system prompt. This is the same pattern used by the existing agent builder for injecting user preferences and session context.

### 10. Cmd+K shortcut hint in TopBar

A small visual indicator in the TopBar right section:

```tsx
{/* Desktop-only Cmd+K hint */}
<kbd className="hidden lg:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-mono text-text-muted bg-ui-element-bg border border-ui-border rounded">
  {navigator.platform.includes('Mac') ? '⌘' : 'Ctrl+'}K
</kbd>
```

Positioned between ApprovalsBadge and ThemeToggle.

---

## Testing Requirements

### Unit Tests (required)

- `test_chat_scope_derivation.test.ts`: `useChatScope` returns correct scope for every route pattern in the resolution table. Edge cases: trailing slashes, nested paths, encoded characters.
- `test_scope_indicator.test.tsx`: `ScopeIndicator` renders correct label for each scope type, renders nothing for `global`.
- `test_ask_chip.test.tsx`: clicking sets scope in store, opens panel, pre-fills prompt when provided.
- `test_command_palette.test.tsx`: opens on Cmd+K, closes on Escape, filters suggestions, sends chat message on Enter with empty suggestions.
- `test_chat_request_scope.py` (backend): `ChatRequest` model accepts `scope` field, validates types, ignores when absent.
- `test_scope_context_builder.py` (backend): `_build_scope_context` produces correct strings for each scope type, truncates long files, returns empty string for `global` and `None`.

### Integration Tests (required)

- `test_chat_with_scope.py`: `POST /api/chat` with `scope: { type: 'file', path: 'notes/test.md' }` succeeds and the agent response references the file context. Without scope, the request still succeeds.
- `test_chat_scope_backwards_compat.py`: `POST /api/chat` without `scope` field (simulating old client) returns a normal response with no error.

### UI Acceptance Tests (Playwright -- written BEFORE implementation)

Script: `tests/uat/playwright/test_spec_049_chat_surfaces.py`. One function per user-visible AC. Selectors target ARIA role/label.

| AC | Flow / Service Test | UI Test (Playwright) |
|----|---------------------|---------------------|
| AC-01 | `test_scope_derived_from_route` | `test_ac_01_scope_updates_on_navigation` |
| AC-02 | `test_scope_sent_in_request` | -- |
| AC-03 | `test_scope_context_injected` | -- |
| AC-04 | -- | `test_ac_04_chat_in_right_pane` |
| AC-05 | -- | `test_ac_05_scope_indicator_displays` |
| AC-06 | -- | `test_ac_06_scope_updates_on_navigate` |
| AC-07 | -- | `test_ac_07_conversation_list_works` |
| AC-08 | -- | `test_ac_08_cmd_k_opens_palette` |
| AC-09 | -- | `test_ac_09_palette_input_autofocused` |
| AC-10 | -- | `test_ac_10_palette_suggestions_render` |
| AC-11 | -- | `test_ac_11_palette_filters_on_type` |
| AC-12 | -- | `test_ac_12_palette_file_navigates` |
| AC-13 | -- | `test_ac_13_cmd_k_skipped_in_composer` |
| AC-14 | -- | `test_ac_14_palette_styling_and_position` |
| AC-15 | CI check: `cmdk` in package.json | -- |
| AC-16 | -- | `test_ac_16_ask_chip_renders` |
| AC-17 | -- | `test_ac_17_ask_chip_opens_chat_with_scope` |
| AC-18 | CI check: no surface-specific imports in AskChip | -- |
| AC-19 | -- | `test_ac_19_today_renders_ask_chips` |
| AC-20 | -- | `test_ac_20_palette_keyboard_nav` |
| AC-21 | -- | `test_ac_21_chat_rail_landmark` |
| AC-22 | -- | `test_ac_22_ask_chip_focus_ring` |
| AC-23 | -- | `test_ac_23_palette_over_active_chat` |
| AC-24 | `test_scope_rapid_navigation` | `test_ac_24_rapid_navigation_scope` |
| AC-25 | `test_scope_field_optional` | -- |

### Manual Verification (UAT)

1. Navigate to Today -- verify scope indicator shows "Today" in chat rail.
2. Navigate to a folder in vault browser -- verify indicator updates to "Folder: <name>".
3. Navigate to a file -- verify "File: <name>".
4. Press Cmd+K on Today -- verify palette opens with suggestions. Type a filename -- verify filter works. Press Escape -- verify dismissal.
5. Type a question in the palette and press Enter -- verify chat rail opens (if collapsed), message appears in conversation, and the scope indicator reflects Today (the scope at palette-open time).
6. Click an "Ask about this" chip next to an approval card -- verify chat rail opens with Today scope.
7. Navigate rapidly between 5 different surfaces -- verify scope indicator updates correctly each time with no stale state.
8. Open Cmd+K while a message is in flight in the chat rail -- verify palette opens and does not disrupt the in-flight message.
9. Send a chat message while viewing a file -- verify the agent's response references the file content (confirming backend scope injection).
10. Test Cmd+K vs. Ctrl+K on both Mac and Windows/Linux (or verify via user agent detection).

---

## Edge Cases

- **Cmd+K while Composer is focused:** the global Cmd+K handler skips activation when `document.activeElement` is inside a `[data-testid="composer"]` container. Rationale: Cmd+K in a text field should not hijack typing. The user can click outside the composer first, then press Cmd+K.
- **Cmd+K while right rail is open with active conversation:** palette opens normally as an overlay. Sending a message from the palette appends to the existing conversation (does not start a new one). Scope is set to what was active when the palette opened, which may differ from the rail's current scope if the user navigated between opening the rail and opening the palette.
- **Scope transitions during navigation:** scope is derived from `useLocation().pathname` via `useMemo`. React Router updates the location synchronously on navigation, so the scope updates in the same render cycle. No debouncing or throttling needed.
- **Backend receives unknown scope type:** the `scope` field on `ChatRequest` is `Optional[dict]`. The `_build_scope_context` function defaults to returning an empty string for any unrecognized `type`. No error, no crash.
- **Backend receives scope with path traversal attempt:** `_build_scope_context` reads files via `VaultService.read_file`, which uses `_resolve` with full path-traversal protection (SPEC-045 AC-22). A malicious `scope.path` of `../../../etc/passwd` is rejected by VaultService; the context builder catches the exception and proceeds without file content.
- **AskChip on a surface where the chat panel is not rendered:** the chip calls `setChatPanelOpen(true)` on the Zustand store. If the SPEC-046 right pane is not present (e.g., on a non-authenticated page), the call is a no-op. AskChip is only rendered inside authenticated surfaces where the pane exists.
- **Palette open with stale suggestion data:** suggestions are read from React Query caches, not fetched on open. If the cache is empty (first load before vault tree is fetched), the palette shows only the free-form input and the "Chat about <scope>" action. This is acceptable for Stage 1.
- **Long file paths in scope indicator:** the indicator shows only the last path segment (filename or folder name). Full path is available via `aria-label` for screen readers.
- **Concurrent scope updates from AskChip and navigation:** AskChip directly calls `setScope()` on the store. If the user clicks an AskChip and then navigates before the chat panel renders, the `ChatRail` component's `useEffect` will overwrite the chip's scope with the new route's scope. This is correct behavior -- the most recent context wins.
- **Pre-filled prompt from AskChip and assistant-ui Composer:** assistant-ui's `<Composer />` does not expose a direct text-setting API. The `pendingPrompt` store field is read by a thin wrapper component around `<Composer />` that injects the text via a controlled input pattern. If assistant-ui updates break this, the fallback is to show the prompt as a toast suggesting the user paste it.

---

## Functional Units (for PR Breakdown)

### FU-1: Scope types + hook + store extension (frontend-dev)
**Branch:** `feat/SPEC-049-scope`
**ACs:** AC-01, AC-24
- Create `api/types/chat.ts` with `ChatScope` type
- Create `hooks/useChatScope.ts`
- Extend `useChatStore` with `scope`, `setScope`, `pendingPrompt`, `setPendingPrompt`
- Unit tests for scope derivation from all route patterns

### FU-2: Backend scope support (backend-dev)
**Branch:** `feat/SPEC-049-scope-backend`
**ACs:** AC-02, AC-03, AC-25
- Extend `ChatRequest` model with optional `scope` field
- Implement `_build_scope_context` in `deep_agent_builder.py`
- Wire scope context injection into `_handle_chat` and `_handle_chat_stream`
- Unit tests for model, context builder
- Integration test for scope in chat request

### FU-3: ChatPanel refactor + ChatRail + ScopeIndicator (frontend-dev)
**Branch:** `feat/SPEC-049-chat-rail`
**Depends on:** FU-1, SPEC-046 FU-2 (three-pane layout must exist)
**ACs:** AC-04, AC-05, AC-06, AC-07, AC-21
- Create `ScopeIndicator` component
- Create `ChatRail` wrapper
- Refactor `ChatPanel` to accept scope prop, remove slide-in styling
- Update `MessageHeader` with scope display
- Wire ChatRail into SPEC-046 right pane
- Playwright tests for rail rendering and scope indicator

### FU-4: Cmd+K palette (frontend-dev)
**Branch:** `feat/SPEC-049-cmd-k`
**Depends on:** FU-1
**ACs:** AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-20, AC-23
- Add `cmdk` to `package.json`
- Create `CommandPalette` component
- Register global Cmd+K handler
- Add Cmd+K hint to TopBar
- Mount palette in `App.tsx` (or AppShell)
- Playwright tests for palette open/close, keyboard nav, filtering, sending

### FU-5: AskChip + surface integration (frontend-dev)
**Branch:** `feat/SPEC-049-ask-chip`
**Depends on:** FU-1, FU-3
**ACs:** AC-16, AC-17, AC-18, AC-19, AC-22
- Create `AskChip` component
- Wire pendingPrompt mechanism for pre-filled chat input
- Add AskChip to Today's ApprovalsSection and AgentSection
- Unit tests for AskChip
- Playwright tests for chip rendering and interaction

**Merge order:** FU-1 → FU-2 (can parallel FU-1), FU-1 → FU-3 → FU-5, FU-1 → FU-4. Recommended: FU-1 first, then FU-2 and FU-4 in parallel, then FU-3, then FU-5.

```
FU-1 (scope types)
 ├── FU-2 (backend scope) ──────────────────┐
 ├── FU-4 (Cmd+K palette) ─────────────────┐│
 └── FU-3 (ChatRail + refactor) ───────────┤│
      └── FU-5 (AskChip + integration) ────┘│
                                             │
                              All merge to main
```

---

## Dependencies (inter-spec)

| Dependency | Direction | Detail |
|------------|-----------|--------|
| SPEC-046 | This spec depends on | Three-pane layout (FU-2 of SPEC-046) must be merged before this spec's FU-3 can wire ChatRail into the right pane. |
| SPEC-045 | This spec depends on | ChatPanel, useChatStore, MessageHeader, ApprovalsBadge, ApprovalsSection, AgentSection all exist from SPEC-045. |
| SPEC-047 (S3 file detail) | Consumes this spec | Will render AskChip with `file` scope. Uses the ChatScope type and AskChip component defined here. |
| SPEC-048 (S4 workflow editor) | Consumes this spec | Will render AskChip with `workflow` scope. |
| SPEC-046 FU-3 | Overlap | SPEC-046 FU-3 creates a minimal ChatRail and wires Cmd+K. This spec supersedes that work with the full implementation. If SPEC-046 FU-3 has not been implemented yet, skip it and implement via this spec. If it has been implemented, this spec refactors it in-place. |

**Overlap note on SPEC-046 FU-3:** SPEC-046 includes a FU-3 ("Chat rail + Cmd+K") that creates a minimal `ChatRail.tsx`, `CommandPalette.tsx`, and `useChatStore.scope`. This spec provides the complete, production-quality versions of those same artifacts. The implementer should check whether SPEC-046 FU-3 has shipped. If it has, FU-1 and FU-3 of this spec refactor the existing files. If it has not, SPEC-046 FU-3 should be skipped entirely and this spec implements the full versions from scratch.

---

## Resolved Questions (2026-04-21, Tim approved all recommendations)

### OQ-A. Cmd+K in form inputs — **RESOLVED: yes, except chat Composer**

Cmd+K fires everywhere except inside `[data-testid="composer"]`. Matches VS Code/Obsidian behavior.

### OQ-B. Chat session isolation — **RESOLVED: single session for Stage 1**

Scope is injected as context, not session identity. Simpler, preserves conversation continuity. Per-scope sessions revisitable in Stage 2.

### OQ-C. AskChip pre-fill — **RESOLVED: pendingPrompt in Zustand store**

Use `pendingPrompt` store field. Fallback to auto-send if assistant-ui's Composer resists external value injection.

---

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-25)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (ChatScope type -> useChatScope hook -> store -> ChatRequest model -> backend context builder)
- [x] Technical decisions cite principles (A1, A4, A14, F2)
- [x] Merge order is explicit and acyclic (FU-1 -> FU-2/FU-4 parallel -> FU-3 -> FU-5)
- [x] Out-of-scope is explicit and enumerates downstream specs
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs (table)
- [x] Existing infrastructure section enumerates every reused primitive
- [x] Scope binding contract defined as a canonical table for cross-spec reference
- [x] Inter-spec dependencies identified, including SPEC-046 FU-3 overlap
- [x] Open questions surfaced with recommendations
