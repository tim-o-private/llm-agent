# SPEC-040: Introspection Loop

> **Status:** Draft
> **Author:** Claude (Spec Writer)
> **Created:** 2026-04-06
> **Updated:** 2026-04-06
> **PRD:** Architecture Proposal (Phase 3, Item 13)
> **Architecture:** `docs/product/ARCHITECTURE-PROPOSAL-next-gen.md`, Phase 3
> **Behavior Spec:** `docs/product/PRODUCT-BEHAVIOR-SPEC-next-architecture.md`, Sections 4.5, 4.6

## Goal

Give the agent a scheduled self-review capability that analyzes its own performance and proposes improvements. The introspection loop runs as a workflow template on the SPEC-036 workflow engine, runs inside the bwrap sandbox (SPEC-038), and is constrained by the security boundary (SPEC-039). It can modify prompts, create new workflow templates, update preferences, and request capability upgrades — but it cannot touch security config.

This is the "brain" that closes the feedback loop: user interactions produce performance data, the agent analyzes patterns, proposes config changes, and better interactions follow.

## Background

The product behavior spec (Section 4.6) states:

> The agent periodically introspects on its own performance and can: create new workflows, improve prompts, or propose new capabilities (subject to modification tier rules).

HQ already demonstrates this pattern informally — Claude Code updates memory, adjusts approaches, and surfaces process improvements. The difference: HQ does it conversationally with Tim. Clarity does it autonomously via a structured workflow with git tracking and user notification.

### What Makes This Different from Memory

Memory (SPEC-018, current) stores observations about the user — "Tim prefers concise briefings," "Sarah's writing style is informal." Memory is data the agent accumulates.

The introspection loop acts on that data: it reads memory, reads interaction history, identifies patterns, and modifies the agent's own config to improve future behavior. Memory is input; config changes are output.

### Relationship to Other Specs

| Spec | Relationship |
|------|-------------|
| **SPEC-036** (Workflow Engine) | The introspection loop is a workflow template that runs on the engine. Uses `AnthropicEngine` for analysis steps. |
| **SPEC-038** (bwrap Sandbox) | Loop runs inside the sandbox. Reads from `/system/` (current config), writes to `/user/` (improvements). |
| **SPEC-039** (Security Boundary) | All writes go to `/user/` (mutable layer). Security changes proposed via `request_capability_upgrade` tool. Git tracking + notification for all changes. |
| **SPEC-037** (Initial Workflows) | Template format reference. The introspection loop follows the same template structure. |
| **SPEC-035** (Config Service) | System config (prompts, workflow templates) loaded via overlay. User overrides stored in `/user/`. |

## Dependencies

| Dependency | What It Provides | Status |
|-----------|-----------------|--------|
| SPEC-036 (Workflow Engine) | Template runtime, scheduling, checkpointing | Draft |
| SPEC-038 (bwrap Sandbox) | Filesystem for reading config + writing improvements | Draft (this sprint) |
| SPEC-039 (Security Boundary) | Modification tier enforcement, git tracking, notifications | Draft (this sprint) |
| SPEC-035 (Config Service) | Config overlay (system defaults + user overrides) | Draft (in progress) |
| SPEC-024 (Notification Feedback) | Feedback buttons — source of user satisfaction signals | Complete |
| SPEC-018 (Proactive Memory) | Agent memory — source of user observations | Complete |
| SPEC-026 (Job Queue) | Scheduling via `JobService` | Complete |

## Acceptance Criteria

### FU-1: Introspection Workflow Template

