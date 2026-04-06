# SPEC-037: Initial Workflows + Human-in-the-Loop

> **Status:** Draft
> **Author:** Claude (Spec Writer)
> **Created:** 2026-04-06
> **Updated:** 2026-04-06
> **PRD:** Architecture Proposal (Phase 2, Items 8–9)
> **Architecture:** `docs/product/ARCHITECTURE-PROPOSAL-next-gen.md`, Sections Q4, Q7

## Goal

Define the first three workflow templates and integrate human-in-the-loop approval via the Workflow Engine (SPEC-036). These workflows replace existing single-shot scheduled executions with multi-step, checkpointed graph workflows that pause for user approval when needed.

The three workflows:
1. **email-triage** — scheduled email processing: read inbox, categorize, surface important items
2. **morning-briefing** — compose daily briefing from calendar + tasks + email + observations
3. **draft-reply** — find thread → compose draft in user's voice → present for approval → send

The user never sees "workflow" or "graph." They see briefings, drafts, and approval requests in their normal chat. The infrastructure is invisible — the product is the behavior.

### Relationship to Existing Specs

| Existing Spec | Relationship |
|--------------|-------------|
| SPEC-028 (Morning & Evening Briefings) | SPEC-028 implemented briefings as single-shot `ScheduledExecutionService` calls with a synthesis prompt. This spec replaces that with a multi-step workflow: separate fetch, categorize, compose, and deliver steps with checkpointing. SPEC-028's `BriefingService`, `user_preferences`, and `deferred_observations` tables are reused. |
| SPEC-029 (Draft Reply) | SPEC-029 implemented draft reply as two tools (`draft_email_reply`, `send_email_reply`) with conversational editing. This spec wraps that into a workflow template so the agent can dispatch it as a multi-step process. The existing tools become capabilities the workflow steps call via the gateway. |
| SPEC-036 (Workflow Engine) | Provides the engine, template parser, builder, checkpointer, run manager, progress streaming, and human gate infrastructure that this spec's templates run on. |
| SPEC-034 (Capability Gateway) | Workflow steps call tools (search_gmail, get_gmail, create_memories, etc.) through the gateway. |
| SPEC-035 (Config Service) | Templates are stored in Supabase Storage under `system/workflows/`. |

## Dependencies

| Dependency | What It Provides | Status |
|-----------|-----------------|--------|
| SPEC-036 (Workflow Engine) | Template parser, AnthropicEngine, GraphBuilder, RunManager, checkpointer, progress streaming, human gates | Draft |
| SPEC-034 (Capability Gateway) | `gateway.execute()` for tool calls within workflow steps | Draft |
| SPEC-035 (Config Service) | Template storage at `system/workflows/` | Draft |
| SPEC-028 (Briefings) | `BriefingService`, `user_preferences`, `deferred_observations`, `briefing_prompts.py` | Complete |
| SPEC-029 (Draft Reply) | `draft_email_reply`, `send_email_reply` tools / capability executors | Complete |
| SPEC-025 (Notifications) | `NotificationService` for delivering briefings and approval requests | Complete |
| SPEC-026 (Job Queue) | `JobService` for scheduling workflow runs | Complete |
| Existing tools | `search_gmail`, `get_gmail`, `search_calendar`, `get_calendar_event`, `get_tasks`, `create_memories`, `search_memories` | Complete |

## Acceptance Criteria

### FU-1: email-triage Workflow Template

- [ ] **AC-01:** A workflow template file `email-triage.md` exists at `system/workflows/email-triage.md` in the config bucket (Supabase Storage). It follows the HQ graph template format (Markdown with YAML frontmatter). [A2]
- [ ] **AC-02:** The template defines three steps: `fetch-emails` (search recent inbox), `categorize` (classify each email by urgency/action-needed), `summarize` (compose triage summary and store important items as memories). All steps have `gate_policy: none` — email triage runs autonomously without human gates. [A1]
- [ ] **AC-03:** The `fetch-emails` step uses tools `[search_gmail, get_gmail]` and accepts parameters: `hours_back` (default 12), `max_emails` (default 20). It searches all connected Gmail accounts for recent unread emails, reads the top N by recency, and outputs structured email data (sender, subject, snippet, date, message_id). [A6]
- [ ] **AC-04:** The `categorize` step receives the fetched emails from `step_outputs["fetch-emails"]` and classifies each into one of four categories: `urgent` (needs response within hours), `actionable` (needs response but not time-sensitive), `informational` (worth knowing, no action needed), `ignorable` (newsletters, automated, spam-like). It outputs a categorized list with category, reasoning, and suggested action for each email. No tools needed — pure LLM classification. [A14]
- [ ] **AC-05:** The `summarize` step receives the categorized emails and composes a triage summary: urgent items first with suggested next actions, actionable items with brief context, informational items as one-line mentions. It uses `[create_memories]` to store urgent/actionable items as memories (entity=`email_triage`, tags=`["email", "triage"]`) for future reference. Output is the formatted triage summary text. [A6]
- [ ] **AC-06:** The workflow completion event (SPEC-036 AC-26) contains the triage summary. The ConversationHandler presents it to the user as a chat message, not a notification card. [A1]
- [ ] **AC-07:** A seed migration uploads the template to `system/workflows/email-triage.md` in the config bucket. [A3]

