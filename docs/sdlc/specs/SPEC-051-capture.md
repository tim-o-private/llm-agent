# SPEC-051: Capture (Stage 2 -- Text Routing into the Vault)

> **Status:** Draft
> **Author:** spec-writer (Claude) on behalf of Tim
> **Created:** 2026-04-21
> **Vision:** [`docs/sdlc/visions/clarity-as-vault.md`](../visions/clarity-as-vault.md) -- Stage 2, Transaction #1
> **Directive:** [`docs/sdlc/visions/clarity-as-vault-functional.md`](../visions/clarity-as-vault-functional.md) -- S1 Notes, S5 Chat
> **Stage:** Clarity-as-Vault Stage 2
> **Depends on:** SPEC-045 (VaultService, today.md notes, approval lane), SPEC-046 (vault shell, vault browser, Cmd+K palette)

---

## Goal

Generalize the SPEC-045 Notes input from "append a bullet to today.md" into a capture system that routes text to any vault location. The user drops a thought; the agent determines where it belongs (a project folder, a meeting-prep doc, an entity page, or today.md if nothing better fits); the agent confirms placement; the user can redirect.

This is Transaction #1 from the vision: "User drops a thought (text). Agent routes into the graph, confirms placement, and may propose a workflow if it recognizes a recurring capture pattern."

Stage 2 exit criterion: **does working memory feel externalized?** The user captures thoughts without deciding where they go; the agent makes good routing decisions; corrections are rare and easy.

---

## What Exists (Stage 1 Foundation)

These primitives ship in Stage 1 and this spec composes them. Nothing here is new work.

| Primitive | Source | What we use it for |
|-----------|--------|--------------------|
| `VaultService` | SPEC-045 `chatServer/services/vault_service.py` | All vault reads and writes. `_resolve` is the security chokepoint. `update_body` fires StorageSync. |
| `markdown_sections` parser | SPEC-045 `chatServer/services/markdown_sections.py` | Parse/patch sections within a target file. Append to a named section. |
| `TodayService.append_note` | SPEC-045 `chatServer/services/today_service.py` | Current capture: appends a timestamped bullet to today.md's Notes section. Becomes the fallback path. |
| `POST /api/today/notes` | SPEC-045 `chatServer/routers/today_router.py` | Current capture endpoint. Stays as-is; new capture endpoint wraps it. |
| `NotesSection` component | SPEC-045 `webApp/src/components/today/NotesSection.tsx` | Current capture UI. Stays as-is; gains a routing indicator. |
| `approval_cards` table | SPEC-045 | Proposal mechanism if agent wants to create a new file/folder. |
| Vault tree API | SPEC-046 `GET /vault/tree` | Agent uses tree structure for routing decisions. |
| Vault file API | SPEC-046 `GET /vault/file`, `GET /vault/folder` | Agent reads target files to determine where content fits. |
| Cmd+K palette | SPEC-046 `CommandPalette.tsx` (cmdk) | Second capture entry point (type thought, submit). |
| Chat rail | SPEC-046 `ChatRail.tsx` | Third capture entry point (conversational capture). |

---

## Interaction Model

### Happy path

1. User types a thought into any capture surface (Notes input on Today, Cmd+K, chat rail, or a future mobile/voice surface).
2. `POST /api/capture` accepts the text, returns immediately with a `capture_id` and `status: "routing"`.
3. The capture-router agent (Haiku -- high volume, low stakes per architecture doc) examines the text, the vault tree, and recent context to determine placement.
4. Agent writes the text to the target file (appending to an existing section, or creating a new bullet list in the appropriate doc) via `VaultService`.
5. A confirmation is returned to the user: "Added to `projects/website-redesign.md` under Notes" with a link to the target file.
6. If the user disagrees, they redirect: "No, that belongs in meeting prep for tomorrow." The agent moves the content.

### Redirect flow

1. User sees the confirmation and says (via chat or inline control) "move this to X" or "wrong place."
2. `POST /api/capture/{id}/redirect` accepts a `target_hint` (free text or a vault path).
3. The agent removes the content from the original location and writes it to the new target.
4. Confirmation updates: "Moved to `meeting-prep/2026-04-22.md`."
5. Redirect is logged -- the agent learns from corrections over time (see Pattern Recognition below).