- [ ] **AC-01:** A workflow template `introspection-loop.md` exists at `system/workflows/introspection-loop.md` in the config bucket (Supabase Storage). It follows the SPEC-036/037 template format (Markdown with YAML frontmatter). [A2]
- [ ] **AC-02:** The template defines four steps: `gather-signals` (collect performance data), `analyze-patterns` (identify improvement opportunities), `propose-changes` (generate specific config modifications), `apply-changes` (carry out approved modifications in sandbox). All steps except `apply-changes` have `gate_policy: none`. `apply-changes` has `gate_policy` determined by trust tier (see AC-16). [A1]
- [ ] **AC-03:** The `gather-signals` step uses tools `[search_memories, read_file, list_files]` and accepts parameters: `period_days` (default 7 — how far back to analyze), `focus_areas` (optional list — e.g., `["email_triage", "briefing_quality"]` to focus analysis). It collects: (1) user feedback signals from the last N days (feedback button data from SPEC-024), (2) interaction patterns (message counts, tool usage, error rates from audit log), (3) current config state (reads key files from `/user/` and `/system/`), (4) agent memory observations. Outputs structured signal data. [A6]
- [ ] **AC-04:** The `analyze-patterns` step receives gathered signals and identifies improvement opportunities. It produces a structured analysis: (1) what's working well (retain), (2) what's degraded or underperforming (fix), (3) what's missing or could be added (create), (4) capability gaps (request). The analysis is grounded in specific data — each finding cites the signal that surfaced it. No tools needed — pure LLM analysis. [A14]
- [ ] **AC-05:** The `propose-changes` step receives the analysis and generates concrete, actionable config modifications. Each proposal specifies: `file_path` (which file to modify), `change_type` (create/update/delete), `diff_preview` (what the change looks like), `rationale` (why this improves performance), `expected_impact` (what should get better), `risk` (what could go wrong). Proposals are ordered by expected impact. No tools needed — pure LLM generation. [A14]
- [ ] **AC-06:** The `apply-changes` step receives approved proposals and carries them out inside the sandbox. It uses tools `[write_file, read_file]` and sandbox commands to modify config files in `/user/`. Each change is committed separately (per SPEC-038 AC-27 auto-commit) with a descriptive message: `"Introspection: {rationale}"`. The step verifies each change was applied correctly by reading the file back. [A6, A13]
- [ ] **AC-07:** A seed migration uploads the template and its step prompts to the config bucket. [A3]

### FU-2: Signal Gathering

- [ ] **AC-08:** The `gather-signals` step collects user feedback from the `notification_feedback` table (SPEC-024): count of positive/negative/neutral feedback per category (briefing, email, general) over the analysis period. Aggregated — not individual messages. [A3]
- [ ] **AC-09:** The step collects interaction metrics from the audit log: total messages, tool invocations per tool, tool error rates, average response latency (if tracked), session duration. These are read via a dedicated `introspection_metrics` view or query, not by scanning raw audit rows. [A3, A14]
- [ ] **AC-10:** The step reads current config from the sandbox filesystem: `/user/agent/instructions.md` (current user instructions), `/user/preferences/*.yaml` (current preferences), `/user/workflows/*.md` (custom workflows), `/user/memory/observations.md` (agent observations). It also reads `/system/agents/clarity/soul.md` to understand the base personality it's working from. [A13]
- [ ] **AC-11:** The step reads recent memory entries via `search_memories` tool with filters: entity types `user_preference`, `communication_style`, `feedback`, created within the analysis period. These represent the agent's learned understanding of the user. [A6]

### FU-3: Analysis + Proposal Generation

- [ ] **AC-12:** The `analyze-patterns` step prompt instructs the LLM to be conservative: propose only changes with clear signal support. The prompt includes anti-patterns: "Do not propose changes based on a single interaction. Do not modify prompts that are working well. Do not add complexity unless simplicity has failed." [A14]
- [ ] **AC-13:** The `propose-changes` step limits proposals to a maximum of 3 per introspection run. This prevents overwhelming the user with changes and limits blast radius if something goes wrong. The step prioritizes the highest-impact proposals. [A14]
- [ ] **AC-14:** Each proposal's `diff_preview` is a concrete, applicable diff — not a vague description. For YAML files, it shows the exact key-value changes. For Markdown files, it shows the exact text being added/modified/removed. The `apply-changes` step can use the proposal without further interpretation. [A14]
- [ ] **AC-15:** Proposals that touch elevated-review paths (per `modification_policy.yaml`) are flagged with `elevated: true`. These get more prominent notifications regardless of trust tier. [A12]

### FU-4: Trust-Tier-Aware Gating

