# SPEC-021: Agent Bootstrap Architecture & Tool Resilience

> **Status:** Draft
> **Author:** Tim + Claude
> **Created:** 2026-02-24
> **Branch:** `feat/spec-021-bootstrap-resilience`

## Goal

Redesign the session_open bootstrap so the agent greets users instantly from pre-computed context instead of burning LLM turns on tool calls. Add Gmail rate limiting, search result truncation, and error resilience so tool failures don't silently eat agent responses.

## Background

The current bootstrap flow was observed in production (trace `019c90df`):

1. Frontend calls `/session_open` → triggers `[SYSTEM: First session. No user message. Begin bootstrap.]`
2. Agent prompt says "check tasks, memories, Gmail before responding" (Operating Model + Session Open guidance)
3. Agent fires 4 parallel tool calls: `get_context`, `get_tasks`, `get_reminders`, `search_gmail`
4. `search_gmail` returns full email bodies for 10 unread messages across 2 accounts → **~120K tokens**
5. Second LLM call (tool results as scratchpad) hits **135K input tokens** → Anthropic 429 (input token rate limit exhausted)
6. SDK retries after 13s, LLM responds with `create_memories` tool calls but **no text content**
7. Agent returns `output: []` → user sees nothing. 34 seconds elapsed, $0+ burned.

Three systemic issues exposed:
- **No data diet:** `search_gmail` returns full bodies in bulk — never useful and catastrophic for token budgets
- **No context pre-computation:** Agent wastes LLM turns (and money) gathering data the backend could pre-fetch
- **No resilience:** Tool errors, LLM rate limits, and empty outputs propagate silently to the user
- **No Gmail rate limiting:** Google API calls are unmetered — risk of quota exhaustion under load

## Acceptance Criteria

### Phase 1: Data Diet & Gmail Hardening

#### Gmail Search Truncation

- [ ] **AC-01:** `search_gmail` uses a subclass of `langchain_google_community.gmail.search.GmailSearch` that overrides `_parse_messages` to use `format="metadata"` (with `metadataHeaders=["Subject","From","Date"]`) instead of `format="raw"`. Batching via `BatchHttpRequest` is preferred but optional for v1. Returns message ID, subject, sender, snippet (from list response), and date. No body. [A14]
- [ ] **AC-02:** `get_gmail` remains the only path to full message bodies. Its description explicitly says "use this to read full email content after finding messages with search_gmail." [A10]
- [ ] **AC-03:** `search_gmail` default `max_results` reduced from 10 to 5 for interactive channels (`web`, `telegram`, `session_open`). Scheduled/heartbeat channels keep 10. [A14]

#### Gmail Rate Limiting

- [ ] **AC-04:** Gmail tool calls are rate-limited per user: max **30 API calls per minute**, **500 per hour**, **5000 per day**. Limits apply to the underlying Google API calls (each `search_gmail` = 1 list + N get calls; each `get_gmail` = 1 get call). [A14]
- [ ] **AC-05:** Rate limit state is tracked in-memory per `(user_id, account_email)` tuple using the existing `RateLimitInfo` pattern from `base_api_service.py`. [A8]
- [ ] **AC-06:** When rate limit is hit, tool returns a clear message: `"Gmail rate limit reached (X/minute). Try again in Y seconds."` — not an exception. The agent can still respond using other tools. [A14]
- [ ] **AC-07:** Rate limit counters are logged at WARN level when >80% consumed. [A14]

### Phase 2: Bootstrap Prompt Rewrite

Bootstrap (first session, new user) fires when the user has no tasks, no reminders, no memories, and no instructions. There's nothing to pre-fetch — the agent's job is to introduce itself and start learning about the user.

#### Session Open Prompt Rewrite

- [ ] **AC-08:** `SESSION_OPEN_BOOTSTRAP_GUIDANCE` rewritten to focus on introduction and learning, **not data gathering**. The agent should NOT call `get_tasks`, `get_reminders`, or `search_gmail` on bootstrap — there's nothing to find. New guidance focuses on: introduce yourself, explain what you can do, ask one concrete question to start learning about the user. May call `create_memories` to record initial observations. [A2]
- [ ] **AC-09:** `SESSION_OPEN_RETURNING_GUIDANCE` updated: for returning users, pre-computed context (from `$bootstrap_context`) replaces tool-call instructions. Agent reads the summary from its prompt instead of calling tools. [A2]
- [ ] **AC-10:** `OPERATING_MODEL` updated: the "Before responding: 1. Check tasks 2. Recall memories" instructions are gated to `web`/`telegram` channels only (interactive, user-initiated). `session_open` channel excluded. [A2]
- [ ] **AC-11:** `ONBOARDING_SECTION` updated to match — remove "check emails, tasks, reminders" step. [A2]

