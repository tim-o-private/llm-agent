/**
 * SPEC-047 AC-01 / AC-13: Top-level file detail view for viewing/editing
 * a single file.
 *
 * Composes EditorPreviewSplit (center pane) + ContextRail (right sub-panel
 * within the center pane). Gets `path` from the vault route param.
 *
 * SPEC-053 AC-22: When the file is an entity doc (path starts with
 * `entities/` and frontmatter contains `entity_type`), an EntityHeader
 * renders above the editor showing type badge, name, and key metadata.
 */

import React, { useState, useCallback, useMemo } from 'react';
import { EditorPreviewSplit } from './EditorPreviewSplit';
import { ContextRail } from './ContextRail';
import { EntityHeader } from './EntityHeader';
import { extractFrontmatter } from '@/lib/extractFrontmatter';
import { useVaultFile } from '@/api/hooks/useVaultHooks';
import { parse as parseYaml } from 'yaml';

interface FileDetailViewProps {
  /** Vault-relative file path, e.g. "projects/readme.md" */
  path: string;
}

/**
 * Parse YAML frontmatter string into a dict, returning null on failure.
 */
function parseFrontmatterYaml(raw: string | null): Record<string, unknown> | null {
  if (!raw) return null;
  try {
    const parsed = parseYaml(raw);
    return typeof parsed === 'object' && parsed !== null
      ? (parsed as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

export const FileDetailView: React.FC<FileDetailViewProps> = ({ path }) => {
  const filename = path.split('/').pop() ?? path;

  // Shared editor content state for ContextRail reactive citations
  const [editorContent, setEditorContent] = useState('');

  const handleContentChange = useCallback((content: string) => {
    setEditorContent(content);
  }, []);

  // Detect entity docs for EntityHeader (AC-22)
  const isEntityPath = path.startsWith('entities/');
  const { data: fileData } = useVaultFile(path, isEntityPath);

  const entityFrontmatter = useMemo(() => {
    if (!isEntityPath || !fileData?.content) return null;
    const { frontmatter: fmRaw } = extractFrontmatter(fileData.content);
    const fm = parseFrontmatterYaml(fmRaw);
    if (fm && fm.entity_type) return fm;
    return null;
  }, [isEntityPath, fileData?.content]);

  return (
    <div className="h-full flex flex-col">
      {/* Entity header — only for entity docs with valid frontmatter */}
      {entityFrontmatter && (
        <EntityHeader frontmatter={entityFrontmatter} />
      )}

      <div className="flex-1 min-h-0 flex">
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
    </div>
  );
};
