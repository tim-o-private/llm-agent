import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Suspense, lazy, useEffect } from 'react';
import { AuthProvider } from '@/features/auth/AuthProvider';
import AppShell from '@/layouts/AppShell';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { Spinner } from '@/components/ui';
import { useTaskViewStore } from '@/stores/useTaskViewStore';
import { Toaster } from '@/components/ui/toast';

// Lazy load pages for better performance
const Home = lazy(() => import('@/pages/Home'));
const Login = lazy(() => import('@/pages/Login'));
const AuthCallback = lazy(() => import('@/pages/AuthCallback').then((module) => ({ default: module.AuthCallback })));

const Today = lazy(() => import('@/pages/Today'));
const ColorSwatchPage = lazy(() => import('@/pages/ColorSwatchPage'));
const DesignSystemPage = lazy(() => import('@/pages/DesignSystemPage'));
const SelectTestPage = lazy(() => import('@/pages/SelectTestPage'));
const IntegrationsPage = lazy(() =>
  import('@/pages/Settings/Integrations').then((module) => ({ default: module.IntegrationsPage })),
);
const DesignDemo = lazy(() =>
  import('@/components/ui/DesignDemo').then((module) => ({ default: () => <module.DesignDemo /> })),
);
const LayoutMockups = lazy(() =>
  import('@/components/ui/LayoutMockups').then((module) => ({ default: () => <module.LayoutMockups /> })),
);

// Vault browser component
const VaultContent = lazy(() =>
  import('@/components/vault/VaultContent').then((module) => ({ default: module.VaultContent })),
);

function App() {
  // Initialize and cleanup global keyboard listener
  useEffect(() => {
    useTaskViewStore.getState().initializeListener();
    return () => {
      useTaskViewStore.getState().destroyListener();
    };
  }, []);

  return (
    <Router>
      <AuthProvider>
        <ErrorBoundary>
          <Suspense
            fallback={
              <div className="w-full h-screen flex items-center justify-center">
                <Spinner />
              </div>
            }
          >
            <Routes>
              {/* Public routes */}
              <Route path="/home" element={<Home />} />
              <Route path="/login" element={<Login />} />
              <Route path="/auth/callback" element={<AuthCallback />} />
              {/* Temporary: Design demo as public route */}
              <Route path="/design-demo" element={<DesignDemo />} />
              {/* Temporary: Layout mockups as public route */}
              <Route path="/layout-mockups" element={<LayoutMockups />} />
              {/* Color swatch page for design reference */}
              <Route path="/colors" element={<ColorSwatchPage />} />
              {/* Design system page for component patterns */}
              <Route path="/design-system" element={<DesignSystemPage />} />
              {/* Temporary: SelectTestPage as public route for testing the Select component */}
              <Route path="/select-test" element={<SelectTestPage />} />

              {/* Protected routes — three-pane AppShell (AC-17) */}
              <Route element={<ProtectedRoute />}>
                <Route element={<AppShell />}>
                  {/* / -> Today (default landing) */}
                  <Route index element={<Today />} />
                  {/* /vault/* -> vault browser (file tree + content) */}
                  <Route path="vault/*" element={<VaultContent />} />
                  {/* /settings -> settings page */}
                  <Route path="settings" element={<IntegrationsPage />} />
                  {/* Redirect old routes (AC-17) */}
                  <Route path="today" element={<Navigate to="/" replace />} />
                  <Route path="coach" element={<Navigate to="/" replace />} />
                  <Route path="coach-v2" element={<Navigate to="/" replace />} />
                  <Route path="today-mockup" element={<Navigate to="/" replace />} />
                </Route>
              </Route>
            </Routes>
          </Suspense>
          <Toaster />
        </ErrorBoundary>
      </AuthProvider>
    </Router>
  );
}

export default App;
