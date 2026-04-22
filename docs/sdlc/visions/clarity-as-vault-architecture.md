# Clarity as Vault — Architecture Notes

**Status:** Implementation-altitude companion to [clarity-as-vault.md](./clarity-as-vault.md). Read that first for the product vision, problems solved, and wedge. This doc covers runtime choices, state mechanics, and build-time decisions that belong in specs rather than the vision.

**Authors:** Tim + Claude (2026-04-16 → 2026-04-17)

---

## Runtime architecture

Two runtimes, one architecture. The **workflow engine** (SPEC-036/037, `chatServer/workflows/run_manager.py`) is the dispatch layer above both: reads workflow text files, walks the graph, invokes the right agent at each node. Agent frontmatter tells the engine which model; the runtime handles the model call.

### Dev runtime: `claude -p`

Tim's personal development loop, authenticated via his existing Claude Max 5x subscription (OAuth — legal for personal dev use; the subscription-in-products ban does not apply to a developer using their own subscription against their own code). Zero marginal cost. Stages 1–3 prototype here for speed.

### Prod runtime: Deep Agents

Ships via Deep Agents (LangChain), already a dependency (`deep_agent_builder.py`; SPEC-044's bwrap backend is a Deep Agents backend). Chosen over Agent SDK for:

- **Model flexibility** — per-task routing across Opus/Sonnet/Haiku and non-Anthropic providers.
- **ZDR** — compose across providers instead of locking to one vendor's policy.
- **LangChain ecosystem** — middleware, subagent spawning, streaming, filesystem backends.
- **Already integrated** — SPEC-044 bwrap backend, `deep_agent_builder.py`.

### Runtime layer mapping

| Layer | Dev (`claude -p`) | Prod (Deep Agents) |
|---|---|---|
| Runtime | `claude` CLI, OAuth, personal use | Deep Agents, API key, per-model routing |
| Scaffolding | Hooks (SessionStart / PreToolUse / PostToolUse / SessionEnd) | Middleware stack |
| Capabilities | Skills as markdown (`.claude/skills/`, auto-discovered) | Skills translated to subagents/tools via loader |
| Tools | MCP servers — Gmail, Calendar, custom | Same MCP servers |
| Isolation | bwrap (SPEC-044) | bwrap (SPEC-044) |
| Storage | Git-backed markdown vault, per user | Same |
| Scheduling | Cron → `claude -p "..." --system-prompt "..."` | Cron → Deep Agent invocation |
| UI | Web app renders vault | Same |

### What ports cleanly vs. needs translation

Ports cleanly (design once):
- Vault format, ownership frontmatter, ledger protocol
- MCP tool definitions
- Skills-as-markdown content
- bwrap sandbox
- UI

Needs translation (dev → prod):
- **Hooks → middleware.** Same concept, different API. Build a thin shim so scaffolding is expressed once; accept small translation cost.
- **Skill loading.** `claude` auto-discovers; Deep Agents needs explicit registration. Shared loader reads the same markdown files.
- **System prompt injection.** `claude --system-prompt` in dev; Deep Agents `instructions` parameter in prod.

### Why prototype on `claude -p` first

- No infra to wire up. Vault as working directory + `claude -p` = working agent in minutes.
- Max 5x covers all dev iteration cost.
- Skills, hooks, and vault format get tested against the real Claude Code harness before runtime commit.
- Claude Code is the reference UX we're generalizing; prototyping there keeps us honest about what properties matter.

### Auth (prod)

- **OpenRouter BYOK-per-user (default)** — we provision a per-user OpenRouter key; user pays OpenRouter directly or via pass-through billing; token usage never touches our ceiling. Covers Anthropic, OpenAI, Google, Groq, and most other providers, preserving the per-agent model-routing story. ZDR becomes a per-route user choice (we surface the indicator; user selects).
- **Central `ANTHROPIC_API_KEY` under Commercial Terms (optional fallback)** — for users who don't want to provision their own key. Standard SaaS model, sanctioned. Capped.
- **No OAuth/subscription tokens** — banned in third-party products per Feb–Apr 2026 enforcement.
- **Bedrock / Vertex** — alternate billing backends if a user's procurement demands cloud-native.
- **No "Login with Claude.ai"** — prohibited without prior Anthropic approval.

---

## State split: Postgres vs. vault

Trust boundary is the line. If forging state by editing a file could compromise safety, billing, or privacy, it belongs in Postgres. Otherwise it's vault.

**Postgres (secure state, RLS-enforced):**
- Users, auth, sessions, tokens, refresh tokens
- Encrypted secrets — OAuth tokens for Gmail/Calendar, BYOK API keys
- Approval records — `user U authorized action A at time T`
- Billing and usage tracking
- Runtime metadata — vault path mapping, sandbox resource limits, rate limits
- Security-sensitive audit log (separate from the user-facing ledger in the vault)

**Vault (transparent, user- and agent-editable):**
- Notes, journal, threads, entity docs
- Workflow definitions and agent markdown
- Skills
- Ledger entries (human-readable "what happened" log)
- Today, morning briefs, summaries
- Proposed actions awaiting approval (content; authorization lives in Postgres)

### Approval lane mechanism

1. Agent writes proposal doc to vault: `proposals/2026-04-17-send-email-to-sarah.md` with full context.
2. UI renders proposal.
3. User approves → Postgres row: `approvals(user_id, proposal_path, approved_at, nonce)`.
4. Workflow engine only executes when a matching Postgres row exists.
5. Editing the proposal file alone does nothing; editing the Postgres row requires DB auth.
6. Both records stay as audit trail.

---

## Model routing (per-agent)

Routing is a property of each agent, declared in frontmatter:

```yaml
---
name: today-writer
model: sonnet-4.6
tools: Read, Write
---
```

Workflow engine reads the agent file; runtime honors `model:`. Changing routing = editing one line of text. Users (or the agent itself) edit these files; power users add their own.

### Initial defaults (living set)

| Agent | Default model | Rationale |
|---|---|---|
| `today-writer` | Sonnet 4.6 | Judgment + writing |
| `entity-refresher` | Haiku 4.5 | Extraction/summarization |
| `capture-router` | Haiku 4.5 | High volume, low stakes |
| `action-executor` | Sonnet 4.6 | Execute carefully |
| `thread-planner` | Opus 4.7 | Real judgment |
| `annotation-responder` | Sonnet 4.6 | Context-aware writing |

Tune with measurement once Stage 1 is running.

---

## Cost / operational

Default path (OpenRouter BYOK-per-user) externalizes token cost to the user — model usage doesn't hit a central billing ceiling we have to defend against runaway agents. Subscription pays for the software, hosting, skills library, updates, support. This is the clean SaaS shape.

Still worth doing regardless of billing backend:

- **Model routing** (above) — cheapest model that does the job. Lower cost → agent can run more aggressively without user friction.
- **Prompt caching** — Anthropic caching (5-min TTL, 1-hour extended beta) for vault-context payloads shared across invocations.
- **Tiered invocation cadence** — expensive loops (Today regeneration) scheduled; cheap loops (capture routing, approval execution) on demand. Don't poll what you can observe.
- **ZDR as user choice** — surface a privacy indicator per route; user picks. Our job is disclosure, not contract negotiation with providers.

### Fallback path (central Anthropic key)

For users who don't provision their own OpenRouter key. Implications:

- Costs scale with usage — must be capped per user.
- API keys have TPM/RPM limits; per-user subprocess spawning needs rate-limit management on our side.
- Commercial Terms replace Consumer Terms once API-key auth is active.
- At scale: a conversation with Anthropic sales for written clarity on centralized-key-serving-many-users is low-risk insurance.

---

## UI architecture

Web app renders two stores: **vault** (markdown) for content/behavior, **Postgres** for security-boundary state.

Responsibilities:
- Render vault — Today primary; doc browser + graph view secondary.
- Render Postgres state where trust matters — approval queue, auth status, billing/usage.
- Approval lane widget — renders proposal from vault; approval action hits Postgres; runtime execution gated by Postgres row.
- Capture input (text; voice Stage 2+) — routes into vault via capture workflow.
- Stream agent activity — SSE over file changes + Postgres change notifications.
- Chat (Stage 3+) — routes through the same primitives as every other transaction.

Not owned by the web app:
- Content state (vault owns).
- Security state (Postgres owns).
- Agent execution (runtime owns).

Clean separation: vault content is also openable in Obsidian (feature + trust signal); security state stays behind the same auth layer we already have.

---

## Research: Anthropic commercial terms

*Researched 2026-04-16. Sources current through April 2026 enforcement actions.*

### Summary

Architecture is viable under current terms. **Dev: `claude -p` + personal Max 5x subscription** (legal personal dev use). **Prod: Deep Agents + API-key auth under Commercial Terms.** Agent SDK would be viable but unnecessarily Anthropic-locked; model flexibility and ZDR composability are worth the framework choice.

### The actual line (Feb–Apr 2026 enforcement)

- **Banned:** Using OAuth tokens from Claude Free/Pro/Max subscriptions in third-party products. Enforcement took down OpenClaw, OpenCode, Goose. Official language: *"Using OAuth tokens obtained through Claude Free, Pro, or Max accounts in any other product, tool, or service — including the Agent SDK — is not permitted."*
- **Permitted:** API-key authentication (`ANTHROPIC_API_KEY`) in products built on Agent SDK, Messages API, or direct `claude` invocation. Commercial Terms govern; explicitly sanctioned for exposing Claude to end users.
- **Rationale (per Anthropic engineering):** Subscription-token wrappers create opaque traffic patterns without telemetry, making support and abuse detection impossible.

### Implications for Clarity

1. Dev on `claude -p` with personal subscription is fine — standard practice for single-developer dev loops.
2. Prod runs on Deep Agents — provider-agnostic, supports model routing, composes ZDR.
3. No "Login with Claude.ai" without prior Anthropic approval.
4. API-key auth (ours or BYOK) in prod, not OAuth/subscription tokens.
5. Bedrock / Vertex available as alternate Anthropic billing backends.

### Key sources

- [Agent SDK Overview — code.claude.com](https://code.claude.com/docs/en/agent-sdk/overview)
- [Claude Code ToS Explained — autonomee.ai](https://autonomee.ai/blog/claude-code-terms-of-service-explained/)
- [Anthropic clarifies ban on third-party tool access — The Register](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/)
- [OpenClaw Ban: OAuth vs API Key — MindStudio](https://www.mindstudio.ai/blog/anthropic-openclaw-ban-oauth-authentication)

---

## Implementation open questions

1. **ZDR disclosure UX.** With OpenRouter BYOK-per-user, ZDR becomes a per-route indicator the user sees when picking or reviewing a model choice. Question: where does this live in the UI, and what's the source of truth for whether a given OpenRouter route is ZDR? Stage 3+ concern.
2. **Hook ↔ middleware abstraction.** Build a thin shim so scaffolding is expressed once, or accept duplicate logic? Leaning: shim, because the abstraction is small and portability buys flexibility.
3. **Multi-user storage model.** One vault per user. Git remote per user? Local volumes? Fly.io persistent volumes? Ties into SPEC-044 sandboxing design.
4. **Conflict resolution.** Agent and user editing the same doc concurrently. Probably: file-level flocks; agent defers to user-edited files and re-reads after.
5. **Voice capture tech.** Web Speech API vs. Whisper via MCP. Stage 2 decision.
6. **First-party vs BYO MCP tools.** Gmail/Calendar — do we host MCP servers or require users to bring their own? Security, ops, and privacy implications.
7. **Vault versioning cadence.** Commit per agent action? Per session? Scheduled? Affects audit and revert UX.
8. **Daily brief triggering.** Fixed cron vs. smart triggering (first laptop open of the morning). First version: fixed cron.
9. **Cmd-K chat session model (Stage 3+).** One persistent session or per-invocation?
10. **Workflow file format.** Deferred — ride existing conventions (Deep Agents, SPEC-036, Claude Code). No new DSL. Resolves during Stage 1.
