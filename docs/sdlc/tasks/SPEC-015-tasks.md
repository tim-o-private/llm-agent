# SPEC-015 Task Breakdown

> **Spec:** `docs/sdlc/specs/SPEC-015-prompt-overhaul.md`
> **Branch:** `feat/SPEC-015-prompt-overhaul`
> **PR Strategy:** Single PR, 4 sequential commits (one per FU)
> **Status:** Ready for execution

## Team Structure

| Role | Agent | Responsibility |
|------|-------|---------------|
| **Orchestrator** | me (team lead) | Validate compliance, manage branch, create PR |
| **backend-dev-tools** | backend-dev (haiku) | Task 1: FU-1 — tool `prompt_section()` methods + tests |
| **backend-dev-builder** | backend-dev (haiku) | Tasks 2–4: FU-2/3/4 — prompt builder, loader, memory, channels |
| **reviewer** | reviewer (haiku) | Task 5: Final review against all ACs |

## Why Two Backend Agents (Not One)

- FU-1 (7 tool files + test file) is the largest piece and fully independent
- FU-2/3/4 all modify `prompt_builder.py` — one agent avoids merge conflicts
- Sequential handoff: backend-dev-tools finishes → backend-dev-builder starts on same branch
- Keeps each agent's scope small enough for haiku

## Tasks

---

### Task 1: Add `prompt_section()` to Tool Classes
**FU:** FU-1
**Agent:** backend-dev-tools
**ACs:** AC-01, AC-07, AC-10
**Depends on:** nothing
**Status:** [ ] pending

**Deliverables:**
1. Add `prompt_section(channel)` classmethod to 7 tool classes (exact return values in spec FU-1 contract)
2. Create `tests/chatServer/tools/test_tool_prompt_sections.py`
3. Commit: `SPEC-015: add prompt_section() classmethods to tool classes`

**Files to modify:**
- `chatServer/tools/task_tools.py` → `GetTasksTool`
- `chatServer/tools/memory_tools.py` → `SaveMemoryTool`
- `chatServer/tools/gmail_tools.py` → `GmailSearchTool`
- `chatServer/tools/reminder_tools.py` → `CreateReminderTool`
- `chatServer/tools/schedule_tools.py` → `CreateScheduleTool`
- `chatServer/tools/update_instructions_tool.py` → `UpdateInstructionsTool`
- `chatServer/tools/email_digest_tool.py` → `EmailDigestTool`

**Files to create:**
- `tests/chatServer/tools/test_tool_prompt_sections.py`

**Verification:** `pytest tests/chatServer/tools/test_tool_prompt_sections.py -x -q && ruff check chatServer/tools/`

**Done when:** Tests pass, ruff clean, commit pushed to branch.

---

### Task 2: Update Prompt Builder — Tool Guidance Collector
**FU:** FU-2
**Agent:** backend-dev-builder
**ACs:** AC-02, AC-03
**Depends on:** Task 1
**Status:** [ ] pending

**Deliverables:**
1. Change `build_agent_prompt()` signature: `tool_names` → `tools`
2. Replace `## Tools` flat listing with `## Tool Guidance` collector loop
3. Update both `load_agent_executor_db()` and `load_agent_executor_db_async()` to pass `tools=instantiated_tools`
4. Create `tests/chatServer/services/test_prompt_builder.py` (tool guidance tests)
5. Commit: `SPEC-015: replace tool name listing with tool guidance collector`

**Files to modify:**
- `chatServer/services/prompt_builder.py` (signature + section 7)
- `src/core/agent_loader_db.py` (both sync and async paths)

**Files to create:**
- `tests/chatServer/services/test_prompt_builder.py`

**Verification:** `pytest tests/chatServer/services/test_prompt_builder.py -x -q && ruff check chatServer/services/prompt_builder.py src/core/agent_loader_db.py`

**Done when:** Tests pass, ruff clean, commit pushed to branch.

---

### Task 3: Pre-loaded Memory Context
**FU:** FU-3
**Agent:** backend-dev-builder
**ACs:** AC-04, AC-05, AC-08
**Depends on:** Task 2
**Status:** [ ] pending