#### Returning User Context Pre-Computation

- [ ] **AC-12:** For **returning users only** (not bootstrap), a lightweight `BootstrapContextService` gathers context before the LLM: task summary (count by status, overdue items), reminder summary (count, next due), email summary (unread count per account, no content). Injected as `$bootstrap_context` in the system prompt. [A1, A8]
- [ ] **AC-13:** `BootstrapContextService` calls are non-LLM — direct DB queries and API calls. Wall time target: <2s. Individual source failures → "(unavailable)". [A14]

#### Onboarding Conversation Design

The bootstrap prompt rewrite (AC-08, AC-11) implements the onboarding conversation described in PRD-001 Workstream 1. Key product decisions:

- **Email connection is NOT mandatory.** Agent must be useful before any integration.
- **Agent frames what it is** — one sentence explaining purpose (chief of staff, help get time back), not a feature list. Users have never encountered a system like this; they need enough context to understand what's possible.
- **One good question** — "What's eating your time right now?" or equivalent. Open-ended, not interrogative.
- **Real conversation** — agent responds to what user says, records to memory, breaks down goals if mentioned.
- **Suggest email connection when natural** — if user mentions email, suggest it. Don't force it.
- **No-email path is a real path** — task management, conversation, planning all work without email. Agent can re-suggest email at natural moments later.
- **Today page + auto-opened chat panel IS the onboarding** — no separate onboarding page. `/coach` page is deprecated.

See `docs/product/PRD-001-make-it-feel-right.md` Workstream 1 for full product context.

> **Resolved:** Gmail onboarding digest (background processing on connect) is now SPEC-023.

#### Executor Limits

- [ ] **AC-14:** Session_open agent executor created with `max_iterations=3` and `max_execution_time=15` (seconds). If exceeded, the agent returns gracefully with whatever it has. [A14]
- [ ] **AC-15:** Interactive (`web`/`telegram`) agent executor gets `max_iterations=10` and `max_execution_time=60`. Current default (15 iterations, no time limit) is too permissive. [A14]

### Phase 3: Error Resilience

#### Tool Error Handling

- [ ] **AC-16:** `CustomizableAgentExecutor` catches `httpx.HTTPStatusError` (429, 5xx) during LLM calls and returns a user-friendly message: `"I'm having trouble connecting right now. Here's what I was able to gather: {partial_results}"`. The agent does NOT silently return empty output. [A14]
- [ ] **AC-17:** When `agent_executor.ainvoke()` returns `output: []` (empty content blocks) or `output: ""`, `session_open_service` returns `silent: true` instead of forwarding empty/nonsense text. Log at ERROR level. [A14]
- [ ] **AC-18:** All tool `_arun` methods that call external APIs (Gmail, memory server) must catch exceptions and return error strings — never raise. Current `search_gmail` already does this; audit and fix any tools that don't. [A14]

#### Anthropic Rate Limit Awareness

- [ ] **AC-19:** `ChatAnthropic` instantiation sets `max_retries=2` (default is 2, but be explicit) and `max_tokens=2048` (up from default 1024, gives the model more room for the greeting after tool calls). [A14]
- [ ] **AC-20:** Add a `token_budget_warning` log: if assembled system prompt exceeds 50K tokens (estimated via `len(prompt) / 4`), log at WARN level before invoking the LLM. This catches token bombs before they hit rate limits. [A14]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/tools/gmail_rate_limiter.py` | Per-user Gmail API rate limiter |
| `chatServer/services/bootstrap_context_service.py` | Pre-compute task/reminder/email context for returning users |
| `tests/chatServer/tools/test_gmail_rate_limiter.py` | Rate limiter unit tests |
| `tests/chatServer/services/test_bootstrap_context_service.py` | Bootstrap context unit tests |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/tools/gmail_tools.py` | Override `_parse_messages` for metadata-only search, integrate rate limiter, adjust `max_results` per channel |
| `chatServer/services/prompt_builder.py` | Rewrite `SESSION_OPEN_BOOTSTRAP_GUIDANCE`, `SESSION_OPEN_RETURNING_GUIDANCE`, `ONBOARDING_SECTION`. Add `$bootstrap_context` placeholder support. |
| `chatServer/services/session_open_service.py` | Inject bootstrap context for returning users |
| `src/core/agent_loader_db.py` | Pass `max_iterations` and `max_execution_time` per channel |
| `chatServer/services/notification_service.py` | Handle empty output → silent response |
| `tests/chatServer/services/test_prompt_builder.py` | Update for new constants |
| `tests/chatServer/services/test_session_open_service.py` | Test bootstrap context injection |
| `tests/chatServer/tools/test_gmail_tools.py` | Test metadata-only search format |

