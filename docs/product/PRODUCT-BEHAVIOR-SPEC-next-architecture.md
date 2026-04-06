# Product Behavior Spec: Next Architecture

> **Status:** Draft v1
> **Created:** 2026-04-06
> **Author:** Tim + Claude (Product)
> **Context:** Consolidation of HQ operating model with Clarity product vision
> **Purpose:** Define product behavior before technical design. This is NOT a PRD or implementation spec. It answers: "When X happens, what does the user experience?"

---

## Governing Principle

Clarity is a personal agent that exercises executive function on behalf of individuals. The rearchitecture changes how Clarity works internally (filesystem-based config, graph workflows, CLI tools) but not what it is. The user experience described in VISION.md remains the north star.

**What changes:** The execution model. LangChain tool chains become graph-based workflows. Custom Python tool classes become CLI tools called server-side. DB-stored agent config becomes filesystem-based definitions. The agent gains the ability to improve itself.

**What doesn't change:** Web chat as primary interface. Trust tiers. The personality. The goal of decreasing user time in the product.

---

## 1. Conversational Experience

### 1.1 Primary Interface: Web Chat

The web chat remains the primary interface. 90% of users will never open a terminal. The experience is conversational — the user talks to Clarity, Clarity responds, takes action, and reports back.

**When a user sends a message:**
- If it's conversational (question, correction, feedback), the agent responds directly.
- If it triggers a multi-step process (e.g., "draft a reply to Mike," "create a weekly report"), the agent acknowledges, executes the relevant workflow, and streams progress or results back to chat.
- The user should not perceive a difference between "the agent answered me" and "the agent ran a workflow." Both feel like talking to a person.

**When a workflow is running:**
- Progress appears inline in chat (not in a separate panel or dashboard).
- The user can interrupt, redirect, or cancel at any time via conversation.
- Long-running workflows (e.g., background research) notify via the existing notification system (web + Telegram).

### 1.2 What the User Never Sees (Unless They Look)

- Graph template definitions
- Agent definition files
- CLI tool invocations
- Filesystem operations
- Prompt text

These are implementation details. The default user interacts through conversation and notifications only.

---

## 2. Tool Model

### 2.1 CLI Tools as the Primary Interface

The agent uses CLI tools (like `gog` for Google services, search tools, etc.) as its primary means of interacting with external services. These tools run server-side, not on the user's machine.

### 2.2 Server-Side Auth, Agent-Accessible Capabilities

**User-facing flow:** The user connects services (Gmail, Calendar, etc.) via OAuth in the web app. Click "Connect Gmail," authorize in Google's consent screen, done.

**What happens under the hood:** Tokens are stored server-side, never exposed to the agent. The server exposes authenticated capabilities that the agent can invoke. The agent sees "I can search emails" and "I can send emails" — it never sees tokens, secrets, or raw HTTP endpoints.

**Hard requirement:** Agents cannot access secrets directly or access the open web except through controlled, auditable capability interfaces.

> Every action the agent takes on an external service is logged, attributable, auditable, and gated by the user's trust configuration.

---

## 3. Trust & Permissions

### 3.1 Trust Tiers (Unchanged from VISION.md)

| Tier | Agent Behavior | User Experience |
|------|---------------|----------------|
| **Inform** | "Here's what I noticed" | Digest, flags, summaries |
| **Recommend** | "Here's what I think you should do" | Suggested actions, draft responses, one-tap approve |
| **Act** | Agent takes action, reports after | Auto-triage, auto-reply, auto-schedule |

Everything starts at Inform. Graduation is per-domain, agent-proposed, user-approved.

### 3.2 Dynamic Allowlist

The agent's permissions are defined in an allowlist that specifies which capabilities it can use and at what trust tier. This allowlist starts restricted and expands as the user and agent gain confidence.

---

## 4. Self-Improvement

### 4.1 What the Agent Can Improve

The agent maintains a filesystem of configuration that defines its behavior: prompt definitions, workflow templates, learned preferences, scheduling rules. The agent can modify parts of this configuration to improve over time.

### 4.2 Modification Tiers (MVP)

Config is split into two layers:

**Everything except security** — agent can edit, user gets a tap-to-approve notification:

| What | Example |
|------|---------|
| Prompt tone, format, length, greeting style | Agent shortens briefings after user feedback |
| New workflow templates, scheduling | Agent creates a "weekly report" workflow |
| How agent categorizes input, response strategies | Agent changes how it prioritizes email senders |
| Memory retention rules, learned preferences | Agent adjusts what it remembers about user patterns |

**Security boundary** — agent cannot edit directly, requires explicit confirmation:

| What | Example |
|------|---------|
| Tool allowlists (which tools the agent can use) | Agent requests access to send emails |
| Approval tiers (what trust level per tool) | Agent proposes graduating from Recommend to Act |
| Auth scopes (which services are connected) | Agent suggests connecting Google Calendar |
| Sub-agent permissions | Agent wants to create a helper with tool access |

**Critical constraint:** The boundary between "everything else" and "security" is determined by which files/fields are being modified, not by what the agent says it's doing. This classification is immutable.

> **Future refinement:** As the product matures, the non-security layer may split further (e.g., style changes auto-approved without tap, behavioral changes require review). For MVP, a single approval UX for all non-security changes is sufficient.

### 4.3 Disclosure Model

Disclosure level is a function of trust tier — not a user setting.

| Trust Tier | Disclosure Behavior |
|------------|-------------------|
| **Inform** (new user/domain) | Full transparency: "I'd like to change how I handle X. Here's what I want to do differently. Approve?" |
| **Recommend** (established) | Middle ground: "I adjusted how I prioritize your notifications. Calendar conflicts now surface first. Let me know if that feels off." |
| **Act** (earned) | Silent with periodic summary. Monthly: "Here's how my judgment has evolved this month." |

**Anti-pattern:** This is never a settings page.

### 4.4 Changelog View

A pullable (not pushed) record of what the agent has changed about itself. Accessible via conversation ("what have you changed recently?") or via the file browser (git history of config files).

### 4.5 Rollback

If user feedback turns negative after a change, the agent identifies the causal change and reverts it. Auto-rollback triggers if behavioral metrics degrade.

### 4.6 Introspection Loop

The agent periodically introspects on its own performance and can: create new workflows, improve prompts, or propose new capabilities (subject to modification tier rules).

---

## 5. "Open the Hood" — Power User Experience

### 5.1 File Browser (MVP)

Power users can open a file browser in the web app that shows the agent's configuration filesystem. Mutable files are editable directly. Immutable files (security boundary) are visible but require explicit unlock.

### 5.2 The Red Button

An explicit, scary, opt-in mode that unlocks the immutable layer for direct editing. Buried in settings, not discoverable by accident.

---

## 6. Workflows (Graph-Based)

Multi-step processes implemented as graph templates. The user never sees "workflow" or "graph" — they experience briefings, drafts, and approvals.

---

## 7. PRD-002 Feature Disposition

PRD-002 features survive conceptually but not architecturally. Briefings, draft-reply, calendar awareness are reimplemented as graph workflows calling CLI tools. PRD-002 as a document is deprecated.

---

## 8. Security Requirements

- Agents cannot access secrets, tokens, or credentials directly
- Agents cannot make arbitrary HTTP requests
- External data tagged as untrusted at ingestion
- Sub-agent permissions capped at parent's level
- Prompt injection evaluation required as recurring operational process
- Full audit trail on all agent actions and config modifications

---

## 9. Open Questions for Architecture

(Resolved — see `docs/product/ARCHITECTURE-PROPOSAL-next-gen.md`)
