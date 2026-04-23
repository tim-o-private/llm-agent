/**
 * SPEC-047 AC-09: Standalone markdown preview pane.
 *
 * Uses react-markdown + remark-gfm + remark-wiki-link. Wiki links render
 * as react-router `<Link>` elements for SPA navigation. YAML frontmatter
 * is extracted and rendered via FrontmatterBlock.
 *
 * This is NOT the assistant-ui markdown component — it's a standalone
 * pipeline for the file detail preview pane.
 */

import { forwardRef } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import wikiLinkPlugin from 'remark-wiki-link';
import { Link } from 'react-router-dom';
import { extractFrontmatter } from '@/lib/extractFrontmatter';
import { FrontmatterBlock } from './FrontmatterBlock';
import type { Components } from 'react-markdown';

interface MarkdownPreviewProps {
  content: string;
  className?: string;
}

/**
 * Custom anchor renderer: wiki links (href starts with /vault/) become
 * react-router Links; external links open in a new tab.
 */
const WikiLinkAnchor: Components['a'] = ({ href, children, ...props }) => {
  if (href?.startsWith('/vault/')) {
    return (
      <Link
        to={href}
        className="text-text-accent hover:underline"
        {...props}
      >
        {children}
      </Link>
    );
  }
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-text-accent hover:underline"
      {...props}
    >
      {children}
    </a>
  );
};

export const MarkdownPreview = forwardRef<HTMLDivElement, MarkdownPreviewProps>(
  ({ content, className }, ref) => {
    const { frontmatter, body } = extractFrontmatter(content);

    return (
      <div
        ref={ref}
        className={`h-full overflow-y-auto px-6 py-4 ${className ?? ''}`}
        aria-label="Rendered preview"
      >
        {frontmatter && <FrontmatterBlock content={frontmatter} />}
        <article className="prose prose-sm dark:prose-invert max-w-none text-text-primary">
          <Markdown
            remarkPlugins={[
              remarkGfm,
              [
                wikiLinkPlugin,
                {
                  pageResolver: (name: string) => [name],
                  hrefTemplate: (permalink: string) => `/vault/${permalink}.md`,
                  aliasDivider: '|',
                },
              ],
            ]}
            components={{
              a: WikiLinkAnchor,
            }}
          >
            {body}
          </Markdown>
        </article>
      </div>
    );
  },
);

MarkdownPreview.displayName = 'MarkdownPreview';
