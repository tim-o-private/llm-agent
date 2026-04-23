# SPEC-054: Orchestration Proposals (Stage 5 -- Agent-Initiated Threads + Self-Improvement)

> **Status:** Draft (contract spec)
> **Author:** spec-writer (Claude) on behalf of Tim
> **Created:** 2026-04-21
> **Vision:** [`docs/sdlc/visions/clarity-as-vault.md`](../visions/clarity-as-vault.md) -- Stage 5, Transaction #5 (Orchestration proposal), Transaction #7 (Delegation)
> **Directive:** [`docs/sdlc/visions/clarity-as-vault-functional.md`](../visions/clarity-as-vault-functional.md) -- S1 Agent section, S4 workflow authoring, S6 approval lane (`workflow_proposal`, `config_change`)
> **Architecture:** [`docs/sdlc/visions/clarity-as-vault-architecture.md`](../visions/clarity-as-vault-architecture.md) -- thread-planner agent (Opus), model routing table
> **Stage:** Clarity-as-Vault Stage 5 (capstone)

**Depends on:**
- SPEC-045 (approval lane, `approval_cards` schema, `activity_log`, VaultService, Today Agent section)
- SPEC-048 (workflow editor -- where proposed workflows are edited after acceptance)
- SPEC-049 (chat scoping -- threads are chat-scopeable files)
- SPEC-050 (activity log -- all orchestration actions logged)
- SPEC-052 (approval execution -- `workflow_proposal` and `config_change` executors)
- SPEC-053 (entity docs -- thread-docs follow the same agent-maintained file pattern)

---

## Goal

Ship the capstone of the Clarity-as-Vault build plan: **the agent takes initiative within approval-gated bounds.** Three capabilities arrive together:

1. **Agent-initiated threads.** The agent notices work that needs multi-step coordination (a question requiring research, a recurring task, a delegated project) and opens a thread-doc in the vault. Thread-docs surface in Today's Agent section. The agent drives threads forward on subsequent runs, adding findings and updating status.

2. **Orchestration proposals.** The agent recognizes recurring work patterns and proposes new workflows, agents, or skills via the approval lane. Approved proposals land as `.flow.md`, agent `.md`, or skill `.md` files that the system runs or loads.

3. **Self-improvement loop.** The agent proposes edits to its own configuration -- agent definitions, skills, workflow templates -- through the same approval lane. Approved changes take effect on next invocation because behavior is declared in markdown.

Stage 5 exit criterion from the vision: **"Does it feel like a co-worker? Are proposed workflows actually taking load off, or noise?"**

### What this spec is and is not

This is a **contract spec with safety emphasis**. It defines the thread-doc format, the orchestration proposal trigger model, the thread-planner agent contract, the self-improvement boundaries, and the safety mechanisms that prevent the agent from spiraling into noise or unsafe self-modification. It has enough structure for Stages 1-4 to preserve the right extension points.

It does **not** contain FU-level PR breakdowns or Playwright scripts. Those arrive when Stage 5 enters the build queue.

---

## Existing Infrastructure (what we reuse)

| Primitive | Source | What we use it for |
|-----------|--------|--------------------|
| `approval_cards` table | SPEC-045 | `workflow_proposal` and `config_change` card types already exist. Orchestration proposals flow through this lane. |
| `workflow_proposal` executor | SPEC-052 | Writes `.flow.md` to `_workflows/` on approval. No new execution path needed. |
| `config_change` executor | SPEC-052 | Applies proposed content to agent/skill markdown on approval. |
| `activity_log` table | SPEC-045/050 | Every orchestration action is logged here. |
| Workflow editor | SPEC-048 | Proposed workflows become `.flow.md` files editable in this view after approval. |
| VaultService | SPEC-045 | All vault reads/writes for thread-docs. `_resolve` is the security chokepoint. |
| Entity doc pattern | SPEC-053 | Thread-docs follow the same frontmatter + body convention as entity docs. |
| Chat scoping | SPEC-049 | Thread-docs are chat-scopeable (`{ type: 'file', path: '_threads/...' }`). |
| Today Agent section | SPEC-045 AC-08 | Thread status surfaces here alongside running/watching/blocked items. |
| Workflow engine | SPEC-036 | Dispatches the orchestration-check workflow on schedule. |
| `suggest_cards` table | SPEC-047 | Thread-doc updates can surface as suggest cards on Today. |
| `markdown_sections` parser | SPEC-045 | Parse/patch sections within thread-docs. |
| Template registry shadow pattern | SPEC-036/048 | New system workflows (`orchestration-check.md`) ship in system config and can be overridden per-user. |
| Model routing | Architecture doc | Thread-planner uses Opus (real judgment); pattern-detector uses Sonnet (analysis). |

---

## 1. Thread-Docs

### Directory structure

Thread-docs live under `_threads/` in the user's vault root:

```
vault/
  _threads/
    2026-04-22-santa-fe-trip-planning.md
    2026-04-20-q3-budget-review.md
    2026-04-18-recurring-newsletter-setup.md
  _workflows/
  entities/
  today.md
```

The `_threads/` directory is created on first thread creation. No seeding of empty directories (unlike `entities/` in SPEC-053) -- threads are exclusively agent-initiated.

### Filename convention

Thread filenames are date-prefixed and kebab-cased from the thread title: `YYYY-MM-DD-<title-slug>.md`. The date prefix is the creation date. This gives natural chronological ordering in the vault browser and avoids collisions.

### Frontmatter schema

```yaml
---
doc_type: thread
title: Santa Fe Trip Planning
status: active          # active | watching | paused | completed | archived
created_at: 2026-04-22T08:30:00Z
updated_at: 2026-04-22T14:15:00Z
initiated_by: agent     # agent | user
trigger: "User said 'plan the Santa Fe trip' in chat on 2026-04-22"
tags:
  - travel
  - personal
next_action: "Research flight options for May 10-14"
next_action_at: 2026-04-23T06:30:00Z   # when the agent should next check in
blocked_on: null        # free text describing what's blocking progress
---
```

