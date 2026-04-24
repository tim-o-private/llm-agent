/**
 * SPEC-045 Today surface — discriminated-union TS types matching the backend
 * payload shapes declared in the spec §"Technical Approach" §2 and §3.
 */

export interface EmailDraftPayload {
  to: string[];
  subject: string;
  body: string;
  thread_ref?: string;
}

export interface CalendarHoldPayload {
  title: string;
  start_at: string;
  end_at: string;
  source_ref?: string;
}

export interface OutreachPayload {
  recipient: string;
  message: string;
  channel: 'email' | 'telegram' | 'other';
}

export interface WorkflowProposalPayload {
  filename: string;
  body: string;
  pattern_observed: string;
}

export interface ConfigChangePayload {
  file_path: string;
  diff: string;
  summary: string;
}

export interface FileOperationPayload {
  operation: 'move' | 'rename' | 'delete';
  source: string;
  target?: string;
}

interface ApprovalCardBase {
  id: string;
  title: string;
  status: 'pending' | 'approved' | 'rejected';
  rationale?: string;
  source_ref?: string;
  decided_at?: string | null;
  decided_by?: string | null;
  decision_note?: string | null;
  created_at?: string;
  /** SPEC-052: execution tracking fields */
  executed_at?: string | null;
  execution_result?: Record<string, unknown> | null;
  execution_error?: string | null;
}

export type ApprovalCard =
  | (ApprovalCardBase & { card_type: 'email_draft'; payload: EmailDraftPayload })
  | (ApprovalCardBase & { card_type: 'calendar_hold'; payload: CalendarHoldPayload })
  | (ApprovalCardBase & { card_type: 'outreach'; payload: OutreachPayload })
  | (ApprovalCardBase & { card_type: 'workflow_proposal'; payload: WorkflowProposalPayload })
  | (ApprovalCardBase & { card_type: 'config_change'; payload: ConfigChangePayload })
  | (ApprovalCardBase & { card_type: 'file_operation'; payload: FileOperationPayload });

export type ApprovalCardType = ApprovalCard['card_type'];

export const APPROVAL_CARD_TYPES = [
  'email_draft',
  'calendar_hold',
  'outreach',
  'workflow_proposal',
  'config_change',
  'file_operation',
] as const satisfies readonly ApprovalCardType[];

export const APPROVAL_TYPE_LABEL: Record<ApprovalCardType, string> = {
  email_draft: 'Email draft',
  calendar_hold: 'Calendar hold',
  outreach: 'Outreach',
  workflow_proposal: 'Workflow proposal',
  config_change: 'Config change',
  file_operation: 'File operation',
};

export interface WikilinkItem {
  text: string;
  wikilink?: string;
}

export interface TodoItem {
  line_id: string;
  text: string;
  checked: boolean;
}

export interface NoteItem {
  created_at: string;
  text: string;
}

export interface AgentItem {
  text: string;
  link?: string;
}

export interface RecentEntry {
  path: string;
  updated_at: string;
}

export interface TodayResponse {
  date: string;
  header: { framing: string | null };
  your_day: WikilinkItem[];
  to_do: TodoItem[];
  notes: NoteItem[];
  agent: {
    running: AgentItem[];
    watching: AgentItem[];
    recent: AgentItem[];
    blocked: AgentItem[];
  };
  approvals: ApprovalCard[];
  recent: RecentEntry[];
  source_mtime?: number | null;
  unknown_sections?: string[];
}

export interface ApprovalsCount {
  count: number;
}

export interface WorkflowRun {
  id: string;
  template_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  completed_at?: string | null;
  started_at?: string | null;
}
