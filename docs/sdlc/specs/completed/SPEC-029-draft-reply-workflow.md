# SPEC-029: Draft-Reply Workflow

> **Status:** Draft
> **Author:** Tim + Claude (Product)
> **Created:** 2026-02-24
> **Updated:** 2026-03-05
> **PRD:** PRD-002 (Expand the World), Workstream 4

## Goal

Enable the agent to draft email replies in the user's voice and send them with explicit approval. This is the first Act-tier capability — the agent does something on the user's behalf, with a hard approval gate before execution. Uses the writing style profile from SPEC-023's sent message analysis to match the user's natural tone, length, and conventions. No inline editing UI — the user revises conversationally ("make it shorter", "change the second sentence to X") and the agent re-presents the updated draft.

## PRD Context

From PRD-002, Workstream 4:

- **Trust tier:** Starts at Recommend — agent proposes, user approves every time. Graduation to Act (auto-send) is future scope requiring a trust tier system that does not exist yet.
- **Writing style:** SPEC-023 extracts tone, length, greeting/signoff patterns. The draft tool uses this in its generation prompt.
- **OAuth:** Requires Gmail compose scope (`gmail.compose`) — included in the initial Gmail OAuth consent alongside `gmail.readonly`. Existing users re-authorize when they first try to send.
- **Inline editing:** MVP uses conversational editing, not an inline text editor.

## Dependencies

| Dependency | What It Provides | Status |
|-----------|-----------------|--------|
| SPEC-023 (Email Onboarding Pipeline) | Writing style profile stored as memory with entity=`writing_style`, tags=`["communication", "style"]` | Complete |
| SPEC-025 (Unified Notification Experience) | `requires_approval`, `pending_action_id` on notifications; inline approval buttons in chat and Telegram | Complete |
| SPEC-026 (Universal Job Queue) | `jobs` table for async processing (used if we need background draft generation) | Complete |
| Gmail OAuth (existing) | `gmail.readonly` scope, `OAuthService`, `store_oauth_tokens` RPC, `GmailToolProvider` credential management | Complete |

## Acceptance Criteria

### OAuth: Gmail Compose Scope

- [ ] **AC-01:** `GMAIL_SCOPES` in `oauth_service.py` is updated to include `gmail.compose` alongside the existing `gmail.readonly`, `openid`, and `userinfo.email` scopes. New users get compose permission on initial Gmail connection. [A6, A11]
- [ ] **AC-02:** For existing users who connected Gmail with only `gmail.readonly`: when the agent detects missing compose scope (by checking stored scopes in `external_api_connections`), it returns a message prompting re-authorization: "I need send permission to reply. Please re-connect your Gmail in [Settings > Integrations] to enable sending." [A6, A13]
- [ ] **AC-03:** The existing Gmail OAuth callback (`handle_gmail_callback`) stores the updated scopes array (now including `gmail.compose`) via `store_oauth_tokens`. No new OAuth endpoints or service names are needed — compose uses the same `service_name='gmail'` connection. [A6, A9]

### Backend: Draft Email Reply Tool

- [ ] **AC-04:** A `DraftEmailReplyTool` (`draft_email_reply`) accepts `message_id`, `account` (email address), and optional `instructions` (user guidance like "tell them I'll be late"). It fetches the original email via `get_gmail`, retrieves the user's writing style from memory, and returns them as structured context (original email content + writing style profile + any user instructions). The **agent** (already an LLM) then composes the draft using this context — the tool does not generate the draft text itself. [A6, A10]
- [ ] **AC-05:** The draft tool's context retrieval includes the user's writing style profile (entity=`writing_style`, tags=`["communication", "style"]`). If no writing style exists in memory, the tool still returns the original email context but includes a note that it cannot match the user's voice yet and suggests connecting more email for style learning. [A6]
- [ ] **AC-06:** `draft_email_reply` has approval tier `AUTO_APPROVE` — drafting text is read-only and safe. The draft is returned as a chat message, not a pending action. [A12]
- [ ] **AC-07:** The agent formats the draft output as a clearly delineated email preview in Markdown: subject line, recipient, and body separated from the agent's commentary. The agent explicitly asks the user to approve, request changes, or cancel. (Note: the tool provides the ingredients; the agent composes and formats.) [A7]

