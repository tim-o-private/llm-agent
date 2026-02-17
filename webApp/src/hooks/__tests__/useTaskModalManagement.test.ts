import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useTaskModalManagement } from '../useTaskModalManagement';
import { useTaskViewStore } from '@/stores/useTaskViewStore';

// Mock the store
vi.mock('@/stores/useTaskViewStore');

const mockUseTaskViewStore = useTaskViewStore as any;

describe('useTaskModalManagement', () => {
  // Mock store state and actions
  const mockStoreState = {
    setModalOpenState: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock the store selector
    mockUseTaskViewStore.mockImplementation((selector: any) => {
      return selector(mockStoreState);
    });
  });

  describe('Basic functionality', () => {
    it('should initialize with no modal open', () => {
      const { result } = renderHook(() => useTaskModalManagement());

      expect(result.current.modalState).toEqual({
        type: null,
        taskId: null,
        isOpen: false,
      });
      expect(result.current.currentTaskId).toBe(null);
      expect(result.current.detailModal.isOpen).toBe(false);
      expect(result.current.prioritizeModal.isOpen).toBe(false);
    });

    it('should provide all expected functions', () => {
      const { result } = renderHook(() => useTaskModalManagement());

      expect(typeof result.current.openModal).toBe('function');
      expect(typeof result.current.closeModal).toBe('function');
      expect(typeof result.current.isModalOpen).toBe('function');
      expect(typeof result.current.isModalOpenForTask).toBe('function');
      expect(typeof result.current.handleModalOpenChange).toBe('function');
    });
  });

  describe('Opening modals', () => {
    it('should open detail modal correctly', () => {
      const { result } = renderHook(() => useTaskModalManagement());

      act(() => {
        result.current.openModal('detail', 'task-1');
      });

      expect(result.current.modalState).toEqual({
        type: 'detail',
        taskId: 'task-1',
        isOpen: true,
      });
      expect(result.current.currentTaskId).toBe('task-1');
      expect(result.current.detailModal.isOpen).toBe(true);
      expect(result.current.detailModal.taskId).toBe('task-1');
      expect(result.current.prioritizeModal.isOpen).toBe(false);
    });

    it('should open prioritize modal correctly', () => {
      const { result } = renderHook(() => useTaskModalManagement());

      act(() => {
        result.current.openModal('prioritize', 'task-2');
      });

      expect(result.current.modalState).toEqual({
        type: 'prioritize',
        taskId: 'task-2',
        isOpen: true,
      });
      expect(result.current.prioritizeModal.isOpen).toBe(true);
      expect(result.current.prioritizeModal.taskId).toBe('task-2');
      expect(result.current.detailModal.isOpen).toBe(false);
    });

    it('should sync with store when opening modal', () => {
      const { result } = renderHook(() => useTaskModalManagement());

      act(() => {
        result.current.openModal('detail', 'task-1');
      });

      expect(mockStoreState.setModalOpenState).toHaveBeenCalledWith('task-1', true);
    });

    it('should not sync with store when syncWithStore is false', () => {
      const { result } = renderHook(() => useTaskModalManagement({ syncWithStore: false }));

      act(() => {
        result.current.openModal('detail', 'task-1');
      });

      expect(mockStoreState.setModalOpenState).not.toHaveBeenCalled();
    });
  });

  describe('Closing modals', () => {
    it('should close modal correctly', () => {
      const { result } = renderHook(() => useTaskModalManagement());

      // First open a modal
      act(() => {
        result.current.openModal('detail', 'task-1');
      });

      // Then close it
      act(() => {
        result.current.closeModal();
      });

      expect(result.current.modalState).toEqual({
        type: null,
        taskId: null,
        isOpen: false,
      });
      expect(result.current.currentTaskId).toBe(null);
      expect(result.current.detailModal.isOpen).toBe(false);
      expect(result.current.prioritizeModal.isOpen).toBe(false);
    });

    it('should sync with store when closing modal', () => {
      const { result } = renderHook(() => useTaskModalManagement());

      // Open modal first
      act(() => {
        result.current.openModal('detail', 'task-1');
      });

      // Clear previous calls
      vi.clearAllMocks();

      // Close modal
      act(() => {
        result.current.closeModal();
      });

      expect(mockStoreState.setModalOpenState).toHaveBeenCalledWith('task-1', false);
    });

    it('should handle onOpenChange correctly', () => {
      const { result } = renderHook(() => useTaskModalManagement());

      // Open modal first
      act(() => {
        result.current.openModal('detail', 'task-1');
      });

      // Simulate Radix Dialog onOpenChange(false)
      act(() => {
        result.current.handleModalOpenChange(false);
      });

      expect(result.current.modalState.isOpen).toBe(false);
    });

    it('should not close modal when onOpenChange(true) is called', () => {
      const { result } = renderHook(() => useTaskModalManagement());

      // Open modal first
      act(() => {
        result.current.openModal('detail', 'task-1');
      });

      // Simulate Radix Dialog onOpenChange(true) - should not close
      act(() => {
        result.current.handleModalOpenChange(true);
      });

      expect(result.current.modalState.isOpen).toBe(true);
    });
  });

  describe('Modal state queries', () => {
    it('should correctly identify open modal types', () => {
      const { result } = renderHook(() => useTaskModalManagement());

      act(() => {
        result.current.openModal('detail', 'task-1');
      });

      expect(result.current.isModalOpen('detail')).toBe(true);
      expect(result.current.isModalOpen('prioritize')).toBe(false);
      expect(result.current.isModalOpen('delete')).toBe(false);
    });

    it('should correctly identify modals open for specific tasks', () => {
      const { result } = renderHook(() => useTaskModalManagement());

      act(() => {
        result.current.openModal('detail', 'task-1');
      });

      expect(result.current.isModalOpenForTask('task-1')).toBe(true);
      expect(result.current.isModalOpenForTask('task-2')).toBe(false);
    });
  });

  describe('Convenience methods', () => {
    it('should provide working detail modal convenience methods', () => {
      const { result } = renderHook(() => useTaskModalManagement());

      // Open via convenience method
      act(() => {
        result.current.detailModal.open('task-1');
      });

      expect(result.current.detailModal.isOpen).toBe(true);
      expect(result.current.detailModal.taskId).toBe('task-1');

      // Close via convenience method
      act(() => {
        result.current.detailModal.close();
      });

      expect(result.current.detailModal.isOpen).toBe(false);
      expect(result.current.detailModal.taskId).toBe(null);
    });

    it('should provide working prioritize modal convenience methods', () => {
      const { result } = renderHook(() => useTaskModalManagement());

      // Open via convenience method
      act(() => {
        result.current.prioritizeModal.open('task-2');
      });

      expect(result.current.prioritizeModal.isOpen).toBe(true);
      expect(result.current.prioritizeModal.taskId).toBe('task-2');

      // Close via convenience method
      act(() => {
        result.current.prioritizeModal.close();
      });

      expect(result.current.prioritizeModal.isOpen).toBe(false);
      expect(result.current.prioritizeModal.taskId).toBe(null);
    });
  });

  describe('Modal switching', () => {
    it('should handle switching between different modal types', () => {
      const { result } = renderHook(() => useTaskModalManagement());

      // Open detail modal
      act(() => {
        result.current.openModal('detail', 'task-1');
      });

      expect(result.current.detailModal.isOpen).toBe(true);
      expect(result.current.prioritizeModal.isOpen).toBe(false);

      // Switch to prioritize modal
      act(() => {
        result.current.openModal('prioritize', 'task-1');
      });

      expect(result.current.detailModal.isOpen).toBe(false);
      expect(result.current.prioritizeModal.isOpen).toBe(true);
      expect(result.current.modalState.type).toBe('prioritize');
    });

    it('should handle opening modal for different task', () => {
      const { result } = renderHook(() => useTaskModalManagement());

      // Open modal for task-1
      act(() => {
        result.current.openModal('detail', 'task-1');
      });

      expect(result.current.currentTaskId).toBe('task-1');

      // Open modal for task-2
      act(() => {
        result.current.openModal('detail', 'task-2');
      });

      expect(result.current.currentTaskId).toBe('task-2');
      expect(result.current.detailModal.taskId).toBe('task-2');
    });
  });
});
