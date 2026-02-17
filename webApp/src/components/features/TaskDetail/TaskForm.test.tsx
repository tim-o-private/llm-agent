import React from 'react';
import { render, screen, waitFor, act as rtlAct } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, test, expect, beforeEach, afterEach, Mock, Mocked } from 'vitest';
import TaskForm from './TaskForm';
import { useEditableEntity } from '@/hooks/useEditableEntity';
import { useTaskStore, TaskStore } from '@/stores/useTaskStore';
import { useAuthStore, AuthState } from '@/features/auth/useAuthStore';
import { Task, TaskPriority, TaskStatus } from '@/api/types';
import { UseEditableEntityReturn, TaskFormData } from '@/types/editableEntityTypes';
import { UseFormReturn, FormState, Control } from 'react-hook-form';

// --- Mock Hooks ---
vi.mock('@/hooks/useEditableEntity');
vi.mock('@/stores/useTaskStore');
vi.mock('@/features/auth/useAuthStore');

// --- RHF Mock Setup ---
const mockRHFRegister = vi.fn();
const mockRHFHandleSubmit = vi.fn((cb) => (e?: React.BaseSyntheticEvent) => {
  e?.preventDefault();
  return cb({});
});
let mockRHFFormState: FormState<TaskFormData>;
const mockRHFReset = vi.fn();
const mockRHFGetValues = vi.fn();
const mockRHFSetValue = vi.fn();
const mockRHFWatch = vi.fn();
const mockRHFTrigger = vi.fn();
const mockRHFClearErrors = vi.fn();
const mockRHFSetError = vi.fn();
const mockRHFGetFieldState = vi.fn();

const mockFormMethods = {
  register: mockRHFRegister,
  handleSubmit: mockRHFHandleSubmit,
  formState: {} as FormState<TaskFormData>,
  reset: mockRHFReset,
  getValues: mockRHFGetValues,
  setValue: mockRHFSetValue,
  watch: mockRHFWatch,
  trigger: mockRHFTrigger,
  clearErrors: mockRHFClearErrors,
  setError: mockRHFSetError,
  getFieldState: mockRHFGetFieldState,
  control: {} as Control<TaskFormData>,
} as unknown as UseFormReturn<TaskFormData>;
// --- End RHF Mock Setup ---

let mockUseEditableEntityReturnValue: UseEditableEntityReturn<Task, TaskFormData>;

const sampleTaskForForm: Task = {
  id: 'task-edit-1',
  user_id: 'user-auth-1',
  title: 'Existing Task Title',
  description: 'Existing task description',
  status: 'in_progress' as TaskStatus,
  priority: 1 as TaskPriority,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  due_date: '2024-12-31T00:00:00.000Z',
  completed_at: null,
  deleted: false,
  parent_task_id: null,
  completed: false,
};

const sampleTaskFormDataForForm: TaskFormData = {
  title: sampleTaskForForm.title,
  description: sampleTaskForForm.description ?? null,
  status: sampleTaskForForm.status,
  priority: sampleTaskForForm.priority,
  due_date: '2024-12-31',
};

// Use the actual imported store state types for mocks
type MockTaskStoreState = Partial<Pick<TaskStore, 'getTaskById' | 'createTask' | 'updateTask'> & { tasks: Task[] }>;
type MockAuthStoreState = Pick<AuthState, 'user'>; // Only pick what is used in the mock

