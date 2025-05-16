# Product Context

This document provides a comprehensive overview of the "Local LLM Terminal Environment" and its associated web application, "Clarity." It covers the purpose, target users, goals, key features, and overall product vision.

## 1. Overall Project Vision & Purpose

**Local LLM Terminal Environment (CLI):**
*   **Purpose:** To create a local, terminal-based environment for interacting with Large Language Models (LLMs), leveraging local file-based storage (Markdown, YAML) for project contexts, calendar information, and user preferences. The aim is to provide structured and predictable interactions with LLMs, assisting with project and calendar management.
*   **Core Idea:** Improve LLM interaction by developing structured methods for providing context, enabling more relevant and accurate responses compared to manual context provision in web interfaces.

**Clarity (Web Application):**
*   **Purpose:** A cross-platform planning and executive function assistant designed primarily for people with ADHD. It focuses on daily task planning, AI-powered coaching, and distraction management features to reduce friction around task initiation, time blindness, and low motivation.
*   **Core Idea:** Combine evidence-based strategies with adaptive AI nudges in a calming, focused, and emotionally supportive interface.

## 2. Target Users

**Local LLM Terminal Environment (CLI):**
*   Developers or technical users looking for a customizable, local-first way to interact with LLMs.
*   Users who want to manage LLM context through local files.
*   Individuals managing multiple tasks who could benefit from LLM assistance with organization.

**Clarity (Web Application):**
*   **Primary:** Adults with ADHD (college students + working professionals).
*   **Needs:** Executive function support, emotional regulation, adaptive task planning, and management of challenges like time blindness and task prioritization.

## 3. Goals

### General Project Goals (CLI & Foundational)
*   Create a functional terminal application for LLM interaction with file-based context.
*   Enable users to define and manage different contexts (global, per-project, per-agent).
*   Utilize LangChain for a flexible LLM interaction layer.
*   Use AI-assisted development to build the tool and learn best practices.

### Clarity Web App Goals (MVP)
*   Build an MVP with core planning and habit-forming functionality.
*   Implement contextual & conversational AI to support executive function.
*   Offer seamless, privacy-respecting integration with Google Calendar & Docs.
*   Design for simplicity, low friction, personalization, and a neurodivergent-friendly experience (low cognitive load, minimal visual clutter).
*   Prioritize web app for initial release, mobile-friendly.
*   Reduce decision fatigue and provide emotional support.

### Non-Goals (Initial / MVP)
*   **CLI:** A GUI (though architecture should allow it later); full-fledged PM/calendar app; real-time sync with external services (initially).
*   **Clarity:** Native mobile apps (deferred); deep analytics/reporting; rich community/social features; third-party wearable integrations (for MVP).

## 4. Key Features & Functionality

### Local LLM Terminal Environment (CLI)
*   **Agent Configuration:** Define agents (prompts, tools, LLM params) via local files (`config/agents/<agent_name>/`).
*   **File-Based Context:**
    *   Global context in `data/global_context/`.
    *   Agent-specific static context and prompts.
*   **REPL Interface:** Interact with agents via `chat` command, switch agents (`/agent <name>`).
*   **Tool Usage:** Agents can read/write files based on declarative `tools_config` scopes (e.g., project read, memory-bank write).
*   **Session Management:** Conversation memory loading/saving, session summaries.
*   **Specialized Agents:** E.g., 'Architect' agent for backlog refinement.

### Clarity Web Application (MVP Features)

**A. Task Planning:**
*   Create/edit tasks (due date, time, category, priority).
*   "Today View" for daily planning (tasks segmented by time blocks).
*   Pomodoro timer with visual countdown.
*   "Focus View" showing only the active task.

**B. AI Coach (Hybrid Interface):**
*   Daily conversational check-in (chat UI).
*   Smart nudge system (e.g., "Want help starting your 10AM writing task?").
*   Personalized tone/feedback preferences.
*   Contextual prompts based on user history and timing.
*   Interaction Triggers: Daily prioritization, post-task reflection, idle detection, scratch pad review, EOD journaling.
*   Capabilities: Reframe vague input, break down tasks, suggest re-scoping/rewards, adapt tone.

