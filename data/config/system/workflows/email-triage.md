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
- **depends_on:** [fetch-emails]
- **tools:** []
- **model:** openai:gpt-4o-mini
- **description:** Classify each email into urgent/actionable/informational/ignorable. Provide one-sentence reasoning per email. Suggest concrete next actions for urgent items.
- **gate:** none

### step-3: Summarize
- **agent:** triage-composer
- **depends_on:** [categorize]
- **tools:** [create_memories]
- **description:** Compose a triage summary. Urgent items first with suggested actions. Actionable items with context. Informational as one-liners. Store urgent/actionable items as memories for future reference.
- **gate:** none
