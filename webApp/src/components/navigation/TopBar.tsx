import React, { useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { UserMenu } from '@/components/UserMenu';
import ThemeToggle from '@/components/ui/ThemeToggle';
import { useChatStore } from '@/stores/useChatStore';
import { ChatBubbleIcon } from '@radix-ui/react-icons';
import { ApprovalsBadge } from '@/components/today/ApprovalsBadge';
import { Breadcrumb } from '@/components/vault/Breadcrumb';

/**
 * AC-04: TopBar spans the full width above all three panes.
 * Contains: breadcrumb (replaces "Clarity" logo text), ApprovalsBadge, ThemeToggle, UserMenu.
 */
const TopBar: React.FC = () => {
  const toggleChatPanel = useChatStore((state) => state.toggleChatPanel);
  const navigate = useNavigate();
  const location = useLocation();

  const jumpToApprovals = () => navigate('/#today-approvals');

  // Derive vault path from current route for breadcrumb
  const vaultPath = useMemo(() => {
    const path = location.pathname;
    if (path === '/' || path === '/today') return '';
    if (path.startsWith('/vault/')) return path.replace('/vault/', '');
    if (path === '/settings') return 'settings';
    return '';
  }, [location.pathname]);

  return (
    <div className="flex-1 px-2 sm:px-4 flex justify-between items-center h-full min-w-0">
      {/* Left section - Breadcrumb replaces logo (AC-04, AC-05) */}
      <div className="flex items-center min-w-0">
        <div className="px-2 sm:px-3">
          <Breadcrumb vaultPath={vaultPath} />
        </div>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Right section */}
      <div className="flex items-center space-x-2 sm:space-x-3 flex-shrink-0">
        <ApprovalsBadge onJump={jumpToApprovals} />
        {/* SPEC-049 AC-08: Cmd+K shortcut hint, desktop only */}
        <kbd className="hidden lg:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-mono text-text-muted bg-ui-element-bg border border-ui-border rounded">
          {typeof navigator !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.platform)
            ? '⌘'
            : 'Ctrl+'}
          K
        </kbd>
        <ThemeToggle />
        {/* Mobile chat toggle - visible only on mobile (desktop uses AppShell button) */}
        <button
          onClick={toggleChatPanel}
          className="md:hidden p-2 rounded-md text-text-muted hover:text-text-primary hover:bg-ui-interactive-bg-hover transition-colors"
          aria-label="Toggle chat"
        >
          <ChatBubbleIcon className="h-5 w-5" />
        </button>
        <UserMenu />
      </div>
    </div>
  );
};

export default TopBar;