describe('TaskForm', () => {
  const mockOnSaveSuccess = vi.fn();
  const mockOnCancel = vi.fn();
  const mockOnDirtyStateChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    mockRHFFormState = {
      errors: {},
      isDirty: false,
      isValid: true,
      isLoading: false,
      isSubmitted: false,
      isSubmitSuccessful: false,
      isSubmitting: false,
      isValidating: false,
      touchedFields: {},
      dirtyFields: {},
      submitCount: 0,
      disabled: false,
      defaultValues: undefined,
      validatingFields: {},
      isReady: true,
    };
    mockFormMethods.formState = mockRHFFormState;
    mockRHFRegister.mockImplementation((name) => ({ name, onChange: vi.fn(), onBlur: vi.fn(), ref: vi.fn() }));
    mockRHFGetValues.mockReturnValue(sampleTaskFormDataForForm);

    mockUseEditableEntityReturnValue = {
      formMethods: mockFormMethods,
      isSaving: false,
      saveError: null,
      canSave: true,
      handleSave: vi.fn(),
      resetFormToInitial: vi.fn(),
      initialData: undefined,
      isCreating: true,
      initialDataError: null,
    };
    (useEditableEntity as Mock).mockReturnValue(mockUseEditableEntityReturnValue);

    const taskStoreMock = useTaskStore as unknown as Mocked<typeof useTaskStore>;
    taskStoreMock.getState = vi.fn().mockReturnValue({
      getTaskById: vi
        .fn()
        .mockImplementation((id: string) => (id === sampleTaskForForm.id ? sampleTaskForForm : undefined)),
      createTask: vi.fn().mockResolvedValue({ ...sampleTaskForForm, id: 'new-task-id' } as Task),
      updateTask: vi.fn().mockResolvedValue(undefined as void),
      tasks: [], // Added to satisfy MockTaskStoreState if not all parts are optional
    } as MockTaskStoreState);

    const authStoreMock = useAuthStore as unknown as Mocked<typeof useAuthStore>;
    // Make sure the mock provides all non-optional fields of AuthState required by MockAuthStoreState
    // If `user` can be null in AuthState, MockAuthStoreState should reflect that or provide a default.
    authStoreMock.getState = vi.fn().mockReturnValue({
      user: { id: 'user-auth-1' } as AuthState['user'], // Cast to User or User | null depending on AuthState
    } as MockAuthStoreState);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderTestForm = (props: Partial<React.ComponentProps<typeof TaskForm>> = {}) => {
    const defaultProps: React.ComponentProps<typeof TaskForm> = {
      taskId: null,
      onSaveSuccess: mockOnSaveSuccess,
      onCancel: mockOnCancel,
      onDirtyStateChange: mockOnDirtyStateChange,
      ...props,
    };
    return render(<TaskForm {...defaultProps} />);
  };

  test('renders correctly in create mode', () => {
    renderTestForm({ taskId: null });
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/status/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/priority/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/due date/i)).toBeInTheDocument();
    // Buttons are no longer in TaskForm - they're in TaskDetailView
  });

  test('renders correctly in edit mode', () => {
    (useEditableEntity as Mock).mockReturnValue({
      ...mockUseEditableEntityReturnValue,
      isCreating: false,
      initialData: sampleTaskForForm,
    });
    renderTestForm({ taskId: sampleTaskForForm.id });
    // Form fields should be present, buttons are handled externally
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
  });

  test('calls handleSave when form is submitted via external button', async () => {
    const user = userEvent.setup();
    let capturedFormState: any = null;

    renderTestForm({
      onFormStateChange: (state) => {
        capturedFormState = state;
      },
    });

    await user.type(screen.getByLabelText(/title/i), 'New Test Task Title');

    // Wait for form state to be captured
    await waitFor(() => {
      expect(capturedFormState).toBeTruthy();
      expect(capturedFormState.canSave).toBe(true);
    });

    // Simulate external button click
    capturedFormState.handleSave();

    await waitFor(() => {
      expect(mockUseEditableEntityReturnValue.handleSave).toHaveBeenCalledOnce();
    });
  });

  test('calls resetFormToInitial and onCancel when external cancel is triggered', async () => {
    let capturedFormState: any = null;

    renderTestForm({
      onFormStateChange: (state) => {
        capturedFormState = state;
      },
    });

    // Wait for form state to be captured
    await waitFor(() => {
      expect(capturedFormState).toBeTruthy();
    });

    // Simulate external cancel button click
    capturedFormState.handleCancel();

    expect(mockUseEditableEntityReturnValue.resetFormToInitial).toHaveBeenCalledOnce();
    expect(mockOnCancel).toHaveBeenCalledOnce();
  });

  test('exposes correct saving state via form state callback', async () => {
    let capturedFormState: any = null;

    (useEditableEntity as Mock).mockReturnValue({
      ...mockUseEditableEntityReturnValue,
      isSaving: true,
    });

    renderTestForm({
      onFormStateChange: (state) => {
        capturedFormState = state;
      },
    });

    await waitFor(() => {
      expect(capturedFormState).toBeTruthy();
      expect(capturedFormState.isSaving).toBe(true);
    });
  });

  test('exposes correct canSave state via form state callback', async () => {
    let capturedFormState: any = null;

    (useEditableEntity as Mock).mockReturnValue({
      ...mockUseEditableEntityReturnValue,
      canSave: false,
    });

    renderTestForm({
      onFormStateChange: (state) => {
        capturedFormState = state;
      },
    });

    await waitFor(() => {
      expect(capturedFormState).toBeTruthy();
      expect(capturedFormState.canSave).toBe(false);
    });
  });

  test('displays save error message when saveError is present', () => {
    (useEditableEntity as Mock).mockReturnValue({
      ...mockUseEditableEntityReturnValue,
      saveError: new Error('Network connection error'),
    });
    renderTestForm();
    expect(screen.getByText(/save error: network connection error/i)).toBeInTheDocument();
  });

  test('calls onDirtyStateChange when RHF formState.isDirty changes', () => {
    const { rerender } = renderTestForm();
    expect(mockOnDirtyStateChange).toHaveBeenCalledWith(false);
    mockOnDirtyStateChange.mockClear();

    rtlAct(() => {
      mockRHFFormState.isDirty = true;
    });
    rerender(
      <TaskForm
        taskId={null}
        onSaveSuccess={mockOnSaveSuccess}
        onCancel={mockOnCancel}
        onDirtyStateChange={mockOnDirtyStateChange}
      />,
    );
    expect(mockOnDirtyStateChange).toHaveBeenCalledWith(true);
    mockOnDirtyStateChange.mockClear();
    rtlAct(() => {
      mockRHFFormState.isDirty = false;
    });
    rerender(
      <TaskForm
        taskId={null}
        onSaveSuccess={mockOnSaveSuccess}
        onCancel={mockOnCancel}
        onDirtyStateChange={mockOnDirtyStateChange}
      />,
    );
    expect(mockOnDirtyStateChange).toHaveBeenCalledWith(false);
  });
});
