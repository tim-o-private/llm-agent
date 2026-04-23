import { createBrowserRouter, RouterProvider, Navigate, Outlet } from 'react-router-dom';
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

/**
 * Root layout: wraps all routes with AuthProvider (which needs router context
 * for useNavigate/useLocation), ErrorBoundary, and Suspense.
 */
function RootLayout() {
  return (
    <AuthProvider>
      <ErrorBoundary>
        <Suspense
          fallback={
            <div className="w-full h-screen flex items-center justify-center">
              <Spinner />
            </div>
          }
        >
          <Outlet />
        </Suspense>
        <Toaster />
      </ErrorBoundary>
    </AuthProvider>
  );
}

const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      // Public routes
      { path: '/home', element: <Home /> },
      { path: '/login', element: <Login /> },
      { path: '/auth/callback', element: <AuthCallback /> },
      { path: '/design-demo', element: <DesignDemo /> },
      { path: '/layout-mockups', element: <LayoutMockups /> },
      { path: '/colors', element: <ColorSwatchPage /> },
      { path: '/design-system', element: <DesignSystemPage /> },
      { path: '/select-test', element: <SelectTestPage /> },

      // Protected routes — three-pane AppShell
      {
        element: <ProtectedRoute />,
        children: [
          {
            element: <AppShell />,
            children: [
              { index: true, element: <Today /> },
              { path: 'vault/*', element: <VaultContent /> },
              { path: 'settings', element: <IntegrationsPage /> },
              // Redirect old routes
              { path: 'today', element: <Navigate to="/" replace /> },
              { path: 'coach', element: <Navigate to="/" replace /> },
              { path: 'coach-v2', element: <Navigate to="/" replace /> },
              { path: 'today-mockup', element: <Navigate to="/" replace /> },
            ],
          },
        ],
      },
    ],
  },
]);

function App() {
  useEffect(() => {
    useTaskViewStore.getState().initializeListener();
    return () => {
      useTaskViewStore.getState().destroyListener();
    };
  }, []);

  return <RouterProvider router={router} />;
}

export default App;
