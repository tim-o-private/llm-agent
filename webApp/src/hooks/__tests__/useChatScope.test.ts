import { renderHook } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useChatScope } from '../useChatScope';

// Mock react-router-dom's useLocation
const mockPathname = vi.fn<() => string>(() => '/');

vi.mock('react-router-dom', () => ({
  useLocation: () => ({ pathname: mockPathname() }),
}));

describe('useChatScope', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // --- Today scope ---

  it('returns today scope for root path "/"', () => {
    mockPathname.mockReturnValue('/');
    const { result } = renderHook(() => useChatScope());
    expect(result.current).toEqual({ type: 'today' });
  });

  it('returns today scope for "/vault/today.md"', () => {
    mockPathname.mockReturnValue('/vault/today.md');
    const { result } = renderHook(() => useChatScope());
    expect(result.current).toEqual({ type: 'today' });
  });

  // --- Workflow scope ---

  it('returns workflow scope for workflow files', () => {
    mockPathname.mockReturnValue('/vault/_workflows/morning-briefing.flow.md');
    const { result } = renderHook(() => useChatScope());
    expect(result.current).toEqual({
      type: 'workflow',
      path: '_workflows/morning-briefing.flow.md',
    });
  });

  it('returns workflow scope for nested workflow files', () => {
    mockPathname.mockReturnValue('/vault/_workflows/nested/deep.flow.md');
    const { result } = renderHook(() => useChatScope());
    // Does not start with _workflows/ directly after the nested part
    // but the relPath is _workflows/nested/deep.flow.md which starts with _workflows/
    expect(result.current).toEqual({
      type: 'workflow',
      path: '_workflows/nested/deep.flow.md',
    });
  });

  it('returns file scope for non-.flow.md files in _workflows', () => {
    mockPathname.mockReturnValue('/vault/_workflows/readme.md');
    const { result } = renderHook(() => useChatScope());
    expect(result.current).toEqual({
      type: 'file',
      path: '_workflows/readme.md',
    });
  });

  // --- Folder scope ---

  it('returns folder scope for paths ending with /', () => {
    mockPathname.mockReturnValue('/vault/projects/');
    const { result } = renderHook(() => useChatScope());
    expect(result.current).toEqual({ type: 'folder', path: 'projects/' });
  });

  it('returns folder scope for nested folders', () => {
    mockPathname.mockReturnValue('/vault/projects/clarity/docs/');
    const { result } = renderHook(() => useChatScope());
    expect(result.current).toEqual({
      type: 'folder',
      path: 'projects/clarity/docs/',
    });
  });

  // --- File scope ---

  it('returns file scope for vault files', () => {
    mockPathname.mockReturnValue('/vault/notes/standup.md');
    const { result } = renderHook(() => useChatScope());
    expect(result.current).toEqual({
      type: 'file',
      path: 'notes/standup.md',
    });
  });

  it('returns file scope for root-level vault files', () => {
    mockPathname.mockReturnValue('/vault/readme.md');
    const { result } = renderHook(() => useChatScope());
    expect(result.current).toEqual({ type: 'file', path: 'readme.md' });
  });

  it('returns file scope for deeply nested files', () => {
    mockPathname.mockReturnValue('/vault/a/b/c/d/file.txt');
    const { result } = renderHook(() => useChatScope());
    expect(result.current).toEqual({
      type: 'file',
      path: 'a/b/c/d/file.txt',
    });
  });

  // --- Global scope ---

  it('returns global scope for /settings', () => {
    mockPathname.mockReturnValue('/settings');
    const { result } = renderHook(() => useChatScope());
    expect(result.current).toEqual({ type: 'global' });
  });

  it('returns global scope for unknown paths', () => {
    mockPathname.mockReturnValue('/auth/login');
    const { result } = renderHook(() => useChatScope());
    expect(result.current).toEqual({ type: 'global' });
  });

  it('returns global scope for bare /vault/ path', () => {
    // /vault/ -> relPath is empty string, falls through to global
    mockPathname.mockReturnValue('/vault/');
    const { result } = renderHook(() => useChatScope());
    // relPath = "" after slicing "/vault/" — ends with "/" but relPath is ""
    // Actually relPath would be "" which doesn't end with "/" but has length 0
    // So this falls through to global
    expect(result.current).toEqual({ type: 'global' });
  });

  // --- Edge cases ---

  it('handles encoded characters in paths', () => {
    mockPathname.mockReturnValue('/vault/notes/my%20file.md');
    const { result } = renderHook(() => useChatScope());
    expect(result.current).toEqual({
      type: 'file',
      path: 'notes/my%20file.md',
    });
  });

  it('differentiates today.md from other vault paths', () => {
    // /vault/today.md is today scope, not file scope
    mockPathname.mockReturnValue('/vault/today.md');
    const { result } = renderHook(() => useChatScope());
    expect(result.current.type).toBe('today');
  });

  it('treats /vault/notes/today.md as file scope (not today)', () => {
    mockPathname.mockReturnValue('/vault/notes/today.md');
    const { result } = renderHook(() => useChatScope());
    expect(result.current).toEqual({
      type: 'file',
      path: 'notes/today.md',
    });
  });
});
