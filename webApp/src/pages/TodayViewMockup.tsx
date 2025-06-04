import React, { useEffect, useCallback, useMemo, useRef, useState } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import clsx from 'clsx';

// Existing imports
import TaskListGroup from '@/components/tasks/TaskListGroup';
import { FastTaskInput } from '@/components/features/TodayView/FastTaskInput';
import { TaskDetailView } from '@/components/features/TaskDetail/TaskDetailView';
import { PrioritizeViewModal } from '@/components/features/PrioritizeView/PrioritizeViewModal';
import { ChatPanelV2 } from '@/components/ChatPanelV2';
import { NotesPane } from '@/components/features/NotesPane/NotesPane';
import { PlusIcon, ChatBubbleIcon, CalendarIcon, TargetIcon } from '@radix-ui/react-icons';
import { Button } from '@/components/ui/Button';

import { useTaskStore } from '@/stores/useTaskStore';
import { useTaskStoreInitializer } from '@/hooks/useTaskStoreInitializer';
import { useCreateFocusSession, useUpdateTaskOrder } from '@/api/hooks/useTaskHooks';
import { Spinner } from '@/components/ui';
import { toast } from '@/components/ui/toast';
import { useTaskViewStore } from '@/stores/useTaskViewStore';

// New types for the card system
type PaneType = 'tasks' | 'chat' | 'calendar' | 'focus' | 'notes';

interface StackedCardProps {
  pane: PaneType;
  isActive: boolean;
  isExiting: boolean;
  isPrimary: boolean;
  stackDepth: number;
  onSwitch: () => void;
  children: React.ReactNode;
}

interface StackedPaneProps {
  panes: PaneType[];
  activePane: PaneType;
  exitingPane: PaneType | null;
  isPrimary: boolean;
  onPaneSwitch: (pane: PaneType) => void;
  renderPaneContent: (pane: PaneType) => React.ReactNode;
}

// Animation hook for exit transitions
const useExitAnimation = (duration: number = 500) => {
  const [exitingItem, setExitingItem] = useState<PaneType | null>(null);
  
  const triggerExit = useCallback((item: PaneType, newItem: PaneType) => {
    if (item === newItem) return;
    
    setExitingItem(item);
    setTimeout(() => setExitingItem(null), duration);
  }, [duration]);
  
  return { exitingItem, triggerExit };
};

// Calculate stack depth for a pane
const calculateStackDepth = (pane: PaneType, activePane: PaneType, panes: PaneType[]): number => {
  const activePaneIndex = panes.indexOf(activePane);
  const paneIndex = panes.indexOf(pane);
  
  if (paneIndex === activePaneIndex) return 0;
  
  // Calculate the minimum distance considering wraparound
  const forwardDistance = (paneIndex - activePaneIndex + panes.length) % panes.length;
  const backwardDistance = (activePaneIndex - paneIndex + panes.length) % panes.length;
  
  return Math.min(forwardDistance, backwardDistance);
};

