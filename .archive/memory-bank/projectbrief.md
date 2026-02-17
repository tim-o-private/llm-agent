# Project Brief

## 1. Project Overview

This project encompasses two main initiatives:

1.  **Local LLM Terminal Environment (CLI):** A Python-based terminal application for interacting with Large Language Models (LLMs) using local file-based context (Markdown, YAML). It aims to provide structured, predictable LLM interactions, initially for project and calendar management assistance. Key features include agent configuration, file-based global and agent-specific context, a REPL interface, and tool usage for file interaction.

2.  **Clarity (Web Application):** A cross-platform planning and executive function assistant designed for adults with ADHD. It focuses on daily task planning, AI-powered coaching, and distraction management. The MVP aims to reduce friction around task initiation and time blindness through a calming, supportive interface with Google Calendar/Docs integration.

## 2. Core Goals

*   **CLI:**
    *   Enable functional LLM interaction with structured, local file-based context.
    *   Utilize LangChain for LLM flexibility.
    *   Serve as a learning platform for AI-assisted development.
*   **Clarity (Web App):**
    *   Provide an MVP with core task planning, habit-forming features, and AI coaching.
    *   Integrate seamlessly with Google Calendar & Docs.
    *   Prioritize simplicity, low friction, and a neurodivergent-friendly design.
    *   Initial landing view for Clarity: Home ('Today') view with integrated chat for AI onboarding.

## 3. Target Audience

*   **CLI:** Technical users, developers wanting local-first LLM interaction and context management.
*   **Clarity:** Adults with ADHD needing support for executive functions, emotional regulation, and adaptive task planning.

## 4. Scope & Key Deliverables (MVP / Initial Phases)

*   **CLI:**
    *   Functional REPL for agent interaction.
    *   Agent configuration and context loading from local files.
    *   Basic file system tools for agents.
    *   'Architect' agent for backlog refinement.
*   **Clarity Web App (Phased Approach):**
    *   **Foundations (Phase 0-0.6):** Auth, UI shell, core task system, scalable design patterns, project restructure, deployment strategy, enhanced chat server.
    *   **AI & Integrations (Phase 1):** AI chat coach (text-based), rule-based nudge system, Google Calendar (basic 2-way sync for non-recurring events), Google Docs linking (no in-app preview for MVP).
    *   **Productivity Layer (Phase 2):** Visual Pomodoro timer, brain dump, focus view, basic gamification (streak counts).
    *   **AI Coach Interaction:** Daily chat check-ins, nudges (system notifications, not in main chat), AI suggestions on scratch pad save, AI task breakdown on creation. Single `ui_directive` support: `show_confetti`.

## 5. High-Level Technical Approach

*   **CLI:** Python, LangChain, Click, YAML/Markdown for data.
*   **Clarity Frontend:** React, TailwindCSS, Radix UI Primitives, Zustand, React Query, Vite.
*   **Clarity Backend:** Supabase (Auth, DB, Storage), FastAPI (`chatServer/`) as a bridge to Python agent core.
*   **AI Model:** Initially Gemini Pro, with LangChain for flexibility.

## 6. Success Metrics (Initial)

*   **CLI:** Users can interact with LLMs using local file context and switch agents.
*   **Clarity:** Users can complete daily planning with AI coaching, nudges are effective, integrations work, and the app is performant. 