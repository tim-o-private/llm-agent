# Clarity UI Development Guide

## CRITICAL UI DEVELOPMENT RULES

*   **Plan-Driven Development:** Always consult `@ui-implementation-plan.md` (via `memory-bank/tasks.md`), `memory-bank/clarity/progress.md`, and `memory-bank/clarity/prd.md` to ensure your work aligns with current tasks, completed work, and overall feature requirements.
*   **Adhere to Patterns:** Strictly follow the architectural and implementation patterns. Do not introduce new patterns without discussion and approval. Refer to the "Detailed UI Guidance & Patterns" section below for links to specific pattern details.
*   **Overlay Management:** Use the `useOverlayStore` (Zustand) and a single `OverlayManager` component to manage the state (open/closed, data) of all modals, trays, and other overlays. Do NOT use local component state (e.g., `useState` for `isOpen`) for overlays.
*   **UI Component & Styling Strategy:** Use Radix UI Primitives (`@radix-ui/react-*`) for component behavior. Utilize `@radix-ui/themes` for its root `<Theme>` provider (manages CSS variables for colors, modes, etc.). Style primitives with Tailwind CSS, leveraging these theme variables. **AVOID** importing and using pre-styled components from `@radix-ui/themes` directly (e.g., `Button from \'@radix-ui/themes\'`). Do not use `@headlessui/react` or rely on `@radix-ui/colors` directly in components.
*   **Animation Strategy:** Prefer standard CSS transitions/animations (via Tailwind or CSS) for simplicity and performance, aligning with "low-stim" design. Avoid `framer-motion` unless CSS is insufficient for complex, justified animations. Do not implement complex or distracting animations.
*   **Application Layout:** Use only one main application shell component (e.g., `webApp/src/layouts/AppShell.tsx`) for consistent page structure. Do not create redundant layout components.
*   **Styling Encapsulation (Wrapper Components):** For common, repeated Tailwind CSS utility combinations that form a logical UI pattern (e.g., cards, specific input styles, panel containers), create dedicated, reusable wrapper components in `webApp/src/components/ui/`. This improves readability and maintainability. Avoid directly repeating extensive Tailwind class strings for the same logical element across multiple different components.
*   **Error Display:** Use a standardized, reusable component (e.g., `ErrorMessage.tsx` or similar, located in `webApp/src/components/ui/`) for all user-facing error messages. Display validation errors inline, next to the relevant form field. Show general application or API errors in a prominent, consistent global location (e.g., toast notification, banner). Do not show raw technical error messages to users.
*   **Loading Indication:** Clearly indicate loading states using visual indicators (spinners, skeleton loaders). Disable interactive elements (buttons, inputs) during related operations. Leverage React Query\'s `isLoading`/`isFetching` states for API-driven loading. Do not leave users uncertain if an action is processing.
*   **Form Management:** MANDATORY use of React Hook Form (`react-hook-form`) for handling form state, and Zod (`zod`) for schema definition and validation. Integrate Zod with React Hook Form using `@hookform/resolvers/zod`. Do not manage complex form state or validation manually.
*   **Accessibility (A11y):** MANDATORY adherence to accessibility best practices. Use semantic HTML. Ensure keyboard navigability and clear focus states. Provide sufficient color contrast. Use ARIA attributes appropriately when semantic HTML is insufficient. Test with screen readers. Radix UI Primitives provide a strong foundation for accessibility.

---

## Detailed UI Guidance & Patterns

**Note:** The main `implementationPatterns.md` document is undergoing refactoring. Key individual UI-related patterns are detailed and linked below. For any pattern not yet listed here, or for API/Data patterns, consult `implementationPatterns.md` (while it is being phased out) or `api-data-guide.md`.

### Core UI & Styling Patterns:
*   **P1: Centralized Overlay Management**
    *   **Summary:** Manage modals, trays, etc., using `useOverlayStore` and an `OverlayManager`.
    *   **Full Details & Example:** [./references/patterns/centralized-overlay-management.md](./references/patterns/centralized-overlay-management.md)
*   **P2: UI Component & Styling Strategy**
    *   **Summary:** Use Radix Primitives, `@radix-ui/themes` (for its `<Theme>` provider & CSS vars), and Tailwind CSS for styling. Avoid direct use of styled Radix Themes components.
    *   **Full Details & Example:** [./references/patterns/ui-component-strategy.md](./references/patterns/ui-component-strategy.md)
*   **P3: Animation Strategy**
    *   **Summary:** Prefer CSS animations for simplicity. Use `framer-motion` sparingly and only for complex, justified needs.
    *   **Full Details:** [./references/patterns/animation-strategy.md](./references/patterns/animation-strategy.md)
