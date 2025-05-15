import { create } from 'zustand';

// Define the possible types of overlays you'll have.
// Add to this union type as new overlays are created.
export type OverlayType = 
  | 'quickAddTray' 
  | 'taskDetailTray'
  // Add other overlay types here, e.g.:
  // | 'settingsModal'
  // | 'confirmationDialog'
  ;

interface ActiveOverlay {
  type: OverlayType;
  data?: any; // Optional data to pass to the overlay component
}

interface OverlayStore {
  activeOverlay: ActiveOverlay | null;
  openOverlay: (type: OverlayType, data?: any) => void;
  closeOverlay: () => void;
}

export const useOverlayStore = create<OverlayStore>((set) => ({
  activeOverlay: null, // No overlay is active initially
  openOverlay: (type, data) => set(() => ({ activeOverlay: { type, data } })),
  closeOverlay: () => set(() => ({ activeOverlay: null })),
})); 