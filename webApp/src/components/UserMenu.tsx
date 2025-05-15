import React from 'react';
import { useAuthStore } from '@/features/auth/useAuthStore';

export const UserMenu: React.FC = () => {
  const { user, loading, signInWithProvider, signOut } = useAuthStore();

  if (loading) return <div>Loading...</div>;

  if (!user) {
    return (
      <button
        onClick={() => signInWithProvider('google')}
        className="btn btn-primary"
      >
        Sign in with Google
      </button>
    );
  }

  return (
    <div className="flex items-center space-x-4">
      <span className="text-gray-700 dark:text-gray-300">{user.email}</span>
      <button onClick={signOut} className="btn btn-secondary">
        Sign out
      </button>
    </div>
  );
}; 