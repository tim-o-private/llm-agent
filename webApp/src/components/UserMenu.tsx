import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/features/auth/useAuthStore';

export const UserMenu: React.FC = () => {
  const { user, loading, signInWithProvider, signOut } = useAuthStore();
  const navigate = useNavigate();

  if (loading) return <div>Loading...</div>;

  if (!user) {
    return (
      <button onClick={() => signInWithProvider('google')} className="btn btn-primary">
        Sign in with Google
      </button>
    );
  }

  return (
    <div className="flex items-center space-x-4">
      <span className="text-text-secondary">{user.email}</span>
      <button onClick={() => navigate('/settings')} className="btn btn-secondary">
        Settings
      </button>
      <button onClick={signOut} className="btn btn-secondary">
        Sign out
      </button>
    </div>
  );
};