**Required fields:** `doc_type` (must be `thread`), `title`, `status`, `created_at`, `initiated_by`.

**Status lifecycle:**

```
active -----> watching -----> completed
  |              |                |
  +---> paused --+                |
  |                               |
  +-----------> archived <--------+
```

- `active` -- the agent is actively working on this thread and will drive it forward on the next scheduled check.
- `watching` -- the agent has done what it can for now and is waiting for an external signal (a reply, a date arriving, user input). It checks in at `next_action_at` or when a relevant signal arrives.
- `paused` -- user explicitly paused the thread ("stop working on this for now"). Agent does not advance it.
- `completed` -- the thread's goal has been achieved. Remains in the vault for reference.
- `archived` -- moved out of active consideration. Can be unarchived.

### Body structure

The body uses H2 sections following the vault convention:

```markdown
## Goal
Plan a 4-day trip to Santa Fe for May 10-14. Budget under $2000.

## Plan
1. Research flights (May 10-14, SFO -> SAF)
2. Find lodging near the plaza
3. Build a day-by-day itinerary
4. Surface the plan for approval

## Progress
- 2026-04-22 14:15: Found 3 flight options via Google Flights. Best: United $340 RT.
- 2026-04-22 08:30: Thread opened. User asked to plan the trip in chat.

## Findings
### Flights
- United UA1234: SFO -> ABQ, $340 RT, 1 stop. Arrives 2pm.
- Southwest WN567: SFO -> ABQ, $280 RT, nonstop. Arrives 4pm.

## Open Questions
- Does the user prefer a hotel or Airbnb?
- Any dietary restrictions for restaurant recommendations?

## Notes
User-captured or agent-added notes.
```

The `markdown_sections` parser (SPEC-045) handles section manipulation. The agent appends to `## Progress` (prepending to the list, most recent first), updates `## Findings`, and manages `## Open Questions`.

---

## 2. Thread-Planner Agent

### Agent definition

A new agent markdown file ships at `data/config/system/agents/clarity/thread-planner.md`:

```yaml
---
name: thread-planner
model: opus
tools: [read_file, write_file, search_gmail, list_calendar_events, web_search]
description: |
  Plans and drives multi-step work threads. Creates thread-docs, 
  updates progress, surfaces findings, and identifies when user 
  input is needed. Uses real judgment to decide what work is worth 
  pursuing and when to stop.
---
```

**Model choice:** Opus per the architecture doc's model routing table. Thread planning requires real judgment: deciding what deserves a thread, structuring a plan, synthesizing findings, knowing when to stop. This is not extraction (Haiku) or careful execution (Sonnet) -- it is planning under ambiguity.

### What the thread-planner can do

1. **Create a thread-doc** in `_threads/` via `VaultService.update_body`.
2. **Update existing thread-docs** -- append progress, update status, revise the plan, add findings.
3. **Read vault files** relevant to the thread (entity docs, other threads, today.md).
4. **Read external signals** -- email, calendar -- when the thread's context requires it.
5. **Surface items in Today** by updating the thread's status and `next_action` (the Today compositor reads thread frontmatter to populate the Agent section).
6. **Ask the user questions** by writing to `## Open Questions` and setting `blocked_on`. The question appears in Today's Agent section as a blocked item.

### What the thread-planner cannot do

1. **Take outbound actions.** No sending emails, creating events, or modifying anything outside the vault. World-facing actions go through the approval lane.
2. **Create approval cards directly.** The thread-planner writes thread-docs and surfaces observations. The orchestration-check workflow (below) is the one that creates `workflow_proposal` or `config_change` cards.
3. **Modify system configuration.** Agent/skill/workflow files are changed only through `config_change` approval cards.
4. **Create other threads from within a thread.** One thread per invocation. The orchestration-check workflow decides when to spawn new threads.

### Thread initiation triggers

The agent creates a thread when:

| Trigger | Example | How it enters the system |
|---------|---------|------------------------|
| User delegation | "Plan the Santa Fe trip" | Chat message. The chat handler detects delegation intent and invokes the thread-planner. |
| Agent observation on scheduled check | Notices 3 emails about the same topic in the last week | The orchestration-check workflow identifies the pattern and creates the thread. |
| Workflow output | A capture lands in inbox with high complexity | The capture-router (SPEC-051) flags captures it cannot route trivially; the orchestration-check workflow picks them up. |

The thread-planner **never creates a thread speculatively.** Every thread must have either a user request or concrete evidence of a pattern (see Noise Prevention below).

---

## 3. Orchestration Proposals

### The orchestration-check workflow

A new workflow file ships at `data/config/system/workflows/orchestration-check.md`:

```yaml
---
name: orchestration-check
description: |
  Periodic check for recurring patterns and active threads. 
  Proposes new workflows when patterns recur, advances active 
  threads, and surfaces items needing user attention.
version: 1
default_gate_policy: none
---
```

**Steps:**

1. **Scan signals:** Read recent activity (captures, emails, calendar, vault changes, activity log) and active thread-docs. Identify recurring patterns (same-shape captures 3+ times, standing requests, repeated manual processes).
2. **Advance threads:** For each `active` thread whose `next_action_at` has passed, invoke the thread-planner to drive it forward. For `watching` threads, check if their watch condition has been met.
3. **Propose workflows:** For each identified recurring pattern that meets the proposal threshold (see below), create a `workflow_proposal` approval card with the proposed `.flow.md` content and the pattern evidence.
4. **Propose config changes:** If the agent's observation suggests a change to an existing agent definition, skill, or workflow (e.g., "the email triage workflow should also check Slack mentions"), create a `config_change` approval card with the proposed new content and rationale.