**Deliverables:**
1. Delete `MEMORY_SECTION` constant from `prompt_builder.py`
2. Delete `## Memory` section from `build_agent_prompt()`
3. Add `## What You Know` section (conditional on `memory_notes` truthiness)
4. DO NOT touch `ONBOARDING_SECTION` or its detection logic
5. Add memory-related tests to `tests/chatServer/services/test_prompt_builder.py`
6. Commit: `SPEC-015: replace static memory section with pre-loaded context`

**Files to modify:**
- `chatServer/services/prompt_builder.py` (constant + section 5)
- `tests/chatServer/services/test_prompt_builder.py` (extend)

**Verification:** `pytest tests/chatServer/services/test_prompt_builder.py -x -q && ruff check chatServer/services/prompt_builder.py`

**Done when:** Tests pass, ruff clean, onboarding still works, commit pushed to branch.

---

### Task 4: Expand Channel Guidance
**FU:** FU-4
**Agent:** backend-dev-builder
**ACs:** AC-06
**Depends on:** Task 2
**Status:** [ ] pending

**Deliverables:**
1. Replace `CHANNEL_GUIDANCE` dict with expanded versions (exact text in spec FU-4 contract)
2. Add channel guidance tests to `tests/chatServer/services/test_prompt_builder.py`
3. Commit: `SPEC-015: expand channel guidance for heartbeat and scheduled`

**Files to modify:**
- `chatServer/services/prompt_builder.py` (lines 6-18)
- `tests/chatServer/services/test_prompt_builder.py` (extend)

**Verification:** `pytest tests/chatServer/services/test_prompt_builder.py -x -q && ruff check chatServer/services/prompt_builder.py`

**Done when:** Tests pass, ruff clean, commit pushed to branch.

---

### Task 5: Review All Changes Against Spec
**Agent:** reviewer (or orchestrator)
**ACs:** AC-01 through AC-10 (all)
**Depends on:** Tasks 1–4
**Status:** [ ] pending

**Checklist:**
- [ ] AC-01: Every tool class listed in FU-1 has `prompt_section(channel)` classmethod
- [ ] AC-02: `build_agent_prompt()` produces `## Tool Guidance` from tool objects
- [ ] AC-03: Both loader paths pass `tools=instantiated_tools` (no `tool_names`)
- [ ] AC-04: `## What You Know` appears when `memory_notes` is truthy
- [ ] AC-05: `MEMORY_SECTION` constant is gone; guidance in tool prompt sections
- [ ] AC-06: `CHANNEL_GUIDANCE` has rich text for all 4 channels
- [ ] AC-07: `prompt_section()` returns different values per channel (verified by Gmail web vs heartbeat)
- [ ] AC-08: Onboarding triggers when `memory_notes` falsy + `user_instructions` falsy + interactive
- [ ] AC-09: All FUs have tests, all tests pass
- [ ] AC-10: No `prompt_section()` return exceeds 300 chars
- [ ] No scope violations (no DB migrations, no frontend, no new tools)
- [ ] `pytest tests/ -x -q` — full test suite passes (no regressions)
- [ ] `ruff check chatServer/ src/` — no new lint errors

**Done when:** All checks pass, PR ready for human review.

## Execution Sequence

```
1. Orchestrator creates branch: feat/SPEC-015-prompt-overhaul
2. Spawn backend-dev-tools → Task 1 (FU-1)
3. Orchestrator validates Task 1 output
4. Spawn backend-dev-builder → Tasks 2, 3, 4 (FU-2, FU-3, FU-4) sequentially
5. Orchestrator validates Tasks 2–4 output
6. Run full verification (Task 5 checklist)
7. Create PR
```

## Risk Notes

- `prompt_builder.py` is small (136 lines) — merge conflicts unlikely between tasks on same branch
- `agent_loader_db.py` has two code paths (sync + async) — both MUST be updated in Task 2
- FU-3 removes `MEMORY_SECTION` which is currently used on line 91 — must happen AFTER FU-2 so the `## Memory` section replacement is clean
- `ruff check` has ~200 pre-existing E501/F401 errors — only check for NEW errors in modified files
