# User Settings & Preferences
User preferences help personalize the AI coach experience, define boundaries for daily flow, and allow for custom interface configurations. Users can define multiple contextual calendars to reflect work time, personal time, and other categories of routine. These define the user's day structure and affect how and when the AI delivers suggestions and prompts.
## Core Fields

| Field                   | Type    | Description                                                                                                    |      |                                            |
| ----------------------- | ------- | -------------------------------------------------------------------------------------------------------------- | ---- | ------------------------------------------ |
| `user_id`               | string  | User reference key                                                                                             |      |                                            |
| `preferred_tone`        | enum    | AI voice preference (`cheerful`, `gentle`, `directive`)                                                        |      |                                            |
| `day_structures`        | list    | Array of user-defined time blocks with name, type (e.g., work, personal), start and end times, and active days | time | Time user considers the start of their day |
| `end_of_day`            | time    | Time user considers the end of their day                                                                       |      |                                            |
| `work_blocks_max`       | number  | Max number of consecutive focus sessions before break                                                          |      |                                            |
| `long_break_freq`       | number  | After how many sessions should a long break be prompted?                                                       |      |                                            |
| `reward_enabled`        | boolean | Whether in-app reward suggestions are active                                                                   |      |                                            |
| `notifications_enabled` | boolean | User opt-in for nudges and reminders                                                                           |      |                                            |
| `default_view`          | enum    | What screen opens on login (`planner`, `chat`, `focus`)                                                        |      |                                            |
| `theme`                 | enum    | Visual theme (light, dark, low-stim)                                                                           |      |                                            |
| enable_animations       | boolean | Turn animations on / off                                                                                       |      |                                            |
## Behavior Notes
- Settings are loaded at login and drive UI layout, tone of messages, and AI cadence.
- Users can access and adjust preferences anytime via the Settings screen.
- Default values are gently suggested during onboarding but fully customizable.
- AI uses `start_of_day` and `end_of_day` to pace reflections and end-of-day review prompts.
# Component Definition: Task Object
The Task object is the atomic unit of planning, execution, and reflection. It must support flexible entry (quick or detailed), track progress and outcomes, and integrate with AI-driven suggestions and motivation systems.
## Core Fields

The Task object also supports:

- **1:many** **relation to Subtasks** – supports progressive completion of complex tasks.
- **1:1 relation to Projects** – enables grouping tasks under longer-term initiatives.

| Field             | Type      | Description                                              |
| ----------------- | --------- | -------------------------------------------------------- |
| `id`              | string    | Unique identifier for the task                           |
| `title`           | string    | Short description of the task                            |
| `description`     | string    | Optional longer detail or instructions                   |
| `status`          | enum      | `"pending"`, `"in_progress"`, `"completed"`, `"skipped"` |
| `created_at`      | timestamp | When the task was created                                |
| `updated_at`      | timestamp | Last time the task was updated                           |
| `due_date`        | date      | Optional date/time the task is due                       |
| `category`        | string    | User-defined or system-defined label (e.g. Work, Health) |
| `value_tag`       | string    | Optional value alignment (e.g. "Family", "Growth")       |
| `linked_doc_url`  | string    | Optional Google Doc or external resource URL             |
| `motivation`      | string    | "Why this matters" – optional user-supplied rationale    |
| `reward_trigger`  | boolean   | If true, marks this task as one that yields a reward     |
| `streak_eligible` | boolean   | Whether this task counts toward streaks                  |
| `breakdown`       | list      | Ordered list of AI-suggested subtasks or steps           |
| `execution_logs`  | list      | Sessions (start time, end time, scratch pad summary)     |
| `completion_note` | string    | Optional user reflection entered after completion        |
## Behavior Notes
- When a task is started, it transitions to `in_progress` and logs the start time.
- If a Pomodoro session ends with no completion, an execution log is still written.
- Tasks marked `completed` may prompt AI to offer praise, reward, or suggest follow-up.
- AI may break large tasks into a `breakdown` array to help with initiation.
- Tasks can be filtered by category, value_tag, or due_date within the Planner View.
# Scratch Pad

