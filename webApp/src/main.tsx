import React, { useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Theme } from '@radix-ui/themes';
import App from './App';
import { useThemeStore, getEffectiveAppearance } from '@/stores/useThemeStore'; // Changed to @/ alias
import '@/styles/index.css'; // Changed to @/ alias
import '@/styles/ui-components.css'; // Changed to @/ alias

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
    <Theme accentColor="violet" grayColor="slate" appearance={effectiveAppearance} radius="medium" scaling="100%">
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