### Backend: Send Email Reply Tool

- [ ] **AC-08:** A `SendEmailReplyTool` (`send_email_reply`) accepts `message_id`, `account`, `body` (the approved draft text), and optional `subject` override. It constructs an RFC 2822 reply message, sets the correct `In-Reply-To` and `References` headers, preserves the `threadId`, and sends via the Gmail API `messages.send` endpoint. [A6, A10]
- [ ] **AC-09:** `send_email_reply` has approval tier `REQUIRES_APPROVAL` — it is security-critical and cannot be overridden to auto-approve. When the agent invokes this tool, it is queued as a `pending_action` and the user sees an approval notification with the full draft text. [A12]
- [ ] **AC-09a:** When `send_email_reply` creates a `pending_action`, the tool populates `context` metadata with `original_subject` (from the original email's Subject header) and `original_sender` (from the original email's From header), so the frontend and Telegram can render them in the approval card. [A6, A12]
- [ ] **AC-10:** On approval, the `pending_actions` executor calls the tool, which sends the email via the Gmail API using `gmail` credentials (which now include compose scope) fetched from `external_api_connections`. On success, it returns a confirmation message. On failure, it returns the error. [A6]
- [ ] **AC-11:** The send tool uses the existing `GmailToolProvider` pattern to fetch credentials for the specified account. The same `gmail` credentials now have compose scope. Handles token refresh via the existing credential refresh pattern. [A6]

### Backend: Gmail Compose Service

- [ ] **AC-12:** A `GmailComposeService` class in `chatServer/services/gmail_compose_service.py` provides `send_reply(credentials, original_message_id, body, subject_override=None)`. It fetches the original message headers (To, Subject, Message-ID, References), constructs the reply with proper threading headers, and sends via the Gmail API. [A1, A6]
- [ ] **AC-13:** The compose service constructs replies with: `To` set to the original sender, `Subject` set to `Re: <original subject>` (unless overridden), `In-Reply-To` set to the original `Message-ID` header, `References` including the original `Message-ID`, and `threadId` set to the original thread. [A6]
- [ ] **AC-14:** The compose service creates the message body as `text/plain` MIME content. HTML email composition is out of scope. [A14]

### Prompt Integration

- [ ] **AC-15:** Both tools have `prompt_section()` methods that provide behavioral guidance: when the user asks to reply, use `draft_email_reply` first, present the draft, wait for approval or revision, then use `send_email_reply`. Never call `send_email_reply` without presenting a draft first. [A6]
- [ ] **AC-16:** The prompt section instructs the agent on conversational editing: if the user says "make it shorter" or "change X to Y", regenerate the draft with the updated instructions and present again. Do not call `send_email_reply` until the user explicitly approves. After presenting each draft, the agent includes a brief affordance hint: "You can ask me to revise it (e.g., 'make it shorter', 'more formal'), or say 'send it' to approve." [A6]

### Frontend: Compose Scope Status

- [ ] **AC-17:** The Integrations page Gmail card shows scope status: "Read Only" when only `gmail.readonly` is connected, "Read & Send" when `gmail.compose` is also present. Shows a "Re-authorize for Send" button for accounts missing compose scope. [F1, A13]
- [ ] **AC-18:** Clicking "Re-authorize for Send" initiates the existing Gmail OAuth flow (which now requests compose scope). On callback, the updated scopes are stored in the same `gmail` connection row. [F1]

### Frontend: Email Draft Approval Preview

- [ ] **AC-19:** `ApprovalInlineMessage` detects `tool_name === 'send_email_reply'` and renders a styled email draft preview component instead of raw JSON `tool_args`. The preview shows: `To` (from `context.original_sender`), `Subject` (from `context.original_subject`), and `Body` (from `tool_args.body`) in a card layout. Falls back to existing raw JSON rendering for other tool names. [F1, A7]