- [ ] **AC-16:** The `apply-changes` step's gate policy is determined by the user's trust tier for `self_improvement`: at **Inform** tier, `gate_policy: "human-required"` — user must approve each change before it's applied. At **Recommend** tier, `gate_policy: "none"` — changes are applied and user is notified after. At **Act** tier, `gate_policy: "none"` — changes are applied silently (user sees in monthly digest). [A12]
- [ ] **AC-17:** When the gate is active (Inform tier), the human gate presents each proposal to the user with: the file being changed, the diff preview, the rationale, and approve/reject buttons. The user can approve individual proposals (selective application) or approve/reject all. [A12, F1]
- [ ] **AC-18:** Rejected proposals are recorded in `/user/memory/rejected_proposals.md` with the proposal content and rejection timestamp. The agent should not re-propose rejected changes in subsequent introspection runs unless new signal data supports it. [A14]

### FU-5: Scheduling + Configuration

- [ ] **AC-19:** A `handle_introspection` job handler is registered for `job_type = "introspection"`. It calls `WorkflowRunManager.start_run("introspection-loop", params)` and self-schedules the next run. [A1]
- [ ] **AC-20:** The introspection schedule is configurable via `user_preferences` — new columns: `introspection_enabled` (BOOLEAN DEFAULT false), `introspection_interval_days` (INTEGER DEFAULT 7), `introspection_focus_areas` (JSONB DEFAULT '[]'). The agent can propose enabling introspection as a capability upgrade (SPEC-039 AC-29). [A13]
- [ ] **AC-21:** A migration adds the introspection preference columns to `user_preferences`. Default is disabled — the agent must be explicitly enabled for self-improvement. [A3]
- [ ] **AC-22:** The `ManageBriefingPreferencesTool` (or a new `ManagePreferencesTool` if the scope outgrows briefings) supports an `introspection` section: `action: "update"` with `preferences: {introspection_enabled, introspection_interval_days, introspection_focus_areas}`. [A6]

### FU-6: Changelog + Conversational Access

- [ ] **AC-23:** The agent can answer "what have you changed about yourself?" by reading the git log from the sandbox: `run_command("git -C /user log --oneline --since='30 days ago'")`. The agent presents a human-readable summary grouped by category (prompt changes, preference changes, new workflows). [A13]
- [ ] **AC-24:** The agent can answer "why did you change X?" by reading the commit message for a specific change: `run_command("git -C /user log --format='%B' -1 {sha}")`. The introspection loop's commit messages include the rationale, making this self-documenting. [A13]
- [ ] **AC-25:** The agent can show a before/after comparison: `run_command("git -C /user diff {sha}~1 {sha}")`. This lets the user see exactly what changed in any self-modification. [A13]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `config/system/workflows/introspection-loop.md` | Introspection workflow template |
| `config/system/workflows/prompts/introspection-loop/gather-signals.md` | Signal gathering step prompt |
| `config/system/workflows/prompts/introspection-loop/analyze-patterns.md` | Analysis step prompt |
| `config/system/workflows/prompts/introspection-loop/propose-changes.md` | Proposal generation step prompt |
| `config/system/workflows/prompts/introspection-loop/apply-changes.md` | Change application step prompt |
| `chatServer/workflows/nodes/introspection_metrics.py` | Metrics gathering from audit log + feedback table |
| `supabase/migrations/2026MMDD000001_seed_introspection_template.sql` | Upload template to config bucket |
| `supabase/migrations/2026MMDD000002_introspection_preferences.sql` | Add preference columns |
| `supabase/migrations/2026MMDD000003_introspection_metrics_view.sql` | Create metrics view for signal gathering |
| `tests/chatServer/workflows/test_introspection_template.py` | Template parsing + step validation |
| `tests/chatServer/workflows/test_introspection_metrics.py` | Metrics gathering tests |
| `tests/chatServer/workflows/test_introspection_scheduling.py` | Scheduling integration tests |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/job_handlers.py` | Add `handle_introspection` handler |
| `chatServer/services/background_tasks.py` | Register introspection handler with `JobRunnerService` |
| `chatServer/tools/briefing_tools.py` (or new `preference_tools.py`) | Add introspection preference management |
| `chatServer/database/user_scoped_tables.py` | Add introspection preference columns |

### Out of Scope

- **Automatic introspection enablement.** The agent must be explicitly enabled for introspection. The agent can propose it via `request_capability_upgrade`, but the user activates it.
- **Cross-user learning.** The introspection loop analyzes one user's data only. Aggregate patterns across users are a future (and privacy-sensitive) concern.
- **Capability development.** The loop can propose new workflow templates but cannot write new tool code or modify the Capability Gateway. Code changes require human developers.
- **Real-time adaptation.** The loop runs periodically (weekly default), not in real-time. Per-interaction adaptation happens via memory (existing), not config changes.
- **A/B testing changes.** The loop applies one version at a time. Running parallel configs to compare is future scope.

## Technical Approach

### 1. introspection-loop.md Template

```markdown
---
name: introspection-loop
description: Scheduled self-review -- analyze performance, propose improvements, apply changes
version: 1
default_gate_policy: none
---

