/**
 * SPEC-047 AC-01: Top-level file detail view for viewing/editing a single file.
 *
 * Composes EditorPreviewSplit within the center pane. Gets `path` from the
 * vault route param. FU-4 will add the ContextRail as a companion panel here.
 */

import React from 'react';
import { EditorPreviewSplit } from './EditorPreviewSplit';

interface FileDetailViewProps {
  /** Vault-relative file path, e.g. "projects/readme.md" */
  path: string;
}

export const FileDetailView: React.FC<FileDetailViewProps> = ({ path }) => {
  return (
    <div className="h-full flex">
      {/* Main editor area — takes full width until FU-4 adds ContextRail */}
      <div className="flex-1 min-w-0 h-full">
        <EditorPreviewSplit path={path} />
      </div>

      {/* FU-4 slot: ContextRail will be added here as a right sub-panel */}
    </div>
  );
};
