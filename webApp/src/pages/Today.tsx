import React, { useState } from 'react';
import { ErrorMessage } from '@/components/ui/ErrorMessage';
import { Spinner } from '@/components/ui/Spinner';
import { Button } from '@/components/ui/Button';
import { useToday, useTodaySource, useRegenerationStatus } from '@/api/hooks/useTodayHooks';
import { HeaderSection } from '@/components/today/HeaderSection';
import { YourDaySection } from '@/components/today/YourDaySection';
import { ToDoSection } from '@/components/today/ToDoSection';
import { NotesSection } from '@/components/today/NotesSection';
import { AgentSection } from '@/components/today/AgentSection';
import { ApprovalsSection } from '@/components/today/ApprovalsSection';
import { RecentSection } from '@/components/today/RecentSection';
import { SourceToggle } from '@/components/today/SourceToggle';

const Today: React.FC = () => {
  const [sourceMode, setSourceMode] = useState(false);
  const { data: today, isLoading, error, refetch } = useToday();
  const { data: sourceText } = useTodaySource(sourceMode);
  const regenStatus = useRegenerationStatus();
  const regenerating =
    regenStatus.data?.status === 'running' || regenStatus.data?.status === 'pending';

  if (isLoading) {
    return (
      <main aria-label="Today" aria-busy="true" className="w-full flex justify-center py-16">
        <Spinner size={28} />
      </main>
    );
  }

  if (error || !today) {
    return (
      <main aria-label="Today" className="w-full flex flex-col items-center py-16 gap-3">
        <ErrorMessage>Couldn&apos;t load Today. Try refreshing.</ErrorMessage>
        <Button variant="soft" size="2" onClick={() => refetch()}>
          Refresh
        </Button>
      </main>
    );
  }

  return (
    <main aria-label="Today" className="w-full">
      <div className="mx-auto max-w-3xl px-4 md:px-0">
        <div className="flex justify-end pt-4">
          <SourceToggle
            sourceMode={sourceMode}
            onToggle={() => setSourceMode((v) => !v)}
          />
        </div>

        {sourceMode ? (
          <pre
            role="region"
            aria-label="Today source (markdown)"
            className="mt-4 overflow-auto rounded-md bg-ui-element-bg p-6 text-sm font-mono text-text-primary whitespace-pre-wrap"
          >
            {sourceText ?? 'Loading source…'}
          </pre>
        ) : (
          <>
            <HeaderSection
              date={today.date}
              framing={today.header.framing}
              regenerating={regenerating}
            />
            <YourDaySection items={today.your_day} />
            <ToDoSection items={today.to_do} />
            <NotesSection notes={today.notes} />
            <AgentSection agent={today.agent} />
            <ApprovalsSection cards={today.approvals} />
            <RecentSection items={today.recent} />
          </>
        )}
      </div>
    </main>
  );
};

export default Today;