### Tool Registration

- [ ] **AC-20:** Both tools are registered in the `tools` table with `type` TEXT values `DraftEmailReplyTool` and `SendEmailReplyTool`, linked to the `assistant` agent via `agent_tools`. [A6]
- [ ] **AC-21:** Both tools are added to `TOOL_REGISTRY` in `agent_loader_db.py`, `TOOL_APPROVAL_DEFAULTS` in `approval_tiers.py`, and `CANONICAL_TOOL_NAMES` in `test_tool_registry_validator.py`. [A6]

### Testing

- [ ] **AC-22:** Unit tests cover: `GmailComposeService.send_reply` happy path, missing headers, token refresh, RFC 2822 formatting. [S1]
- [ ] **AC-23:** Unit tests cover: `draft_email_reply` tool with and without writing style in memory, error when Gmail not connected, context output format. [S1]
- [ ] **AC-24:** Unit tests cover: `send_email_reply` tool approval tier is REQUIRES_APPROVAL, successful send, error handling, missing compose scope detection, `context` metadata includes `original_subject` and `original_sender`. [S1]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/services/gmail_compose_service.py` | Gmail compose API wrapper — `send_reply()` |
| `chatServer/tools/gmail_compose_tools.py` | `DraftEmailReplyTool`, `SendEmailReplyTool` |
| `tests/chatServer/services/test_gmail_compose_service.py` | Unit tests for GmailComposeService |
| `tests/chatServer/tools/test_gmail_compose_tools.py` | Unit tests for draft and send tools |
| `supabase/migrations/2026MMDD000001_register_compose_tools.sql` | Register tools in `tools` table, link to `assistant` agent |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/oauth_service.py` | Add `gmail.compose` to `GMAIL_SCOPES` |
| `src/core/agent_loader_db.py` | Add `DraftEmailReplyTool`, `SendEmailReplyTool` to `TOOL_REGISTRY` |
| `chatServer/security/approval_tiers.py` | Add `draft_email_reply` (AUTO_APPROVE) and `send_email_reply` (REQUIRES_APPROVAL) |
| `tests/chatServer/services/test_tool_registry_validator.py` | Add both tool names to `CANONICAL_TOOL_NAMES` |
| `webApp/src/pages/Settings/Integrations.tsx` | Show compose scope status, re-authorize button for existing connections |
| `webApp/src/components/ui/chat/ApprovalInlineMessage.tsx` | Add `send_email_reply` detection and email draft preview component |

### Out of Scope

- **New message composition** — only replies to existing threads. New message drafting is a future spec.
- **HTML email bodies** — text/plain only. Rich formatting is future scope.
- **Attachments** — text-only replies. Attachment support is future scope.
- **Trust tier graduation** — auto-send after N successful sends requires a trust tier system that does not exist. Future spec.
- **Inline text editor** — no rich editor component. Users revise via conversation.
- **Batch replies** — one reply at a time. "Reply to all my unread emails" is future scope.
- **Reply-all** — replies go to the original sender only. CC/BCC handling is future scope.
- **Gmail draft API** — we do not use Gmail's draft API (which stores drafts server-side). Drafts exist only as chat messages and pending_actions context.
- **Proactive draft suggestions** — the agent only drafts when asked. Proactive "you should reply to X" is future scope, dependent on the briefing system.

## Technical Approach

### 1. OAuth Scope Upgrade (`chatServer/services/oauth_service.py`)

The `gmail.compose` scope is added to `GMAIL_SCOPES` alongside the existing `gmail.readonly`. New users get compose permission on initial connection. The same `service_name='gmail'` connection is used — no new connection type needed.

```python
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]
```

**Existing users:** Users who connected Gmail before this change have tokens with only `gmail.readonly`. When the `send_email_reply` tool detects missing compose scope (by checking the `scopes` array in `external_api_connections`), it returns a message prompting re-authorization. The user clicks "Re-authorize" in Settings > Integrations, which runs the standard Gmail OAuth flow with the updated scopes. The callback updates the existing connection row via `store_oauth_tokens` (ON CONFLICT UPDATE).

