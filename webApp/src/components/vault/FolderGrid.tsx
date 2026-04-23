import React from 'react';
import { Link } from 'react-router-dom';
import { useVaultFolder } from '@/api/hooks/useVaultHooks';
import { Spinner } from '@/components/ui/Spinner';
import { FileTextIcon } from '@radix-ui/react-icons';
import { FolderIcon } from '@/components/ui/icons/FolderIcon';

interface FolderGridProps {
  /** Relative folder path within the vault, e.g. "projects" or "" for root */
  folderPath: string;
}

function typeChip(entry: { type: string; name: string }) {
  if (entry.type === 'folder') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
        folder
      </span>
    );
  }
  const ext = entry.name.split('.').pop()?.toLowerCase() ?? '';
  const label = ext === 'md' ? 'markdown' : ext || 'file';
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-ui-element-bg text-text-secondary">
      {label}
    </span>
  );
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

/**
 * AC-13: Grid of folder contents showing filename, type chip, last modified.
 */
export const FolderGrid: React.FC<FolderGridProps> = ({ folderPath }) => {
  const { data, isLoading, error } = useVaultFolder(folderPath);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Spinner size={24} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center py-16 text-text-secondary">
        <p>Failed to load folder contents.</p>
      </div>
    );
  }

  if (!data?.entries || data.entries.length === 0) {
    return (
      <div className="flex flex-col items-center py-16 text-text-secondary">
        <p>This folder is empty.</p>
      </div>
    );
  }

  // Sort: folders first, then alphabetically
  const sorted = [...data.entries].sort((a, b) => {
    if (a.type === 'folder' && b.type !== 'folder') return -1;
    if (a.type !== 'folder' && b.type === 'folder') return 1;
    return a.name.localeCompare(b.name);
  });

  return (
    <div className="w-full">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {sorted.map((entry) => {
          const href =
            entry.type === 'folder'
              ? `/vault/${entry.path}/`
              : `/vault/${entry.path}`;

          return (
            <Link
              key={entry.path}
              to={href}
              className="group flex items-start gap-3 p-3 rounded-lg border border-ui-border bg-ui-element-bg/50 hover:bg-ui-interactive-bg-hover hover:border-ui-border-glow transition-colors"
            >
              {entry.type === 'folder' ? (
                <FolderIcon className="h-5 w-5 text-text-muted flex-shrink-0 mt-0.5" />
              ) : (
                <FileTextIcon className="h-5 w-5 text-text-muted flex-shrink-0 mt-0.5" />
              )}
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-text-primary truncate group-hover:text-text-accent transition-colors">
                  {entry.name}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  {typeChip(entry)}
                  <span className="text-xs text-text-muted">{formatDate(entry.mtime)}</span>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
};
