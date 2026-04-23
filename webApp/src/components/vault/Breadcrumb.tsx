import React from 'react';
import { Link } from 'react-router-dom';
import { ChevronRightIcon, HomeIcon } from '@radix-ui/react-icons';

interface BreadcrumbProps {
  /** Current vault path, e.g. "projects/foo/readme.md" or "" for root/Today */
  vaultPath: string;
}

/**
 * AC-05: Breadcrumb shows the current vault path.
 * Root shows "Today". Segments are clickable links to parent folders.
 */
export const Breadcrumb: React.FC<BreadcrumbProps> = ({ vaultPath }) => {
  // Root / empty path = Today
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

  const segments = vaultPath.split('/').filter(Boolean);

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

        return (
          <React.Fragment key={href}>
            <ChevronRightIcon className="h-3.5 w-3.5 text-text-muted flex-shrink-0" />
            {isLast ? (
              <span className="font-medium text-text-primary truncate">{segment}</span>
            ) : (
              <Link
                to={href}
                className="text-text-secondary hover:text-text-accent transition-colors truncate"
              >
                {segment}
              </Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};
