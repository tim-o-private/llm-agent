# SPEC-023: Email Onboarding Pipeline

> **Status:** Draft
> **Author:** Tim + Claude (Product)
> **Created:** 2026-02-24
> **Updated:** 2026-02-24

## Goal

When a user connects their Gmail account, kick off a background job that processes 7 days of email (inbox + sent) and writes structured insights to memory. The agent should know the user's key relationships, communication style, recurring patterns, and open action items — without the user having to tell it any of this. This is the "magic moment" where Clarity demonstrates judgment, not just data access.

## Background

Today, when a user connects Gmail via OAuth, the connection is silently stored and nothing else happens. The agent only encounters email when it actively calls `search_gmail` — which on first session burns 120K+ tokens on raw email bodies (SPEC-021 problem). The fix isn't just making search cheaper (SPEC-021 handles that). It's pre-processing email into structured memory so the agent already knows the user's world before they ask.

See `docs/product/PRD-001-make-it-feel-right.md` Workstream 1 for full product context.

## Acceptance Criteria

### Background Job Infrastructure

- [ ] **AC-01:** A new `email_processing_jobs` table exists with columns: `id` (UUID PK), `user_id` (UUID FK), `connection_id` (UUID FK to external_api_connections), `status` (pending/processing/complete/failed), `created_at`, `started_at`, `completed_at`, `error_message` (nullable TEXT), `result_summary` (nullable JSONB). RLS policy: owner-only via `is_record_owner()`. [A8, A9]
- [ ] **AC-02:** When a Gmail connection is created or reactivated in `external_api_router.py`, a row is inserted into `email_processing_jobs` with status `pending`. [A1, A14]
- [ ] **AC-03:** `BackgroundTaskService` checks for pending email processing jobs every 60 seconds. When found, it executes the job via `EmailOnboardingService` and updates status to `processing` → `complete` (or `failed` with error message). [A1]

### Email Processing Pipeline

