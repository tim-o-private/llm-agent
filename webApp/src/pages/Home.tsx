import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <div className="min-h-screen bg-ui-bg flex flex-col items-center justify-center p-4">
      <h1 className="text-4xl font-bold text-text-primary mb-8">Welcome to Clarity</h1>
      <p className="text-lg text-text-muted mb-8 text-center max-w-2xl">
        Your AI-powered productivity companion for focused work and personal growth.
      </p>
      <div className="space-x-4">
        <Link
          to="/login"
          className="inline-block bg-brand-primary text-brand-primary-text px-6 py-3 rounded-lg font-medium hover:bg-brand-primary-hover transition-colors"
        >
          Get Started
        </Link>
        <Link
          to="/dashboard"
          className="inline-block bg-ui-interactive-bg text-text-primary px-6 py-3 rounded-lg font-medium hover:bg-ui-interactive-bg-hover transition-colors"
        >
          View Demo
        </Link>
      </div>
    </div>
  );
} 