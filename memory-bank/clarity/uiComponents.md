### 1. **Navigation & Layout**

| Component  | Description                                                                 |
| ---------- | --------------------------------------------------------------------------- |
| `AppShell` | Layout wrapper with left-hand nav, top status/header, and content region    |
| `SideNav`  | Vertical nav with icons (Today, Focus, Coach, Settings)                     |
| `TopBar`   | Shows current date, streak progress, and optional profile or mode indicator |

---

### 2. **Task Management Components**

| Component         | Description                                                                                |
| ----------------- | ------------------------------------------------------------------------------------------ |
| `TaskCard`        | Task with checkbox, time, title, optional category pill. Used for displaying tasks in various views. |
| `TaskListGroup`   | Group of tasks per time block, with label (Morning, Afternoon, Evening)                    |
| `TaskDetailTray`  | Expanded task view for editing, used within Add Task or after clicking a task              |
| `FABQuickAdd`     | Bottom-right floating button that expands into inline quick-add input (`OpenedFAB.pdf`)    |
| `QuickAddTray`    | Tray-style form with task name, time, priority, reminders, "Add" button                    |
| `TaskStatusBadge` | Inline badge showing task status (e.g., Completed, Skipped, Upcoming)                      |

---

### 3. **Focus Mode**

|Component|Description|
|---|---|
|`FocusTimer`|Circular timer UI with countdown, play/pause, and complete button|
|`FocusHeader`|Task name + optional category tag|
|`ScratchPadToggle`|Opens Scratch Pad overlay from within Focus Mode|
|`ReflectionPrompt`|Appears at session end, prompting mood and outcome input|

---

### 4. **Chat / Coach Panel**

|Component|Description|
|---|---|
|`CoachPanel`|Full chat view or side panel with AI-generated suggestions|
|`MessageBubble`|Chat message with timestamp (e.g. from `Message bubble.png`)|
|`MessageInput`|"Start typing..." input with send icon (`Message footer.png`)|
|`MessageHeader`|Header with avatar, tone tag, or prompt label (`Message header.png`)|
|`CoachCard`|Summarized suggestions like "Want help prioritizing today's tasks?"|

---

### 5. **Scratch Pad**

|Component|Description|
|---|---|
|`ScratchOverlay`|Overlay that slides in with input and history of captured thoughts|
|`ScratchEntryCard`|A single entry with timestamp, edit, and "Convert to Task"/archive buttons|

---

### 6. **Reflection & Review**

|Component|Description|
|---|---|
|`ReflectionModal`|Modal that appears after Focus Mode or EOD, prompts user for feedback|
|`MoodPicker`|Emoji or word-based quick selection of mood|
|`TaskOutcomeSelector`|Buttons for "Completed", "Worked on it", "Skipped"|

---

### 7. **Settings & Controls**

|Component|Description|
|---|---|
|`SettingsPage`|Full page with sections: tone, structure, reminders, data export|
|`TimeBlockEditor`|UI to manage custom time blocks (Work, Family, etc.)|
|`ToggleField`|UI toggle (Radix UI Switch) for preferences (e.g., enable reminders, enable rewards)|

---

### 8. **General / Atomic Components**

|Component|Description|
|---|---|
|`Checkbox`|Accessible checkbox component (Radix UI Checkbox).|
|`Modal`|Accessible modal dialog component (Radix UI Dialog) with CSS animations.|
|`ErrorMessage`|Component for displaying standardized error messages, typically for form validation.|

---