// Stacked Card Component
const StackedCard: React.FC<StackedCardProps> = ({
  isActive,
  isExiting,
  isPrimary,
  stackDepth,
  onSwitch,
  children
}) => {
  const transform = useMemo(() => {
    let horizontalOffset = 0;
    let verticalOffset = 0;
    
    if (isExiting) {
      horizontalOffset = isPrimary ? -300 : 300;
      verticalOffset = -100;
    } else if (stackDepth > 0) {
      horizontalOffset = isPrimary ? -stackDepth * 20 : stackDepth * 20;
      verticalOffset = stackDepth * 8;
    }
    
    const scale = isExiting ? 0.7 : 1 - stackDepth * 0.05;
    
    return `translateX(${horizontalOffset}px) translateY(${verticalOffset}px) translateZ(-${stackDepth * 10}px) scale(${scale})`;
  }, [isExiting, isPrimary, stackDepth]);

  return (
    <div
      className={clsx(
        'absolute transition-all duration-500 ease-out',
        // Positioning
        isActive && isPrimary && 'left-8 right-0 top-0 bottom-0',
        isActive && !isPrimary && 'left-0 right-8 top-0 bottom-0',
        (!isActive || isExiting) && 'left-0 right-0 top-0 bottom-0',
        // Opacity for exit animation - more dramatic
        isExiting && 'opacity-0',
        !isExiting && 'opacity-100'
      )}
      style={{
        transform,
        zIndex: isActive ? 10 : isExiting ? 20 : 10 - stackDepth,
        pointerEvents: isActive ? 'auto' : 'none'
      }}
      onClick={!isActive ? onSwitch : undefined}
    >
      <div className={clsx(
        'rounded-lg border h-full relative overflow-hidden',
        'transition-all duration-500 ease-out',
        // Active card - glassmorphic with transparency and blur
        stackDepth === 0 && 'backdrop-blur-glass bg-gradient-to-br from-ui-element-bg/85 via-ui-bg-glow/70 to-ui-element-bg/85 border-violet-300/40 text-text-primary shadow-glow',
        // Stacked cards - solid foundation cards
        stackDepth === 1 && 'bg-gradient-to-br from-ui-element-bg via-ui-bg-glow to-ui-element-bg border-ui-border text-text-primary shadow-md',
        stackDepth === 2 && 'bg-gradient-to-br from-ui-bg-alt via-ui-surface to-ui-bg-alt border-ui-border text-text-primary shadow-sm',
        // Hover effects for stacked cards
        !isActive && stackDepth <= 2 && 'hover:border-ui-border-focus cursor-pointer hover:shadow-glow hover:backdrop-blur-md'
              )}>
        {/* Card content */}
        {children}
      </div>
    </div>
  );
};

// Stacked Pane Container
const StackedPane: React.FC<StackedPaneProps> = ({
  panes,
  activePane,
  exitingPane,
  isPrimary,
  onPaneSwitch,
  renderPaneContent
}) => {
  const panesToRender = useMemo(() => {
    const result = [];
    
    // Add regular panes (active + stacked)
    panes.forEach((pane) => {
      const isActive = pane === activePane;
      
      if (isActive) {
        result.push({ pane, isActive: true, isExiting: false, stackDepth: 0 });
      } else {
        const stackDepth = calculateStackDepth(pane, activePane, panes);
        if (stackDepth <= 2) { // Limit to 2 stacked cards
          result.push({ pane, isActive: false, isExiting: false, stackDepth });
        }
      }
    });
    
    // Add exiting pane if different from current
    if (exitingPane && exitingPane !== activePane) {
      result.push({ pane: exitingPane, isActive: false, isExiting: true, stackDepth: 0 });
    }
    
    return result;
  }, [panes, activePane, exitingPane]);

  return (
    <div className="relative overflow-visible h-full" style={{ transformStyle: 'preserve-3d' }}>
      {panesToRender.map(({ pane, isActive, isExiting, stackDepth }) => (
        <StackedCard
          key={`${isPrimary ? 'primary' : 'secondary'}-${pane}-${isExiting ? 'exiting' : 'normal'}`}
          pane={pane}
          isActive={isActive}
          isExiting={isExiting}
          isPrimary={isPrimary}
          stackDepth={stackDepth}
          onSwitch={() => onPaneSwitch(pane)}
        >
          {renderPaneContent(pane)}
        </StackedCard>
      ))}
    </div>
  );
};