### Fallback

If the agent cannot determine a meaningful target, the capture falls back to today.md's Notes section -- the exact behavior SPEC-045 already implements. The user sees "Added to Today notes" and can redirect from there.

---

## Entry Points

Capture is a single backend operation reachable from multiple surfaces. Each surface calls the same `POST /api/capture` endpoint; the difference is context metadata attached to the request.

| Surface | Entry mechanism | Context available | Ships with |
|---------|----------------|-------------------|------------|
| Today Notes input | Existing textarea + submit | `source: "today"`, today.md visible | This spec (upgrade existing) |
| Cmd+K palette | Type thought, submit | `source: "cmdk"`, current vault path | This spec (extend SPEC-046 palette) |
| Chat rail | Conversational: "remember that..." | `source: "chat"`, current chat scope, conversation history | This spec (extend SPEC-046 chat) |
| Direct vault edit | User types into a file (not routed) | N/A -- this is Transaction #3, not capture | Out of scope |

---

## Acceptance Criteria

### Core capture flow

- [ ] **AC-01:** `POST /api/capture` accepts `{ text: string, source: string, context?: object }` and returns `{ capture_id: string, status: "routing" }` with HTTP 202. The capture is persisted to a `captures` table before the agent is invoked. [A1, A14]

- [ ] **AC-02:** The capture-router agent examines the text, the user's vault tree (via `VaultService`), and optional context to determine a target file and section. The agent returns a `CaptureRouting` with `{ target_path: string, target_section: string | null, method: "append" | "create", reasoning: string }`. [A12]

- [ ] **AC-03:** When `method` is `"append"`, the text is appended to the named section of the target file (using `markdown_sections.append_to_section` or equivalent). When `method` is `"create"`, a new file is created at `target_path` with the capture as its initial content. File creation goes through `VaultService.update_body` (which enforces path safety and fires sync). [A8]

- [ ] **AC-04:** When the agent cannot determine a meaningful target (confidence below threshold or vault is too sparse), the capture falls back to `today.md` Notes section -- the exact SPEC-045 `append_note` path. The response indicates `fallback: true`. [A14]

- [ ] **AC-05:** After routing completes, the `captures` row is updated with `status: "placed"`, `target_path`, `target_section`, `method`, and `reasoning`. A completion payload is available via `GET /api/capture/{id}`. [A10]

- [ ] **AC-06:** If routing fails (agent error, timeout, VaultService write failure), the capture falls back to today.md Notes. The `captures` row is updated with `status: "placed"`, `fallback: true`, and `error_detail`. The user's thought is never lost. [A12]

### Confirmation and redirect

- [ ] **AC-07:** The capture response (polled or pushed) includes a human-readable `confirmation` string: "Added to `<target_path>` [under <section>]" with a vault link the UI can render as a clickable path. [A13]

- [ ] **AC-08:** `POST /api/capture/{id}/redirect` accepts `{ target_hint: string }`. The agent interprets the hint (a vault path, a file name, or a natural-language description like "meeting prep for tomorrow"), removes the content from the original location, writes it to the new target, and updates the `captures` row. Returns the updated confirmation. [A13]

- [ ] **AC-09:** Redirect is only allowed while `status` is `"placed"`. Attempting to redirect a capture that is still `"routing"` returns 409. Attempting to redirect after a previous redirect succeeds (captures are single-redirect in Stage 2; multi-hop is a Stage 3+ concern). [A14]

- [ ] **AC-10:** Both initial placement and redirects are logged in `activity_log` with `actor: "capture-router"` and the relevant `subject_path`. [A12]

### Entry point integration

- [ ] **AC-11:** The Today Notes textarea continues to work exactly as SPEC-045 defined (Cmd+Enter to save, immediate append to today.md). A toggle or preference `capture_routing_enabled` (default `false` in Stage 2 rollout, flipped to `true` once routing quality is validated) switches the Notes input from direct-append to routed-capture mode. When routing is enabled, the submit calls `POST /api/capture` instead of `POST /api/today/notes`. [A13, A14]

