import React from 'react';
import { Card } from '../../components/ui/Card';
import { GmailConnection } from '../../components/features/GmailConnection/GmailConnection';

export const IntegrationsPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-2">Integrations</h1>
        <p className="text-gray-600">Connect external services to enhance your AI assistant capabilities.</p>
      </div>

      <div className="grid gap-6">
        {/* Gmail Integration */}
        <GmailConnection
          onConnectionChange={(isConnected) => {
            console.log('Gmail connection status:', isConnected);
          }}
        />

        {/* Future integrations can be added here */}
        <Card className="p-6 opacity-50">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 bg-gray-200 rounded flex items-center justify-center">📅</div>
            <h3 className="text-lg font-semibold text-gray-500">Google Calendar</h3>
            <span className="text-sm bg-gray-100 text-gray-600 px-2 py-1 rounded">Coming Soon</span>
          </div>
          <p className="text-gray-500 text-sm">
            Connect your Google Calendar to enable scheduling and event management.
          </p>
        </Card>

        <Card className="p-6 opacity-50">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 bg-gray-200 rounded flex items-center justify-center">💬</div>
            <h3 className="text-lg font-semibold text-gray-500">Slack</h3>
            <span className="text-sm bg-gray-100 text-gray-600 px-2 py-1 rounded">Coming Soon</span>
          </div>
          <p className="text-gray-500 text-sm">Connect Slack to send notifications and manage team communications.</p>
        </Card>
      </div>
    </div>
  );
};
