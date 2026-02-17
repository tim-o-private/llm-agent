import create from 'zustand';
import { persist } from 'zustand/middleware';

export type ThemeAppearance = 'light' | 'dark' | 'system';

interface ThemeState {
  appearance: ThemeAppearance;
  setAppearance: (appearance: ThemeAppearance) => void;
  toggleAppearance: () => void; // Simple toggle between light/dark for now
}

const THEME_STORAGE_KEY = 'clarity-theme-appearance';

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      appearance: 'light', // Default appearance
      setAppearance: (appearance) => set({ appearance }),
      toggleAppearance: () => {
        const currentAppearance = get().appearance;
        // Simple toggle: if dark, go light, otherwise go dark.
        // Ignores 'system' for this simple toggle for now.
        const newAppearance = currentAppearance === 'dark' ? 'light' : 'dark';
        set({ appearance: newAppearance });
      },
    }),
    {
      name: THEME_STORAGE_KEY,
      onRehydrateStorage: () => (state) => {
        // Optional: you can do something when state is rehydrated
        if (state) {
          // If 'system' is stored, try to determine system preference on load
          // For simplicity, we'll default to 'light' if 'system' is encountered during rehydration for now.
          // A more complete solution would check matchMedia.
          if (state.appearance === 'system') {
            // This is a placeholder for more complex system theme detection logic
            const systemPrefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            state.appearance = systemPrefersDark ? 'dark' : 'light';
          }
        }
      },
    },
  ),
);

// Helper to get the effective appearance considering 'system' setting
export function getEffectiveAppearance(storedAppearance: ThemeAppearance): 'light' | 'dark' {
  if (storedAppearance === 'system') {
    if (typeof window !== 'undefined') {
      return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'light'; // Default for SSR or non-browser environments
  }
  return storedAppearance;
}