# Introspection Loop

Periodic self-review workflow that analyzes agent performance data,
identifies improvement opportunities, and applies config changes
within the mutable layer.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| period_days | no | Analysis period in days (default: 7) |
| focus_areas | no | Specific areas to focus on (default: all) |
| trust_tier | yes | User's self_improvement trust tier (inform/recommend/act) |

## Steps

### step-1: Gather Signals
- **agent:** signal-gatherer
- **depends_on:** []
- **tools:** [search_memories, read_file, list_files]
- **description:** Collect performance data: user feedback, interaction metrics,
  current config state, agent memory. Output structured signal data for analysis.
- **gate:** none

### step-2: Analyze Patterns
- **agent:** pattern-analyzer
- **depends_on:** [step-1]
- **tools:** []
- **model:** claude-sonnet-4-5-20250514
- **description:** Identify what's working, what's degraded, what's missing, and
  what capabilities are needed. Ground every finding in specific signal data.
  Be conservative -- only flag genuine patterns.
- **gate:** none

### step-3: Propose Changes
- **agent:** improvement-proposer
- **depends_on:** [step-2]
- **tools:** []
- **model:** claude-sonnet-4-5-20250514
- **description:** Generate up to 3 concrete config modifications. Each proposal
  includes: file path, change type, exact diff, rationale, expected impact, risk
  assessment. Order by expected impact.
- **gate:** none

### step-4: Apply Changes
- **agent:** config-editor
- **depends_on:** [step-3]
- **tools:** [write_file, read_file]
- **description:** Carry out approved proposals in the sandbox. Write each change,
  verify it, and commit with rationale. Skip rejected proposals.
- **gate_policy:** dynamic
- **gate_resolver:** trust_tier
```

### 2. Step Prompts

#### gather-signals.md

```markdown
# Signal Gathering for Introspection

You are collecting performance data for the agent's periodic self-review.

## What to Collect

1. **User Feedback** -- Use search_memories to find feedback-tagged memories
   from the last {period_days} days. Count positive/negative by category.

