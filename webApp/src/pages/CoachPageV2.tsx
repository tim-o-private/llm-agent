import React from 'react';
import { ChatPanel } from '@/components/ChatPanel';

const CoachPageV2: React.FC = () => {
  return (
    <div className="h-full flex flex-col p-4 md:p-6 lg:p-8">
      <ChatPanel />
    </div>
  );
};

export default CoachPageV2;
