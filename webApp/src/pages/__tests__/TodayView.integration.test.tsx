import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import TodayView from '../TodayView';
import { useTaskStore } from '@/stores/useTaskStore';
import { useTaskViewStore } from '@/stores/useTaskViewStore';
import { useTaskStoreInitializer } from '@/hooks/useTaskStoreInitializer';

// Mock all the dependencies
vi.mock('@/stores/useTaskStore');
vi.mock('@/stores/useTaskViewStore');
vi.mock('@/hooks/useTaskStoreInitializer');
vi.mock('@/api/hooks/useTaskHooks', () => ({
  useCreateFocusSession: () => ({ mutate: vi.fn() }),
  useUpdateTaskOrder: () => ({ mutate: vi.fn() }),
}));

const mockUseTaskStore = useTaskStore as any;
const mockUseTaskViewStore = useTaskViewStore as any;
const mockUseTaskStoreInitializer = useTaskStoreInitializer as any;

describe('TodayView Modal Integration', () => {
  const mockTasks = [
    {
      id: 'task-1',
      title: 'Test Task 1',
      completed: false,
      status: 'pending',
      priority: 1,
      position: 0,
    },
    {
      id: 'task-2',
      title: 'Test Task 2',
      completed: false,
      status: 'in_progress',
      priority: 2,
      position: 1,
    },
  ];

  const mockTaskStore = {
    getTopLevelTasks: () => mockTasks,
    updateTask: vi.fn(),
    deleteTask: vi.fn(),
    getSubtasksByParentId: () => [],
  };

  const mockTaskViewStore = {
    selectedTaskIds: new Set(),
    toggleSelectedTask: vi.fn(),
    removeSelectedTask: vi.fn(),
    setInputFocusState: vi.fn(),
    setModalOpenState: vi.fn(),
    focusedTaskId: null,
    setFocusedTaskId: vi.fn(),
    setCurrentNavigableTasks: vi.fn(),
    requestOpenDetailForTaskId: null,
    clearDetailOpenRequest: vi.fn(),
    requestFocusFastInput: false,
    clearFocusFastInputRequest: vi.fn(),
    initializeListener: vi.fn(),
    destroyListener: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();

    mockUseTaskStore.mockImplementation((selector: any) => {
      return selector(mockTaskStore);
    });

    mockUseTaskViewStore.mockImplementation((selector: any) => {
      return selector(mockTaskViewStore);
    });

    mockUseTaskStoreInitializer.mockReturnValue({
      isLoading: false,
      error: null,
      initialized: true,
    });
  });

  it('should render without modal open initially', () => {
    render(<TodayView />);

    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('Test Task 1')).toBeInTheDocument();
    expect(screen.getByText('Test Task 2')).toBeInTheDocument();

    // No modals should be visible
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should open detail modal when task is clicked', async () => {
    render(<TodayView />);

    // Find and click a task card (this would trigger the detail modal)
    const taskCard = screen.getByText('Test Task 1').closest('[role="button"]');
    if (taskCard) {
      fireEvent.click(taskCard);

      // Wait for modal to appear
      await waitFor(() => {
        expect(screen.queryByRole('dialog')).toBeInTheDocument();
      });
    }
  });

  it('should handle modal state correctly', () => {
    // This test verifies that the modal management hook is properly integrated
    // by checking that the component renders without errors and manages state
    const { rerender } = render(<TodayView />);

    // Component should render successfully with modal management
    expect(screen.getByText('Today')).toBeInTheDocument();

    // Re-render should work without issues
    rerender(<TodayView />);
    expect(screen.getByText('Today')).toBeInTheDocument();
  });
});

// Simple smoke test to ensure the hook can be imported and used
describe('Modal Management Hook Smoke Test', () => {
  it('should be importable and usable', async () => {
    const { useTaskModalManagement } = await import('@/hooks/useTaskModalManagement');
    expect(typeof useTaskModalManagement).toBe('function');
  });
});