- [ ] **AC-12:** The Cmd+K palette (SPEC-046) gains a "Capture" action. Typing into Cmd+K and selecting "Capture" (or pressing a modifier like Shift+Enter) submits the text as a capture. Context includes the current vault path. [A14]

- [ ] **AC-13:** The chat rail recognizes capture intent from conversational phrasing ("remember that...", "note to self:", "capture:"). When detected, the agent invokes the capture flow internally and confirms placement in the chat response. This is agent behavior, not a new endpoint -- the chat agent calls the capture service. [A12]

### UI confirmation

- [ ] **AC-14:** When capture routing is enabled, the Notes section (and Cmd+K capture) shows a transient confirmation banner after placement: the confirmation string from AC-07, a link to the target file, and a "Move" button that opens a redirect input. The banner auto-dismisses after 10 seconds or on user action. [A13]

- [ ] **AC-15:** The "Move" button on the confirmation banner opens an inline input (text field with vault-path autocomplete from the tree data). Submitting calls `POST /api/capture/{id}/redirect`. The banner updates with the new confirmation. [A13]

### Quality and observability

- [ ] **AC-16:** Redirect events are tracked as `capture_redirects` -- a lightweight counter per `(original_path, redirected_to_path)` pair. This data feeds pattern recognition (AC-17) and routing quality metrics. No separate table; stored as a JSON field on the `captures` row.

- [ ] **AC-17:** (Stage 2 stretch) When the agent observes 3+ redirects with the same pattern (e.g., "grocery" captures always get moved to `lists/groceries.md`), it proposes a routing rule via the approval lane: "I notice you always move grocery captures to lists/groceries.md. Want me to route them there automatically?" Approval creates a `capture_rules` entry the router consults before invoking the LLM. [A12, A2]

---

## Technical Approach

### 1. `captures` table

```sql
CREATE TABLE captures (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    text            TEXT NOT NULL,
    source          TEXT NOT NULL,  -- 'today', 'cmdk', 'chat'
    context         JSONB,          -- source-specific metadata
    status          TEXT NOT NULL DEFAULT 'routing'
                    CHECK (status IN ('routing', 'placed', 'failed')),
    target_path     TEXT,
    target_section  TEXT,
    method          TEXT CHECK (method IN ('append', 'create')),
    reasoning       TEXT,
    fallback        BOOLEAN NOT NULL DEFAULT FALSE,
    error_detail    TEXT,
    redirect        JSONB,          -- { target_hint, new_target_path, new_target_section, redirected_at }
    confirmation    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    placed_at       TIMESTAMPTZ,
    CONSTRAINT text_not_empty CHECK (char_length(trim(text)) > 0)
);
CREATE INDEX ON captures(user_id, created_at DESC);
CREATE INDEX ON captures(user_id, status) WHERE status = 'routing';
-- RLS: user SELECT/UPDATE own rows; INSERT via service role (backend creates on behalf of user).
```

This is a ledger, not a content store. The captured text lives in the vault file after placement; the table is the audit trail plus the redirect mechanism.

### 2. `capture_rules` table (Stage 2 stretch -- AC-17)

```sql
CREATE TABLE capture_rules (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    pattern     TEXT NOT NULL,      -- natural-language pattern description
    matcher     JSONB NOT NULL,     -- structured: { keywords: [], regex?: string }
    target_path TEXT NOT NULL,
    target_section TEXT,
    method      TEXT NOT NULL DEFAULT 'append',
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source      TEXT NOT NULL DEFAULT 'proposed'  -- 'proposed' (from AC-17) or 'user'
);
CREATE INDEX ON capture_rules(user_id) WHERE enabled = TRUE;
-- RLS: user full CRUD on own rows.
```

### 3. CaptureService

