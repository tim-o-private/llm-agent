import React, { useState } from 'react';
// AppShell is used via AppLayout in App.tsx, so no direct import here is needed if this page is rendered via <Outlet /> in AppLayout.
import TaskListGroup from '../components/tasks/TaskListGroup'; // Assuming TaskListGroup is created
import { TaskCardProps } from '@/components/ui'; // Updated import
import FABQuickAdd from '../components/tasks/FABQuickAdd'; // Import FABQuickAdd
import QuickAddTray from '../components/tasks/QuickAddTray'; // Import QuickAddTray
import { AnimatePresence } from 'framer-motion'; // Import AnimatePresence
import TaskDetailTray, { TaskDetails } from '../components/tasks/TaskDetailTray'; // Import TaskDetailTray and TaskDetails

// Initial Mock data for demonstration
const initialMockMorningTasks: TaskCardProps[] = [
  { id: '1', title: 'Morning Meditation', time: '7:00 AM', category: 'Mindfulness', completed: true, onToggleComplete: () => {} }, // Placeholder, will be replaced
  { id: '2', title: 'Review daily priorities', time: '7:30 AM', completed: false, onToggleComplete: () => {} }, // Placeholder
];

const initialMockAfternoonTasks: TaskCardProps[] = [
  { id: '3', title: 'Project Titan meeting', time: '2:00 PM', category: 'Work', completed: false, onToggleComplete: () => {} }, // Placeholder
];

const initialMockEveningTasks: TaskCardProps[] = [
  { id: '4', title: 'Read for 30 minutes', time: '8:00 PM', category: 'Growth', completed: false, onToggleComplete: () => {} }, // Placeholder
];

// Placeholder for CoachCard to be added later - REMOVED this functional component definition
// const CoachCardPlaceholder = () => (
//   <div className="p-4 bg-gray-200 dark:bg-gray-700 rounded-lg shadow">
//     <p className="text-sm text-gray-700 dark:text-gray-300">AI Coach Suggestions here...</p>
//   </div>
// );

