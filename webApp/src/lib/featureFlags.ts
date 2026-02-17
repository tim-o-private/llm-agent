// Feature flags for assistant-ui migration
export interface FeatureFlags {
  useAssistantUI: boolean;
  enableStreamingChat: boolean;
  enableToolVisualization: boolean;
  enableMessageActions: boolean;
  enableAdvancedAccessibility: boolean;
}

// Default feature flags - can be overridden by environment variables or user preferences
const defaultFlags: FeatureFlags = {
  useAssistantUI: true, // Enable assistant-ui by default
  enableStreamingChat: false,
  enableToolVisualization: false,
  enableMessageActions: false,
  enableAdvancedAccessibility: true, // Always enable accessibility
};

// Environment variable overrides
const envFlags: Partial<FeatureFlags> = {
  useAssistantUI: import.meta.env.VITE_USE_ASSISTANT_UI === 'true',
  enableStreamingChat: import.meta.env.VITE_ENABLE_STREAMING_CHAT === 'true',
  enableToolVisualization: import.meta.env.VITE_ENABLE_TOOL_VISUALIZATION === 'true',
  enableMessageActions: import.meta.env.VITE_ENABLE_MESSAGE_ACTIONS === 'true',
  enableAdvancedAccessibility: import.meta.env.VITE_ENABLE_ADVANCED_ACCESSIBILITY !== 'false',
};

// Local storage keys for user preferences
const FEATURE_FLAGS_STORAGE_KEY = 'chatUI_featureFlags';

// Get user preference overrides from localStorage
function getUserPreferences(): Partial<FeatureFlags> {
  try {
    const stored = localStorage.getItem(FEATURE_FLAGS_STORAGE_KEY);
    return stored ? JSON.parse(stored) : {};
  } catch (error) {
    console.warn('Failed to parse feature flags from localStorage:', error);
    return {};
  }
}

// Save user preferences to localStorage
export function setUserPreference(flag: keyof FeatureFlags, value: boolean): void {
  try {
    const current = getUserPreferences();
    const updated = { ...current, [flag]: value };
    localStorage.setItem(FEATURE_FLAGS_STORAGE_KEY, JSON.stringify(updated));
  } catch (error) {
    console.warn('Failed to save feature flag preference:', error);
  }
}

// Get the final feature flags (default < env < user preferences)
export function getFeatureFlags(): FeatureFlags {
  const userPrefs = getUserPreferences();

  return {
    ...defaultFlags,
    ...envFlags,
    ...userPrefs,
  };
}

// Individual flag getters for convenience
export function useAssistantUI(): boolean {
  return getFeatureFlags().useAssistantUI;
}

export function enableStreamingChat(): boolean {
  return getFeatureFlags().enableStreamingChat;
}

export function enableToolVisualization(): boolean {
  return getFeatureFlags().enableToolVisualization;
}

export function enableMessageActions(): boolean {
  return getFeatureFlags().enableMessageActions;
}

export function enableAdvancedAccessibility(): boolean {
  return getFeatureFlags().enableAdvancedAccessibility;
}

// Hook for React components to use feature flags with reactivity
import { useState, useEffect } from 'react';

export function useFeatureFlags(): FeatureFlags {
  const [flags, setFlags] = useState<FeatureFlags>(getFeatureFlags());

  useEffect(() => {
    // Listen for localStorage changes (from other tabs/windows)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === FEATURE_FLAGS_STORAGE_KEY) {
        setFlags(getFeatureFlags());
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  return flags;
}

// Hook for individual feature flags
export function useFeatureFlag(flag: keyof FeatureFlags): boolean {
  const flags = useFeatureFlags();
  return flags[flag];
}

// Development helper to toggle flags (only available in development)
export function toggleFeatureFlag(flag: keyof FeatureFlags): void {
  if (import.meta.env.DEV) {
    const current = getFeatureFlags();
    setUserPreference(flag, !current[flag]);
    // Trigger a storage event to update other components
    window.dispatchEvent(
      new StorageEvent('storage', {
        key: FEATURE_FLAGS_STORAGE_KEY,
        newValue: localStorage.getItem(FEATURE_FLAGS_STORAGE_KEY),
      }),
    );
  } else {
    console.warn('Feature flag toggling is only available in development mode');
  }
}

// Migration helper - determines which chat panel to use
export function shouldUseAssistantUI(): boolean {
  return getFeatureFlags().useAssistantUI;
}

// Debug helper to log current feature flags
export function logFeatureFlags(): void {
  if (import.meta.env.DEV) {
    console.table(getFeatureFlags());
  }
}
