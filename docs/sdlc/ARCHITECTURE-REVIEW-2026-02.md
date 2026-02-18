# Architecture Review & Priority Analysis — February 2026

## Executive Summary

llm-agent has solid foundations across all three components (webApp, chatServer, src/core) but is stuck in a "90% done" state where individual features work in isolation but lack the connective tissue to deliver an end-to-end experience. This review maps the current state, compares against OpenClaw's architecture (which solves the same "unified personal AI assistant" problem at scale), and proposes a prioritized path to delivering real value.

---

## Current State Assessment

### What Works

| Component | Feature | Status |
|-----------|---------|--------|
| chatServer | Chat endpoint (`/api/chat`) | Working — agent loading, memory, content block normalization |
| chatServer | Actions/approval system (`/api/actions`) | Working — pending actions, audit trail |
| chatServer | Gmail tools | Working — `gmail_tools.py`, vault token integration |
| chatServer | Notification service | Implemented — DB + Telegram routing |
| chatServer | Telegram bot | Implemented — webhook handler, channel linking |
| chatServer | Scheduled execution | Implemented — APScheduler, `agent_execution_results` storage |
| chatServer | Chat history | Implemented — `PostgresChatMessageHistory`, history router |
| webApp | Auth flow | Working — Supabase auth, protected routes, JWT |
| webApp | TodayView (task management) | Working — full CRUD, drag-and-drop, keyboard nav, subtasks |
| webApp | CoachPage (chat) | Working — `ChatPanel` component |
| webApp | Settings/Integrations | Working — Gmail connection, Telegram linking |
| webApp | Design system | Established — semantic tokens, custom components |
| DB | Schema | 37 migrations — agents, tools, sessions, notifications, channels, approvals, schedules |

### What's Half-Built (the "90% problem")

1. **Notifications exist but have no frontend consumer.** `notifications_router.py` and `notification_service.py` are implemented. `useNotificationHooks.ts` exists. But there's no notification bell, inbox, or toast integration in `AppShell`. Users can't see when the agent acts on their behalf.

2. **Telegram is wired but not deployed.** Bot code works, linking UI exists, but `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_URL` aren't set on Fly.io. Zero users can actually use it.

3. **Scheduled execution runs but has no visibility.** `scheduled_execution_service.py` stores results in `agent_execution_results`, but there's no UI to view past runs or manage schedules. The agent acts autonomously with no window into what it did.

4. **Chat history is stored but not surfaced.** `chat_history_router.py` and `useChatHistoryHooks.ts` exist, but `CoachPage` doesn't load previous conversations. Every session feels like starting from scratch.

5. **Unified sessions designed but not implemented.** SPEC-005 describes the vision (all channels share `chat_sessions`), but it's blocked by SPEC-004 (test coverage). The `channel` column was added to `chat_sessions` but no code routes through it.

6. **SPEC-001/002/003 implemented but untested.** All three features (notifications, telegram, scheduled exec) lack test coverage, which blocks SPEC-005 and all downstream work.

### What's Missing Entirely

- **No real-time feedback during agent execution.** Chat is request/response. No streaming, no "agent is thinking" indicator, no intermediate step visibility.
- **No conversation list/history browser.** The ChatPanel shows one conversation. No way to see past sessions, search, or switch.
- **No agent configuration UI.** Agent selection, prompt customization, and tool configuration are DB-only. No user-facing controls.
- **No webhook/automation triggers.** Unlike OpenClaw's webhook + cron + pub/sub approach, there's no way for external events to trigger agent actions.
- **No multi-agent orchestration.** The roadmap mentions agent-to-agent communication, but there's no protocol for it.

---

## OpenClaw Comparison

OpenClaw (206k stars, MIT license) solves the same core problem — a personal AI assistant accessible across channels — but at a much more mature stage. Key architectural lessons:

### What OpenClaw Gets Right

| Concept | OpenClaw | llm-agent equivalent |
|---------|----------|---------------------|
| **Gateway (control plane)** | WebSocket server at `ws://127.0.0.1:18789` — all channels connect to a single event bus | No equivalent. Each channel has its own handler with duplicated logic |
| **Channel extensions** | Modular `extensions/` directory — each channel is a plugin | Telegram is hardcoded in `channels/telegram_bot.py`. No plugin model |
| **Skills platform** | Bundled, managed, and workspace skills with a registry (ClawHub) | Agent tools loaded from DB, but no skill marketplace or sharing |
| **Canvas + A2UI** | Agent-driven visual workspace — the agent can generate interactive UI | No equivalent. The agent returns plain text |
| **Always-on daemon** | `launchd`/`systemd` service — the assistant is always running | Server-only. No local daemon concept |
| **Security model** | Sandbox modes (main vs non-main), DM pairing approval | Tool approval system exists but simpler |
| **Device integration** | macOS/iOS/Android companion apps with camera, location, etc. | Web-only |

### What's Transferable (vs. What's Not Worth Copying)

**Worth adopting:**
1. **Event bus / message routing pattern** — instead of each channel reimplementing agent loading + approval + history, a central event bus receives messages from any channel and routes them through a shared pipeline. This is essentially what SPEC-005 (unified sessions) describes, but formalized.
2. **Skill/tool composability** — tools should be composable units that can be added/removed per user/agent without DB migrations.
3. **Notification as a first-class channel** — OpenClaw treats every output channel equally. Notifications aren't an afterthought.

**Not worth copying (yet):**
- Device integration (iOS/Android) — too much scope
- Canvas/A2UI — requires a fundamentally different rendering model
- Local daemon architecture — llm-agent is cloud-hosted, which is fine for now

