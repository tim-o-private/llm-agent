"""draft-reply workflow template and step prompts."""

TEMPLATE = """\
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
- **depends_on:** [fetch-context]
- **tools:** []
- **description:** Generate a reply draft matching the user's voice. Match greeting/signoff patterns, typical message length, and vocabulary from the writing style profile. Incorporate any user instructions.
- **gate:** none

### step-3: Present for Approval
- **agent:** approval-presenter
- **depends_on:** [compose-draft]
- **tools:** []
- **node_type:** gate
- **gate_policy:** human-required
- **description:** Present the composed draft to the user. Show subject, recipient, and body in a styled email preview. User can approve (send), reject (cancel), or revise (provide feedback and re-compose).
- **gate:** none

### step-4: Send
- **agent:** email-sender
- **depends_on:** [present-for-approval]
- **tools:** [send_email_reply]
- **description:** Send the approved draft via Gmail. Confirm send with message ID and thread ID.
- **gate:** none
"""

PROMPT_COMPOSE_DRAFT = """\
# Email Draft Composition

You are drafting an email reply in the user's voice.

## Writing Style

Use the writing style profile provided in the context:
- Match their typical greeting (e.g., "Hi [name]," vs "Hey!" vs no greeting)
- Match their typical signoff (e.g., "Best," vs "Thanks," vs just their name)
- Match their typical message length — if they write 2-sentence replies, don't write 5 paragraphs
- Use their vocabulary patterns — formal vs casual, contractions vs not

If no writing style profile is available, use a neutral professional tone:
- "Hi [name]," greeting
- "Best, [user's name]" signoff
- Clear and concise, 2-3 paragraphs max

## Instructions

1. Read the original email carefully — understand what's being asked
2. If the user provided specific instructions, follow them precisely
3. Draft a reply that sounds like the user wrote it, not like an AI
4. Don't be overly formal or overly casual — match the user's style
5. Keep it concise — match the typical length of the user's replies

## Output Format

Return the draft as plain text, ready to send:
- Subject line (usually "Re: [original subject]")
- Body text with greeting, content, and signoff
- No metadata, no commentary — just the email text
"""

# Max revision count before giving up
MAX_REVISIONS = 3
