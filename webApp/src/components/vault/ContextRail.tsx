/**
 * SPEC-047 AC-13 / AC-14 / AC-15: AI context rail.
 *
 * Narrow panel rendered as a sub-panel within the center pane (NOT the chat
 * rail). Four sections: Summary, Citations, Linked by (backlinks), Activity.
 *
 * Collapsible via toggle button. Collapsed state persisted in localStorage.
 * Citations update reactively as the user types (debounced 500ms).
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeftIcon, ChevronRightIcon } from '@radix-ui/react-icons';
import { extractCitations, type Citation } from '@/lib/extractCitations';
import { extractFrontmatter } from '@/lib/extractFrontmatter';
import { useBacklinks, useFileContext } from '@/api/hooks/useFileDetailHooks';

const COLLAPSED_KEY = 'file-detail-context-rail-collapsed';

interface ContextRailProps {
  /** Vault-relative file path */
  path: string;
  /** Current editor content for reactive citation extraction */
  editorContent: string;
  /** Filename for aria-label */
  filename: string;
}

// --- Section component -------------------------------------------------------

const RailSection: React.FC<{
  name: string;
  title: string;
  children: React.ReactNode;
}> = ({ name, title, children }) => {
  const labelId = `context-${name}`;

  return (
    <section aria-labelledby={labelId} className="py-3 px-3">
      <h3
        id={labelId}
        className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-2"
      >
        {title}
      </h3>
      {children}
    </section>
  );
};

// --- Summary section ---------------------------------------------------------

function extractSummary(content: string): string | null {
  if (!content.trim()) return null;

  const { body } = extractFrontmatter(content);
  if (!body.trim()) return null;

  // Find the first non-empty paragraph
  const paragraphs = body.split(/\n\n+/);
  for (const para of paragraphs) {
    const trimmed = para.trim();
    // Skip headings, lists, code blocks, and empty lines
    if (
      !trimmed ||
      trimmed.startsWith('#') ||
      trimmed.startsWith('- ') ||
      trimmed.startsWith('* ') ||
      trimmed.startsWith('```') ||
      trimmed.startsWith('> ')
    ) {
      continue;
    }
    // Take up to 280 chars
    if (trimmed.length <= 280) return trimmed;
    return trimmed.slice(0, 277) + '...';
  }

  return null;
}

const SummarySection: React.FC<{ content: string }> = ({ content }) => {
  const summary = useMemo(() => extractSummary(content), [content]);

  return (
    <RailSection name="summary" title="Summary">
      {summary ? (
        <p className="text-sm text-text-secondary leading-relaxed">
          {summary}
        </p>
      ) : (
        <p className="text-xs text-text-muted italic">No summary available.</p>
      )}
    </RailSection>
  );
};

// --- Citations section -------------------------------------------------------

const CitationsSection: React.FC<{ citations: Citation[] }> = ({
  citations,
}) => {
  if (citations.length === 0) {
    return (
      <RailSection name="citations" title="Citations">
        <p className="text-xs text-text-muted italic">No outgoing links.</p>
      </RailSection>
    );
  }

  return (
    <RailSection name="citations" title="Citations">
      <ol className="space-y-1">
        {citations.map((cite) => (
          <li key={cite.target} className="flex items-center gap-2">
            <span className="flex-shrink-0 w-5 h-5 flex items-center justify-center text-[10px] font-bold rounded-full bg-brand-primary/10 text-brand-primary">
              {cite.index + 1}
            </span>
            <Link
              to={`/vault/${cite.target}.md`}
              className="text-xs font-mono text-text-accent hover:underline truncate"
              title={cite.display}
            >
              {cite.display}
            </Link>
          </li>
        ))}
      </ol>
    </RailSection>
  );
};

// --- Linked By section -------------------------------------------------------