- [ ] **AC-04:** `EmailOnboardingService` processes inbox and sent mail for the connected account, covering the last 7 days. Uses `search_gmail` with metadata-only format (SPEC-021 dependency) and `get_gmail` for selective full-body reads when needed for context. [A1, A14]
- [ ] **AC-05:** Processing extracts and stores as memory entries: key relationships (people the user communicates with, inferred relationship, frequency), recurring patterns (newsletters, project threads, automated notifications), open action items (emails that appear to need replies or have deadlines), and inferred life context (kids' school, home projects, work domain). Memory entries use appropriate types (`core_identity`, `project_context`, `episodic`) and entity links. [A6]
- [ ] **AC-06:** Processing analyzes sent messages to create a writing style profile: tone (formal/casual), typical length, common phrases, formatting preferences. Stored as a `core_identity` memory entry with entity `writing_style`. [A6]
- [ ] **AC-07:** Processing completes within 5 minutes for a typical personal email account (~100-200 emails in 7 days). Uses Haiku model for categorization/extraction and Sonnet for final synthesis only. [A14]

### User Notification & Reveal

- [ ] **AC-08:** When processing completes successfully, a notification is sent to the user via `NotificationService` with category `agent_result`. Title: "I've read through your email." Body includes a brief summary of what was found (key relationships count, action items count, patterns identified). [A7]
- [ ] **AC-09:** On the next `session_open` after processing completes, the agent's pre-loaded memory notes include the email insights. The agent references these naturally in its greeting (e.g., "Looks like you've got a lot going on with [contractor] about a renovation..."). No special code needed — memory pre-fetch already loads `core_identity` and `project_context` entries. [A14]

### Validation with User

- [ ] **AC-10:** The notification body (AC-08) or the agent's next greeting (AC-09) explicitly invites the user to validate: "Does this sound right? Am I missing anything important?" The agent should treat the user's response as high-value calibration data and record corrections to memory. [A12]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/2026MMDD000001_email_processing_jobs.sql` | Create table + RLS |
| `chatServer/services/email_onboarding_service.py` | Core processing pipeline |
| `chatServer/models/email_processing.py` | Pydantic models for job status |
| `tests/chatServer/services/test_email_onboarding_service.py` | Service unit tests |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/routers/external_api_router.py` | Insert pending job on Gmail connect |
| `chatServer/services/background_tasks.py` | Add check for pending email processing jobs |
| `chatServer/main.py` | No changes needed (background tasks auto-start) |

### Out of Scope

- Gmail search truncation / metadata-only format (SPEC-021 prerequisite)
- Gmail rate limiting (SPEC-021)
- Real-time email monitoring / push notifications (future spec)
- Processing for non-Gmail providers (future)
- Reprocessing on demand (future — user says "reread my email")
- Calendar, Slack, or other signal source processing (future specs)

## Technical Approach

### 1. DB Migration

Create `email_processing_jobs` table with RLS. One job per user per connection. Status lifecycle: `pending` → `processing` → `complete` | `failed`.

### 2. OAuth Hook

In `external_api_router.py`, after successful Gmail connection upsert, insert a pending job:

```python
# After connection stored successfully
await db_client.table("email_processing_jobs").insert({
    "user_id": str(user.id),
    "connection_id": str(connection_id),
    "status": "pending"
}).execute()
```

Per A1, this stays thin — just the insert. Processing logic lives in the service.

### 3. Background Task Integration

Add a method to `BackgroundTaskService`:

```python
async def _check_email_processing_jobs(self):
    """Check for pending email processing jobs and execute them."""
    # Query pending jobs
    # For each: update to processing, call EmailOnboardingService, update to complete/failed
```

This mirrors the existing pattern for scheduled agent execution and reminder delivery.

### 4. Email Onboarding Service

The service:
1. Loads the user's Gmail credentials from `external_api_connections`
2. Searches inbox (`newer_than:7d`) — gets metadata only (subject, from, date, snippet)
3. Searches sent (`in:sent newer_than:7d`) — same format
4. Groups by sender/recipient, identifies patterns
5. For high-signal emails (looks like action item, important sender), fetches full body via `get_gmail`
6. Calls LLM (Haiku) to categorize and extract:
   - Key relationships with inferred context
   - Recurring patterns (newsletters, project threads)
   - Open action items
   - Life domain signals
7. Calls LLM (Haiku) on sent messages to extract writing style profile
8. Calls LLM (Sonnet) for final synthesis: cohesive summary for notification
9. Stores all insights as memory entries via `MemoryClient`
10. Sends notification via `NotificationService`

**Token budget estimate:**
- 200 emails × ~200 tokens (metadata) = 40K tokens input for categorization
- 20 high-signal emails × ~1K tokens (body) = 20K tokens for deep reads
- Writing style analysis: ~10K tokens of sent messages
- Synthesis: ~5K tokens
- Total: ~75K tokens at Haiku rates ≈ $0.02-0.05 per user

### 5. Memory Storage

Example memory entries created:

```python
# Key relationship
create_memories(
    text="User communicates frequently with Mike Chen (contractor). "
         "Topic: kitchen renovation. Urgency: high (daily exchanges). "
         "User tends to reply within hours.",
    memory_type="core_identity",
    entity="Mike Chen",
    tags=["home", "relationship", "contractor"]
)

# Writing style
create_memories(
    text="User writes casually. Typical email length: 2-4 sentences. "
         "Uses contractions, occasional humor. Signs off with first name only. "
         "Doesn't use formal greetings.",
    memory_type="core_identity",
    entity="writing_style",
    tags=["communication", "style"]
)

# Action item
create_memories(
    text="Open action: permission slip from Riverside Elementary due Friday 2/28. "
         "Email from office@riverside.edu on 2/22.",
    memory_type="episodic",
    entity="Riverside Elementary",
    tags=["family", "school", "action_item"]
)

# Life context
create_memories(
    text="User has children at Riverside Elementary (inferred from school emails). "
         "Receives weekly newsletters and occasional urgent notices.",
    memory_type="core_identity",
    entity="Riverside Elementary",
    tags=["family", "school"]
)
```

### Dependencies

- **SPEC-021 AC-01:** Gmail search metadata-only format. Without this, email processing burns too many tokens on raw bodies. If SPEC-021 isn't complete, this spec can still work but will be more expensive and slower.
- **SPEC-022:** Soul rewrite should ship first or alongside, so the agent's personality is right when it delivers the reveal moment.

## Testing Requirements

### Unit Tests (required)

- `test_email_onboarding_service.py`: Service processes mock email data and calls memory client with correct entries
- `test_email_onboarding_service.py`: Service handles Gmail API errors gracefully (returns error status, doesn't crash)
- `test_email_onboarding_service.py`: Service handles empty inbox (no emails in 7 days) — still completes, creates minimal memory
- `test_email_onboarding_service.py`: Service sends notification on completion
- `test_email_onboarding_service.py`: Job status transitions: pending → processing → complete

### Integration Tests

- OAuth callback creates pending job in DB
- Background task picks up pending job and executes
- Memory entries exist after processing completes
- Notification sent to user

### AC-to-Test Mapping

| AC | Test Type | Test Function |
|----|-----------|--------------|
| AC-01 | Unit | `test_email_processing_jobs_table_exists` |
| AC-02 | Unit | `test_gmail_connect_creates_pending_job` |
| AC-03 | Unit | `test_background_task_picks_up_pending_job` |
| AC-04 | Unit | `test_service_processes_inbox_and_sent` |
| AC-05 | Unit | `test_service_creates_relationship_memories` |
| AC-06 | Unit | `test_service_creates_writing_style_memory` |
| AC-07 | Integration | `test_processing_completes_within_5_minutes` |
| AC-08 | Unit | `test_service_sends_completion_notification` |
| AC-09 | Manual | Verify memory notes in next session_open |
| AC-10 | Manual | Verify notification invites validation |

### Manual Verification (UAT)

- [ ] Connect Gmail account
- [ ] Verify pending job created (check DB)
- [ ] Wait for processing to complete (<5 min)
- [ ] Verify notification received with summary
- [ ] Open new chat session — verify agent references email insights in greeting
- [ ] Correct the agent ("that's not my contractor, that's my neighbor") — verify it updates

## Edge Cases

- **User has no email in last 7 days:** Service completes with minimal output. Creates memory: "User's inbox had no recent activity." Agent can still be useful through conversation.
- **User has thousands of emails (heavy inbox):** Limit processing to most recent 200 emails. Log warning if truncated.
- **Gmail API rate limit hit during processing:** Service catches rate limit errors, processes what it can, marks job as complete with partial results. Logs warning.
- **User disconnects Gmail before processing completes:** Job fails gracefully. Status set to `failed` with message "Gmail connection removed during processing."
- **Multiple Gmail accounts connected:** One job per connection. Process independently. Memory entries tagged with account email.
- **User reconnects Gmail (disconnect + reconnect):** New pending job created. Previous job results remain in memory (agent can reconcile).
- **Memory server unavailable:** Job fails, status set to `failed`. Can be retried on next background task check.

## Functional Units (for PR Breakdown)

1. **FU-1:** Migration + models (`feat/SPEC-023-migration`)
   - `email_processing_jobs` table + RLS
   - Pydantic models

2. **FU-2:** Service + background task integration (`feat/SPEC-023-service`)
   - `EmailOnboardingService` class
   - Background task loop addition
   - OAuth hook in external_api_router
   - Unit tests

3. **FU-3:** Notification + validation prompt (`feat/SPEC-023-notification`)
   - Completion notification
   - Summary formatting
   - Tests

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-10)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (DB → service → notification)
- [x] Technical decisions reference principles (A1, A2, A6, A7, A8, A9, A12, A14)
- [x] Merge order is explicit (FU-1 → FU-2 → FU-3)
- [x] Out-of-scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
