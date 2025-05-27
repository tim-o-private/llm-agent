import React, { useEffect, useState } from 'react';
import { useTaskStore } from '../hooks/useTaskStore'; // Assuming the new store location
import { Spinner } from '@/components/ui/Spinner';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { TrashIcon, Pencil1Icon, CheckIcon, Cross1Icon } from '@radix-ui/react-icons';
import { toast } from 'react-hot-toast';
// TODO: Replace react-hot-toast with Radix UI Toast as per project guidelines (see agent-core-instructions.md)
import { Task, TaskStatus } from '@/api/types';

/**
 * Example component demonstrating the use of the new task store with local-first state
 * and eventual sync with the database.
 */
export const TaskListExample: React.FC = () => {
  // Access the task store
  const { 
    tasks, 
    isLoading, 
    error,
    pendingChanges,
    isSyncing,
    fetchTasks, 
    createTask, 
    updateTask, 
    deleteTask,
    getSubtasksByParentId
  } = useTaskStore();
  
  // Local state for new task input
  const [newTaskTitle, setNewTaskTitle] = useState('');
  // Local state for task being edited
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const [editedTitle, setEditedTitle] = useState('');
  
  // Fetch tasks on component mount
  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);
  
  // Convert tasks object to array for rendering
  const taskList = Object.values(tasks)
    .filter(task => !task.parent_task_id) // Only show top-level tasks
    .sort((a, b) => {
      // Sort by position
      const posA = a.position || 0;
      const posB = b.position || 0;
      if (posA !== posB) return posA - posB;
      
      // Then by priority (higher first)
      if (a.priority !== b.priority) return b.priority - a.priority;
      
      // Then by created date (newer first)
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
  
  // Handle creating a new task
  const handleCreateTask = () => {
    if (!newTaskTitle.trim()) return;
    
    // Create task with optimistic UI update
    const newTaskId = createTask({ 
      title: newTaskTitle,
      status: 'pending',
      priority: 0
    });
    
    // Clear input
    setNewTaskTitle('');
    toast.success('Task created!'); // NOTE: Project preference is Radix UI Toast
    console.log('Created task with temporary ID:', newTaskId);
  };
  
  // Handle updating a task status
  const handleToggleComplete = (task: Task) => {
    const newStatus: TaskStatus = task.status === 'completed' ? 'pending' : 'completed';
    updateTask(task.id, { 
      status: newStatus,
      completed: newStatus === 'completed'
    });
  };
  
  // Start editing a task
  const handleStartEdit = (task: Task) => {
    setEditingTaskId(task.id);
    setEditedTitle(task.title);
  };
  
  // Cancel editing
  const handleCancelEdit = () => {
    setEditingTaskId(null);
    setEditedTitle('');
  };
  
  // Save edited task
  const handleSaveEdit = (taskId: string) => {
    if (!editedTitle.trim()) {
      toast.error('Task title cannot be empty'); // NOTE: Project preference is Radix UI Toast
      return;
    }
    
    updateTask(taskId, { title: editedTitle });
    setEditingTaskId(null);
    setEditedTitle('');
  };
  
  // Delete a task
  const handleDeleteTask = (taskId: string) => {
    if (window.confirm('Are you sure you want to delete this task?')) {
      deleteTask(taskId);
    }
  };
  
  // Show subtasks for a task
  const renderSubtasks = (parentId: string) => {
    const subtasks = getSubtasksByParentId(parentId);
    
    if (subtasks.length === 0) return null;
    
    return (
      <div className="pl-6 mt-2 space-y-2">
        {subtasks.map(subtask => (
          <div 
            key={subtask.id} 
            className="flex items-center p-2 border-l-2 border-gray-200 dark:border-gray-700"
          >
            <input
              type="checkbox"
              checked={subtask.status === 'completed'}
              onChange={() => handleToggleComplete(subtask)}
              className="mr-2"
            />
            
            {editingTaskId === subtask.id ? (
              <div className="flex flex-grow items-center">
                <Input
                  value={editedTitle}
                  onChange={(e) => setEditedTitle(e.target.value)}
                  className="mr-2 flex-grow"
                  autoFocus
                />
                <Button 
                  size="sm" 
                  onClick={() => handleSaveEdit(subtask.id)}
                  className="mr-1"
                >
                  <CheckIcon className="h-4 w-4" />
                </Button>
                <Button 
                  size="sm" 
                  variant="secondary"
                  onClick={handleCancelEdit}
                >
                  <Cross1Icon className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <>
                <span className={`flex-grow ${subtask.status === 'completed' ? 'line-through text-gray-500' : ''}`}>
                  {subtask.title}
                </span>
                <Button 
                  size="sm" 
                  variant="ghost" 
                  onClick={() => handleStartEdit(subtask)}
                  className="mr-1"
                >
                  <Pencil1Icon className="h-4 w-4" />
                </Button>
                <Button 
                  size="sm" 
                  variant="ghost" 
                  onClick={() => handleDeleteTask(subtask.id)}
                >
                  <TrashIcon className="h-4 w-4 text-red-500" />
                </Button>
              </>
            )}
          </div>
        ))}
      </div>
    );
  };
  
  // Calculate sync status indicators
  const pendingChangesCount = Object.keys(pendingChanges).length;
  const hasPendingChanges = pendingChangesCount > 0;
  
  // Render loading state
  if (isLoading && Object.keys(tasks).length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8">
        <Spinner size={32} />
        <p className="mt-4 text-gray-500">Loading tasks...</p>
      </div>
    );
  }
  
  // Render error state
  if (error && !isLoading && Object.keys(tasks).length === 0) {
    return (
      <div className="p-8 text-center">
        <p className="text-red-500">Error loading tasks: {error.message}</p>
        <Button onClick={() => fetchTasks()} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }
  
  return (
    <div className="container mx-auto p-4">
      <div className="mb-2 flex justify-between items-center">
        <h1 className="text-2xl font-bold">Tasks</h1>
        
        {/* Sync status indicator */}
        <div className="text-sm text-gray-500 flex items-center">
          {isSyncing ? (
            <>
              <Spinner size={16} className="mr-2" />
              <span>Syncing...</span>
            </>
          ) : hasPendingChanges ? (
            <span>Pending changes: {pendingChangesCount}</span>
          ) : (
            <span>All changes saved</span>
          )}
        </div>
      </div>
      
      {/* New task input */}
      <div className="flex mb-6">
        <Input
          type="text"
          placeholder="Add a new task..."
          value={newTaskTitle}
          onChange={(e) => setNewTaskTitle(e.target.value)}
          className="flex-grow mr-2"
          onKeyDown={(e) => e.key === 'Enter' && handleCreateTask()}
        />
        <Button onClick={handleCreateTask} disabled={!newTaskTitle.trim()}>
          Add Task
        </Button>
      </div>
      
      {/* Task list */}
      <div className="space-y-3">
        {taskList.length === 0 ? (
          <p className="text-center text-gray-500 py-8">No tasks yet. Add one above!</p>
        ) : (
          taskList.map(task => (
            <div key={task.id} className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={task.status === 'completed'}
                  onChange={() => handleToggleComplete(task)}
                  className="mr-4"
                />
                
                {editingTaskId === task.id ? (
                  <div className="flex flex-grow items-center">
                    <Input
                      value={editedTitle}
                      onChange={(e) => setEditedTitle(e.target.value)}
                      className="mr-2 flex-grow"
                      autoFocus
                    />
                    <Button 
                      size="sm" 
                      onClick={() => handleSaveEdit(task.id)}
                      className="mr-1"
                    >
                      <CheckIcon className="h-4 w-4" />
                    </Button>
                    <Button 
                      size="sm" 
                      variant="secondary"
                      onClick={handleCancelEdit}
                    >
                      <Cross1Icon className="h-4 w-4" />
                    </Button>
                  </div>
                ) : (
                  <>
                    <div className="flex-grow">
                      <h3 className={`font-medium ${task.status === 'completed' ? 'line-through text-gray-500' : ''}`}>
                        {task.title}
                      </h3>
                      {task.description && (
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                          {task.description}
                        </p>
                      )}
                    </div>
                    <Button 
                      size="sm" 
                      variant="ghost" 
                      onClick={() => handleStartEdit(task)}
                      className="mr-1"
                    >
                      <Pencil1Icon className="h-4 w-4" />
                    </Button>
                    <Button 
                      size="sm" 
                      variant="ghost" 
                      onClick={() => handleDeleteTask(task.id)}
                    >
                      <TrashIcon className="h-4 w-4 text-red-500" />
                    </Button>
                  </>
                )}
              </div>
              
              {/* Render subtasks */}
              {renderSubtasks(task.id)}
              
              {/* Add subtask button */}
              <Button
                variant="ghost"
                size="sm"
                className="mt-2 text-xs"
                onClick={() => {
                  const subtaskId = createTask({
                    title: `Subtask for ${task.title}`,
                    parent_task_id: task.id,
                    priority: task.priority,
                    status: 'pending',
                    subtask_position: getSubtasksByParentId(task.id).length,
                  });
                  
                  // Start editing the new subtask
                  setEditingTaskId(subtaskId);
                  setEditedTitle(`Subtask for ${task.title}`);
                }}
              >
                + Add Subtask
              </Button>
              
              {/* Show temporary ID indicator for debugging */}
              {task.id.startsWith('temp_') && (
                <div className="mt-2 text-xs text-gray-400">
                  Temporary ID: {task.id} (pending sync)
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}; 