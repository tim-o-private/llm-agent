# Memory Bank Clarity Consolidation Plan

## Overview
Systematic review and consolidation of `memory-bank/clarity/` content into the streamlined Memory Bank structure.

## Content Analysis

### 📁 Root Files (10 files, ~60KB)
- `agent-core-instructions.md` (66 lines) - **EXTRACT**: Agent development guidelines
- `ui-guide.md` (87 lines) - **EXTRACT**: UI pattern index and rules  
- `api-data-guide.md` (94 lines) - **EXTRACT**: Backend development rules
- `implementationPatterns.md` (84 lines) - **ARCHIVE**: Mostly moved to references
- `prd.md` (112 lines) - **ARCHIVE**: Historical product requirements
- `progress.md` (134 lines) - **ARCHIVE**: Historical progress tracking
- `project-overview.md` (95 lines) - **EXTRACT**: Architecture overview
- `ddl.sql` (276 lines) - **EXTRACT**: Current schema reference
- `agent-ui-dev-instructions.md` (75 lines) - **EXTRACT**: UI development rules
- Plus: testing/, diagrams/, UI Mockups/ directories

### 📁 References/Patterns (15 files, ~150KB)
- `useEditableEntity-guide.md` (609 lines) - **REVIEW**: Complex hook, may be over-abstracted
- `tool-creation-pattern.md` (280 lines) - **EXTRACT**: Detailed CRUDTool patterns
- `reusable-ui-logic-hooks.md` (243 lines) - **EXTRACT**: UI hook patterns
- `local-first-state-management.md` (151 lines) - **REVIEW**: Complex state patterns
- `form-management.md` (114 lines) - **EXTRACT**: React Hook Form + Zod
- `ui-component-strategy.md` (68 lines) - **CHECK**: May contradict new patterns
- `monorepo-component-architecture.md` (80 lines) - **EXTRACT**: Architecture patterns
- Plus: 8 other pattern files

### 📁 References/Guides (6 files, ~40KB)
- `supabaseRLSGuide.md` (154 lines) - **EXTRACT**: Excellent RLS patterns
- `state-management-design.md` (264 lines) - **REVIEW**: Detailed state architecture
- `memory_system_v2.md` (135 lines) - **EXTRACT**: Memory architecture
- `keyboard-shortcut-guide.md` (70 lines) - **EXTRACT**: Implementation patterns
- `zustand-store-design.md` (83 lines) - **EXTRACT**: Store design guidelines

### 📁 References/Examples (3 files, ~30KB)
- `state-management-example.ts` (386 lines) - **REVIEW**: Complex implementation
- `state-management-component-example.tsx` (352 lines) - **REVIEW**: Complex example
- Plus: diagrams and SQL examples

## Consolidation Actions

### Phase 1: Extract Core Patterns
1. **UI Patterns** - Add to `patterns/ui-patterns.md`:
   - Form management (React Hook Form + Zod)
   - Keyboard shortcut implementation
   - UI hook patterns
   - Component architecture

2. **API Patterns** - Add to `patterns/api-patterns.md`:
   - FastAPI development guidelines
   - Error handling patterns
   - Authentication patterns

3. **Data Patterns** - Add to `patterns/data-patterns.md`:
   - RLS implementation guide
   - Schema management
   - Migration patterns

4. **Agent Patterns** - Add to `patterns/agent-patterns.md`:
   - Detailed CRUDTool configuration
   - Tool creation patterns
   - Memory system architecture

### Phase 2: Resolve Contradictions
1. **UI Component Strategy**: Check source code for actual Radix usage
2. **State Management**: Verify current React Query + Zustand approach
3. **Tool Patterns**: Ensure CRUDTool patterns match implementation

### Phase 3: Archive Legacy Content
1. **Historical files**: PRD, progress tracking, old overviews
2. **Over-complex patterns**: useEditableEntity, complex state examples
3. **Redundant guides**: Patterns already covered in new structure

### Phase 4: Update Navigation
1. Update `README.md` with consolidated patterns
2. Ensure bidirectional linking works
3. Run validation tools

## Success Criteria
- [ ] All valuable patterns extracted to streamlined files
- [ ] No contradictions between legacy and new patterns
- [ ] Legacy content properly archived
- [ ] File length limits maintained
- [ ] Validation tools pass
- [ ] Navigation updated

## Estimated Impact
- **Extract**: ~20 new patterns across 4 pattern files
- **Archive**: ~25 files, ~200KB of legacy content
- **Consolidate**: Single source of truth for all patterns 