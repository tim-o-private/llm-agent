"""introspection-loop workflow template and step prompts."""

TEMPLATE = """\
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
- **node_type:** service
- **description:** Collect performance data: user feedback, interaction metrics, current config state, agent memory. Output structured signal data for analysis.  # noqa: E501
- **gate_policy:** none

### step-2: Analyze Patterns
- **agent:** pattern-analyzer
- **depends_on:** [gather-signals]
- **tools:** []
- **model:** claude-sonnet-4-5-20250514
- **description:** Identify what's working, what's degraded, what's missing, and what capabilities are needed. Ground every finding in specific signal data. Be conservative -- only flag genuine patterns.  # noqa: E501
- **gate_policy:** none

### step-3: Propose Changes
- **agent:** improvement-proposer
- **depends_on:** [analyze-patterns]
- **tools:** []
- **model:** claude-sonnet-4-5-20250514
- **description:** Generate up to 3 concrete config modifications. Each proposal includes: file path, change type, exact diff, rationale, expected impact, risk assessment. Order by expected impact.  # noqa: E501
- **gate_policy:** none

### step-4: Apply Changes
- **agent:** config-editor
- **depends_on:** [propose-changes]
- **tools:** [write_file, read_file]
- **node_type:** service
- **description:** Carry out approved proposals in the sandbox. Write each change, verify it, and commit with rationale. Skip rejected proposals. Respect security boundary.  # noqa: E501
- **gate_policy:** dynamic
"""

PROMPT_GATHER_SIGNALS = """\
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
"""

PROMPT_ANALYZE_PATTERNS = """\
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
"""

PROMPT_PROPOSE_CHANGES = """\
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
  "diff_preview": "- briefing_length: 500\\n+ briefing_length: 300",
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
"""

PROMPT_APPLY_CHANGES = """\
# Apply Introspection Changes

You are applying approved config modifications to the sandbox.

## Process

For each proposal:
1. Read the current file (if update/delete)
2. Apply the change exactly as specified in diff_preview
3. Verify the result by reading the file back
4. Report success or failure

## Rules

- Only write to /user/ paths (mutable layer)
- Never modify /system/ paths (read-only)
- Skip proposals marked as rejected
- Skip proposals marked as elevated unless explicitly approved
- If a file write fails, log the error and continue to the next proposal
- Each change will be committed separately by the service layer

## Output

Return a summary of applied changes:
{
  "applied": [{"file_path": "...", "change_type": "...", "status": "success"}],
  "skipped": [{"file_path": "...", "reason": "rejected"}],
  "failed": [{"file_path": "...", "error": "..."}]
}
"""