```python
class CaptureService:
    """Orchestrates the capture flow: persist -> route -> place -> confirm."""

    def __init__(
        self,
        vault: VaultService,
        today: TodayService,
        system_client,   # for captures table INSERT (service role)
        user_client,     # for captures table SELECT/UPDATE (RLS)
        activity_log: ActivityLogService,
    ):
        ...

    async def create_capture(
        self, user_id: str, text: str, source: str, context: dict | None = None,
    ) -> dict:
        """Persist capture row, dispatch routing, return capture_id."""
        # 1. Check capture_rules for a matching rule (fast path -- no LLM)
        # 2. If no rule matches, dispatch to capture-router agent (async)
        # 3. Return { capture_id, status: "routing" } immediately
        ...

    async def route_capture(self, capture_id: str, user_id: str) -> None:
        """Called by the agent dispatcher. Determines target, writes to vault, updates row."""
        # 1. Read vault tree for structure context
        # 2. Read recent captures for pattern context
        # 3. Invoke capture-router agent with (text, tree, context)
        # 4. Write to target via VaultService
        # 5. Update captures row (status, target_path, confirmation)
        # 6. Log to activity_log
        ...

    async def redirect_capture(
        self, user_id: str, capture_id: str, target_hint: str,
    ) -> dict:
        """Move a placed capture to a new location."""
        # 1. Read original placement from captures row
        # 2. Remove content from original file (reverse the append/create)
        # 3. Interpret target_hint (vault path or natural language)
        # 4. Write to new target
        # 5. Update captures row with redirect info
        # 6. Log to activity_log
        ...

    async def get_capture(self, user_id: str, capture_id: str) -> dict:
        """Return current state of a capture (for polling)."""
        ...
```

### 4. Capture-router agent

The agent is a text file in `data/config/system/agents/capture-router.md`:

```yaml
---
name: capture-router
description: Routes captured text to the right vault location
model: haiku-4.5
tools: [vault_tree, vault_read]
---
```

The agent receives a structured prompt:

```
You are routing a captured thought into a user's vault. Given the text and
the vault structure, determine the best file and section to place it.

## Captured text
{text}

## Vault structure
{tree summary -- folder names, top-level files, recently modified files}

## Context
Source: {source}
Current path: {context.current_path if any}
Recent captures: {last 5 captures with their targets}

## Rules
- If the text clearly relates to an existing file or project folder, route there.
- If the text is a task or to-do, route to today.md's "To do" section.
- If the text mentions a specific person, project, or entity that has a doc, route to that doc.
- If uncertain, route to today.md's "Notes" section (fallback).
- Respond with JSON: { target_path, target_section, method, reasoning, confidence }
```

**Confidence threshold:** if `confidence < 0.6`, fall back to today.md Notes. The threshold is a `user_preferences` column (default 0.6), tunable per user.

**Cost:** Haiku-4.5 at ~$0.25/M input, ~$1.25/M output. A capture prompt is ~500 tokens input, ~100 tokens output. Cost per capture: ~$0.0003. At 50 captures/day: ~$0.015/day. Negligible.

### 5. Routing strategy

The agent's routing decisions follow this priority order:

1. **Capture rules (AC-17):** if a user-approved or user-created rule matches, skip the LLM entirely. This is the fast path.
2. **Explicit path in text:** if the user writes "add to projects/foo.md: ...", parse and honor it.
3. **Entity match:** if the text mentions a known entity (person, project, company) that has a vault doc, route to that doc's Notes or relevant section.
4. **Folder affinity:** if captured from a specific vault context (e.g., user was viewing `projects/website/` when they hit Cmd+K), bias routing toward that subtree.
5. **Content similarity:** compare the text against recent vault file summaries (if available from future entity-refresh workflows).
6. **Fallback:** today.md Notes.

Priorities 3-5 are quality improvements that can be iterated post-launch. The MVP (AC-01 through AC-06) needs only priority 1, 2, and 6 to be functional.

### 6. API contract

**Capture endpoint:**

```
POST /api/capture
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "text": "Need to review the contract before Friday meeting",
  "source": "today",       // "today" | "cmdk" | "chat"
  "context": {             // optional, source-specific
    "current_path": "projects/acme/"
  }
}

Response 202:
{
  "capture_id": "uuid",
  "status": "routing"
}
```

**Capture status (polling):**

