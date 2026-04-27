import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ChevronRightIcon, HomeIcon } from '@radix-ui/react-icons';
import { useRenameItem } from '@/api/hooks/useVaultHooks';
import { toast } from '@/components/ui/toast';

interface BreadcrumbProps {
  vaultPath: string;
}

export const Breadcrumb: React.FC<BreadcrumbProps> = ({ vaultPath }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const renameMutation = useRenameItem();
  const inputRef = useRef<HTMLInputElement>(null);

  const isNew = !!(location.state as { isNew?: boolean } | null)?.isNew;
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState('');

  const segments = useMemo(
    () => (vaultPath ? vaultPath.split('/').filter(Boolean) : []),
    [vaultPath],
  );
  const lastSegment = segments[segments.length - 1] ?? '';
  const dotIdx = lastSegment.lastIndexOf('.');
  const hasExtension = dotIdx > 0;
  const nameOnly = hasExtension ? lastSegment.slice(0, dotIdx) : lastSegment;
  const ext = hasExtension ? lastSegment.slice(dotIdx) : '';

  // Enter edit mode when arriving at a newly created item
  useEffect(() => {
    if (isNew && lastSegment) {
      setEditing(true);
      setEditValue(nameOnly);
      window.history.replaceState({}, '');
    }
  }, [isNew, lastSegment, nameOnly]);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const commitRename = useCallback(() => {
    if (!editing) return;
    const trimmed = editValue.trim();

    if (!trimmed || trimmed === nameOnly) {
      setEditing(false);
      return;
    }

    if (/[/\\]/.test(trimmed)) {
      toast.error('Name cannot contain slashes');
      return;
    }

    const newFilename = ext ? `${trimmed}${ext}` : trimmed;
    const parentPath = segments.slice(0, -1).join('/');
    const sourcePath = vaultPath.replace(/\/$/, '');
    const newPath = parentPath ? `${parentPath}/${newFilename}` : newFilename;

    renameMutation.mutate(
      { source: sourcePath, target: newPath },
      {
        onSuccess: (result) => {
          setEditing(false);
          const suffix = ext ? '' : '/';
          navigate(`/vault/${result.path}${suffix}`, { replace: true });
        },
        onError: (err) => {
          toast.error(err.message);
          setEditing(false);
        },
      },
    );
  }, [editing, editValue, nameOnly, ext, segments, vaultPath, renameMutation, navigate]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        commitRename();
      } else if (e.key === 'Escape') {
        setEditing(false);
      }
    },
    [commitRename],
  );

  if (!vaultPath || vaultPath === 'today.md') {
    return (
      <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-sm">
        <Link
          to="/"
          className="flex items-center gap-1.5 text-text-primary font-semibold hover:text-text-accent transition-colors"
        >
          <HomeIcon className="h-4 w-4" />
          <span>Today</span>
        </Link>
      </nav>
    );
  }

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-sm min-w-0">
      <Link
        to="/"
        className="flex items-center gap-1 text-text-secondary hover:text-text-accent transition-colors flex-shrink-0"
      >
        <HomeIcon className="h-4 w-4" />
      </Link>

      {segments.map((segment, index) => {
        const isLast = index === segments.length - 1;
        const href =
          '/vault/' + segments.slice(0, index + 1).join('/') + (isLast ? '' : '/');

        let segmentEl: React.ReactNode;
        if (isLast && editing) {
          segmentEl = (
            <input
              ref={inputRef}
              type="text"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={commitRename}
              onKeyDown={handleKeyDown}
              className="font-medium text-text-primary bg-transparent border-b border-dashed border-brand-primary outline-none min-w-[60px] max-w-[200px] px-0.5"
              style={{ width: `${Math.max(editValue.length, 4)}ch` }}
              disabled={renameMutation.isPending}
            />
          );
        } else if (isLast) {
          segmentEl = (
            <span
              className="font-medium text-text-primary truncate cursor-text"
              onDoubleClick={() => {
                setEditValue(nameOnly);
                setEditing(true);
              }}
              title="Double-click to rename"
            >
              {segment}
            </span>
          );
        } else {
          segmentEl = (
            <Link
              to={href}
              className="text-text-secondary hover:text-text-accent transition-colors truncate"
            >
              {segment}
            </Link>
          );
        }

        return (
          <React.Fragment key={href}>
            <ChevronRightIcon className="h-3.5 w-3.5 text-text-muted flex-shrink-0" />
            {segmentEl}
          </React.Fragment>
        );
      })}
    </nav>
  );
};