The Scratch Pad is a temporary, low-friction capture space for thoughts, ideas, and potential tasks that arise during execution sessions.
## Core Fields

| Field               | Type      | Description                                                    |
| ------------------- | --------- | -------------------------------------------------------------- |
| `id`                | string    | Unique identifier for the entry                                |
| `content`           | string    | User-entered text or voice transcription                       |
| `created_at`        | timestamp | Timestamp of capture                                           |
| `session_id`        | string    | Optional reference to the focus session it was captured during |
| `task_context`      | string    | Optional task ID the user was working on at the time           |
| `archived`          | boolean   | If true, removed from active capture queue                     |
| `converted_to_task` | boolean   | If true, this was promoted to a Task                           |
## Behavior Notes
- Scratch entries can be viewed in a chronological feed or by associated task.    
- AI reviews unarchived entries to suggest new tasks or surface patterns.
- Scratch Pad may be opened as a modal or side-panel during any execution session.
- Users may manually promote an entry to a task or delete/archive it.

# Focus Session Log
Each task execution session (typically Pomodoro-style) is logged to capture time-on-task and user reflections.
## Core Fields

| Field         | Type      | Description                                               |
| ------------- | --------- | --------------------------------------------------------- |
| `id`          | string    | Unique session ID                                         |
| `task_id`     | string    | Reference to associated Task                              |
| `started_at`  | timestamp | Session start time                                        |
| `ended_at`    | timestamp | Session end time                                          |
| `interrupted` | boolean   | True if the session was stopped early                     |
| `notes`       | string    | User-entered summary of what was done                     |
| `mood`        | enum      | Mood selected post-session (e.g., "energized", "drained") |
| `duration`    | number    | Total duration (in minutes or seconds)                    |
## Behavior Notes
- Automatically linked to the task and stored within `task.execution_logs`
- Can be reviewed in end-of-day reflection or task history
- Optionally used to inform streak tracking and reward logic

# 🔹 Streak Tracker

Provides simple gamification by tracking consecutive days with completed tasks or reflection.

#### Core Fields

| Field                | Type   | Description                                       |
| -------------------- | ------ | ------------------------------------------------- |
| `user_id`            | string | ID of the user                                    |
| `current_streak`     | number | Number of consecutive days with a tracked success |
| `longest_streak`     | number | User's personal best streak                       |
| `last_activity_date` | date   | Date of last qualifying activity                  |

## Behavior Notes
- Streaks increment only after a task is completed AND a reflection is logged
- Tied to user-visible badges or lightweight visual rewards
- AI may comment on streaks during daily and end-of-day chats.

# Prompting Logic Model

Prompts are driven by user context, tone preferences, and key interaction moments in the day. Each is composed of a trigger, intent, tone, optional contextual data, and UI instructions when appropriate. Prompts may be generated dynamically or drawn from templates, depending on recent chat history and summarization state.

Prompts are driven by user context, tone preferences, and key interaction moments in the day. Each is composed of a trigger, intent, tone, and optional contextual data.

## Prompt Contexts & Triggers

| Phase             | Trigger                               | Purpose                                           |
| ----------------- | ------------------------------------- | ------------------------------------------------- |
| Onboarding        | First login                           | Introduce AI, guide user through feature overview |
| Daily Planning    | Start of day or planner open          | Help prioritize tasks, frame goals                |
| Execution Start   | Task start                            | Encourage, remind of goal or time block           |
| Mid-Session Nudge | Inactivity or distraction             | Refocus attention or offer encouragement          |
| End of Session    | Timer complete                        | Check task completion, offer reward or reflection |
| Capture Review    | Scratch pad entries unprocessed       | Suggest converting to tasks or ideas              |
| End of Day        | User-defined day end time or manually | Summarize, reflect, and preview tomorrow          |

## Prompt Template Example
Prompts may also include UI behavior flags to enhance engagement. For example, they can trigger animations or visual effects upon certain outcomes.