**Why not a separate connection:** The user decided to reuse the existing gmail connection. Compose is a natural extension of the gmail integration, not a separate service. This avoids re-auth confusion, extra connection cards, and the CHECK constraint / RPC whitelist changes that a new service name would require.

**Google Cloud Console:** `gmail.compose` must be added to the OAuth consent screen's requested scopes. This is a restricted scope that may require Google verification for apps with >100 users. Non-blocking for dev/test.

### 2. Gmail Compose Service (`chatServer/services/gmail_compose_service.py`)

Thin service wrapping the Gmail API send endpoint. Follows the same pattern as `CalendarService`.

```python
import base64
import email.mime.text
import logging
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class GmailComposeService:
    """Send email replies via the Gmail API."""

    def __init__(self, credentials: Credentials):
        self.service = build("gmail", "v1", credentials=credentials)

    def send_reply(
        self,
        original_message_id: str,
        body: str,
        subject_override: Optional[str] = None,
    ) -> dict:
        """Send a reply to an existing email message.

        Args:
            original_message_id: Gmail message ID to reply to.
            body: Plain text reply body.
            subject_override: Override the Re: subject line.

        Returns:
            Dict with sent message id and threadId.
        """
        # 1. Fetch original message headers
        original = self.service.users().messages().get(
            userId="me", id=original_message_id, format="metadata",
            metadataHeaders=["Subject", "From", "Message-ID", "References"],
        ).execute()

        headers = {
            h["name"]: h["value"]
            for h in original.get("payload", {}).get("headers", [])
        }
        thread_id = original.get("threadId")

        # 2. Construct reply headers
        to = headers.get("From", "")
        subject = subject_override or f"Re: {headers.get('Subject', '')}"
        in_reply_to = headers.get("Message-ID", "")
        references = headers.get("References", "")
        if in_reply_to:
            references = f"{references} {in_reply_to}".strip()

        # 3. Build MIME message
        mime_message = email.mime.text.MIMEText(body, "plain")
        mime_message["To"] = to
        mime_message["Subject"] = subject
        mime_message["In-Reply-To"] = in_reply_to
        mime_message["References"] = references

        raw = base64.urlsafe_b64encode(
            mime_message.as_bytes()
        ).decode("ascii")

        # 4. Send via Gmail API
        sent = self.service.users().messages().send(
            userId="me",
            body={"raw": raw, "threadId": thread_id},
        ).execute()

        return {
            "message_id": sent.get("id"),
            "thread_id": sent.get("threadId"),
            "to": to,
            "subject": subject,
        }
```

### 3. Draft Email Reply Tool

The tool's role is to **fetch and assemble context** — original email content, writing style profile, and user instructions — and return them as structured data. The **agent** (already an LLM) then composes the draft using this context. This avoids a nested LLM call and leverages the agent's conversational context.

```python
class DraftEmailReplyInput(BaseModel):
    message_id: str = Field(..., description="Gmail message ID to reply to")
    account: str = Field(..., description="Email address of the Gmail account")
    instructions: Optional[str] = Field(
        default=None,
        description="Optional guidance for the reply (e.g., 'tell them I agree but need more time')",
    )

class DraftEmailReplyTool(BaseTool):
    name: str = "draft_email_reply"
    description: str = (
        "Fetch an email and the user's writing style to prepare a reply. "
        "Returns the original email content and writing style profile as context. "
        "The agent then composes the draft using this context."
    )
    args_schema: Type[BaseModel] = DraftEmailReplyInput

    # Injected fields
    user_id: str = Field(...)
    agent_name: str = Field(...)
    supabase_url: str = Field(...)
    supabase_key: str = Field(...)

    async def _arun(self, message_id: str, account: str, instructions: str = None) -> str:
        # 1. Check gmail connection has compose scope — if not, return re-auth message
        # 2. Fetch original email via get_gmail pattern
        # 3. Retrieve writing style from memory (entity="writing_style", tags=["communication", "style"])
        # 4. Return structured context: original email + writing style + instructions
        #    The agent composes the draft — this tool provides the ingredients.
        # 5. If no writing style found, include note about neutral tone

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        if channel in ("web", "telegram"):
            return (
                "Email Replies: When the user asks to reply to an email, use draft_email_reply "
                "to fetch the original email and your writing style context. Then compose a draft "
                "reply in the user's voice based on that context. Present the draft and wait for approval. "
                "If they request changes, regenerate with updated instructions. "
                "Only use send_email_reply after explicit approval. "
                "Never send without showing the draft first. "
                "After presenting each draft, include a hint: 'You can ask me to revise it "
                "(e.g., \"make it shorter\", \"more formal\"), or say \"send it\" to approve.'"
            )
        return None
```