*   **P4: Consolidated Application Layout**
    *   **Summary:** Utilize a single main application shell component (e.g., `AppShell.tsx`).
    *   **Full Details:** [./references/patterns/consolidated-app-layout.md](./references/patterns/consolidated-app-layout.md)
*   **P6: Encapsulating Styling Patterns (Wrapper Components)**
    *   **Summary:** Create reusable wrapper components in `webApp/src/components/ui/` for common Tailwind CSS utility combinations.
    *   **Full Details & Example:** [./references/patterns/encapsulating-styling-patterns.md](./references/patterns/encapsulating-styling-patterns.md)
*   **P7: Consistent Error Display**
    *   **Summary:** Use a standardized, reusable component for clear and consistent error messages. Display validation errors inline and general errors globally.
    *   **Full Details & Example:** [./references/patterns/consistent-error-display.md](./references/patterns/consistent-error-display.md)
*   **P8: Consistent Loading Indication**
    *   **Summary:** Use visual indicators (spinners, skeletons) for loading. Disable interactive elements. Leverage React Query\'s `isLoading`/`isPending` states.
    *   **Full Details & Example:** [./references/patterns/consistent-loading-indication.md](./references/patterns/consistent-loading-indication.md)
*   **P9: Form Management (React Hook Form + Zod)**
    *   **Summary:** Use React Hook Form for state and Zod for schema/validation, integrated via `@hookform/resolvers/zod`.
    *   **Full Details & Example:** [./references/patterns/form-management.md](./references/patterns/form-management.md)
*   **P10: Accessibility (A11y) Best Practices**
    *   **Summary:** Adhere to A11y best practices: semantic HTML, keyboard navigation, focus states, color contrast, ARIA. Leverage Radix Primitives.
    *   **Full Details & Example:** [./references/patterns/accessibility-best-practices.md](./references/patterns/accessibility-best-practices.md)

### Other Key UI Documents:
*   `memory-bank/clarity/uiComponents.md` (Shared UI component details)
*   `memory-bank/clarity/uiPages.md` (Page structures and UI states)
*   `memory-bank/clarity/style-guide.md` (Visual styling - to be merged here or into references)
*   `memory-bank/clarity/interactionModel.md` (User interaction principles)
*   `memory-bank/clarity/designBrief.md` (Aesthetic guidelines)

### Key `webApp` Directory Structure
*   Adhere strictly to the established project directory layout for the `webApp`:
    *   `webApp/src/components/ui/`: Shared, reusable UI components (Radix Primitives styled with Tailwind, wrapper components).
    *   `webApp/src/components/{feature}/`: Feature-specific UI components.
    *   `webApp/src/hooks/`: Custom React hooks (non-API related general UI logic).
    *   `webApp/src/api/hooks/`: Custom React Query hooks for all frontend API interactions (to Supabase or `chatServer`).
    *   `webApp/src/api/types.ts`: Frontend TypeScript type definitions for API data.
    *   `webApp/src/stores/`: Zustand stores for global/shared UI state.
    *   `webApp/src/pages/`: Components representing application pages/routes.
    *   `webApp/src/layouts/`: Components defining overall page structure (e.g., `AppShell.tsx`).

---

## General Component Best Practices (Frontend - `webApp`)

*   **Lean Pages & Components:** Page components (`webApp/src/pages/`) and feature components (`webApp/src/components/{feature}/`) should primarily be responsible for layout and composing UI elements. Keep them focused on presentation.
*   **Delegate Logic to Hooks:** Encapsulate business logic, complex state transformations, and side effects (excluding direct API calls, which are handled by React Query hooks) in custom React hooks (e.g., `useSpecificPageLogic.ts` placed in `webApp/src/hooks/` or co-located with feature components if highly specific).
*   **Reusable UI Components:** Place general-purpose, reusable UI elements in `webApp/src/components/ui/`. These should receive data and event handlers via props.
*   **Derived State (`useMemo`):** Utilize `useMemo` to compute derived data from props or state. This is crucial for performance as it prevents unnecessary recalculations on re-renders (e.g., transforming a list of items from a store into view models before passing to a list component).
*   **Minimize Logic in Render:** The render function (JSX) of a component should be as declarative as possible. Avoid complex computations, transformations, or side effects directly within the JSX. Extract these into event handlers, effects, or memoized values.

---

## Keyboard Shortcut Implementation

*   **Implementation:** Use `useEffect` hooks with proper cleanup for `keydown` event listeners. Always check for active inputs/modals to prevent interference. Use `event.preventDefault()` as needed.
*   **State Interaction:** Modify state via Zustand store actions for shared state, or local state setters for component-specific changes.
*   **Consistency & Discoverability:** Strive for consistent key usage and ensure clear focus indication. Refer to the detailed guide for comprehensive best practices and examples.
*   **Full Details & Examples:** [./references/guides/keyboard-shortcut-guide.md](./references/guides/keyboard-shortcut-guide.md) 