// Keyboard navigation hook
const useKeyboardNavigation = (
  panes: PaneType[],
  primaryPane: PaneType,
  secondaryPane: PaneType,
  focusedPane: 'primary' | 'secondary',
  onPrimarySwitch: (pane: PaneType) => void,
  onSecondarySwitch: (pane: PaneType) => void,
  onFocusSwitch: (focus: 'primary' | 'secondary') => void
) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Quick switch with Cmd/Ctrl + 1-4
      if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '4') {
        e.preventDefault();
        const paneIndex = parseInt(e.key) - 1;
        const targetPane = panes[paneIndex];
        if (targetPane) {
          if (focusedPane === 'primary') {
            onPrimarySwitch(targetPane);
          } else {
            onSecondarySwitch(targetPane);
          }
        }
      }
      
      // [ key - rotate left panel (primary) to next card
      if (e.key === '[') {
        e.preventDefault();
        const currentIndex = panes.indexOf(primaryPane);
        const nextIndex = currentIndex < panes.length - 1 ? currentIndex + 1 : 0;
        onPrimarySwitch(panes[nextIndex]);
      }
      
      // ] key - rotate right panel (secondary) to next card
      if (e.key === ']') {
        e.preventDefault();
        const currentIndex = panes.indexOf(secondaryPane);
        const nextIndex = currentIndex < panes.length - 1 ? currentIndex + 1 : 0;
        onSecondarySwitch(panes[nextIndex]);
      }
      
      // Tab to switch focus
      if (e.key === 'Tab' && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        onFocusSwitch(focusedPane === 'primary' ? 'secondary' : 'primary');
      }
      
      // Arrow keys to cycle
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        const currentPane = focusedPane === 'primary' ? primaryPane : secondaryPane;
        const currentIndex = panes.indexOf(currentPane);
        
        let nextIndex;
        if (e.key === 'ArrowRight') {
          nextIndex = currentIndex < panes.length - 1 ? currentIndex + 1 : 0;
        } else {
          nextIndex = currentIndex > 0 ? currentIndex - 1 : panes.length - 1;
        }
        
        const nextPane = panes[nextIndex];
        if (focusedPane === 'primary') {
          onPrimarySwitch(nextPane);
        } else {
          onSecondarySwitch(nextPane);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [panes, primaryPane, secondaryPane, focusedPane, onPrimarySwitch, onSecondarySwitch, onFocusSwitch]);
};

// Task-related keyboard shortcuts hook
const useTaskKeyboardShortcuts = (
  displayTasks: any[],
  focusedTaskId: string | null,
  setFocusedTaskId: (id: string | null) => void,
  setIsFastInputUiFocused: (focused: boolean) => void,
  openDetailModalForTask: (taskId: string) => void,
  currentDetailTaskId: string | null
) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeElement = document.activeElement;
      const isModalOpen = document.querySelector('[role="dialog"][data-state="open"]');
      const isInputActive = activeElement && (
        activeElement.tagName === 'INPUT' || 
        activeElement.tagName === 'TEXTAREA'
      );

      // If modal is open or input is active, don't process shortcuts
      if (isModalOpen || isInputActive) return;

      switch(e.key.toLowerCase()) {
        case 't':
          e.preventDefault();
          setIsFastInputUiFocused(true);
          break;
        case 'e':
          if (focusedTaskId && !currentDetailTaskId) { 
            e.preventDefault();
            openDetailModalForTask(focusedTaskId);
          } else if (displayTasks.length > 0 && !currentDetailTaskId && !focusedTaskId) {
            e.preventDefault();
            openDetailModalForTask(displayTasks[0].id);
          }
          break;
        case 'n':
          e.preventDefault();
          if (displayTasks.length > 0) {
            const currentIndex = displayTasks.findIndex(task => task.id === focusedTaskId);
            if (currentIndex === -1) {
              setFocusedTaskId(displayTasks[0].id);
            } else if (currentIndex < displayTasks.length - 1) {
              setFocusedTaskId(displayTasks[currentIndex + 1].id);
            }
          }
          break;
        case 'p':
          e.preventDefault();
          if (displayTasks.length > 0) {
            const currentIndex = displayTasks.findIndex(task => task.id === focusedTaskId);
            if (currentIndex === -1) {
              setFocusedTaskId(displayTasks[displayTasks.length - 1].id);
            } else if (currentIndex > 0) {
              setFocusedTaskId(displayTasks[currentIndex - 1].id);
            }
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [displayTasks, focusedTaskId, setFocusedTaskId, setIsFastInputUiFocused, openDetailModalForTask, currentDetailTaskId]);
};

