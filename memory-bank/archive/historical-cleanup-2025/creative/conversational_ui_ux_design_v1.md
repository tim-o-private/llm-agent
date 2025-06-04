# 🎨 CREATIVE PHASE: UI/UX Design - Conversational Task Management & Agent Interaction

**Date:** {datetime.now().isoformat()}
**Associated Task in `tasks.md`:** BRAINPLN-001 / PLAN-STEP-4: "Initiate CREATIVE phase for UI/UX Design for Conversational Task Management."

## 1. Component Description

This component focuses on the user interface and experience for interacting with the AI agent, managing tasks created or modified by the agent, and providing feedback. It includes the chat interface, how agent-proposed tasks are displayed and confirmed, and how users can influence agent behavior through feedback.

## 2. Requirements & Constraints

*   **Functional Requirements:**
    *   **FR1: Conversational UI:** Clear, intuitive chat interface.
    *   **FR2: Agent Task Display:** Clearly distinguishable agent-proposed tasks.
    *   **FR3: Task Confirmation Workflow:** User review and confirm/reject agent proposals.
    *   **FR4: Agent Feedback Mechanism:** Simple way to provide feedback on agent responses.
    *   **FR5: Real-time Updates:** UI reflects task changes in near real-time.
*   **Non-Functional Requirements:**
    *   **NFR1: Clarity & Intuitiveness.**
    *   **NFR2: Responsiveness.**
    *   **NFR3: Accessibility (WCAG).**
    *   **NFR4: Consistency with Clarity UI (Radix UI + Tailwind).
*   **Constraints:**
    *   **C1: Existing Task View Integration.**
    *   **C2: Technology Stack (React, Tailwind, Radix, Zustand).**
    *   **C3: "Low-Stim" Design Philosophy.**

## 3. Options Analysis

**Option 1: Integrated Chat Panel with In-line Task Previews & Confirmation Modals**

*   **Description:** Collapsible chat panel. Agent-proposed tasks appear as visually distinct "ghost" `TaskCard` in `TodayView`. Clicking opens a confirmation modal (review mode `TaskDetailView`) with "Confirm", "Edit & Create", "Reject" actions. Feedback via thumbs up/down on messages.
*   **Pros:** Integrated experience, familiar patterns, clear review step.
*   **Cons:** Potential modal fatigue, visual clutter from ghost tasks.

**Option 2: Dedicated "Agent Actions" Review Area + Contextual Chat Indicators**

*   **Description:** Standard chat. Proposals go to a dedicated "Agent Inbox" / "Review Agent Actions" tab with compact proposal cards and direct confirm/edit/reject buttons.
*   **Pros:** Decoupled review keeps main list clean, focused batch review, less interruption.
*   **Cons:** Context switching, discoverability of the review area.

**Option 3: "Smart" Inline Task Creation with Undo/Edit Emphasis**

*   **Description:** Agent immediately creates/edits tasks. Chat response confirms with "[Edit]" or "[Undo]" links. Prominent toast also offers Undo.
*   **Pros:** Fastest interaction, reduced clicks, natural language flow.
*   **Cons:** Higher risk of errors, complex undo logic, user trust dependent.

## 4. Recommended Approach & Justification

**Chosen Option: Option 1 - Integrated Chat Panel with In-line Task Previews & Confirmation Modals**

**Justification:**
Option 1 provides the best balance for initial implementation, prioritizing clarity and explicit user control. It's contextually relevant, leverages existing UI patterns, has manageable complexity, and offers a tight feedback loop. It can evolve towards Option 2 elements if needed.

**Agent Feedback (FR4) Implementation:**
*   Thumbs up/down icons on agent messages.
*   Thumbs up: Positive signal to backend.
*   Thumbs down: Negative signal + reveals optional text input ("Tell us more") for specific feedback, sent to backend.

## 5. Implementation Guidelines (High-Level for UI/UX)

1.  **Chat Panel (`ChatPanel.tsx`, `TodayView.tsx`):** Display history, input, thinking indicator. Add feedback icons and submission logic.
2.  **"Ghost" Task Card (`TaskCard.tsx` variant, `TodayView.tsx`):** Visual variant for proposals (e.g., dashed border, badge). Logic to handle pending tasks (Zustand state, status: `pending_agent_proposal`).
3.  **Confirmation Modal (`AgentTaskConfirmationModal.tsx`):** Similar to `TaskDetailView` (review mode). Display proposed data, show diff for edits. Buttons: "Confirm", "Edit & Confirm", "Reject". Confirm finalizes task via `useTaskStore`.
4.  **State Management (`useTaskStore.ts`, `useAgentInteractionStore.ts`):** Manage pending proposals, transition to confirmed tasks.
5.  **Real-time Updates:** Ensure confirmed tasks reflect correctly via Supabase live.
6.  **Styling:** Adhere to Radix + Tailwind and existing visual language.

## 6. Verification Checkpoint

*   [X] **Addresses FR1-FR5:** Yes.
*   [X] **Addresses NFR1-NFR4:** Yes (design intent).
*   [X] **Adheres to C1-C3:** Yes.

---
🎨🎨🎨 **EXITING CREATIVE PHASE: UI/UX Design - Conversational Task Management & Agent Interaction** 🎨🎨🎨 