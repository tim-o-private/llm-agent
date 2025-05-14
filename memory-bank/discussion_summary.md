# Discussion Summary & Clarifications (Post-Document Review)

This document summarizes key decisions and clarifications made during the discussion following the review of files in `memory-bank/clarity/`. This information supplements the details found in `designBrief.md`, `coreUserJourney.md`, `prd.md`, `componentDefinitions.md`, `interactionModel.md`, and `featureRoadmap.md`.

**Key Clarifications & Decisions:**

1.  **Initial Landing View:** The user's initial landing view after authentication will be the Home ('Today') view, featuring an integrated chat window for the AI assistant's onboarding guidance.
2.  **Nudging System Evolution:** Adaptive nudging (Phase 3) will involve the AI learning from user behavior to tailor nudges, though specifics are TBD pending user data. Phase 1 will use a simple rule-based system.
3.  **Priority/Layout Specificity:** Eisenhower Matrix layout is considered one option for priority tagging, not a strict requirement for Phase 1. The exact timing is TBD.
4.  **Mindfulness Check-ins:** Deferred to a later phase (post-MVP).
5.  **AI Coach Interaction Model:**
    *   Daily check-ins are primarily chat-driven, supplemented by static UI elements (stats, streaks).
    *   Nudges will appear *outside* the main chat interface, ideally as system notifications/alarms.
6.  **Google Calendar Integration (Phase 1 Scope):** Limited to basic two-way sync for *events without recurrence*. More complex handling (recurring events, specific details) is deferred to Phase 2.
7.  **Google Docs Integration (Phase 1 Scope):** Limited to linking/opening documents via the `linked_doc_url` field. No in-app content preview, editing, or AI reading of document content in Phase 1. The AI can be instructed to save chat contents to a GDoc or told to read a GDoc, but this implies a future capability beyond MVP linking.
8.  **Gamification/Rewards (Phase 1 Scope):** Limited to basic streak counts (tasks/hour, tasks/day, reviews/week, % reviews completed). The underlying design should be modular to allow for future expansion (badges, custom rewards), but user customization of visible stats is not in MVP. The `reward_trigger` and `streak_eligible` fields on the Task object can be included in the data model from Phase 1 for future use.
9.  **User Settings & AI Application:** The AI will use user settings like `day_structures`, `start_of_day`, and `end_of_day` to pace interactions and holistically manage tasks across different user contexts (work, personal, etc.).
10. **Scratch Pad Review Frequency:** The AI should attempt to review and suggest converting scratch pad items into tasks when the user *saves* new scratch pad entries.
11. **Focus Session Mood Usage:** The `mood` field in the Focus Session Log is initially for data collection to encourage user self-reflection. It *should* influence AI tone and be used for analysis in the future, but the primary Phase 1 goal is data capture.
12. **UI Directives Implementation:** For Phase 1, include support for a single `ui_directive`: `show_confetti`. The AI will pass directives via tool calls.
13. **Task Lifecycle Hooks (Phase 1 Scope):** The "AI suggests breakdown" hook on task creation *is* included in Phase 1. Other detailed lifecycle hooks described in `interactionModel.md` are deferred to later phases based on user feedback and maturity of the AI coaching. The core Phase 1 AI interaction focuses on planning guidance, task capture from scratch/brain dump, leading reviews, and prompting user action.
14. **Offline Mode Communication:** Adding a requirement for a status banner indicating offline mode is deferred to Phase 2.

**AI UI Integration Patterns (Decision Points):**

*   **Today/Planner View:** Use a **collapsible chat panel** at the bottom.
*   **Focus Mode:** Use a small, persistent **chat icon** that opens a **small, floating chat window/modal** for AI interaction during the session.
*   **Add/Edit Task Modal:** Include a **button** (e.g., "Ask AI to formalize") that triggers the AI to process current task input and suggest updates or additions *within the modal UI*, without opening a separate chat window.
*   **Scratch Pad:** Integrate AI suggestions directly into the Scratch Pad UI. Consider also providing access to the floating chat window via the chat icon pattern used in Focus Mode.
*   **Settings Screen:** No direct AI chat integration.

This summary captures the refinements and decisions made, which can now inform the creation of specific backlog items.
