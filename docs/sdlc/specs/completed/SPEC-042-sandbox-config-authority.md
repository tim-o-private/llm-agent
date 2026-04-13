# SPEC-042: Sandbox Config Authority — File-Based Agent Loading

> **Status:** Superseded by SPEC-043 (Deep Agents Runtime)
> **Author:** Claude (Architecture) + Tim
> **Date:** 2026-04-07
> **Depends on:** SPECs 038-041 (bwrap sandbox plumbing — implemented)
> **References:** ARCHITECTURE-PROPOSAL-next-gen.md, PRODUCT-BEHAVIOR-SPEC-next-architecture.md, ~/github/hq/ (source framework)

---

## Problem Statement

SPECs 038-041 built the sandbox infrastructure (bwrap execution, provisioner, git tracker, sync service, security boundary, self-improvement service, approval flow) but never ported the file-based agent/skill framework from hq. The sandbox tree is empty directories. Agent loading still reads entirely from Postgres (`agent_configurations`, `tools`, `agent_tools`, `user_agent_prompt_customizations`). The introspection loop references non-existent tools and files. Nothing in the sandbox feeds back into agent behavior.

The architecture proposal states: *"DB-stored agent config becomes filesystem-based definitions"* and *"The HQ operating model ports directly — config as files, agent edits files, git tracks changes."*

This spec delivers on that promise.

---

## Design Principles

1. **Files are the config authority.** The sandbox tree defines agent behavior. Postgres is a fallback during migration, then deprecated.
2. **Port the pattern, not the code.** hq uses symlinks + Claude Code directory walking. Clarity uses Supabase Storage + ConfigHydrator. Different mechanism, same pattern: system defaults + user overrides, discovered as skills.
3. **Agent SDK skill format.** Agent configuration is expressed as `SKILL.md` files that the Claude Agent SDK discovers and loads. This gives immediate effect — change a file, agent behavior changes on next invocation.
4. **Graceful degradation.** When `BWRAP_ENABLED=false`, fall back to Postgres. The system works in both modes during migration.

---

## Sandbox Tree Structure

### System layer (read-only, deployed as code)

Stored in Supabase Storage at `/system/`, mounted read-only in bwrap at `/system/`.

```
system/
  skills/
    clarity-soul/
      SKILL.md               # Behavioral philosophy, personality, values
    clarity-identity/
      SKILL.md               # Name, vibe, greeting style, tone rules
    safety-guidelines/
      SKILL.md               # Hard boundaries, what never to do
    tool-guidance/
      SKILL.md               # General guidance for using tools effectively
      references/
        gmail.md              # Gmail-specific patterns
        calendar.md           # Calendar-specific patterns
        memory.md             # Memory tool patterns
  agent.md                    # Default agent definition (frontmatter: tools, model, skills list)
```

### User layer (read-write, per-user)

Stored in Supabase Storage at `/users/{user_id}/`, hydrated to local disk, mounted read-write in bwrap.

```
users/{user_id}/
  skills/
    communication-preferences/
      SKILL.md               # Briefing length, verbosity, notification style
    domain-knowledge/
      SKILL.md               # What the user does, their context, preferences
    custom-workflows/
      SKILL.md               # User-specific workflow triggers and patterns
  agent.md                    # User overrides (optional — extends system agent.md)
  memory/
    observations.md           # Agent's learned observations about this user
  .gitignore
  .git/
```

### Overlay resolution

When loading agent config:
1. User's `agent.md` extends (not replaces) system `agent.md`
2. User skills are discovered alongside system skills — both loaded
3. User skills with the same name as system skills override them

### Skill file format

Following the Agent SDK / Claude Code convention:

```markdown
---
name: clarity-soul
description: >
  Core behavioral philosophy for the Clarity agent.
  Defines personality, values, and interaction style.
---

# Clarity Soul

You are Clarity, a personal agent that exercises executive function
on behalf of individuals...

[rest of behavioral content]
```

### Agent definition format

