/**
 * SPEC-049 — derives ChatScope from the current route.
 *
 * Single source of truth for scope derivation. No component should compute
 * scope independently. See SPEC-049 §"Scope resolution rules" table.
 */

import { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import type { ChatScope } from '@/api/types/chat';

export function useChatScope(): ChatScope {
  const { pathname } = useLocation();

  return useMemo(() => {
    // Today surface
    if (pathname === '/' || pathname === '/vault/today.md') {
      return { type: 'today' };
    }

    // Vault paths
    if (pathname.startsWith('/vault/')) {
      const relPath = pathname.slice('/vault/'.length);

      // Workflow files — must check before generic file match
      if (relPath.startsWith('_workflows/') && relPath.endsWith('.flow.md')) {
        return { type: 'workflow', path: relPath };
      }

      // Folder (ends with /)
      if (relPath.endsWith('/')) {
        return { type: 'folder', path: relPath };
      }

      // File (any other non-empty vault path)
      if (relPath.length > 0) {
        return { type: 'file', path: relPath };
      }
    }

    // Default fallback — settings, auth pages, etc.
    return { type: 'global' };
  }, [pathname]);
}
