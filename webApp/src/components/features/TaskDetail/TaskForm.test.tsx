import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, test, expect, beforeEach, afterEach, Mock } from 'vitest';
import TaskForm from './TaskForm';
import { useTaskStore, TaskStore } from '@/stores/useTaskStore';
import { useAuthStore, AuthState } from '@/features/auth/useAuthStore';
import { Task, TaskPriority, TaskStatus } from '@/api/types';
import { UseRadixFormReturn } from '@/hooks/useRadixForm';
import { TaskFormData } from '@/types/editableEntityTypes';
import type { AppError } from '@/types/error';

// --- Mock Hooks ---
vi.mock('@/hooks/useRadixForm');
vi.mock('@/stores/useTaskStore');
vi.mock('@/features/auth/useAuthStore');

import { useRadixForm } from '@/hooks/useRadixForm';

const mockHandleSave = vi.fn().mockResolvedValue(undefined);
const mockHandleCancel = vi.fn();
const mockHandleFieldChange = vi.fn();
const mockSetFormData = vi.fn();

const defaultFormData: TaskFormData = {
  title: '',
  description: null,
  status: 'pending' as TaskStatus,
  priority: 0 as TaskPriority,
  due_date: null,
};

let mockRadixFormReturn: UseRadixFormReturn<TaskFormData>;

const sampleTask: Task = {
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

type MockTaskStoreState = Partial<Pick<TaskStore, 'getTaskById' | 'createTask' | 'updateTask'> & { tasks: Task[] }>;
type MockAuthStoreState = Pick<AuthState, 'user'>;

describe('TaskForm', () => {
  const mockOnSaveSuccess = vi.fn();
  const mockOnCancel = vi.fn();
  const mockOnDirtyStateChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    mockRadixFormReturn = {
      formData: { ...defaultFormData },
      setFormData: mockSetFormData,
      isDirty: false,
      isSaving: false,
      isCreating: true,
      saveError: null,
      handleSave: mockHandleSave,
      handleCancel: mockHandleCancel,
      handleFieldChange: mockHandleFieldChange,
      formState: {
        canSave: false,
        isSaving: false,
        isCreating: true,
        saveError: null,
        handleSave: mockHandleSave,
        handleCancel: mockHandleCancel,
        isDirty: false,
      },
    };

    (useRadixForm as Mock).mockImplementation(({ onDirtyStateChange }) => {
      // Mirror the real hook: call onDirtyStateChange after every render when isDirty changes
      const prevRef = React.useRef<boolean | undefined>(undefined);
      React.useEffect(() => {
        if (prevRef.current !== mockRadixFormReturn.isDirty) {
          prevRef.current = mockRadixFormReturn.isDirty;
          onDirtyStateChange?.(mockRadixFormReturn.isDirty);
        }
      });
      return mockRadixFormReturn;
    });

    const taskStoreMock = useTaskStore as unknown as { getState: Mock };
    taskStoreMock.getState = vi.fn().mockReturnValue({
      getTaskById: vi.fn().mockImplementation((id: string) =>
        id === sampleTask.id ? sampleTask : undefined,
      ),
      createTask: vi.fn().mockResolvedValue({ ...sampleTask, id: 'new-task-id' } as Task),
      updateTask: vi.fn().mockResolvedValue(undefined as void),
      tasks: [],
    } as MockTaskStoreState);

    const authStoreMock = useAuthStore as unknown as { getState: Mock };
    authStoreMock.getState = vi.fn().mockReturnValue({
      user: { id: 'user-auth-1' } as AuthState['user'],
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
    // Status/Priority use Radix Select (no accessible label association in jsdom)
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Priority')).toBeInTheDocument();
    expect(screen.getByLabelText(/due date/i)).toBeInTheDocument();
  });

  test('renders correctly in edit mode', () => {
    mockRadixFormReturn.isCreating = false;
    mockRadixFormReturn.formData = {
      title: sampleTask.title,
      description: sampleTask.description ?? null,
      status: sampleTask.status,
      priority: sampleTask.priority,
      due_date: '2024-12-31',
    };
    renderTestForm({ taskId: sampleTask.id });
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
  });

  test('calls handleSave when form is submitted via external button', async () => {
    const user = userEvent.setup();
    renderTestForm();

    await user.type(screen.getByLabelText(/title/i), 'New Test Task Title');

    await waitFor(() => {
      expect(mockHandleFieldChange).toHaveBeenCalledWith('title', expect.stringContaining('N'));
    });
  });

  test('calls handleCancel when cancel is triggered', () => {
    renderTestForm();
    mockHandleCancel();
    expect(mockHandleCancel).toHaveBeenCalledOnce();
  });

  test('exposes correct saving state via onDirtyStateChange callback', async () => {
    mockRadixFormReturn.isSaving = true;
    mockRadixFormReturn.formState.isSaving = true;

    renderTestForm();

    // onDirtyStateChange is called on mount
    await waitFor(() => {
      expect(mockOnDirtyStateChange).toHaveBeenCalledWith(false);
    });
  });

  test('exposes correct canSave state via formState', async () => {
    mockRadixFormReturn.isDirty = true;
    mockRadixFormReturn.formState.canSave = true;
    mockRadixFormReturn.formState.isDirty = true;

    renderTestForm();

    await waitFor(() => {
      expect(mockOnDirtyStateChange).toHaveBeenCalledWith(true);
    });
  });

  test('displays save error message when saveError is present', () => {
    mockRadixFormReturn.saveError = { message: 'Network connection error' } satisfies AppError;
    renderTestForm();
    expect(screen.getByText(/save error: network connection error/i)).toBeInTheDocument();
  });

  test('calls onDirtyStateChange when isDirty changes', async () => {
    mockRadixFormReturn.isDirty = false;
    const { rerender } = renderTestForm();

    await waitFor(() => {
      expect(mockOnDirtyStateChange).toHaveBeenCalledWith(false);
    });
    mockOnDirtyStateChange.mockClear();

    // Simulate isDirty becoming true
    mockRadixFormReturn.isDirty = true;
    rerender(
      <TaskForm
        taskId={null}
        onSaveSuccess={mockOnSaveSuccess}
        onCancel={mockOnCancel}
        onDirtyStateChange={mockOnDirtyStateChange}
      />,
    );

    await waitFor(() => {
      expect(mockOnDirtyStateChange).toHaveBeenCalledWith(true);
    });
  });
});
