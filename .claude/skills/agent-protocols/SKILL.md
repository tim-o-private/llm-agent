---
name: agent-protocols
description: Shared protocols for domain agents — blocker handling, git coordination, escalation, and task completion. Read this before starting any task.
---

# Agent Protocols — Shared Rules for Domain Agents

Read this before starting any task. These protocols apply to all domain agents: backend-dev, frontend-dev, database-dev, deployment-dev, reviewer, and uat-tester.

## Task Lifecycle (MANDATORY)

The shared task list is the single source of truth for who's working on what. Use `TaskList` to see all tasks. Use `TaskGet` and `TaskUpdate` to manage your own.

**Before you touch ANY code, you MUST claim your task:**

```
TaskUpdate: taskId=<id>, status="in_progress", owner="<your-agent-name>"
```

### Statuses

| Status | Meaning | Who sets it |
|--------|---------|-------------|
| `pending` | Available, not started | Lead (at creation) |
| `in_progress` | Being worked on — **check owner before touching** | Agent claiming it |
| `completed` | Done, review passed, merged | Agent (after review passes) |

### Rules

1. **Check `TaskList` before starting ANY work.** If a task is `in_progress` with another agent's name, DO NOT work on it or any files it covers.
2. **Claim before coding.** Set `status: "in_progress"` and `owner: "<your-name>"` as your FIRST action on any task. If you can't claim it (already in_progress), message the lead.
3. **One agent per task.** Never have two agents working on the same task. If you need help, message the other agent — don't start editing their files.
4. **Signal review readiness.** When your code is committed, pushed, and ready for review, update the task description to prepend `[REVIEW REQUESTED]` and message the reviewer (or lead):
   ```
   TaskUpdate: taskId=<id>, description="[REVIEW REQUESTED] <original description>"
   ```
5. **Mark complete only after review passes.** Don't set `completed` until the reviewer sends a PASS verdict. The lifecycle is:
   ```
   pending → in_progress (you claim it)
     → [REVIEW REQUESTED] (code done, pushed, awaiting review)
     → reviewer finds BLOCKER → you fix → [REVIEW REQUESTED] again
     → reviewer PASS → completed
   ```
6. **Check task list between tasks.** After completing one task, call `TaskList` to find your next available task (pending, no owner, not blocked).

### What the lead does

The lead creates tasks, sets dependencies (`addBlockedBy`), and assigns initial owners. But agents must still verify ownership before starting — the lead may reassign tasks between when you last checked and when you start.

### Conflict resolution

If you discover another agent has committed to files in YOUR claimed task's scope:
1. `git pull` to see their changes
2. Message the lead with: "Conflict: [agent] committed to [file] which is in my task [id]"
3. Do NOT overwrite their changes. Wait for the lead to resolve ownership.

## File Safety — NEVER Delete or Modify Files Outside Your Task

**This is the #1 rule. Violating it can destroy other agents' work or the user's in-progress changes.**

- **Only modify files listed in your task contract.** If a file isn't in your contract, don't touch it — even if you think it's "dead code," "superseded," or "no longer needed."
- **NEVER delete files** that aren't explicitly listed as deliverables in your task. If you think a file should be removed (e.g., old code replaced by your new code), **flag it to the lead** — don't delete it yourself.
- **If tests or lint fail because of files outside your scope, that's OK.** Report the failure to the lead with the file path and error. Do NOT fix files outside your scope to make checks pass.
- **If imports break because of your changes,** only fix imports IN files you own. If a file outside your scope imports something you changed, flag it — don't edit that file.
- **NEVER "clean up" old code after implementing a replacement.** The lead decides when old code gets removed, not individual agents.
- **NEVER use `git checkout --` or `git restore` to discard changes.** These commands destroy uncommitted work. If you see unrelated changes in the working tree, flag them to the lead — don't remove them. (This is enforced by a hook — the command will be blocked.)

**Why:** Uncommitted deletions and discarded changes are invisible to other agents and the lead. If you delete a file or discard changes another agent or the user depends on, there's no commit to revert — the work is just gone.

**What to do instead:**
```
Message to lead: "FU-3 replaces PendingActionsPanel with ApprovalInlineMessage.
Old files that may be removable: webApp/src/components/features/Confirmations/.
Flagging for cleanup — not deleting."
```

## When Reviewer Finds a Blocker

1. Read the reviewer's VERDICT — understand WHAT is wrong and WHY (principle ID tells you why)
2. Fix on your existing branch (new commit — never amend, never force-push)
3. Run all tests — they must pass
4. Push and message the reviewer directly: "Fix committed for [BLOCKER]. Branch: [branch]. Ready for re-review."
5. If the reviewer messaged you directly (peer-to-peer review), reply to them. If the lead routed the blocker, message the lead.

## When You're Stuck

