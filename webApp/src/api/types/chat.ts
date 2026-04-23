/**
 * SPEC-049 Chat Surfaces — ChatScope discriminated union type.
 *
 * Canonical type definition for chat scope, referenced by all chat-related
 * modules: useChatScope hook, useChatStore, ChatPanel, ChatRail, AskChip,
 * CommandPalette, and the backend ChatRequest model.
 *
 * See SPEC-049 §"Scope Binding Contract" for the full resolution rules.
 */

export type ChatScopeType = 'global' | 'today' | 'folder' | 'file' | 'workflow';

export type ChatScope =
  | { type: 'global' }
  | { type: 'today' }
  | { type: 'folder'; path: string }
  | { type: 'file'; path: string }
  | { type: 'workflow'; path: string };