```
{
  "trigger": "end_of_session",
  "intent": "reflection",
  "tone": "gentle",
  "context": {
    "task_title": "Finish email draft",
    "session_duration": 25,
    "user_mood": "neutral"
  },
  "prompt": "Nice work on that session! Did you manage to finish your draft, or do we want to break it down into smaller pieces for next time?",
  "ui_directives": ["show_confetti", "highlight_task_completion"]
},
  "prompt": "Nice work on that session! Did you manage to finish your draft, or do we want to break it down into smaller pieces for next time?"
}
```
## Prompt Parameters
- **Trigger condition**: defines when prompt activates
- **Tone style**: determined by user preference
- **Intent**: e.g., motivate, organize, reflect, redirect
- **Context**: Optional values like current task, time of day, user input/mood

## Memory & Summarization

- Recent chat history (up to ~1 day) is retained in full for maximum personalization.
- At scheduled intervals (e.g. overnight or every 6 hours), the system summarizes the recent chat log into a compact memory chunk.
- Summaries are retained per-user and scoped by context (e.g., daily planning, task execution, scratch pad review).
- Summarized memories are reloaded and prepended to future prompts when appropriate.
- Short-term memory is cached for performance and cost savings.
## System Behavior
- Prompts are pulled from a library or generated on-demand
- Coach uses prior interactions to personalize voice and priority
- Reflections are always optional and non-punitive

# Prompt Library & Storage Strategy

To enable modular, personalized prompting at scale, the app will support a structured prompt library with both static templates and dynamic generation.

## Prompt Source Types

| Type          | Description                                                                            |
| ------------- | -------------------------------------------------------------------------------------- |
| **Template**  | Hand-authored prompts stored in a prompt database, tagged by tone, trigger, and intent |
| **Generated** | Prompts dynamically composed from user/task context and system summaries               |
| **Hybrid**    | Templates with fillable placeholders (e.g., task title, mood), populated on demand     |
## Prompt Storage Schema

| Field           | Type    | Description                                                         |
| --------------- | ------- | ------------------------------------------------------------------- |
| `id`            | string  | Unique prompt ID                                                    |
| `trigger`       | enum    | Associated phase (e.g. `end_of_session`, `daily_planning`)          |
| `intent`        | enum    | Core purpose: `reflect`, `motivate`, `organize`, `redirect`         |
| `tone`          | enum    | Optional tone tag: `gentle`, `directive`, `cheerful`                |
| `template_text` | string  | Full text with optional placeholders (`{{task_title}}`, `{{mood}}`) |
| `ui_directives` | list    | Optional array of frontend actions to trigger (e.g., confetti)      |
| `active`        | boolean | Whether this template is currently in use                           |
| `version`       | string  | Version tag for A/B testing and fallback logic                      |
#### Selection Logic
- At runtime, prompt selection follows:
    1. Check if recent context summary includes relevant system-generated prompt
    2. If not, filter template prompts by `trigger`, `intent`, `tone` preference
    3. Select best match or fallback default
    4. Populate placeholders with available context (task title, session notes, etc.)
- Fallbacks exist for each `trigger` to ensure graceful degradation

# 🔹 Memory Lifecycle
To enable continuity, context, and personalization across sessions, the AI maintains both short-term and long-term memory for each user.
## Memory Tiers

| Tier                 | Scope                                                      | Retention  | Purpose                                            |
| -------------------- | ---------------------------------------------------------- | ---------- | -------------------------------------------------- |
| **Working Memory**   | Last 24h of unsummarized prompts & responses               | 1 day      | Preserve full dialogue fidelity and nuance         |
| **Daily Summary**    | Condensed summary of day's key actions, reflections, tasks | ~7–14 days | Context for coaching and streak continuity         |
| **Long-Term Memory** | Aggregated insights, user tone, value tags, preferences    | indefinite | Power behavior adaptation and task personalization |
## Lifecycle Stages
1. **Real-Time Capture**: All task actions, scratch entries, coach interactions are stored in working memory.
2. **Checkpoint Summarization**: Once per day (or every 6 hours), working memory is compressed into a structured daily summary (tasks completed, goals adjusted, scratch trends, mood tags).
3. **Long-Term Condensation**: Periodically, summaries are distilled into key behavioral markers (e.g. "User often completes tasks after verbalizing goal"), used to refine AI behavior. 

