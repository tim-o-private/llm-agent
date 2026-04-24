import React, { useState } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { CardShell } from './CardShell';
import type { ApprovalCard } from '@/api/types/today';
import { useApproveCard } from '@/api/hooks/useApprovalsHooks';

interface Props {
  card: Extract<ApprovalCard, { card_type: 'file_operation' }>;
}

export const FileOperationCard: React.FC<Props> = ({ card }) => {
  const approve = useApproveCard();
  const [confirmOpen, setConfirmOpen] = useState(false);

  const isDelete = card.payload.operation === 'delete';
  const opBadgeColor: 'red' | 'gray' = isDelete ? 'red' : 'gray';

  const runApprove = () => {
    approve.mutate({ id: card.id });
    setConfirmOpen(false);
  };

  return (
    <CardShell
      card={card}
      actions={
        <Button
          variant="solid"
          color={isDelete ? 'red' : undefined}
          size="2"
          onClick={() => (isDelete ? setConfirmOpen(true) : runApprove())}
          disabled={approve.isPending}
          aria-label="Approve"
        >
          Approve
        </Button>
      }
    >
      <div className="flex items-center gap-2">
        <span className="text-text-muted">Operation:</span>
        <Badge variant="solid" color={opBadgeColor}>
          {card.payload.operation}
        </Badge>
      </div>
      <div>
        <span className="text-text-muted">Source: </span>
        <span className="font-mono text-sm">{card.payload.source}</span>
      </div>
      {card.payload.target && (
        <div>
          <span className="text-text-muted">Target: </span>
          <span className="font-mono text-sm">{card.payload.target}</span>
        </div>
      )}

      <Modal
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Delete this file?"
        description={`This will permanently delete ${card.payload.source} from your vault.`}
      >
        <div className="flex justify-end gap-2">
          <Button variant="soft" size="2" onClick={() => setConfirmOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="solid"
            color="red"
            size="2"
            onClick={runApprove}
            disabled={approve.isPending}
          >
            Approve delete
          </Button>
        </div>
      </Modal>
    </CardShell>
  );
};

export default FileOperationCard;