### Out of Scope

## Non-Goals

- **Email body summarization** (LLM-based) — future work if search snippets aren't enough
- **Streaming session_open responses** — bootstrap should be fast enough (<3s) that streaming isn't needed
- **Gmail push notifications** — separate feature; this spec is about controlling outbound API usage
- **Refactoring `base_api_service.py`** — Gmail rate limiting uses the pattern but doesn't require inheriting from the class (tools are `BaseTool`, not `BaseAPIService`)

## Implementation Notes

### Gmail Rate Limiter

Create a standalone `GmailRateLimiter` class (not a subclass of `BaseAPIService`) that `BaseGmailTool` holds a reference to. Singleton per process, keyed by `(user_id, account_email)`. Can reuse `RateLimitInfo` dataclass.

```python
# chatServer/tools/gmail_rate_limiter.py
class GmailRateLimiter:
    """In-memory rate limiter for Gmail API calls."""
    _limits: Dict[Tuple[str, str], RateLimitInfo] = {}

    @classmethod
    def check_and_increment(cls, user_id: str, account: str) -> Optional[str]:
        """Returns None if OK, error message string if limited."""
```

### Bootstrap Context Assembly (Returning Users Only)

```python
# chatServer/services/bootstrap_context_service.py
@dataclass
class BootstrapContext:
    tasks_summary: str       # "3 active tasks (1 overdue). Top: 'Call dentist' (overdue 1d)"
    reminders_summary: str   # "2 upcoming reminders. Next: 'Review UAT' in 4 days"
    email_summary: str       # "t.p.obrien@gmail.com: 10 unread. tim@sundaycarpenter.com: 8 unread"

    def render(self) -> str:
        """Format as prompt section text."""
```

Not used during bootstrap (new user) — only for returning user session_open. Memory notes are already pre-fetched by `prompt_builder.py`.

### Search Result Format Change

**Current flow** (`GmailSearch._parse_messages` — N+1 API calls, full bodies):
```
messages.list(q=query, maxResults=10)  →  10 message IDs
messages.get(id=X, format="raw")       →  ×10 sequential calls, each downloads full email
LangChain parses raw bytes, extracts body  →  ~120K tokens of email content
```

**New flow** (subclass overrides `_parse_messages` — N+1 calls but lightweight):
```
messages.list(q=query, maxResults=5)   →  5 message IDs + snippets
messages.get(id=X, format="metadata", metadataHeaders=["Subject","From","Date"])  ×5
→  no body download, just headers. Optional: batch via BatchHttpRequest for 1 roundtrip.
```

The subclass is ~20 lines — override `_parse_messages`, swap `format="raw"` for `format="metadata"`, extract headers from the metadata response instead of parsing raw bytes. The `GmailToolProvider.get_gmail_tools()` method already wraps LangChain's toolkit; we just substitute our subclass for the search tool in that list.

Before:
```
=== t.p.obrien@gmail.com ===
[{'id': '19c90daa...', 'threadId': '...', 'snippet': '...', 'body': '<full HTML body ~5KB>', 'subject': '...', 'sender': '...'}]
```

After:
```
=== t.p.obrien@gmail.com ===
1. [19c90daa] "Run failed: claude-code-review.yml" — from: notifications@github.com — Feb 24
2. [19c90da3] "PR #85 merged" — from: notifications@github.com — Feb 24
3. ...
(Use get_gmail with message ID and account for full content)
```

Google's `BatchHttpRequest` sends up to 100 requests as a single multipart HTTP call. For 5-10 messages this means **2 API calls total** (1 list + 1 batch) instead of 11-21.

## Risks

| Risk | Mitigation |
|------|------------|
| Returning-user context may be stale by the time agent responds | Context is computed <2s before LLM call — acceptable staleness for greetings |
| Bootstrap greeting without data may feel empty | By design — focus on learning about the user, not showing off empty data. Gmail onboarding digest (future spec) will fill memory before the agent needs it |
| Gmail rate limits may be too restrictive for power users | Limits are per-user, match Google's own quotas, and return clear messages (not errors) |
| In-memory rate limits reset on server restart | Acceptable for v1 — Google's own quotas are the hard backstop |

## Migration Path

