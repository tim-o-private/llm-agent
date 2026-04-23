/**
 * SPEC-047 AC-16 / AC-17: Suggest card component.
 *
 * Rendered in the preview pane at the end of the body content.
 * Each card has a "Clarity suggests" label, body text, and Accept/Dismiss
 * buttons. Accept inserts the suggested text into the editor; dismiss
 * removes the card.
 */

import React from 'react';
import { CheckIcon, Cross2Icon } from '@radix-ui/react-icons';
import type { SuggestCard as SuggestCardType } from '@/api/types/fileDetail';

interface SuggestCardProps {
  card: SuggestCardType;
  onAccept: (card: SuggestCardType) => void;
  onDismiss: (card: SuggestCardType) => void;
  isAccepting?: boolean;
  isDismissing?: boolean;
}

export const SuggestCard: React.FC<SuggestCardProps> = ({
  card,
  onAccept,
  onDismiss,
  isAccepting = false,
  isDismissing = false,
}) => {
  const truncatedBody =
    card.body.length > 80 ? card.body.slice(0, 80) + '...' : card.body;
  const isLoading = isAccepting || isDismissing;

  return (
    <div
      role="region"
      aria-label={`Suggestion: ${truncatedBody}`}
      className="my-3 rounded-lg border border-brand-primary/30 bg-brand-primary/5 p-4"
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-semibold text-brand-primary uppercase tracking-wide">
          {card.label}
        </span>
        {card.target_line > 0 && (
          <span className="text-xs text-text-muted">
            Line {card.target_line}
          </span>
        )}
      </div>

      {/* Body */}
      <p className="text-sm text-text-secondary leading-relaxed mb-3">
        {card.body}
      </p>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {card.suggested_text && (
          <button
            onClick={() => onAccept(card)}
            disabled={isLoading}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md bg-brand-primary text-white hover:bg-brand-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Accept suggestion"
          >
            <CheckIcon className="w-3 h-3" />
            {isAccepting ? 'Accepting...' : 'Accept'}
          </button>
        )}
        <button
          onClick={() => onDismiss(card)}
          disabled={isLoading}
          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md text-text-muted hover:text-text-primary bg-ui-element-bg hover:bg-ui-interactive-bg-hover border border-ui-border transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Dismiss suggestion"
        >
          <Cross2Icon className="w-3 h-3" />
          {isDismissing ? 'Dismissing...' : 'Dismiss'}
        </button>
      </div>
    </div>
  );
};
