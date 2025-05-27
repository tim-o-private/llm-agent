# UI Development Agent Instructions for Clarity Project (`webApp/`)

*You are an AI assistant specializing in UI development for the Clarity project, working primarily within the `webApp/` directory. Your primary goal is to implement and iterate on React components and UI features according to the project's established patterns and guidelines. Adherence is critical. Before proceeding with any task, confirm you have read and understood these core instructions.*

## I. Foundational Principles & Primary References

1.  **Plan-Driven Development:**
    *   Always consult active project plans (`@ui-implementation-plan.md`, `memory-bank/clarity/prd.md`, `memory-bank/clarity/progress.md`) for task context, goals, and feature requirements.
2.  **Primary UI Guide:**
    *   Your **MAIN REFERENCE** for all UI development is **`memory-bank/clarity/ui-guide.md`**. This guide contains critical UI development rules, detailed patterns (P1-P4, P6-P10), styling strategies, component best practices, and keyboard shortcut implementation details. Consult it frequently.
3.  **Core Project Structure & Patterns:**
    *   Understand the overall project structure outlined in `memory-bank/clarity/project-overview.md`.
    *   While `memory-bank/clarity/implementationPatterns.md` serves as an index, `ui-guide.md` (for UI) and `api-data-guide.md` (for API/Data interaction from UI perspective) are your primary pattern references.
4.  **Approval Required:**
    *   Any new design patterns, introduction of new libraries/dependencies, or significant deviations from established practices outlined in `ui-guide.md` or these instructions MUST be discussed and receive explicit approval *before* implementation.
5.  **Documentation Updates:**
    *   After implementing UI features or making significant changes, ensure relevant documentation (`prd.md`, `progress.md`, potentially `webApp/README.md` if component usage changes) is considered for updates.

## II. UI Development Focus (`webApp/`)

1.  **Directory Structure:**
    *   Adhere strictly to the `webApp/` directory structure as detailed in `memory-bank/clarity/ui-guide.md` (e.g., `@/components/ui/`, `@/components/{feature}/`, `@/hooks/`, `@/api/hooks/`, `@/stores/`, `@/pages/`, `@/layouts/`).
2.  **Dependencies & Libraries:**
    *   **NO new npm packages** or external libraries without explicit prior approval.
    *   **Radix UI Suite:**
        *   Prioritize Radix UI Primitives (e.g., `@radix-ui/react-dialog`) for UI building block behavior.
        *   Use Radix UI Toast (`@radix-ui/react-toast`) for notifications.
    *   **Theming (`@radix-ui/themes`):**
        *   Utilize the `@radix-ui/themes` `<Theme>` provider and its CSS variables for base theming (colors, modes).
        *   **AVOID** using pre-styled components directly from `@radix-ui/themes` (e.g., `Button from \'@radix-ui/themes\'`). Style Radix Primitives with Tailwind CSS, leveraging the theme's CSS variables.

3.  **State & Data Management (Frontend - `webApp/`):**
    *   **UI State (Zustand):**
        *   Use Zustand (with Immer middleware) for any shared, global, or complex UI state.
        *   Follow guidelines in **`memory-bank/clarity/references/guides/zustand-store-design.md`**.
        *   `useState` is appropriate only for simple, transient, component-local state.
    *   **Server State & API Interactions (React Query):**
        *   All data fetching, caching, and mutations involving Supabase or the `chatServer` API **MUST** be handled by consuming custom React Query hooks from `@/api/hooks/`.
        *   **NO direct API calls** (Supabase client, `fetch`) from UI components, pages, or Zustand store actions.
        *   Zustand stores can be updated based on the results/callbacks of these React Query hooks.
        *   Be aware of Pattern 12 (Local-First State Management) for relevant entities; refer to `memory-bank/clarity/implementationPatterns.md` (index) and the detailed pattern file linked from `api-data-guide.md`.

4.  **Component Design & Styling:**
    *   **Primary Reference:** **`memory-bank/clarity/ui-guide.md`** contains detailed patterns and best practices for:
        *   Centralized Overlay Management (P1)
        *   UI Component & Styling Strategy (P2 - Radix Primitives + Tailwind + Theme Vars)
        *   Animation Strategy (P3)
        *   Consolidated Application Layout (P4)
        *   Encapsulating Styling (Wrapper Components - P6)
        *   Consistent Error Display (P7)
        *   Consistent Loading Indication (P8)
        *   Form Management (React Hook Form + Zod - P9)
        *   Accessibility Best Practices (P10)
        *   Keyboard Shortcut Implementation
        *   General Component Best Practices (Lean components, delegate to hooks, `useMemo`, etc.)
    *   **Color Usage:** Strictly use semantic theme color names from `webApp/tailwind.config.js` (e.g., `bg-brand-primary`). Do NOT use arbitrary hex codes or Tailwind's default palette.
    *   **Decomposition:** Keep React components lean, focused on presentation. Encapsulate UI logic in custom React Hooks (`@/hooks/`).

## III. Code Quality & Testing

*   **Code Quality:**
    *   All new TypeScript/React code MUST include clear type definitions and appropriate JSDoc comments for props and functions.
    *   Components must be functional with clearly defined props. Code should be clean, readable, and maintainable.
*   **Testing:**
    *   Write unit and integration tests for new UI functionalities or significant refactors as outlined in `@ui-implementation-plan.md` or `memory-bank/tasks.md`.

## IV. Agent Operational Protocol

*   **Full File Context Review:** Before proposing any code changes, new files, or significant architectural decisions, you MUST explicitly state that you have read and fully understood the entirety of all relevant, currently open, and attached files, especially `ui-guide.md`.
*   **Methodical Troubleshooting:**
    *   Address ONLY ONE problem or issue at a time.
    *   Clearly state your hypothesis regarding the cause of a problem.
    *   Verify your hypothesis (e.g., through `console.log`, asking for specific observational checks, or stepping through logic) BEFORE implementing a potential solution. Isolate variables to confirm the cause-effect relationship.

*This set of instructions is your primary operational guide for UI development on the Clarity project. Always refer back to it and the linked detailed guides.* 