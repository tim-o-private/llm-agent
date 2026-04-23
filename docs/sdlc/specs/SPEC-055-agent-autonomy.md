# SPEC-055: Agent Autonomy and Action Orientation

> **Status:** Draft
> **Author:** Tim + Claude (Product)
> **Created:** 2026-04-21
> **Updated:** 2026-04-21
> **Vision:** [`docs/product/VISION.md`](../product/VISION.md)
> **Depends On:** SPEC-043 (Deep Agents runtime), SPEC-037 (Initial Workflows), SPEC-044 (bwrap Sandbox)

---

## Goal

Transform Clarity from an **informative assistant** into an **autonomous agent** that exercises judgment and takes action. The infrastructure — tools, approval tiers, scheduled execution — already exists. This spec changes **agent behavior** (prompts, tool guidance) and adds **tool expansion** (agent requests new tools, user grants them) so the agent acts instead of reports.

Safety is enforced by the existing approval tier system (`AUTO_APPROVE`, `REQUIRES_APPROVAL`, `USER_CONFIGURABLE`). The agent does not need a separate trust architecture — it simply needs permission to use the tools it has, and a way to request tools it doesn't.

Success looks like: the user says "handle my morning email" and the agent archives noise, drafts replies, creates tasks, and reports what it did — not what it found.

---

## Existing Infrastructure (what we reuse verbatim)

| Primitive | Location | What we use it for |
|-----------|----------|---------------------|
| Approval tiers | `chatServer/security/approval_tiers.py` | `AUTO_APPROVE` reads execute immediately; `REQUIRES_APPROVAL` writes queue for user approval; `USER_CONFIGURABLE` lets user override per tool |
| Tool loading | `src/core/agent_loader_db.py` — `load_tools_from_db()` | Tools instantiated per user from DB config; agent only gets tools assigned to it |
| Scheduled execution | `chatServer/services/scheduled_execution_service.py` | Heartbeat, email digest, briefings — we change the prompts they send |
| Deep Agent runtime | `chatServer/services/deep_agent_builder.py` | Agent loop; we change system prompt and tool guidance |
| `user_tool_preferences` table | existing migration | User overrides for `USER_CONFIGURABLE` tools |
| `pending_actions` table | existing migration | Queue for `REQUIRES_APPROVAL` tool executions |
| `agent_execution_results` table | existing migration | Audit trail for scheduled runs |
| Memory tools | `chatServer/tools/memory_tools.py` | Agent stores what it learned |

---

## Model: Tool Grants + Approval Tiers

The agent has access to a subset of tools configured in `agent_tools`. Within those tools, the approval tier system enforces safety:

- **AUTO_APPROVE:** Agent uses freely (read-only: search_gmail, get_tasks, search_memories)
- **REQUIRES_APPROVAL:** Agent uses, execution queues for user approval (send_email, delete_tasks)
- **USER_CONFIGURABLE:** User flipped the switch; agent uses or queues based on preference

**Tool expansion:** If the agent needs a tool it doesn't have (e.g. "I need Calendar to check conflicts"), it calls `request_tool` which creates an approval card. User grants → tool added to agent config → available on next run.

**No graduation system.** No domain tiers. No evidence thresholds. The agent either has a tool and uses it within approval constraints, or it doesn't have it and requests it.

---

## Acceptance Criteria

### Prompt Redesign — Heartbeat

- [ ] **AC-01:** The heartbeat prompt instructs the agent to **take low-risk actions** using available tools. Specifically: archive clearly low-priority emails, mark calendar invites as accepted when appropriate, and create tasks for anything with a deadline. The agent uses `AUTO_APPROVE` tools directly without asking. [F3, F6]
- [ ] **AC-02:** If heartbeat finds nothing actionable, respond `HEARTBEAT_OK`. If it takes action, report a 1-2 sentence summary of **what it did**, not what it found. [F3]
- [ ] **AC-03:** Heartbeat actions requiring `REQUIRES_APPROVAL` tools create `pending_actions` via the normal approval flow. The agent does not ask permission in the chat — it calls the tool, the approval system intercepts, user approves later. [A12]