**Writing style retrieval:** The tool calls `search_memories` (or uses the memory client directly) to find memories with `entity="writing_style"` and `tags=["communication", "style"]`. The onboarding service (SPEC-023) stores these as `core_identity` type memories. If no writing style memory exists, the tool returns the original email context with a note: "I don't have enough data on your writing style yet. This draft will use a neutral tone."

**Context assembly (not draft generation):** The tool fetches the original email and writing style, then returns them as structured context for the agent. The agent (which is already an LLM) uses this context plus any user instructions to compose the draft inline. This avoids a nested LLM call and leverages the agent's conversational context and memory.

### 4. Send Email Reply Tool

```python
class SendEmailReplyInput(BaseModel):
    message_id: str = Field(..., description="Gmail message ID to reply to")
    account: str = Field(..., description="Email address of the Gmail account to send from")
    body: str = Field(..., description="The approved reply text to send")
    subject: Optional[str] = Field(default=None, description="Override reply subject line")

class SendEmailReplyTool(BaseTool):
    name: str = "send_email_reply"
    description: str = (
        "Send an approved email reply. This action requires user approval. "
        "Only call this after the user has reviewed and approved the draft."
    )
    args_schema: Type[BaseModel] = SendEmailReplyInput

    async def _arun(self, message_id: str, account: str, body: str, subject: str = None) -> str:
        # 1. Get gmail credentials for this account via GmailToolProvider pattern
        # 2. Verify compose scope is present — if not, return re-auth message
        # 3. Fetch original email headers to populate context metadata
        # 4. Build GmailComposeService with credentials
        # 5. Call send_reply()
        # 6. Return confirmation with message ID
```

Because `send_email_reply` has tier `REQUIRES_APPROVAL`, the tool wrapper intercepts the call, stores it as a `pending_action` with the full `tool_args` (including the draft body), and creates a notification with `requires_approval=true`. The tool must populate `context` metadata with `original_subject` and `original_sender` (fetched from the original email headers) when creating the pending action, so the frontend/Telegram can render them in the approval card. The user sees the draft text in the notification and can approve or reject. On approval, the `PendingActionsService.approve_action()` executor calls the tool's `_arun` method.

### 5. Conversational Editing Flow

No new infrastructure needed. The flow is:

1. User: "Reply to Mike's email about the timeline"
2. Agent calls `draft_email_reply(message_id=..., account=..., instructions=None)`
3. Agent receives original email + writing style context, composes draft, presents it with revision hint
4. User: "Make it shorter and more casual"
5. Agent calls `draft_email_reply(message_id=..., account=..., instructions="shorter and more casual")` — or simply regenerates in-conversation using context
6. Agent presents revised draft
7. User: "Send it"
8. Agent calls `send_email_reply(message_id=..., account=..., body="<the approved draft>")`
9. Tool wrapper queues as pending_action (with `context.original_subject` and `context.original_sender`) → user approves → email sends

Step 5 is where the agent's conversational ability shines — it does not necessarily need to re-call the tool. It can revise the draft using the conversation context and its own capabilities. The `draft_email_reply` tool is primarily for the initial fetch-and-context step.

### 6. DB Migration

Migration is minimal — only tool registration. No schema changes needed since we reuse the existing `gmail` service name.

