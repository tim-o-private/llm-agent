import { useEffect, useRef } from 'react';
import { useTaskViewStore } from '@/stores/useTaskViewStore';

export interface NavigableTask {
  id: string;
}

export interface KeyboardNavigationConfig {
  /**
   * Whether keyboard navigation is enabled for this page
   * @default true
   */
  enabled?: boolean;
  
  /**
   * Whether to auto-focus the first task when tasks are available
   * @default true
   */
  autoFocusFirst?: boolean;
  
  /**
   * Whether to clear focus when no tasks are available
   * @default true
   */
  clearFocusOnEmpty?: boolean;
}

export interface UseTaskKeyboardNavigationProps {
  /**
   * Array of tasks that can be navigated with keyboard
   */
  tasks: NavigableTask[];
  
  /**
   * Whether the fast input is currently focused (prevents auto-focus of tasks)
   */
  isInputFocused?: boolean;
  
  /**
   * Configuration options
   */
  config?: KeyboardNavigationConfig;
}

export interface UseTaskKeyboardNavigationReturn {
  /**
   * ID of the currently focused task
   */
  focusedTaskId: string | null;
  
  /**
   * Set the focused task ID
   */
  setFocusedTaskId: (taskId: string | null) => void;
  
  /**
   * Initialize keyboard listeners (call in useEffect)
   */
  initializeKeyboardListeners: () => void;
  
  /**
   * Cleanup keyboard listeners (call in useEffect cleanup)
   */
  destroyKeyboardListeners: () => void;
  
  /**
   * Handle request to open detail modal (from keyboard shortcut)
   */
  requestOpenDetailForTaskId: string | null;
  
  /**
   * Clear the detail open request
   */
  clearDetailOpenRequest: () => void;
  
  /**
   * Handle request to focus fast input (from keyboard shortcut)
   */
  requestFocusFastInput: boolean;
  
  /**
   * Clear the fast input focus request
   */
  clearFocusFastInputRequest: () => void;
}

/**
 * Custom hook for managing keyboard navigation in task lists
 * 
 * Features:
 * - Arrow keys / j/k for navigation
 * - Enter/e to open task details
 * - Space to toggle selection
 * - a/t to focus fast input
 * - Escape to clear focus/selection
 * 
 * @param props Configuration and task data
 * @returns Navigation state and handlers
 */
export const useTaskKeyboardNavigation = ({
  tasks,
  isInputFocused = false,
  config = {}
}: UseTaskKeyboardNavigationProps): UseTaskKeyboardNavigationReturn => {
  const {
    enabled = true,
    autoFocusFirst = true,
    clearFocusOnEmpty = true
  } = config;

  // Store selectors
  const focusedTaskId = useTaskViewStore(state => state.focusedTaskId);
  const setFocusedTaskId = useTaskViewStore(state => state.setFocusedTaskId);
  const setCurrentNavigableTasks = useTaskViewStore(state => state.setCurrentNavigableTasks);
  const requestOpenDetailForTaskId = useTaskViewStore(state => state.requestOpenDetailForTaskId);
  const clearDetailOpenRequest = useTaskViewStore(state => state.clearDetailOpenRequest);
  const requestFocusFastInput = useTaskViewStore(state => state.requestFocusFastInput);
  const clearFocusFastInputRequest = useTaskViewStore(state => state.clearFocusFastInputRequest);
  const initializeListener = useTaskViewStore(state => state.initializeListener);
  const destroyListener = useTaskViewStore(state => state.destroyListener);

  // Track if we've initialized listeners to prevent double initialization
  const listenersInitialized = useRef(false);

  // Update navigable tasks in store when tasks change
  useEffect(() => {
    if (enabled) {
      setCurrentNavigableTasks(tasks);
    }
  }, [tasks, setCurrentNavigableTasks, enabled]);

  // Auto-focus first task when tasks become available
  useEffect(() => {
    if (!enabled || !autoFocusFirst) return;
    
    // Only auto-focus if there's truly no focused task AND we're not in the middle of a modal operation
    // This prevents the auto-focus from overriding manual focus restoration after modal closes
    if (!focusedTaskId && tasks.length > 0 && !isInputFocused) {
      // Add a small delay to allow any pending focus restoration to complete first
      const timeoutId = setTimeout(() => {
        // Double-check that focus is still null after the delay and system is not busy
        const currentState = useTaskViewStore.getState();
        if (!currentState.focusedTaskId && tasks.length > 0 && !currentState.isSystemBusy) {
          setFocusedTaskId(tasks[0].id);
        }
      }, 10);
      
      return () => clearTimeout(timeoutId);
    }
  }, [tasks.length, focusedTaskId, isInputFocused, setFocusedTaskId, enabled, autoFocusFirst]);

  // Clear focus when no tasks available
  useEffect(() => {
    if (!enabled || !clearFocusOnEmpty) return;
    
    if (focusedTaskId && tasks.length === 0) {
      setFocusedTaskId(null);
    }
  }, [tasks.length, focusedTaskId, setFocusedTaskId, enabled, clearFocusOnEmpty]);

  // Initialize/destroy keyboard listeners
  const initializeKeyboardListeners = () => {
    if (enabled && !listenersInitialized.current) {
      initializeListener();
      listenersInitialized.current = true;
    }
  };

  const destroyKeyboardListeners = () => {
    if (listenersInitialized.current) {
      destroyListener();
      listenersInitialized.current = false;
    }
  };

  return {
    focusedTaskId,
    setFocusedTaskId,
    initializeKeyboardListeners,
    destroyKeyboardListeners,
    requestOpenDetailForTaskId,
    clearDetailOpenRequest,
    requestFocusFastInput,
    clearFocusFastInputRequest,
  };
}; 