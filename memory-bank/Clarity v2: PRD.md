# **Clarity Assistant PRD (2025-05-30)**

## **Purpose**

Clarity is an executive-function assistant designed to give users clarity and focus by:

* **Filtering inbound noise** so they stop paying attention to what doesn't matter

* **Multiplying outbound output** so goals are met with less effort

* **Eliminating manual data entry** and returning attention to the user

Unlike traditional productivity tools, Clarity doesn't ask users to manage tools or structure. It operates invisibly, surfacing only when useful—and acting as a virtual executive assistant that thinks ahead, summarizes, plans, and executes.

## **Target Users**

* Knowledge workers, independent professionals, and overwhelmed parents

* Primary pain points: too much inbound noise, not enough proactive follow-up, cognitive overload from context switching and remembering everything

## **Core Experience Principles**

1. **Single Interface**: All complexity is hidden; user interacts through a chat window and planner UI  
2. **Proactive Intelligence**: Clarity initiates work when possible—not just responds  
3. **Low Friction**: No manual tagging, no setup, no structured inputs required  
   **Memory \+ Agency**: Clarity remembers, reasons, and acts on behalf of the user  
4. **Privacy-Respecting**: Always clear what’s being used and why

## **MVP Scope**

### **Inputs**

* Brain Dump (text/voice input)  
* Slack (DMs, Mentions, Select Channels)  
* Email (Gmail OAuth)  
* Calendar (Google Calendar API)

### **Outputs**

* Daily Digest: Slack, Email, Calendar triaged and summarized  
* Draft Responses: For Slack/email messages requiring input  
* Auto-Scheduled Focus Sessions: From task memory \+ calendar gaps  
* Reminders: From notes, recurring items, tasks with time references

### **UI Surfaces**

* Chat Window (primary interface)  
* Planner View (Today, Week)  
* Digest Feed (summary of new, handled, or upcoming)  
* Brain Dump Input Pane

## **Assistant Behavior**

### **Inbound Filtering**

* Slack and Email digested by LLM  
* Summarizes only high-signal threads  
* Flags actionables, requests, and critical updates

### **Outbound Multiplication**

* Drafts replies based on thread context  
* Creates tasks from notes and messages  
* Prepares calendar blocks without being asked  
* Prepares gift reminders, shopping carts, travel plans based on memory

### **Intelligence Constraints**

* Assistant does not block UI responsiveness—long ops run async  
* All tools and agents are hidden from user; surfaced only as outcomes  
* Assistant can trigger sub-agents and receive asynchronous updates

## **Key Subsystems**

* Memory System (short-term, long-term, value-tagged facts)  
* Agent Orchestrator (handles agent lifecycle, job queuing, status reporting)  
* Prompt Engine (builds structured prompt chains \+ tool calls)  
* UI Bridge (syncs memory/task/calendar state with frontend without lag)

## **Phased Implementation Approach**

### **Phase 1: Foundation – Ingest \+ Tasking**

* Brain Dump input  
* Ingest layer for Email, Calendar, Slack  
* Short-term Memory Store  
* Note-to-Task Agent  
* Planner View (Today)  
* Passive Reminder Engine

### **Phase 2: Output Automation – Agents & Digest**

* Slack Digest Agent  
* Email/SMS Reply Drafter  
* Task Classifier  
* Assistant Feed \+ Digest UI

### **Phase 3: Assistant as Multiplier**

* Auto-Scheduler Agent  
* Gift Suggestion \+ Reminder Agent  
* Grocery Planner Agent  
* Calendar Block Manager  
* Goal Tracking Dashboard

## **Module Breakdown**

| ModuleDescription |  |
| ----- | ----- |
| Brain Dump | Unstructured capture; interpreted by agents to suggest tasks or reminders |
| Slack Digest Agent | Summarizes mentions and threads into actionable summaries |
| Reply Drafter Agent | Drafts Slack/Email responses using context and tone memory |
| Scheduler Agent | Finds open calendar slots for key tasks and adds blocks proactively |
| Note-to-Task Agent | Transforms brain dump entries into suggested tasks |
| Reminder Agent | Surfaces deferred or time-sensitive tasks based on intent or history |
| Output Feed | Presents "what Clarity has done for you" in a digest format |

## **User Experience Narrative**

