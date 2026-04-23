---
name: orchestration-check
description: |
  Periodic check for recurring patterns and active threads.
  Proposes new workflows when patterns recur, advances active
  threads, and surfaces items needing user attention.
version: 1
default_gate_policy: none
---

# Orchestration Check

Scheduled or on-demand workflow that scans for recurring work patterns,
advances active threads, and creates proposals when patterns meet the
threshold. Runs daily at the user's configured `orchestration_check_time`.

Gated by `user_preferences.orchestration_check_enabled` (default: false).

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
