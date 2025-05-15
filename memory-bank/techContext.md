# Tech Context

This document outlines the technical stack, architecture, and key implementation patterns for the project, covering both the CLI (Local LLM Terminal Environment) and Web (Clarity) applications.

## 1. Core Technologies & Stack

### CLI Application (Local LLM Terminal Environment)
*   **Programming Language:** Python 3.x
*   **LLM Interaction Framework:** LangChain
*   **Initial LLM Provider:** Google Cloud (for Gemini Pro API)
*   **Command Line Interface (CLI):** Click
*   **Structured Data Handling:** PyYAML
*   **Configuration Management:** PyYAML, python-dotenv
*   **File Parsing:** Standard Python I/O, markdown library

### Web Application (Clarity)
*   **Frontend Framework:** React 18+
*   **Styling & Theming:**
    *   **Primary Theming Engine:** Radix UI Themes (`@radix-ui/themes`) for base theming, color palettes (light/dark modes, accent colors), and consistency with Radix Primitives.
    *   **Utility Styling:** TailwindCSS for layout, spacing, typography, and styling custom components or overriding Radix Theme styles where necessary.
    *   **Integration:** TailwindCSS will be configured to utilize Radix Theme's CSS custom properties for semantic color definitions.
*   **UI Primitives:** Radix UI (`@radix-ui/react-*`) for accessible, unstyled (or lightly styled by Radix Themes) component behaviors.
*   **State Management:**
    *   **Server State:** React Query (`@tanstack/react-query`) for data fetching, caching, and mutations.
    *   **Client State:** Zustand for global client-side state (e.g., overlay management).
*   **Backend Services:** Supabase (Auth, Database, Storage)
*   **API Layer (between WebApp and Python Core):** FastAPI (Python) application (`chatServer/`)
    *   This acts as a bridge to the Python-based LLM agent backend.
*   **LLM Integration (Web):** LangChain (via FastAPI backend), potentially OpenRouter-compatible API layer.
*   **UI Components (Libraries):**
    *   Radix UI Themes (`@radix-ui/themes`) - For theming provider and some pre-styled components.
    *   Radix UI Primitives (`@radix-ui/react-*`) - For core accessible behaviors.
    *   Framer Motion (for deliberate, simple animations, prefer CSS animations where possible)
    *   `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/modifiers` (for drag-and-drop functionality)
*   **Form Handling:** React Hook Form + Zod
*   **Date/Time:** date-fns
*   **Notifications:** react-hot-toast
*   **Icons:** Lucide Icons
*   **Calendar Integration:** Google Calendar API
*   **Document Integration:** Google Docs API

### General
*   **File Formats:**
    *   Notes & Free Text: Markdown (.md)
    *   Structured Data: YAML (.yaml, .yml) - Primary config, JSON - API/state.
    *   Environment: .env files.
*   **Development Tools & Environment:**
    *   OS: Ubuntu 24.04 LTS
    *   Version Control: Git
    *   Package Management: Python (pip + `requirements.txt`), Node (pnpm + `pnpm-workspace.yaml`)
    *   Code Editor: Cursor
    *   Development Server (Web): Vite
    *   Testing: Python (pytest), Frontend (Vitest + Testing Library)
    *   Linting/Formatting: Python (black, flake8), Frontend (ESLint, Prettier)
    *   CI/CD: GitHub Actions
*   **Infrastructure & Services (Production for Web):**
    *   Hosting: Frontend (Vercel/Cloudflare Pages), API (FastAPI on Fly.io, Cloud Run, etc.)
    *   Database & Auth: Supabase
    *   Monitoring: Sentry
    *   Analytics: PostHog (opt-in)
*   **Security & Privacy (Web):**
    *   Authentication: OAuth 2.0 (Supabase)
    *   Data Encryption: At rest (Supabase), In transit (TLS)
    *   Access Control: Row-level security (Supabase)

## 2. System Architecture Overview

The system follows a modular architecture:

