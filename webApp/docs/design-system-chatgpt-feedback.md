# Design System Iteration: Context Modes, Focus, and Mobile

This document is an active working space for refining the Clarity app’s visual system and interaction patterns, focusing on context modes (split-pane vs. full-bleed), progressive disclosure, and mobile adaptation. It is meant to challenge current assumptions, articulate explicit design principles, and document actionable next steps for user testing and implementation.

---

## 1. Context Modes: Split-Pane, Focus, Overlay

### A. Modes Table

| Mode               | Description                                                                                        | Typical Use Case                               | Trigger/Transition                                     |
| ------------------ | -------------------------------------------------------------------------------------------------- | ---------------------------------------------- | ------------------------------------------------------ |
| Split-Pane         | Two side-by-side panes (primary/secondary), each with stacked cards. Both visible and interactive. | Daily planning, task execution with context    | Default on desktop; can transition from any other mode |
| Full-Bleed/Focus   | One card takes over the full workspace; all other context hidden (optionally overlays nav).        | Deep work, Pomodoro, onboarding, reflection    | User keyboard shortcut, UI button, AI coach suggestion |
| Modal Overlay      | Temporary overlay or modal for important flows (e.g., coach prompt, settings, add/edit task).      | Interruption, onboarding step, AI intervention | Explicit user action, AI coach event                   |
| Mobile Single Card | On small screens, only one card visible at a time. Can swipe or tap to navigate stack.             | All flows on phone, quick capture              | Responsive breakpoint triggers automatically           |

### B. Design Principles

* Any card or pane can be “promoted” to full focus mode with a shortcut or button.
* Progressive disclosure: Users can reveal/hide context as needed (never forced to see everything).
* Overlay/modal states are reserved for critical flows or coach interventions.
* On mobile, always show a single card; allow navigation by swipe/tap or explicit “stack reveal.”

---

## 2. Progressive Disclosure: Focus vs. Context

### A. Principle Statement

The system supports instant transitions between "all context" (planning, history, coach, etc.) and "just the task" (focus mode). Users and the AI can both trigger these transitions.

### B. Controls & Shortcuts

* **Keyboard:** `Cmd+Shift+F` (Focus mode), `Esc` (Return to previous), `Tab` (Cycle panes), `Cmd+1-4` (Quick switch)
* **Mouse/Touch:** Double-click card edge or focus icon to expand/collapse
* **AI Coach:** Suggests focus/return to context during appropriate flows

### C. Edge Cases

* On mobile, default is single-card; “focus” removes nav if needed
* Reflections, onboarding, or urgent AI interventions *always* use full-bleed/modal overlay

---

## 3. Mobile Adaptation

### A. Pattern Table

| Feature/Screen         | Desktop Pattern        | Mobile Adaptation                       | Gaps/Questions                     |
| ---------------------- | ---------------------- | --------------------------------------- | ---------------------------------- |
| Split-Pane Planning    | 2 panes, stacked cards | Single card, swipe to next              | Needs test: Is swipe intuitive?    |
| Focus Mode             | Full-bleed, timer only | Full-bleed, minimal nav                 | Consider bottom sheet for controls |
| Reflection/Coach Modal | Overlay, dimmed bg     | Overlay, slides up (bottom sheet/modal) | Consistent animation?              |
| Task Add/Edit          | Modal or tray          | Modal full-screen or sheet              | Entry/exit pattern?                |
| Navigation             | Left sidebar, icons    | Bottom nav, swipe/tap to switch         | How many icons max?                |

### B. Mobile-First Gaps

* Card stack metaphor is less clear on mobile—need alternative visual indicator or badge
* Consider haptics or subtle vibration for focus transitions
* Touch gestures should never conflict with native phone navigation

---

## 4. Stack Depth & Visual Indicators

### A. Options Table

| Pattern            | Visual Indicator                          | Pros                                 | Cons/Questions             |
| ------------------ | ----------------------------------------- | ------------------------------------ | -------------------------- |
| 2-Card Stack       | Two visible edges/partial cards           | Intuitive depth, clear physical hint | Still some visual clutter? |
| 1-Card + Edge Peek | One full card, subtle edge/"peek" shadow  | Minimal distraction, hints at more   | Easy to overlook?          |
| Badge/Number       | Numeric badge (e.g., “+2” on card edge)   | Clear, universally understood        | Lacks metaphor/less visual |
| Animated “Peek”    | On hover/tap, edge animates or slides out | Context on demand, minimal clutter   | More dev/design work       |

### B. Decision Matrix: When to Use Which Cue

| Situation / Screen              | Default Indicator  | Rationale                                                       |
| ------------------------------- | ------------------ | --------------------------------------------------------------- |
| Daily Planning (Desktop)        | Edge Peek + Hover  | Clear context, minimal distraction, discoverable on interaction |
| Task Execution / Focus Mode     | None               | Eliminate all distractions; just the task                       |
| Modal/Overlay (Add/Edit, Coach) | None or Badge      | Overlay dominates, badge only if context still matters          |
| Mobile (General Navigation)     | Edge Peek + Swipe  | Space constraints; use subtle edge, reveal stack on swipe       |
| Mobile (Focus, Reflection)      | None               | Single-task, full-bleed for minimalism                          |
| History/Review screens          | Edge Peek or Badge | Depends on available space; badge for long stacks               |

### C. Key Interaction Flows for Visual Cues

1. **Reveal More Cards (Desktop):**

   * User hovers over or taps the edge peek on active card.
   * Animation: edge widens, underlying card(s) partially slide out or become more visible.
   * Clicking/tapping a visible card brings it to front, active.

2. **Reveal More Cards (Mobile):**

   * User swipes from card edge or taps small edge peek.
   * Animation: card slides horizontally (or vertically, depending on mobile pattern), next card moves into view.
   * Optional: haptic feedback on stack change.

3. **Show Numeric Badge:**

   * If more than one card is stacked, show badge on edge of active card (e.g., "+2").
   * Badge animates on stack change (e.g., new card added, old one removed).
   * Clicking badge (desktop) or tapping (mobile) opens stack preview.

4. **Focus Mode Transition:**

   * User clicks "focus" button or triggers keyboard shortcut.
   * All context/edge peeks/badges instantly hide with smooth fade.
   * Only the active card remains in full-bleed mode.

5. **Return from Focus/Overlay:**

   * User hits `Esc`/back or completes modal flow.
   * Stack/edge peek reappears, restoring previous context.

---

## 5. Coach & Modal Dominance

### A. System Principle

Coach prompts, onboarding, and urgent flows may “take over” the entire UI as modal overlays or full-bleed screens.

### B. Implementation Notes

* Coach modals always return the user to their previous context after completion.
* Use distinct colors/animations to distinguish “coach takeover” from other overlays.

---

## 6. Next Steps & Open Questions

* Prototype these modes and transitions in Figma/code
* Write usability testing script: focus on context switching, mobile adaptation, and stack comprehension
* Review all visual effects for accessibility (contrast, motion)
* Decide on MVP mobile pattern and document clearly
* How does AI “suggest” or “trigger” context transitions in a non-annoying way?

---

> \[Continue to iterate in this canvas; add notes, questions, mockups, and user test plans as needed.]
