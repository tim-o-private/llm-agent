# Core Instructions for AI Agent on the Clarity Project

*You are an AI assistant working on the Clarity project. Adherence to established patterns and guidelines is critical. Before proceeding with any task, confirm you have read and understood these core instructions by replying with "ACKNOWLEDGED. I have read and understood these core instructions."*

1.  **Foundation & Planning:**
    *   Always consult active project plans (`@ui-implementation-plan.md`, `memory-bank/clarity/prd.md`, `memory-bank/clarity/progress.md`) for task context and goals.
    *   Strictly follow established patterns documented in `memory-bank/clarity/implementationPatterns.md` and best practices in `memory-bank/clarity/pageComponentBestPractices.md`.
    *   **Approval Required:** Any new design patterns, introduction of new libraries/dependencies, or significant deviations from established practices MUST be discussed and receive explicit approval *before* implementation.
    *   After implementing features or making significant changes, ensure all relevant documentation (e.g., PRDs, progress files, pattern documents, component definitions) is updated accordingly.

2.  **Dependencies & Libraries:**
    *   **NO new dependencies** (npm packages, external libraries) shall be introduced without explicit prior approval.
    *   **Radix UI Suite First:**
        *   For UI building blocks, prioritize using Radix UI Primitives (e.g., `@radix-ui/react-dialog`, `@radix-ui/react-dropdown-menu`) for behavior.
        *   For common UI elements like Toast notifications, use the corresponding Radix component (e.g., `@radix-ui/react-toast`) *before* considering or introducing any third-party alternatives. If a Radix component is deemed unsuitable for a specific, justified reason, an alternative requires explicit approval.
    *   **Theming with `@radix-ui/themes`:**
        *   The project utilizes the `@radix-ui/themes` library for its `<Theme>` provider and the CSS variables it exposes for base theming (colors, light/dark modes, accent colors).
        *   However, **AVOID using pre-styled components directly from the `@radix-ui/themes` package** (e.g., do NOT `import { Button } from '@radix-ui/themes';`). Instead, style Radix UI Primitives with Tailwind CSS, leveraging the theme's CSS variables.

3.  **State & Data Management (Frontend - `webApp`):**
    *   **UI State:** Use Zustand (with Immer middleware) for any shared, global, or complex UI state. Refer to `memory-bank/clarity/references/guides/zustand-store-design.md` for specific guidelines. `useState` is appropriate only for simple, transient, component-local state.
    *   **Server State & API Interactions:** It is MANDATORY to use React Query (`@tanstack/react-query`) for all data fetching, caching, and mutation operations involving Supabase or the `chatServer` API.
    *   All API calls (i.e., Supabase client interactions, `fetch` calls to `chatServer`) MUST be encapsulated within custom React Query hooks located in `@/api/hooks/`.
    *   **NO direct API calls from UI components, pages, or Zustand store actions.** Zustand stores can be updated based on the results/callbacks of React Query hooks.
    *   Where applicable, follow Pattern 12 (Local-First State Management with Eventual Sync) as detailed in `memory-bank/clarity/implementationPatterns.md`.

4.  **Component Design & Styling (Frontend - `webApp`):**
    *   **Decomposition:** Keep React components lean and primarily focused on presentation. Business logic, complex state transformations, and side effects should be encapsulated in custom React Hooks.
    *   **Styling Approach:** Style Radix UI Primitives using Tailwind CSS utility classes.
    *   **Color Usage:** ALL colors MUST be applied using the pre-defined semantic theme color names available in `webApp/tailwind.config.js` (e.g., `bg-brand-primary`, `text-text-secondary`, `border-ui-border`). These theme colors are configured to map to the Radix Theme CSS variables. Do NOT use arbitrary hex codes or Tailwind's default color palette directly in components.
    *   Utilize and create reusable wrapper components (as per Pattern 6 in `implementationPatterns.md`) in `@/components/ui/` to encapsulate common styling patterns and ensure consistency.
    *   Adhere to established patterns for error display (Pattern 7), loading indications (Pattern 8), form management (Pattern 9 using React Hook Form + Zod), and accessibility (Pattern 10).

5.  **Backend Development (`chatServer`):**
    *   When developing FastAPI endpoints, adhere to the guidelines outlined in `memory-bank/clarity/clarity-ui-api-development-guidance.md` (Section VI).
    *   The `chatServer` should leverage the core agent logic and utilities from the `src/` directory.

6.  **Code Quality, Testing & Database Management:**
    *   **Code Quality:** All new TypeScript/React and Python code must include clear type definitions/hints and appropriate docstrings. Ensure components are functional with clearly defined props. Code should be clean, readable, and maintainable.
    *   **Testing:** Write unit and integration tests for new functionalities or significant refactors as outlined in `@ui-implementation-plan.md` or `memory-bank/tasks.md`. For backend API endpoints, use FastAPI's `TestClient` and mock database interactions/external services.
    *   **Database Changes:** All Data Definition Language (DDL) changes, including those for Row Level Security (RLS), MUST be managed via Supabase migration scripts. Ensure `memory-bank/clarity/ddl.sql` is updated to reflect the current schema, and follow the RLS implementation guide in `memory-bank/clarity/references/guides/supabaseRLSGuide.md`.

7.  **Agent Operational Protocol:**
    *   **Full File Context Review:** Before proposing any code changes, new files, or significant architectural decisions, you MUST explicitly state that you have read and fully understood the entirety of all relevant, currently open, and attached files.
    *   **Methodical Troubleshooting:**
        *   Address ONLY ONE problem or issue at a time.
        *   Clearly state your hypothesis regarding the cause of a problem.
        *   Verify your hypothesis (e.g., through `console.log` statements, asking for specific observational checks, or by stepping through logic) BEFORE implementing a potential solution. Isolate variables to confirm the cause-effect relationship. 