```sql
-- Register tools in the tools table (post-SPEC-019 schema: tools.type is TEXT)
INSERT INTO tools (name, type, description, config)
VALUES
  ('draft_email_reply', 'DraftEmailReplyTool',
   'Draft a reply to an email in the user''s writing style', '{}')
ON CONFLICT (name) DO UPDATE SET
  type = EXCLUDED.type,
  description = EXCLUDED.description,
  is_active = true,
  updated_at = now();

INSERT INTO tools (name, type, description, config)
VALUES
  ('send_email_reply', 'SendEmailReplyTool',
   'Send an approved email reply via Gmail', '{}')
ON CONFLICT (name) DO UPDATE SET
  type = EXCLUDED.type,
  description = EXCLUDED.description,
  is_active = true,
  updated_at = now();

-- Link tools to assistant agent via agent_tools
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT ac.id, t.id, true
FROM agent_configurations ac, tools t
WHERE ac.agent_name = 'assistant' AND t.name = 'draft_email_reply'
ON CONFLICT DO NOTHING;

INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT ac.id, t.id, true
FROM agent_configurations ac, tools t
WHERE ac.agent_name = 'assistant' AND t.name = 'send_email_reply'
ON CONFLICT DO NOTHING;
```

## Testing Requirements

### Unit Tests (required)

**`tests/chatServer/services/test_gmail_compose_service.py`:**
- Test `send_reply` constructs correct MIME headers (To, Subject, In-Reply-To, References)
- Test `send_reply` uses `Re: ` prefix on subject
- Test `send_reply` with subject override
- Test `send_reply` preserves threadId
- Test `send_reply` handles missing original headers gracefully
- Test RFC 2822 base64 encoding of message body

**`tests/chatServer/tools/test_gmail_compose_tools.py`:**
- Test `draft_email_reply` `_arun` happy path returns structured context (original email + writing style)
- Test `draft_email_reply` with no writing style in memory returns context with neutral tone note
- Test `draft_email_reply` with no Gmail connection returns helpful error
- Test `draft_email_reply` detects missing compose scope and returns re-auth message
- Test `draft_email_reply` with instructions passes them through in context
- Test `send_email_reply` approval tier is `REQUIRES_APPROVAL`
- Test `send_email_reply` `_arun` happy path returns confirmation
- Test `send_email_reply` populates `context` with `original_subject` and `original_sender`
- Test `send_email_reply` with missing compose scope returns re-auth message
- Test `send_email_reply` handles Gmail API errors gracefully
- Test `prompt_section` returns guidance strings

### AC-to-Test Mapping

| AC | Test Type | Test Function |
|----|-----------|---------------|
| AC-01 | Unit | `test_gmail_scopes_include_compose` |
| AC-02 | Unit | `test_missing_compose_scope_returns_reauth_message` |
| AC-04 | Unit | `test_draft_email_reply_happy_path` |
| AC-05 | Unit | `test_draft_no_writing_style_returns_generic` |
| AC-06 | Unit | `test_draft_approval_tier_auto_approve` |
| AC-08 | Unit | `test_send_reply_rfc2822_format` |
| AC-09 | Unit | `test_send_approval_tier_requires_approval` |
| AC-09a | Unit | `test_send_populates_context_metadata` |
| AC-12 | Unit | `test_compose_service_send_reply` |
| AC-13 | Unit | `test_compose_service_threading_headers` |
| AC-15 | Unit | `test_prompt_section_content` |
| AC-19 | Unit | `test_approval_inline_email_draft_preview` |
| AC-21 | Unit | `test_tool_registry_completeness` (existing validator) |
| AC-22 | Unit | All GmailComposeService tests |
| AC-23 | Unit | All draft tool tests |
| AC-24 | Unit | All send tool tests |

### Manual Verification (UAT)

