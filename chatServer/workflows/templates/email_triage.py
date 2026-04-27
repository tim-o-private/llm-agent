"""email-triage workflow template and step prompts."""

TEMPLATE = """\
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
- **description:** Search all connected Gmail accounts for recent unread emails. Read the top messages by recency. Output structured data: sender, subject, snippet, date, message_id, account.  # noqa: E501
- **gate:** none

### step-2: Categorize
- **agent:** email-classifier
- **depends_on:** [fetch-emails]
- **tools:** []
- **description:** Classify each email into urgent/actionable/informational/ignorable. Provide one-sentence reasoning per email. Suggest concrete next actions for urgent items.  # noqa: E501
- **gate:** none

### step-3: Summarize
- **agent:** triage-composer
- **depends_on:** [categorize]
- **tools:** [create_memories]
- **description:** Compose a triage summary. Urgent items first with suggested actions. Actionable items with context. Informational as one-liners. Store urgent/actionable items as memories for future reference.  # noqa: E501
- **gate:** none
"""

PROMPT_CATEGORIZE = """\
# Email Categorization

You are classifying emails by urgency for the user's daily triage.

## Categories

- **urgent**: Needs response within hours. Examples: client escalations, time-sensitive requests, meeting conflicts, financial matters requiring action.  # noqa: E501
- **actionable**: Needs response but not time-sensitive. Examples: project updates requiring feedback, scheduling requests, non-urgent questions.  # noqa: E501
- **informational**: Worth knowing, no action needed. Examples: team announcements, status updates, newsletters the user subscribed to intentionally.  # noqa: E501
- **ignorable**: No value. Examples: automated notifications, marketing emails, newsletters they didn't subscribe to, social media alerts.  # noqa: E501

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

Keep total output under 500 words. Be decisive — when in doubt between actionable and informational, choose informational.  # noqa: E501
"""

PROMPT_SUMMARIZE = """\
# Triage Summary Composition

You are composing a triage summary from categorized emails.

## Structure

1. **Urgent items first** — each with a suggested next action
2. **Actionable items** — brief context on what's needed
3. **Informational items** — one-line mentions only
4. **Ignorable** — just a count ("12 emails skipped")

## Style

- Be concise and direct
- Use the user's name for senders they know (if identifiable from context)
- Frame urgency in terms of deadlines or consequences, not just labels
- Keep total summary under 400 words

## Memory Storage

For each urgent or actionable email, call create_memories with:
- entity: "email_triage"
- content: One-sentence summary of the email and why it matters
- tags: ["email", "triage"]
"""
