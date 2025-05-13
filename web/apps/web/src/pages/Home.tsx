import React from 'react';
import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <h1 className="text-4xl font-bold text-gray-900 mb-8">Welcome to Clarity</h1>
      <p className="text-lg text-gray-600 mb-8 text-center max-w-2xl">
        Your AI-powered productivity companion for focused work and personal growth.
      </p>
      <div className="space-x-4">
        <Link
          to="/login"
          className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
        >
          Get Started
        </Link>
        <Link
          to="/dashboard"
          className="inline-block bg-gray-200 text-gray-800 px-6 py-3 rounded-lg font-medium hover:bg-gray-300 transition-colors"
        >
          View Demo
        </Link>
      </div>
    </div>
  );
} 