import React from 'react';
import { useOverlayStore } from '../../stores/useOverlayStore';

// Import overlay components
const AddTaskTray = React.lazy(() => import('../tasks/AddTaskTray'));

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
        // AddTaskTray handles both quick add and task detail modes
        return <AddTaskTray {...commonOverlayProps} />;
      // Add cases for other OverlayTypes here
      // case 'settingsModal':
      //   return <SettingsModal {...commonProps} />;
      default:
        console.warn(`OverlayManager: No component registered for overlay type: ${type}`);
        return null;
    }
  };

  return <React.Suspense fallback={<OverlayLoadingFallback />}>{renderOverlay()}</React.Suspense>;
};