### Prompt Redesign — Email Digest

- [ ] **AC-04:** The email digest prompt instructs the agent to **act on email** before summarizing: archive noise, draft replies to scheduling emails, create tasks for deadlines. After acting, give a 2-3 sentence summary of what it did and what needs user attention. [F1, F3]
- [ ] **AC-05:** If the agent lacks tools needed for the digest (e.g. Gmail disconnected), it requests the tool via `request_tool` and reports what it couldn't do. [F3]

### New: End-of-Day Agent

- [ ] **AC-06:** A new scheduled agent `end_of_day` runs at configurable time (default 18:00 user-local). It reviews: (a) emails not responded to → drafts replies as pending actions, (b) tasks due tomorrow → bumps to notification, (c) calendar conflicts tomorrow → alerts user. [F6]
- [ ] **AC-07:** End-of-day agent stores a daily summary memory: "Today I archived 12 newsletters, drafted 2 replies, created 1 task." [F5]

### Tool Request Flow

- [ ] **AC-08:** New tool `request_tool(tool_name: str, reason: str)` available to all agents. When called, it creates an `approval_card` with type `tool_request`. User approves → tool added to agent's config in `agent_tools` table. [F3]
- [ ] **AC-09:** Agent guidance includes: "If you need a tool you don't have, call `request_tool`. Never apologize for lacking tools — just request them." [F3]
- [ ] **AC-10:** Tool request cards render in the UI with tool name, reason, and Grant/Deny buttons. Denied requests are remembered; agent does not re-request the same tool for 7 days. [F3]

### Action Journal and Self-Correction

- [ ] **AC-11:** Every autonomous action is logged to the **action journal**: timestamp, tool used, input summary, result, user reaction. Stored via `create_memories` with `memory_type='episodic'`, tags `['action_journal']`. [F5]
- [ ] **AC-12:** Agent loads last 20 action journal entries into context on every scheduled run via `search_memories(query='recent actions', tags=['action_journal'])`. [F5]
- [ ] **AC-13:** When user corrects an agent (rejects approval card, undoes action), agent stores `memory_type='episodic'`, tags `['correction']`, describing what was wrong. Loaded on next run. [F5]
- [ ] **AC-14:** Agent tool guidance includes a "Self-correction" section: "If corrected, store what you learned. Search corrections before acting. Never make the same mistake twice in the same week." [F5]

---

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/services/action_journal_service.py` | Write and query action journal entries via MemoryClient |
| `chatServer/tools/autonomy_tools.py` | `RequestTool` — creates tool request approval cards |
| `chatServer/prompts/heartbeat_v2.md` | Action-oriented heartbeat system prompt |
| `chatServer/prompts/email_digest_v2.md` | Triage-first digest system prompt |
| `chatServer/prompts/end_of_day.md` | End-of-day agent system prompt |
| `chatServer/prompts/self_correction_guidance.md` | Tool guidance for all agents: act, don't report; correct and learn |
| `supabase/migrations/20260421000001_tool_request_cards.sql` | Add `tool_request` to `approval_card_type` enum; `tool_requests` table tracks denied tools with cooldown |
| `tests/unit/services/test_action_journal_service.py` | Journal write/query, memory integration |
| `tests/unit/tools/test_autonomy_tools.py` | RequestTool schema, prompt sections |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/deep_agent_builder.py` | Load `self_correction_guidance.md` into tool guidance for all agents. Add action journal context loading on scheduled runs. Replace heartbeat/digest channel text with v2 prompts. |
| `chatServer/services/scheduled_execution_service.py` | Use `heartbeat_v2.md` for heartbeat. Use `email_digest_v2.md` for digest. Add end-of-day dispatch. |
| `chatServer/services/email_digest_service.py` | Update default prompt to triage-first. Load action journal before invocation. Write journal after run. |
| `chatServer/security/approval_tiers.py` | Add `request_tool` to `TOOL_APPROVAL_DEFAULTS` as `AUTO_APPROVE`. |
| `src/core/agent_loader_db.py` | Register `RequestTool` in `TOOL_REGISTRY`. |
| `webApp/src/components/today/approvals/ToolRequestCard.tsx` | Render tool request approval cards with Grant/Deny. |
| `webApp/src/api/types/today.ts` | Add `tool_request` to `ApprovalCard` union. |