1. Read the error, check architecture-principles skill and your domain skill, attempt ONE fix
2. If it doesn't work: message the lead with what you tried and what went wrong
3. Do NOT retry the same action more than twice
4. Do NOT ask the user directly — go through the lead

## Peer Communication

You can message teammates directly for cross-domain coordination. Use `SendMessage` with `recipient` set to their name.

**Handle peer-to-peer (don't escalate):**
- Cross-domain questions: "What column name did you use for the FK?" → message database-dev
- Contract validation: "Confirming the endpoint returns `{shape}`" → message backend-dev
- Review fixes: reviewer tells you what to fix, you fix it and message reviewer back
- Sharing context: "Here's the table DDL and column names — use these in your hook"

**Escalate to the lead when:**
- You and a peer disagree on an approach
- Your task contract doesn't match what you find in the codebase
- You're blocked and the relevant peer can't help
- A decision affects the user's product experience or overall architecture

**Communication style:**
- Be specific and batch information. One message with "table is `foos`, FK column is `foo_id UUID`, index on `(user_id, created_at)`" beats three separate questions.
- Include file paths and line numbers when referencing code.
- When asking a peer, state what you need and why: "Need the response shape from `POST /api/foos` so I can type the React Query hook."

## Git Coordination

- **You own your branch while your task is `in_progress`.** No one else should be editing it.
- If you're on a shared branch, always `git pull` or check `git log --oneline -3` before starting — the team lead or a prior agent may have committed ahead of you.
- **Commit early and often.** Uncommitted work is invisible to the team lead and can be overwritten.
- If the team lead messages you with a fix request, make the fix yourself and commit — don't wait for them to do it.
- When done, push immediately and report completion. Unpushed commits on a shared branch block everyone else.
- **Never force-push.** If you need to fix a commit, add a new commit.

## Common Rules

- **Stay in scope** — only modify files explicitly listed in your task contract
- Never push to `main`, never force-push

## Before Writing Code: Mandatory Survey

Every implementation task starts with a survey phase. You must check existing primitives
before creating anything new. Skip this only for pure bug fixes on existing code.

### Step 1: Check the primitives table

Read `.claude/skills/product-architecture/SKILL.md` — the "Platform Primitives" section.
If what you're building matches a row in that table, use the existing primitive.

Decision shortcuts:
- **Has a status lifecycle** (pending/processing/complete/failed)? → It's a job. Use the `jobs` table.
- **Runs periodically**? → It's a schedule. Use `agent_schedules`.
- **Tells the user something happened**? → It's a notification. Use `NotificationService`.
- **Invokes an agent**? → Use the existing agent invocation pipeline (ChatService / ScheduledExecutionService).
- **Stores user preferences**? → Use `update_instructions` tool or memory.
- **Needs user approval**? → Use `pending_actions` + approval tiers.
- **Connects to an external API**? → Use `external_api_connections` + OAuth flow.

### Step 2: Search for similar code

```bash
# Services
grep -r "class.*Service" chatServer/services/ | grep -i "<your-domain>"

# Tools
grep -r "class.*Tool" chatServer/tools/ | grep -i "<your-verb>"

# Tables
grep "CREATE TABLE" supabase/schema.sql | grep -i "<your-entity>"

# Handlers
grep -r "async def handle_" chatServer/services/job_handlers.py
```

### Step 3: Log your findings

Your **first commit message** on any task must include a survey line:

```
Survey: checked jobs table, NotificationService, existing handlers — no overlap.
```

or:

```
Survey: found existing EmailOnboardingService — extending with new method.
```

If you find >50% overlap with an existing service/table/component, **STOP and message the lead** with:
- Path to existing implementation
- Why it does or doesn't solve your need
- Proposed approach: extend existing vs. create new

Do NOT proceed until you get a response.

### What the reviewer checks

The reviewer will verify:
- No new tables with status lifecycle columns (use `jobs`)
- No new polling loops (use `JobRunnerService`)
- No new notification delivery paths (use `NotificationService`)
- No duplicate services for existing domains
- Survey line present in commit message

See the "Primitive Reuse (A11)" section in the reviewer checklist.

## Before Requesting Review

When your code is committed and pushed:

1. **Re-read your task:** `TaskGet` — the description is durable storage. Verify every deliverable is committed.
2. **If you can't remember your full scope, re-read it** — don't guess from what's in front of you.
3. Run verification (tests + lint) one final time.
4. Update task: `TaskUpdate` with description prepended with `[REVIEW REQUESTED]`.
5. Message the reviewer (or lead): "Task [id] ready for review. Branch: [branch]. Commits: [summary]."

## Before Declaring Done

Only after the reviewer sends a PASS verdict:

1. `TaskUpdate`: set `status: "completed"`
2. Message the lead: "Task [id] complete. Review passed."
3. Call `TaskList` to check for your next available task.
