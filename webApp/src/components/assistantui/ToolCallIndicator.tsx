import type { FC } from 'react';

interface ToolFallbackProps {
  toolName: string;
  argsText?: string;
  result?: unknown;
  status?: { type: string };
}

export const ToolFallback: FC<ToolFallbackProps> = ({ toolName, status }) => {
  const isRunning = !status || status.type === 'running';

  return (
    <div
      className={`flex items-center gap-2 px-3 py-1.5 my-1 text-xs font-mono rounded-md border border-dashed transition-colors ${
        isRunning
          ? 'text-text-accent bg-accent-surface/50 border-accent-subtle animate-pulse'
          : 'text-text-muted bg-ui-element-bg/50 border-ui-border'
      }`}
    >
      {isRunning && (
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-text-accent animate-ping" />
      )}
      <span>{isRunning ? `using ${toolName}` : `used ${toolName}`}</span>
    </div>
  );
};
