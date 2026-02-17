import { useState, useCallback } from 'react';
import { useTaskViewStore } from '@/stores/useTaskViewStore';

export type ModalType = 'detail' | 'prioritize' | 'delete' | 'archive';

export interface ModalState {
  type: ModalType | null;
  taskId: string | null;
  isOpen: boolean;
}

export interface UseTaskModalManagementProps {
  /**
   * Whether to sync modal state with the global store
   * @default true
   */
  syncWithStore?: boolean;
}

export interface UseTaskModalManagementReturn {
  /**
   * Current modal state
   */
  modalState: ModalState;

  /**
   * Open a specific modal for a task
   */
  openModal: (type: ModalType, taskId: string) => void;

  /**
   * Close the current modal
   */
  closeModal: () => void;

  /**
   * Check if a specific modal type is open
   */
  isModalOpen: (type: ModalType) => boolean;

  /**
   * Check if a modal is open for a specific task
   */
  isModalOpenForTask: (taskId: string) => boolean;

  /**
   * Get the currently open task ID (if any)
   */
  currentTaskId: string | null;

  /**
   * Handle modal open/close changes (for Radix Dialog onOpenChange)
   */
  handleModalOpenChange: (isOpen: boolean) => void;

  /**
   * Convenience getters for specific modal types
   */
  detailModal: {
    isOpen: boolean;
    taskId: string | null;
    open: (taskId: string) => void;
    close: () => void;
  };

  prioritizeModal: {
    isOpen: boolean;
    taskId: string | null;
    open: (taskId: string) => void;
    close: () => void;
  };
}

/**
 * Custom hook for managing task modal state
 *
 * Features:
 * - Unified modal state management
 * - Eliminates dual state patterns
 * - Syncs with global store for keyboard shortcuts
 * - Type-safe modal operations
 * - Convenience methods for common modals
 *
 * @param props Configuration options
 * @returns Modal state and management functions
 */
export const useTaskModalManagement = ({
  syncWithStore = true,
}: UseTaskModalManagementProps = {}): UseTaskModalManagementReturn => {
  // Local modal state
  const [modalState, setModalState] = useState<ModalState>({
    type: null,
    taskId: null,
    isOpen: false,
  });

  // Store integration for keyboard shortcuts
  const setModalOpenState = useTaskViewStore((state) => state.setModalOpenState);

  // Open a modal
  const openModal = useCallback(
    (type: ModalType, taskId: string) => {
      const newState: ModalState = {
        type,
        taskId,
        isOpen: true,
      };

      setModalState(newState);

      // Sync with store if enabled - use a specific modal identifier
      if (syncWithStore) {
        const modalIdentifier = `${type}-${taskId}`;
        setModalOpenState(modalIdentifier, true);
      }
    },
    [syncWithStore, setModalOpenState],
  );

  // Close the current modal
  const closeModal = useCallback(() => {
    const currentTaskId = modalState.taskId;
    const currentType = modalState.type;

    setModalState({
      type: null,
      taskId: null,
      isOpen: false,
    });

    // Sync with store if enabled - use the same specific modal identifier
    if (syncWithStore && currentTaskId && currentType) {
      const modalIdentifier = `${currentType}-${currentTaskId}`;
      setModalOpenState(modalIdentifier, false);
    }
  }, [modalState.taskId, modalState.type, syncWithStore, setModalOpenState]);

  // Handle Radix Dialog onOpenChange
  const handleModalOpenChange = useCallback(
    (isOpen: boolean) => {
      if (!isOpen) {
        closeModal();
      }
    },
    [closeModal],
  );

  // Check if a specific modal type is open
  const isModalOpen = useCallback(
    (type: ModalType) => {
      return modalState.isOpen && modalState.type === type;
    },
    [modalState.isOpen, modalState.type],
  );

  // Check if a modal is open for a specific task
  const isModalOpenForTask = useCallback(
    (taskId: string) => {
      return modalState.isOpen && modalState.taskId === taskId;
    },
    [modalState.isOpen, modalState.taskId],
  );

  // Convenience getters
  const detailModal = {
    isOpen: isModalOpen('detail'),
    taskId: isModalOpen('detail') ? modalState.taskId : null,
    open: (taskId: string) => openModal('detail', taskId),
    close: closeModal,
  };

  const prioritizeModal = {
    isOpen: isModalOpen('prioritize'),
    taskId: isModalOpen('prioritize') ? modalState.taskId : null,
    open: (taskId: string) => openModal('prioritize', taskId),
    close: closeModal,
  };

  return {
    modalState,
    openModal,
    closeModal,
    isModalOpen,
    isModalOpenForTask,
    currentTaskId: modalState.taskId,
    handleModalOpenChange,
    detailModal,
    prioritizeModal,
  };
};
