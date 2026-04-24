/**
 * SPEC-051 AC-14/AC-15: Transient confirmation banner after capture placement.
 *
 * Shows the confirmation string, a link to the target file, and a "Move"
 * button. Auto-dismisses after 10 seconds. "Move" opens an inline redirect
 * input with vault-path autocomplete.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { useRedirectCapture } from '@/api/hooks/useCaptureHooks';
import { useVaultTree } from '@/api/hooks/useVaultHooks';
import type { CaptureResponse } from '@/api/types/capture';
import type { TreeNode } from '@/api/types/vault';

const AUTO_DISMISS_MS = 10_000;

interface CaptureConfirmationProps {
  capture: CaptureResponse;
  onDismiss: () => void;
}

function flattenTree(nodes: TreeNode[]): string[] {
  const paths: string[] = [];
  for (const node of nodes) {
    if (node.type === 'file') {
      paths.push(node.path);
    }
    if (node.children) {
      paths.push(...flattenTree(node.children));
    }
  }
  return paths;
}

export const CaptureConfirmation: React.FC<CaptureConfirmationProps> = ({
  capture,
  onDismiss,
}) => {
  const [showRedirect, setShowRedirect] = useState(false);
  const [redirectInput, setRedirectInput] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const redirect = useRedirectCapture();
  const { data: treeData } = useVaultTree();

  // Auto-dismiss after 10 seconds.
  useEffect(() => {
    const timer = setTimeout(onDismiss, AUTO_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  // Focus redirect input when opened.
  useEffect(() => {
    if (showRedirect && inputRef.current) {
      inputRef.current.focus();
    }
  }, [showRedirect]);

  // Update suggestions when input changes.
  useEffect(() => {
    if (!redirectInput.trim() || !treeData?.tree) {
      setSuggestions([]);
      return;
    }
    const allPaths = flattenTree(treeData.tree);
    const query = redirectInput.toLowerCase();
    const matched = allPaths
      .filter((p) => p.toLowerCase().includes(query))
      .slice(0, 5);
    setSuggestions(matched);
  }, [redirectInput, treeData]);

  const handleRedirect = useCallback(
    (hint: string) => {
      if (!hint.trim()) return;
      redirect.mutate(
        { captureId: capture.capture_id, targetHint: hint },
        {
          onSuccess: () => {
            setShowRedirect(false);
            setRedirectInput('');
          },
        },
      );
    },
    [capture.capture_id, redirect],
  );

  const handleRedirectKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleRedirect(redirectInput);
    }
    if (e.key === 'Escape') {
      setShowRedirect(false);
      setRedirectInput('');
    }
  };

  const targetPath = capture.redirect?.new_target_path ?? capture.target_path;
  const confirmation = capture.confirmation ?? 'Capture placed';
  const vaultLink = targetPath ? `/vault/${targetPath}` : null;

  return (
    <div
      role="status"
      aria-label="Capture confirmation"
      className="mt-2 p-3 rounded-md border border-ui-border bg-ui-bg text-sm animate-in slide-in-from-top-1 duration-200"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex-1 min-w-0">
          <span className="text-text-primary">
            {confirmation}
          </span>
          {vaultLink && (
            <Link
              to={vaultLink}
              className="ml-1 text-accent-text hover:underline"
              onClick={onDismiss}
            >
              Open
            </Link>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {!showRedirect && !capture.redirect && (
            <Button
              variant="ghost"
              size="1"
              onClick={() => setShowRedirect(true)}
              aria-label="Move capture to different location"
            >
              Move
            </Button>
          )}
          <Button
            variant="ghost"
            size="1"
            onClick={onDismiss}
            aria-label="Dismiss confirmation"
          >
            Dismiss
          </Button>
        </div>
      </div>

      {showRedirect && (
        <div className="mt-2 space-y-1">
          <div className="relative">
            <input
              ref={inputRef}
              type="text"
              value={redirectInput}
              onChange={(e) => setRedirectInput(e.target.value)}
              onKeyDown={handleRedirectKeyDown}
              placeholder="Move to... (path or description)"
              aria-label="Redirect target"
              className="w-full px-2 py-1 text-sm border border-ui-border rounded bg-ui-bg text-text-primary placeholder:text-text-muted outline-none focus:ring-1 focus:ring-accent-border"
              disabled={redirect.isPending}
            />
            {suggestions.length > 0 && (
              <ul
                role="listbox"
                aria-label="Path suggestions"
                className="absolute left-0 right-0 top-full mt-1 border border-ui-border rounded bg-ui-bg shadow-elevated z-10 max-h-40 overflow-y-auto"
              >
                {suggestions.map((path) => (
                  <li
                    key={path}
                    role="option"
                    aria-selected={false}
                    className="px-2 py-1 text-xs text-text-secondary cursor-pointer hover:bg-ui-interactive-bg-hover"
                    onClick={() => {
                      setRedirectInput(path);
                      handleRedirect(path);
                    }}
                  >
                    {path}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-muted">Enter to move, Escape to cancel</span>
            <Button
              variant="soft"
              size="1"
              onClick={() => handleRedirect(redirectInput)}
              disabled={redirect.isPending || !redirectInput.trim()}
            >
              {redirect.isPending ? 'Moving...' : 'Move'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CaptureConfirmation;
