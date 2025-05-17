## Pattern 8: Consistent Loading Indication

**Goal:** Inform the user clearly when content is loading or an action is in progress, preventing confusion and duplicate actions.

*   **DO:** Use visual indicators for loading states. This can include:
    *   **Spinners:** For quick, localized actions (e.g., a button click initiating a save).
    *   **Skeleton Loaders:** For initial page/component data fetches where the structure of the content is known. This provides a better perceived performance.
    *   **Progress Bars:** For longer, trackable operations (less common in this app, but good to keep in mind).
*   **DO:** Disable interactive elements (buttons, inputs, links) that trigger or are affected by an ongoing operation. This prevents duplicate submissions and clearly indicates that the system is busy.
*   **DO:** Show loading states for both initial data fetches (e.g., loading a page or a list of items) and user-initiated actions (e.g., clicking a save button, submitting a form).
*   **DO:** Leverage the `isLoading`, `isFetching`, or `isPending` (for mutations) statuses provided by React Query hooks (Pattern 5) to automatically manage and display loading states related to API calls.
*   **DO:** Ensure loading indicators are accessible (e.g., if they obscure content, provide appropriate ARIA attributes).
*   **DON'T:** Leave the user uncertain about whether an action is processing or if content is still loading. Lack of feedback is frustrating.
*   **DON'T:** Block the entire UI with a full-screen modal spinner unless the application is truly unusable during the loading period. Prefer localized loading indicators.
*   **DON'T:** Use inconsistent loading indicators (different styles, different placements) across various parts of the application. Strive for a cohesive look and feel.

**Example (Illustrative - Leveraging React Query):**

```typescript
// Assuming useTasks and useCreateTask hooks from Pattern 5 example exist.
// import { useTasks, useCreateTask } from '@/api/hooks/useTaskHooks';
// import { Spinner } from '@/components/ui/Spinner'; // A hypothetical spinner component
// import { TaskSkeletonList } from '@/components/skeletons/TaskSkeletonList'; // Hypothetical skeleton
// import { ErrorMessage } from '@/components/ui/ErrorMessage'; // From Pattern 7

// function TaskListDisplay() {
//   const { data: tasks, isLoading, isFetching, error } = useTasks(); // isLoading for initial, isFetching for background updates

//   if (isLoading) {
//     // return <TaskSkeletonList count={5} />; // Show skeleton during initial load
//   }

//   if (error) {
//     return <ErrorMessage message={`Failed to load tasks: ${error.message}`} isInline={false} />;
//   }

//   if (!tasks || tasks.length === 0) {
//     return <p>No tasks found.</p>;
//   }

//   return (
//     <div>
//       {isFetching && <Spinner />} {/* Optional: Show a small spinner for background refetches */}
//       <ul>
//         {tasks.map(task => (
//           <li key={task.id}>{task.title}</li>
//         ))}
//       </ul>
//     </div>
//   );
// }

// function CreateTaskButton() {
//   const createTaskMutation = useCreateTask();

//   const handleOptimisticClick = () => {
//     // Example with optimistic update - UI changes before API call confirms
//     // The actual API call is handled by mutate/mutateAsync
//     // createTaskMutation.mutate({ title: 'Optimistic New Task', status: 'pending' });
//   };

//   const handlePessimisticClick = async () => {
//     try {
//       // UI waits for API call to complete
//       // await createTaskMutation.mutateAsync({ title: 'Pessimistic New Task', description: 'Details...', status: 'pending' });
//       // toast.success("Task created successfully!");
//     } catch (err) {
//       // Error already handled by hook's onError, or can be handled here too
//       // toast.error(err.message || "Failed to create task.");
//     }
//   };

//   return (
//     <button 
//       onClick={handlePessimisticClick} 
//       disabled={createTaskMutation.isPending} // Use isPending for mutations
//     >
//       {createTaskMutation.isPending ? (
//         <><Spinner size="sm" /> Adding Task...</> 
//       ) : (
//         'Add Task'
//       )}
//     </button>
//   );
// }
```

*Note: The example code is illustrative. Actual component names (`Spinner`, `TaskSkeletonList`), props, and integration will depend on the project's UI library and specific React Query setup in `webApp/`.* 