### Out of Scope

- **Trust graduation system** — no tiers, no proposals, no evidence thresholds, no 14-day cooldowns. Cut entirely.
- **Trust tier UI panel** — users manage tool access via approval cards, not a settings panel.
- **Per-domain tracking** — approval tiers are per-tool, not per-domain.
- **ML-based judgment** — heuristics only.
- **Undo of autonomous actions** — logged but not reversible in this spec.

---

## Technical Approach

### 1. Prompt Architecture Changes

For scheduled channels (`scheduled`, `heartbeat`), add an **Action Context** section to the system prompt:

```
## Action Context
You have these tools: {tool_list}.
AUTO_APPROVE tools: use freely without asking.
REQUIRES_APPROVAL tools: call them; the system will queue for user approval.
If you need a tool you don't have, call request_tool.

Recent actions you've taken:
{action_journal_entries}

Recent corrections from the user:
{correction_memories}

Do not narrate your reasoning. Do the work and report what you did.
```

`ActionContextService` (new, ~60 lines) gathers:
- Tool list from agent config
- Approval tier labels for each tool
- Last 20 action journal entries via `search_memories(tags=['action_journal'])`
- Last 10 corrections via `search_memories(tags=['correction'])`

### 2. Heartbeat V2 Prompt

Replace `_CHANNEL_HEADERS["heartbeat"]`:

```markdown
## Channel
Automated heartbeat. No one is waiting.

Your job: maintain the user's inbox and calendar.
1. Search Gmail for unread email from last 4 hours
2. For each email:
   - Newsletter / marketing / automated → archive it
   - Scheduling / from known contact → draft reply (creates pending action)
   - Has a deadline → create task
   - Unclear → leave unread
3. Check calendar for next 4 hours
4. Check tasks due today

Rules:
- Use your tools. Do not describe what you would do — do it.
- Archive liberally. When in doubt, archive.
- If nothing needs attention → respond exactly HEARTBEAT_OK
- If you took action → report what you did in 1-2 sentences
- If you lack Gmail access → request_tool("search_gmail", "I need to check email for the heartbeat")
- Never fabricate
```

### 3. Email Digest V2 Prompt

```markdown
## Channel
Automated email processing.

Your job: process unread email from last 24 hours.

Step 1 — Act:
- Search Gmail for unread
- Archive newsletters, promotions, automated noise
- Draft replies to scheduling emails (pending action)
- Create tasks for anything with a deadline
- Flag truly urgent items

Step 2 — Report:
- What you archived (count)
- What you drafted (pending actions created)
- What needs user attention today
- What tasks you created

Keep under 150 words. Report what you did, not what you found.
```

### 4. End-of-Day Agent

New scheduled agent, configured in `agent_configurations`:

- **Name:** `end_of_day`
- **Schedule:** Daily at 18:00 user-local (column `end_of_day_time` on `user_preferences`, default '18:00')
- **Tools:** Gmail, Tasks, Calendar, Memory (whatever the user has granted)
- **Prompt:** from `end_of_day.md`

```markdown
## Channel
End-of-day review.

Your job: prepare the user for tomorrow.
1. Search Gmail for emails received today with no reply
   - Important ones → draft reply, create pending action
2. Get tasks due tomorrow or overdue
   - Overdue → notify user
   - Due tomorrow → add to summary
3. Check calendar for tomorrow
   - Conflicts? Alert immediately
4. Store daily summary memory

Report in 3 sentences max.
```

### 5. Tool Request Flow

