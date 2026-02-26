# SPEC-029: Draft-Reply Workflow

> **Status:** Placeholder
> **Author:** Tim + Claude (Product)
> **Created:** 2026-02-24
> **PRD:** PRD-002 (Expand the World), Workstream 4

## Goal

Enable the agent to draft email replies in the user's voice and send them with approval. This is the first Act-tier capability — the agent does something on the user's behalf, with explicit approval. Uses the writing style profile from SPEC-023's sent message analysis.

## Dependencies

- **SPEC-023** (Email Onboarding Pipeline) — provides writing style profile in memory
- **SPEC-025** (Unified Notification Experience) — inline approval flow for draft review

## Key Design Points (from PRD-002)

- **MVP scope:** Agent drafts replies when it's confident it would help. No inline editing — user says "change the second sentence to X" and agent revises conversationally. No trust tier graduation system yet.
- **Flow:** User asks to reply → agent finds email, drafts using writing style profile → presents draft in chat → user approves/requests changes → on approval, agent sends via Gmail compose API.
- **Writing style:** SPEC-023 extracts tone, length, greeting/signoff patterns. Draft tool uses this in its system prompt.
- **Trust tier:** Starts at Recommend — agent proposes, user approves every time. Graduation to Act (auto-send) is future scope, requires a trust tier system that doesn't exist yet.
- **OAuth:** Requires Gmail compose scope (`gmail.compose`) — new consent beyond current `gmail.readonly`. Separate from calendar scope.

## What Needs Drafting

- `draft_email_reply` tool design — how it fetches the target email, loads writing style from memory, generates draft
- `send_email_draft` tool design — approval-gated, sends via Gmail API
- OAuth scope upgrade flow — user already has `gmail.readonly`, needs to re-consent for `gmail.compose`
- How the agent decides when to proactively suggest drafting (vs. waiting to be asked)
- Conversational editing flow — how revision requests are handled

## Rough Scope

| Area | Estimated Changes |
|------|-------------------|
| Backend | `DraftEmailReplyTool`, `SendEmailDraftTool`, Gmail compose service |
| Database | Tool registration, possibly draft storage table |
| OAuth | New Gmail compose scope, re-consent flow |
| Frontend | None for MVP (drafts render as chat messages, approval via SPEC-025 inline buttons) |
| Prompt | Tool guidance for when to draft, writing style injection |

## Open Questions

- Thread reply vs. new message — start with replies only?
- Attachments — out of scope for MVP (text-only)?
- How to handle the scope upgrade gracefully when user already has readonly?
- Should drafts be stored persistently (for revision history) or are they ephemeral chat messages?
- What's the minimum writing style signal needed before the agent should attempt drafting?

---

*This is a placeholder. Full spec will be drafted when Phase 2a (SPEC-025, SPEC-016, SPEC-027) is complete. The trust tier graduation system will be a separate design exercise.*
