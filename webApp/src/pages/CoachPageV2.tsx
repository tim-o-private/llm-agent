import React from 'react';
import { ChatPanelV2 } from '@/components/ChatPanelV2';

const CoachPageV2: React.FC = () => {
  return (
    <div className="h-full flex flex-col p-4 md:p-6 lg:p-8">
      {/* The ChatPanelV2 itself should handle its internal layout and scrolling */}
      {/* This surrounding div ensures the ChatPanelV2 can expand to fill the AppShell content area */}
      <ChatPanelV2 />
    </div>
  );
};

export default CoachPageV2; 