### **Phase 0: Infrastructure & Foundations (v0.1 Alpha)**

**Goal:** Lay the groundwork for task management, UI shell, and basic auth

| Area           | Feature                                                    | Notes                                      |
| -------------- | ---------------------------------------------------------- | ------------------------------------------ |
| Auth           | Google & Apple OAuth sign-in                               | Use Supabase or Firebase for speed         |
| Task System    | Create/edit/delete tasks with due date, category, priority | Minimal UI, use Tailwind for accessibility |
| UI Shell       | “Today” view, bottom nav bar (web PWA style)               | Responsive from day one                    |
| Storage        | User-owned data storage (tasks, prefs)                     | Supabase with row-level security           |
| Planning Logic | Daily planning interface with quick-add                    | Skip advanced scheduling for now           |
**Technical focus:** Backend wiring, basic layout, user sessions  
**Milestone:** Logged-in user can view today’s tasks, add/edit/delete tasks

---
### **Phase 1: AI Coaching & Integrations (v0.2 Beta)**

**Goal:** Introduce conversational + contextual AI and first real integrations

| Area             | Feature                                                     | Notes                            |
| ---------------- | ----------------------------------------------------------- | -------------------------------- |
| AI Chat Coach    | Text-based planning session (e.g., “What’s today’s focus?”) | Simple prompt, flexible backend  |
| Nudge System     | Time-based suggestions (e.g., late for task)                | Simple rule-based trigger system |
| Google Calendar  | Sync with user calendar (2-way)                             | Tasks = events, events = tasks   |
| Google Docs Link | Attach GDocs to task items                                  | For essays, plans, notes         |
**Technical focus:** Prompt design, routing to LLM backend, integration auth  
**Milestone:** AI can suggest next actions, nudge if task is skipped, and assist with planning

### **Phase 2: Smart Productivity Layer (v0.3 Beta)**

**Goal:** Help users start and complete tasks more easily with light AI

| Area            | Feature                                              | Notes                            |
| --------------- | ---------------------------------------------------- | -------------------------------- |
| Visual Timer    | Pomodoro-style focus timer (15/25-min blocks)        | Add visual countdown UI          |
| Brain Dump      | Quick note entry field for unstructured thoughts     | Optionally voice-to-text later   |
| Focus View      | One-task-only view to reduce distractions            | Toggle in task view              |
| Gamification    | Streak counter, light confetti or badges             | Local-only rewards at first      |
| AI Prompts (v1) | Static “coach” suggestions (e.g., prewritten nudges) | Not yet adaptive, but well-timed |
**Technical focus:** Lightweight feedback loops, session state  
**Milestone:** User completes a planning session and sees task nudges

---

### **Phase 3: Personalization & Feedback Loops (v0.4 MVP Launch)**

**Goal:** Deliver adaptive coaching, personal rewards, and user control

| Area               | Feature                                                | Notes                           |
| ------------------ | ------------------------------------------------------ | ------------------------------- |
| Adaptive Nudging   | Adjust timing and tone of AI prompts based on behavior | Use local rules or basic ML     |
| “Why This Matters” | User sets personal motivation per task/goal            | Optional, surfaces on reminders |
| Progress Feedback  | Progress bar, “done list,” reflection prompts          | Optional journal integration    |
| Values/Goals Page  | Select personal values, map goals to them              | ACT-style coaching hooks        |
| Focus Mode v2      | Soft site blocker or Chrome extension                  | Optional distraction guardrails |
**Technical focus:** Data-driven adaptation, onboarding flow  
**Milestone:** App supports full loop: plan → prompt → act → reflect → replan

---

## **Ongoing / Future (Post-MVP)**

- Mobile app (iOS native or Capacitor wrap)
- Coach tone customization (“cheer me on” vs. “stay chill”)
- Data export + sync to Notion, Obsidian, or Markdown
- Community support options (coaching group, Discord link)
- Workspace version for teams/students