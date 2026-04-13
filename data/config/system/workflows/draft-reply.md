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
