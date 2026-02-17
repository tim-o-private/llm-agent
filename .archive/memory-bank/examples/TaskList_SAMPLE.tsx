/**
 * TaskList Component - Displays a list of tasks with loading and error states
 * 
 * @docs memory-bank/patterns/ui-patterns.md#pattern-3-react-query-hooks
 * @rules memory-bank/rules/ui-rules.json#ui-004,ui-005
 * @examples memory-bank/patterns/ui-patterns.md#complete-component-example
 * @related webApp/src/components/ui/ErrorMessage.tsx webApp/src/api/hooks/useTaskHooks.ts
 */

import { useTaskHooks } from '@/api/hooks/useTaskHooks';
import { ErrorMessage } from '@/components/ui/ErrorMessage';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { Card } from '@/components/ui/Card';
import { useOverlayStore } from '@/stores/useOverlayStore';

interface Task {
  id: string;
  title: string;
  description?: string;
  completed: boolean;
  createdAt: string;
}

interface TaskListProps {
  userId: string;
  filter?: 'all' | 'completed' | 'pending';
}

/**
 * TaskList component following UI patterns for React Query hooks,
 * error handling, and centralized overlay management.
 * 
 * Implements patterns:
 * - Pattern 3: React Query Hooks for API state
 * - Pattern 5: Consistent error/loading states  
 * - Pattern 2: Centralized overlay management
 */
export function TaskList({ userId, filter = 'all' }: TaskListProps) {
  const { openModal } = useOverlayStore();
  const { data: tasks, isLoading, error } = useTaskHooks.useFetchTasks(userId, filter);

  // Pattern 5: Handle loading state first
  if (isLoading) {
    return (
      <div className="flex justify-center p-8">
        <LoadingSpinner />
      </div>
    );
  }

  // Pattern 5: Handle error state with consistent ErrorMessage component
  if (error) {
    return <ErrorMessage error={error} />;
  }

  // Handle empty state
  if (!tasks || tasks.length === 0) {
    return (
      <div className="text-center p-8 text-text-secondary">
        No tasks found. Create your first task to get started.
      </div>
    );
  }

  // Pattern 2: Use centralized overlay for task editing
  const handleEditTask = (taskId: string) => {
    openModal('editTask', { taskId });
  };

  const handleCreateTask = () => {
    openModal('createTask', { userId });
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-text-primary">
          Tasks ({tasks.length})
        </h2>
        <button
          onClick={handleCreateTask}
          className="bg-brand-primary text-white px-4 py-2 rounded hover:bg-brand-primary-hover"
        >
          Add Task
        </button>
      </div>

      <div className="space-y-3">
        {tasks.map((task) => (
          <Card 
            key={task.id}
            className="cursor-pointer hover:shadow-md transition-shadow"
            onClick={() => handleEditTask(task.id)}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className={`font-medium ${task.completed ? 'line-through text-text-secondary' : 'text-text-primary'}`}>
                  {task.title}
                </h3>
                {task.description && (
                  <p className="text-text-secondary text-sm mt-1">
                    {task.description}
                  </p>
                )}
                <p className="text-text-tertiary text-xs mt-2">
                  Created {new Date(task.createdAt).toLocaleDateString()}
                </p>
              </div>
              <div className="ml-4">
                {task.completed ? (
                  <span className="text-green-600 text-sm">✓ Complete</span>
                ) : (
                  <span className="text-yellow-600 text-sm">○ Pending</span>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
} 