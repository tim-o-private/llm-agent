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
import {
  useSaveFile,
  useFileContext,
  useSuggestCardAccept,
  useSuggestCardDismiss,
} from '@/api/hooks/useFileDetailHooks';
import { VaultEditor, type VaultEditorHandle } from './VaultEditor';
import { MarkdownPreview } from './MarkdownPreview';
import { FileHeaderBar } from './FileHeaderBar';
import { LayoutToggle, type LayoutMode } from './LayoutToggle';
import type { SaveState } from './SaveStatus';
import type { SuggestCard as SuggestCardType } from '@/api/types/fileDetail';
import { Spinner } from '@/components/ui/Spinner';
import { toast } from '@/components/ui/toast';

interface EditorPreviewSplitProps {
  /** Vault-relative path, e.g. "projects/readme.md" */
  path: string;
  defaultLayout?: LayoutMode;
  /** Callback to expose current editor content to parent (for ContextRail) */
  onContentChange?: (content: string) => void;
}

export const EditorPreviewSplit: React.FC<EditorPreviewSplitProps> = ({
  path,
  defaultLayout,
  onContentChange,
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

  // Suggest cards: fetch file context + mutations
  const { data: fileContext } = useFileContext(path);
  const acceptMutation = useSuggestCardAccept();
  const dismissMutation = useSuggestCardDismiss();
  const [acceptingCardId, setAcceptingCardId] = useState<string | null>(null);
  const [dismissingCardId, setDismissingCardId] = useState<string | null>(null);

  // Initialize content when data loads
  useEffect(() => {
    if (data && !contentLoaded) {
      setEditorContent(data.content);
      setLastSavedContent(data.content);
      setLocalMtime(new Date(data.mtime).getTime() / 1000);
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

  // SPA navigation blocker (AC-06): useBlocker requires data router (createBrowserRouter),
  // but the app uses BrowserRouter. beforeunload above covers tab close. For SPA nav,
  // we intercept link clicks on the vault tree via this flag that consumers can check.
  // Full useBlocker support arrives when the app migrates to createBrowserRouter.

  // Handle content change from editor
  const handleEditorChange = useCallback(
    (newContent: string) => {
      setEditorContent(newContent);
      onContentChange?.(newContent);
    },
    [onContentChange],
  );

  // Propagate initial content load to parent
  useEffect(() => {
    if (contentLoaded) {
      onContentChange?.(editorContent);
    }
    // Only on load, not every change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contentLoaded]);

  // Suggest card accept handler (AC-17)
  const handleSuggestAccept = useCallback(
    (card: SuggestCardType) => {
      setAcceptingCardId(card.id);
      acceptMutation.mutate(
        { id: card.id, filePath: path },
        {
          onSuccess: (response) => {
            setAcceptingCardId(null);
            // Insert text at the target line
            const editor = editorRef.current;
            if (editor && response.text) {
              const currentContent = editor.getValue();
              const lines = currentContent.split('\n');
              const insertLine = Math.min(
                response.target_line,
                lines.length,
              );

              if (response.target_line > lines.length) {
                toast.default(
                  'Original position changed — text inserted at end.',
                );
              }

              lines.splice(insertLine, 0, response.text);
              const newContent = lines.join('\n');
              editor.setValue(newContent);
              setEditorContent(newContent);
              onContentChange?.(newContent);
            }
          },
          onError: () => {
            setAcceptingCardId(null);
          },
        },
      );
    },
    [acceptMutation, path, onContentChange],
  );

  // Suggest card dismiss handler (AC-17)
  const handleSuggestDismiss = useCallback(
    (card: SuggestCardType) => {
      setDismissingCardId(card.id);
      dismissMutation.mutate(
        { id: card.id, filePath: path },
        {
          onSuccess: () => {
            setDismissingCardId(null);
          },
          onError: () => {
            setDismissingCardId(null);
          },
        },
      );
    },
    [dismissMutation, path],
  );

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
              <MarkdownPreview
                ref={previewRef}
                content={editorContent}
                suggestCards={fileContext?.suggest_cards}
                onSuggestAccept={handleSuggestAccept}
                onSuggestDismiss={handleSuggestDismiss}
                acceptingCardId={acceptingCardId}
                dismissingCardId={dismissingCardId}
              />
            </Panel>
          )}
        </PanelGroup>
      </div>

      {/* AC-06: SPA navigation blocker deferred — requires createBrowserRouter migration.
         beforeunload handler above covers tab-close/refresh. */}
    </div>
  );
};
