import { useCallback } from 'react';
import { useThemeStore, getEffectiveAppearance, ThemeAppearance } from '../stores/useThemeStore';

export type EffectiveTheme = 'light' | 'dark';

export function useTheme(): [EffectiveTheme, (theme: ThemeAppearance) => void, () => void] {
  const storeSetAppearance = useThemeStore((state) => state.setAppearance);
  const storeToggleAppearance = useThemeStore((state) => state.toggleAppearance);
  const storedAppearance = useThemeStore((state) => state.appearance);

  const effectiveTheme = getEffectiveAppearance(storedAppearance);

  // The setTheme function from the hook can now accept 'light', 'dark', or 'system'
  const setTheme = useCallback(
    (newAppearance: ThemeAppearance) => {
      storeSetAppearance(newAppearance);
    },
    [storeSetAppearance]
  );

  // The toggleTheme function will use the store's toggle logic (light/dark)
  const toggleTheme = useCallback(() => {
    storeToggleAppearance();
  }, [storeToggleAppearance]);

  return [effectiveTheme, setTheme, toggleTheme];
} 