*   **CLI Application:** Consists of a CLI Layer, Core Layer (agent logic, LLM interaction), and Utilities.
    *   `src/utils/config_loader.py`: Loads app config (base YAML + .env overrides).
    *   `src/utils/path_helpers.py`: Centralized path construction.
    *   `src/utils/chat_helpers.py`: REPL command helpers, memory management.
    *   `src/core/llm_interface.py`: Consistent LLM interaction via LangChain.
    *   `src/core/file_parser.py`: Reads Markdown and YAML.
    *   `src/core/context_manager.py`: Gathers global context.
    *   `src/core/agent_loader.py`: Loads agent configs, tools, and constructs `AgentExecutor`.
*   **Web Application (Clarity):** Consists of a UI Layer (React), State Management (React Query, Zustand), and an API Layer (custom hooks interacting with `chatServer/` and Supabase).
    *   The `chatServer/` (FastAPI) acts as an intermediary to the core Python agent logic.
*   **Shared Services:** Supabase (Auth, DB, Storage), LLM Services.

*(Mermaid diagrams from the original systemPatterns.md can be referenced there for visual architecture)*

### Key Architectural Decisions & Principles
*   **Modular Code Organization:** Clear separation of concerns.
*   **State Management (Web):** Defined above (React Query for server, Zustand for client). Centralized overlay state management (`useOverlayStore`).
*   **UI Component Architecture (Web):** Atomic Design, Radix UI primitives + Tailwind styling, custom hooks. Wrapper components for common Tailwind patterns.
*   **Data Flow (Web):** Unidirectional, server-state sync via React Query, optimistic updates.
*   **Authentication & Authorization (Web):** OAuth with Supabase, RLS.
*   **API Interaction (Web):** Centralized API interaction via React Query custom hooks in `@/api/hooks/`. No direct `supabase` client calls or `fetch` calls in UI components.

## 3. Key Implementation Patterns (Clarity Web App)

*(These are detailed further in `memory-bank/clarity/implementationPatterns.md` and `memory-bank/systemPatterns.md`)*

*   **Pattern 1: Centralized Overlay State Management:** Use `useOverlayStore` (Zustand) and an `OverlayManager`.
*   **Pattern 2: UI Component Strategy: Radix UI Themes & Primitives + Tailwind CSS:** Utilize Radix UI Themes for overall theming and color management. Use Radix UI Primitives for base component behaviors. Style with TailwindCSS, leveraging Radix Theme CSS variables for color consistency.
*   **Pattern 3: Re-evaluated Animation Strategy:** Prefer CSS transitions/animations. Use `framer-motion` sparingly.
*   **Pattern 4: Consolidated Application Layout:** Single main layout component (e.g., `AppShell.tsx`).
*   **Pattern 5: Centralized API Interaction with React Query:** All backend interactions via custom hooks in `@/api/hooks/`.
*   **Pattern 6: Encapsulating Styling Patterns with Wrapper Components:** Create reusable components for common Tailwind utility combinations.
*   **Pattern 7: Consistent Error Display:** Standardized `ErrorMessage.tsx` component.
*   **Pattern 8: Consistent Loading Indication:** Standardized spinners/skeletons, use React Query `isLoading`/`isFetching`.
*   **Pattern 9: Form Management:** React Hook Form + Zod.
*   **Pattern 10: Accessibility Best Practices:** Semantic HTML, ARIA, keyboard navigation, etc.
*   **Pattern 11: Standardized DDL & RLS:** Central DDL (`memory-bank/clarity/ddl.sql`), RLS via Supabase migrations.

## 4. Project Structure (High-Level)
*   `cli/`: CLI Application (Python, LangChain)
*   `webApp/`: Web Application (React, Vite, TailwindCSS) - Formerly `web/apps/web`
*   `chatServer/`: Backend API for WebApp (FastAPI, Python) - Formerly `web/apps/api`
*   `memory-bank/`: Project memory, including `tasks.md`, `prd.md`, context files, etc.
*   `src/`: Core Python logic for the agent system (used by CLI and `chatServer/`)