1. **All three phases can ship independently**
2. **Phase 2 bootstrap rewrite** is the fastest win — pure prompt changes, no code for the new-user path
3. **Phase 2 returning-user context** needs the `BootstrapContextService` but doesn't depend on Phase 1
4. Recommended order: Phase 2 (bootstrap prompt) → Phase 1 (gmail hardening) → Phase 3 (error resilience) → Phase 2 (returning-user context service)

## Testing

- **Unit:** `search_gmail` returns summary-only format; rate limiter blocks after threshold
- **Unit:** `BootstrapContextService` returns valid context when individual sources fail (returning user path)
- **Unit:** Empty `output` from executor triggers silent response in session_open_service
- **Integration:** New user bootstrap completes in <5s with zero tool calls, produces a greeting
- **Integration:** Returning user session_open uses pre-computed context, no redundant tool calls
- **Integration:** Gmail rate limiter correctly tracks calls across search + get sequences
- **UAT:** New user bootstrap shows introduction + question, no "No text content" errors
- **UAT:** Returning user session_open shows task/reminder summary from pre-computed context

### AC-to-Test Mapping

| AC | Test Type | Test Function |
|----|-----------|--------------|
| AC-01 | Unit | `test_search_gmail_returns_metadata_only` |
| AC-02 | Unit | `test_get_gmail_returns_full_body` |
| AC-03 | Unit | `test_search_gmail_max_results_by_channel` |
| AC-04 | Unit | `test_rate_limiter_blocks_after_threshold` |
| AC-05 | Unit | `test_rate_limiter_keyed_per_user_account` |
| AC-06 | Unit | `test_rate_limiter_returns_message_not_exception` |
| AC-07 | Unit | `test_rate_limiter_warns_at_80_percent` |
| AC-08 | Unit + UAT | `test_bootstrap_guidance_no_tool_calls` |
| AC-09 | Unit | `test_returning_user_uses_bootstrap_context` |
| AC-10 | Unit | `test_operating_model_excluded_session_open` |
| AC-11 | Unit | `test_onboarding_section_no_tool_calls` |
| AC-12 | Unit | `test_bootstrap_context_service_returns_summaries` |
| AC-13 | Unit | `test_bootstrap_context_service_handles_failures` |
| AC-14 | Unit | `test_session_open_executor_limits` |
| AC-15 | Unit | `test_interactive_executor_limits` |
| AC-16 | Unit | `test_executor_catches_rate_limit_errors` |
| AC-17 | Unit | `test_empty_output_returns_silent` |
| AC-18 | Unit | `test_tool_arun_never_raises` |
| AC-19 | Unit | `test_chat_anthropic_explicit_settings` |
| AC-20 | Unit | `test_token_budget_warning_logged` |

### Manual Verification (UAT)

- [ ] New user opens app — sees greeting within 3 seconds, no tool calls, agent asks one question
- [ ] New user has a conversation — agent records memories, breaks down goals if mentioned
- [ ] New user is NOT prompted to connect email unless they mention it
- [ ] Returning user opens app — sees quick summary from pre-computed context
- [ ] Returning user with nothing in flight — gets `WAKEUP_SILENT` (no notification)
- [ ] Gmail search returns metadata only (no email bodies)
- [ ] Rate limiter triggers after threshold — agent gets clear message, continues with other tools
- [ ] Empty agent output → user sees nothing (silent), no error shown

## Functional Units (for PR Breakdown)

1. **FU-1:** Gmail data diet — metadata-only search, max_results per channel (`feat/SPEC-021-gmail-diet`)
2. **FU-2:** Gmail rate limiter (`feat/SPEC-021-rate-limiter`)
3. **FU-3:** Bootstrap prompt rewrite — SESSION_OPEN_BOOTSTRAP_GUIDANCE, ONBOARDING_SECTION, OPERATING_MODEL gating (`feat/SPEC-021-bootstrap-prompt`)
4. **FU-4:** Bootstrap context service — BootstrapContextService + session_open integration + returning user guidance (`feat/SPEC-021-bootstrap-context`)
5. **FU-5:** Error resilience — executor limits, empty output handling, tool error audit, token budget warning (`feat/SPEC-021-resilience`)

**Merge order:** FU-1 → FU-2 (parallel OK) → FU-3 → FU-4 → FU-5

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-20)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (Gmail API → tool → prompt → service)
- [x] Technical decisions reference principles (A1, A2, A8, A10, A14)
- [x] Merge order is explicit and acyclic
- [x] Out-of-scope is explicit
- [x] Edge cases documented (in Risks table)
- [x] Testing requirements map to ACs
