---
name: tool-guidance
description: >
  Static tool guidance for Clarity. Dynamic per-channel sections are injected by the prompt builder at runtime.
---

# Tool Guidance

> **Note:** Detailed tool guidance is populated dynamically by the prompt builder
> at runtime based on the active tool set and channel. This file is a placeholder.
>
> To add static tool guidance that should appear in all contexts, edit this file
> via the Clarity skill editor.

## Available Tool Categories

- **Email** -- read, search, compose, and send emails via Gmail
- **Calendar** -- view and create events via Google Calendar
- **Tasks** -- create, update, complete, and search tasks
- **Reminders** -- set and manage time-based reminders
- **Memory** -- store and recall long-term observations about the user
- **Web search** -- search the web for current information
- **Notifications** -- send messages and alerts to the user

Use `search_memories` before answering questions about the user's history.
Use `create_memories` to store new observations worth keeping.
