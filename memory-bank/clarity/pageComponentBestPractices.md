# Page Component Best Practices

## Guiding Principles
The goal is to create React page components that are lean, focused on presentation, and delegate complex logic to custom hooks and state management solutions. This promotes maintainability, testability, and reusability.

## 1. Separation of Concerns
*   **Lean Pages:** Page components (`/pages/` or route components) should primarily be responsible for layout and composing UI components.
*   **Delegate Logic to Hooks:** Business logic, complex state transformations, and side effects (like API calls) should be encapsulated in custom React hooks (e.g., `useSpecificPageLogic`).
*   **UI Components:** Reusable UI elements should be in `src/components/ui/` or `src/components/features/` and receive data and handlers as props.

## 2. UI State Management Strategy
*   **`useState`:** Use for simple, local component state that doesn't need to be shared or persisted (e.g., toggle for a dropdown within a component, input field values before submission if not globally relevant).
*   **Zustand Stores:** Prefer Zustand for state that:
    *   Needs to be shared across multiple components without prop drilling.
    *   Represents global UI state (e.g., theme, open/closed state of a global modal, currently focused task ID if used by multiple disparate components).
    *   Requires more complex update logic that benefits from centralized actions.
    *   Refer to `memory-bank/clarity/zustandStoreDesign.md` for detailed Zustand guidelines.

## 3. Data Fetching & Caching
*   **Mandate React Query:** All server-state fetching, caching, and synchronization (e.g., API calls to Supabase) MUST be handled using React Query (`@tanstack/react-query`).
*   **Custom Hooks for Queries/Mutations:** Wrap React Query `useQuery` and `useMutation` calls in custom hooks (e.g., `useFetchTasks`, `useUpdateTask`) co-located with API function definitions (e.g., in `src/api/hooks/`). This centralizes query keys, configurations, and data transformation.
*   **No Direct API Calls in Components:** Page components or UI components should not directly make API calls. They should use the custom hooks provided by the API layer.

## 4. Derived State
*   **`useMemo`:** Use `useMemo` to compute derived data from props or state. This prevents unnecessary recalculations on re-renders.
    *   Example: Transforming a raw list of tasks from a store or API hook into view models (`TaskCardProps[]`) for rendering.

## 5. Minimize Logic in Render
*   The render function of a component should be as declarative as possible.
*   Avoid complex computations, transformations, or side effects directly within the JSX. Use helper functions, `useMemo`, or `useEffect` as appropriate.

## 6. `TodayView.tsx` - A Case for Further Refinement
*   While `TodayView.tsx` has been significantly improved by moving UI state to `useTaskViewStore`, it still contains a considerable amount of logic (e.g., `useMemo` for `displayTasks`, keyboard handlers, DND setup).
*   **Future Consideration:** Plan to further refactor `TodayView.tsx` by extracting more of its presentational logic and complex event handling into dedicated custom hooks (e.g., `useTodayViewDisplayLogic`, `useTodayViewKeyboardShortcuts`). This will make the `TodayView` component itself even leaner and more focused on composing its child elements. 