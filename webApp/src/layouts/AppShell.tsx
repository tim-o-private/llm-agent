import React from 'react';
import { Outlet } from 'react-router-dom';
import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
} from 'react-resizable-panels';
import TopBar from '@/components/navigation/TopBar';
import { ChatPanel } from '@/components/ChatPanel';
import { FileTree } from '@/components/vault/FileTree';
import { useChatStore } from '@/stores/useChatStore';
import { ActivityPanel } from '@/components/activity/ActivityPanel';
import { OverlayManager } from '@/components/overlays/OverlayManager';
import {
  ChatBubbleIcon,
  DoubleArrowRightIcon,
  DoubleArrowLeftIcon,
} from '@radix-ui/react-icons';

/**
 * SPEC-046 AC-01: Three-pane AppShell using react-resizable-panels.
 *
 * +--------------------------------------------------+
 * | TopBar (full width, above all panes)              |
 * +--------------------------------------------------+
 * | FileTree    | Content (Outlet)  | Chat (right)    |
 * | (15%,       | (fills remaining) | (25%,           |
 * |  collapsible)|                  |  collapsible)   |
 * +--------------------------------------------------+
 */
const AppShell: React.FC = () => {
  const isChatPanelOpen = useChatStore((state) => state.isChatPanelOpen);
  const toggleChatPanel = useChatStore((state) => state.toggleChatPanel);

  return (
    <>
      <div className="h-screen flex flex-col bg-gradient-to-br from-ui-bg via-ui-bg-glow to-ui-bg">
        {/* AC-04: TopBar spans full width above all panes */}
        <header className="relative z-20 flex-shrink-0 flex h-14 bg-ui-element-bg/80 backdrop-blur-glass shadow-elevated border-b border-ui-border-glow">
          <TopBar />
        </header>

        {/* Three-pane layout */}
        <PanelGroup direction="horizontal" className="flex-1">
          {/* AC-01/AC-02: Left pane — FileTree, collapsible */}
          <Panel
            defaultSize={15}
            minSize={3}
            collapsible
            collapsedSize={0}
            className="hidden md:block"
          >
            <div className="h-full overflow-hidden border-r border-ui-border">
              <FileTree />
            </div>
          </Panel>

          <PanelResizeHandle className="hidden md:flex w-1.5 items-center justify-center bg-transparent hover:bg-brand-primary/20 transition-colors group">
            <div className="w-0.5 h-8 rounded-full bg-ui-border group-hover:bg-brand-primary transition-colors" />
          </PanelResizeHandle>

          {/* Center pane — routed content */}
          <Panel defaultSize={isChatPanelOpen ? 60 : 85} minSize={30}>
            <main className="h-full overflow-y-auto focus:outline-none" tabIndex={-1}>
              <Outlet />
            </main>
          </Panel>

          {/* AC-03: Right pane — Chat rail, collapsible */}
          {isChatPanelOpen && (
            <>
              <PanelResizeHandle className="hidden md:flex w-1.5 items-center justify-center bg-transparent hover:bg-brand-primary/20 transition-colors group">
                <div className="w-0.5 h-8 rounded-full bg-ui-border group-hover:bg-brand-primary transition-colors" />
              </PanelResizeHandle>

              <Panel defaultSize={25} minSize={15} className="hidden md:block">
                <div className="h-full overflow-hidden">
                  <ChatPanel agentId={import.meta.env.VITE_DEFAULT_CHAT_AGENT_ID || 'assistant'} />
                </div>
              </Panel>
            </>
          )}
        </PanelGroup>

        {/* Chat toggle button — fixed on right edge */}
        <button
          onClick={toggleChatPanel}
          className={`hidden md:flex fixed top-1/2 -translate-y-1/2 right-0 z-30 flex-col items-center justify-center w-8 py-3 rounded-l-lg text-text-muted hover:text-text-electric bg-ui-element-bg/90 backdrop-blur-glass border border-r-0 border-ui-border-glow shadow-glow hover:shadow-electric transition-all duration-300 ${
            isChatPanelOpen ? 'text-text-accent' : ''
          }`}
          aria-label={isChatPanelOpen ? 'Close chat panel' : 'Open chat panel'}
        >
          {isChatPanelOpen ? (
            <DoubleArrowRightIcon className="h-4 w-4" />
          ) : (
            <>
              <ChatBubbleIcon className="h-4 w-4" />
              <span className="text-[10px] mt-1 writing-mode-vertical" style={{ writingMode: 'vertical-rl' }}>
                Chat
              </span>
            </>
          )}
        </button>

        {/* Mobile chat overlay */}
        {isChatPanelOpen && (
          <div className="md:hidden fixed inset-0 z-40 bg-ui-element-bg/95 backdrop-blur-glass">
            <button
              onClick={toggleChatPanel}
              className="absolute top-3 right-3 z-10 p-2 rounded-md text-text-muted hover:text-text-primary hover:bg-ui-interactive-bg-hover transition-colors"
              aria-label="Close chat panel"
            >
              <DoubleArrowLeftIcon className="h-5 w-5" />
            </button>
            <div className="h-full">
              <ChatPanel agentId={import.meta.env.VITE_DEFAULT_CHAT_AGENT_ID || 'assistant'} />
            </div>
          </div>
        )}
      </div>
      {/* SPEC-050: Activity log overlay panel */}
      <ActivityPanel />
      <OverlayManager />
    </>
  );
};

export default AppShell;
