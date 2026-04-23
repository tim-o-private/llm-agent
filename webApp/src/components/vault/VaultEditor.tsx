/**
 * SPEC-047 AC-02: Extensible CodeMirror 6 wrapper component.
 *
 * Uncontrolled internally — CodeMirror manages its own EditorState.
 * Parent passes initial `content`; changes reported via `onChange`.
 * Imperative handle exposes `getValue()`, `setValue()`, `getSelection()`, `focus()`.
 *
 * Extensions: lang-markdown with language-data, commands (Cmd+S),
 * search, lineWrapping, highlightActiveLine.
 *
 * SPEC-048 can compose this with workflow-specific extensions via
 * the `extensions` prop.
 */

import {
  useRef,
  useEffect,
  useImperativeHandle,
  forwardRef,
  useCallback,
} from 'react';
import { EditorState, type Extension } from '@codemirror/state';
import { EditorView, keymap, highlightActiveLine } from '@codemirror/view';
import { defaultKeymap, indentWithTab } from '@codemirror/commands';
import { markdown, markdownLanguage } from '@codemirror/lang-markdown';
import { yaml } from '@codemirror/lang-yaml';
import { languages } from '@codemirror/language-data';
import { search } from '@codemirror/search';

// --- Theme: reads Tailwind CSS variables for dark/light mode -----------------

const clarityTheme = EditorView.theme(
  {
    '&': {
      height: '100%',
      fontSize: '14px',
      fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
    },
    '.cm-content': {
      padding: '12px 16px',
      caretColor: 'var(--color-text-primary, #e4e4e7)',
    },
    '.cm-cursor': {
      borderLeftColor: 'var(--color-text-primary, #e4e4e7)',
    },
    '&.cm-focused .cm-selectionBackground, .cm-selectionBackground': {
      backgroundColor: 'var(--color-brand-primary-alpha, rgba(99, 102, 241, 0.25))',
    },
    '.cm-gutters': {
      backgroundColor: 'transparent',
      borderRight: 'none',
      color: 'var(--color-text-muted, #71717a)',
    },
    '.cm-activeLine': {
      backgroundColor: 'var(--color-ui-element-bg, rgba(39, 39, 42, 0.5))',
    },
    '.cm-activeLineGutter': {
      backgroundColor: 'transparent',
    },
  },
  { dark: true },
);

// --- Props & Handle ----------------------------------------------------------

export interface VaultEditorProps {
  content: string;
  onChange: (content: string) => void;
  onSave?: () => void;
  language?: 'markdown' | 'yaml';
  readOnly?: boolean;
  className?: string;
  /** Additional CM6 extensions (for SPEC-048 extensibility) */
  extensions?: Extension[];
  /** Filename for aria-label */
  filename?: string;
  /** Ref for scroll sync — exposes the EditorView's scrollDOM */
  onScroll?: (e: Event) => void;
}

export interface VaultEditorHandle {
  getValue(): string;
  setValue(content: string): void;
  getSelection(): string;
  focus(): void;
  getScrollDOM(): HTMLElement | null;
}

export const VaultEditor = forwardRef<VaultEditorHandle, VaultEditorProps>(
  (
    {
      content,
      onChange,
      onSave,
      language = 'markdown',
      readOnly = false,
      className,
      extensions: extraExtensions,
      filename,
      onScroll,
    },
    ref,
  ) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const viewRef = useRef<EditorView | null>(null);
    const onChangeRef = useRef(onChange);
    const onSaveRef = useRef(onSave);

    // Keep callback refs current without re-creating the editor
    useEffect(() => {
      onChangeRef.current = onChange;
    }, [onChange]);
    useEffect(() => {
      onSaveRef.current = onSave;
    }, [onSave]);

    // Imperative handle
    useImperativeHandle(
      ref,
      () => ({
        getValue() {
          return viewRef.current?.state.doc.toString() ?? '';
        },
        setValue(newContent: string) {
          const view = viewRef.current;
          if (!view) return;
          view.dispatch({
            changes: { from: 0, to: view.state.doc.length, insert: newContent },
          });
        },
        getSelection() {
          const view = viewRef.current;
          if (!view) return '';
          const { from, to } = view.state.selection.main;
          return view.state.doc.sliceString(from, to);
        },
        focus() {
          viewRef.current?.focus();
        },
        getScrollDOM() {
          return viewRef.current?.scrollDOM ?? null;
        },
      }),
      [],
    );

    // Build language extension
    const buildLangExtension = useCallback((): Extension => {
      if (language === 'yaml') return yaml();
      return markdown({ base: markdownLanguage, codeLanguages: languages });
    }, [language]);

    // Create editor on mount, destroy on unmount
    useEffect(() => {
      if (!containerRef.current) return;

      const saveKeymap = keymap.of([
        {
          key: 'Mod-s',
          run: () => {
            onSaveRef.current?.();
            return true;
          },
        },
      ]);

      const updateListener = EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          onChangeRef.current(update.state.doc.toString());
        }
      });

      const baseExtensions: Extension[] = [
        clarityTheme,
        buildLangExtension(),
        keymap.of([...defaultKeymap, indentWithTab]),
        saveKeymap,
        search(),
        EditorView.lineWrapping,
        highlightActiveLine(),
        updateListener,
        EditorView.editable.of(!readOnly),
        EditorState.readOnly.of(readOnly),
      ];

      if (extraExtensions) {
        baseExtensions.push(...extraExtensions);
      }

      const state = EditorState.create({
        doc: content,
        extensions: baseExtensions,
      });

      const view = new EditorView({
        state,
        parent: containerRef.current,
      });

      viewRef.current = view;

      return () => {
        view.destroy();
        viewRef.current = null;
      };
      // Only re-create editor when language or readOnly changes, not on every content change
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [language, readOnly, buildLangExtension]);

    // Scroll listener for scroll sync
    useEffect(() => {
      const scrollDOM = viewRef.current?.scrollDOM;
      if (!scrollDOM || !onScroll) return;

      scrollDOM.addEventListener('scroll', onScroll, { passive: true });
      return () => {
        scrollDOM.removeEventListener('scroll', onScroll);
      };
    }, [onScroll]);

    const ariaLabel = filename ? `Source editor for ${filename}` : 'Source editor';

    return (
      <div
        ref={containerRef}
        className={`h-full overflow-hidden ${className ?? ''}`}
        role="textbox"
        aria-label={ariaLabel}
        aria-multiline="true"
      />
    );
  },
);

VaultEditor.displayName = 'VaultEditor';
