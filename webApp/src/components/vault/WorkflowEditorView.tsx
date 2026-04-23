/**
 * SPEC-048 AC-01/AC-02/AC-03/AC-09/AC-13: Top-level workflow editor view.
 *
 * Three sub-panes using react-resizable-panels:
 *   Left (18%, collapsible): WorkflowListPanel
 *   Center (55%): FileHeaderBar + editor/preview
 *   Right (27%, collapsible): RunHistoryPanel
 *
 * Composes SPEC-047 components (VaultEditor, FileHeaderBar, MarkdownPreview)
 * with workflow-specific panels and controls. Does NOT duplicate the editor.
 *
 * AC-13: auto-save before dry-run/run-now. AC-14/AC-16: dialog wiring.
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
import {
  useDryRun,
  useRunWorkflow,
} from '@/api/hooks/useWorkflowEditorHooks';
import { VaultEditor, type VaultEditorHandle } from './VaultEditor';
import { MarkdownPreview } from './MarkdownPreview';
import { FileHeaderBar } from './FileHeaderBar';
import { LayoutToggle, type LayoutMode } from './LayoutToggle';
import { WorkflowListPanel } from './WorkflowListPanel';
import { RunHistoryPanel } from './RunHistoryPanel';
import { WorkflowHeaderExtension } from './WorkflowHeaderExtension';
import { DryRunResultsDialog } from './DryRunResultsDialog';
import { ParameterInputDialog } from './ParameterInputDialog';
import type { SaveState } from './SaveStatus';
import type { SuggestCard as SuggestCardType } from '@/api/types/fileDetail';
import type { DryRunResult, DryRunParameter } from '@/api/types/workflowEditor';
import { Spinner } from '@/components/ui/Spinner';
import { toast } from '@/components/ui/toast';
import { useBlocker } from 'react-router-dom';
import {
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@radix-ui/react-icons';

interface WorkflowEditorViewProps {
  path: string;
}

function extractTemplateName(path: string): string {
  // "_workflows/morning-briefing.flow.md" -> "morning-briefing"
  const filename = path.split('/').pop() ?? '';
  return filename.replace(/\.flow\.md$/, '');
}

// Persist collapsed state in localStorage
function getCollapsed(key: string): boolean {
  try {
    return localStorage.getItem(key) === 'true';
  } catch {
    return false;
  }
}

function setCollapsedState(key: string, value: boolean) {
  try {
    localStorage.setItem(key, String(value));
  } catch {
    // Ignore storage errors
  }
}

export const WorkflowEditorView: React.FC<WorkflowEditorViewProps> = ({
  path,
}) => {
  const templateName = extractTemplateName(path);

  // --- Editor state (mirrors EditorPreviewSplit internals) ---
  const [layoutMode, setLayoutMode] = useState<LayoutMode>('source');
  const [editorContent, setEditorContent] = useState<string>('');
  const [lastSavedContent, setLastSavedContent] = useState<string>('');
  const [localMtime, setLocalMtime] = useState<number>(0);
  const [saveState, setSaveState] = useState<SaveState>('saved');
  const [contentLoaded, setContentLoaded] = useState(false);

  const editorRef = useRef<VaultEditorHandle>(null);
  const previewRef = useRef<HTMLDivElement>(null);
  const scrollSyncEnabled = useRef(true);
  const previewScrollTimeout = useRef<ReturnType<typeof setTimeout>>();

  // Panel collapse state
  const [listCollapsed, setListCollapsed] = useState(() =>
    getCollapsed('workflow-editor-list-collapsed'),
  );
  const [historyCollapsed, setHistoryCollapsed] = useState(() =>
    getCollapsed('workflow-editor-history-collapsed'),
  );

  // Dialog state (AC-14, AC-16)
  const [dryRunDialogOpen, setDryRunDialogOpen] = useState(false);
  const [dryRunResult, setDryRunResult] = useState<DryRunResult | null>(null);
  const [paramDialogOpen, setParamDialogOpen] = useState(false);
  const [paramList, setParamList] = useState<DryRunParameter[]>([]);

  // Panel refs for imperative collapse
  const listPanelRef = useRef<import('react-resizable-panels').ImperativePanelHandle>(null);
  const historyPanelRef = useRef<import('react-resizable-panels').ImperativePanelHandle>(null);

  // Fetch file content
  const { data, isLoading, error } = useVaultFile(path);
  const saveMutation = useSaveFile();
  const dryRunMutation = useDryRun();
  const runWorkflowMutation = useRunWorkflow();

  // Suggest cards
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

  // beforeunload protection
  useEffect(() => {
    if (!isDirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [isDirty]);

  // React Router navigation blocker
  const blocker = useBlocker(isDirty);

  // Handle content change from editor
  const handleEditorChange = useCallback((newContent: string) => {
    setEditorContent(newContent);
  }, []);

  // Suggest card handlers
  const handleSuggestAccept = useCallback(
    (card: SuggestCardType) => {
      setAcceptingCardId(card.id);
      acceptMutation.mutate(
        { id: card.id, filePath: path },
        {
          onSuccess: (response) => {
            setAcceptingCardId(null);
            const editor = editorRef.current;
            if (editor && response.text) {
              const currentContent = editor.getValue();
              const lines = currentContent.split('\n');
              const insertLine = Math.min(response.target_line, lines.length);
              if (response.target_line > lines.length) {
                toast.default('Original position changed — text inserted at end.');
              }
              lines.splice(insertLine, 0, response.text);
              const newContent = lines.join('\n');
              editor.setValue(newContent);
              setEditorContent(newContent);
            }
          },
          onError: () => setAcceptingCardId(null),
        },
      );
    },
    [acceptMutation, path],
  );

  const handleSuggestDismiss = useCallback(
    (card: SuggestCardType) => {
      setDismissingCardId(card.id);
      dismissMutation.mutate(
        { id: card.id, filePath: path },
        {
          onSuccess: () => setDismissingCardId(null),
          onError: () => setDismissingCardId(null),
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

  /**
   * AC-13: Auto-save before run. Returns a promise that resolves on success
   * or rejects on failure (409/network error). If not dirty, resolves immediately.
   */
  const autoSaveAsync = useCallback((): Promise<void> => {
    if (!isDirty) return Promise.resolve();

    return new Promise((resolve, reject) => {
      setSaveState('saving');
      saveMutation.mutate(
        { path, content: editorContent, mtime: localMtime },
        {
          onSuccess: (response) => {
            setLocalMtime(response.mtime);
            setLastSavedContent(editorContent);
            setSaveState('saved');
            resolve();
          },
          onError: (err) => {
            setSaveState('unsaved');
            toast.error('Save failed — fix conflicts before running.');
            reject(err);
          },
        },
      );
    });
  }, [isDirty, path, editorContent, localMtime, saveMutation]);

  /**
   * AC-13 + AC-14: Dry run handler.
   * Auto-saves first, then dispatches dry run and shows results dialog.
   */
  const handleDryRun = useCallback(async () => {
    try {
      await autoSaveAsync();
    } catch {
      return; // Save failed, abort
    }

    dryRunMutation.mutate(templateName, {
      onSuccess: (result) => {
        setDryRunResult(result);
        setDryRunDialogOpen(true);
      },
    });
  }, [autoSaveAsync, dryRunMutation, templateName]);

  /**
   * AC-13 + AC-15 + AC-16: Run now handler.
   * Auto-saves, validates via dry run, shows parameter dialog if needed.
   */
  const handleRunNow = useCallback(async () => {
    try {
      await autoSaveAsync();
    } catch {
      return; // Save failed, abort
    }

    // Dry run to check for parameters and validity
    dryRunMutation.mutate(templateName, {
      onSuccess: (result) => {
        if (!result.valid) {
          toast.error('Workflow validation failed — check dry run for details');
          setDryRunResult(result);
          setDryRunDialogOpen(true);
          return;
        }

        const requiredParams = result.parameters.filter((p) => p.required);
        if (requiredParams.length > 0) {
          // AC-16: Show parameter dialog before dispatch
          setParamList(result.parameters);
          setParamDialogOpen(true);
        } else {
          // No parameters needed, run directly
          runWorkflowMutation.mutate({ template_name: templateName });
        }
      },
    });
  }, [autoSaveAsync, dryRunMutation, runWorkflowMutation, templateName]);

  /** AC-16: Run with user-provided parameters from the dialog. */
  const handleRunWithParams = useCallback(
    (values: Record<string, string>) => {
      runWorkflowMutation.mutate(
        { template_name: templateName, parameters: values },
        {
          onSuccess: () => {
            setParamDialogOpen(false);
          },
        },
      );
    },
    [runWorkflowMutation, templateName],
  );

  // Collapse handlers
  const handleListCollapseToggle = useCallback(() => {
    const panel = listPanelRef.current;
    if (!panel) return;
    if (panel.isCollapsed()) {
      panel.expand();
    } else {
      panel.collapse();
    }
  }, []);

  const handleHistoryCollapseToggle = useCallback(() => {
    const panel = historyPanelRef.current;
    if (!panel) return;
    if (panel.isCollapsed()) {
      panel.expand();
    } else {
      panel.collapse();
    }
  }, []);

  const handleListCollapse = useCallback(() => {
    setListCollapsed(true);
    setCollapsedState('workflow-editor-list-collapsed', true);
  }, []);

  const handleListExpand = useCallback(() => {
    setListCollapsed(false);
    setCollapsedState('workflow-editor-list-collapsed', false);
  }, []);

  const handleHistoryCollapse = useCallback(() => {
    setHistoryCollapsed(true);
    setCollapsedState('workflow-editor-history-collapsed', true);
  }, []);

  const handleHistoryExpand = useCallback(() => {
    setHistoryCollapsed(false);
    setCollapsedState('workflow-editor-history-collapsed', false);
  }, []);

  // Scroll sync
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

  const handlePreviewScroll = useCallback(() => {
    scrollSyncEnabled.current = false;
    if (previewScrollTimeout.current) {
      clearTimeout(previewScrollTimeout.current);
    }
    previewScrollTimeout.current = setTimeout(() => {
      scrollSyncEnabled.current = true;
    }, 1000);
  }, []);

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
        <p className="text-lg font-medium">Workflow not found</p>
        <p className="text-sm mt-1 text-text-muted">
          The file{' '}
          <code className="px-1 py-0.5 bg-ui-element-bg rounded text-xs">
            {path}
          </code>{' '}
          could not be loaded.
        </p>
      </div>
    );
  }

  return (
    <>
      <PanelGroup
        direction="horizontal"
        aria-label="Workflow editor"
        className="h-full"
      >
        {/* Left: Workflow list panel */}
        <Panel
          ref={listPanelRef}
          defaultSize={18}
          minSize={12}
          collapsible
          collapsedSize={0}
          onCollapse={handleListCollapse}
          onExpand={handleListExpand}
          aria-label="Workflow list"
        >
          <WorkflowListPanel currentPath={path} />
        </Panel>

        {/* Resize handle + collapse toggle for list */}
        <PanelResizeHandle className="flex w-1.5 items-center justify-center bg-transparent hover:bg-brand-primary/20 transition-colors group relative">
          <div className="w-0.5 h-8 rounded-full bg-ui-border group-hover:bg-brand-primary transition-colors" />
          {listCollapsed && (
            <button
              onClick={handleListCollapseToggle}
              className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-full bg-ui-element-bg border border-ui-border rounded-l-md px-0.5 py-4 text-text-muted hover:text-text-primary transition-colors"
              aria-label="Expand workflow list"
            >
              <ChevronRightIcon className="h-3 w-3" />
              <span className="text-[9px] font-medium [writing-mode:vertical-lr] rotate-180 mt-1">
                Workflows
              </span>
            </button>
          )}
        </PanelResizeHandle>

        {/* Center: Editor area */}
        <Panel defaultSize={55} minSize={30}>
          <div className="flex flex-col h-full">
            {/* Header bar with workflow extension */}
            <FileHeaderBar
              vaultPath={path}
              saveState={saveState}
              onSave={handleSave}
              editorRef={editorRef}
              layoutToggle={
                <LayoutToggle mode={layoutMode} onChange={setLayoutMode} />
              }
              extension={
                <WorkflowHeaderExtension
                  editorContent={editorContent}
                  isDryRunning={dryRunMutation.isPending}
                  isRunning={runWorkflowMutation.isPending}
                  onDryRun={handleDryRun}
                  onRunNow={handleRunNow}
                />
              }
            />

            {/* Editor / Preview split */}
            <div className="flex-1 min-h-0">
              <PanelGroup
                direction="horizontal"
                aria-label="Editor split view"
              >
                {showEditor && (
                  <Panel
                    defaultSize={layoutMode === 'split' ? 50 : 100}
                    minSize={25}
                  >
                    <VaultEditor
                      ref={editorRef}
                      content={contentLoaded ? lastSavedContent : ''}
                      onChange={handleEditorChange}
                      onSave={handleSave}
                      language="markdown"
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
                  <Panel
                    defaultSize={layoutMode === 'split' ? 50 : 100}
                    minSize={25}
                  >
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
          </div>
        </Panel>

        {/* Resize handle + collapse toggle for history */}
        <PanelResizeHandle className="flex w-1.5 items-center justify-center bg-transparent hover:bg-brand-primary/20 transition-colors group relative">
          <div className="w-0.5 h-8 rounded-full bg-ui-border group-hover:bg-brand-primary transition-colors" />
          {historyCollapsed && (
            <button
              onClick={handleHistoryCollapseToggle}
              className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-full bg-ui-element-bg border border-ui-border rounded-r-md px-0.5 py-4 text-text-muted hover:text-text-primary transition-colors"
              aria-label="Expand run history"
            >
              <ChevronLeftIcon className="h-3 w-3" />
              <span className="text-[9px] font-medium [writing-mode:vertical-lr] mt-1">
                Run History
              </span>
            </button>
          )}
        </PanelResizeHandle>

        {/* Right: Run history panel */}
        <Panel
          ref={historyPanelRef}
          defaultSize={27}
          minSize={15}
          collapsible
          collapsedSize={0}
          onCollapse={handleHistoryCollapse}
          onExpand={handleHistoryExpand}
          aria-label="Run history"
        >
          <RunHistoryPanel templateName={templateName} />
        </Panel>
      </PanelGroup>

      {/* Navigation blocker dialog */}
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

      {/* Dry run results dialog (AC-14) */}
      <DryRunResultsDialog
        open={dryRunDialogOpen}
        onOpenChange={setDryRunDialogOpen}
        result={dryRunResult}
      />

      {/* Parameter input dialog (AC-16) */}
      <ParameterInputDialog
        open={paramDialogOpen}
        onOpenChange={setParamDialogOpen}
        parameters={paramList}
        onRun={handleRunWithParams}
        isRunning={runWorkflowMutation.isPending}
      />
    </>
  );
};
