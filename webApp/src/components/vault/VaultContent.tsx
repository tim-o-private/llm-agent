import React, { Suspense, lazy } from 'react';
import { useParams } from 'react-router-dom';
import { Spinner } from '@/components/ui/Spinner';
import { FolderGrid } from './FolderGrid';
import { FilePreview } from './FilePreview';
import { FileDetailView } from './FileDetailView';

const Today = lazy(() => import('@/pages/Today'));

/**
 * AC-12..AC-16: Router dispatcher for vault paths.
 *
 * Reads the `*` param from the /vault/* route and decides:
 * - empty or "today.md" -> render Today page
 * - ends with "/" -> render FolderGrid
 * - ends with ".md" or other extension -> render FilePreview
 * - no match -> 404 empty state
 */
export const VaultContent: React.FC = () => {
  const { '*': splat } = useParams<{ '*': string }>();
  const vaultPath = splat ?? '';

  if (vaultPath === '' || vaultPath === 'today.md') {
    return (
      <div className="h-full overflow-y-auto">
        <Suspense
          fallback={
            <div className="flex items-center justify-center py-16">
              <Spinner size={24} />
            </div>
          }
        >
          <Today />
        </Suspense>
      </div>
    );
  }

  const isFolder = vaultPath.endsWith('/');
  const isMarkdown = vaultPath.endsWith('.md');
  const hasExtension = /\.[a-zA-Z0-9]+$/.test(vaultPath);

  // SPEC-047: .md files render in the full-height FileDetailView (CodeMirror editor)
  if (isMarkdown) {
    return <FileDetailView path={vaultPath} />;
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl px-4 md:px-6 py-4">
        {isFolder ? (
          <FolderGrid folderPath={vaultPath.replace(/\/$/, '')} />
        ) : hasExtension ? (
          <FilePreview filePath={vaultPath} />
        ) : (
          /* AC-15: 404 empty state */
          <div className="flex flex-col items-center py-16 text-text-secondary">
            <p className="text-lg font-medium">File not found in vault.</p>
            <p className="text-sm mt-1">
              The path <code className="px-1 py-0.5 bg-ui-element-bg rounded text-xs">{vaultPath}</code> does not
              match a known file.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