## 5. Core Data Models (Derived from `memory-bank/clarity/componentDefinitions.md`)

This section outlines key data structures. Detailed DDL and RLS policies for Supabase implementation are managed in `data/db/ddl.sql` and `memory-bank/clarity/supabaseRLSGuide.md`.

### 5.1. User Settings & Preferences
*   **Purpose:** Personalize AI coach, define daily flow boundaries, configure interface.
*   **Core Fields:**
    *   `user_id`: string (User reference key)
    *   `preferred_tone`: enum (`cheerful`, `gentle`, `directive`)
    *   `day_structures`: list (User-defined time blocks: name, type, start/end times, active days)
    *   `start_of_day`: time
    *   `end_of_day`: time
    *   `work_blocks_max`: number (Max consecutive focus sessions before break)
    *   `long_break_freq`: number (After how many sessions for long break)
    *   `reward_enabled`: boolean
    *   `notifications_enabled`: boolean
    *   `default_view`: enum (`planner`, `chat`, `focus`)
    *   `theme`: enum (`light`, `dark`, `low-stim`)
    *   `enable_animations`: boolean

### 5.2. Task Object
*   **Purpose:** Atomic unit for planning, execution, reflection.
*   **Relations:** 1:many to Subtasks, 1:1 to Projects (future).
*   **Core Fields:**
    *   `id`: string (Unique identifier)
    *   `title`: string (Short description)
    *   `description`: string (Optional longer detail)
    *   `status`: enum (`pending`, `in_progress`, `completed`, `skipped`)
    *   `created_at`: timestamp
    *   `updated_at`: timestamp
    *   `due_date`: date (Optional)
    *   `category`: string (User-defined or system label)
    *   `value_tag`: string (Optional value alignment)
    *   `linked_doc_url`: string (Optional Google Doc/external URL)
    *   `motivation`: string ("Why this matters")
    *   `reward_trigger`: boolean (Task yields a reward)
    *   `streak_eligible`: boolean (Counts towards streaks)
    *   `breakdown`: list (AI-suggested subtasks/steps)
    *   `execution_logs`: list (Sessions: start/end time, scratch pad summary)
    *   `completion_note`: string (Optional user reflection post-completion)
    *   `user_id`: string (Foreign key to user) - *Ensured for RLS*
    *   `time_period`: TEXT CHECK (time_period IN ('Morning', 'Afternoon', 'Evening')) - *From ddl.sql*
    *   `notes`: TEXT - *From ddl.sql, possibly maps to description or completion_note depending on usage*
    *   `completed`: BOOLEAN DEFAULT FALSE NOT NULL - *From ddl.sql, maps to status='completed'*
    *   `position`: integer (For ordering in lists, e.g., Today View) - *Implied by dnd-kit tasks*


### 5.3. Scratch Pad Entry
*   **Purpose:** Low-friction capture for thoughts/ideas during execution.
*   **Core Fields:**
    *   `id`: string (Unique identifier)
    *   `content`: string (User-entered text/voice transcription)
    *   `created_at`: timestamp
    *   `session_id`: string (Optional reference to focus session)
    *   `task_context`: string (Optional task ID user was working on)
    *   `archived`: boolean
    *   `converted_to_task`: boolean
    *   `user_id`: string (Foreign key to user) - *Implied for RLS*

### 5.4. Focus Session Log
*   **Purpose:** Log task execution sessions (Pomodoro-style) for time-on-task and reflections.
*   **Core Fields:**
    *   `id`: string (Unique session ID)
    *   `task_id`: string (Reference to Task)
    *   `user_id`: string (Foreign key to user) - *Implied for RLS*
    *   `started_at`: timestamp
    *   `ended_at`: timestamp
    *   `interrupted`: boolean (Session stopped early)
    *   `notes`: string (User summary of what was done)
    *   `mood`: enum (e.g., `energized`, `drained`)
    *   `duration`: number (Minutes or seconds)

