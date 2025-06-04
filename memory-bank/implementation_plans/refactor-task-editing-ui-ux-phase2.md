# Implementation Plan: Task Editing UI - Phase 2 (Proper Separation of Concerns)

**Version:** 2.0
**Date:** 2025-01-26
**Status:** Proposed
**Context:** Phase 1 completed with basic functionality, but separation of concerns is insufficient

## 1. Problem Analysis

After completing Phase 1, we identified that `TaskDetailView.tsx` (234 lines) still violates separation of concerns:

- **Too Many Responsibilities**: Dialog management, form coordination, delete logic, UI layout, state management
- **Tight Coupling**: Form buttons rendered in TaskDetailView instead of TaskForm
- **Missing Abstractions**: No dedicated components for actions, delete handling, or modal wrapper
- **Complex State Management**: Multiple local state variables for coordination

## 2. Proposed Component Architecture

### 2.1. Component Hierarchy
```
TaskDetailView (Simplified - 50-80 lines)
├── TaskModalWrapper (New - Dialog logic)
│   ├── TaskForm (Form fields only)
│   ├── SubtaskList (Existing)
│   └── TaskActionBar (New - All actions: save/cancel/delete)
```

### 2.2. Responsibility Matrix

| Component | Responsibilities |
|-----------|-----------------|
| **TaskDetailView** | Props coordination, component composition |
| **TaskModalWrapper** | Dialog state, open/close logic, dirty state warnings |
| **TaskForm** | Form state, validation, form fields UI (no buttons) |
| **TaskActionBar** | All actions: save/cancel/delete, form state coordination |
| **SubtaskList** | Subtask display, add/edit subtasks |

## 3. Detailed Refactoring Plan

### 3.1. Create TaskModalWrapper Component

**File:** `webApp/src/components/features/TaskDetail/TaskModalWrapper.tsx`

**Responsibilities:**
- Radix Dialog setup and configuration
- Modal open/close state management
- Dirty state warning ("unsaved changes")
- Modal registration with TaskViewStore
- Loading and error state display

**Props:**
```typescript
interface TaskModalWrapperProps {
  taskId: string | null;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
}
```

### 3.2. Create TaskActionBar Component

**File:** `webApp/src/components/features/TaskDetail/TaskActionBar.tsx`

**Responsibilities:**
- Unified action bar with save/cancel/delete buttons
- Form state coordination (get form state from TaskForm)
- Delete confirmation dialog
- Subtask cascade deletion logic
- Action success/error handling

**Props:**
```typescript
interface TaskActionBarProps {
  taskId: string | null;
  formState: {
    canSave: boolean;
    isSaving: boolean;
    isCreating: boolean;
    saveError: any;
    handleSave: () => void;
    handleCancel: () => void;
  } | null;
  onSaveSuccess?: () => void;
  onCancel?: () => void;
  onDeleteSuccess?: () => void;
}
```

**Layout:**
```
[Cancel] [Save/Create Task] ... [Delete Task]
```

**Design Pattern:**
- **Left side**: Cancel (secondary action)
- **Center-left**: Save/Create (primary action) 
- **Right side**: Delete (destructive action, only for existing tasks)
- **Spacing**: Use `justify-between` or similar to separate primary from destructive actions
- **Visual hierarchy**: Primary button prominent, secondary muted, destructive red/danger styling

### 3.3. Simplify TaskForm Component

**Current Issues:**
- Action buttons are rendered in TaskDetailView
- Complex form state exposure

**Simplifications:**
- Remove action buttons (moved to TaskActionBar)
- Focus purely on form fields and validation
- Expose form state via callback for TaskActionBar

**Updated Props:**
```typescript
interface TaskFormProps {
  taskId: string | null | undefined;
  parentTaskId?: string | null;
  onSaveSuccess?: (savedTask: Task | void) => void;
  onCancel?: () => void;
  onDirtyStateChange?: (isDirty: boolean) => void;
  onFormStateChange?: (state: FormState) => void; // For TaskActionBar
}
```

### 3.4. Simplify TaskDetailView

**Target:** Reduce from 234 lines to 50-80 lines

**New Responsibilities:**
- Props coordination between components
- Component composition and layout
- High-level event handling (save success, delete success)

**Simplified Structure:**
```typescript
export const TaskDetailView: React.FC<TaskDetailViewProps> = ({
  taskId,
  isOpen,
  onOpenChange,
  onTaskUpdated,
  onDeleteTaskFromDetail,
}) => {
  const [formState, setFormState] = useState(null);

  const handleSaveSuccess = (savedTask?: Task | void) => {
    toast.success(`Task saved successfully!`);
    onTaskUpdated();
    onOpenChange(false);
  };

  const handleDeleteSuccess = () => {
    onDeleteTaskFromDetail?.(taskId!);
    onOpenChange(false);
  };

  const handleCancel = () => {
    onOpenChange(false);
  };

  return (
    <TaskModalWrapper
      taskId={taskId}
      isOpen={isOpen}
      onOpenChange={onOpenChange}
    >
      <div className="space-y-4">
        <TaskForm
          taskId={taskId}
          onSaveSuccess={handleSaveSuccess}
          onCancel={handleCancel}
          onFormStateChange={setFormState}
        />
        
        {taskId && (
          <SubtaskList parentTaskId={taskId} />
        )}
        
        <TaskActionBar
          taskId={taskId}
          formState={formState}
          onSaveSuccess={handleSaveSuccess}
          onCancel={handleCancel}
          onDeleteSuccess={handleDeleteSuccess}
        />
      </div>
    </TaskModalWrapper>
  );
};
```

## 4. Implementation Steps

### Step 1: Create TaskModalWrapper
- Extract dialog logic from TaskDetailView
- Handle dirty state warnings
- Manage modal registration

### Step 2: Create TaskActionBar
- Create unified action bar component
- Extract delete logic from TaskDetailView
- Coordinate with TaskForm for save/cancel actions
- Handle delete confirmation and subtask cascade

### Step 3: Simplify TaskForm
- Remove action buttons (moved to TaskActionBar)
- Focus on form fields and validation only
- Expose form state via callback

### Step 4: Refactor TaskDetailView
- Remove extracted logic
- Simplify to composition and coordination
- Reduce line count to 50-80 lines

### Step 5: Update Tests
- Update existing tests for new component structure
- Add tests for new components

## 5. Benefits of This Refactoring

### 5.1. Single Responsibility Principle
- Each component has one clear purpose
- Easier to understand and maintain
- Better testability

### 5.2. Improved Reusability
- TaskModalWrapper can be reused for other entity modals
- TaskDeleteSection can be adapted for other entities
- TaskForm is more self-contained

### 5.3. Better Encapsulation
- Form logic stays within TaskForm
- Delete logic is isolated
- Modal logic is centralized

### 5.4. Easier Testing
- Smaller, focused components
- Clear input/output boundaries
- Isolated concerns

## 6. Success Criteria

- [ ] TaskDetailView reduced to 50-80 lines
- [ ] Each component has single, clear responsibility
- [ ] All action buttons unified in TaskActionBar
- [ ] Delete logic isolated in TaskActionBar
- [ ] Modal logic centralized in TaskModalWrapper
- [ ] All existing functionality preserved
- [ ] Tests updated and passing
- [ ] No regression in user experience

## 7. Risk Mitigation

- **Breaking Changes**: Maintain existing props interface for TaskDetailView
- **State Management**: Careful handling of state flow between components
- **Testing**: Comprehensive testing of new component interactions
- **Rollback Plan**: Keep original implementation until new version is fully tested 