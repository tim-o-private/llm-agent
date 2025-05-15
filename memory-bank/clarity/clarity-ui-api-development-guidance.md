# Cursor Rule: clarity-ui-api-development-guidance

## Description

Provides comprehensive guidance for developing UI and API features for the Clarity project. This rule ensures adherence to established architectural patterns, component strategies, data handling, security measures, documentation practices, and the overall project plan. It is essential for maintaining consistency, quality, and efficiency in development.

---

## I. Foundational Principle: Plan-Driven Development

1.  **Primary Task Guidance:**
    *   Always consult **`@ui-implementation-plan.md`** as the authoritative source for current development tasks, detailed steps for ongoing phases (like Phase 0.4, Phase 0.5, etc.), and planned refactoring efforts.
    *   Verify completed work and the current development focus by checking **`memory-bank/clarity/progress.md`**.
2.  **Feature Requirements:**
    *   All UI and API development must align with the feature requirements, user stories, and project goals defined in **`memory-bank/clarity/prd.md`**.

---

## II. Adherence to Implementation Patterns

Strictly follow the architectural and implementation patterns defined in **`memory-bank/clarity/implementationPatterns.md`**. Key patterns include:

1.  **Pattern 1: Centralized Overlay State Management**
    *   **Goal:** Manage modals, trays, etc., consistently using `useOverlayStore` and an `OverlayManager`.
2.  **Pattern 2: UI Component Strategy: Radix UI Primitives + Tailwind CSS**
    *   **Goal:** Use `@radix-ui/react-*` primitives for behavior, styled with Tailwind CSS. Avoid Headless UI for new components and do not use `@radix-ui/themes` or `@radix-ui/colors`.
3.  **Pattern 3: Re-evaluated Animation Strategy**
    *   **Goal:** Prefer CSS transitions/animations for simplicity and performance, aligning with "low-stim" design. Avoid `framer-motion` unless CSS is insufficient for complex, justified animations.
4.  **Pattern 4: Consolidated Application Layout**
    *   **Goal:** Utilize a single, definitive main application layout component (e.g., `AppShell.tsx`).
5.  **Pattern 5: Centralized API Interaction with React Query**
    *   **Goal:** Encapsulate all Supabase (or other backend) interactions within custom React Query hooks (`@tanstack/react-query`) located in `@/api/hooks/`. For direct interaction with Supabase from frontend React Query hooks (as seen in `useTaskHooks.ts`), ensure RLS (Pattern 11) is robustly implemented. The `chatServer/` backend should then be utilized for more complex business logic, data aggregation, or when a server-side intermediary is explicitly needed.
6.  **Pattern 6: Encapsulating Styling Patterns with Wrapper Components**
    *   **Goal:** Create reusable wrapper components in `@/components/ui/` to encapsulate common Tailwind CSS utility combinations, improving readability and maintainability.
7.  **Pattern 7: Consistent Error Display**
    *   **Goal:** Use a standardized, reusable component (e.g., `ErrorMessage.tsx`) for clear and consistent error presentation.
8.  **Pattern 8: Consistent Loading Indication**
    *   **Goal:** Provide clear feedback for loading states using spinners, skeleton loaders, and React Query's `isLoading`/`isFetching` states. Disable interactive elements during operations.
9.  **Pattern 9: Form Management**
    *   **Goal:** Use React Hook Form and Zod for structured form handling, validation, and submission logic.
10. **Pattern 10: Accessibility Best Practices**
    *   **Goal:** Ensure UI is accessible (semantic HTML, ARIA, keyboard navigation, screen reader compatibility, color contrast).
11. **Pattern 11: Standardized DDL & Row Level Security (RLS) for Data Access**
    *   **Goal:** Maintain a central DDL source of truth in `memory-bank/clarity/ddl.sql`. Implement consistent RLS in Supabase using a reusable SQL helper function (`public.is_record_owner`) and database migrations.
    *   **Reference:** For detailed RLS implementation, consult **`memory-bank/clarity/supabaseRLSGuide.md`**.

---

## III. Consult Clarity Project Documentation (`memory-bank/clarity/`)

Before and during development, refer to these documents for context and specifications:

*   **`uiComponents.md`**: For definitions, descriptions, and usage guidelines of shared/reusable UI components (e.g., `TaskCard`, `Modal`, `Checkbox`).
*   **`uiPages.md`**: For page structures, intended routes, key components per page, and UI states (modals/overlays).
*   **`componentDefinitions.md`**: For underlying data models, object structures, and type definitions relevant to UI and API interactions.
*   **`ddl.sql`**: As the definitive source for the current database schema.
*   **`prd.md`**: For overall product vision, user stories, and detailed feature specifications.
*   **Supplementary Context:**
    *   `interactionModel.md`: For guiding principles on user interactions.
    *   `coreUserJourney.md`: To understand primary user flows.
    *   `designBrief.md`: For aesthetic and design guidelines.
    *   `featureRoadmap.md`: For a high-level overview of planned features.

---

## IV. Development Workflow & Code Generation

(Derived from `@project-structure.md` and project conventions)

1.  **Directory Structure (Post-Refactor to `webApp` and `chatServer`):**
    *   Adhere strictly to the established project directory layout.
    *   **`webApp/src/components/ui/`**: Shared UI components. (Note: can be referenced as `@/components/ui/`)
    *   **`webApp/src/components/` (feature subdirs)**: Feature-specific UI components.
    *   **`webApp/src/hooks/`**: Custom React hooks. (Note: can be referenced as `@/hooks/`)
    *   **`webApp/src/api/hooks/`**: React Query hooks for frontend API interactions (to Supabase direct or to `chatServer`). (Note: can be referenced as `@/api/hooks/`)
    *   **`webApp/src/api/types.ts`**: Frontend TypeScript type definitions. (Note: can be referenced as `@/api/types.ts`)
    *   **`chatServer/`**: Backend Python code. `main.py` is the entry point. Future organization may include subdirectories like `routers/`, `services/`, `models/` directly within `chatServer/`.
2.  **Code Quality:**
    *   All new TypeScript/React and Python code should include clear type definitions/hints and docstrings where appropriate.
    *   Ensure components are functional, with props clearly defined.
3.  **Testing:**
    *   Write tests for new functionalities or significant refactors as outlined in the **`@ui-implementation-plan.md`**.

---

## V. Documentation & Post-Development Updates

(Derived from `@project-structure.md`)

1.  **Workflow:** Follow the established documentation flow: Backlog -> PRD -> Implementation Plan -> Develop (Branch, Commits, PR) -> Deliver -> Update Documentation.
2.  **Key Documents to Update After Delivery/Refactor:**
    *   **`memory-bank/clarity/prd.md`**: Update feature status and details.
    *   **`memory-bank/clarity/progress.md`**: Log completed tasks.
    *   **`webApp/README.md`** (post-refactor): Update if UI components or usage instructions change.
    *   **`chatServer/README.md`** (post-refactor): Document setup, endpoints, and operation.
    *   **`memory-bank/clarity/uiComponents.md` / `uiPages.md`**: Reflect any changes to component definitions, page structures, or UI states.
    *   **`memory-bank/clarity/implementationPatterns.md`**: Update or add patterns if new conventions are established or existing ones refined.
    *   **`memory-bank/clarity/ddl.sql`**: Ensure it reflects the current state of the database schema after any migrations.
3.  **Database Changes:** All DDL changes, including RLS policies and helper functions, MUST be managed via Supabase migration scripts.

---

## VI. Backend API (FastAPI) Development Guidelines (`chatServer/` post-refactor)

This section provides specific guidance for developing and maintaining the FastAPI backend application, which resides in `chatServer/`.

1.  **Project Structure (`chatServer/`):**
    *   `main.py`: Located in `chatServer/main.py`. FastAPI application instantiation, middleware, and global configurations.
    *   `routers/` (or `endpoints/`): Future directory within `chatServer/` for API routers. Each router should group related endpoints (e.g., `chat_router.py`, `agent_actions_router.py`).
    *   `services/`: Future directory within `chatServer/` for the business logic layer.
    *   `models/` (or `schemas/`): Future directory within `chatServer/` for Pydantic models.
    *   `db/` (or `database/`): Future directory within `chatServer/` for database client setup (e.g., Supabase client initialization for Python).
    *   `core/`: Future directory within `chatServer/` for core configurations, settings loading for the server (if split from `main.py`).
    *   `utils/`: Future directory within `chatServer/` for utility functions specific to the backend.
    *   Reference `LLM_AGENT_SRC_PATH` for integrating core agent logic from the project root `src/` directory.

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