**C. Motivation & Feedback:**
*   Streaks, badges, or light gamification.
*   Customizable in-app rewards/triggers.
*   Immediate feedback (notifications, animations).

**D. Distraction Management:**
*   Focus mode (optional website blocker, DND sync).
*   Brain-dump pad (text/voice input) for intrusive thoughts.
*   Optional mindfulness check-ins.

**E. Integrations:**
*   Google Calendar Sync (read/write events).
*   Google Docs Integration (attach/jump to docs per task).
*   OAuth sign-in (Google, Apple).

## 5. Key Product Mechanisms & Flows (Derived from `memory-bank/clarity/componentDefinitions.md`)

This section describes conceptual models for core product functionalities, particularly how the AI Coach and system interact with the user through various cycles and prompts.

### 5.1. Prompting Logic Model
*   **Core Idea:** Prompts are driven by user context, tone preferences, and key interaction moments. They can be dynamic or template-based.
*   **Prompt Contexts & Triggers:**
    *   **Onboarding:** First login (Introduce AI, feature overview).
    *   **Daily Planning:** Start of day/planner open (Help prioritize, frame goals).
    *   **Execution Start:** Task start (Encourage, remind goal/time block).
    *   **Mid-Session Nudge:** Inactivity/distraction (Refocus, encouragement).
    *   **End of Session:** Timer complete (Check completion, offer reward/reflection).
    *   **Capture Review:** Scratch pad entries unprocessed (Suggest converting to tasks/ideas).
    *   **End of Day:** User-defined EOD/manual trigger (Summarize, reflect, preview tomorrow).
*   **Prompt Parameters:** Trigger condition, tone style, intent (motivate, organize, reflect), context (task, time, mood).
*   **UI Directives:** Prompts can include flags for UI behaviors (e.g., `show_confetti`).
*   **Source Types:** Template (DB, tagged by tone/trigger/intent), Generated (dynamic from context/summaries), Hybrid (templates with placeholders).

### 5.2. Memory Lifecycle (AI Coach & Agent)
*   **Purpose:** Enable continuity, context, and personalization across sessions.
*   **Memory Tiers:**
    *   **Working Memory:** Last ~24h unsummarized interactions (Full dialogue fidelity).
    *   **Daily Summary:** Condensed summary of day's actions, reflections, tasks (Context for coaching, streaks; retained ~7-14 days).
    *   **Long-Term Memory:** Aggregated insights, user tone, value tags, preferences (Power behavior adaptation; retained indefinitely).
*   **Lifecycle Stages:**
    1.  **Real-Time Capture:** All interactions stored in working memory.
    2.  **Checkpoint Summarization:** Daily/periodic compression of working memory to daily summary.
    3.  **Long-Term Condensation:** Periodic distillation of summaries into behavioral markers.
*   **Technical Notes:** User-scoped memory. Long-term in Supabase, working memory cached server-side. Summaries can be embedded/indexed for RAG.

### 5.3. Task Lifecycle Hooks
*   **Purpose:** AI and system respond to key user interactions at defined task stages.
*   **Lifecycle Phases & Hooks:**
    *   **Create:** User enters new task (AI suggests breakdown, checks vagueness, infers category/value).
    *   **Plan:** Daily prioritization (AI nudges for due time, category, motivation, reward).
    *   **Start:** User presses "Start Task" (AI motivational prompt; task status to `in_progress`).
    *   **During:** Timer runs in Focus Mode (Idle detection -> coach nudge; Scratch Pad usage noted).
    *   **Midway:** Halfway through session (Optional check-in).
    *   **End:** Timer ends (Prompt for completion + reflection; update streak if done).
    *   **Reflect:** Task marked complete (AI logs mood/reflection, suggests next task/reward).
    *   **Skip:** Task skipped (AI reframe/re-scope suggestion).

### 5.4. Data Sync, Privacy & Integration Logic (Conceptual)
*   **MVP Focus:** Google Calendar events, Google Docs attachments.
*   Future integrations will follow similar patterns of user-authorized data access and synchronization to enhance planning and execution within Clarity.

