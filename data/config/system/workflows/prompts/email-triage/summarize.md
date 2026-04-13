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
