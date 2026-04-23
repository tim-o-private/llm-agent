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
import { SuggestCard } from './SuggestCard';
import type { Components } from 'react-markdown';
import type { SuggestCard as SuggestCardType } from '@/api/types/fileDetail';

interface MarkdownPreviewProps {
  content: string;
  className?: string;
  /** Suggest cards to render at the end of the preview body */
  suggestCards?: SuggestCardType[];
  /** Called when user accepts a suggest card */
  onSuggestAccept?: (card: SuggestCardType) => void;
  /** Called when user dismisses a suggest card */
  onSuggestDismiss?: (card: SuggestCardType) => void;
  /** ID of the card currently being accepted */
  acceptingCardId?: string | null;
  /** ID of the card currently being dismissed */
  dismissingCardId?: string | null;
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
  (
    {
      content,
      className,
      suggestCards,
      onSuggestAccept,
      onSuggestDismiss,
      acceptingCardId,
      dismissingCardId,
    },
    ref,
  ) => {
    const { frontmatter, body } = extractFrontmatter(content);

    // Filter to pending cards, sorted by target_line (AC-16: end of preview, ordered)
    const pendingCards = suggestCards
      ?.filter((c) => c.status === 'pending')
      .sort((a, b) => a.target_line - b.target_line);

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

        {/* Suggest cards rendered at the end of the preview body (Stage 1) */}
        {pendingCards && pendingCards.length > 0 && (
          <div className="mt-6 space-y-2">
            {pendingCards.map((card) => (
              <SuggestCard
                key={card.id}
                card={card}
                onAccept={(c) => onSuggestAccept?.(c)}
                onDismiss={(c) => onSuggestDismiss?.(c)}
                isAccepting={acceptingCardId === card.id}
                isDismissing={dismissingCardId === card.id}
              />
            ))}
          </div>
        )}
      </div>
    );
  },
);

MarkdownPreview.displayName = 'MarkdownPreview';