### 5.5. AI Coach Interaction Model (Derived from `memory-bank/clarity/interactionModel.md`)
*   **Purpose:** The AI Coach supports planning, motivation, and reflection across the user's daily flow.
*   **Interaction Triggers:**
    *   Daily prioritization session (via chat).
    *   Post-task reflection prompts (after completion or skipped).
    *   Idle detection during execution (gentle nudge/encouragement).
    *   Review of scratch pad for task suggestions.
    *   End-of-day journaling and feedback.
*   **Key Capabilities:**
    *   Reframe vague user input into actionable tasks.
    *   Break down complex tasks into small steps (populating `task.breakdown`).
    *   Suggest re-scoping or rewards based on fatigue/frustration.
    *   Maintain memory of completed tasks for streak tracking and reinforcement.
    *   Adapt tone (`cheerful`, `gentle`, `directive`) based on user preference.
*   **State Requirements:**
    *   Retain daily context (active task, scratch pad, focus sessions, user preferences).
    *   Time-aware (track task/session completion times, EOD).
    *   Graceful degradation in low-connectivity/offline scenarios (Note: this requires careful design for local caching and sync).

## 6. User Experience & Design (Clarity)

*   **Design Goals:** Low friction, neurodivergent-friendly, emotionally positive, context-aware, modular but consistent.
*   **Tone:** Friendly, non-judgmental, supportive.
*   **Visual Style:** Calm, minimal, with occasional joyful touches. Large readable sans-serif fonts. Muted base colors with accents. Light/dark themes.
*   **Layout Priorities:**
    *   **Home ("Today View"):** Focused list, easy task addition, access to timer/coach.
    *   **Focus Mode:** One task, timer, minimal navigation.
    *   **Coach Panel:** Side panel or modal for planning/reflection.
*   **Accessibility:** Minimal choices per screen, strong visual hierarchy, consistent navigation, optional animations, WCAG 2.1 compliance focus.

## 7. Core User Journey (Clarity - Simplified)

1.  **Authentication & Onboarding:** Sign in, AI coach introduces app & core flows (planning, execution).
2.  **Daily Planning:** Add/edit tasks in "Today View", AI may assist.
3.  **Focus & Execution:** Start task -> Focus Mode with timer, Scratch Pad available, AI nudges if idle.
4.  **Reflection & Motivation:** Task completion triggers feedback, streaks logged, optional reflection.
5.  **Supportive Features:** Coach Panel, Brain Dump, Settings always accessible.

## 8. Feature Roadmap (Clarity - Phased Approach Summary)

*   **Phase 0 (Alpha - Foundations):** Auth, basic task system, UI shell, storage.
    *   *Key Outcome:* Logged-in user can CUD tasks and view them.
*   **Phase 0.4 (Refactor):** Implement scalable design and implementation patterns.
*   **Phase 0.5 (Core Task UI):** Implement "Today View", task addition flow, basic chat interface, focus mode screen.
*   **Phase 0.6 (Restructure & Deploy):** Project restructure, deployment strategy, enhance chat server.
*   **Phase 1 (Beta - AI & Integrations):** AI chat coach, nudge system, Google Calendar/Docs integration.
    *   *Key Outcome:* AI assists with planning and nudges, integrations work.
*   **Phase 2 (Beta - Smart Productivity):** Visual timer, brain dump, focus view, gamification.
    *   *Key Outcome:* User completes planning and sees task nudges.
*   **Phase 3 (MVP Launch - Personalization):** Adaptive nudging, "Why This Matters" per task, progress feedback, values/goals page.
    *   *Key Outcome:* App supports full loop: plan -> prompt -> act -> reflect -> replan.

## 9. Success Criteria (Overall MVP)

*   **CLI:** Functional LLM interaction with file-based context, agent switching.
*   **Clarity:** Users complete daily planning with AI coaching, nudges are effective, feedback systems work, focus mode aids concentration, integrations are reliable. App is performant on web/mobile browsers.

This provides a good overview of the product context. Next, I will work on `projectbrief.md`. 