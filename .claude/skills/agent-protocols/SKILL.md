---
name: agent-protocols
description: Shared protocols for domain agents — blocker handling, git coordination, escalation, and task completion. Read this before starting any task.
---

# Agent Protocols — Shared Rules for Domain Agents

Read this before starting any task. These protocols apply to all domain agents: backend-dev, frontend-dev, database-dev, deployment-dev, and uat-tester.

## When Reviewer Finds a Blocker

1. Read the reviewer's VERDICT — understand WHAT is wrong and WHY (principle ID tells you why)
2. Fix on your existing branch (new commit — never amend, never force-push)
3. Run all tests — they must pass
4. Push and message orchestrator: "Fix committed for [BLOCKER]. Branch: [branch]. Ready for re-review."

## When You're Stuck

1. Read the error, check architecture-principles skill and your domain skill, attempt ONE fix
2. If it doesn't work: message orchestrator with what you tried and what went wrong
3. Do NOT retry the same action more than twice
4. Do NOT ask the user directly — go through the orchestrator

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

If you find >50% overlap with an existing service/table/component, **STOP and message the orchestrator** with:
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

## Before Declaring Done

Your task contract may have been compressed during this session. Before marking complete:

1. **Re-read your task:** `TaskGet` with your task ID — the description field is durable storage
2. **Check every deliverable** listed in the task description against what you've committed
3. **If you can't remember your full scope, re-read it** — don't guess from what's in front of you
4. Run verification (tests + lint) one final time
5. Only then: `TaskUpdate` status to completed + message the orchestrator
