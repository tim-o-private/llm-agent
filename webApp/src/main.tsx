import React, { useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Theme } from '@radix-ui/themes';
import App from './App';
import { useThemeStore, getEffectiveAppearance } from './stores/useThemeStore'; // Import store and helper
import '@radix-ui/themes/styles.css'; // Radix Themes CSS
import './styles/index.css';
import './styles/ui-components.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

// Create a wrapper component to use the Zustand hook
function ThemedApp() {
  const storedAppearance = useThemeStore((state) => state.appearance);
  const effectiveAppearance = getEffectiveAppearance(storedAppearance);

  useEffect(() => {
    const root = window.document.documentElement;
    if (effectiveAppearance === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [effectiveAppearance]); // Rerun effect when effectiveAppearance changes

  return (
    <Theme accentColor="indigo" grayColor="slate" appearance={effectiveAppearance}>
      <App />
    </Theme>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemedApp />
    </QueryClientProvider>
  </React.StrictMode>
); 