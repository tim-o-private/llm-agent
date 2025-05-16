import { BrowserRouter as Router, Routes, Route, Outlet } from 'react-router-dom';
import { Suspense, lazy } from 'react';
import { AuthProvider } from '@/features/auth/AuthProvider';
import AppShell from '@/layouts/AppShell';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { Spinner } from '@/components/ui';

// Lazy load pages for better performance
const Home = lazy(() => import('@/pages/Home'));
const Login = lazy(() => import('@/pages/Login'));
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const TodayView = lazy(() => import('@/pages/TodayView.tsx'));
const CoachPage = lazy(() => import('@/pages/CoachPage'));

// AppLayout component is no longer needed as AppShell is the primary layout.

function App() {
  return (
    <Router>
      <AuthProvider>
        <ErrorBoundary>
          <Suspense fallback={<div className="w-full h-screen flex items-center justify-center"><Spinner /></div>}>
            <Routes>
              {/* Public routes */}
              <Route path="/" element={<Home />} />
              <Route path="/login" element={<Login />} />

              {/* Protected routes wrapped by AppShell directly */}
              <Route element={<ProtectedRoute />}>
                {/* Wrap child routes with AppShell and render them via Outlet */}
                <Route element={<AppShell><Outlet /></AppShell>}> 
                  <Route path="/today" element={<TodayView />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/coach" element={<CoachPage />} />
                  {/* Default protected route */}
                  <Route index element={<TodayView />} /> 
                </Route>
              </Route>
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </AuthProvider>
    </Router>
  );
}

export default App; 