```markdown
---
name: clarity
model: claude-sonnet-4-5-20250514
tools:
  - SearchGmailTool
  - GetGmailTool
  - CreateTasksTool
  # ... full tool list
skills:
  - clarity-soul
  - clarity-identity
  - safety-guidelines
  - tool-guidance
---

# Agent Instructions

[Channel-specific guidance, response format rules, etc.]
```

---

## Functional Units

### FU-1: Seed System Layer in Supabase Storage

**What:** Create a seed script that populates the system layer in Supabase Storage from current Postgres values.

**Why:** The ConfigHydrator downloads from Storage on first provision. The bucket is currently empty.

**Inputs:**
- `agent_configurations` table: `soul`, `identity`, `llm_config`, `prompt_template` columns
- Current hardcoded prompt assembly in `build_agent_prompt()` / `conversation_handler_builder.py`

**Outputs:**
- `scripts/seed_config_storage.py` — reads from Postgres, writes to Supabase Storage
- System skills: `clarity-soul/SKILL.md`, `clarity-identity/SKILL.md`, `safety-guidelines/SKILL.md`, `tool-guidance/SKILL.md`
- System `agent.md` with tool list from `agent_tools` table

**ACs:**
- AC-01: Seed script reads current `soul` from `agent_configurations` and writes to `system/skills/clarity-soul/SKILL.md` in Storage
- AC-02: Seed script reads current `identity` JSON and writes to `system/skills/clarity-identity/SKILL.md` as formatted markdown
- AC-03: Seed script creates `system/agent.md` with frontmatter listing all active tools from `agent_tools` JOIN `tools`
- AC-04: Seed script creates `system/skills/tool-guidance/SKILL.md` from existing tool prompt sections
- AC-05: Seed script creates `system/skills/safety-guidelines/SKILL.md` from existing safety/boundary content
- AC-06: Running seed script twice is idempotent (uses `write_system` with upsert)
- AC-07: Seed script also writes user-layer skills for existing `user_agent_prompt_customizations` rows

### FU-2: Update ConfigHydrator for Skill Tree

**What:** Update `ConfigHydrator.hydrate()` to create the skill directory structure and populate with downloaded files.

**Why:** Currently creates bare directories (`agents/`, `workflows/`, `preferences/`, `memory/`). Should create `skills/` and download skill files from Storage.

**ACs:**
- AC-08: Hydrator creates `skills/` subdirectory in user tree
- AC-09: Hydrator downloads system-layer skills alongside user-layer skills (system skills are read-only reference copies)
- AC-10: Hydrator preserves existing tree structure (backwards compatible)
- AC-11: Post-hydration, user tree has a working set of `SKILL.md` files the agent can read

### FU-3: Agent Loading from File Tree

**What:** Update agent initialization to read config from the sandbox file tree instead of (or in addition to) Postgres.

**Why:** This is the core requirement. Without this, the sandbox is write-only.

**Integration point:** `ConversationHandlerBuilder.build()` and/or `load_agent_executor_db_async()` — wherever the agent's system prompt and tool list are assembled.

**Approach:**
1. At session init, check if user has a provisioned sandbox
2. If yes: read `agent.md` + discover `skills/` from the user's sandbox directory
3. Assemble system prompt from skill files instead of DB columns
4. Fall back to Postgres if sandbox unavailable or files missing

**ACs:**
- AC-12: `ConversationHandlerBuilder` reads `agent.md` from sandbox when available
- AC-13: `ConversationHandlerBuilder` discovers and loads `SKILL.md` files from `skills/` directories (both system and user layer)
- AC-14: Skill content is assembled into the system prompt in a structured way (each skill as a labeled section)
- AC-15: Tool list from `agent.md` frontmatter determines which tools are loaded (with Postgres fallback)
- AC-16: User instructions from `user_agent_prompt_customizations` fall back to `skills/communication-preferences/SKILL.md`
- AC-17: When `BWRAP_ENABLED=false`, agent loading falls back to current Postgres path entirely
- AC-18: Agent loading reads from local disk (hydrated cache), NOT from Supabase Storage on every request

### FU-4: Register Workflow Service Nodes

**What:** Register `gather_metrics` and `apply_improvements` with the `GraphBuilder` service registry so the introspection workflow can execute.

**Why:** Service nodes exist as functions but are never registered. The workflow engine would crash at runtime.