A user starts their day with no inbox overwhelm. Clarity has already digested overnight Slack and email activity, created a few suggested responses, and highlighted only the threads needing input. It’s drafted a plan for the day by combining known tasks, goals from the user’s memory, and available calendar blocks.

Throughout the day, the user jots down thoughts in the Brain Dump: ideas, reminders, vague to-dos. Clarity interprets and categorizes them, turning them into structured tasks or scheduling follow-ups.

When a coworker sends a Slack message asking for feedback on a doc, Clarity drafts a response and offers to schedule 30 minutes to review it. If a birthday or vacation is coming up, Clarity surfaces relevant reminders with suggested actions—like sending a gift or rescheduling work.

At the end of the day, the user sees a short digest of completed tasks, drafted responses, and quiet nudges for tomorrow’s top priorities. No chaos, no context-switching—just clarity.

### **Persona: John and Mary – The Busy Parents**

John and Mary are working parents juggling work deadlines, school activities, groceries, and doctors appointments. Clarity becomes their shared memory and scheduling buffer.

* Clarity auto-schedules pediatric appointments and back-to-school nights from their email/calendar.  
* When John adds "Prep snacks for soccer" to the Brain Dump, Clarity checks the pantry and suggests what to buy.  
* Mary forwards a teacher email about a field trip. Clarity turns it into a calendar event, adds a reminder to sign the form, and suggests a to-do to pack lunch.  
* They upload a photo of the class calendar to Clarity; it extracts dates and events and syncs them with their shared Google Calendar.  
* Every Sunday, Clarity handles meal planning: it remembers dietary preferences, drafts a weekly menu, and creates an Instacart cart for review and adjustment.  
* At dinner, they get a quiet summary: "3 things left this week, none urgent. You're ahead."

### **Persona: Anne – The Overloaded Professional**

Anne is a product manager managing multiple teams and drowning in messages. Clarity acts as her attention firewall and reply assistant.

* Each morning, Clarity presents a digest of 100+ Slack messages and highlights only 4 that need input.  
* Drafted responses are shown inline, ready to review or send.  
* Her Brain Dump contains half-written thoughts like "Follow up on API versioning"—Clarity turns it into a scheduled task with the right team tagged.  
* When she forgets to respond to a question from a week ago, Clarity surfaces it with: "Do you still want to reply to James?"  
* By Friday, Clarity has drafted a recap of completed work and proposes 3 planning blocks for next week.

Clarity doesn’t just organize Anne's chaos—it handles it, quietly and proactively.

## **Assistant Activity Rhythm**

To maintain a sense of reliability and minimize surprise, Clarity adheres to a clear but unobtrusive activity rhythm:

* **Daily Digest**: Delivered each morning by 7:30am, summarizing important messages, tasks, and meetings. Precise timing can be adjusted by the user.  
* **Planning Sync**: Runs after the Digest and again at midday. Checks in with the user on progress, automatically updates Planner view based on open time and task urgency.  
* **Reminder Review**: Clarity surfaces reminders and missed actions in the evening wind-down summary.  
* **Passive Monitoring**: Clarity watches for new brain dump entries, emails, Slack threads, or calendar changes and reacts within minutes—without interrupting the user unless required.

## **Memory Lifecycle**

Clarity maintains multiple layers of memory to personalize and prioritize effectively:

* **Working Memory (24h)**: Tracks active tasks, recent inputs, and interactions.  
* **Short-Term Summary (7–14 days)**: Captures recent completions, replies, themes in brain dump entries.  
* **Long-Term Memory**: Stores durable facts—preferences, habits, recurring goals, relationship reminders, and value tags.

Users don’t manage this memory directly, but Clarity occasionally surfaces “memory updates” when habits or themes shift—e.g., “You've mentioned ‘marketing campaign’ 5 times this week. Want to make it a project?”

## **Background Activity UX**

All agents run quietly in the background. To maintain user trust:

* Every action taken by Clarity is reflected in the **Assistant Output Feed**  
* Agent status is never exposed unless something fails or requires approval  
* Activity updates are phrased like journal entries: “✅ Replied to Sam on Q3 notes. 📆 Scheduled a follow-up.”

## **Interaction Modalities**

The user interacts with Clarity through a few predictable gestures:

