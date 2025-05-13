import React from 'react';
import { BrowserRouter as Router, Routes, Route, Outlet } from 'react-router-dom';
import { Suspense, lazy } from 'react';
import { AuthProvider } from './features/auth/AuthProvider';
import AppShell from './layouts/AppShell';
import { ProtectedRoute } from './components/ProtectedRoute';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Spinner } from '@clarity/ui';

// Lazy load pages for better performance
const Home = lazy(() => import('./pages/Home'));
const Login = lazy(() => import('./pages/Login'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const TodayView = lazy(() => import('./pages/TodayView'));
const CoachPage = lazy(() => import('./pages/CoachPage'));

// Layout component that incorporates AppShell
const AppLayout: React.FC = () => {
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
};

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

              {/* Protected routes wrapped by AppLayout (which includes AppShell) */}
              <Route element={<ProtectedRoute />}>
                <Route element={<AppLayout />}>
                  <Route path="/today" element={<TodayView />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/coach" element={<CoachPage />} />
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