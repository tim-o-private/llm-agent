import { BrowserRouter as Router, Routes, Route, Outlet } from 'react-router-dom';
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
const AuthCallback = lazy(() => import('@/pages/AuthCallback').then(module => ({ default: module.AuthCallback })));

const TodayView = lazy(() => import('@/pages/TodayView.tsx'));
const TodayViewMockup = lazy(() => import('@/pages/TodayViewMockup'));
const CoachPage = lazy(() => import('@/pages/CoachPage'));
const CoachPageV2 = lazy(() => import('@/pages/CoachPageV2'));
const ColorSwatchPage = lazy(() => import('@/pages/ColorSwatchPage'));
const DesignSystemPage = lazy(() => import('@/pages/DesignSystemPage'));
const SelectTestPage = lazy(() => import('@/pages/SelectTestPage'));
const IntegrationsPage = lazy(() => import('@/pages/Settings/Integrations').then(module => ({ default: module.IntegrationsPage })));
const DesignDemo = lazy(() => import('@/components/ui/DesignDemo').then(module => ({ default: () => <module.DesignDemo /> })));
const LayoutMockups = lazy(() => import('@/components/ui/LayoutMockups').then(module => ({ default: () => <module.LayoutMockups /> })));

// AppLayout component is no longer needed as AppShell is the primary layout.

function App() {
  // Initialize and cleanup global keyboard listener
  useEffect(() => {
    useTaskViewStore.getState().initializeListener();
    return () => {
      useTaskViewStore.getState().destroyListener();
    };
  }, []); // Empty dependency array ensures this runs only once on mount and unmount

  return (
    <Router>
      <AuthProvider>
        <ErrorBoundary>
          <Suspense fallback={<div className="w-full h-screen flex items-center justify-center"><Spinner /></div>}>
            <Routes>
              {/* Public routes */}
              <Route path="/" element={<Home />} />
              <Route path="/login" element={<Login />} />
              <Route path="/auth/callback" element={<AuthCallback />} />
              {/* Temporary: CoachPageV2 as public route for testing */}
              <Route path="/coach-v2" element={<CoachPageV2 />} />
              {/* Temporary: Design demo as public route */}
              <Route path="/design-demo" element={<DesignDemo />} />
              {/* Temporary: Layout mockups as public route */}
              <Route path="/layout-mockups" element={<LayoutMockups />} />
              {/* Temporary: TodayView mockup as public route for testing */}
              <Route path="/today-mockup" element={<TodayViewMockup />} />
              {/* Color swatch page for design reference */}
              <Route path="/colors" element={<ColorSwatchPage />} />
              {/* Design system page for component patterns */}
              <Route path="/design-system" element={<DesignSystemPage />} />
              {/* Temporary: SelectTestPage as public route for testing the Select component */}
              <Route path="/select-test" element={<SelectTestPage />} />
              {/* Protected routes wrapped by AppShell directly */}
              <Route element={<ProtectedRoute />}>
                {/* Wrap child routes with AppShell and render them via Outlet */}
                <Route element={<AppShell><Outlet /></AppShell>}> 
                  <Route path="/today" element={<TodayView />} />
                  <Route path="/coach" element={<CoachPage />} />
                  <Route path="/settings" element={<IntegrationsPage />} />
                  {/* Default protected route */}
                  <Route index element={<TodayView />} /> 
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