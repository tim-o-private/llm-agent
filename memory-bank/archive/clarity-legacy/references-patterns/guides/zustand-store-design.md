# Zustand Store Design Guidelines

## Guiding Principles
Zustand stores should be well-scoped, manage a cohesive slice of application state, and provide clear actions for state modification. This ensures predictability, testability, and prevents stores from becoming overly complex.

## 1. Scope & Granularity
*   **Cohesive State:** Each store should manage a specific domain or feature's state (e.g., `useTaskViewStore` for UI state related to the task view, `useAuthStore` for authentication state, `useThemeStore` for theming).
*   **Avoid Monolithic Stores:** Do not create a single global store for all application state. Break down state into logical, smaller stores.

## 2. State Structure
*   **Normalized Data (When Applicable):** For collections of items (e.g., tasks, users), consider a normalized structure (e.g., an object `{ [id: string]: ItemType }` and an array of IDs `string[]`) if it simplifies updates and lookups. However, for simpler lists, a direct array `ItemType[]` is acceptable.
*   **`Set` and `Map` for Collections:** When dealing with collections where uniqueness or fast lookups by key are important (e.g., `selectedTaskIds`), use JavaScript `Set` or `Map` objects. Remember to call `enableMapSet()` from `immer` at the application's entry point (e.g., `main.tsx`) to ensure Immer can correctly handle these data structures.
    *   Example from `useTaskViewStore`: `selectedTaskIds: new Set<string>()`

## 3. Actions
*   **Clear and Specific:** Actions should have clear, descriptive names that indicate their purpose (e.g., `setFocusedTaskId`, `toggleSelectedTask`, `openDetailModal`).
*   **Only Way to Modify State:** Components should *never* directly mutate store state. All state changes MUST go through actions defined in the store.
*   **Payloads:** Actions can accept payloads to provide necessary data for state updates.

## 4. Immutability
*   **Immer Middleware:** Always use the `immer` middleware (`zustand/middleware/immer`). This allows you to write state update logic in a mutable style within your actions, while Immer handles the complexities of producing a new immutable state tree.
    *   Example: `set(state => { state.focusedTaskId = newId; })`

## 5. Selectors
*   **Granular Subscriptions:** Encourage the use of selectors to subscribe to specific pieces of state. This prevents components from re-rendering unnecessarily when unrelated parts of the store's state change.
    *   Example: `const focusedTaskId = useTaskViewStore(state => state.focusedTaskId);`
*   **Memoized Selectors (Rarely Needed with Zustand):** Zustand's default shallow equality check for selector results is often sufficient. For complex computations based on store state, `useMemo` in the component is usually preferred over creating memoized selectors directly in the store, unless the computation is very expensive and used in many places.

## 6. API Calls & Side Effects
*   **No API Calls Directly in Stores:** Zustand stores are primarily for client-side UI state management. API calls and other asynchronous side effects should be handled by React Query hooks.
*   **Updating Store After API Calls:** After a successful API call (e.g., fetching tasks, updating a task), the React Query hook (or the component using it) can then call a store action to update the relevant client-side UI state.
    *   Example: `useFetchTasks` hook fetches tasks; its `onSuccess` callback calls `useTaskViewStore.getState().setRawTasks(fetchedTasks)`. 

## 7. Middleware
*   **`devtools`:** Always include `devtools` middleware during development to enable debugging with Redux DevTools.
*   **`persist` (Use Judiciously):** Use `persist` middleware if a store's state needs to be persisted to `localStorage` (e.g., user preferences, theme). Be mindful of what is persisted to avoid storing large amounts of data or sensitive information.
*   **`immer`:** Mandatory for immutable state updates, as mentioned above.

## Example Structure (Conceptual)

```typescript
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
// import { enableMapSet } from 'immer'; // Call in main.tsx

interface MyFeatureState {
  someId: string | null;
  itemMap: Map<string, YourItemType>;
  isLoading: boolean;
  // ... other state properties
}

interface MyFeatureActions {
  setSomeId: (id: string | null) => void;
  addItem: (item: YourItemType) => void;
  updateItem: (itemId: string, updates: Partial<YourItemType>) => void;
  setLoading: (loading: boolean) => void;
}

export const useMyFeatureStore = create<MyFeatureState & MyFeatureActions>()(
  devtools(
    persist(
      immer((set, get) => ({
        someId: null,
        itemMap: new Map(),
        isLoading: false,

        setSomeId: (id) => set(state => { state.someId = id; }),
        addItem: (item) => set(state => { state.itemMap.set(item.id, item); }),
        updateItem: (itemId, updates) => set(state => {
          const item = state.itemMap.get(itemId);
          if (item) {
            Object.assign(item, updates);
          }
        }),
        setLoading: (loading) => set(state => { state.isLoading = loading; }),
      })),
      { name: 'my-feature-storage' } // Name for localStorage
    )
  )
);
``` 