---

## Priority Recommendations

### Tier 1: "Make What Exists Work" (unblock value delivery)

These are the items that connect existing, working pieces to create an actually usable product.

#### 1. Surface notifications in the web UI

**Why:** The agent can already act (scheduled execution, tool approval requests) but the user has no way to know about it. This is the single biggest gap between "demo" and "useful."

**What:**
- Add a `NotificationBadge` component to `AppShell` navigation
- Create a `NotificationInbox` panel/page using existing `useNotificationHooks.ts`
- Wire notification polling (already built at 10s intervals in hooks)
- Show toast for new notifications

**Depends on:** Nothing. All backend pieces exist.

#### 2. Load chat history in CoachPage

**Why:** Conversations that reset every visit make the agent feel stateless and useless. Chat history is already stored — it just needs to be loaded.

**What:**
- Add session list sidebar to CoachPage using `useChatSessionHooks.ts`
- Load message history on session select using `useChatHistoryHooks.ts`
- Create new sessions explicitly rather than implicitly

**Depends on:** Nothing. Backend endpoints and hooks exist.

#### 3. Deploy Telegram integration

**Why:** This is literally one CLI command (`flyctl secrets set`) away from working. Telegram gives the agent a mobile-accessible channel without building a mobile app.

**What:**
- Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_URL` as Fly secrets
- Test the webhook flow end-to-end
- Document the setup

**Depends on:** Fly.io access, bot token from BotFather.

### Tier 2: "Make It Reliable" (test + unify)

#### 4. SPEC-004: Test coverage for notifications, telegram, scheduled execution

**Why:** Untested code is unreliable code. These three features are already "implemented" but shipping them without tests means every deploy is a gamble. This also unblocks SPEC-005.

**What:** The spec already exists with 5 parallel tasks defined.

#### 5. SPEC-005: Unified sessions

**Why:** Without this, each channel is an island. The user can't see their Telegram conversations in the web UI, or get notified about a scheduled run's results in Telegram.

**What:** The spec already exists. It's the architectural foundation for the event-bus pattern OpenClaw uses.

### Tier 3: "Make It Powerful" (new capabilities)

#### 6. Scheduled execution dashboard

**Why:** The agent can run on a schedule, but users can't see what it did. This closes the autonomy loop: schedule -> execute -> review results.

**What:**
- New page listing `agent_execution_results`
- CRUD for `agent_schedules`
- Inline result viewer

#### 7. Agent configuration UI

**Why:** Currently, switching agents or customizing prompts requires DB changes. Users should be able to select agents, customize system prompts, and enable/disable tools from the web UI.

**What:**
- Expose agent list endpoint
- Build agent picker in CoachPage
- Surface `prompt_customizations` API in settings

#### 8. Streaming/real-time agent responses

**Why:** The current request/response model makes the agent feel slow and opaque. Streaming shows the agent's thinking process and reduces perceived latency.

**What:**
- Add SSE or WebSocket endpoint for chat
- Stream intermediate steps and partial responses
- Update ChatPanel to render incrementally

---

## Recommended Execution Order

```
Phase 1 (Immediate — "ship what's built"):
  [1] Notification UI in AppShell
  [2] Chat history loading in CoachPage
  [3] Deploy Telegram (Fly secrets)

Phase 2 (Foundation — "make it solid"):
  [4] SPEC-004 test coverage
  [5] SPEC-005 unified sessions

Phase 3 (Growth — "make it powerful"):
  [6] Scheduled execution dashboard
  [7] Agent configuration UI
  [8] Streaming responses
```

Phase 1 items are independent and can be done in parallel. They transform the platform from "features exist in code" to "features work for users."

---

## Comparison to Existing Roadmap

The existing ROADMAP.md and BACKLOG.md are well-organized but have a sequencing problem: SPEC-004 (tests) blocks everything, creating a bottleneck. The recommendation above re-sequences so that **user-facing value** comes first (notifications UI, chat history, telegram deploy) while tests run in parallel rather than as a strict prerequisite.

The existing backlog items map to this analysis:
- P1 "Notification preferences UI" → Part of item [1] above
- P1 "Set Telegram env vars on Fly.io" → Item [3] above
- P2 "Execution results dashboard" → Item [6] above
- P2 "Agent schedule management UI" → Part of item [6] above

The "Agent Autonomy" future milestone from ROADMAP.md becomes achievable once unified sessions (item [5]) land — it provides the messaging backbone that agent-to-agent communication needs.

---

## Key Architectural Decision: Event Bus vs. Current Direct Routing

The biggest structural debt is that each channel (web, telegram, scheduled) has its own handler that independently loads agents, wraps tools, and manages history. OpenClaw solves this with a WebSocket gateway that all channels connect to.

For llm-agent, a lighter-weight version would be:

```python
# chatServer/services/message_bus.py
class AgentMessageBus:
    """Central pipeline: receive message -> load agent -> execute -> route response"""

    async def process_message(self, message: InboundMessage) -> OutboundMessage:
        # 1. Upsert chat_sessions with channel tag
        # 2. Load agent (cached)
        # 3. Wrap tools with approval
        # 4. Load/attach memory
        # 5. Execute
        # 6. Normalize response
        # 7. Store in history
        # 8. Route notifications
        return outbound
```

Each channel handler would become a thin adapter that translates its input format to `InboundMessage` and routes the `OutboundMessage` back through its channel. This is essentially what SPEC-005's unified sessions enables.

**Recommendation:** Don't build the message bus as a separate project. Instead, refactor toward it incrementally as part of SPEC-005 implementation.
