import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '@/features/auth/useAuthStore';

export const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuthStore();

  if (loading) return <div>Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}; 