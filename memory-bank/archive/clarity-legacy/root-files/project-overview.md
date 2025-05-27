# Clarity Project Overview

## Project Vision & Goals

*   [Placeholder for project vision and goals - to be populated]

---

## Core Development Principles

### Plan-Driven Development

1.  **Primary Task Guidance:**
    *   Always consult **`@ui-implementation-plan.md`** (often referred to via `memory-bank/tasks.md`) as the authoritative source for current development tasks, detailed steps for ongoing phases, and planned refactoring efforts.
    *   Verify completed work and the current development focus by checking **`memory-bank/clarity/progress.md`**.
2.  **Feature Requirements:**
    *   All UI and API development must align with the feature requirements, user stories, and project goals defined in **`memory-bank/clarity/prd.md`**.
3.  **Architectural Adherence:**
    *   Strictly follow the overall **Monorepo Structure and Component Architecture** as defined. This includes the separation of concerns between `webApp/`, `chatServer/`, and `src/`, and their prescribed interaction flows. For full details, see the [Monorepo and Component Architecture Pattern](./references/patterns/monorepo-component-architecture.md).

---

## Core Architectural Components

*   The project is structured as a monorepo with distinct frontend (`webApp/`), backend (`chatServer/`), and core logic (`src/`) components. For a detailed breakdown of this structure, interaction flows, and key architectural decisions, refer to:
    *   **Pattern 13: Monorepo Structure and Component Architecture:** [Full Details](./references/patterns/monorepo-component-architecture.md)

### Key Directory Structures

*   **`webApp/`**: Frontend React/TypeScript application.
    *   `webApp/src/components/ui/`: Shared, reusable UI components.
    *   `webApp/src/components/{feature}/`: Feature-specific UI components.
    *   `webApp/src/hooks/`: Custom React hooks (non-API related).
    *   `webApp/src/api/hooks/`: Custom React Query hooks for API interactions.
    *   `webApp/src/api/types.ts`: Frontend TypeScript type definitions.
    *   `webApp/src/stores/`: Zustand global state stores.
    *   `webApp/src/pages/`: Page components.
    *   `webApp/src/layouts/`: Layout components (e.g., `AppShell.tsx`).
*   **`chatServer/`**: Backend Python FastAPI application.
    *   `chatServer/main.py`: Main application entry point.
    *   (Future directories: `routers/`, `services/`, `models/` for organization).
*   **`src/`**: Core Python LLM agent framework logic.
*   **`memory-bank/`**: Project memory, documentation, and agent configurations.
    *   `memory-bank/clarity/`: Specific documentation for the Clarity project.
*   **`supabase/migrations/`**: Database schema migrations.

---

## Key Documentation Links & Reference Points

This section provides links to essential project documentation. Specific guides will contain more focused critical rules and detailed explanations.

**Core Guides (Contain Critical Rules):**
*   **Core Agent Instructions:** [./agent-core-instructions.md](./agent-core-instructions.md) - *General rules for AI agent operation.*
*   **UI Development Guide:** [./ui-guide.md](./ui-guide.md) - *Critical rules and detailed guidance for frontend UI development.*
*   **API & Data Management Guide:** [./api-data-guide.md](./api-data-guide.md) - *Critical rules and detailed guidance for backend API and data layer development.*

**Project Management & Planning:**
*   **Tasks & Roadmap:** [../tasks.md](../tasks.md) - *Current development tasks, backlog, and high-level roadmap.*
*   **Project Brief & Product Requirements (PRD):** `memory-bank/clarity/prd.md` - *Overall product vision, user stories, and detailed feature specifications.*
*   **Progress Tracking:** `memory-bank/clarity/progress.md` - *Log of completed tasks and current development focus.*
*   **Feature Roadmap (High-Level):** `memory-bank/clarity/featureRoadmap.md`

**Technical & Design Specifications:**
*   `memory-bank/clarity/implementationPatterns.md` - *Definitive source for architectural and implementation patterns.*
*   Frontend TypeScript data types are defined in `webApp/src/api/types.ts`.
*   Backend Pydantic data models are defined in `chatServer/models/` (or `chatServer/schemas/`).
*   `memory-bank/clarity/ddl.sql` - *Definitive source for the current database schema.*
*   **UI Component Library Info:** `memory-bank/clarity/uiComponents.md` - *Definitions and usage for shared/reusable UI components.*
*   **UI Page Structures:** `memory-bank/clarity/uiPages.md` - *Page structures, routes, key components per page, and UI states.*
*   **Style Guide:** `memory-bank/clarity/style-guide.md` (Details to be merged into `ui-guide.md` or `references/`)

**User Experience & Design:**
*   **Interaction Model:** `memory-bank/clarity/interactionModel.md` - *Guiding principles on user interactions.*
*   **Core User Journey:** `memory-bank/clarity/coreUserJourney.md` - *Primary user flows.*
*   **Design Brief:** `memory-bank/clarity/designBrief.md` - *Aesthetic and design guidelines.*

**Reference Materials Folder:**
*   **All Other Detailed Examples, Diagrams, Specific Guides:** [./references/](./references/) - *Contains subfolders for diagrams, code examples, and specific how-to guides.*

---

## Documentation Practices & Workflow

1.  **Standard Workflow:** Follow the established documentation and development flow: Backlog -> PRD (`memory-bank/clarity/prd.md`) -> Implementation Plan (`memory-bank/tasks.md`) -> Develop (Branch, Commits, PR) -> Deliver -> Update Documentation.
2.  **Key Documents to Update After Delivery/Refactor:**
    *   `memory-bank/clarity/prd.md`: Update feature status and details.
    *   `memory-bank/clarity/progress.md`: Log completed tasks.
    *   `webApp/README.md`: Update if UI components or usage instructions change significantly.
    *   `chatServer/README.md`: Document setup, new endpoints, and operational changes.
    *   Relevant UI/API Guides (`ui-guide.md`, `api-data-guide.md`): Update if critical rules or core guidance changes.
    *   `memory-bank/clarity/implementationPatterns.md`: Update or add patterns if new conventions are established or existing ones refined. Examples of new patterns should go into `memory-bank/clarity/references/patterns/`.
    *   `memory-bank/clarity/ddl.sql`: Ensure it reflects the current state of the database schema after any migrations.
    *   Consider updates to `memory-bank/clarity/uiComponents.md` or `memory-bank/clarity/uiPages.md` if those documents are actively maintained and changes are significant.
3.  **Database Schema Changes:** All DDL changes, including RLS policies and helper functions, MUST be managed via Supabase migration scripts (`supabase/migrations/`). 