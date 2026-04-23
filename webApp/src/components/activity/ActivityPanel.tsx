import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Cross2Icon } from '@radix-ui/react-icons';
import { useActivityLog, useMarkActivityViewed } from '@/api/hooks/useActivityHooks';
import { useActivityStore } from '@/stores/useActivityStore';
import { ActivityEntryComponent } from './ActivityEntry';
import { ActivityFiltersComponent } from './ActivityFilters';
import type { ActivityFilters } from '@/api/types/activity';

/**
 * SPEC-050 AC-12: Slide-in panel from the right edge, overlaying content.
 * role="complementary", aria-label="Agent activity log".
 * Opening triggers POST /api/activity/mark-viewed.
 */
export const ActivityPanel: React.FC = () => {
  const isOpen = useActivityStore((s) => s.isOpen);
  const close = useActivityStore((s) => s.close);

  const [filters, setFilters] = useState<ActivityFilters>({});
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading } =
    useActivityLog(filters);
  const markViewed = useMarkActivityViewed();
  const sentinelRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Mark viewed when panel opens
  const prevOpenRef = useRef(false);
  useEffect(() => {
    if (isOpen && !prevOpenRef.current) {
      markViewed.mutate();
    }
    prevOpenRef.current = isOpen;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  // Flatten all pages into a single array
  const allEntries = useMemo(
    () => data?.pages.flatMap((p) => p.items) ?? [],
    [data],
  );

  // Determine whether entries exist at all (ignoring filters)
  const totalFromFirstPage = data?.pages[0]?.total ?? 0;
  const hasAnyEntries = totalFromFirstPage > 0 || allEntries.length > 0;
  const hasFilters = Boolean(filters.q || filters.status || filters.workflow_run_id);

  // Infinite scroll via IntersectionObserver
  const fetchNextPageStable = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          fetchNextPageStable();
        }
      },
      { rootMargin: '100px' },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [fetchNextPageStable]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm"
        onClick={close}
        aria-hidden="true"
      />

      {/* Panel */}
      <aside
        role="complementary"
        aria-label="Agent activity log"
        className="fixed top-0 right-0 z-50 h-full w-full max-w-lg bg-ui-bg border-l border-ui-border shadow-elevated flex flex-col animate-slide-in-right"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-ui-border flex-shrink-0">
          <h2 className="text-base font-medium text-text-primary">
            Activity Log
          </h2>
          <button
            type="button"
            onClick={close}
            aria-label="Close activity log"
            className="p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-ui-interactive-bg-hover transition-colors"
          >
            <Cross2Icon className="h-4 w-4" />
          </button>
        </div>

        {/* Filters */}
        <ActivityFiltersComponent
          filters={filters}
          onChange={setFilters}
          entries={allEntries}
        />

        {/* Entry list */}
        <div
          ref={scrollContainerRef}
          className="flex-1 overflow-y-auto"
        >
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-primary border-t-transparent" />
            </div>
          ) : allEntries.length === 0 ? (
            <div className="px-4 py-12 text-center text-sm text-text-muted">
              {hasFilters || hasAnyEntries
                ? 'No matching entries. Try adjusting your filters.'
                : 'No agent activity yet. Actions will appear here as the agent works.'}
            </div>
          ) : (
            <ol aria-label="Activity entries">
              {allEntries.map((entry) => (
                <li key={entry.id}>
                  <ActivityEntryComponent entry={entry} />
                </li>
              ))}
            </ol>
          )}

          {/* Sentinel for infinite scroll */}
          <div ref={sentinelRef} className="h-1" aria-hidden="true" />

          {/* Loading indicator for next page */}
          {isFetchingNextPage && (
            <div className="flex items-center justify-center py-4">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-brand-primary border-t-transparent" />
              <span className="ml-2 text-xs text-text-muted">
                Loading more...
              </span>
            </div>
          )}
        </div>
      </aside>
    </>
  );
};

export default ActivityPanel;
