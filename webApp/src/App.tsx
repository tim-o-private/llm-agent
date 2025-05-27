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

const TodayView = lazy(() => import('@/pages/TodayView.tsx'));
const CoachPage = lazy(() => import('@/pages/CoachPage'));
const CoachPageV2 = lazy(() => import('@/pages/CoachPageV2'));

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
              {/* Temporary: CoachPageV2 as public route for testing */}
              <Route path="/coach-v2" element={<CoachPageV2 />} />

              {/* Protected routes wrapped by AppShell directly */}
              <Route element={<ProtectedRoute />}>
                {/* Wrap child routes with AppShell and render them via Outlet */}
                <Route element={<AppShell><Outlet /></AppShell>}> 
                  <Route path="/today" element={<TodayView />} />
                  <Route path="/coach" element={<CoachPage />} />
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