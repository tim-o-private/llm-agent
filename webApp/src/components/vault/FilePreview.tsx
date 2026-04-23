import React from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useVaultFile } from '@/api/hooks/useVaultHooks';
import { Spinner } from '@/components/ui/Spinner';

interface FilePreviewProps {
  /** Relative path within the vault, e.g. "projects/readme.md" */
  filePath: string;
}

/**
 * AC-14: Read-only markdown preview using react-markdown + remark-gfm.
 * No editing in this spec (SPEC-047 upgrades to CodeMirror).
 */
export const FilePreview: React.FC<FilePreviewProps> = ({ filePath }) => {
  const { data, isLoading, error } = useVaultFile(filePath);

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
        <p>Failed to load file.</p>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const fileName = filePath.split('/').pop() ?? filePath;
  const isMarkdown = filePath.endsWith('.md');

  return (
    <div className="w-full">
      {/* File info header */}
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-ui-border">
        <h1 className="text-lg font-semibold text-text-primary">{fileName}</h1>
        <span className="text-xs text-text-muted">
          {data.size > 0 && `${(data.size / 1024).toFixed(1)} KB`}
        </span>
      </div>

      {/* Content */}
      {isMarkdown ? (
        <article className="prose prose-sm dark:prose-invert max-w-none text-text-primary">
          <Markdown remarkPlugins={[remarkGfm]}>{data.content}</Markdown>
        </article>
      ) : (
        <pre className="overflow-auto rounded-md bg-ui-element-bg p-4 text-sm font-mono text-text-primary whitespace-pre-wrap">
          {data.content}
        </pre>
      )}
    </div>
  );
};