- [ ] Connect Gmail (new user) — verify OAuth consent includes compose permission
- [ ] Verify Integrations page shows "Read & Send" for new connections
- [ ] For existing readonly connection: verify "Re-authorize for Send" button appears
- [ ] Click re-authorize, complete OAuth — verify connection updates to include compose scope
- [ ] Ask agent: "Reply to [person]'s last email about [topic]"
- [ ] Verify agent fetches the email, generates a draft in user's style, presents it clearly
- [ ] Verify draft presentation includes revision hint ("You can ask me to revise it...")
- [ ] Say "make it shorter" — verify agent revises and re-presents
- [ ] Say "send it" — verify agent calls send tool, pending_action notification appears
- [ ] Verify approval card shows styled email preview (To, Subject, Body) — NOT raw JSON
- [ ] Approve the pending action — verify email sends, confirmation appears
- [ ] Reject a pending action — verify email is NOT sent, agent acknowledges
- [ ] Ask agent to reply when no compose scope — verify re-auth prompt
- [ ] Verify sent email appears in the correct thread in Gmail (check threadId, In-Reply-To headers)
- [ ] Via Telegram: ask agent to draft a reply, approve via inline button — verify cross-channel works
- [ ] Via Telegram: verify long drafts are truncated at 4096 chars with "... [see full draft in web app]"

## Edge Cases

- **No writing style in memory:** Tool returns context with neutral professional tone note. Does not block the flow.
- **No compose scope on existing connection:** `draft_email_reply` and `send_email_reply` detect missing scope, return re-auth prompt with deep link to Settings > Integrations.
- **Expired token:** Uses existing `GmailToolProvider` refresh pattern. If refresh fails, returns reconnect message.
- **Original email deleted:** Gmail API returns 404 for the message ID. Tool returns "I couldn't find that email — it may have been deleted."
- **Reply to no-reply address:** The tool sends to whatever the `From` header says. If the reply bounces, that is normal email behavior — no special handling.
- **Very long email thread:** The `draft_email_reply` tool only fetches the single message, not the full thread. The agent uses conversation context for thread awareness.
- **Multiple Gmail accounts:** User specifies `account` parameter. If ambiguous, the agent should ask which account to use, same as `search_gmail` pattern.
- **Pending action expires:** Default 24h expiry on pending_actions. If the user does not approve in time, the draft expires and the agent can regenerate if asked.
- **Concurrent draft sessions:** Each draft is ephemeral in the conversation. No conflict — the pending_action stores the specific body text.
- **Unicode and special characters:** MIME text/plain encoding handles UTF-8 natively. No special handling needed.
- **Telegram draft exceeds 4096 chars:** Telegram messages have a 4096-character limit. If a draft body exceeds this, the Telegram notification truncates the body and appends "... [see full draft in web app]" with a link to the web UI.

## Functional Units (for PR Breakdown)

### FU-1: OAuth Scope + Migration + Tool Registration (backend-dev)

**Branch:** `feat/SPEC-029-oauth-tools`

**OAuth changes:**
- Add `gmail.compose` to `GMAIL_SCOPES` in `oauth_service.py` (one-line change)

**Migration:**
- Register `draft_email_reply` and `send_email_reply` in `tools` table, link to `assistant` via `agent_tools`

**Tool registration:**
- Add `draft_email_reply` and `send_email_reply` to `TOOL_APPROVAL_DEFAULTS` in `approval_tiers.py`
- Add both to `CANONICAL_TOOL_NAMES` in `test_tool_registry_validator.py`
- Add both to `TOOL_REGISTRY` in `agent_loader_db.py`

**Tests:**
- Verify `GMAIL_SCOPES` includes compose
- Tool registry validator passes with new tools

**ACs covered:** AC-01, AC-02, AC-03, AC-20, AC-21

### FU-2: Compose Service + Tools + Tests (backend-dev)

**Branch:** `feat/SPEC-029-compose-tools` (depends on FU-1 merge)

**New files:**
- `chatServer/services/gmail_compose_service.py` — `GmailComposeService` with `send_reply()`
- `chatServer/tools/gmail_compose_tools.py` — `DraftEmailReplyTool`, `SendEmailReplyTool`
- `tests/chatServer/services/test_gmail_compose_service.py`
- `tests/chatServer/tools/test_gmail_compose_tools.py`

