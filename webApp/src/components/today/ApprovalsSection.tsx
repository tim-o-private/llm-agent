import React from 'react';
import type { ApprovalCard } from '@/api/types/today';
import { EmailDraftCard } from './approvals/EmailDraftCard';
import { CalendarHoldCard } from './approvals/CalendarHoldCard';
import { OutreachCard } from './approvals/OutreachCard';
import { WorkflowProposalCard } from './approvals/WorkflowProposalCard';
import { ConfigChangeCard } from './approvals/ConfigChangeCard';
import { FileOperationCard } from './approvals/FileOperationCard';

const HEADING_ID = 'today-approvals-heading';

const CardRenderer: React.FC<{ card: ApprovalCard }> = ({ card }) => {
  switch (card.card_type) {
    case 'email_draft':
      return <EmailDraftCard card={card} />;
    case 'calendar_hold':
      return <CalendarHoldCard card={card} />;
    case 'outreach':
      return <OutreachCard card={card} />;
    case 'workflow_proposal':
      return <WorkflowProposalCard card={card} />;
    case 'config_change':
      return <ConfigChangeCard card={card} />;
    case 'file_operation':
      return <FileOperationCard card={card} />;
    default:
      return null;
  }
};

export const ApprovalsSection: React.FC<{ cards: ApprovalCard[] }> = ({ cards }) => (
  <section aria-labelledby={HEADING_ID} id="today-approvals" className="py-6">
    <h2 id={HEADING_ID} className="text-lg font-medium text-text-secondary tracking-tight mb-3">
      Approvals
    </h2>
    {cards.length === 0 ? (
      <p className="text-sm text-text-muted italic">Nothing awaiting approval.</p>
    ) : (
      <div className="space-y-3" aria-live="polite">
        {cards.map((card) => (
          <CardRenderer key={card.id} card={card} />
        ))}
      </div>
    )}
  </section>
);

export default ApprovalsSection;