```
GET /api/capture/{id}
Authorization: Bearer <jwt>

Response 200:
{
  "capture_id": "uuid",
  "status": "placed",
  "target_path": "projects/acme/contract-review.md",
  "target_section": "Notes",
  "method": "append",
  "confirmation": "Added to projects/acme/contract-review.md under Notes",
  "fallback": false,
  "redirect": null,
  "created_at": "2026-04-21T14:30:00Z",
  "placed_at": "2026-04-21T14:30:02Z"
}
```

**Redirect:**

```
POST /api/capture/{id}/redirect
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "target_hint": "meeting prep for Friday"
}

Response 200:
{
  "capture_id": "uuid",
  "status": "placed",
  "target_path": "meetings/2026-04-25-prep.md",
  "target_section": "Notes",
  "confirmation": "Moved to meetings/2026-04-25-prep.md under Notes",
  "redirect": {
    "from_path": "projects/acme/contract-review.md",
    "target_hint": "meeting prep for Friday",
    "redirected_at": "2026-04-21T14:31:00Z"
  }
}
```

### 7. Completion signal

Stage 2 uses polling. The capture-router agent (Haiku) typically responds in under 2 seconds. The UI polls `GET /api/capture/{id}` at 1-second intervals for up to 10 seconds after submission. If still `"routing"` after 10 seconds, show "Still routing..." with a manual refresh button. Timeout at 30 seconds triggers fallback to today.md.

SSE/WebSocket push for capture completion is explicitly deferred -- the latency budget is generous enough that polling at 1s is indistinguishable from push for the user.

### 8. Frontend changes

**Today NotesSection:** when `capture_routing_enabled` is true, the submit handler calls `POST /api/capture` instead of `POST /api/today/notes`. After submission, a `CaptureConfirmation` banner slides in below the input showing the confirmation text, a link to the target, and a "Move" button. The banner uses the same transient-notification pattern as the existing approval toast.

**Cmd+K extension:** the existing SPEC-046 `CommandPalette` gains a "Capture" action. When the user types text that does not match a file/command, the palette offers "Capture: {text}" as the first suggestion. Selecting it fires `POST /api/capture` with `source: "cmdk"` and `context: { current_path }`.

**Chat integration:** no frontend change. The chat agent's system prompt includes instructions to detect capture intent and invoke the capture service internally. The confirmation appears as a chat message.

**New hook:** `useCaptureHooks.ts` exports `useCreateCapture`, `useCaptureStatus(id)`, `useRedirectCapture`.

**New types:** `api/types/capture.ts` exports `CaptureRequest`, `CaptureResponse`, `CaptureStatus`, `RedirectRequest`.

---

## What Stage 1 Specs Must Preserve

These are constraints on SPEC-045, SPEC-046, and any other Stage 1 spec to avoid boxing out capture.

| Constraint | Why | Which spec |
|------------|-----|------------|
| `VaultService.update_body` must accept any `rel_path`, not just `today.md` | Capture writes to arbitrary vault files | SPEC-045 (already satisfied) |
| `markdown_sections.append_to_section` must work on any markdown file, not just today.md | Capture appends to arbitrary docs | SPEC-045 (already satisfied -- pure function, no today.md coupling) |
| `VaultService` must expose a method to read the vault tree (or SPEC-046 `list_tree` must be callable from services, not just from the router) | Capture-router agent needs tree context | SPEC-046 (verify `list_tree` is a VaultService method, not router-only logic) |
| The Cmd+K palette must support extensible actions (not hardcoded to file search) | Capture adds a "Capture" action | SPEC-046 (verify action extensibility in CommandPalette design) |
| `POST /api/today/notes` must remain functional alongside the new capture endpoint | Backward compatibility; fallback path; users with routing disabled | SPEC-045 (no change needed -- keep the endpoint) |
| `activity_log` table must accept `actor` values beyond the Stage 1 set | Capture logs as `actor: "capture-router"` | SPEC-045 (already satisfied -- `actor` is TEXT, not ENUM) |
| Chat agent system prompt must be modifiable without code change | Capture intent detection is prompt-level, not code-level | SPEC-046 (verify chat agent config is markdown-based) |

