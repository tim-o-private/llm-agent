/**
 * SPEC-047 AC-07 / AC-10: Split view container for editor + preview.
 *
 * Uses react-resizable-panels for the horizontal split. Three layout
 * modes: split (default for .md), source (default for .flow.md), preview.
 * Manages dirty state and save flow. Scroll sync in split mode.
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
} from 'react-resizable-panels';
import { useVaultFile } from '@/api/hooks/useVaultHooks';
import { useSaveFile } from '@/api/hooks/useFileDetailHooks';
import { VaultEditor, type VaultEditorHandle } from './VaultEditor';
import { MarkdownPreview } from './MarkdownPreview';
import { FileHeaderBar } from './FileHeaderBar';
import { LayoutToggle, type LayoutMode } from './LayoutToggle';
import type { SaveState } from './SaveStatus';
import { Spinner } from '@/components/ui/Spinner';
import { useBlocker } from 'react-router-dom';

interface EditorPreviewSplitProps {
  /** Vault-relative path, e.g. "projects/readme.md" */
  path: string;
  defaultLayout?: LayoutMode;
}

export const EditorPreviewSplit: React.FC<EditorPreviewSplitProps> = ({
  path,
  defaultLayout,
}) => {
  const isFlowFile = path.endsWith('.flow.md');
  const initialLayout = defaultLayout ?? (isFlowFile ? 'source' : 'split');

  const [layoutMode, setLayoutMode] = useState<LayoutMode>(initialLayout);
  const [editorContent, setEditorContent] = useState<string>('');
  const [lastSavedContent, setLastSavedContent] = useState<string>('');
  const [localMtime, setLocalMtime] = useState<number>(0);
  const [saveState, setSaveState] = useState<SaveState>('saved');
  const [contentLoaded, setContentLoaded] = useState(false);

  const editorRef = useRef<VaultEditorHandle>(null);
  const previewRef = useRef<HTMLDivElement>(null);
  const scrollSyncEnabled = useRef(true);
  const previewScrollTimeout = useRef<ReturnType<typeof setTimeout>>();

  // Fetch file content
  const { data, isLoading, error } = useVaultFile(path);
  const saveMutation = useSaveFile();

  // Initialize content when data loads
  useEffect(() => {
    if (data && !contentLoaded) {
      setEditorContent(data.content);
      setLastSavedContent(data.content);
      setLocalMtime(parseFloat(data.mtime));
      setContentLoaded(true);
      setSaveState('saved');
    }
  }, [data, contentLoaded]);

  // Reset when path changes
  useEffect(() => {
    setContentLoaded(false);
    setSaveState('saved');
  }, [path]);

  // Dirty state tracking
  const isDirty = editorContent !== lastSavedContent && contentLoaded;

  useEffect(() => {
    if (!contentLoaded) return;
    setSaveState(isDirty ? 'unsaved' : 'saved');
  }, [isDirty, contentLoaded]);

  // beforeunload protection (AC-06)
  useEffect(() => {
    if (!isDirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [isDirty]);

  // React Router navigation blocker (AC-06)
  const blocker = useBlocker(isDirty);

  // Handle content change from editor
  const handleEditorChange = useCallback((newContent: string) => {
    setEditorContent(newContent);
  }, []);

  // Save handler
  const handleSave = useCallback(() => {
    if (!isDirty) return;
    setSaveState('saving');

    saveMutation.mutate(
      { path, content: editorContent, mtime: localMtime },
      {
        onSuccess: (response) => {
          setLocalMtime(response.mtime);
          setLastSavedContent(editorContent);
          setSaveState('saved');
        },
        onError: () => {
          setSaveState('unsaved');
        },
      },
    );
  }, [isDirty, path, editorContent, localMtime, saveMutation]);

  // Scroll sync (AC-10): percentage-based
  const handleEditorScroll = useCallback(
    (e: Event) => {
      if (layoutMode !== 'split' || !scrollSyncEnabled.current) return;
      const editorScrollDOM = e.target as HTMLElement;
      const preview = previewRef.current;
      if (!preview) return;

      const scrollRatio =
        editorScrollDOM.scrollTop /
        (editorScrollDOM.scrollHeight - editorScrollDOM.clientHeight || 1);
      preview.scrollTop =
        scrollRatio * (preview.scrollHeight - preview.clientHeight);
    },
    [layoutMode],
  );

  // Re-engage scroll sync after user scrolls preview independently
  const handlePreviewScroll = useCallback(() => {
    scrollSyncEnabled.current = false;
    if (previewScrollTimeout.current) {
      clearTimeout(previewScrollTimeout.current);
    }
    // Re-engage after 1s of no preview scroll
    previewScrollTimeout.current = setTimeout(() => {
      scrollSyncEnabled.current = true;
    }, 1000);
  }, []);

  // Attach preview scroll listener
  useEffect(() => {
    const preview = previewRef.current;
    if (!preview) return;
    preview.addEventListener('scroll', handlePreviewScroll, { passive: true });
    return () => preview.removeEventListener('scroll', handlePreviewScroll);
  }, [handlePreviewScroll, layoutMode]);

  const filename = path.split('/').pop() ?? path;
  const showEditor = layoutMode === 'split' || layoutMode === 'source';
  const showPreview = layoutMode === 'split' || layoutMode === 'preview';

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner size={24} />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-text-secondary">
        <p className="text-lg font-medium">File not found in vault</p>
        <p className="text-sm mt-1 text-text-muted">
          The file <code className="px-1 py-0.5 bg-ui-element-bg rounded text-xs">{path}</code> could not be loaded.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header bar */}
      <FileHeaderBar
        vaultPath={path}
        saveState={saveState}
        onSave={handleSave}
        editorRef={editorRef}
        layoutToggle={
          <LayoutToggle mode={layoutMode} onChange={setLayoutMode} />
        }
      />

      {/* Editor / Preview split */}
      <div className="flex-1 min-h-0">
        <PanelGroup direction="horizontal" aria-label="Editor split view">
          {showEditor && (
            <Panel defaultSize={layoutMode === 'split' ? 50 : 100} minSize={25}>
              <VaultEditor
                ref={editorRef}
                content={contentLoaded ? lastSavedContent : ''}
                onChange={handleEditorChange}
                onSave={handleSave}
                language={path.endsWith('.yaml') || path.endsWith('.yml') ? 'yaml' : 'markdown'}
                filename={filename}
                onScroll={handleEditorScroll}
              />
            </Panel>
          )}
          {showEditor && showPreview && (
            <PanelResizeHandle className="flex w-1.5 items-center justify-center bg-transparent hover:bg-brand-primary/20 transition-colors group">
              <div className="w-0.5 h-8 rounded-full bg-ui-border group-hover:bg-brand-primary transition-colors" />
            </PanelResizeHandle>
          )}
          {showPreview && (
            <Panel defaultSize={layoutMode === 'split' ? 50 : 100} minSize={25}>
              <MarkdownPreview ref={previewRef} content={editorContent} />
            </Panel>
          )}
        </PanelGroup>
      </div>

      {/* Navigation blocker dialog (AC-06) */}
      {blocker.state === 'blocked' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-ui-element-bg border border-ui-border rounded-lg p-6 max-w-sm mx-4 shadow-elevated">
            <h2 className="text-lg font-semibold text-text-primary mb-2">
              Unsaved changes
            </h2>
            <p className="text-sm text-text-secondary mb-4">
              You have unsaved changes. Discard?
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => blocker.reset?.()}
                className="px-3 py-1.5 text-sm rounded-md text-text-primary bg-ui-element-bg border border-ui-border hover:bg-ui-interactive-bg-hover transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => blocker.proceed?.()}
                className="px-3 py-1.5 text-sm rounded-md text-white bg-red-600 hover:bg-red-700 transition-colors"
              >
                Discard
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
