# Core Instructions for AI Agents on the Clarity Project

*You are an AI assistant working on the Clarity project. Your role may vary (UI development, backend logic, general tasks). Adherence to established project structures, plans, and specialized guidelines is critical. Before proceeding with any task, confirm you have read and understood these core instructions and any specialized instructions relevant to your current task.*

## I. Foundational Principles & Project Context

1.  **Plan-Driven Development:**
    *   Always consult active project plans (`@ui-implementation-plan.md` or other relevant task-specific plans), `memory-bank/clarity/prd.md` (Product Requirements), and `memory-bank/clarity/progress.md` for task context, goals, and overall feature requirements.
2.  **Project Overview & Structure:**
    *   For a high-level understanding of the project, its architecture (monorepo: `webApp/`, `chatServer/`, `src/`), and links to key documentation, refer to **`memory-bank/clarity/project-overview.md`**.
3.  **Approval Required for Major Deviations:**
    *   Any new design patterns (not covered in existing guides), introduction of new libraries/dependencies, or significant deviations from established practices MUST be discussed and receive explicit approval *before* implementation.
4.  **Documentation Updates:**
    *   After implementing features or making significant changes, ensure all relevant project documentation (e.g., `prd.md`, `progress.md`, READMEs, relevant guides) is considered for updates as outlined in `memory-bank/clarity/project-overview.md`.

## II. Specialized Task Guidance

*   **For UI Development (working within `webApp/`):**
    *   Your primary instruction set is **`memory-bank/clarity/agent-ui-dev-instructions.md`**. This guide contains specific rules for UI development, component strategies, state management, styling, and links to detailed UI patterns and best practices in `memory-bank/clarity/ui-guide.md`.
*   **For Backend Development (`chatServer/`) or Core Agent Logic (`src/`):
    *   Your primary reference for API design, data management, database interaction (including DDL/RLS principles), and FastAPI backend guidelines is **`memory-bank/clarity/api-data-guide.md`**.
    *   This guide also links to detailed patterns for API interaction, data handling, and relevant diagrams.
*   **General Pattern Index:**
    *   `memory-bank/clarity/implementationPatterns.md` serves as a master index for all documented architectural and implementation patterns, linking to their detailed explanations in `memory-bank/clarity/references/patterns/`.

## III. General Code Quality & Testing (All Areas)

*   **Code Quality:**
    *   All new TypeScript/React and Python code MUST include clear type definitions/hints and appropriate JSDoc (for TS/React) or docstrings (for Python) for functions, classes, and complex logic.
    *   Code should be clean, readable, maintainable, and adhere to the specific styling and architectural guidelines for its respective area (`webApp/`, `chatServer/`, `src/`).
*   **Testing:**
    *   Write unit and integration tests for new functionalities or significant refactors as outlined in task-specific plans (e.g., `@ui-implementation-plan.md`) or `memory-bank/tasks.md`.
    *   For backend API endpoints, use FastAPI's `TestClient` and mock database interactions/external services as detailed in `api-data-guide.md`.

## IV. Database Interaction & Schema

*   While detailed database management is covered in `api-data-guide.md`:
    *   All agents should be aware that Data Definition Language (DDL) changes (table creation, alterations, RLS policies) MUST be managed via Supabase migration scripts (`supabase/migrations/`).
    *   `memory-bank/clarity/ddl.sql` is a reference snapshot of the schema.
    *   Row Level Security (RLS) is critical for data access. Frontend agents consume data protected by RLS via React Query hooks.

## V. Agent Operational Protocol (Universal)

*   **Acknowledge Instructions:** Before starting any new major task or if instructions have been updated, confirm you have read and understood these core instructions and any specialized instructions relevant to your task.
*   **Full File Context Review:** Before proposing any code changes, new files, or significant architectural decisions, you MUST explicitly state that you have read and fully understood the entirety of all relevant, currently open, and attached files pertinent to your task.
*   **Methodical Troubleshooting:**
    *   Address ONLY ONE problem or issue at a time.
    *   Clearly state your hypothesis regarding the cause of a problem.
    *   Verify your hypothesis (e.g., through logging, targeted checks, or stepping through logic) BEFORE implementing a potential solution. Isolate variables to confirm the cause-effect relationship.

*This document provides core, high-level instructions. Always consult the specialized guides (`agent-ui-dev-instructions.md`, `api-data-guide.md`, `ui-guide.md`, etc.) and the `project-overview.md` for detailed context and procedures relevant to your specific area of work.* 