```python
class RequestTool(BaseTool):
    name = "request_tool"
    description = "Request access to a tool you don't currently have."

    async def _arun(self, tool_name: str, reason: str) -> str:
        # 1. Check if tool already denied within 7 days
        # 2. Create approval_card with type='tool_request'
        # 3. Return "Tool request submitted. User will review."
```

**Grant flow:**
1. User sees card: "Agent requests Calendar: 'I need to check conflicts in the heartbeat'"
2. User clicks Grant → tool added to `agent_tools` for this agent
3. Agent has tool on next invocation

**Deny flow:**
1. User clicks Deny → row inserted into `tool_requests` (user_id, tool_name, denied_at)
2. Agent blocked from re-requesting same tool for 7 days

### 6. Action Journal

Every tool call writes a journal entry:

```json
{
  "timestamp": "2026-04-21T14:30:00Z",
  "tool": "search_gmail",
  "input_summary": "unread newsletters last 4h",
  "result_summary": "found 12, archived 12",
  "pending_actions_created": 0
}
```

Stored via `create_memories`:
- `memory_type='episodic'`
- `tags=['action_journal']`
- `text` = JSON string

Loaded into context on scheduled runs (last 20 entries).

### 7. Self-Correction Guidance

Loaded into all agents' tool guidance:

```
## Self-Correction
- Act first, report after. Don't narrate reasoning.
- If the user corrects you, store a correction memory immediately.
- Search corrections before taking similar actions.
- Never make the same mistake twice in one week.
- If you lack a tool, request it. Never apologize for not having tools.
```

---

## Testing Requirements

### Unit Tests

- `test_action_journal_service.py`: write/query, 20-entry limit, memory integration
- `test_autonomy_tools.py`: RequestTool schema, cooldown logic, card creation

### Integration Tests

- `test_heartbeat_v2.py`: heartbeat archives newsletters (mock Gmail), creates tasks, reports actions
- `test_digest_v2.py`: digest triages before summarizing, writes action journal
- `test_tool_request.py`: agent requests tool → card created → grant adds tool → deny blocks re-request

### Manual Verification

1. Trigger heartbeat with mock newsletters. Verify archived, not just reported.
2. Trigger heartbeat with scheduling email. Verify pending action created.
3. Run digest. Verify triage happens before summary.
4. Remove Gmail from agent tools. Trigger heartbeat. Verify agent requests tool via card.
5. Grant tool request. Verify next run has Gmail.
6. Deny tool request. Verify agent does not re-request for 7 days.
7. Correct agent (reject archive). Verify correction memory stored. Next run searches corrections.

---

## Edge Cases

- **Gmail disconnected:** agent requests tool or skips; notes in summary; no error notification
- **No tools assigned:** agent requests all needed tools; user gets batch of request cards
- **Tool request denied:** 7-day cooldown; agent instructed not to apologize or repeatedly ask
- **Action journal grows large:** last 20 entries loaded; older entries in DB but not context
- **Correction loop:** if user corrects same thing 3 times, agent stores escalating priority tag
- **End-of-day with no data:** agent reports "Nothing to prepare — you're all set for tomorrow"

---

## Functional Units (for PR Breakdown)

1. **Unit 1:** Migration + tool request schema (`feat/SPEC-055-migration`)
2. **Unit 2:** Action journal + autonomy tools (`feat/SPEC-055-autonomy`)
3. **Unit 3:** Prompt redesign (heartbeat v2, digest v2, end-of-day) (`feat/SPEC-055-prompts`)
4. **Unit 4:** Frontend tool request cards (`feat/SPEC-055-ui`)
5. **Unit 5:** Tests + integration (`feat/SPEC-055-tests`)

Merge order: 1 → 2 → 3 → 4 → 5

---

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-14)
- [x] Every AC maps to at least one functional unit
- [x] Cross-domain boundaries: schema → API → UI
- [x] Technical decisions reference principles: A1, A8, F3, F5
- [x] Merge order explicit and acyclic
- [x] Out-of-scope explicit (graduation system cut)
- [x] Edge cases documented
- [x] Testing requirements map to ACs