**ACs:**
- AC-19: `WorkflowRunManager` registers `gather_metrics` as service for step name `gather-signals`
- AC-20: `WorkflowRunManager` registers `apply_improvements` as service for step name `apply-changes`
- AC-21: Registration happens before graph compilation, verified by test

### FU-5: Fix Introspection Template

**What:** Update the introspection template and prompts to reference actual skill files and use the real service nodes.

**Why:** Template references non-existent tools (`read_file`, `write_file`) and non-existent files (`/user/agent/instructions.md`).

**Approach:** Steps 1 and 4 are service nodes (Python functions), not LLM-with-tools steps. They don't need `read_file`/`write_file` tools — they read/write the filesystem directly in Python. Steps 2 and 3 are LLM steps that receive the output of step 1 as context.

**ACs:**
- AC-22: `gather_metrics` service node reads skill files from the user's sandbox tree (soul, preferences, observations) alongside DB metrics
- AC-23: `apply_improvements` service node writes `SKILL.md` files to the sandbox tree (not arbitrary files)
- AC-24: Template step definitions updated: steps 1 and 4 are `node_type: service`, steps 2 and 3 are LLM steps with no file tools
- AC-25: Template prompts reference actual skill paths (`/user/skills/communication-preferences/SKILL.md`, not `/user/agent/instructions.md`)
- AC-26: Proposals from step 3 target specific skill files, not arbitrary paths

### FU-6: Workflow Trigger

**What:** Add a job handler and schedule mechanism for the introspection loop.

**Why:** Nothing currently triggers the introspection workflow.

**ACs:**
- AC-27: `handle_introspection` job handler in `job_handlers.py` starts the introspection workflow for a given user
- AC-28: Introspection can be triggered by a scheduled job (default: weekly)
- AC-29: Introspection can be triggered manually via API endpoint (for testing)
- AC-30: Job handler passes user's trust tier to the workflow parameters

---

## What Is NOT In Scope

- **Capability Gateway** (ARCHITECTURE-PROPOSAL Q2) — separate spec
- **Tool registry migration** — `tools` table stays in Postgres
- **LangChain removal** — separate effort
- **Web frontend file browser** — API exists, frontend is separate
- **ChangeTracker, RollbackService, SecurityConfigService** (SPEC-039 extras) — deferred
- **`/tools/` bwrap mount** — not needed; tools run server-side via Python, not as CLI tools inside bwrap
- **ConversationHandler v2 migration** — separate effort (feature flag already exists)

---

## Postgres Deprecation Path

After FU-3 is confirmed working:

| Column/Table | Status | Removal Timeline |
|---|---|---|
| `agent_configurations.soul` | Fallback only | Drop after 1 migration cycle |
| `agent_configurations.identity` | Fallback only | Drop after 1 migration cycle |
| `agent_configurations.prompt_template` | Fallback only | Drop after 1 migration cycle |
| `user_agent_prompt_customizations` | Fallback only | Drop after 1 migration cycle |
| `agent_configurations.llm_config` | Keep (operational, not behavioral) | Stays |
| `tools` table | Keep (tool registry) | Stays |
| `agent_tools` table | Keep (system-level assignment) | Stays |
| All transactional tables | Keep | Stays |

---

## Testing Strategy

- **Unit tests:** Skill file parsing, prompt assembly from files, overlay resolution
- **Integration test:** Seed → hydrate → load agent → verify system prompt contains skill content
- **Introspection test:** Trigger workflow → verify proposal targets valid skill path → approve → verify file written → verify next agent load picks up change
- **Fallback test:** `BWRAP_ENABLED=false` → verify Postgres path still works unchanged

---

## Implementation Order

1. **FU-1** (seed) — creates the content that everything else depends on
2. **FU-2** (hydrator update) — so provisioning produces a useful tree
3. **FU-3** (agent loading) — the core requirement; makes sandbox load-bearing
4. **FU-4** (service node registration) — unblocks workflow execution
5. **FU-5** (template fix) — makes introspection loop functional
6. **FU-6** (trigger) — makes introspection loop run

FU-4 through FU-6 can parallelize after FU-3.
