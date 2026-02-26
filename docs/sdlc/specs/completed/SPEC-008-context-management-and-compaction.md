# SPEC-008: Context Management & Compaction

> **Status:** Draft
> **Author:** Tim + Claude
> **Created:** 2026-02-18
> **Updated:** 2026-02-18

## Goal

Prevent long-running agent conversations from hitting context window limits by implementing tiered context management: tool output pruning, conversation compaction with pre-compaction memory flush, and session-level token tracking. This is the foundation for "always-on" agent sessions that can run indefinitely without degrading.

## Problem

Today, every agent invocation ships the full chat history to the LLM:
- No pruning of old tool results (CRUDTool outputs, Gmail search results, etc.)
- No compaction — history grows unbounded until it exceeds the context window
- No token tracking per session — we don't know how close we are to the limit
- When the context window is exceeded, the API returns a 400 error and the session is broken
- The agent's LTM (from SPEC-006) provides cross-session memory, but there's no mechanism to consolidate in-session knowledge before it's lost to compaction

## Prior Art: OpenClaw

This spec is heavily informed by [OpenClaw](https://github.com/openclaw/openclaw)'s three-layer context management:

1. **Session pruning** — Trims old tool results in-memory before each LLM call. Soft-trim (head+tail with `...`) for oversized results, hard-clear (placeholder replacement) for old results. Tied to cache TTL for cost optimization.

2. **Compaction** — Summarizes older conversation into a single entry, persisted in session history. Future turns see `[summary] + [recent messages]`.

3. **Pre-compaction memory flush** — Before compacting, the system injects a synthetic agent turn: "You're about to lose context. Save anything durable to memory now." The agent writes to disk, replies with a silent token, and the user never sees it. The gateway (not the agent) owns this decision.

Key design insight: the agent never decides what to forget. The system decides *when* to forget, gives the agent one chance to consolidate, then prunes mechanically.

## Acceptance Criteria

### Token Tracking (prerequisite)
- [ ] AC-1: Each agent invocation estimates token count of the message payload before sending to the LLM
- [ ] AC-2: `chat_sessions` tracks cumulative `total_tokens` (input + output) per session
- [ ] AC-3: Token estimates are available to the compaction threshold check

### Tool Output Pruning
- [ ] AC-4: Tool results older than N assistant turns are soft-trimmed (keep first 1500 + last 1500 chars, insert `...`)
- [ ] AC-5: Tool results older than M assistant turns are hard-cleared (replaced with `[Tool result cleared]`)
- [ ] AC-6: Pruning is configurable per agent via `agent_configurations.config`
- [ ] AC-7: User/assistant messages are never modified by pruning

### Pre-Compaction Memory Flush
- [ ] AC-8: When session token count exceeds `context_window - reserve_tokens - flush_threshold`, a flush turn fires
- [ ] AC-9: Flush turn injects a synthetic user message instructing the agent to save durable context to LTM
- [ ] AC-10: Flush turn uses the agent's existing `save_memory` tool (from SPEC-006)
- [ ] AC-11: Flush response is suppressed — user never sees it (silent token convention)
- [ ] AC-12: Flush fires at most once per compaction cycle (tracked in session metadata)

### Conversation Compaction
- [ ] AC-13: When session token count exceeds `context_window - reserve_tokens`, compaction triggers
- [ ] AC-14: Compaction summarizes older messages into a single system message using a secondary LLM call
- [ ] AC-15: Compacted summary + recent messages replace the full history for subsequent turns
- [ ] AC-16: Compaction summary is persisted in the session (not just in-memory)
- [ ] AC-17: Recent N assistant turns are preserved verbatim (not compacted)

### Cost Controls
- [ ] AC-18: Compaction summary call uses a cheaper model (Haiku) regardless of the session's primary model
- [ ] AC-19: Flush turn uses the session's primary model (needs full tool access and context understanding)

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/services/context_manager.py` | Token estimation, pruning, compaction orchestration |
| `chatServer/services/compaction_service.py` | Compaction logic: summarize history, build compacted payload |
| `tests/chatServer/services/test_context_manager.py` | Token estimation, pruning logic tests |
| `tests/chatServer/services/test_compaction_service.py` | Compaction + flush tests |
| `supabase/migrations/YYYYMMDD_add_session_token_tracking.sql` | Add token tracking columns to chat_sessions |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/chat.py` | Integrate context manager: prune before LLM call, check compaction threshold after, track tokens |
| `chatServer/models/chat.py` | Add token tracking fields to session models |
| `chatServer/config/settings.py` | Add compaction/pruning config defaults |

### Out of Scope

- Vector memory search / semantic retrieval (future spec — upgrade path from SPEC-006's text blob LTM)
- Temporal decay on memory (requires structured memory, not text blob)
- Cross-session compaction (each session is independent)
- Frontend UI for context usage (future spec — could show a context window gauge)
- Multi-agent shared context management (different problem; relevant to SDLC orchestrator)

## Technical Approach

### Unit 1: Token Tracking (backend-dev)

**Branch:** `feat/SPEC-008-token-tracking`

Add token estimation to the chat service. We don't need exact counts — estimates are sufficient for threshold decisions.

```python
# chatServer/services/context_manager.py

class ContextManager:
    """Manages context window budget for agent sessions."""

    def __init__(self, context_window: int = 200_000, reserve_tokens: int = 20_000):
        self.context_window = context_window
        self.reserve_tokens = reserve_tokens

    def estimate_tokens(self, messages: list[dict]) -> int:
        """Rough token estimate: chars / 4. Good enough for threshold decisions."""
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        return total_chars // 4

    def should_compact(self, estimated_tokens: int) -> bool:
        return estimated_tokens > (self.context_window - self.reserve_tokens)

    def should_flush(self, estimated_tokens: int, flush_threshold: int = 4000) -> bool:
        return estimated_tokens > (self.context_window - self.reserve_tokens - flush_threshold)
```

**Migration:** Add `total_tokens_estimate INTEGER DEFAULT 0` and `compaction_count INTEGER DEFAULT 0` to `chat_sessions`.

### Unit 2: Tool Output Pruning (backend-dev)

**Branch:** `feat/SPEC-008-tool-pruning`

Applied in-memory before each LLM call. Never modifies the persisted session history.

```python
class ContextManager:
    # ...

    def prune_tool_results(
        self,
        messages: list[dict],
        keep_last_assistants: int = 3,
        soft_trim_max_chars: int = 4000,
        head_chars: int = 1500,
        tail_chars: int = 1500,
    ) -> list[dict]:
        """Prune old tool results to reduce context size.

        - Messages after the last `keep_last_assistants` assistant messages: untouched
        - Older tool results > soft_trim_max_chars: head + ... + tail
        - User/assistant messages: never modified
        """
```

Design decisions:
- Only `tool` role messages are candidates for pruning
- Image/attachment content blocks are skipped (never trimmed)
- The pruned messages list is used for the LLM call only — the original history stays intact in the DB

### Unit 3: Pre-Compaction Memory Flush (backend-dev) — blocked by Unit 1, SPEC-006

**Branch:** `feat/SPEC-008-memory-flush`

When `should_flush()` returns true, inject a synthetic turn before the real user message:

```python
FLUSH_SYSTEM_PROMPT = (
    "Pre-compaction memory flush. The session is near its context limit. "
    "Review the conversation and save any durable context to memory using save_memory. "
    "Include user preferences, decisions, key facts, and anything that should persist. "
    "Reply with SILENT after saving, or SILENT if nothing needs saving."
)

SILENT_TOKEN = "SILENT"

async def run_memory_flush(
    self,
    agent_executor,
    session_id: str,
    messages: list[dict],
) -> bool:
    """Run a silent memory flush turn. Returns True if flush executed."""
    # Check if already flushed this compaction cycle
    if self._already_flushed(session_id):
        return False

    # Inject flush prompt as a synthetic user message
    flush_messages = messages + [{"role": "user", "content": FLUSH_SYSTEM_PROMPT}]

    # Run agent turn — it may call save_memory tool
    response = await agent_executor.ainvoke({"input": FLUSH_SYSTEM_PROMPT, ...})

    # Check for silent token — suppress response if present
    response_text = str(response.get("output", ""))
    if SILENT_TOKEN in response_text.upper():
        # Don't persist this turn to chat history — user never sees it
        pass
    else:
        # Unusual: agent had something to say. Log but don't deliver.
        logger.info(f"Memory flush produced non-silent response for session {session_id}")

    # Mark flushed for this compaction cycle
    self._mark_flushed(session_id)
    return True
```

Key design point: the flush turn is **not persisted** to the chat session history. It's a ghost turn — it happened (and its side effects like `save_memory` calls persist), but the conversation doesn't record it.

### Unit 4: Conversation Compaction (backend-dev) — blocked by Unit 1

**Branch:** `feat/SPEC-008-compaction`

When `should_compact()` returns true (after flush has had its chance):

```python
COMPACTION_PROMPT = (
    "Summarize the following conversation into a concise summary that preserves:\n"
    "- Key decisions and agreements\n"
    "- Important context about the user's goals\n"
    "- Any open questions or pending items\n"
    "- Tool results that are still relevant\n\n"
    "Be concise but complete. This summary will replace the conversation history."
)

async def compact_session(
    self,
    messages: list[dict],
    keep_recent: int = 5,
) -> list[dict]:
    """Compact older messages into a summary, keeping recent turns verbatim."""
    if len(messages) <= keep_recent * 2:
        return messages  # Too few messages to compact

    old_messages = messages[:-keep_recent * 2]  # Messages to summarize
    recent_messages = messages[-keep_recent * 2:]  # Messages to keep

    # Use Haiku for cost efficiency
    summary = await self._generate_summary(old_messages, model="claude-haiku-4-5-20251001")

    # Build compacted history
    compacted = [
        {"role": "system", "content": f"[Session compacted. Summary of prior conversation:]\n\n{summary}"},
        *recent_messages,
    ]

    return compacted
```

The compacted history replaces the in-memory message list and is persisted as the session's new baseline. The original messages can be retained in an archive table if needed for debugging, but are not sent to the LLM.

### Integration in chat.py

The existing `chat.py` service gains a context management step:

```python
# Pseudocode for the modified chat flow
async def handle_message(user_id, session_id, user_message):
    messages = await load_chat_history(session_id)
    context_mgr = ContextManager(context_window=200_000)

    # Step 1: Estimate tokens
    estimated = context_mgr.estimate_tokens(messages)

    # Step 2: Memory flush if near threshold
    if context_mgr.should_flush(estimated):
        await context_mgr.run_memory_flush(agent_executor, session_id, messages)

    # Step 3: Compact if over threshold
    if context_mgr.should_compact(estimated):
        messages = await context_mgr.compact_session(messages)
        await persist_compacted_history(session_id, messages)

    # Step 4: Prune tool results (in-memory only)
    pruned_messages = context_mgr.prune_tool_results(messages)

    # Step 5: Normal agent invocation with pruned messages
    response = await agent_executor.ainvoke({"input": user_message, "chat_history": pruned_messages})

    # Step 6: Track tokens
    await update_session_tokens(session_id, estimated + response_tokens)
```

### Dependencies

```
SPEC-006 (LTM + save_memory tool) ──┐
                                     ├── Unit 3 (memory flush)
Unit 1 (token tracking) ────────────┤
                                     ├── Unit 4 (compaction)
Unit 2 (tool pruning) ──────────────┘  (independent, can start immediately)
```

Unit 2 (pruning) has no dependencies and is the quickest win.

## Testing Requirements

### Unit Tests

**`tests/chatServer/services/test_context_manager.py`:**
- `test_estimate_tokens_empty_messages`
- `test_estimate_tokens_proportional_to_content`
- `test_should_compact_below_threshold_returns_false`
- `test_should_compact_above_threshold_returns_true`
- `test_should_flush_fires_before_compact`
- `test_prune_preserves_recent_tool_results`
- `test_prune_soft_trims_oversized_old_results`
- `test_prune_hard_clears_very_old_results`
- `test_prune_never_modifies_user_messages`
- `test_prune_never_modifies_assistant_messages`
- `test_prune_skips_image_content_blocks`

**`tests/chatServer/services/test_compaction_service.py`:**
- `test_compact_preserves_recent_messages`
- `test_compact_summarizes_old_messages`
- `test_compact_uses_haiku_model`
- `test_compact_noop_when_few_messages`
- `test_memory_flush_calls_save_memory_tool`
- `test_memory_flush_suppresses_silent_response`
- `test_memory_flush_fires_once_per_cycle`
- `test_memory_flush_skipped_when_already_flushed`

### Integration Tests

- `test_long_session_triggers_compaction` — Send enough messages to exceed threshold, verify compaction fires
- `test_flush_then_compact_preserves_ltm` — Verify save_memory is called before history is lost
- `test_pruned_session_still_produces_coherent_responses` — Agent can follow conversation after pruning

### Manual Verification (UAT)

- [ ] Start a long conversation (20+ turns with tool use) — verify no 400 errors
- [ ] Check that compaction summary makes sense (read from DB)
- [ ] Verify LTM was updated during flush (check `agent_long_term_memory` table)
- [ ] After compaction, agent still references key facts from early in conversation

## Configuration Defaults

```python
# chatServer/config/settings.py additions
context_window: int = 200_000          # Claude's context window
reserve_tokens: int = 20_000           # Buffer for response + system prompt
flush_threshold: int = 4_000           # Flush fires this many tokens before compaction
keep_recent_turns: int = 5             # Assistant turns preserved during compaction
prune_keep_last_assistants: int = 3    # Tool results after this many assistant turns are untouched
prune_soft_trim_chars: int = 4_000     # Tool results larger than this get soft-trimmed
compaction_model: str = "claude-haiku-4-5-20251001"  # Cheap model for summarization
```

## Cost Analysis

**Compaction summary (Haiku):**
- Input: ~5000-10000 tokens (old conversation to summarize)
- Output: ~500-1000 tokens (summary)
- Cost: ~$0.005 per compaction
- Frequency: Once per ~50-100 turns (depends on tool output volume)

**Memory flush (session model):**
- Input: Full context + flush prompt
- Output: save_memory tool call + SILENT
- Cost: Same as one normal turn (unavoidable — needs full context to decide what to save)
- Frequency: Once per compaction cycle

**Pruning:**
- Zero LLM cost — pure string manipulation in Python
- Reduces subsequent LLM call costs by shrinking input tokens

## Future Considerations

- **Streaming compaction status** — Show user "Organizing conversation..." while compaction runs
- **Compaction quality scoring** — Verify summary captures key facts (could use a second LLM pass)
- **Tiered memory** — Replace text blob LTM with structured, searchable memory (vector store)
- **Cross-channel compaction** — Compact across web + Telegram sessions for the same user
- **Agent-initiated memory** — Let the agent proactively save memories during normal conversation, not just during flush (requires prompt engineering to avoid over-saving)