## Technical Notes
- All memory is scoped per user.
- Long-term memory is stored in Supabase; short-term working memory may be cached server-side.
- Summaries can be embedded or indexed for retrieval-augmented prompting.
- Caching layers should be optimized to minimize token cost and latency.
- Recent chat history (up to ~1 day) is retained in full for maximum personalization.
- At scheduled intervals (e.g. overnight or every 6 hours), the system summarizes the recent chat log into a compact memory chunk.
- Summaries are retained per-user and scoped by context (e.g., daily planning, task execution, scratch pad review).
- Summarized memories are reloaded and prepended to future prompts when appropriate.
- Short-term memory is cached for performance and cost savings.
## System Behavior
- Prompts are pulled from a library or generated on-demand.
- Coach uses prior interactions to personalize voice and priority.
- Reflections are always optional and non-punitive.

# 🔹 Task Lifecycle Hooks
The AI and system respond to key user interactions at defined task lifecycle stages to enhance motivation, structure, and completion likelihood.
## Lifecycle Phases & Hooks

| Phase       | Trigger                    | AI/System Action                                                              |
| ----------- | -------------------------- | ----------------------------------------------------------------------------- |
| **Create**  | User enters new task       | AI suggests breakdown, checks vagueness, infers category/value_tag            |
| **Plan**    | Daily prioritization       | AI nudges to set due time, category, motivation, reward toggle                |
| **Start**   | User presses "Start Task"  | AI delivers tone-matched motivational prompt; task state set to `in_progress` |
| **During**  | Timer runs (in Focus Mode) | Idle detection triggers a coach nudge; Scratch Pad usage noted                |
| **Midway**  | Halfway through session    | Optional check-in: "Want to keep going or adjust?"                            |
| **End**     | Timer ends                 | Prompt for task completion + reflection; update streak logic if completed     |
| **Reflect** | Task marked complete       | AI logs user mood/reflection, suggests next task or reward                    |
| **Skip**    | Task skipped               | AI follows up with reframe suggestion or task re-scoping prompt               |
## System Notes
- All hooks support custom UI behavior (e.g., confetti, modal, assistant panel)    
- Hooks also log analytics data to support behavior insights and feedback loops
- Each hook condition is modular and can evolve independently from UI or backend state machine

# 🔹 Data Sync, Privacy & Integration Logic

Clarity will support external integrations to enhance continuity and user convenience. MVP support focuses on syncing Google Calendar events and Google Docs attachments.
## Google Calendar Integration

| Action                | Trigger                      | Behavior                                                                                      |
| --------------------- | ---------------------------- | --------------------------------------------------------------------------------------------- |
| Push task to calendar | User sets task with due time | App creates/edit Google Calendar event with task title and timing                             |
| Pull from calendar    | Planner View loads           | Events within `day_structures` appear as blocked time slots (read-only unless linked to task) |
| Update calendar event | Task updated                 | Reflected in linked calendar entry if connected                                               |
| Event reminder nudge  | Event start time imminent    | AI prompt may appear in Chat or Planner with a reminder to begin                              |
## Google Docs Integration

| Action             | Trigger                               | Behavior                                                                  |
| ------------------ | ------------------------------------- | ------------------------------------------------------------------------- |
| Attach doc to task | User pastes or links a Google Doc URL | Link is stored as `linked_doc_url` and can be launched from the task card |
| Open linked doc    | User views task in Focus or Planner   | Link opens in new tab or preview modal                                    |

## Sync Infrastructure Notes
- Calendar sync uses OAuth 2.0 scopes for read/write per-user
- Sync is always opt-in and shown clearly in Settings
- Failed syncs should fall back gracefully with a log for debugging
- Rate limits are respected and changes are batched to minimize API calls
- For MVP, Docs integration is link-based only (no content indexing) 

