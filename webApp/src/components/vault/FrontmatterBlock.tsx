/**
 * SPEC-047 AC-09 / AC-18: Styled block for YAML frontmatter in the preview pane.
 *
 * Renders raw YAML in JetBrains Mono (font-mono), muted background,
 * with a "Frontmatter" label.
 */

import React from 'react';

interface FrontmatterBlockProps {
  content: string;
}

export const FrontmatterBlock: React.FC<FrontmatterBlockProps> = ({ content }) => {
  return (
    <div className="mb-4 rounded-md border border-ui-border bg-ui-element-bg/50 overflow-hidden">
      <div className="px-3 py-1.5 border-b border-ui-border bg-ui-element-bg">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
          Frontmatter
        </span>
      </div>
      <pre className="px-3 py-2 text-xs font-mono text-text-secondary whitespace-pre-wrap overflow-x-auto leading-relaxed">
        {content}
      </pre>
    </div>
  );
};
