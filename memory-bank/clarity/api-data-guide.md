# Clarity API & Data Management Guide

## CRITICAL API & DATA RULES

*   **Plan-Driven Development:** Always consult `@ui-implementation-plan.md` (via `memory-bank/tasks.md`), `memory-bank/clarity/progress.md`, and `memory-bank/clarity/prd.md` to ensure your work aligns with current tasks, completed work, and overall feature requirements.
*   **Adhere to Patterns:** Strictly follow the architectural and implementation patterns defined. Do not introduce new patterns without discussion and approval. Refer to the "Detailed API & Data Guidance" section below for links to specific pattern details.
*   **Centralized API Interaction (React Query):** MANDATORY use of React Query (`@tanstack/react-query`) for all data fetching, caching, and mutations (Supabase or `chatServer` API). Encapsulate all API calls within custom React Query hooks in `webApp/src/api/hooks/`. Components or Zustand stores MUST NOT make direct API calls.
*   **Standardized DDL & Row Level Security (RLS):** All Data Definition Language (DDL) changes, including those for Row Level Security (RLS), MUST be managed via Supabase migration scripts. Ensure `memory-bank/clarity/ddl.sql` is updated to reflect the current schema, and follow the RLS implementation guide in `memory-bank/clarity/references/guides/supabaseRLSGuide.md`.
*   **Backend (`chatServer/`) Development:**
    *   Maintain clear project structure in `chatServer/` (e.g., `main.py`, `routers/`, `services/`, `models/`).
    *   Design RESTful endpoints using Pydantic models for request/response validation.
    *   Secure endpoints with JWT validation (from Supabase Auth) and implement appropriate authorization logic.
    *   Implement consistent error handling (JSON responses, HTTP status codes) via FastAPI exception handlers.
    *   Manage dependencies via `chatServer/requirements.txt` and use virtual environments.
    *   The `chatServer` should leverage the core agent logic and utilities from the `src/` directory via `LLM_AGENT_SRC_PATH`.
*   **Local-First State Management (Zustand with Sync - P12):** For entity data requiring immediate UI feedback and offline capabilities, use Zustand stores with local-first operations (optimistic updates, temporary IDs) and background synchronization with the server. This complements React Query for server state. (Details linked below)

---

## Detailed API & Data Guidance

**Note:** The main `implementationPatterns.md` document is undergoing refactoring. Key individual API/Data-related patterns are detailed and linked below. For any pattern not yet listed here, or for UI patterns, consult `implementationPatterns.md` (while it is being phased out) or `ui-guide.md`.

*   **P5: Centralized API Interaction (React Query)**
    *   **Summary:** MANDATORY use of React Query for all data fetching/caching/mutations. API calls encapsulated in custom hooks in `webApp/src/api/hooks/`.
    *   **Full Details & Example:** [./references/patterns/centralized-api-interaction.md](./references/patterns/centralized-api-interaction.md)
*   **P11: Standardized DDL & Row Level Security (RLS)**
    *   **Summary:** Maintain an up-to-date `ddl.sql`, manage schema changes and RLS via Supabase migrations. Use the reusable SQL helper function for RLS.
    *   **Full Details & Guide:** [./references/patterns/standardized-ddl-rls.md](./references/patterns/standardized-ddl-rls.md) (Links to `memory-bank/clarity/references/guides/supabaseRLSGuide.md`)
*   **P12: Local-First State Management with Eventual Sync**
    *   **Summary:** Use Zustand stores with local-first operations and background synchronization for responsive UI and offline capabilities.
    *   **Full Details & Example:** [./references/patterns/local-first-state-management.md](./references/patterns/local-first-state-management.md)

### Visualizing Data Flows:
*   For diagrams illustrating the local-first state management, optimistic updates, and data synchronization processes, refer to: [./references/diagrams/state-management-flow.md](./references/diagrams/state-management-flow.md)

### Key Supporting Documents for API & Data:
*   `memory-bank/clarity/ddl.sql` (Definitive database schema - ensure this is kept up-to-date with migrations)
*   Frontend TypeScript types are defined in `webApp/src/api/types.ts`.
*   Backend Pydantic models are defined in `chatServer/models/` (or `chatServer/schemas/`).
*   `memory-bank/clarity/references/guides/supabaseRLSGuide.md` (Detailed guide for implementing Row Level Security)

### Database Changes Workflow
*   All DDL changes (table creation, alterations, RLS policies, helper functions, etc.) MUST be managed via Supabase migration scripts located in `supabase/migrations/`.
*   After applying migrations, ensure `memory-bank/clarity/ddl.sql` is updated to accurately reflect the current state of the database schema.
*   For RLS, follow the standardized approach using a reusable SQL helper function as detailed in `memory-bank/clarity/references/guides/supabaseRLSGuide.md`.

### Backend API (FastAPI) Development Guidelines (`chatServer/`)

This section provides specific guidance for developing and maintaining the FastAPI backend application, which resides in `chatServer/`.

1.  **Project Structure (`chatServer/`):**
    *   `main.py`: Located in `chatServer/main.py`. FastAPI application instantiation, middleware, and global configurations.
    *   `routers/` (or `endpoints/`): Future directory within `chatServer/` for API routers. Each router should group related endpoints (e.g., `chat_router.py`, `agent_actions_router.py`).
    *   `services/`: Future directory within `chatServer/` for the business logic layer.
    *   `models/` (or `schemas/`): Future directory within `chatServer/` for Pydantic models.
    *   `db/` (or `database/`): Future directory within `chatServer/` for database client setup (e.g., Supabase client initialization for Python).
    *   `core/`: Future directory within `chatServer/` for core configurations, settings loading for the server (if split from `main.py`).
    *   `utils/`: Future directory within `chatServer/` for utility functions specific to the backend.
    *   Reference `LLM_AGENT_SRC_PATH` (set in `.env`) for integrating core agent logic from the project root `src/` directory.

2.  **Endpoint Design & Conventions:**
    *   **RESTful Principles:** Strive for RESTful endpoint design.
    *   **Naming:** Use plural nouns for resource collections (e.g., `/agent/tasks`, `/notifications`).
    *   **Request/Response Models:** Define Pydantic models for all request bodies and response payloads. Keep frontend TypeScript types (`webApp/src/api/types.ts`) synchronized with backend Pydantic models where direct DTOs are involved.

3.  **Authentication & Authorization:**
    *   **JWT Validation:** Endpoints requiring authentication must validate the JWT token obtained by the frontend from Supabase Auth. Use FastAPI's dependency injection.
    *   **User Context:** Make the user's ID available to endpoint logic.
    *   **Authorization:** Implement checks to ensure the user has permission for the action.

4.  **Error Handling:**
    *   Return consistent JSON error responses (e.g., `{"detail": "Error message"}`).
    *   Use appropriate HTTP status codes.
    *   Implement FastAPI exception handlers.

5.  **Dependency Management:**
    *   Manage Python dependencies using `chatServer/requirements.txt`.
    *   Use virtual environments.

6.  **Logging:**
    *   Implement structured logging using Python's `logging` module.

7.  **Testing:**
    *   Write unit and integration tests for API endpoints using FastAPI's `TestClient`.
    *   Mock database interactions and external services.

8.  **Database Interaction (via `supabase-py` or similar):**
    *   If `chatServer` needs to interact directly with Supabase (e.g., for agent-initiated task creation):
        *   Initialize the Supabase Python client using appropriate service role keys (managed via environment variables).
        *   Perform database operations through this client.
        *   Be mindful of RLS; service roles typically bypass RLS unless policies specifically target them.

*   [Placeholder for more detailed API and Data guidance - to be populated and linked] 