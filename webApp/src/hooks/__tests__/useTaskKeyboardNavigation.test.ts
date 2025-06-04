import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useTaskKeyboardNavigation, NavigableTask } from '../useTaskKeyboardNavigation';
import { useTaskViewStore } from '@/stores/useTaskViewStore';

// Mock the store
vi.mock('@/stores/useTaskViewStore');

const mockUseTaskViewStore = useTaskViewStore as any;

describe('useTaskKeyboardNavigation', () => {
  // Mock store state and actions
  const mockStoreState = {
    focusedTaskId: null as string | null,
    setFocusedTaskId: vi.fn(),
    setCurrentNavigableTasks: vi.fn(),
    requestOpenDetailForTaskId: null as string | null,
    clearDetailOpenRequest: vi.fn(),
    requestFocusFastInput: false,
    clearFocusFastInputRequest: vi.fn(),
    initializeListener: vi.fn(),
    destroyListener: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock the store selector to return different values based on the property being accessed
    mockUseTaskViewStore.mockImplementation((selector: any) => {
      return selector(mockStoreState);
    });
  });

  const sampleTasks: NavigableTask[] = [
    { id: 'task-1' },
    { id: 'task-2' },
    { id: 'task-3' },
  ];

  describe('Basic functionality', () => {
    it('should initialize with default configuration', () => {
      const { result } = renderHook(() =>
        useTaskKeyboardNavigation({ tasks: sampleTasks })
      );

      expect(result.current.focusedTaskId).toBe(null);
      expect(result.current.setFocusedTaskId).toBe(mockStoreState.setFocusedTaskId);
      expect(result.current.requestOpenDetailForTaskId).toBe(null);
      expect(result.current.requestFocusFastInput).toBe(false);
    });

    it('should update navigable tasks in store when tasks change', () => {
      const { rerender } = renderHook(
        ({ tasks }) => useTaskKeyboardNavigation({ tasks }),
        { initialProps: { tasks: sampleTasks } }
      );

      expect(mockStoreState.setCurrentNavigableTasks).toHaveBeenCalledWith(sampleTasks);

      const newTasks = [{ id: 'task-4' }, { id: 'task-5' }];
      rerender({ tasks: newTasks });

      expect(mockStoreState.setCurrentNavigableTasks).toHaveBeenCalledWith(newTasks);
    });
  });

  describe('Auto-focus behavior', () => {
    it('should auto-focus first task when tasks become available', () => {
      // Start with no focused task and no input focused
      mockStoreState.focusedTaskId = null;
      
      renderHook(() =>
        useTaskKeyboardNavigation({ 
          tasks: sampleTasks, 
          isInputFocused: false 
        })
      );

      expect(mockStoreState.setFocusedTaskId).toHaveBeenCalledWith('task-1');
    });

    it('should not auto-focus when input is focused', () => {
      mockStoreState.focusedTaskId = null;
      
      renderHook(() =>
        useTaskKeyboardNavigation({ 
          tasks: sampleTasks, 
          isInputFocused: true 
        })
      );

      expect(mockStoreState.setFocusedTaskId).not.toHaveBeenCalled();
    });

    it('should not auto-focus when already focused on a task', () => {
      mockStoreState.focusedTaskId = 'task-2';
      
      renderHook(() =>
        useTaskKeyboardNavigation({ 
          tasks: sampleTasks, 
          isInputFocused: false 
        })
      );

      expect(mockStoreState.setFocusedTaskId).not.toHaveBeenCalled();
    });

    it('should not auto-focus when disabled in config', () => {
      mockStoreState.focusedTaskId = null;
      
      renderHook(() =>
        useTaskKeyboardNavigation({ 
          tasks: sampleTasks, 
          isInputFocused: false,
          config: { autoFocusFirst: false }
        })
      );

      expect(mockStoreState.setFocusedTaskId).not.toHaveBeenCalled();
    });
  });

  describe('Clear focus behavior', () => {
    it('should clear focus when no tasks available', () => {
      mockStoreState.focusedTaskId = 'task-1';
      
      const { rerender } = renderHook(
        ({ tasks }) => useTaskKeyboardNavigation({ tasks }),
        { initialProps: { tasks: sampleTasks } }
      );

      // Change to empty tasks array
      rerender({ tasks: [] });

      expect(mockStoreState.setFocusedTaskId).toHaveBeenCalledWith(null);
    });

    it('should not clear focus when disabled in config', () => {
      mockStoreState.focusedTaskId = 'task-1';
      
      const { rerender } = renderHook(
        ({ tasks }) => useTaskKeyboardNavigation({ 
          tasks, 
          config: { clearFocusOnEmpty: false } 
        }),
        { initialProps: { tasks: sampleTasks } }
      );

      rerender({ tasks: [] });

      expect(mockStoreState.setFocusedTaskId).not.toHaveBeenCalledWith(null);
    });
  });

  describe('Keyboard listener management', () => {
    it('should provide initialize and destroy functions', () => {
      const { result } = renderHook(() =>
        useTaskKeyboardNavigation({ tasks: sampleTasks })
      );

      expect(typeof result.current.initializeKeyboardListeners).toBe('function');
      expect(typeof result.current.destroyKeyboardListeners).toBe('function');
    });

    it('should initialize listeners when called', () => {
      const { result } = renderHook(() =>
        useTaskKeyboardNavigation({ tasks: sampleTasks })
      );

      act(() => {
        result.current.initializeKeyboardListeners();
      });

      expect(mockStoreState.initializeListener).toHaveBeenCalled();
    });

    it('should destroy listeners when called', () => {
      const { result } = renderHook(() =>
        useTaskKeyboardNavigation({ tasks: sampleTasks })
      );

      // Initialize first
      act(() => {
        result.current.initializeKeyboardListeners();
      });

      // Then destroy
      act(() => {
        result.current.destroyKeyboardListeners();
      });

      expect(mockStoreState.destroyListener).toHaveBeenCalled();
    });

    it('should not double-initialize listeners', () => {
      const { result } = renderHook(() =>
        useTaskKeyboardNavigation({ tasks: sampleTasks })
      );

      act(() => {
        result.current.initializeKeyboardListeners();
        result.current.initializeKeyboardListeners(); // Call twice
      });

      expect(mockStoreState.initializeListener).toHaveBeenCalledTimes(1);
    });
  });

  describe('Configuration options', () => {
    it('should respect enabled: false configuration', () => {
      mockStoreState.focusedTaskId = null;
      
      renderHook(() =>
        useTaskKeyboardNavigation({ 
          tasks: sampleTasks,
          config: { enabled: false }
        })
      );

      // Should not set navigable tasks or auto-focus when disabled
      expect(mockStoreState.setCurrentNavigableTasks).not.toHaveBeenCalled();
      expect(mockStoreState.setFocusedTaskId).not.toHaveBeenCalled();
    });

    it('should not initialize listeners when disabled', () => {
      const { result } = renderHook(() =>
        useTaskKeyboardNavigation({ 
          tasks: sampleTasks,
          config: { enabled: false }
        })
      );

      act(() => {
        result.current.initializeKeyboardListeners();
      });

      expect(mockStoreState.initializeListener).not.toHaveBeenCalled();
    });
  });

  describe('Store integration', () => {
    it('should expose store request states', () => {
      mockStoreState.requestOpenDetailForTaskId = 'task-1';
      mockStoreState.requestFocusFastInput = true;

      const { result } = renderHook(() =>
        useTaskKeyboardNavigation({ tasks: sampleTasks })
      );

      expect(result.current.requestOpenDetailForTaskId).toBe('task-1');
      expect(result.current.requestFocusFastInput).toBe(true);
    });

    it('should expose store clear functions', () => {
      const { result } = renderHook(() =>
        useTaskKeyboardNavigation({ tasks: sampleTasks })
      );

      expect(result.current.clearDetailOpenRequest).toBe(mockStoreState.clearDetailOpenRequest);
      expect(result.current.clearFocusFastInputRequest).toBe(mockStoreState.clearFocusFastInputRequest);
    });
  });
}); 