---

## Scope

### Out of Scope

- **Voice capture** -- Stage 2 vision mentions voice, but this spec covers text only. Voice capture (Web Speech API or Whisper via MCP) is a separate spec.
- **Rich capture (images, clipboard, files)** -- text only in this spec.
- **Bulk capture / import** -- single thought at a time.
- **Multi-hop redirect** -- one redirect per capture in Stage 2. Chain redirects are a Stage 3+ concern.
- **Automatic vault restructuring** -- the agent routes to existing structure. Proposing new folders or reorganizing the vault is Stage 4 (entity docs) or Stage 5 (orchestration proposals).
- **Real-time collaborative editing** -- single-user write via VaultService. Concurrent capture from two tabs uses the existing mtime-based conflict resolution from SPEC-045.
- **Full NLP intent parsing for chat capture** -- Stage 2 uses keyword detection ("remember", "note to self", "capture:"). Sophisticated intent parsing is a model capability upgrade, not spec scope.
- **Capture from Telegram or other channels** -- web surfaces only in Stage 2. Cross-channel capture (A7) is a later concern.

### Dependencies

| Dependency | Status | Blocking? |
|------------|--------|-----------|
| SPEC-045 (VaultService, today.md, approval lane, activity_log) | In progress on `spec/SPEC-045-today` | Yes -- VaultService is the write path |
| SPEC-046 (vault shell, tree API, Cmd+K, chat rail) | Draft | Yes -- entry points depend on shell surfaces |
| SPEC-049 (chat surfaces, not yet written) | Not started | Soft -- AC-13 (chat capture) can ship without a dedicated chat spec if the chat rail from SPEC-046 is functional |
| Capture-router agent definition | New (ships with this spec) | No -- authored as part of this spec's implementation |

---

## Edge Cases

- **Empty vault (new user):** vault tree has only `today.md` and system defaults. Agent always falls back to today.md Notes. This is correct -- there is nowhere better to route until the user builds vault structure.
- **Capture text is very long (>10KB):** reject at the API level with 413. Captures are thoughts, not documents. If a user needs to create a long document, they use the file editor (SPEC-047).
- **Target file does not exist and method is "append":** agent mismatch. CaptureService falls back: create the file with the capture as content, log a warning. The routing is still correct from the user's perspective.
- **Target file was deleted between routing and write:** VaultService.update_body creates parent dirs and writes. The file reappears. Log the event.
- **Two captures route to the same file simultaneously:** VaultService uses mtime-based conflict detection. Second write gets 409, retries with fresh body. Same pattern as SPEC-045 concurrent notes.
- **User redirects to a path that does not exist:** the redirect agent interprets the hint and may create a new file. If the hint is ambiguous, the redirect fails gracefully and the agent asks for clarification (in the confirmation banner or chat).
- **Agent returns a target_path outside the user's vault:** `VaultService._resolve` rejects it with 403. CaptureService catches the 403 and falls back to today.md. Security boundary is unchanged.
- **Agent timeout (>30s):** CaptureService catches the timeout, places the capture in today.md Notes, updates the row with `fallback: true` and `error_detail: "routing_timeout"`. User's thought is never lost.
- **Capture routing is disabled but user hits Cmd+K capture:** Cmd+K capture always uses the `POST /api/capture` endpoint regardless of the `capture_routing_enabled` toggle. The toggle only affects the Today Notes input (AC-11). Cmd+K is an explicit "I want smart routing" gesture.
- **Rate limiting:** captures are user-initiated, so natural rate limits apply. As a safety valve, cap at 100 captures per user per hour. Return 429 beyond that.

---

## Testing Requirements

### Unit Tests

- `test_capture_service.py`: create -> route -> place round-trip; fallback on low confidence; fallback on agent error; redirect updates row and moves content; redirect on non-placed capture returns 409; activity_log entries emitted.
- `test_capture_router_agent.py`: mock agent responses; verify routing decision parsing; confidence threshold enforcement; fallback behavior.
- `test_capture_rules.py` (stretch): rule matching; rule skips LLM; disabled rules ignored.