## Privacy & Data Control
- All user data is encrypted in transit and at rest using Supabase-managed encryption
- Users may request a full export or deletion of their data at any time (self-service endpoint in Settings)
- No user data is used for training AI models or shared with third parties
- Scratch pad entries, task history, and reflection logs are stored in a user-scoped namespace
- User settings include fine-grained control over:
    - Calendar and document access
    - Memory summarization cadence
    - Reflection and logging preferences
- Default is maximum privacy: no sync or reflection data leaves the user’s scope unless explicitly enabled
- Calendar sync uses OAuth 2.0 scopes for read/write per-user
- Sync is always opt-in and shown clearly in Settings
- Failed syncs should fall back gracefully with a log for debugging    
- Rate limits are respected and changes are batched to minimize API calls
- For MVP, Docs integration is link-based only (no content indexing)

# ### View Model Definitions

Each screen in the app supports a small number of distinct UI states. These view models define layout structure, reactive behaviors, and coach interactivity.
## Today View / Planner

| State         | Description                                                                       |
| ------------- | --------------------------------------------------------------------------------- |
| `empty`       | No tasks scheduled. Coach suggests first task or brain dump.                      |
| `scheduled`   | Tasks present and sorted by time or priority. Coach may nudge for prioritization. |
| `overdue`     | One or more tasks not marked complete. Coach may prompt to review or adjust.      |
| `AI_planning` | User in reflection/planning interaction via Chat. Planner auto-syncs changes.     |
## Add Task Modal

| State       | Description                                                      |
| ----------- | ---------------------------------------------------------------- |
| `quick_add` | Simple title + optional due time. One-tap save.                  |
| `detailed`  | Expanded form: category, motivation, linked doc, value tag.      |
| `editing`   | Fields pre-populated from existing task. Save or delete enabled. |
## Focus Mode

| State       | Description                                                                    |
| ----------- | ------------------------------------------------------------------------------ |
| `active`    | Timer running; task and scratch pad visible. Coach quiet unless idle detected. |
| `paused`    | Timer stopped. User can resume, skip, or adjust task.                          |
| `completed` | Task marked complete or session ends. Trigger reflection prompt.               |
## Coach Panel / Chat View

| State          | Description                                                               |
| -------------- | ------------------------------------------------------------------------- |
| `passive`      | Awaiting input. Can surface soft nudges or summaries.                     |
| `engaged`      | Mid-conversation (planning, reflection, etc.). Displays adaptive prompts. |
| `summary_mode` | Delivering memory recall or suggesting changes. Often post-reflection.    |
## Scratch Pad

| State        | Description                                                      |
| ------------ | ---------------------------------------------------------------- |
| `open`       | Visible overlay. Captures new notes. Suggestion flag active.     |
| `minimized`  | Collapsed but still logging quick input (e.g., hotkey or voice). |
| `processing` | Coach actively analyzing recent scratch content for conversion.  |
# Offline & Fallback Behavior

Clarity is designed to remain useful even when the user is offline or encounters sync/API issues.
## Offline Functionality

| Feature               | Behavior                                                                         |
| --------------------- | -------------------------------------------------------------------------------- |
| Task Management       | Tasks can be created, edited, and deleted locally; changes sync when back online |
| Focus Mode            | Timer, Scratch Pad, and Task logging operate in local memory                     |
| Scratch Pad           | Entries are cached locally until confirmed synced                                |
| Reflections & Journal | Logged locally, queued for sync with memory and streak tracker                   |
## Fallback Logic

| Context                 | Fallback Behavior                                                              |
| ----------------------- | ------------------------------------------------------------------------------ |
| AI Coach Unavailable    | Show “Coach is resting” message; surface static tips or last cached suggestion |
| Prompt generation fails | Fall back to static template library with default tone and phrasing            |
| Sync errors (Calendar)  | Notify user and retry silently in background (or manual retry option)          |
| Google Docs link fails  | Warn and prompt user to check permissions manually                             |
## Technical Notes
- IndexedDB or similar client-side store used for offline cache
- Sync queue retries on app reconnect or relaunch
- Offline mode is visually indicated in Planner and Focus Mode with status banner
- Local-only changes are timestamped and conflict-resolved by last modified on sync.