// Main TodayView Mockup Component
const TodayViewMockup: React.FC = () => {
  // Existing TodayView logic (simplified for mockup)
  const { isLoading: isLoadingTasks, error: fetchError, initialized } = useTaskStoreInitializer();
  const {
    updateTask,
    deleteTask,
    getSubtasksByParentId,
  } = useTaskStore(state => ({
    updateTask: state.updateTask,
    deleteTask: state.deleteTask,
    getSubtasksByParentId: state.getSubtasksByParentId,
  }));
  
  const topLevelTasksFromStore = useTaskStore(state => state.getTopLevelTasks());
  const { mutate: createFocusSession } = useCreateFocusSession();
  const { mutate: updateTaskOrderMutation } = useUpdateTaskOrder();

  // Card system state
  const availablePanes: PaneType[] = ['tasks', 'chat', 'calendar', 'focus', 'notes'];
  const [primaryPane, setPrimaryPane] = useState<PaneType>('tasks');
  const [secondaryPane, setSecondaryPane] = useState<PaneType>('chat');
  const [focusedPane, setFocusedPane] = useState<'primary' | 'secondary'>('primary');
  
  // Exit animations
  const { exitingItem: exitingPrimaryPane, triggerExit: triggerPrimaryExit } = useExitAnimation();
  const { exitingItem: exitingSecondaryPane, triggerExit: triggerSecondaryExit } = useExitAnimation();

  // Existing TodayView state
  const [currentDetailTaskId, setCurrentDetailTaskId] = useState<string | null>(null);
  const [currentPrioritizeTaskId, setCurrentPrioritizeTaskId] = useState<string | null>(null);
  const [isFastInputUiFocused, setIsFastInputUiFocused] = useState(false);

  const focusedTaskId = useTaskViewStore(state => state.focusedTaskId);
  const setFocusedTaskId = useTaskViewStore(state => state.setFocusedTaskId);
  const selectedTaskIds = useTaskViewStore(state => state.selectedTaskIds);
  const toggleSelectedTask = useTaskViewStore(state => state.toggleSelectedTask);
  const removeSelectedTask = useTaskViewStore(state => state.removeSelectedTask);
  const setModalOpenState = useTaskViewStore(state => state.setModalOpenState);
  const setInputFocusState = useTaskViewStore(state => state.setInputFocusState);

  const fastInputRef = useRef<HTMLInputElement>(null);

  // Pane switching handlers
  const handlePrimarySwitch = useCallback((newPane: PaneType) => {
    triggerPrimaryExit(primaryPane, newPane);
    setPrimaryPane(newPane);
  }, [primaryPane, triggerPrimaryExit]);

  const handleSecondarySwitch = useCallback((newPane: PaneType) => {
    triggerSecondaryExit(secondaryPane, newPane);
    setSecondaryPane(newPane);
  }, [secondaryPane, triggerSecondaryExit]);

  // Keyboard navigation
  useKeyboardNavigation(
    availablePanes,
    primaryPane,
    secondaryPane,
    focusedPane,
    handlePrimarySwitch,
    handleSecondarySwitch,
    setFocusedPane
  );

  // Existing TodayView handlers (simplified)
  const handleTaskCreatedByFastInput = useCallback((taskId: string) => {
    setIsFastInputUiFocused(false);
    setInputFocusState(false);
    if (taskId) {
      setFocusedTaskId(taskId);
    }
  }, [setInputFocusState, setFocusedTaskId]);

  const handleMarkComplete = useCallback((taskId: string) => {
    updateTask(taskId, { completed: true, status: 'completed' });
    removeSelectedTask(taskId);
  }, [updateTask, removeSelectedTask]);

  const handleDeleteTask = useCallback((taskId: string) => {
    deleteTask(taskId);
    if (currentDetailTaskId === taskId) {
      setCurrentDetailTaskId(null);
      setModalOpenState(taskId, false); 
    }
    if (focusedTaskId === taskId) {
      setFocusedTaskId(null);
    }
    removeSelectedTask(taskId);
  }, [deleteTask, currentDetailTaskId, focusedTaskId, setFocusedTaskId, removeSelectedTask, setModalOpenState]);

  const openDetailModalForTask = useCallback((taskId: string) => {
    setCurrentDetailTaskId(taskId);
    setModalOpenState(taskId, true);
  }, [setModalOpenState]);

  const openPrioritizeModalForTask = useCallback((taskId: string) => {
    setCurrentPrioritizeTaskId(taskId);
    setModalOpenState(taskId, true);
  }, [setModalOpenState]);

  // Map tasks to view models (simplified)
  const displayTasksWithSubtasks = useMemo(() => {
    if (!initialized || !topLevelTasksFromStore || topLevelTasksFromStore.length === 0) return [];

    return topLevelTasksFromStore.map(task => {
      const subtasks = getSubtasksByParentId(task.id);
      return {
        ...task,
        onStartTask: () => console.log('Start task:', task.id),
        onEdit: () => openDetailModalForTask(task.id),
        isFocused: task.id === focusedTaskId,
        isSelected: selectedTaskIds.has(task.id),
        onSelectTask: () => toggleSelectedTask(task.id),
        onMarkComplete: () => handleMarkComplete(task.id),
        onDeleteTask: () => handleDeleteTask(task.id),
        onStartFocus: () => openPrioritizeModalForTask(task.id),
        subtasks,
      };
    });
  }, [
    initialized,
    topLevelTasksFromStore,
    getSubtasksByParentId,
    focusedTaskId,
    selectedTaskIds,
    openDetailModalForTask,
    toggleSelectedTask,
    handleMarkComplete,
    handleDeleteTask,
    openPrioritizeModalForTask
  ]);

  // Task keyboard shortcuts (after displayTasksWithSubtasks is defined)
  useTaskKeyboardShortcuts(
    displayTasksWithSubtasks,
    focusedTaskId,
    setFocusedTaskId,
    setIsFastInputUiFocused,
    openDetailModalForTask,
    currentDetailTaskId
  );

  // DND sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Render pane content
  const renderPaneContent = useCallback((pane: PaneType) => {
    switch (pane) {
      case 'tasks':
        return (
          <div className="flex flex-col h-full">
            {/* Header matching original TodayView */}
            <div className="flex justify-between items-center mb-6 px-6 pt-6">
              <div className="flex items-center space-x-2">
                <Button variant="outline" onClick={() => setIsFastInputUiFocused(true)}>
                  <PlusIcon className="mr-2 h-4 w-4" /> New Task
                </Button>
              </div>
            </div>
            
            {/* Fast Input */}
            <div className="mb-6 px-6">
              <FastTaskInput 
                ref={fastInputRef}
                isFocused={isFastInputUiFocused} 
                onTaskCreated={handleTaskCreatedByFastInput} 
                onBlurred={() => {
                  setIsFastInputUiFocused(false);
                  setInputFocusState(false);
                }}
                onFocused={() => setInputFocusState(true)}
              />
            </div>
            
            {/* Task List */}
            <div className="flex-1 overflow-y-auto px-6">
              {displayTasksWithSubtasks.length === 0 ? (
                <div className="flex-grow flex flex-col items-center justify-center text-text-muted">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                  </svg>
                  <p className="text-lg">Your day is clear!</p>
                  <p>Add some tasks to get started.</p>
                </div>
              ) : (
                <DndContext sensors={sensors} collisionDetection={closestCenter}>
                  <SortableContext items={displayTasksWithSubtasks.map(t => t.id)} strategy={verticalListSortingStrategy}>
                    <TaskListGroup tasks={displayTasksWithSubtasks} title="Today's Tasks" />
                  </SortableContext>
                </DndContext>
              )}
            </div>
          </div>
        );
        
      case 'chat':
        return (
          <div className="flex flex-col h-full">
            <div className="flex justify-between items-center mb-6 px-6 pt-6">
              <h2 className="text-2xl font-bold text-text-primary flex items-center">
                <ChatBubbleIcon className="mr-2 h-6 w-6" />
                AI Coach
              </h2>
            </div>
            <div className="flex-1 overflow-hidden px-6">
              <ChatPanelV2 agentId="assistant" />
            </div>
          </div>
        );
        
      case 'calendar':
        return (
          <div className="flex flex-col h-full">
            <div className="flex justify-between items-center mb-6 px-6 pt-6">
              <h2 className="text-2xl font-bold text-text-primary flex items-center">
                <CalendarIcon className="mr-2 h-6 w-6" />
                Calendar
              </h2>
            </div>
            <div className="flex-1 px-6 flex items-center justify-center text-text-muted">
              <div className="text-center">
                <CalendarIcon className="h-16 w-16 mb-4 opacity-50 mx-auto" />
                <p className="text-lg">Calendar View</p>
                <p>Coming soon...</p>
              </div>
            </div>
          </div>
        );
        
      case 'focus':
        return (
          <div className="flex flex-col h-full">
            <div className="flex justify-between items-center mb-6 px-6 pt-6">
              <h2 className="text-2xl font-bold text-text-primary flex items-center">
                <TargetIcon className="mr-2 h-6 w-6" />
                Focus Session
              </h2>
            </div>
            <div className="flex-1 px-6 flex items-center justify-center text-text-muted">
              <div className="text-center">
                <TargetIcon className="h-16 w-16 mb-4 opacity-50 mx-auto" />
                <p className="text-lg">Focus Mode</p>
                <p>Deep work session controls</p>
              </div>
            </div>
          </div>
        );
        
      case 'notes':
        return <NotesPane />;
        
      default:
        return <div className="p-6">Unknown pane: {pane}</div>;
    }
  }, [
    displayTasksWithSubtasks,
    isFastInputUiFocused,
    handleTaskCreatedByFastInput,
    setInputFocusState,
    sensors
  ]);

  if (isLoadingTasks) {
    return (
      <div className="flex justify-center items-center h-full">
        <Spinner size={32} /><p className="ml-2">Loading tasks...</p>
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="text-destructive p-4">
        Error loading tasks: {fetchError instanceof Error ? fetchError.message : String(fetchError)}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-ui-bg via-ui-bg-glow to-ui-bg">
      {/* Header matching original TodayView */}
      <div className="flex justify-between items-center mb-6 px-6 pt-6">
        <h1 className="text-3xl font-bold text-text-primary">Today</h1>
        
        {/* Pane indicators and controls */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-sm text-text-muted">
            <span className={clsx(
              'px-2 py-1 rounded-md',
              focusedPane === 'primary' ? 'bg-brand-primary/20 text-brand-primary' : 'bg-ui-surface/50'
            )}>
              Primary: {primaryPane}
            </span>
            <span className={clsx(
              'px-2 py-1 rounded-md',
              focusedPane === 'secondary' ? 'bg-brand-primary/20 text-brand-primary' : 'bg-ui-surface/50'
            )}>
              Secondary: {secondaryPane}
            </span>
          </div>
          
          {/* Quick switch buttons */}
          <div className="flex space-x-1">
            {availablePanes.map((pane, index) => (
              <Button
                key={pane}
                variant="outline"
                onClick={() => {
                  if (focusedPane === 'primary') {
                    handlePrimarySwitch(pane);
                  } else {
                    handleSecondarySwitch(pane);
                  }
                }}
                className="text-xs px-2 py-1"
              >
                ⌘{index + 1}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Split pane layout */}
      <div className="flex flex-1 overflow-hidden px-6">
        {/* Primary Pane (60%) */}
        <div 
          className={clsx(
            'relative transition-all duration-300',
            'w-3/5 pr-3', // 60% width with minimal padding
            focusedPane === 'primary' && 'ring-inset rounded-sm'
          )}
          onClick={() => setFocusedPane('primary')}
        >
          <StackedPane
            panes={availablePanes}
            activePane={primaryPane}
            exitingPane={exitingPrimaryPane}
            isPrimary={true}
            onPaneSwitch={handlePrimarySwitch}
            renderPaneContent={renderPaneContent}
          />
        </div>

        {/* Secondary Pane (40%) */}
        <div 
          className={clsx(
            'relative transition-all duration-300',
            'w-2/5 pl-3', // 40% width with minimal padding
            focusedPane === 'secondary' && 'ring-2 ring-brand-primary/30 ring-inset rounded-lg'
          )}
          onClick={() => setFocusedPane('secondary')}
        >
          <StackedPane
            panes={availablePanes}
            activePane={secondaryPane}
            exitingPane={exitingSecondaryPane}
            isPrimary={false}
            onPaneSwitch={handleSecondarySwitch}
            renderPaneContent={renderPaneContent}
          />
        </div>
      </div>

      {/* Keyboard shortcuts help */}
      <div className="absolute bottom-4 left-4 text-xs text-text-muted bg-ui-element-bg/90 rounded-lg p-3 border border-ui-border shadow-sm">
        <div className="space-y-1">
          <div><kbd className="px-1 py-0.5 bg-ui-bg-alt rounded text-xs">T</kbd> New task • <kbd className="px-1 py-0.5 bg-ui-bg-alt rounded text-xs">E</kbd> Edit • <kbd className="px-1 py-0.5 bg-ui-bg-alt rounded text-xs">N/P</kbd> Navigate tasks</div>
          <div><kbd className="px-1 py-0.5 bg-ui-bg-alt rounded text-xs">Tab</kbd> Switch focus • <kbd className="px-1 py-0.5 bg-ui-bg-alt rounded text-xs">⌘1-4</kbd> Quick switch • <kbd className="px-1 py-0.5 bg-ui-bg-alt rounded text-xs">←→</kbd> Cycle panes</div>
          <div><kbd className="px-1 py-0.5 bg-ui-bg-alt rounded text-xs">[</kbd> Rotate left panel • <kbd className="px-1 py-0.5 bg-ui-bg-alt rounded text-xs">]</kbd> Rotate right panel</div>
        </div>
      </div>

      {/* Existing modals */}
      {currentDetailTaskId && (
        <TaskDetailView
          taskId={currentDetailTaskId}
          isOpen={currentDetailTaskId !== null}
          onOpenChange={(isOpenFromDialog) => { 
            setModalOpenState(currentDetailTaskId, isOpenFromDialog);
            if (!isOpenFromDialog) {
              setCurrentDetailTaskId(null);
            }
          }}
          onTaskUpdated={() => {}} 
          onDeleteTaskFromDetail={handleDeleteTask}
        />
      )}

      {currentPrioritizeTaskId && (
        <PrioritizeViewModal
          taskId={currentPrioritizeTaskId}
          isOpen={currentPrioritizeTaskId !== null}
          onOpenChange={(isOpenFromDialog) => { 
            setModalOpenState(currentPrioritizeTaskId, isOpenFromDialog);
            if (!isOpenFromDialog) {
              setCurrentPrioritizeTaskId(null);
            }
          }}
          onStartFocusSession={(task) => {
            toast.success(`Task "${task.title}" ready for focus session.`);
            setModalOpenState(task.id, false);
            setCurrentPrioritizeTaskId(null);
          }}
        />
      )}
    </div>
  );
};

export default TodayViewMockup; 