import React from 'react';
import { ChatPanel } from '@/components/ChatPanel';

const CoachPage: React.FC = () => {
  return (
    <div className="h-full flex flex-col p-4 md:p-6 lg:p-8">
      {/* The ChatPanel itself should handle its internal layout and scrolling */}
      {/* This surrounding div ensures the ChatPanel can expand to fill the AppShell content area */}
      <ChatPanel />
    </div>
  );
};

export default CoachPage; 