### FU-2: morning-briefing Workflow Template

- [ ] **AC-08:** A workflow template file `morning-briefing.md` exists at `system/workflows/morning-briefing.md` in the config bucket. [A2]
- [ ] **AC-09:** The template defines three steps: `gather-context` (fetch calendar, tasks, email, observations in parallel), `compose-briefing` (synthesize into opinionated 3-5 item briefing), `deliver` (send via notification service). All steps have `gate_policy: none` — morning briefings are autonomous. [A1]
- [ ] **AC-10:** The `gather-context` step uses tools `[search_calendar, get_tasks, search_gmail, search_memories]` and accepts parameters: `timezone` (required), `briefing_sections` (default: `{"calendar": true, "tasks": true, "email": true, "observations": true}`). It fetches: today's calendar events, active/overdue tasks with due dates, recent unread emails (last 12 hours), and unconsumed deferred observations from memory. Outputs structured context data per section. [A6]
- [ ] **AC-11:** The `compose-briefing` step receives gathered context and composes a briefing following SPEC-028's synthesis prompt guidelines: 300-word limit, 3-5 items ordered by importance (not by category), opinionated framing ("You should..." not "There are..."). No tools needed — pure LLM generation. The step's system prompt includes the user's standing instructions for personalization context. [A14]
- [ ] **AC-12:** The `deliver` step sends the composed briefing via `NotificationService.notify_user()` with `type="notify"`, `category="briefing"`. On Telegram, the body is post-processed via `format_for_telegram()` (SPEC-028 pattern). The step also marks consumed deferred observations (same as SPEC-028 AC-10). Uses no LLM call — this is a pure service call node, not an engine step. [A7]
- [ ] **AC-13:** The morning briefing workflow integrates with SPEC-028's scheduling infrastructure. The existing `handle_morning_briefing` job handler in `job_handlers.py` is updated to dispatch the workflow via `WorkflowRunManager.start_run("morning-briefing", params)` instead of directly calling `BriefingService.generate_morning_briefing()`. The self-scheduling pattern (next occurrence) is preserved. [A11]
- [ ] **AC-14:** The evening briefing uses the same workflow engine but with a different template `evening-briefing.md` that gathers: tasks completed today, tasks still open, pending replies, and tomorrow's calendar. Follows the same three-step pattern as morning briefing. [A1]
- [ ] **AC-15:** A seed migration uploads both templates to the config bucket. [A3]

### FU-3: draft-reply Workflow Template