### Integration Tests

- `test_capture_api.py`: auth required; `POST /api/capture` returns 202; `GET /api/capture/{id}` returns placed status after routing; cross-user isolation (user B cannot read user A's captures); redirect round-trip; 413 on oversized text; 429 on rate limit.
- `test_capture_vault_write.py`: capture places content in the correct vault file; redirect removes from original and places in new target; fallback writes to today.md.

### UI Tests (Playwright)

- `test_ac_11_notes_routing_toggle`: with routing enabled, Notes submit shows confirmation banner with target link; with routing disabled, Notes submit behaves as SPEC-045 (immediate append).
- `test_ac_12_cmdk_capture`: Cmd+K palette offers "Capture" action; submitting shows confirmation.
- `test_ac_14_confirmation_banner`: banner appears after placement; link navigates to target file; "Move" button opens redirect input.
- `test_ac_15_redirect_flow`: redirect input accepts text; submission updates banner with new target.

### Manual Verification

1. Capture "call dentist tomorrow" from Today Notes with routing enabled -- verify it routes to today.md's To Do section (not Notes), confirm banner shows.
2. Capture "review the Acme contract" from Cmd+K while viewing `projects/acme/` -- verify it routes to a file under `projects/acme/`.
3. After step 2, click "Move" and type "today" -- verify content moves to today.md Notes.
4. In chat rail, type "remember to buy milk" -- verify agent responds with capture confirmation.
5. Create 5+ captures mentioning "groceries" and redirect each to `lists/groceries.md` -- verify the agent proposes a routing rule (AC-17 stretch).
6. Capture with an empty vault (new user) -- verify fallback to today.md Notes.
7. Verify `captures` table has audit trail for all captures, including redirects.

---

## Pattern Recognition Model (AC-17 stretch goal)

The pattern recognition feature is explicitly a **stretch goal** for Stage 2. It ships if routing quality is good enough that the system has meaningful redirect data to learn from. If Stage 2 focuses on getting basic routing right, pattern recognition defers to Stage 3.

The model is simple:

1. A background job (daily or on-demand) scans recent captures for the current user.
2. Groups captures by `(original target, redirect target)` pairs.
3. When a pair has 3+ occurrences, generates a proposed `capture_rule` and submits it to the approval lane as a `workflow_proposal` card: "I notice you always move [pattern] captures to [target]. Want me to route them there automatically?"
4. User approves -> rule is created in `capture_rules` and consulted before LLM routing.
5. User rejects -> the pattern is marked as rejected and not re-proposed for 30 days.

This is Transaction #5 from the vision ("Orchestration proposal") applied to capture. It demonstrates the self-improvement loop without requiring the full Stage 5 workflow-authoring capability.

---

## Resolved Questions (2026-04-21, Tim approved all recommendations)

### 1. Routing model — **RESOLVED: asynchronous**

`POST /api/capture` returns 202 immediately, UI polls at 1s. Haiku latency makes it feel synchronous in practice; async foundation handles edge cases cleanly.

### 2. Today Notes toggle — **RESOLVED: toggle for conservative rollout**

`capture_routing_enabled` preference, default `false`. Enables shadow-mode validation of routing quality before switching the default.

### 3. Pattern recognition (AC-17) — **RESOLVED: in-scope as stretch**

AC-17 explicitly marked as stretch. Implementation team skips if routing quality work consumes the time budget.

---

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-17)
- [x] ACs are testable (each has a clear verification path)
- [x] API contracts are concrete (endpoint paths, request/response shapes, status codes)
- [x] Technical approach cites architecture principles (A1, A2, A8, A10, A12, A13, A14)
- [x] Dependencies enumerated with blocking status
- [x] Edge cases documented with expected behavior
- [x] Stage 1 preservation constraints are explicit (table of what must not change)
- [x] Out-of-scope is explicit
- [x] Agent model and cost estimated
- [x] Testing requirements map to ACs
- [x] Decisions requiring input are flagged with options and recommendations
- [x] Exit criterion from vision doc referenced (working memory externalized)