* **Chat Window**: Ask for help, respond to nudges, review digests, or issue open-ended commands  
* **Planner UI**: Drag and drop tasks, accept or reject suggestions, view schedule overlays  
* **Inline Controls**: Accept draft responses, promote brain dump ideas to tasks, approve suggested purchases  
* **Global Quick Action (⌘K)**: Log a thought, ask for help, or navigate to focus mode

## **Mobile View Considerations**

Clarity’s mobile UX supports:

* Brain Dump capture (text or voice)  
* Digest review (including Slack, Email, Calendar)  
* Quick interaction with Assistant suggestions (e.g. “Reply,” “Add to Plan,” “Snooze”)  
* Notifications for actionable items only

More complex planning and reflection flows are deferred to desktop. Mobile favors frictionless capture and ultra-fast triage.

## **Master List System**

The master list is the foundation of Clarity’s long-term utility. It represents a comprehensive, dynamic set of life obligations, responsibilities, and priorities inferred from the user's context.

### **Overview**

* The assistant builds the master list during onboarding through conversation.  
* The list includes known recurring categories (e.g., "Car Maintenance", "Home Cleaning", "Birthday Reminders") and inferred ones (e.g., "Dog Care" if user has pets)  
* The user can review, add, edit, reorder, or archive list items. The assistant continues to evolve the list based on ongoing behavior.

### **Item Structure**

Each item on the master list may include:

* **Label** (e.g., "Grocery Planning")  
* **Time Anchors** (daily/weekly/monthly/yearly)  
* **One-Time and Recurring Tasks**  
* **Automation Scope**:  
  * `Silent Autonomy`: Do without asking, no notification  
  * `Autonomous with Update`: Do without asking, but notify  
  * `Suggest Mode`: Make suggestions, request approval  
  * `Manual Only`: Only act if explicitly asked  
  * `Ignore`: Track but take no action

### **Interaction Surface**

* Initially shown as a document in the canvas to support scale, search, and easy editing  
* Users can reorder, set frequency, or adjust automation level per item  
* Future UI enhancements may use **cards** with a **drag-and-drop interface**

### **Example Items**

* School Calendar → Extracted events, reminders, permissions, packing lists  
* Pets → Vet visits, flea meds, park visits, food reordering  
* Vehicles → Oil changes, tire rotation, inspection scheduling  
* Taxes → Quarterly estimate reminders, annual prep  
* Holidays → Gift planning, travel coordination, hosting prep

### **Lifecycle States**

* `Suggested` → proposed by assistant  
* `Accepted` → confirmed by user  
* `Paused` → snoozed until relevant again  
* `Archived` → removed from active memory

The master list is Clarity’s internal map of what the user *needs to care about*. It is not a to-do list—it is a **system awareness template** that powers automation, memory, and prioritization across agents.

### **Master List Example**

📌 Car Maintenance

\- Frequency: Monthly

\- Next: Tire rotation (Oct 15\)

\- Automation: Suggest

\- Status: Accepted

\- Notes: Subaru Outback, last service June

\- Source: Onboarding Chat

📌 School Calendar

\- Frequency: Yearly \+ Ad hoc

\- Next: Field trip (Sep 12), Back to School Night (Aug 30\)

\- Automation: Autonomous with Update

\- Notes: PS 87 Class 2B

\- Source: Uploaded Image

📌 Grocery Planning

\- Frequency: Weekly (Sunday PM)

\- Automation: Silent

\- Notes: Dairy-free, kids hate zucchini

\- Source: Brain Dump

## **First-Session Magic**

Clarity earns trust in its first 5 minutes by demonstrating real action:

* The user starts a chat and is asked a few smart, respectful questions about their life: family, location, profession, routines.  
* Clarity uses this to generate a "master list" of life priorities: bills, maintenance, birthdays, appointments, responsibilities, planned vacations.  
* The user corrects or adjusts the list naturally through conversation: "We have two dogs" → Clarity adds vet visits, immunizations, daily walks.  
* When the master list is aligned, Clarity can begin to act \- it proposes calendar events for the upcoming year.  
* From there, Clarity is ready to act. Upload a school calendar photo? It parses and schedules everything. Ask about dinner? It checks preferences, drafts a menu, and queues a grocery cart or Doordash order from a local restaurant.

The goal: Clarity starts by listening, builds a useful mental model of the user's life, and immediately begins removing friction—without any setup or explanation required. The user remains in control of the changes and can provide feedback about what's important. Clarity can immediately adjust based on the user's needs.