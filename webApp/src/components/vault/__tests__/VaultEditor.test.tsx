import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VaultEditor } from '../VaultEditor';

// CodeMirror 6 requires real DOM layout (getBoundingClientRect, etc.) that
// jsdom cannot provide. We can test: mounting, aria-label, readOnly prop.
// We do NOT attempt to simulate typing — that requires a real browser (Playwright).

// Mock CodeMirror modules so the component mounts in jsdom without errors.
// EditorView is the critical one — it needs a parent element but calls
// layout APIs that jsdom stubs as zeros.
const mockDestroy = vi.fn();
const mockFocus = vi.fn();

vi.mock('@codemirror/view', () => {
  class MockEditorView {
    state: { doc: { toString: () => string; length: number }; selection: { main: { from: number; to: number } } };
    scrollDOM: HTMLDivElement;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    constructor({ state, parent }: { state: any; parent: HTMLElement }) {
      this.state = state;
      this.scrollDOM = document.createElement('div');
      // Append a div to the parent so the container isn't empty
      parent.appendChild(document.createElement('div'));
    }

    dispatch() {}
    destroy() {
      mockDestroy();
    }
    focus() {
      mockFocus();
    }
  }

  return {
    EditorView: Object.assign(MockEditorView, {
      theme: () => [],
      lineWrapping: [],
      editable: { of: () => [] },
      updateListener: { of: () => [] },
    }),
    keymap: { of: () => [] },
    highlightActiveLine: () => [],
  };
});

vi.mock('@codemirror/state', () => ({
  EditorState: {
    create: ({ doc }: { doc: string }) => ({
      doc: {
        toString: () => doc,
        length: doc.length,
      },
      selection: { main: { from: 0, to: 0 } },
    }),
    readOnly: { of: () => [] },
  },
}));

vi.mock('@codemirror/commands', () => ({
  defaultKeymap: [],
  indentWithTab: { key: 'Tab', run: () => true },
}));

vi.mock('@codemirror/lang-markdown', () => ({
  markdown: () => [],
  markdownLanguage: {},
}));

vi.mock('@codemirror/lang-yaml', () => ({
  yaml: () => [],
}));

vi.mock('@codemirror/language-data', () => ({
  languages: [],
}));

vi.mock('@codemirror/search', () => ({
  search: () => [],
}));

describe('VaultEditor', () => {
  it('mounts without error', () => {
    const onChange = vi.fn();
    render(<VaultEditor content="# Hello" onChange={onChange} />);
    // The container div renders with role="textbox"
    const editor = screen.getByRole('textbox');
    expect(editor).toBeDefined();
  });

  it('has correct aria-label with filename', () => {
    const onChange = vi.fn();
    render(
      <VaultEditor
        content="# Hello"
        onChange={onChange}
        filename="meeting.md"
      />,
    );
    const editor = screen.getByRole('textbox', {
      name: 'Source editor for meeting.md',
    });
    expect(editor).toBeDefined();
  });

  it('has fallback aria-label without filename', () => {
    const onChange = vi.fn();
    render(<VaultEditor content="" onChange={onChange} />);
    const editor = screen.getByRole('textbox', { name: 'Source editor' });
    expect(editor).toBeDefined();
  });

  it('sets aria-multiline="true"', () => {
    const onChange = vi.fn();
    render(<VaultEditor content="" onChange={onChange} />);
    const editor = screen.getByRole('textbox');
    expect(editor.getAttribute('aria-multiline')).toBe('true');
  });

  it('destroys editor on unmount', () => {
    const onChange = vi.fn();
    const { unmount } = render(
      <VaultEditor content="# Test" onChange={onChange} />,
    );
    unmount();
    expect(mockDestroy).toHaveBeenCalled();
  });

  it('applies readOnly prop', () => {
    // With the mock, we verify the component mounts in readOnly mode
    // without error — actual read-only enforcement is a CodeMirror concern
    const onChange = vi.fn();
    render(
      <VaultEditor content="# Read only" onChange={onChange} readOnly />,
    );
    const editor = screen.getByRole('textbox');
    expect(editor).toBeDefined();
  });
});
