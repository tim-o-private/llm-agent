import React, { useState, useEffect } from 'react';
import { Task } from '@/api/types';
import { Button } from '@/components/ui/Button';

// Placeholder for session configuration passed from PrioritizeView
interface ExecuteSessionConfig {
  breakdown: string;
  timerDuration: number; // in seconds
}

interface ExecuteViewProps {
  task: Task | null;
  sessionConfig: ExecuteSessionConfig | null;
  onEndSession: () => void; // Callback when session ends or is manually stopped
}

export const ExecuteView: React.FC<ExecuteViewProps> = ({ task, sessionConfig, onEndSession }) => {
  const [timeLeft, setTimeLeft] = useState(sessionConfig?.timerDuration || 0);

  useEffect(() => {
    if (sessionConfig?.timerDuration) {
      setTimeLeft(sessionConfig.timerDuration);
    }
  }, [sessionConfig]);

  useEffect(() => {
    if (timeLeft <= 0) {
      // TODO: Potentially auto-trigger onEndSession or a notification
      return;
    }

    const timerId = setInterval(() => {
      setTimeLeft((prevTime) => prevTime - 1);
    }, 1000);

    return () => clearInterval(timerId);
  }, [timeLeft]);

  if (!task || !sessionConfig) {
    return (
      <div className="fixed inset-0 bg-ui-bg/70 flex items-center justify-center z-[100]">
        <p className="text-text-primary text-xl">Loading focus session...</p>
      </div>
    );
  }

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="fixed inset-0 bg-ui-bg text-text-primary flex flex-col items-center justify-center p-8 z-[100]">
      <div className="absolute top-8 left-8">
        <h1 className="text-2xl font-bold">Focus Mode</h1>
      </div>

      <div className="text-center">
        <p className="text-lg text-text-muted mb-2">Focusing on:</p>
        <h2 className="text-4xl font-semibold mb-8 truncate max-w-xl">{task.title}</h2>

        <div className="text-8xl font-mono mb-12">{formatTime(timeLeft)}</div>

        {sessionConfig.breakdown && (
          <div className="mb-8 p-4 bg-ui-element-bg rounded-lg max-w-md mx-auto">
            <h3 className="text-md font-semibold text-text-secondary mb-2">Session Steps:</h3>
            <p className="text-sm text-text-muted whitespace-pre-line">{sessionConfig.breakdown}</p>
          </div>
        )}

        <div className="flex space-x-4">
          <Button
            variant="soft"
            onClick={() => {
              /* TODO: Pause timer */
            }}
          >
            Pause
          </Button>
          <Button variant="solid" color="red" onClick={onEndSession}>
            End Session
          </Button>
        </div>
      </div>

      {/* Placeholder for Agent Chat & Scratch Pad - expandable panel */}
      {/* <div className="absolute bottom-8 right-8">
        <Button variant="outline">Notes & AI Coach</Button>
      </div> */}
    </div>
  );
};

export default ExecuteView;
