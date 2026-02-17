# Memory Bank Simplification Plan

## Problem Statement
Agents continue to reinvent functionality and patterns because:
- Critical information is scattered across multiple files
- Documentation contains outdated/completed tasks
- No clear schema maps project structure to relevant memory files
- Complex navigation requires reading multiple files to understand basic patterns

## Goals
1. **Remove outdated information** - Archive completed tasks, remove obsolete patterns
2. **Ensure accuracy and succinctness** - Consolidate overlapping content, keep files <500 lines
3. **Create machine-readable rules** - Distill to actionable patterns agents can follow
4. **Map to project structure** - Clear schema showing which memory files are relevant for which parts of the codebase
5. **Bidirectional linking** - Code files link to docs, docs link back to code
6. **Automated validation** - Linters check for broken links and enforce documentation standards

## Proposed New Structure

```
memory-bank/
├── README.md                    # Navigation guide for agents (<200 lines)
├── project-context.md           # Consolidated project overview (<300 lines)
├── active-tasks.md              # Current tasks only (<200 lines)
├── patterns/                    # All implementation patterns
│   ├── ui-patterns.md          # Frontend patterns (<400 lines)
│   ├── api-patterns.md         # Backend patterns (<400 lines)
│   ├── data-patterns.md        # Database/RLS patterns (<300 lines)
│   └── agent-patterns.md       # Agent tool patterns (<300 lines)
├── rules/                       # Machine-readable rules by area
│   ├── ui-rules.json           # UI development rules
│   ├── api-rules.json          # API development rules
│   ├── data-rules.json         # Database rules
│   └── agent-rules.json        # Agent development rules
├── schemas/                     # Current schemas and types
│   ├── database-schema.sql     # Current DDL (replaces ddl.sql)
│   ├── api-types.ts           # API type definitions
│   └── ui-types.ts            # UI component types
├── tools/                       # Automation and validation
│   ├── link-checker.js         # Validates bidirectional links
│   ├── doc-linter.js          # Enforces documentation standards
│   └── unused-file-detector.js # Flags unused files for deletion
└── archive/                     # Historical information
    ├── completed-tasks/        # Archived completed tasks
    ├── deprecated-patterns/    # Old patterns for reference
    ├── chat-history/          # Historical conversations
    └── unused-files/          # Files flagged for deletion
```

## Key Improvements

### 1. File Length Limits
- **README.md**: <200 lines (navigation only)
- **Pattern files**: <400 lines each (examples over explanations)
- **Active tasks**: <200 lines (current tasks only)
- **Project context**: <300 lines (essential info only)

### 2. Bidirectional Linking System
**Code files get doc headers:**
```tsx
/**
 * @docs memory-bank/patterns/ui-patterns.md#pattern-2-state-management
 * @rules memory-bank/rules/ui-rules.json#ui-003,ui-004
 * @examples memory-bank/patterns/ui-patterns.md#react-query-for-api-state
 */
import { useTaskHooks } from '@/api/hooks/useTaskHooks';
```

**Doc files link back to code:**
```markdown
## Pattern 2: State Management
**Implementation**: [`useTaskHooks.ts`](../webApp/src/api/hooks/useTaskHooks.ts)
**Examples**: [`TaskList.tsx`](../webApp/src/components/features/tasks/TaskList.tsx)
```

### 3. Automated Validation Tools
- **Link checker**: Validates all @docs, @rules, @examples references
- **Doc linter**: Enforces file length limits, required sections
- **Unused file detector**: Flags files not referenced anywhere

### 4. Few-Shot Prompt Approach
Replace explanations with examples:

```markdown
// ❌ OLD: "Use React Query hooks for API interactions because..."
// ✅ NEW: Show 3 examples of correct usage, 2 examples of what to avoid
```

## Implementation Steps

### Phase 1: Create Structure & Tools
1. Create new directory structure
2. Build link checker and doc linter tools
3. Create file length monitoring
4. Identify unused files for deletion

### Phase 2: Consolidate with Examples
1. Extract patterns as few-shot examples
2. Add bidirectional links to existing code
3. Create machine-readable rules
4. Archive completed tasks

### Phase 3: Validation & Cleanup
1. Run link checker on all files
2. Enforce file length limits
3. Delete unused files
4. Test with sample agent queries

### Phase 4: Automation
1. Add pre-commit hooks for link validation
2. CI/CD checks for documentation standards
3. Automated unused file detection
4. Documentation coverage reports

## Bidirectional Linking Schema

### Code File Headers
```tsx
/**
 * @docs memory-bank/patterns/ui-patterns.md#pattern-name
 * @rules memory-bank/rules/ui-rules.json#rule-id
 * @examples memory-bank/patterns/ui-patterns.md#section-name
 * @related webApp/src/components/ui/Button.tsx
 */
```

### Documentation Links
```markdown
**Files**: [`Component.tsx`](../path/to/Component.tsx) [`Hook.ts`](../path/to/Hook.ts)
**Rules**: [ui-001](rules/ui-rules.json#ui-001) [ui-002](rules/ui-rules.json#ui-002)
**Related**: [API Pattern](api-patterns.md#related-pattern)
```

## Unused Files to Flag for Deletion

Based on initial analysis, these files appear unused:
- `memory-bank/chatGPTConvo.md` - Historical conversation
- `memory-bank/keyboard_nav_audit.md` - Completed audit
- `memory-bank/webAppImportStrategy.md` - Superseded by patterns
- `memory-bank/clarity/chatHistory` - Historical conversation
- `memory-bank/clarity/creative-*.md` - Completed creative phases
- Files in `memory-bank/implementation_plans/` - Completed plans
- Files in `memory-bank/summaries/` - Historical summaries

## Validation Rules

### File Length Enforcement
```javascript
// doc-linter.js rules
const FILE_LIMITS = {
  'README.md': 200,
  'patterns/*.md': 400,
  'active-tasks.md': 200,
  'project-context.md': 300
};
```

### Link Validation
```javascript
// link-checker.js rules
const REQUIRED_HEADERS = {
  '*.tsx': ['@docs', '@rules'],
  '*.ts': ['@docs'],
  'patterns/*.md': ['**Files**', '**Rules**']
};
```

### Documentation Coverage
- Every `.tsx` file must have `@docs` header
- Every pattern must link to implementation files
- Every rule must have examples in pattern files
- No broken links allowed in CI/CD

## Success Metrics

- Agents find patterns in <2 file reads (measured)
- No broken links in documentation (automated)
- File length limits enforced (automated)
- Zero unused files in repo (automated)
- Documentation coverage >90% (measured)

## Next Steps

1. **Get approval** for this enhanced structure
2. **Build validation tools** before content migration
3. **Implement bidirectional linking** in sample files
4. **Test automation** with existing codebase
5. **Begin content consolidation** with length limits 