**Key implementation notes:**
- `DraftEmailReplyTool` returns structured context (original email + writing style), NOT a composed draft
- `SendEmailReplyTool` uses existing `GmailToolProvider` pattern for credentials (same `gmail` connection)
- `SendEmailReplyTool` must populate `context` metadata with `original_subject` and `original_sender` when the pending action is created
- Both tools detect missing compose scope and return re-auth message

**ACs covered:** AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-09a, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-22, AC-23, AC-24

### FU-3: Frontend — Scope Status + Draft Preview (frontend-dev)

**Branch:** `feat/SPEC-029-frontend` (depends on FU-1 merge for updated scopes)

**Modified files:**
- `webApp/src/pages/Settings/Integrations.tsx` — show compose scope status per account, "Re-authorize for Send" button for readonly-only connections
- `webApp/src/components/ui/chat/ApprovalInlineMessage.tsx` — detect `tool_name === 'send_email_reply'` and render styled email draft preview (To/Subject/Body card) instead of raw JSON

**ACs covered:** AC-17, AC-18, AC-19

### Merge Order

```
FU-1 (OAuth + Registration) → FU-2 (Service + Tools)
FU-1 (OAuth + Registration) → FU-3 (Frontend)
```

FU-2 and FU-3 can run in parallel after FU-1 merges. FU-2 is the critical path — it contains the core functionality. FU-3 is independent frontend work.

## Downstream Contracts

### Cross-Domain: Tool Args Shape (for pending_actions context)

```json
{
  "tool_name": "send_email_reply",
  "tool_args": {
    "message_id": "18e1234abc",
    "account": "user@gmail.com",
    "body": "Hey Mike,\n\nSounds good — let's aim for Thursday.\n\nTim",
    "subject": null
  },
  "context": {
    "agent_name": "assistant",
    "session_id": "<uuid>",
    "original_subject": "Re: Renovation Timeline",
    "original_sender": "mike@example.com"
  }
}
```

The frontend `ApprovalInlineMessage` detects `tool_name === 'send_email_reply'` and renders `tool_args.body` as the draft body, `context.original_subject` as the subject, and `context.original_sender` as the recipient in a styled email preview card. Telegram renders the same data inline, truncating at 4096 characters if needed.

## Effort Estimation

| FU | Domain | Estimated Effort | Complexity |
|----|--------|-----------------|------------|
| FU-1 | Backend | 0.5 day | Low — one-line scope change, migration, tool registration |
| FU-2 | Backend | 2-3 days | Medium — new service, two tools, memory integration, tests |
| FU-3 | Frontend | 1-1.5 days | Medium — scope status UI, email draft preview component |
| **Total** | | **3.5-5 days** | |

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-24, plus AC-09a)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (tool_args shape for pending_actions)
- [x] Technical decisions reference principles from architecture-principles (A1, A6, A7, A9, A10, A11, A12, A13, A14, F1, S1)
- [x] Merge order is explicit and acyclic (FU-1 → FU-2, FU-1 → FU-3)
- [x] Out-of-scope is explicit (9 items listed)
- [x] Edge cases documented with expected behavior (11 cases)
- [x] Testing requirements map to ACs
- [x] Dependencies documented with status
- [x] `context` metadata contract specified for pending_action rendering

## Decisions (Resolved)

1. **~~Separate `gmail_compose` connection~~ → Reuse existing `gmail` connection.** Add `gmail.compose` to `GMAIL_SCOPES` for initial setup. Existing users re-auth when needed. No new service name, no schema changes.

2. **`draft_email_reply` as a dedicated tool.** Ensures writing style is always fetched. Cleaner than relying on the agent to chain `get_gmail` + `search_memories`.

3. **Approval via pending_actions for `send_email_reply`.** Agent presents draft in chat → user approves → tool sends. Uses existing SPEC-025 approval infrastructure.

4. **Google Cloud Console: `gmail.compose` scope.** Must be added to OAuth consent screen. Restricted scope — requires Google verification for >100 users. Non-blocking for dev/test.