### 5.5. Streak Tracker
*   **Purpose:** Gamification by tracking consecutive days with completed tasks/reflection.
*   **Core Fields:**
    *   `user_id`: string (User ID)
    *   `current_streak`: number
    *   `longest_streak`: number
    *   `last_activity_date`: date
    *   `type`: enum (`task_completion`, `reflection_logged`) - *Suggestion: To track different types of streaks if desired*

## 6. Key Implementation Patterns (Clarity UI/API - Derived from `memory-bank/clarity/implementationPatterns.md`)

This section outlines key architectural patterns and strategies. Style-guide specific component strategies (like Radix Theming) are in `style-guide.md`.

### 6.1. Pattern 1: Centralized Overlay State Management
*   **Goal:** Manage modals, trays, etc., consistently using `useOverlayStore` (Zustand) and an `OverlayManager`.
*   **Method:** `useOverlayStore` controls which overlay is open and passes data. `OverlayManager` renders the correct overlay. Overlays get state/data via props and call `useOverlayStore.getState().closeOverlay()`.
*   **Avoid:** Individual `isOpen` states in components/pages for overlays.

### 6.2. Pattern 3: Re-evaluated Animation Strategy (CSS over Framer Motion)
*   **Goal:** Use animations deliberately, favoring simplicity and CSS transitions/keyframes.
*   **Method:** Align with "low-stim" and "minimal cognitive load".
*   **Avoid:** `framer-motion` for animations achievable with CSS; complex or distracting animations.

### 6.3. Pattern 4: Consolidated Application Layout
*   **Goal:** Single, clear component for main application structure (e.g., `webApp/src/layouts/AppShell.tsx`).
*   **Method:** All routes requiring the main layout use this single component.
*   **Avoid:** Multiple layout files for the same purpose.

### 6.4. Pattern 5: Centralized API Interaction with React Query
*   **Goal:** Consistent data fetching/mutation using `@tanstack/react-query`, encapsulating API logic.
*   **Method:** Custom React Query hooks (e.g., `useTasks`) in `@/api/hooks/` encapsulate Supabase or `chatServer` calls. Components use these hooks. `onSuccess` handlers invalidate queries.
*   **Avoid:** Direct Supabase/fetch calls in UI components; manual loading/error/data state for API calls.

### 6.5. Pattern 6: Encapsulating Styling Patterns with Wrapper Components
*   **Goal:** Reusable, recognizable styling patterns for Tailwind CSS by creating dedicated React wrapper components.
*   **Method:** Identify repeated Tailwind utility sets, create small wrapper components (e.g., `PanelContainer`, `Card`), apply utilities inside. Use `clsx` for conditional classes.
*   **Avoid:** Repeating long strings of Tailwind utilities for logical UI patterns.


## Tailwind CSS Best Practices

### Defining Semantic Colors for `@apply`

When defining custom semantic colors in `tailwind.config.js` that are intended to be used with the `@apply` directive within CSS files (e.g., in `ui-components.css`):

*   **Prefer "root" semantic names** for your color keys.
    *   Example: Instead of `colors: { 'bg-brand-primary': 'var(--accent-9)' }`, use `colors: { 'brand-primary': 'var(--accent-9)' }`.
*   Tailwind will then automatically generate the necessary utility class variants from this root name (e.g., `.bg-brand-primary`, `.text-brand-primary`, `.border-brand-primary`).
*   You can then reliably use these generated classes with `@apply` (e.g., `@apply bg-brand-primary;`).
*   **Avoid using utility prefixes (like `bg-`, `text-`) directly within the color configuration keys if you intend to use them broadly with `@apply`.** While Tailwind allows this for creating explicitly named utilities (e.g., `colors: { 'bg-only-this': 'value' }` generates *only* `.bg-only-this`), this approach can sometimes lead to issues where `@apply` fails to resolve the class. If an explicitly named utility is strictly necessary and `@apply` is problematic, direct CSS variable assignment (e.g., `background-color: var(...)`) can serve as a workaround. 