**Schedule:** Runs on a configurable schedule via `user_preferences.orchestration_check_enabled` (BOOL, default `false`) and `orchestration_check_time` (TEXT, default `'07:00'`). Uses the same job-handler pattern as SPEC-045's `regenerate-today` schedule. Can also be triggered on-demand via `POST /workflows/run` with `template_name=orchestration-check`.

### Pattern detection model

The agent uses a **pattern-detector** sub-step (Sonnet model -- analysis work, not judgment) to identify recurring patterns. The model receives:

- Recent captures (last 14 days)
- Recent activity log entries (last 14 days)
- Existing workflow definitions (to avoid proposing duplicates)
- Existing thread-docs (to avoid creating duplicate threads)

The pattern-detector outputs a structured list of candidate patterns:

```json
{
  "patterns": [
    {
      "description": "User captures meeting notes after every standup (Mon/Wed/Fri)",
      "evidence": ["capture-2026-04-22-standup", "capture-2026-04-20-standup", "capture-2026-04-18-standup"],
      "proposed_action": "workflow_proposal",
      "confidence": "high"
    }
  ]
}
```

### Proposal threshold

A pattern must meet **all** of the following to generate a proposal:

1. **Recurrence:** The pattern has occurred at least 3 times in the last 14 days.
2. **No existing coverage:** No existing workflow already handles this pattern. The agent checks `_workflows/` for semantic overlap.
3. **User has not rejected a similar proposal in the last 30 days.** The agent checks `approval_cards` for rejected `workflow_proposal` cards with similar content.
4. **Confidence:** The pattern-detector's confidence is `high` or `medium` (not `low`).

These thresholds are deliberately conservative. The exit criterion is "taking load off, or noise?" -- erring on the side of fewer proposals is correct until the system proves reliable. [A14]

### Proposal content

A `workflow_proposal` approval card contains:

```json
{
  "card_type": "workflow_proposal",
  "title": "New workflow: Auto-file standup notes",
  "payload": {
    "filename": "auto-file-standup-notes.flow.md",
    "body": "---\nname: auto-file-standup-notes\n...",
    "pattern_observed": "You've captured meeting notes after standup 8 times in the last month. Each time you route them to projects/standup-notes/. This workflow would do that automatically."
  },
  "rationale": "Detected recurring capture pattern: standup notes routed to the same folder after every standup meeting."
}
```

The `payload.body` is a complete, valid `.flow.md` file that the SPEC-052 `workflow_proposal` executor writes to `_workflows/` on approval. The user can edit the body before approving (SPEC-045 AC-15 edit flow).

A `config_change` approval card contains:

```json
{
  "card_type": "config_change",
  "title": "Update email-triage workflow: add Slack mentions",
  "payload": {
    "file_path": "_workflows/email-triage.flow.md",
    "diff": "---\nname: email-triage\n... (complete proposed new content)",
    "summary": "Add a step to check Slack mentions when triaging morning email. You mentioned Slack 4 times in the last week's captures."
  },
  "rationale": "You've been manually checking Slack after email triage. Adding it to the workflow saves a step."
}
```

---

## 4. How Threads Surface in Today

The Today compositor (SPEC-045) already reads the Agent section from `today.md`. Stage 5 extends this: the `regenerate-today` workflow's gather step also reads `_threads/` frontmatter and populates the Agent section with thread status.

### Agent section thread display

Each active or watching thread surfaces as a line item in the Agent section:

- **Running** (status `active`): "Planning Santa Fe trip -- researching flights" (title + next_action)
- **Watching** (status `watching`): "Q3 budget review -- waiting for Sarah's input" (title + blocked_on or next_action)
- **Blocked** (status `active` with `blocked_on` set): "Newsletter setup -- needs your input: which topics?" (title + blocked_on). This surfaces as a call-to-action.

Each item links to the thread-doc in the vault (clickable via wikilink or direct `/vault/_threads/...` path). The user can interact with the thread by opening it (SPEC-047 file detail view) or chatting about it (SPEC-049 chat scoping with `{ type: 'file', path: '_threads/...' }`).

`paused`, `completed`, and `archived` threads do not appear in Today's Agent section. They are accessible through the vault browser.

### Activity log integration

Every thread creation, status change, progress update, and proposal creation emits an `activity_log` entry with:
- `actor`: `"thread-planner"` or `"orchestration-check"`
- `action`: descriptive prose ("Created thread: Santa Fe trip planning", "Advanced thread: found 3 flight options", "Proposed workflow: auto-file standup notes")
- `subject_path`: the thread-doc path or the proposed workflow path
- `status`: `"done"` for successful actions, `"awaiting_approval"` for proposals

---

## 5. Self-Improvement Loop

### What the agent can propose to change

| Target | Card type | Example |
|--------|-----------|---------|
| Workflow template | `workflow_proposal` | Propose a new `.flow.md` file |
| Existing workflow | `config_change` | Edit steps, add tools, change schedule |
| Agent definition | `config_change` | Change an agent's model, tools, or description |
| Skill file | `config_change` | Add or edit a skill markdown file |
| System prompt fragment | `config_change` | Edit a system-level instruction file |

### What the agent cannot propose

These are hard boundaries, not threshold-gated:

1. **Security configuration.** Auth, RLS policies, sandbox settings, approval tier definitions -- these are code, not markdown. The agent cannot touch them. [A12]
2. **Its own approval gate.** The agent cannot propose reducing the approval requirement for its own changes. The approval lane is a security boundary, not a configuration surface.
3. **Tool implementations.** MCP server code, tool class implementations -- these are code boundaries. The agent proposes *use* of tools (via agent definitions), not tool *behavior*.
4. **User data outside the vault.** Postgres rows (auth, billing, preferences beyond what's in the vault) are not targets for config_change proposals.
5. **Removal of safety constraints.** Any proposed content that removes approval gates, disables logging, or weakens isolation is blocked by the config_change executor's safety validator (see below).

### Safety validator

The `config_change` executor (SPEC-052) gains a **pre-execution validation step** for Stage 5:

```python
class ConfigChangeSafetyValidator:
    """Validates proposed config changes before execution."""

    BLOCKED_PATTERNS = [
        r"default_gate_policy:\s*none",    # removing approval gates
        r"approval_tier:\s*auto",          # auto-approving actions
        # ... patterns that reduce safety
    ]

    PROTECTED_PATHS = [
        "system/security/",
        "system/auth/",
        "_activity/",
    ]

    def validate(self, file_path: str, proposed_content: str) -> tuple[bool, str | None]:
        """Returns (is_safe, rejection_reason)."""
        for path_prefix in self.PROTECTED_PATHS:
            if file_path.startswith(path_prefix):
                return False, f"Protected path: {path_prefix} cannot be modified via config_change"

        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, proposed_content):
                return False, f"Proposed content contains blocked pattern: {pattern}"

        return True, None
```

The validator runs **before** the user sees the approval card. If a proposed change fails validation, the card is created with `status='rejected'` and the rationale explains why. The user never has to evaluate an unsafe proposal.

This is a conservative first pass. The blocked patterns list grows as we discover new unsafe patterns. [A12, A14]

### Maximum blast radius

Every approved `config_change` affects exactly one file. There is no batch-edit mechanism. The worst case for a single approved change:

- **Workflow file:** a broken workflow fails on next run. The activity log shows the failure. The user can edit or revert via the workflow editor (SPEC-048). Previous workflow runs are unaffected.
- **Agent definition:** a broken agent definition fails when the workflow engine tries to load it. The error surfaces in the activity log. The user edits the file to fix it.
- **Skill file:** a broken skill is loaded by the agent on next invocation. If it causes bad behavior, the user notices via the activity log and edits the skill.

In all cases: the vault is git-backed (vision doc), so `git revert` recovers any file. The activity log provides the audit trail to identify what changed.

### Rollback mechanism

Stage 5 rollback is manual: the user opens the file, sees the change, and edits or reverts it. The approval card's `payload.diff` field (which contains the complete proposed content) serves as the "before" reference -- the user can compare current content to what was proposed.

A future spec can add a "Revert this change" button on the activity log entry that reads the pre-change content from git and writes it back. This spec does not build that UI but the data model supports it.

---

## 6. Noise Prevention

The exit criterion is explicit: "Are proposed workflows actually taking load off, or noise?" These mechanisms prevent the agent from becoming a proposal factory.

### Rate limits

| Scope | Limit | Rationale |
|-------|-------|-----------|
| `workflow_proposal` cards per day | 2 | A co-worker who proposes 5 new processes a day is annoying. |
| `config_change` cards per day | 3 | Config tweaks are lighter-weight but still need attention. |
| Thread creations per day | 3 | Threads are heavier than proposals -- each one demands ongoing attention. |
| Re-proposal after rejection | 30-day cooldown | The agent must not nag. Similar proposals (same pattern, same target file) are blocked for 30 days after rejection. |

These limits are per-user and stored as constants in the orchestration-check workflow. They can be overridden per-user via `user_preferences.orchestration_limits` (JSONB, optional -- absent means use defaults). [A13]

### Quality signals

The agent tracks proposal acceptance rates in the activity log:

- After 5 consecutive rejections: the agent pauses proposals for 7 days and logs "Pausing proposals -- recent suggestions haven't been useful."
- After 3 consecutive acceptances: the agent may increase confidence thresholds slightly, proposing more selectively (not more frequently).

This is heuristic, not ML. The activity log provides the data; the orchestration-check workflow reads it. [A14]

### User controls

- **`user_preferences.orchestration_check_enabled`:** master switch. Default `false`. User must opt in. [A13]
- **`user_preferences.orchestration_limits`:** per-type rate limits. Override defaults. [A13]
- **"Stop proposing X" in chat:** the user can tell the agent to stop a specific category of proposals. The agent records this as a permanent rejection signal (stored in a `_threads/_meta/suppressed-patterns.md` file in the vault, not in Postgres).
- **Pause all threads:** a single chat command or preference toggle pauses all active threads to `paused` status.

---

## 7. What Stage 1-4 Specs Must Preserve

These are the contract constraints that earlier specs must not violate for Stage 5 to work.

| Constraint | Established by | Why Stage 5 needs it |
|------------|---------------|----------------------|
| `approval_cards` supports `workflow_proposal` and `config_change` card types | SPEC-045 | Orchestration proposals flow through these card types. |
| `workflow_proposal` executor writes `.flow.md` to `_workflows/` | SPEC-052 AC-11 | Approved workflow proposals land as runnable workflow files. |
| `config_change` executor applies proposed content to vault files | SPEC-052 AC-12 | Approved config changes update agent/skill/workflow definitions. |
| `config_change` executor can be extended with a pre-execution validator | SPEC-052 executor pattern | Safety validator hooks into the executor before write. |
| `activity_log` accepts arbitrary `actor` and `action` strings | SPEC-045/050 | Thread-planner and orchestration-check write entries with their own actor names. |
| Today Agent section reads from `today.md` content (not a separate data source) | SPEC-045 AC-08 | Thread status is written into `today.md` by the `regenerate-today` workflow. |
| `_threads/` path prefix is not excluded from `VaultService._walk_recent` | SPEC-045 | Thread-docs appear in the Recent section when modified. |
| `_threads/` path prefix is not excluded from `GET /vault/tree` | SPEC-046 | Thread-docs appear in the vault browser file tree. |
| Chat scoping works for any vault file path | SPEC-049 | Thread-docs at `_threads/*.md` are chat-scopeable. |
| `markdown_sections` parser preserves unknown sections | SPEC-045 | Thread-planner can add sections to thread-docs without losing content. |
| `suggest_cards` table exists and is renderable | SPEC-047 | Thread updates can surface as suggest cards on relevant files. |
| Workflow engine dispatches by template_name | SPEC-036 | `orchestration-check` workflow runs on schedule. |
| `user_preferences` table accepts new columns | SPEC-045 pattern | Orchestration scheduling adds preference columns. |
| The `config_change` payload field `diff` stores complete proposed content | SPEC-052 | The safety validator inspects the complete proposed content, not a patch. |
| Template registry shadow pattern (user overrides system) | SPEC-036/048 | User can customize the orchestration-check workflow. |
| `remark-wiki-link` renders links in thread-doc preview | SPEC-047 | Thread-docs use wikilinks to entities and other files. |

---

## Acceptance Criteria

### Thread-docs

- [ ] **AC-01:** The `_threads/` directory is created on first thread creation via `VaultService`. No seeding. Thread-docs are plain markdown files with YAML frontmatter containing at minimum `doc_type: thread`, `title`, `status`, `created_at`, `initiated_by`. [F1]

- [ ] **AC-02:** Thread-doc filenames follow the convention `YYYY-MM-DD-<title-slug>.md`. The slugifier reuses the same pure function from SPEC-053 (`chatServer/lib/slugify.py`). [A10]

- [ ] **AC-03:** Thread-doc status lifecycle supports five states: `active`, `watching`, `paused`, `completed`, `archived`. Status transitions are validated: `paused` and `archived` can be reached from any state; `completed` can only be reached from `active` or `watching`; `active` can be reached from `watching` or `paused`. Invalid transitions are rejected by the thread service. [A12]

- [ ] **AC-04:** The thread-planner agent creates thread-docs when: (a) the user explicitly delegates work via chat ("plan the Santa Fe trip"), or (b) the orchestration-check workflow identifies a pattern requiring multi-step coordination. The agent never creates threads speculatively -- every thread has a concrete trigger documented in the frontmatter `trigger` field. [A14]

- [ ] **AC-05:** The thread-planner agent is defined at `data/config/system/agents/clarity/thread-planner.md` with `model: opus` per the architecture doc's model routing table. Tools: `read_file`, `write_file`, `search_gmail`, `list_calendar_events`, `web_search`. [A2]

- [ ] **AC-06:** Thread-docs surface in Today's Agent section. The `regenerate-today` workflow reads `_threads/` frontmatter and includes: `active` threads under "Running", `watching` threads under "Watching", `active` threads with `blocked_on` set under "Blocked". Each item shows the thread title and either `next_action` or `blocked_on`. Items link to the thread-doc. `paused`, `completed`, and `archived` threads do not appear. [A14]

- [ ] **AC-07:** Thread-docs are accessible via the vault browser (SPEC-046), the file detail view (SPEC-047), and chat scoping (SPEC-049 `{ type: 'file', path: '_threads/...' }`). No thread-specific UI beyond what the vault already provides. [A14]

### Orchestration proposals

- [ ] **AC-08:** A new workflow `orchestration-check.md` ships at `data/config/system/workflows/orchestration-check.md`. It scans recent signals (captures, emails, calendar, vault changes, activity log) for recurring patterns, advances active threads, and creates `workflow_proposal` or `config_change` approval cards when patterns meet the proposal threshold. [A2]

- [ ] **AC-09:** The orchestration-check workflow runs on a configurable schedule via `user_preferences.orchestration_check_enabled` (BOOL, default `false`) and `orchestration_check_time` (TEXT, default `'07:00'`). It can also be triggered on-demand. The scheduling uses the existing job-handler pattern from SPEC-045/037. [A13]

- [ ] **AC-10:** The proposal threshold requires all of: (a) pattern recurrence >= 3 times in 14 days, (b) no existing workflow covers the pattern, (c) no similar proposal rejected in the last 30 days, (d) pattern-detector confidence is `high` or `medium`. [A14]

- [ ] **AC-11:** Proposed workflows (`workflow_proposal` cards) contain a complete, valid `.flow.md` body in `payload.body` and a human-readable `pattern_observed` explanation. The user can preview the workflow content, edit it before approving (SPEC-045 AC-15), and the SPEC-052 executor writes it to `_workflows/` on approval. [A12]

- [ ] **AC-12:** Proposed config changes (`config_change` cards) contain the complete proposed new file content in `payload.diff`, the target `file_path`, and a `summary` explaining the change and the evidence behind it. [A12]

### Self-improvement and safety

- [ ] **AC-13:** The `config_change` executor validates proposed content through a `ConfigChangeSafetyValidator` before the user sees the approval card. Proposals targeting protected paths (`system/security/`, `system/auth/`, `_activity/`) are auto-rejected. Proposals containing blocked patterns (removing approval gates, setting auto-approve tiers) are auto-rejected. Rejections are logged in `activity_log` with reasoning. [A12]

- [ ] **AC-14:** Every approved `config_change` affects exactly one file. There is no batch-edit mechanism. The worst-case blast radius is one broken file, recoverable via git revert or manual edit. [A12]

- [ ] **AC-15:** The agent cannot propose changes to: (a) its own approval gate mechanism, (b) security configuration (auth, RLS, sandbox), (c) tool implementations (code, not markdown), (d) Postgres state outside the vault. These are hard boundaries, not threshold-gated. [A12]

### Noise prevention

- [ ] **AC-16:** Rate limits per user per day: max 2 `workflow_proposal` cards, max 3 `config_change` cards, max 3 new thread creations. Limits are enforced by the orchestration-check workflow before card creation. Limits are stored as constants with per-user override via `user_preferences.orchestration_limits` (JSONB, optional). [A13, A14]

- [ ] **AC-17:** After a `workflow_proposal` or `config_change` card is rejected, the agent does not re-propose a similar change (same pattern or same target file) for 30 days. Similarity is determined by the orchestration-check workflow reading recent rejected cards from `approval_cards`. [A14]

- [ ] **AC-18:** After 5 consecutive proposal rejections (any type), the orchestration-check workflow pauses all proposals for 7 days and logs the pause in `activity_log`. The user can re-enable proposals early by toggling `orchestration_check_enabled` off and on. [A14]

- [ ] **AC-19:** The `orchestration_check_enabled` preference defaults to `false`. The user must explicitly opt in. This is the master switch for all Stage 5 agent initiative. When disabled, no threads are created, no proposals are made, and existing active threads are not advanced (they remain in their current state). [A13]

### Activity log integration

- [ ] **AC-20:** Every orchestration action emits an `activity_log` entry: thread creation, thread status change, thread progress update, proposal creation, proposal auto-rejection by safety validator, rate limit enforcement. Actor is `"thread-planner"` or `"orchestration-check"`. [SPEC-050 integration]

### Auth and isolation

- [ ] **AC-21:** All thread-doc and orchestration operations respect the existing VaultService access control model. Thread-docs live in the user's vault sandbox. User A cannot read or modify User B's threads. The orchestration-check workflow runs scoped to the authenticated user. [A8]

---

## Scope

### Files to create

| File | Purpose |
|------|---------|
| `supabase/migrations/YYYYMMDD_user_prefs_orchestration.sql` | Add `orchestration_check_enabled` (BOOL, default false), `orchestration_check_time` (TEXT, default '07:00'), `orchestration_limits` (JSONB, nullable) to `user_preferences`. |
| `chatServer/services/thread_service.py` | Thread-specific operations on top of VaultService: create_thread, update_thread, list_active_threads, advance_thread, change_status. Validates status transitions. |
| `chatServer/services/orchestration_service.py` | Orchestration-check logic: pattern detection, proposal creation, rate limit enforcement, rejection cooldown checking. |
| `chatServer/services/config_change_validator.py` | `ConfigChangeSafetyValidator`: pre-execution validation for config_change proposals. Protected paths, blocked patterns. |
| `chatServer/routers/thread_router.py` | `GET /vault/threads` (list active), `GET /vault/threads/:slug` (read), `POST /vault/threads/:slug/status` (change status). Thin routers. [A1] |
| `data/config/system/agents/clarity/thread-planner.md` | Agent markdown: model (Opus), tools, description. |
| `data/config/system/agents/clarity/pattern-detector.md` | Agent markdown: model (Sonnet), description -- analysis step for the orchestration-check workflow. |
| `data/config/system/workflows/orchestration-check.md` | Workflow: scan signals, advance threads, propose workflows/config changes. |
| `webApp/src/api/types/thread.ts` | `ThreadSummary`, `ThreadDoc` types. |
| `webApp/src/api/hooks/useThreadHooks.ts` | `useActiveThreads`, `useThread`, `useChangeThreadStatus`. [A4] |
| `tests/unit/services/test_thread_service.py` | Thread creation, status transitions (valid and invalid), listing, frontmatter preservation. |
| `tests/unit/services/test_orchestration_service.py` | Pattern detection, rate limits, rejection cooldown, proposal creation. |
| `tests/unit/services/test_config_change_validator.py` | Protected paths, blocked patterns, safe changes pass. |
| `tests/integration/test_thread_api.py` | Auth, cross-user isolation, status transitions, listing. |

### Files to modify

| File | Change |
|------|--------|
| `chatServer/services/approval_executors/config_change.py` | Add pre-execution call to `ConfigChangeSafetyValidator.validate()`. Reject unsafe changes before write. |
| `chatServer/main.py` | Register `thread_router`. |
| `data/config/system/workflows/regenerate-today.md` | Gather step reads `_threads/` frontmatter to populate the Agent section. |
| `chatServer/services/job_handlers.py` | Add `handle_orchestration_check` handler following the SPEC-045 pattern. |

### Out of scope

- **Thread-specific UI view** -- thread-docs are rendered by the existing file detail view (SPEC-047). No specialized thread editor or timeline view.
- **Agent-to-agent delegation within threads** -- the thread-planner works alone. Multi-agent coordination within a thread is a post-Stage-5 concern.
- **Automated rollback UI** -- "Revert this change" button on activity log entries. The data model supports it; the UI is a future spec.
- **ML-based pattern detection** -- pattern detection is heuristic (prompt-based, not trained). Good enough for low-volume personal use.
- **Voice/multimodal thread input** -- text only.
- **Thread templates** -- no pre-built thread structures. The agent generates the plan per-thread.
- **Thread sharing or collaboration** -- threads are per-user vault files. No sharing mechanism.
- **Real-time thread progress updates** -- polling via Today regeneration. SSE for thread updates is a future spec.
- **Continuous autonomous initiative** -- the vision doc explicitly defers this past Stage 5: "unbounded autonomous initiative (agent continuously watching its own performance and editing without explicit trigger)." This spec is schedule-triggered and user-delegated, not continuous.

---

## Technical Approach

### 1. ThreadService -- thread operations on top of VaultService

```python
class ThreadService:
    def __init__(self, vault: VaultService):
        self._vault = vault

    VALID_TRANSITIONS = {
        "active": {"watching", "paused", "completed", "archived"},
        "watching": {"active", "paused", "completed", "archived"},
        "paused": {"active", "watching", "archived"},
        "completed": {"archived"},
        "archived": {"active"},  # unarchive
    }

    async def create_thread(
        self, user_id: str, title: str, trigger: str,
        initiated_by: str = "agent", goal: str = "",
    ) -> str:
        """Create a thread-doc. Returns the vault-relative path."""
        slug = slugify(title)
        date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = f"{date_prefix}-{slug}.md"
        rel_path = f"_threads/{filename}"

        frontmatter = {
            "doc_type": "thread",
            "title": title,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "initiated_by": initiated_by,
            "trigger": trigger,
            "tags": [],
            "next_action": None,
            "next_action_at": None,
            "blocked_on": None,
        }
        body = f"## Goal\n{goal}\n\n## Plan\n\n## Progress\n\n## Findings\n\n## Open Questions\n\n## Notes\n"
        content = serialize_frontmatter_doc(frontmatter, body)
        await self._vault.update_body(user_id, rel_path, content)
        return rel_path

    async def change_status(
        self, user_id: str, rel_path: str, new_status: str
    ) -> None:
        """Validate and apply a status transition."""
        content = await self._vault.read_file(user_id, rel_path)
        fm, body = parse_frontmatter(content)
        current = fm.get("status")
        if new_status not in self.VALID_TRANSITIONS.get(current, set()):
            raise HTTPException(
                422,
                f"Invalid transition: {current} -> {new_status}"
            )
        fm["status"] = new_status
        fm["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self._vault.update_body(
            user_id, rel_path, serialize_frontmatter_doc(fm, body)
        )

    async def list_active_threads(self, user_id: str) -> list[dict]:
        """Return frontmatter summaries for active/watching/blocked threads."""
        # Walk _threads/, read frontmatter, filter by status
        ...
```

### 2. OrchestrationService -- proposal creation with rate limits

```python
class OrchestrationService:
    DAILY_LIMITS = {
        "workflow_proposal": 2,
        "config_change": 3,
        "thread_creation": 3,
    }
    REJECTION_COOLDOWN_DAYS = 30
    CONSECUTIVE_REJECTION_PAUSE_THRESHOLD = 5
    CONSECUTIVE_REJECTION_PAUSE_DAYS = 7

    async def can_propose(
        self, user_id: str, card_type: str, db
    ) -> tuple[bool, str | None]:
        """Check rate limits and cooldowns. Returns (allowed, reason)."""
        # Check user-specific limits from preferences
        # Check daily count from approval_cards
        # Check consecutive rejection pause
        ...

    async def is_similar_rejected(
        self, user_id: str, pattern_description: str, target_path: str | None, db
    ) -> bool:
        """Check if a similar proposal was rejected in the last 30 days."""
        # Query rejected approval_cards for semantic similarity
        # Stage 5: simple substring/path match, not embedding-based
        ...
```

### 3. ConfigChangeSafetyValidator

The validator is called in two places:
1. **Before card creation** (in OrchestrationService): prevents unsafe proposals from entering the approval lane.
2. **Before execution** (in ConfigChangeExecutor, SPEC-052): defense-in-depth -- catches anything that slipped past the creation check.

```python
class ConfigChangeSafetyValidator:
    PROTECTED_PATHS = [
        "system/security/",
        "system/auth/",
        "_activity/",
    ]

    BLOCKED_CONTENT_PATTERNS = [
        r"default_gate_policy:\s*none",
        r"approval_tier:\s*(auto|none)",
        r"tools:\s*\[.*delete_file.*\]",  # agents shouldn't get destructive tools via self-edit
    ]

    def validate(self, file_path: str, proposed_content: str) -> tuple[bool, str | None]:
        for prefix in self.PROTECTED_PATHS:
            if file_path.startswith(prefix):
                return False, f"Cannot modify protected path: {prefix}"

        for pattern in self.BLOCKED_CONTENT_PATTERNS:
            if re.search(pattern, proposed_content, re.IGNORECASE):
                return False, f"Proposed content matches blocked pattern"

        return True, None
```

### 4. Orchestration-check workflow structure

```markdown
---
name: orchestration-check
description: Periodic check for recurring patterns and active threads.
version: 1
default_gate_policy: none
---

## Parameters
| Parameter | Required | Description |
|-----------|----------|-------------|
| scope | no | 'full' or 'incremental' (default: incremental) |

## Steps

### step-1: Scan signals
- **agent:** pattern-detector
- **depends_on:** []
- **tools:** [read_file, search_gmail, list_calendar_events]
- **description:** Read recent captures (14 days), activity log, vault changes. Identify recurring patterns. Cross-reference against existing workflows and recent rejected proposals. Output structured pattern list.
- **gate:** none

### step-2: Advance threads
- **agent:** thread-planner
- **depends_on:** []
- **tools:** [read_file, write_file, search_gmail, list_calendar_events, web_search]
- **description:** For each active thread with next_action_at in the past, drive it forward. For each watching thread, check watch conditions. Update thread-doc progress and status.
- **gate:** none

### step-3: Create proposals
- **agent:** pattern-detector
- **depends_on:** [step-1]
- **tools:** [read_file, write_file]
- **description:** For each pattern meeting the proposal threshold, create a workflow_proposal or config_change approval card. Respect rate limits. Include pattern evidence and proposed content.
- **gate:** none
```

### 5. Thread router

```python
router = APIRouter(prefix="/vault/threads", tags=["threads"])

@router.get("")
async def list_threads(
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
    status: str | None = Query(default=None),
):
    """List thread summaries. Optionally filter by status."""
    service = ThreadService(vault)
    threads = await service.list_active_threads(user_id)
    if status:
        threads = [t for t in threads if t["status"] == status]
    return {"threads": threads}

@router.post("/{slug}/status")
async def change_thread_status(
    slug: str,
    payload: ChangeStatusRequest,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Change a thread's status. Validates transition rules."""
    service = ThreadService(vault)
    rel_path = f"_threads/{slug}.md"
    await service.change_status(user_id, rel_path, payload.status)
    return {"status": payload.status}
```

### 6. Frontend types

```typescript
// api/types/thread.ts

export interface ThreadSummary {
  path: string;
  title: string;
  status: 'active' | 'watching' | 'paused' | 'completed' | 'archived';
  next_action: string | null;
  blocked_on: string | null;
  created_at: string;
  updated_at: string;
}

export interface ThreadDoc {
  frontmatter: Record<string, unknown>;
  body: string;
  path: string;
}
```

---

## Edge Cases

- **Thread title collision:** two threads with the same title on the same day produce the same filename. The `create_thread` method appends a numeric suffix (`-2`, `-3`) when the path already exists.
- **Orchestration-check runs with no signals:** the workflow completes with no proposals and no thread advances. Activity log entry: "Orchestration check completed -- no patterns detected."
- **User edits a thread-doc manually:** the thread-planner reads the file before writing. If `updated_at` changed since the last agent write, the agent respects the user's edits and merges non-conflicting changes (appends to Progress, does not overwrite user-edited sections). On true conflict, the agent defers to the user's content and notes the conflict in Progress.
- **Thread-planner invoked for a thread that was archived:** the planner reads the status, sees `archived`, and skips the thread. No error.
- **Rate limit hit during orchestration-check:** the workflow logs which proposals were suppressed and why. The next day's run can pick them up if the pattern persists.
- **Rejected proposal check finds a semantically similar but textually different proposal:** Stage 5 uses simple substring and path matching for similarity. Embedding-based similarity is deferred. If in doubt, the agent does not re-propose. [A14]
- **Config change proposed for a file that doesn't exist:** the card is created with the proposal. If approved, the executor writes the file (creating it). This is intentional -- proposing a new skill file that doesn't exist yet is a valid use case.
- **Safety validator false positive:** a legitimate config change is blocked by an overly broad pattern. The activity log records the rejection with reasoning. The user can manually make the change via the file editor (SPEC-047). The blocked patterns list is iterated based on false positive feedback.
- **Multiple orchestration-check runs in one day:** each run independently checks rate limits by counting today's cards. The limits apply to the cumulative total, not per-run.
- **User disables orchestration_check_enabled while threads are active:** active threads remain in their current state but are not advanced. They surface in the vault browser but not in Today's Agent section (the regeneration workflow checks the preference before including threads). Re-enabling resumes normal advancement.
- **Thread with `blocked_on` set but status is `watching`:** this is valid. The thread surfaces under "Watching" in Today, with the `blocked_on` text explaining what it is waiting for.
- **Very large number of threads (>100):** `list_active_threads` reads frontmatter from each file. At 100 threads with ~1KB frontmatter each, this is ~100KB of reads -- acceptable. If it becomes slow, a materialized index (similar to the entity index in SPEC-053) can be added.

---

## Testing Requirements

### Unit Tests

- `test_thread_service.py`: create_thread writes correct frontmatter and body; status transitions validated (all valid paths succeed, invalid paths rejected with 422); list_active_threads filters correctly; filename collision handled with suffix.
- `test_orchestration_service.py`: rate limits enforced (proposal blocked after limit); rejection cooldown checked (similar proposal within 30 days blocked); consecutive rejection pause triggered at threshold; user-specific limit overrides respected.
- `test_config_change_validator.py`: protected paths rejected; blocked patterns rejected; safe changes pass; case-insensitive pattern matching works; empty content passes.

### Integration Tests

- `test_thread_api.py`: auth required on all endpoints; cross-user isolation; list returns only user's threads; status change round-trip; invalid slug returns 404.
- `test_orchestration_check.py`: workflow runs to completion; proposals respect rate limits; rejected-proposal cooldown works end-to-end.

---

## Resolved Questions (2026-04-21, Tim approved all recommendations)

### 1. Thread creation from chat — **RESOLVED: hybrid with confirmation prompt**

Agent detects intent and proposes: "This sounds like multi-step work. Create a thread?" User confirms. Aligns with approval-lane philosophy, prevents misfires.

### 2. Safety validator placement — **RESOLVED: pre-creation + pre-execution**

Unsafe proposals never enter the approval lane. The user only sees actionable items. Pre-creation validation is cheap and the blocked-patterns list is small.

### 3. Thread-doc body format ��� **RESOLVED: structured minimum, open to additional sections**

Goal, Plan, Progress, Findings, Open Questions, Notes as the template. Agent can add sections as needed; `markdown_sections` preserves them.

### 4. Orchestration-check schedule — **RESOLVED: daily only for Stage 5**

Runs once at configured time. "Co-worker checks in once a day." Event-triggered advancement is a natural extension once the daily rhythm proves the model.

---

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-21)
- [x] Thread-doc format defined (frontmatter schema, body structure, status lifecycle, filename convention)
- [x] Orchestration proposal trigger model defined (pattern detection, threshold, evidence)
- [x] Thread-planner agent contract defined (model, tools, what it can and cannot do)
- [x] How threads surface in Today's Agent section defined
- [x] Self-improvement loop defined (what can change, what cannot, safety boundaries)
- [x] Safety boundaries explicit: protected paths, blocked patterns, hard limits on what cannot be proposed
- [x] Maximum blast radius of an approved proposal documented (one file, git-recoverable)
- [x] Noise prevention mechanisms defined (rate limits, rejection cooldown, consecutive rejection pause, master switch)
- [x] Stage 1-4 preservation constraints enumerated in a table
- [x] Rollback mechanism defined (manual for Stage 5, data model supports automated rollback later)
- [x] Edge cases documented with expected behavior
- [x] Technical decisions cite principles (A2, A8, A10, A12, A13, A14; F1)
- [x] Decisions requiring input called out with options, tradeoffs, and recommendations
- [x] No overlap with SPEC-055 (agent autonomy -- pre-vault trust system, different architecture)
- [x] Vision doc caveats addressed: "self-improvement is free for technical users" with rollback, conservative defaults, and safety validation for non-technical users
