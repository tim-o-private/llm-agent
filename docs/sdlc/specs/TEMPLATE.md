# SPEC-NNN: Title

> **Status:** Draft | Ready | In Progress | Review | Done
> **Author:** [name]
> **Created:** YYYY-MM-DD
> **Updated:** YYYY-MM-DD

## Goal

One paragraph describing what this spec achieves and why it matters.

## Acceptance Criteria

Testable conditions that must be true when this spec is complete:

- [ ] AC-1: [Specific, testable criterion]
- [ ] AC-2: [Specific, testable criterion]
- [ ] AC-3: [Specific, testable criterion]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `path/to/file.py` | Description |

### Files to Modify

| File | Change |
|------|--------|
| `path/to/file.py` | Description of modification |

### Out of Scope

- [Things this spec explicitly does NOT do]
- [Adjacent features that belong in a different spec]

## Technical Approach

Reference skills and patterns:

1. **Step 1:** Description (see `backend-patterns` skill for service layer pattern)
2. **Step 2:** Description (see `database-patterns` skill for RLS setup)
3. **Step 3:** Description (see `frontend-patterns` skill for hook pattern)

### Dependencies

- [Other specs or external systems this depends on]
- [Database tables that must exist]

## Testing Requirements

### Unit Tests (required)

- Every new function/method gets at least one test
- Every new service class gets tests for its public methods
- Test files go in `tests/` mirroring the source structure

### Integration Tests (required for API/DB changes)

- New API endpoints: test request -> response cycle with auth
- New database tables: test RLS policies with owner/non-owner
- New frontend hooks: test data fetching with mocked API

### What to Test

- Happy path for each acceptance criterion
- Auth failure (401/403)
- Invalid input
- Edge cases listed below

### Manual Verification (UAT)

- [ ] Step-by-step manual test plan for the user

## Edge Cases

- [Edge case 1: description and expected behavior]
- [Edge case 2: description and expected behavior]

## Functional Units (for PR Breakdown)

Each unit gets its own branch and PR:

1. **Unit 1:** Migration + RLS (`feat/SPEC-NNN-migration`)
2. **Unit 2:** Service layer (`feat/SPEC-NNN-service`)
3. **Unit 3:** API endpoints + tests (`feat/SPEC-NNN-api`)
4. **Unit 4:** Frontend components + hooks + tests (`feat/SPEC-NNN-ui`)
