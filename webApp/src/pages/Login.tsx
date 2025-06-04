import { UserMenu } from '@/components/UserMenu';
import { useEffect } from 'react';

export function AuthLogger() {
  useEffect(() => {
    console.log("Landed on:", window.location.href);
  }, []);
  return null;
} 

export default function Login() {
  return (
    <div className="min-h-screen bg-ui-bg flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-text-primary">Welcome back</h2>
          <p className="mt-2 text-text-muted">Sign in to your account</p>
        </div>
        <div className="mt-8 flex justify-center">
          <UserMenu />
          <AuthLogger />
        </div>
      </div>
    </div>
  );
}