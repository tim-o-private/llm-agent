/**
 * SPEC-047 AC-11 / AC-12: File header toolbar.
 *
 * Contains breadcrumb, save-status indicator, layout toggle, and action
 * chips (History, Share, Ask). Accepts an optional `extension` prop
 * for SPEC-048 to inject workflow-specific controls.
 */

import React, { useCallback } from 'react';
import { Breadcrumb } from './Breadcrumb';
import { SaveStatus, type SaveState } from './SaveStatus';
import type { VaultEditorHandle } from './VaultEditor';
import { useChatStore } from '@/stores/useChatStore';
import * as Tooltip from '@radix-ui/react-tooltip';
import {
  ChatBubbleIcon,
  CounterClockwiseClockIcon,
  Share1Icon,
} from '@radix-ui/react-icons';

interface FileHeaderBarProps {
  vaultPath: string;
  saveState: SaveState;
  onSave: () => void;
  editorRef: React.RefObject<VaultEditorHandle | null>;
  layoutToggle: React.ReactNode;
  /** Slot for SPEC-048 workflow-specific controls */
  extension?: React.ReactNode;
}

const DisabledChip: React.FC<{
  icon: React.ReactNode;
  label: string;
  tooltip: string;
  testId: string;
}> = ({ icon, label, tooltip, testId }) => (
  <Tooltip.Provider delayDuration={300}>
    <Tooltip.Root>
      <Tooltip.Trigger asChild>
        <button
          disabled
          data-testid={testId}
          className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-text-muted bg-ui-element-bg border border-ui-border rounded-md opacity-50 cursor-not-allowed"
          aria-label={label}
        >
          {icon}
          {label}
        </button>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          side="bottom"
          sideOffset={4}
          className="z-50 rounded-md bg-ui-element-bg border border-ui-border px-2 py-1 text-xs text-text-secondary shadow-md"
        >
          {tooltip}
          <Tooltip.Arrow className="fill-ui-element-bg" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  </Tooltip.Provider>
);

export const FileHeaderBar: React.FC<FileHeaderBarProps> = ({
  vaultPath,
  saveState,
  onSave,
  editorRef,
  layoutToggle,
  extension,
}) => {
  /**
   * AC-12: "Ask" chip opens chat rail scoped to current file.
   * If there is selected text in the editor, include it as quoted context.
   * We handle this directly instead of using AskChip because we need to
   * capture the selection at click time, not render time.
   */
  const handleAskClick = useCallback(() => {
    const store = useChatStore.getState();
    store.setScope({ type: 'file', path: vaultPath });
    store.setChatPanelOpen(true);

    const selection = editorRef.current?.getSelection();
    if (selection) {
      const quoted = `> ${selection.split('\n').join('\n> ')}\n\n`;
      store.setPendingPrompt(quoted);
    }
  }, [vaultPath, editorRef]);

  return (
    <div
      role="toolbar"
      aria-label="File actions"
      className="flex items-center gap-3 px-4 py-2 border-b border-ui-border bg-ui-element-bg/30 flex-shrink-0"
    >
      {/* Left: Breadcrumb + SaveStatus */}
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <Breadcrumb vaultPath={vaultPath} />
        <SaveStatus state={saveState} />
        {saveState === 'unsaved' && (
          <button
            onClick={onSave}
            className="px-2 py-0.5 text-xs font-medium rounded-md bg-brand-primary text-white hover:bg-brand-primary/90 transition-colors"
          >
            Save
          </button>
        )}
      </div>

      {/* Center: Layout toggle */}
      <div className="flex-shrink-0">{layoutToggle}</div>

      {/* Right: Action chips */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {extension}
        <DisabledChip
          icon={<CounterClockwiseClockIcon className="w-3 h-3" />}
          label="History"
          tooltip="Coming soon"
          testId="chip-history"
        />
        <DisabledChip
          icon={<Share1Icon className="w-3 h-3" />}
          label="Share"
          tooltip="Coming soon"
          testId="chip-share"
        />
        <button
          onClick={handleAskClick}
          data-testid="chip-ask"
          className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-text-muted hover:text-text-primary bg-ui-element-bg hover:bg-ui-interactive-bg-hover border border-ui-border rounded-md transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-primary"
          aria-label="Ask about this file"
        >
          <ChatBubbleIcon className="w-3 h-3" />
          Ask
        </button>
      </div>
    </div>
  );
};
