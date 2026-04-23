/**
 * SPEC-047 AC-01 / AC-13: Top-level file detail view for viewing/editing
 * a single file.
 *
 * Composes EditorPreviewSplit (center pane) + ContextRail (right sub-panel
 * within the center pane). Gets `path` from the vault route param.
 */

import React, { useState, useCallback } from 'react';
import { EditorPreviewSplit } from './EditorPreviewSplit';
import { ContextRail } from './ContextRail';

interface FileDetailViewProps {
  /** Vault-relative file path, e.g. "projects/readme.md" */
  path: string;
}

export const FileDetailView: React.FC<FileDetailViewProps> = ({ path }) => {
  const filename = path.split('/').pop() ?? path;

  // Shared editor content state for ContextRail reactive citations
  const [editorContent, setEditorContent] = useState('');

  const handleContentChange = useCallback((content: string) => {
    setEditorContent(content);
  }, []);

  return (
    <div className="h-full flex">
      {/* Main editor area */}
      <div className="flex-1 min-w-0 h-full">
        <EditorPreviewSplit
          path={path}
          onContentChange={handleContentChange}
        />
      </div>

      {/* AI Context Rail — sub-panel within the center pane */}
      <ContextRail
        path={path}
        editorContent={editorContent}
        filename={filename}
      />
    </div>
  );
};