const TodayView: React.FC = () => {
  const [morningTasks, setMorningTasks] = useState<TaskCardProps[]>(initialMockMorningTasks);
  const [afternoonTasks, setAfternoonTasks] = useState<TaskCardProps[]>(initialMockAfternoonTasks);
  const [eveningTasks, setEveningTasks] = useState<TaskCardProps[]>(initialMockEveningTasks);
  // REMOVED: const [isAddTaskTrayOpen, setIsAddTaskTrayOpen] = useState(false); // State for AddTaskTray

  // State for trays
  const [isQuickAddTrayOpen, setIsQuickAddTrayOpen] = useState(false);
  const [isTaskDetailTrayOpen, setIsTaskDetailTrayOpen] = useState(false);
  const [initialDataForDetailTray, setInitialDataForDetailTray] = useState<Partial<TaskDetails> | undefined>(undefined);

  const handleToggleTask = (taskId: string) => {
    const updateTasks = (tasks: TaskCardProps[]) =>
      tasks.map(task =>
        task.id === taskId ? { ...task, completed: !task.completed } : task
      );

    setMorningTasks(prevTasks => updateTasks(prevTasks));
    setAfternoonTasks(prevTasks => updateTasks(prevTasks));
    setEveningTasks(prevTasks => updateTasks(prevTasks));
    // console.log(`Task ${taskId} toggled.`); // Logging can be removed or kept for debugging
  };

  // Handlers for QuickAddTray
  const handleOpenQuickAddTray = () => {
    setIsQuickAddTrayOpen(true);
  };

  const handleCloseQuickAddTray = () => {
    setIsQuickAddTrayOpen(false);
  };

  const handleAddTaskFromQuickTray = (taskData: { title: string; timePeriod: string }) => {
    const newTask: TaskCardProps = {
      id: String(Date.now()), // Simple ID generation
      title: taskData.title,
      completed: false,
      onToggleComplete: handleToggleTask, // Ensure this handler is passed
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), // Placeholder time
      // category: undefined, // Or some default category
    };

    switch (taskData.timePeriod) {
      case 'Morning':
        setMorningTasks(prevTasks => [newTask, ...prevTasks]);
        break;
      case 'Afternoon':
        setAfternoonTasks(prevTasks => [newTask, ...prevTasks]);
        break;
      case 'Evening':
        setEveningTasks(prevTasks => [newTask, ...prevTasks]);
        break;
      default:
        setMorningTasks(prevTasks => [newTask, ...prevTasks]); // Default to morning
    }
    handleCloseQuickAddTray();
  };

  // Handlers for TaskDetailTray
  const openTaskDetailTrayFromQuickAdd = (data: { title: string; timePeriod: string }) => {
    console.log('[TodayView] openTaskDetailTrayFromQuickAdd called with:', data);
    setInitialDataForDetailTray({ title: data.title, timePeriod: data.timePeriod, notes: '' });
    setIsTaskDetailTrayOpen(true);
    console.log('[TodayView] Set isTaskDetailTrayOpen to true.');
    handleCloseQuickAddTray();
  };

  const closeTaskDetailTray = () => {
    console.log('[TodayView] closeTaskDetailTray called.');
    setIsTaskDetailTrayOpen(false);
    setInitialDataForDetailTray(undefined);
  };

  const saveTaskFromDetailTray = (taskDetails: TaskDetails) => {
    console.log('[TodayView] saveTaskFromDetailTray called with:', taskDetails);
    const newTask: TaskCardProps = {
      id: String(Date.now()), // Simple ID generation
      title: taskDetails.title,
      notes: taskDetails.notes, // Assuming TaskCardProps can hold notes
      category: taskDetails.notes ? 'Detailed' : undefined, // Example: add category if notes exist
      completed: false,
      onToggleComplete: handleToggleTask,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), // Placeholder time
    };

    switch (taskDetails.timePeriod) {
      case 'Morning':
        setMorningTasks(prevTasks => [newTask, ...prevTasks]);
        break;
      case 'Afternoon':
        setAfternoonTasks(prevTasks => [newTask, ...prevTasks]);
        break;
      case 'Evening':
        setEveningTasks(prevTasks => [newTask, ...prevTasks]);
        break;
      default:
        setMorningTasks(prevTasks => [newTask, ...prevTasks]); // Default to morning
    }
    closeTaskDetailTray();
  };

  // Add onToggleComplete to tasks before passing to TaskListGroup
  // This ensures TaskCard receives the correct handler.
  const morningTasksWithHandler = morningTasks.map(task => ({...task, onToggleComplete: handleToggleTask}));
  const afternoonTasksWithHandler = afternoonTasks.map(task => ({...task, onToggleComplete: handleToggleTask}));
  const eveningTasksWithHandler = eveningTasks.map(task => ({...task, onToggleComplete: handleToggleTask}));

  const allTasksCount = morningTasksWithHandler.length + afternoonTasksWithHandler.length + eveningTasksWithHandler.length;

  return (
    <div className="p-4 md:p-6 lg:p-8 h-full flex flex-col">
      <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-6">Today's Focus</h1>

      {/* Log states for debugging TaskDetailTray */}
      {/* 
      <pre className="text-xs bg-gray-100 p-2 rounded dark:bg-gray-700 dark:text-gray-300">
        isTaskDetailTrayOpen: {String(isTaskDetailTrayOpen)}
        initialDataForDetailTray: {JSON.stringify(initialDataForDetailTray)}
      </pre>
      */}
      {allTasksCount === 0 ? (
        <div className="flex-grow flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
          </svg>
          <p className="text-lg">Your day is clear!</p>
          <p>Add some tasks to get started.</p>
        </div>
      ) : (
        <div className="flex-grow overflow-y-auto space-y-8">
          <TaskListGroup title="Morning" tasks={morningTasksWithHandler} />
          <TaskListGroup title="Afternoon" tasks={afternoonTasksWithHandler} />
          <TaskListGroup title="Evening" tasks={eveningTasksWithHandler} />
        </div>
      )}

      {/* Replace placeholder with actual FABQuickAdd component */}
      <FABQuickAdd onClick={handleOpenQuickAddTray} />

      {/* Placeholder for CoachCard - remains as a div for now */}
      <div 
        className="hidden md:block fixed top-1/3 right-6 bg-white dark:bg-gray-800 p-4 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 w-64 h-auto"
      >
        {/* Placeholder for CoachCard content */}
      </div>

      {/* Un-comment and integrate QuickAddTray */}
      <AnimatePresence>
        {isQuickAddTrayOpen && (
          <QuickAddTray 
            isOpen={isQuickAddTrayOpen}
            onClose={handleCloseQuickAddTray} 
            onAddTask={handleAddTaskFromQuickTray}
            onOpenDetails={openTaskDetailTrayFromQuickAdd} // Prop to open detail tray
          />
        )}
      </AnimatePresence>

      {/* Log props passed to TaskDetailTray */}
      {/* {console.log('[TodayView] Rendering TaskDetailTray with isOpen:', isTaskDetailTrayOpen, 'initialData:', initialDataForDetailTray)} */}
      <TaskDetailTray 
        isOpen={isTaskDetailTrayOpen} 
        onClose={closeTaskDetailTray} 
        onSaveTask={saveTaskFromDetailTray} 
        initialTaskData={initialDataForDetailTray}
      />
    </div>
  );
};

export default TodayView; 