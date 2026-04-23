import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ActivityEntry } from '@/api/types/activity';
import type { ActivityFilters as ActivityFiltersType } from '@/api/types/activity';

interface ActivityFiltersProps {
  filters: ActivityFiltersType;
  onChange: (filters: ActivityFiltersType) => void;
  /** All loaded entries — used to derive the workflow dropdown options. */
  entries: ActivityEntry[];
}

const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'done', label: 'Done' },
  { value: 'failed', label: 'Failed' },
  { value: 'awaiting_approval', label: 'Awaiting approval' },
] as const;

export const ActivityFiltersComponent: React.FC<ActivityFiltersProps> = ({
  filters,
  onChange,
  entries,
}) => {
  // Debounced search
  const [localSearch, setLocalSearch] = useState(filters.q ?? '');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setLocalSearch(value);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        onChange({ ...filters, q: value || undefined });
      }, 300);
    },
    [filters, onChange],
  );

  // Clean up timeout on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  // Sync local search when filters.q changes externally
  useEffect(() => {
    setLocalSearch(filters.q ?? '');
  }, [filters.q]);

  // Derive distinct workflow run IDs from loaded entries
  const workflowOptions = useMemo(() => {
    const ids = new Set<string>();
    for (const entry of entries) {
      if (entry.workflow_run_id) ids.add(entry.workflow_run_id);
    }
    return Array.from(ids);
  }, [entries]);

  return (
    <div className="px-4 py-3 space-y-2 border-b border-ui-border">
      {/* Search */}
      <input
        type="search"
        aria-label="Search activity log"
        placeholder="Search activity..."
        value={localSearch}
        onChange={handleSearchChange}
        className="w-full px-3 py-1.5 text-sm rounded-md bg-ui-element-bg border border-ui-border text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-brand-primary"
      />

      {/* Filter row */}
      <div className="flex items-center gap-2">
        {/* Status dropdown */}
        <select
          aria-label="Filter by status"
          value={filters.status ?? ''}
          onChange={(e) =>
            onChange({ ...filters, status: e.target.value || undefined })
          }
          className="flex-1 px-2 py-1 text-xs rounded-md bg-ui-element-bg border border-ui-border text-text-primary focus:outline-none focus:ring-1 focus:ring-brand-primary"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Workflow dropdown */}
        <select
          aria-label="Filter by workflow"
          value={filters.workflow_run_id ?? ''}
          onChange={(e) =>
            onChange({
              ...filters,
              workflow_run_id: e.target.value || undefined,
            })
          }
          className="flex-1 px-2 py-1 text-xs rounded-md bg-ui-element-bg border border-ui-border text-text-primary focus:outline-none focus:ring-1 focus:ring-brand-primary"
        >
          <option value="">All workflows</option>
          {workflowOptions.map((id) => (
            <option key={id} value={id}>
              Run: {id.slice(0, 8)}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

export default ActivityFiltersComponent;
