# Active Tasks

> **Current tasks only** - No completed tasks or historical information

## In Progress

### Memory Bank Simplification (Phase 2)
**Status**: Active  
**Complexity**: 2 (Simple Enhancement)  
**Objective**: Implement simplified Memory Bank structure with bidirectional linking and validation tools

**Checklist**:
- [x] Create new directory structure
- [x] Create navigation README (<200 lines)
- [x] Create UI patterns file with DO/DON'T examples
- [x] Create machine-readable UI rules
- [x] Create validation tools
- [x] Archive unused files (moved 10+ files, ~8,000+ lines)
- [x] Test validation tools (all checks passing)
- [x] Create consolidated project context file
- [x] Create API patterns file (addresses common traps: single DB, prescribed connections, avoid unnecessary endpoints)
- [x] Create data patterns file (RLS patterns, migration-only changes, single database principle)
- [x] Create agent patterns file (CRUDTool abstraction, LangChain patterns, configuration-driven)
- [x] Create corresponding rule files (api-rules.json, data-rules.json, agent-rules.json)
- [ ] Add @docs headers to existing code files

### CRUD Tool Migration to DB Configuration
**Status**: In Progress  
**Complexity**: 2-3 (Simple to Moderate)  
**Objective**: Move all CRUD tool logic to `agent_tools` table config. Only generic `CRUDTool` class remains in code.

**Checklist**:
- [x] Migrate all LTM CRUD tools to DB config
- [x] Remove explicit CRUD tool subclasses from code
- [x] Update loader to instantiate tools from DB config
- [x] Test: Add new CRUD tool by DB insert only
- [ ] Document pattern in `tool-creation-pattern.md`
- [ ] Update onboarding docs

### ChatServer Main.py Decomposition - Phase 3
**Status**: Nearly Complete  
**Complexity**: 3 (Intermediate Feature)  
**Objective**: Extract business logic into service classes and background task management

**Checklist**:
- [x] Create services module structure
- [x] Extract background tasks into dedicated service
- [x] Create ChatService with comprehensive tests (17 tests)
- [x] Create PromptCustomizationService with tests (13 tests)
- [x] Update main.py to use service layer
- [x] Verify no regressions in functionality
- [ ] Update documentation

## Pending

### Session Management Integration Testing
**Status**: Pending  
**Complexity**: 2 (Simple Enhancement)  
**Objective**: Complete integration testing for new session management system

**Tasks**:
- [ ] Test session persistence across browser refreshes
- [ ] Test executor caching performance
- [ ] Test background task cleanup
- [ ] Fix any integration bugs found
- [ ] Performance testing with multiple concurrent sessions

### Agent Tool Loading Refactor
**Status**: To Do  
**Complexity**: 3-4 (Intermediate to Complex)  
**Objective**: Refactor `src/core/agent_loader.py` for cleaner tool loading system

**Tasks**:
- [ ] Analyze current tool loading architecture
- [ ] Design cleaner separation of concerns
- [ ] Implement extensible tool registration system
- [ ] Create comprehensive tests
- [ ] Update documentation

### Additional Agent Tools
**Status**: To Do  
**Complexity**: 2-3 (Simple to Moderate)  
**Objective**: Add web search, document reading, calendar interaction tools

**Tasks**:
- [ ] Implement web search tool
- [ ] Implement document reading tool
- [ ] Implement calendar interaction tool
- [ ] Create tests for new tools
- [ ] Update tool documentation

## Quick Reference

**File Locations**:
- Tasks: `memory-bank/active-tasks.md` (this file)
- Patterns: `memory-bank/patterns/`
- Rules: `memory-bank/rules/`
- Tools: `memory-bank/tools/`

**Validation**:
- Run: `node memory-bank/tools/link-checker.js`
- Check: File lengths, broken links, unused files

**Documentation Rules**:
- Keep this file under 200 lines
- Archive completed tasks to `memory-bank/archive/completed-tasks/`
- Link to relevant pattern files for implementation guidance 