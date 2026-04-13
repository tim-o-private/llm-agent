---
name: self-improvement
description: >
  How to create new skills and workflow templates when you notice repeatable patterns.
  Covers file formats, decision criteria, and examples.
---

# Self-Improvement

You can extend your own capabilities by creating skills and workflow templates.
These persist across sessions and are auto-discovered.

## When to Create a Skill

Create a skill when you notice a pattern you've handled more than twice:
- A recurring question type that requires specific steps
- A domain-specific process the user follows regularly
- A preference set that affects how you handle a category of work

**Don't create a skill for:** one-off tasks, simple preferences (put those in
your working memory), or things that are better tracked as tasks.

## Skill Format

Write to `/user/skills/{skill-name}/SKILL.md`:

```markdown
---
name: skill-name
description: >
  One-line description of what this skill does and when to use it.
---

# Skill Name

[Instructions, procedures, decision criteria, examples]
```

The description is how you'll find this skill later — make it specific enough
that you'll know when to load it.

## When to Create a Workflow

Create a workflow template when you notice a multi-step process that:
- Has a consistent sequence of steps
- Involves gathering information, then synthesizing, then acting
- Benefits from structure (steps might get skipped in freeform conversation)

## Workflow Format

Write to `/user/workflows/{workflow-name}.md`. Use existing system workflows
as reference — read any file in `/system/workflows/` to see the format.

## Decision Guide

| Signal | Action |
|--------|--------|
| User corrects you the same way twice | Update working memory with the preference |
| You follow the same 3+ steps repeatedly | Create a skill |
| A multi-step process keeps losing state | Create a workflow template |
| User describes a recurring task | Create a scheduled task, not a skill |

## Quality Check

Before creating a skill or workflow, verify:
- It captures a genuine pattern, not a one-off
- The description is specific enough for future discovery
- It doesn't duplicate an existing skill (check `/system/skills/` first)