const LinkedBySection: React.FC<{ path: string }> = ({ path }) => {
  const { data, isLoading } = useBacklinks(path);

  return (
    <RailSection name="linked-by" title="Linked by">
      {isLoading ? (
        <p className="text-xs text-text-muted">Loading...</p>
      ) : !data?.backlinks?.length ? (
        <p className="text-xs text-text-muted italic">No incoming links.</p>
      ) : (
        <ul className="space-y-1">
          {data.backlinks.map((bl) => (
            <li key={bl.path}>
              <Link
                to={`/vault/${bl.path}`}
                className="text-xs text-text-accent hover:underline truncate block"
                title={bl.path}
              >
                {bl.name}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </RailSection>
  );
};

// --- Activity section --------------------------------------------------------

const ActivitySection: React.FC<{ path: string }> = ({ path }) => {
  const { data, isLoading } = useFileContext(path);

  return (
    <RailSection name="activity" title="Activity">
      {isLoading ? (
        <p className="text-xs text-text-muted">Loading...</p>
      ) : !data?.activity?.length ? (
        <p className="text-xs text-text-muted italic">No recent activity.</p>
      ) : (
        <ul className="space-y-1.5">
          {data.activity.map((entry) => (
            <li key={entry.id} className="text-xs text-text-secondary">
              <span className="font-medium">{entry.actor}</span>{' '}
              {entry.action}
              <span className="block text-text-muted text-[10px]">
                {new Date(entry.created_at).toLocaleString()}
              </span>
            </li>
          ))}
        </ul>
      )}
    </RailSection>
  );
};

// --- Main ContextRail --------------------------------------------------------

export const ContextRail: React.FC<ContextRailProps> = ({
  path,
  editorContent,
  filename,
}) => {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(COLLAPSED_KEY) === 'true';
    } catch {
      return false;
    }
  });

  // Debounced citations (500ms)
  const [debouncedContent, setDebouncedContent] = useState(editorContent);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedContent(editorContent);
    }, 500);
    return () => clearTimeout(timer);
  }, [editorContent]);

  const citations = useMemo(
    () => extractCitations(debouncedContent),
    [debouncedContent],
  );

  // Persist collapsed state
  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(COLLAPSED_KEY, String(next));
      } catch {
        // storage full or unavailable — silently ignore
      }
      return next;
    });
  }, []);

  if (collapsed) {
    return (
      <div
        aria-label={`AI context for ${filename}`}
        className="flex flex-col items-center justify-start py-4 w-8 border-l border-ui-border bg-ui-element-bg/30 h-full cursor-pointer"
        onClick={toggleCollapsed}
        role="complementary"
      >
        <button
          onClick={(e) => {
            e.stopPropagation();
            toggleCollapsed();
          }}
          className="mb-2 text-text-muted hover:text-text-primary transition-colors"
          aria-label="Expand context rail"
        >
          <ChevronLeftIcon className="w-4 h-4" />
        </button>
        <span
          className="text-xs text-text-muted font-medium tracking-wider"
          style={{ writingMode: 'vertical-rl' }}
        >
          Context
        </span>
      </div>
    );
  }

  return (
    <div
      aria-label={`AI context for ${filename}`}
      role="complementary"
      className="h-full border-l border-ui-border bg-ui-element-bg/10 overflow-y-auto w-[220px] min-w-[180px] flex flex-col"
    >
      {/* Collapse toggle */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-ui-border flex-shrink-0">
        <span className="text-xs font-semibold text-text-muted uppercase tracking-wide">
          Context
        </span>
        <button
          onClick={toggleCollapsed}
          className="text-text-muted hover:text-text-primary transition-colors"
          aria-label="Collapse context rail"
        >
          <ChevronRightIcon className="w-4 h-4" />
        </button>
      </div>

      {/* Sections */}
      <div className="flex-1 overflow-y-auto divide-y divide-ui-border/50">
        <SummarySection content={editorContent} />
        <CitationsSection citations={citations} />
        <LinkedBySection path={path} />
        <ActivitySection path={path} />
      </div>
    </div>
  );
};