2. **Current Config** -- Read these files from the sandbox:
   - /user/agent/instructions.md (user instructions)
   - /user/preferences/*.yaml (all preference files)
   - /user/memory/observations.md (your observations)
   - /system/agents/clarity/soul.md (base personality -- read-only reference)

3. **Interaction History** -- Read /user/memory/ for recent interaction patterns.

4. **Focus Areas** -- If specific focus_areas are provided, prioritize
   data collection for those areas.

## Output Format

Return structured JSON:
{
  "period": {"start": "ISO date", "end": "ISO date"},
  "feedback": {"positive": N, "negative": N, "by_category": {...}},
  "config_state": {"instructions_summary": "...", "preferences": {...}},
  "observations": ["key observation 1", "..."],
  "interaction_patterns": {"messages_per_day": N, "top_tools": [...]}
}

Be thorough but concise. Raw data is not needed -- summarize patterns.
```

#### analyze-patterns.md

```markdown
# Pattern Analysis for Introspection

You are analyzing performance data to identify improvement opportunities.

## Anti-Patterns (DO NOT do these)

- Do not propose changes based on a single interaction or data point
- Do not modify prompts/config that are working well (if positive feedback
  and no issues, leave it alone)
- Do not add complexity unless simplicity has demonstrably failed
- Do not propose changes that contradict the user's explicit instructions
- Do not re-propose previously rejected changes (check rejected_proposals.md)

## Analysis Structure

For each finding, provide:

1. **What's Working** -- Behaviors with positive signal. These are retained.
2. **What's Degraded** -- Behaviors with negative signal or increasing errors.
   Cite the specific data (e.g., "3 negative feedback on briefing length
   in the last week").
3. **What's Missing** -- Capabilities or behaviors the user seems to want
   but the agent doesn't currently provide. Cite interaction patterns
   (e.g., "user asked about calendar 5 times but no calendar workflow exists").
4. **Capability Gaps** -- Tools or permissions the agent needs but doesn't have.
   These become capability upgrade requests, not config changes.

## Output

Return structured findings. Each finding must cite specific signal data.
Maximum 5 findings per category.
```

#### propose-changes.md

```markdown
# Improvement Proposal Generation

You are generating concrete config modifications based on the analysis.

## Rules

- Maximum 3 proposals per run
- Order by expected impact (highest first)
- Each proposal must be immediately actionable -- no ambiguity
- Proposals must include exact file paths and exact content changes
- For YAML: show exact key-value pairs to add/modify/remove
- For Markdown: show exact text changes

## Proposal Format

For each proposal, output JSON:
{
  "file_path": "/user/preferences/communication.yaml",
  "change_type": "update",
  "diff_preview": "- briefing_length: 500\n+ briefing_length: 300",
  "rationale": "3 negative feedback signals on briefing length this week.
    User consistently skims past the second half.",
  "expected_impact": "Shorter briefings, higher completion rate, better signal",
  "risk": "May miss important context. Mitigated by keeping 3-5 item format.",
  "elevated": false
}

For capability gaps (things that require security config changes):
{
  "type": "capability_request",
  "tool_name": "send_email_reply",
  "requested_tier": "act",
  "current_tier": "recommend",
  "justification": "User has approved all 12 draft replies over 3 weeks with
    no reverts. The approve step adds friction without adding safety."
}
```

### 3. Dynamic Gate Resolution

The `apply-changes` step has a dynamic gate that depends on the user's trust tier. The workflow engine (SPEC-036) needs a small extension:

```python
# In GraphBuilder, when building the apply-changes node:
def _resolve_gate_policy(self, step: StepDef, user_id: str) -> str:
    """Resolve dynamic gate policy based on user's trust tier."""
    if step.gate_resolver == "trust_tier":
        tier = self._trust_tier_resolver.get_tier(
            user_id, "self_improvement"
        )
        if tier == "inform":
            return "human-required"
        else:
            return "none"  # recommend + act = apply without gate
    return step.gate_policy
```

### 4. Metrics View

```sql
-- supabase/migrations/2026MMDD000003_introspection_metrics_view.sql

CREATE OR REPLACE VIEW introspection_metrics AS
SELECT
    user_id,
    date_trunc('day', created_at) as day,
    COUNT(*) FILTER (WHERE event_type = 'message') as message_count,
    COUNT(*) FILTER (WHERE event_type = 'tool_invocation') as tool_invocations,
    COUNT(*) FILTER (WHERE event_type = 'tool_error') as tool_errors,
    COUNT(DISTINCT session_id) as session_count
FROM audit_log
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY user_id, date_trunc('day', created_at);

-- Feedback aggregation
CREATE OR REPLACE VIEW introspection_feedback AS
SELECT
    user_id,
    category,
    COUNT(*) FILTER (WHERE sentiment = 'positive') as positive_count,
    COUNT(*) FILTER (WHERE sentiment = 'negative') as negative_count,
    COUNT(*) FILTER (WHERE sentiment = 'neutral') as neutral_count,
    date_trunc('week', created_at) as week
FROM notification_feedback
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY user_id, category, date_trunc('week', created_at);
```

### 5. Job Handler

```python
# In chatServer/services/job_handlers.py

async def handle_introspection(job: dict) -> dict:
    """Run introspection loop as a workflow."""
    user_id = job["input"]["user_id"]

    # Get user preferences
    prefs = await get_user_preferences(user_id)
    trust_tier = await get_trust_tier(user_id, "self_improvement")

    # Dispatch workflow
    run_manager = get_workflow_run_manager()
    run_id = await run_manager.start_run(
        user_id=user_id,
        template_name="introspection-loop",
        parameters={
            "period_days": prefs.introspection_interval_days,
            "focus_areas": prefs.introspection_focus_areas or [],
            "trust_tier": trust_tier,
        },
    )

    # Self-schedule next run
    next_time = (
        datetime.now(timezone.utc)
        + timedelta(days=prefs.introspection_interval_days)
    )
    job_service = JobService(get_db_pool())
    await job_service.create(
        job_type="introspection",
        input={"user_id": user_id},
        user_id=user_id,
        scheduled_for=next_time,
        expires_at=next_time + timedelta(days=1),
    )

    return {"run_id": run_id, "next_scheduled": next_time.isoformat()}
```

### 6. Rejected Proposals Tracking

When a proposal is rejected at the human gate, it is appended to the tracking file in the user's memory directory. The format is:

```markdown
## Rejected 2026-04-13
- **File:** /user/preferences/communication.yaml
- **Change:** update briefing_length from 500 to 300
- **Rationale:** User feedback indicated briefings too long
- **Why rejected:** User declined at approval gate
```

The `analyze-patterns` step prompt instructs the LLM to check this file and not re-propose rejected changes unless new supporting data exists.

## Blast Radius

### Direct Impact

| Component | Impact | Risk |
|-----------|--------|------|
| `chatServer/workflows/` (SPEC-036) | Consumer: runs introspection as a workflow | **Low** — standard workflow template |
| `chatServer/sandbox/` (SPEC-038) | Consumer: reads/writes config in sandbox | **Low** — uses existing run_command interface |
| `chatServer/services/job_handlers.py` | Modified: new handler | **Low** — additive |
| `user_preferences` table | Modified: new columns | **Low** — additive columns with defaults |
| Supabase Storage | Consumer: template + prompt storage | **Low** — standard config files |

### Indirect Impact

| Component | Impact | Risk |
|-----------|--------|------|
| Agent behavior | **PRIMARY TARGET** — introspection changes how the agent behaves | **High** — bad changes degrade UX. Mitigated by SPEC-039 auto-rollback. |
| Notification system | Consumer: change notifications and approval requests | **Low** — uses existing API |
| Audit log | Read by signal gathering | **Low** — read-only access via views |

### Token Cost

Each introspection run makes 3-4 Anthropic API calls (one per step, excluding service-node steps). Estimated cost per run:
- gather-signals: ~2K input, ~1K output (Sonnet) = ~$0.02
- analyze-patterns: ~3K input, ~2K output (Sonnet) = ~$0.04
- propose-changes: ~4K input, ~2K output (Sonnet) = ~$0.05
- apply-changes: ~2K input, ~1K output (Sonnet) = ~$0.02

**Total: ~$0.13 per weekly run.** Negligible.

## Testing

| Test | Maps to AC | Type |
|------|-----------|------|
| Template parses correctly | AC-01, AC-02 | Unit |
| Gather-signals collects feedback, config, memory | AC-08, AC-09, AC-10, AC-11 | Unit (mock tools) |
| Analyze-patterns produces structured findings | AC-04, AC-12 | Unit (mock LLM) |
| Propose-changes limits to 3 proposals max | AC-13 | Unit (mock LLM) |
| Proposals include exact diff previews | AC-14 | Unit (mock LLM) |
| Apply-changes writes to /user/ via sandbox | AC-06 | Integration (`@sandbox`) |
| Apply-changes skips rejected proposals | AC-18 | Unit |
| Dynamic gate: Inform tier results in human-required | AC-16 | Unit |
| Dynamic gate: Recommend tier results in no gate | AC-16 | Unit |
| Rejected proposals recorded in file | AC-18 | Unit |
| Job handler dispatches and self-schedules | AC-19 | Unit (mock run_manager) |
| Introspection preferences CRUD | AC-20, AC-22 | Unit |
| Metrics view returns aggregated data | AC-09 | Integration (DB) |
| Changelog accessible via git log | AC-23 | Integration (`@sandbox`) |
| Diff accessible via git diff | AC-25 | Integration (`@sandbox`) |

## Edge Cases

1. **No data to analyze.** New user with fewer than 7 days of history. The `gather-signals` step returns sparse data. The `analyze-patterns` step should detect this and return: "Insufficient data for analysis. Will re-evaluate in {period_days} days." No proposals generated.

2. **All proposals rejected repeatedly.** If the same type of proposal is rejected 3 times (tracked via `rejected_proposals.md`), the `propose-changes` step should stop proposing that type and note: "Skipping {category} proposals -- previously rejected 3 times."

3. **Agent breaks its own config.** A malformed YAML file in `/user/preferences/` causes a parse error. The ConfigService's overlay resolution falls back to `/system/` defaults (SPEC-035 pattern). The auto-rollback service (SPEC-039) detects the error and reverts the commit.

4. **Introspection loop tries to modify its own template.** The introspection template is in `/system/workflows/` (read-only). The agent can create a custom override in `/user/workflows/introspection-loop.md`, but this is unlikely and harmless — the override would be used for future runs, and the ChangeTracker would flag it as `elevated: true`.

5. **Concurrent introspection and user interaction.** The introspection loop runs in the background while the user chats. File writes are serialized via git locks. The user sees config changes appear mid-conversation only at the notification level — the agent's runtime config is cached and refreshes on next interaction.

6. **Token budget exhaustion.** If a step exceeds its `max_tokens`, it returns partial output. The next step handles partial input gracefully (the prompt includes: "If prior step output is truncated, work with available data").

## Resolved Decisions

1. **Introspection runs as a workflow, not custom code.** Decision: workflow template on SPEC-036 engine. Rationale: consistent model for all multi-step processes, checkpointing for free, human gates for approval, scheduling via job queue. No special-case code.

2. **Default disabled.** Decision: introspection is opt-in (`introspection_enabled: false`). Rationale: self-modification is a power feature. Users should explicitly enable it, and the agent can propose enabling it after establishing trust.

3. **Max 3 proposals per run.** Decision: hard limit in the step prompt. Rationale: each change has blast radius. Limiting to 3 keeps the feedback loop tight — apply few changes, measure impact, iterate. High-volume changes make attribution impossible.

4. **Weekly default cadence.** Decision: 7-day interval. Rationale: matches the auto-rollback baseline window (SPEC-039 AC-22). Enough time to accumulate meaningful signal. More frequent runs would be noisy; less frequent would miss trends.

5. **Rejected proposals persist.** Decision: tracked in `/user/memory/rejected_proposals.md` with the agent instructed not to re-propose. Rationale: respects user preferences. If the user rejected "shorten briefings" once, proposing it again next week is annoying. New signal can override this — the prompt says "unless new signal data supports it."

## Decisions Requiring Your Input

1. **Introspection enablement UX.** How does the user enable introspection? **Option A:** Agent proposes it after establishing trust (e.g., after 2 weeks of positive interactions) via `request_capability_upgrade` flow. **Option B:** Settings toggle in the web app (discoverable but requires user initiative). **Option C:** Both -- agent proposes, user can also find it in settings. Recommendation: Option C.

2. **What counts as "sufficient signal" for a proposal?** The analysis prompt says "do not propose based on a single interaction." But what's the threshold? **Option A:** Leave it to LLM judgment (current approach -- prompt says "genuine patterns"). **Option B:** Quantitative threshold (e.g., >=3 negative signals on the same topic). Recommendation: Option A for MVP -- the LLM's judgment with conservative prompting is sufficient. Quantitative thresholds add rigidity that may not match diverse user patterns.

3. **Should the introspection loop have access to raw conversation messages?** Currently it reads aggregated metrics and memory. **Option A:** Aggregated only (privacy-preserving, current design). **Option B:** Access to last N messages for deeper analysis. Recommendation: Option A -- conversation content is already distilled into memory and feedback signals. Raw message access adds privacy risk and token cost for marginal analytical gain.
