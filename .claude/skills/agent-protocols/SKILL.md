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

## Before Declaring Done

Your task contract may have been compressed during this session. Before marking complete:

1. **Re-read your task:** `TaskGet` with your task ID — the description field is durable storage
2. **Check every deliverable** listed in the task description against what you've committed
3. **If you can't remember your full scope, re-read it** — don't guess from what's in front of you
4. Run verification (tests + lint) one final time
5. Only then: `TaskUpdate` status to completed + message the orchestrator
