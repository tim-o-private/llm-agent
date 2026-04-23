/**
 * SPEC-047 AC-07: Segmented control for editor layout modes.
 *
 * Three buttons: Split, Source, Preview. Active button gets
 * `data-testid="layout-<mode>"`. Operable via arrow keys for
 * accessibility (AC-24).
 */

import React, { useCallback, useRef } from 'react';

export type LayoutMode = 'split' | 'source' | 'preview';

interface LayoutToggleProps {
  mode: LayoutMode;
  onChange: (mode: LayoutMode) => void;
}

const MODES: LayoutMode[] = ['split', 'source', 'preview'];
const LABELS: Record<LayoutMode, string> = {
  split: 'Split',
  source: 'Source',
  preview: 'Preview',
};

export const LayoutToggle: React.FC<LayoutToggleProps> = ({ mode, onChange }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const currentIndex = MODES.indexOf(mode);
      let nextIndex = -1;

      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        nextIndex = (currentIndex + 1) % MODES.length;
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        nextIndex = (currentIndex - 1 + MODES.length) % MODES.length;
      }

      if (nextIndex >= 0) {
        onChange(MODES[nextIndex]);
        // Focus the newly active button
        const buttons = containerRef.current?.querySelectorAll('button');
        (buttons?.[nextIndex] as HTMLButtonElement)?.focus();
      }
    },
    [mode, onChange],
  );

  return (
    <div
      ref={containerRef}
      role="radiogroup"
      aria-label="Editor layout"
      className="inline-flex rounded-md border border-ui-border bg-ui-element-bg overflow-hidden"
      onKeyDown={handleKeyDown}
    >
      {MODES.map((m) => {
        const isActive = m === mode;
        return (
          <button
            key={m}
            role="radio"
            aria-checked={isActive}
            tabIndex={isActive ? 0 : -1}
            data-testid={isActive ? `layout-${m}` : undefined}
            onClick={() => onChange(m)}
            className={`px-2.5 py-1 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-primary ${
              isActive
                ? 'bg-brand-primary/10 text-text-primary'
                : 'text-text-muted hover:text-text-primary hover:bg-ui-interactive-bg-hover'
            }`}
          >
            {LABELS[m]}
          </button>
        );
      })}
    </div>
  );
};
