### 🎯 Goal
Define the high-level structure of the refactored project, outlining the roles of its major components and how they interact. This pattern documents the architectural decisions made during the Phase 0.6 project restructure.

*   **DO:** Maintain a clear separation of concerns between the frontend application (`webApp`), the backend API server (`chatServer`), and the core LLM agent logic (`src`).
*   **DO:** Use the defined interaction flows for communication between these components.
*   **DO:** Manage environment-specific configurations in their respective locations (`webApp/.env`, root `.env`).

### 1. Overall Structure & Roles

The project is now organized into three primary top-level directories, each serving a distinct purpose:

*   **`webApp/`**: Contains the React/TypeScript frontend application. This is what the end-user interacts with for task management, AI coaching, and other UI-driven features. It is responsible for all presentation logic and direct user interaction.
    *   Further details in `webApp/README.md`.
*   **`chatServer/`**: A Python FastAPI backend server. Its primary roles are:
    1.  To provide an API for the `webApp` (e.g., for chat functionality, agent-driven actions).
    2.  To load and manage Langchain agent configurations (from `config/agents/`).
    3.  To execute agent logic by leveraging the core `src/` directory.
    4.  (Future) To handle more complex backend tasks, data processing, or interactions with external services that shouldn't be done directly from the frontend.
    *   Further details in `chatServer/README.md`.
*   **`src/`**: The core Python library for the LLM agent framework. This includes:
    1.  The command-line interface (CLI) for direct agent interaction and development.
    2.  Core logic for agent instantiation, context management, and tool integration.
    3.  Utilities for configuration loading and other shared functionalities.
    *   This directory is utilized by both the `chatServer` (as a library) and the standalone Python CLI.

### 2. Key Decision: Separation of Concerns

The main driver for the refactor was to establish a clearer separation of concerns:

*   **Frontend (`webApp`):** Focuses solely on user interface and user experience. It fetches data and triggers actions via APIs.
*   **Backend (`chatServer`):** Acts as an intermediary and business logic layer. It protects direct access to certain resources, orchestrates complex operations (like agent execution), and can manage its own state or connections (e.g., to Supabase with service roles if needed for specific agent tasks).
*   **Core Logic (`src`):** Contains the reusable engine for LLM agent functionality, independent of how it's exposed (CLI or `chatServer`).

This separation improves maintainability, scalability, and allows for independent development and deployment of the different parts of the application.

### 3. Interaction Flows

*   **`webApp` <-> `chatServer`:**
    *   The `webApp` communicates with the `chatServer` primarily via RESTful API calls to endpoints defined in `chatServer/main.py` (e.g., `/api/chat`).
    *   All chat messages from the UI are sent to the `chatServer`.
    *   (Future) Other agent-driven actions initiated from the UI (e.g., processing notes, creating tasks via agent) will also go through `chatServer` APIs.
*   **`chatServer` <-> `src/`:**
    *   The `chatServer` imports and uses modules from the `src/` directory as a Python library.
    *   It relies on `LLM_AGENT_SRC_PATH=src` (set in the root `.env` file) being added to `sys.path` (as handled in `chatServer/main.py`) to find and load core agent logic, configurations, and utilities from `src/`.
    *   Specifically, it uses `ConfigLoader` and agent execution logic from `src/core/` to run agents based on requests from the `webApp`.
*   **`webApp` <-> Supabase:**
    *   For user authentication and direct data operations (CRUD on tasks, user settings, etc.), the `webApp` interacts directly with Supabase.
    *   This interaction is managed through React Query hooks (`@/api/hooks/`) as defined in **Pattern 5**, which use the Supabase JavaScript client.
    *   Security for these direct frontend-to-Supabase calls is enforced by Supabase's Row Level Security (RLS) policies, as defined in **Pattern 11**.

### 4. Path Aliases & Module Resolution

*   **`webApp/` (Frontend):**
    *   Uses TypeScript path aliases (e.g., `@/*` pointing to `webApp/src/*`) defined in `webApp/tsconfig.json` for cleaner and more maintainable import paths within the React application.
*   **`chatServer/` & `src/` (Backend & Core):**
    *   The `chatServer` relies on the `src/` directory being available in the Python path. This is typically achieved by setting `LLM_AGENT_SRC_PATH=src` in the root `.env` file, which `chatServer/main.py` uses to dynamically add `src` to `sys.path`.
    *   The core Python CLI in `src/` also benefits from the project root being set up for `pip install -e .`, which makes the `src` package importable.

### 5. Configuration Management

*   **Root `.env`:**
    *   Contains global environment variables like `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `LANGSMITH_API_KEY`, `LLM_AGENT_SRC_PATH`.
    *   Used by both `chatServer` and the `src/` core CLI.
*   **`webApp/.env`:**
    *   Contains frontend-specific environment variables, prefixed with `VITE_` (e.g., `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`).
    *   These are bundled into the frontend application by Vite during the build process.
*   **`config/agents/`:**
    *   Contains YAML configuration files for different LLM agents.
    *   These are loaded by the `ConfigLoader` in `src/core/config_loader.py`, which is used by both `chatServer` and the CLI.

### 6. Supabase Integration

*   **Authentication:** Supabase is the primary authentication provider. The `webApp` uses Supabase Auth UI and client libraries for user sign-up, sign-in, and session management.
*   **Database:** Supabase Postgres is used as the primary database for storing application data (tasks, user profiles, etc.).
*   **RLS (Row Level Security):** As detailed in **Pattern 11**, RLS is critical for securing data access when the `webApp` interacts directly with Supabase.
*   **Migrations:** Database schema changes (DDL, RLS policies) are managed via Supabase migrations (`supabase/migrations/`). The `memory-bank/clarity/ddl.sql` file should be kept in sync with the applied migrations as a reference.

---

*This pattern concludes the initial set of architectural guidelines derived from the project refactor and existing best practices. Further patterns may be added as the system evolves.* 