- [ ] **AC-16:** A workflow template file `draft-reply.md` exists at `system/workflows/draft-reply.md` in the config bucket. [A2]
- [ ] **AC-17:** The template defines four steps: `fetch-context` (get original email + writing style), `compose-draft` (generate reply in user's voice), `present-for-approval` (human gate — show draft, wait for approve/revise/cancel), `send` (send approved draft via Gmail). [A1]
- [ ] **AC-18:** The `fetch-context` step uses tools `[get_gmail, search_memories]` and accepts parameters: `message_id` (required), `account` (required), `instructions` (optional — user guidance like "tell them I agree"). It fetches the original email content and the user's writing style profile (entity=`writing_style`, tags=`["communication", "style"]`). If no writing style exists, it includes a note about using neutral professional tone. Outputs structured context: original email + writing style + instructions. [A6]
- [ ] **AC-19:** The `compose-draft` step receives the fetched context and generates a reply draft in the user's voice. The step's system prompt instructs: match the user's greeting/signoff style, match their typical message length, use their vocabulary patterns. No tools needed — pure LLM generation. Output is the formatted draft with subject line, recipient, and body. [A14]
- [ ] **AC-20:** The `present-for-approval` step has `gate_policy: "human-required"`. The gate node presents the draft to the user via a pending action with `tool_name: "workflow_gate"`, `tool_args: {run_id, step_name: "present-for-approval", output_preview: <draft text>}`, and `context: {template_name: "draft-reply", original_subject, original_sender, draft_body}`. The pending action renders as a styled email preview (same format as SPEC-029 AC-19's `ApprovalInlineMessage` for `send_email_reply`). [A12]
- [ ] **AC-21:** The approval response supports three actions: `approve` (proceed to send), `reject` (cancel the workflow), and `revise` (restart from compose-draft with new instructions). The `revise` action includes user feedback text that is injected into the compose-draft step's parameters on re-execution. [A12]
- [ ] **AC-22:** The `send` step uses tools `[send_email_reply]` to send the approved draft. It calls `send_email_reply` with the `message_id`, `account`, and approved `body` from the gate approval. Output is the send confirmation (message_id, thread_id). [A6]
- [ ] **AC-23:** If the user initiates draft-reply conversationally ("reply to Mike's email"), the agent calls `dispatch_workflow("draft-reply", {message_id, account, instructions})`. If the user directly calls `draft_email_reply` (existing tool), it still works via the old conversational flow (backward compatibility). [A7, A14]
- [ ] **AC-24:** A seed migration uploads the template to the config bucket. [A3]

### FU-4: Human Gate Integration (Cross-Cutting)

- [ ] **AC-25:** The `ApprovalInlineMessage` component (frontend, SPEC-029) is extended to detect `tool_name === "workflow_gate"` pending actions. For `draft-reply` gates, it renders the same styled email preview as `send_email_reply` approvals (To, Subject, Body card). For other workflow gates, it renders a generic step output preview with approve/reject buttons. [F1]
- [ ] **AC-26:** Telegram inline approval buttons work for workflow gates. The notification includes the step output preview (truncated to 4096 chars for Telegram) and inline approve/reject buttons via `InlineKeyboardMarkup`. [A7]
- [ ] **AC-27:** The `revise` action for draft-reply gates is supported on web only (Telegram shows approve/reject). On web, the approval card includes an optional text input for revision instructions alongside approve/reject buttons. [F1]
- [ ] **AC-28:** The `WorkflowRunManager.resume_run()` (SPEC-036 AC-24) handles the `revise` action by: resetting the graph state to before the `compose-draft` step, injecting the revision instructions into the step parameters, and re-executing from `compose-draft`. The checkpointer enables this rollback. [A14]

### FU-5: Scheduling + Migration

- [ ] **AC-29:** The existing SPEC-028 `handle_morning_briefing` job handler is updated to use `WorkflowRunManager.start_run("morning-briefing", {timezone, briefing_sections})` instead of `BriefingService.generate_morning_briefing()`. The self-scheduling logic (compute next occurrence, create next job) remains in the handler, not in the workflow. [A1]
- [ ] **AC-30:** The existing SPEC-028 `handle_evening_briefing` job handler is updated similarly to use `WorkflowRunManager.start_run("evening-briefing", {...})`. [A1]
- [ ] **AC-31:** Email triage is scheduleable: a `handle_email_triage` handler is added for `job_type = "email_triage"`. It calls `WorkflowRunManager.start_run("email-triage", {hours_back, max_emails})` and self-schedules the next run. The schedule is configurable via `user_preferences` — new columns `email_triage_enabled` (BOOLEAN DEFAULT false) and `email_triage_interval_hours` (INTEGER DEFAULT 6). [A1]
- [ ] **AC-32:** The `ManageBriefingPreferencesTool` (SPEC-028 AC-20) is extended with an `email_triage` section: `action: "update"` with `preferences: {email_triage_enabled, email_triage_interval_hours}` creates/cancels triage jobs. [A6]
- [ ] **AC-33:** A migration adds `email_triage_enabled` and `email_triage_interval_hours` columns to `user_preferences`. [A3]

### FU-6: Step Prompt Engineering

- [ ] **AC-34:** Each workflow step that uses the AnthropicEngine has a carefully engineered system prompt stored alongside the template. System prompts are read from `system/workflows/prompts/{template_name}/{step_name}.md` in the config bucket. [A2]
- [ ] **AC-35:** The email-triage `categorize` step prompt instructs the LLM to: use the four-category system (urgent/actionable/informational/ignorable), provide one-sentence reasoning per email, suggest concrete next actions for urgent items, and not classify promotional/automated emails as actionable. Max output: 500 words. [A14]
- [ ] **AC-36:** The morning-briefing `compose-briefing` step prompt follows SPEC-028's synthesis guidelines: 300-word limit, 3-5 items, importance-ordered, opinionated framing. It incorporates the user's standing instructions for tone/style context. [A14]
- [ ] **AC-37:** The draft-reply `compose-draft` step prompt instructs: match the user's greeting/signoff patterns, match their typical message length (based on writing style profile), use their vocabulary patterns, and incorporate any explicit instructions from the user. The prompt includes the full writing style profile and original email content as context. [A14]
- [ ] **AC-38:** Step prompts are loaded by the `AnthropicEngine` before each step execution. The engine passes them as the `system_prompt` parameter. If no prompt file exists for a step, the step's `description` field from the template is used as the system prompt. [A1]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `config/system/workflows/email-triage.md` | Email triage workflow template |
| `config/system/workflows/morning-briefing.md` | Morning briefing workflow template |
| `config/system/workflows/evening-briefing.md` | Evening briefing workflow template |
| `config/system/workflows/draft-reply.md` | Draft reply workflow template |
| `config/system/workflows/prompts/email-triage/categorize.md` | Categorization step prompt |
| `config/system/workflows/prompts/email-triage/summarize.md` | Summary step prompt |
| `config/system/workflows/prompts/morning-briefing/compose-briefing.md` | Briefing composition prompt |
| `config/system/workflows/prompts/evening-briefing/compose-briefing.md` | Evening briefing composition prompt |
| `config/system/workflows/prompts/draft-reply/compose-draft.md` | Draft composition prompt |
| `supabase/migrations/2026MMDD000001_seed_workflow_templates.sql` | Upload templates to config bucket |
| `supabase/migrations/2026MMDD000002_email_triage_preferences.sql` | Add email_triage columns to user_preferences |
| `chatServer/workflows/nodes/__init__.py` | Service nodes package (non-LLM steps) |
| `chatServer/workflows/nodes/deliver_briefing.py` | Briefing delivery node (NotificationService call) |
| `chatServer/workflows/nodes/mark_observations_consumed.py` | Mark deferred observations consumed |
| `tests/chatServer/workflows/test_email_triage_template.py` | Template parsing + step validation |
| `tests/chatServer/workflows/test_morning_briefing_template.py` | Template parsing + step validation |
| `tests/chatServer/workflows/test_draft_reply_template.py` | Template parsing + step validation |
| `tests/chatServer/workflows/test_draft_reply_revision.py` | Revision loop tests |
| `tests/chatServer/workflows/test_scheduling_integration.py` | Job handler → workflow dispatch |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/job_handlers.py` | Update `handle_morning_briefing` and `handle_evening_briefing` to dispatch workflows; add `handle_email_triage` handler |
| `chatServer/services/background_tasks.py` | Register `handle_email_triage` handler; update briefing bootstrap for email triage |
| `chatServer/tools/briefing_tools.py` (or `capabilities/executors/briefing.py`) | Extend `update_briefing_preferences` to handle email triage settings |
| `chatServer/services/pending_actions.py` | Support `revise` action type for workflow gates (in addition to approve/reject) |
| `chatServer/workflows/run_manager.py` | Add `revise` handling in `resume_run()` — rollback to step and re-execute |
| `chatServer/workflows/engine.py` | Load step prompts from ConfigService before execution |
| `webApp/src/components/ui/chat/ApprovalInlineMessage.tsx` | Detect `workflow_gate` tool_name, render step output preview + revision UI |
| `chatServer/database/user_scoped_tables.py` | (Already updated in SPEC-036 — no additional changes) |

### Out of Scope

- **Custom user workflow templates.** Users don't create or edit workflows in this spec. System-provided only.
- **Inline draft editing UI.** Revision is text-based ("make it shorter"), not a rich text editor. Same as SPEC-029 decision.
- **Parallel step execution within a workflow.** The `gather-context` step in morning-briefing conceptually fetches 4 sources "in parallel," but the workflow engine executes it as a single LLM step that calls multiple tools. True parallel step execution is SPEC-036 out-of-scope.
- **Evening briefing workflow template details.** AC-14 establishes it exists and follows the morning pattern. Detailed prompts are shipped but not individually spec'd — they follow the morning briefing precedent.
- **Batch email operations.** "Reply to all my unread emails" is future scope. Each draft-reply is one email.
- **Proactive draft suggestions.** The agent only drafts when asked or when the triage workflow surfaces an urgent email. Proactive "you should reply to X" as a standalone feature is future scope.
- **Email triage acting on emails.** Triage reads and categorizes only. Auto-archiving, auto-labeling, or auto-replying are future scope requiring Act-tier trust escalation.

## Technical Approach

### 1. email-triage.md Template

```markdown
---
name: email-triage
description: Process recent emails — categorize by urgency, surface important items
version: 1
default_gate_policy: none
---

# Email Triage

Scheduled workflow that reads recent emails, categorizes them by urgency,
and surfaces items needing attention.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| hours_back | no | How many hours of email to process (default: 12) |
| max_emails | no | Maximum emails to process per account (default: 20) |

## Steps

### step-1: Fetch Emails
- **agent:** email-fetcher
- **depends_on:** []
- **tools:** [search_gmail, get_gmail]
- **description:** Search all connected Gmail accounts for recent unread emails. Read the top messages by recency. Output structured data: sender, subject, snippet, date, message_id, account.
- **gate:** none

### step-2: Categorize
- **agent:** email-classifier
- **depends_on:** [step-1]
- **tools:** []
- **model:** claude-haiku-4-5-20251001
- **description:** Classify each email into urgent/actionable/informational/ignorable. Provide one-sentence reasoning per email. Suggest concrete next actions for urgent items.
- **gate:** none

### step-3: Summarize
- **agent:** triage-composer
- **depends_on:** [step-2]
- **tools:** [create_memories]
- **description:** Compose a triage summary. Urgent items first with suggested actions. Actionable items with context. Informational as one-liners. Store urgent/actionable items as memories for future reference.
- **gate:** none
```

**Cost optimization:** The `categorize` step uses Haiku (AC-08 per-step model override) since email classification is a structured task that doesn't need Sonnet-level reasoning. The `summarize` step uses Sonnet for better natural language composition.

### 2. morning-briefing.md Template

```markdown
---
name: morning-briefing
description: Compose personalized daily morning briefing from calendar, tasks, email, and observations
version: 1
default_gate_policy: none
---

# Morning Briefing

Scheduled workflow that gathers context from multiple sources and composes
an opinionated daily briefing.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| timezone | yes | User's IANA timezone (e.g., America/New_York) |
| briefing_sections | no | Which sections to include (default: all enabled) |

## Steps

### step-1: Gather Context
- **agent:** context-gatherer
- **depends_on:** []
- **tools:** [search_calendar, get_tasks, search_gmail, search_memories]
- **description:** Fetch today's calendar events, active/overdue tasks with due dates, recent unread emails (last 12 hours), and unconsumed deferred observations. Output structured context per section.
- **gate:** none

### step-2: Compose Briefing
- **agent:** briefing-composer
- **depends_on:** [step-1]
- **tools:** []
- **description:** Synthesize gathered context into a 300-word morning briefing. Pick 3-5 most important items. Order by importance, not category. Use opinionated framing. Include user's standing instructions for tone.
- **gate:** none

### step-3: Deliver
- **agent:** briefing-deliverer
- **depends_on:** [step-2]
- **tools:** []
- **node_type:** service
- **description:** Send briefing via NotificationService. Post-process for Telegram. Mark deferred observations as consumed.
- **gate:** none
```

**Service node:** Step 3 (`deliver`) is marked with `node_type: service` — a new template field that tells the GraphBuilder to create a service node (Python function) instead of an engine node (LLM call). This avoids wasting an API call on a pure delivery step. The `GraphBuilder` recognizes this field and creates a closure that calls `NotificationService.notify_user()` directly.

### 3. draft-reply.md Template

```markdown
---
name: draft-reply
description: Draft an email reply in the user's voice, present for approval, and send
version: 1
default_gate_policy: escalation-only
---

# Draft Reply

Interactive workflow for composing and sending email replies with
human approval before sending.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| message_id | yes | Gmail message ID to reply to |
| account | yes | Email address of the Gmail account |
| instructions | no | User guidance for the reply (e.g., "tell them I agree") |

## Steps

### step-1: Fetch Context
- **agent:** context-fetcher
- **depends_on:** []
- **tools:** [get_gmail, search_memories]
- **description:** Fetch the original email content and the user's writing style profile. If no writing style exists, note that a neutral professional tone will be used.
- **gate:** none

### step-2: Compose Draft
- **agent:** draft-composer
- **depends_on:** [step-1]
- **tools:** []
- **description:** Generate a reply draft matching the user's voice. Match greeting/signoff patterns, typical message length, and vocabulary from the writing style profile. Incorporate any user instructions.
- **gate:** none

### step-3: Present for Approval
- **agent:** approval-presenter
- **depends_on:** [step-2]
- **tools:** []
- **node_type:** gate
- **gate_policy:** human-required
- **description:** Present the composed draft to the user. Show subject, recipient, and body in a styled email preview. User can approve (send), reject (cancel), or revise (provide feedback and re-compose).
- **gate:** none

### step-4: Send
- **agent:** email-sender
- **depends_on:** [step-3]
- **tools:** [send_email_reply]
- **description:** Send the approved draft via Gmail. Confirm send with message ID and thread ID.
- **gate:** none
```

### 4. Revision Loop for Draft Reply

The `revise` action creates a loop:

```
compose-draft → present-for-approval → [revise] → compose-draft → present-for-approval → ...
```

Implementation in `WorkflowRunManager.resume_run()`:

```python
async def resume_run(self, run_id: str, action: str, data: dict | None = None):
    run = await self._get_run(run_id)

    if action == "approve":
        # Standard resume — inject approval and continue
        await self._compiled_graph.aupdate_state(
            {"configurable": {"thread_id": run.thread_id}},
            {"approval": "approved", "approval_data": data},
        )
        asyncio.create_task(self._continue_run(run))

    elif action == "reject":
        await self._cancel_run(run, reason="User rejected")

    elif action == "revise":
        # Rollback to compose-draft step with new instructions
        revision_instructions = data.get("instructions", "")
        # Update parameters with revision instructions
        current_state = await self._compiled_graph.aget_state(
            {"configurable": {"thread_id": run.thread_id}}
        )
        updated_params = {**current_state.values["parameters"]}
        # Append revision to existing instructions
        existing = updated_params.get("instructions", "")
        updated_params["instructions"] = f"{existing}\n\nRevision: {revision_instructions}".strip()

        await self._compiled_graph.aupdate_state(
            {"configurable": {"thread_id": run.thread_id}},
            {"parameters": updated_params, "approval": "revise"},
        )
        asyncio.create_task(self._continue_run(run))
```

The graph uses a conditional edge after the gate node:

```python
def route_after_gate(state: WorkflowState) -> str:
    if state.get("approval") == "revise":
        return "compose-draft"  # Loop back
    elif state.get("approval") == "approved":
        return "send"  # Continue
    else:
        return END  # Rejected or error
```

### 5. Service Nodes (non-LLM steps)

Some workflow steps don't need LLM calls — they're pure service operations (deliver notification, mark observations consumed, etc.). These are registered as **service nodes** to avoid unnecessary API costs.

```python
# In GraphBuilder:
def _make_node(self, step: StepDef, engine: AnthropicEngine) -> Callable:
    if step.node_type == "service":
        return self._make_service_node(step)
    elif step.node_type == "gate":
        return self._make_gate_node(step)
    else:
        return self._make_engine_node(step, engine)

def _make_service_node(self, step: StepDef) -> Callable:
    """Create a node that calls a registered service function, not the LLM."""
    service_fn = self._service_registry.get(step.name)
    if not service_fn:
        raise ValueError(f"No service registered for step '{step.name}'")

    async def node(state: WorkflowState) -> dict:
        result = await service_fn(state)
        return {"step_outputs": {**state["step_outputs"], step.name: result}}

    return node
```

Service functions for this spec:

```python
# chatServer/workflows/nodes/deliver_briefing.py
async def deliver_briefing(state: WorkflowState) -> str:
    """Deliver composed briefing via NotificationService."""
    briefing_text = state["step_outputs"]["compose-briefing"]
    user_id = state["parameters"]["user_id"]

    notification_service = get_notification_service()
    await notification_service.notify_user(
        user_id=user_id,
        body=briefing_text,
        notification_type="notify",
        category="briefing",
    )

    # Mark deferred observations consumed
    db_client = get_system_client()
    await db_client.table("deferred_observations").update(
        {"consumed_at": datetime.now(timezone.utc).isoformat()}
    ).eq("user_id", user_id).is_("consumed_at", "null").execute()

    return "Briefing delivered"
```

### 6. Step Prompts

Step prompts live as config files and are loaded by the `AnthropicEngine` before each step. Example for the email triage categorize step:

```markdown
# Email Categorization

You are classifying emails by urgency for the user's daily triage.

## Categories

- **urgent**: Needs response within hours. Examples: client escalations, time-sensitive requests, meeting conflicts, financial matters requiring action.
- **actionable**: Needs response but not time-sensitive. Examples: project updates requiring feedback, scheduling requests, non-urgent questions.
- **informational**: Worth knowing, no action needed. Examples: team announcements, status updates, newsletters the user subscribed to intentionally.
- **ignorable**: No value. Examples: automated notifications, marketing emails, newsletters they didn't subscribe to, social media alerts.

## Instructions

For each email in the input:
1. Assign exactly one category
2. Provide one sentence explaining why
3. For urgent items only: suggest a concrete next action

## Output Format

Return a structured list:
- [URGENT] From: sender — Subject: subject — Reason: why — Action: suggested action
- [ACTIONABLE] From: sender — Subject: subject — Reason: why
- [INFORMATIONAL] sender: subject (one line)
- [IGNORABLE] (count only, don't list individual emails)

Keep total output under 500 words. Be decisive — when in doubt between actionable and informational, choose informational.
```

### 7. Job Handler Migration (Briefings)

```python
# chatServer/services/job_handlers.py — updated

async def handle_morning_briefing(job: dict) -> dict:
    """Execute morning briefing as a workflow."""
    user_id = job["input"]["user_id"]

    # Get user preferences for parameters
    briefing_service = BriefingService(get_system_client())
    prefs = await briefing_service.get_user_preferences(user_id)

    # Dispatch workflow
    run_manager = get_workflow_run_manager()
    run_id = await run_manager.start_run(
        user_id=user_id,
        template_name="morning-briefing",
        parameters={
            "timezone": prefs.timezone,
            "briefing_sections": prefs.briefing_sections,
        },
    )

    # Self-schedule next occurrence (same as before)
    next_time = compute_next_briefing_time(prefs.timezone, prefs.morning_briefing_time)
    job_service = JobService(get_db_pool())
    await job_service.create(
        job_type="morning_briefing",
        input={"user_id": user_id},
        user_id=user_id,
        scheduled_for=next_time,
        expires_at=next_time + timedelta(hours=4),
    )

    return {"run_id": run_id, "next_scheduled": next_time.isoformat()}
```

### 8. Frontend: Workflow Gate Approval Card

The `ApprovalInlineMessage` component extends to handle `workflow_gate` tool names:

```typescript
// Detection in ApprovalInlineMessage.tsx
if (toolName === "workflow_gate") {
  const { template_name, draft_body, original_subject, original_sender } = context;

  if (template_name === "draft-reply") {
    // Render email draft preview (same as send_email_reply)
    return <EmailDraftPreview
      to={original_sender}
      subject={original_subject}
      body={draft_body}
      onApprove={handleApprove}
      onReject={handleReject}
      onRevise={handleRevise}  // New: revision text input
    />;
  }

  // Generic workflow gate: step output preview + approve/reject
  return <WorkflowGateCard
    stepName={toolArgs.step_name}
    preview={toolArgs.output_preview}
    onApprove={handleApprove}
    onReject={handleReject}
  />;
}
```

The `handleRevise` callback sends a `PATCH /api/actions/{action_id}` with `{"action": "revise", "data": {"instructions": revisionText}}`. The actions router routes this to `WorkflowRunManager.resume_run()` with `action="revise"`.

## Blast Radius

### New Files

| Component | Count | Risk |
|-----------|-------|------|
| Workflow templates (config files) | 4 templates + 5 prompts | Low — config data only |
| Service nodes | 2 files | Low — thin wrappers around existing services |
| Migration | 2 files | Low — additive (new columns, new config files) |
| Tests | 5 files | Low — test code only |

### Modified Existing Components

| File | Impact | Risk |
|------|--------|------|
| `chatServer/services/job_handlers.py` | Update 2 handlers, add 1 new | Medium — changes briefing execution path |
| `chatServer/services/background_tasks.py` | Register new handler + triage bootstrap | Low — additive |
| `chatServer/tools/briefing_tools.py` | Extend preferences for email triage | Low — additive to existing tool |
| `chatServer/services/pending_actions.py` | Support `revise` action type | Medium — new action flow |
| `chatServer/workflows/run_manager.py` | Add revision handling | Medium — graph state manipulation |
| `chatServer/workflows/engine.py` | Load step prompts from config | Low — additive |
| `webApp/src/components/ui/chat/ApprovalInlineMessage.tsx` | Detect workflow_gate + revision UI | **HIGH** — UX change |
| `chatServer/routers/actions.py` | Route `revise` action to run_manager | Low — additive |

### Existing Components NOT Modified

| Component | Why |
|-----------|-----|
| `BriefingService` | Still used for `get_user_preferences`, `update_user_preferences` — workflow replaces `generate_morning_briefing` only |
| `NotificationService` | Called by service nodes — interface unchanged |
| `PendingActionsService` | Called by gate nodes — interface unchanged (just new action type) |
| `draft_email_reply` / `send_email_reply` tools | Workflow calls them via gateway — tools unchanged |
| `user_preferences` table (schema) | Extended with new columns, existing columns unchanged |

## Testing Requirements

### Unit Tests

**Template tests (per template):**
- `test_parse_email_triage_template` — correct steps, tools, gate policies
- `test_parse_morning_briefing_template` — correct steps, parameter requirements
- `test_parse_draft_reply_template` — correct steps, human gate on step-3
- `test_parse_evening_briefing_template` — follows morning pattern

**Revision loop tests:**
- `test_revise_action_loops_to_compose` — revise → compose-draft re-executes
- `test_revise_preserves_original_context` — original email context survives revision
- `test_revise_appends_instructions` — revision instructions merged with originals
- `test_multiple_revisions` — revise → compose → revise → compose works

**Scheduling tests:**
- `test_morning_briefing_handler_dispatches_workflow` — handler calls `start_run`
- `test_morning_briefing_handler_self_schedules` — next job created after completion
- `test_email_triage_handler_dispatches_workflow` — new handler works
- `test_email_triage_schedule_create_on_enable` — enabling creates first job
- `test_email_triage_schedule_cancel_on_disable` — disabling cancels pending jobs

**Service node tests:**
- `test_deliver_briefing_sends_notification` — notification service called
- `test_deliver_briefing_marks_observations_consumed` — DB updated
- `test_deliver_briefing_telegram_format` — Telegram post-processing applied

### Integration Tests

- `test_email_triage_full_workflow` — start → fetch → categorize → summarize → complete
- `test_morning_briefing_full_workflow` — start → gather → compose → deliver → complete
- `test_draft_reply_approve_flow` — start → fetch → compose → gate → approve → send → complete
- `test_draft_reply_revise_flow` — start → compose → gate → revise → compose → gate → approve → send
- `test_draft_reply_reject_flow` — start → compose → gate → reject → cancelled

### AC-to-Test Mapping

| AC | Test | Notes |
|----|------|-------|
| AC-01–07 | `test_parse_email_triage_template`, `test_email_triage_full_workflow` | Template + execution |
| AC-08–15 | `test_parse_morning_briefing_template`, `test_morning_briefing_full_workflow` | Template + execution |
| AC-16–24 | `test_parse_draft_reply_template`, `test_draft_reply_*_flow` | Template + all flows |
| AC-25–27 | Frontend component tests (manual verification) | Approval card UI |
| AC-28 | `test_revise_*` suite | Revision loop mechanics |
| AC-29–30 | `test_*_briefing_handler_dispatches_workflow` | Job handler migration |
| AC-31–33 | `test_email_triage_*` scheduling tests | Triage scheduling |
| AC-34–38 | Template parse + engine integration | Prompt loading |

### Manual Verification (UAT)

- [ ] Schedule a morning briefing → verify workflow runs and delivers briefing to chat + Telegram
- [ ] Verify briefing content follows 3-5 item, importance-ordered format
- [ ] Ask "triage my email" → verify `dispatch_workflow("email-triage")` fires
- [ ] Verify email triage categorization is sensible (urgent vs informational)
- [ ] Ask "reply to [person]'s email" → verify `dispatch_workflow("draft-reply")` fires
- [ ] Verify draft appears in styled email preview card
- [ ] Click "Approve" on draft → verify email sends, confirmation appears
- [ ] Click "Reject" on draft → verify workflow cancelled, no email sent
- [ ] Enter revision text ("make it shorter") → verify new draft appears
- [ ] Verify revision preserves original email context
- [ ] Via Telegram: verify briefing + draft approval work cross-channel
- [ ] Enable email triage in preferences → verify scheduled triage jobs created
- [ ] Disable email triage → verify pending jobs cancelled

## Edge Cases

- **No Gmail connected:** `fetch-emails` step tools return "Gmail not connected" error. Workflow fails gracefully with clear error in the event stream. Morning briefing skips email section if Gmail is unavailable.
- **No calendar connected:** `gather-context` step skips calendar data. Briefing composed from remaining sections.
- **Empty inbox for triage:** `fetch-emails` returns zero results. `categorize` step receives empty input, outputs "No new emails." Workflow completes with a brief "all clear" summary.
- **Writing style not yet learned:** `fetch-context` notes absence. `compose-draft` uses neutral professional tone. Not a blocker — degrades gracefully.
- **Revision with contradictory instructions:** Each revision appends to the instruction list. The LLM resolves conflicts by prioritizing the most recent instruction (last one wins). No special handling needed — this is natural LLM behavior.
- **Workflow step API error:** The engine handles per-step errors. If a step fails (e.g., API rate limit), the run status is set to `failed` with the error. The job handler's retry mechanism re-runs the entire workflow from the beginning (checkpoint not used for retry — retry is a fresh run).
- **User approves after long delay:** Pending actions expire after 24h. If the user approves an expired action, the actions router returns "This action has expired." The user can re-initiate the draft-reply conversation.
- **Concurrent draft-reply workflows:** Each run is independent (SPEC-036). Two draft-reply workflows for different emails run without conflict. Two for the same email are technically allowed but unusual — the agent should recognize and prevent this conversationally.
- **Briefing sections all disabled:** If the user disables all sections in `briefing_sections`, the `gather-context` step fetches nothing. The `compose-briefing` step receives empty context and produces a minimal "No updates today" message. Not an error.

## Functional Units (for PR Breakdown)

### FU-1: email-triage Template + Prompts (backend-dev)
**ACs:** AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-34, AC-35
**Depends on:** SPEC-036 FU-1 (template parser)

Template file, step prompts, seed migration, template parse tests.

### FU-2: morning-briefing + evening-briefing Templates + Prompts (backend-dev)
**ACs:** AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-36
**Depends on:** SPEC-036 FU-1, SPEC-028 (BriefingService)

Template files, step prompts, service nodes (deliver, mark consumed), seed migration.

### FU-3: draft-reply Template + Revision Loop (backend-dev)
**ACs:** AC-16, AC-17, AC-18, AC-19, AC-20, AC-21, AC-22, AC-23, AC-24, AC-28, AC-37
**Depends on:** SPEC-036 FU-2 (engine) + FU-5 (human gates), SPEC-029 (draft/send tools)

Template file, step prompts, revision loop in run_manager, conditional edges.

### FU-4: Frontend — Workflow Gate Approval (frontend-dev)
**ACs:** AC-25, AC-26, AC-27
**Depends on:** FU-3

Extend `ApprovalInlineMessage` for `workflow_gate`, add revision text input.

### FU-5: Scheduling Migration + Email Triage (backend-dev)
**ACs:** AC-29, AC-30, AC-31, AC-32, AC-33
**Depends on:** FU-1, FU-2, SPEC-036 FU-6 (scheduling integration)

Update briefing handlers, add email triage handler + preferences.

### FU-6: Step Prompt Engine Integration (backend-dev)
**ACs:** AC-34, AC-38
**Depends on:** SPEC-036 FU-2 (engine), SPEC-035 (ConfigService)

Engine loads prompts from config, fallback to step description.

### Merge Order

```
FU-1 ──→ FU-5
FU-2 ──→ FU-5
FU-3 ──→ FU-4
FU-6 (can merge anytime after SPEC-036 FU-2)
```

FU-1, FU-2, FU-3, and FU-6 can proceed in parallel once their SPEC-036 dependencies are met.

## Decisions Requiring Your Input

1. **Email triage as default-enabled:** The spec has `email_triage_enabled` defaulting to `false` — users opt in. An alternative is defaulting to `true` for users who have Gmail connected. **Should email triage be opt-in or opt-out for Gmail-connected users?**

2. **Revision loop limit:** The draft-reply workflow allows unlimited revisions (approve/revise/reject at each gate). In theory, a user could loop forever. **Should we cap revisions (e.g., max 5) to prevent runaway token costs, or is this an unrealistic concern?**

3. **SPEC-028 deprecation:** This spec migrates morning/evening briefing execution from `BriefingService.generate_morning_briefing()` to the workflow engine. The old code path remains (SPEC-028's synthesis prompt, direct `ScheduledExecutionService` call). **Should the old path be removed in this spec, or kept as fallback behind a feature flag?**

4. **Step model assignment:** The email triage `categorize` step is assigned `claude-haiku-4-5-20251001` for cost savings. All other steps use the default Sonnet. **Is Haiku appropriate for email classification, or should all steps start on the same model?**

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-38)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (workflow_gate pending_action shape, revision action format, step prompt path convention)
- [x] Technical decisions reference architecture principles (A1, A2, A3, A6, A7, A11, A12, A14, F1)
- [x] Merge order is explicit and acyclic
- [x] Out-of-scope is explicit (7 items)
- [x] Edge cases documented with expected behavior (9 cases)
- [x] Testing requirements map to ACs
- [x] Dependencies documented with status
- [x] Blast radius assessed for all new and modified files
- [x] Relationship to existing SPEC-028 and SPEC-029 clearly documented
- [x] All three workflow templates fully specified with step details
