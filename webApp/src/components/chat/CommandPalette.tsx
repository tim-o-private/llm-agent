/**
 * SPEC-049 AC-08 through AC-15, AC-20, AC-23: Cmd+K command palette.
 * SPEC-051 AC-12: "Capture" action for smart text routing.
 *
 * Built on the `cmdk` library. Opens with Cmd+K (Mac) / Ctrl+K (Windows/Linux).
 * Captures scope at open time. Free-form input with suggestion groups.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Command } from 'cmdk';
import { useChatScope } from '@/hooks/useChatScope';
import { useChatStore } from '@/stores/useChatStore';
import { useCreateCapture } from '@/api/hooks/useCaptureHooks';
import { CaptureConfirmation } from '@/components/capture/CaptureConfirmation';
import type { ChatScope } from '@/api/types/chat';
import type { CaptureResponse } from '@/api/types/capture';
import { scopeLabel } from '@/lib/scopeLabel';

export const CommandPalette: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [captureResult, setCaptureResult] = useState<CaptureResponse | null>(null);
  const scopeAtOpen = useRef<ChatScope>({ type: 'global' });
  const currentScope = useChatScope();
  const createCapture = useCreateCapture();

  // Register global Cmd+K / Ctrl+K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        // Skip when focused inside the chat composer
        const active = document.activeElement as HTMLElement | null;
        if (active?.closest('[data-testid="composer"]')) {
          return;
        }
        e.preventDefault();
        scopeAtOpen.current = currentScope;
        setSearch('');
        setCaptureResult(null);
        setOpen(true);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [currentScope]);

  /** Send the query text as a chat message and open the rail. */
  const sendAsChat = useCallback(
    (query: string) => {
      if (!query.trim()) return;
      const store = useChatStore.getState();
      store.setScope(scopeAtOpen.current);
      store.setChatPanelOpen(true);
      store.setPendingPrompt(query.trim());
      setOpen(false);
    },
    [],
  );

  /** Capture the query text via the capture API. */
  const captureText = useCallback(
    (query: string) => {
      if (!query.trim()) return;
      const scope = scopeAtOpen.current;
      const context: Record<string, string> = {};
      if ('path' in scope && scope.path) {
        context.current_path = scope.path;
      }
      createCapture.mutate(
        { text: query.trim(), source: 'cmdk', context },
        {
          onSuccess: (capture) => {
            setCaptureResult(capture);
            setSearch('');
          },
        },
      );
    },
    [createCapture],
  );

  if (!open) return null;

  const label = scopeLabel(scopeAtOpen.current) ?? 'this page';

  return (
    <Command.Dialog
      open={open}
      onOpenChange={(isOpen) => {
        setOpen(isOpen);
        if (!isOpen) setCaptureResult(null);
      }}
      label="Command palette"
      className="fixed inset-0 z-50"
      shouldFilter={true}
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50"
        onClick={() => setOpen(false)}
        aria-hidden="true"
      />

      {/* Dialog body */}
      <div className="fixed inset-0 flex items-start justify-center pt-[20vh] pointer-events-none">
        <div className="relative w-full max-w-[640px] bg-ui-bg border border-ui-border rounded-lg shadow-elevated pointer-events-auto mx-4">
          <Command.Input
            value={search}
            onValueChange={setSearch}
            placeholder="Ask Clarity anything..."
            aria-label="Ask or search..."
            className="w-full px-4 py-3 text-base bg-transparent border-b border-ui-border outline-none text-text-primary placeholder:text-text-muted"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && search.trim()) {
                // If there are no visible items (cmdk filters to empty), send as chat
                const list = e.currentTarget
                  .closest('[cmdk-root]')
                  ?.querySelector('[cmdk-list]');
                const items = list?.querySelectorAll('[cmdk-item]');
                if (!items || items.length === 0) {
                  sendAsChat(search);
                }
              }
            }}
          />

          <Command.List className="max-h-[300px] overflow-y-auto p-2">
            <Command.Empty>
              <Command.Item
                onSelect={() => sendAsChat(search)}
                className="px-3 py-2 text-sm text-text-primary rounded-md cursor-pointer data-[selected=true]:bg-ui-interactive-bg-hover"
              >
                Ask: {search}
              </Command.Item>
            </Command.Empty>

            <Command.Group heading="Actions">
              <Command.Item
                value={`Capture ${search}`}
                onSelect={() => captureText(search)}
                className="px-3 py-2 text-sm text-text-primary rounded-md cursor-pointer data-[selected=true]:bg-ui-interactive-bg-hover"
              >
                Capture: {search || '...'}
              </Command.Item>
              <Command.Item
                value={`Chat about ${label}`}
                onSelect={() => sendAsChat(search || `Tell me about ${label}`)}
                className="px-3 py-2 text-sm text-text-primary rounded-md cursor-pointer data-[selected=true]:bg-ui-interactive-bg-hover"
              >
                Chat about {label}
              </Command.Item>
            </Command.Group>
          </Command.List>

          {/* Capture confirmation banner inside the palette */}
          {captureResult && captureResult.status === 'placed' && (
            <div className="border-t border-ui-border p-2">
              <CaptureConfirmation
                capture={captureResult}
                onDismiss={() => {
                  setCaptureResult(null);
                  setOpen(false);
                }}
              />
            </div>
          )}
        </div>
      </div>
    </Command.Dialog>
  );
};

export default CommandPalette;
