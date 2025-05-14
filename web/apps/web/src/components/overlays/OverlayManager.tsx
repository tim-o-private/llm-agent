import React from 'react';
import { useOverlayStore, OverlayType } from '../../stores/useOverlayStore';

// Import your overlay components here
// Example: import QuickAddTray from '../tasks/QuickAddTray';
// Example: import TaskDetailTray from '../tasks/TaskDetailTray';

// TODO: Lazily load overlay components for better performance if they are heavy
const AddTaskTray = React.lazy(() => import('../tasks/AddTaskTray'));
// We'll use AddTaskTray for both 'quickAddTray' and 'taskDetailTray' for now as an example.
// In a real scenario, TaskDetailTray would be a different component or AddTaskTray would handle different modes.

// Placeholder for TaskDetailTray if it's distinct and needed
// const TaskDetailTray = React.lazy(() => import('../tasks/TaskDetailTray'));

// A simple loading fallback for lazy components
const OverlayLoadingFallback = () => (
  <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
    {/* You might want a spinner here */}
    <p className="text-white">Loading overlay...</p>
  </div>
);

export const OverlayManager: React.FC = () => {
  const { activeOverlay, closeOverlay } = useOverlayStore();

  if (!activeOverlay) {
    return null;
  }

  const renderOverlay = () => {
    const { type, data } = activeOverlay;
    // Common props passed to all overlays managed by OverlayManager
    const commonOverlayProps = {
      isOpen: true, // The overlay component should be visible if rendered by manager
      onClose: closeOverlay, // Standard way to signal closing
      ...(data || {}), // Pass any additional data from the store
    };

    switch (type) {
      case 'quickAddTray':
        // AddTaskTray now handles its own submission via useCreateTask hook
        return <AddTaskTray {...commonOverlayProps} />;
      case 'taskDetailTray':
        // If AddTaskTray is reused for task details, it would need to inspect `data` 
        // (e.g., data.taskId) to switch to an edit mode and use useUpdateTask.
        // For now, just rendering it like quickAddTray.
        // A dedicated TaskDetailTray component would be cleaner.
        console.log('Opening taskDetailTray with data:', data);
        // Example: return <TaskDetailTray {...commonOverlayProps} />; 
        // Using AddTaskTray for now, it won't use the data for editing yet.
        return <AddTaskTray {...commonOverlayProps} />;
      // Add cases for other OverlayTypes here
      // case 'settingsModal':
      //   return <SettingsModal {...commonProps} />;
      default:
        console.warn(`OverlayManager: No component registered for overlay type: ${type}`);
        return null;
    }
  };

  return (
    <React.Suspense fallback={<OverlayLoadingFallback />}>
      {renderOverlay()}
    </React.Suspense>
  );
}; 