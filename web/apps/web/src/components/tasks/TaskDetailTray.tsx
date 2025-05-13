import React, { useState, useEffect } from 'react';
import { Button, Input, Label, Modal } from '@clarity/ui'; // Removed Textarea import

export interface TaskDetails {
  title: string;
  timePeriod: string;
  notes?: string;
}

interface TaskDetailTrayProps {
  isOpen: boolean;
  onClose: () => void;
  onSaveTask: (task: TaskDetails) => void;
  initialTaskData?: Partial<TaskDetails>; // For editing existing tasks
}

const TaskDetailTray: React.FC<TaskDetailTrayProps> = ({ 
  isOpen, 
  onClose, 
  onSaveTask, 
  initialTaskData 
}) => {
  const [title, setTitle] = useState('');
  const [timePeriod, setTimePeriod] = useState('Morning');
  const [notes, setNotes] = useState('');

  useEffect(() => {
    if (isOpen) {
      setTitle(initialTaskData?.title || '');
      setTimePeriod(initialTaskData?.timePeriod || 'Morning');
      setNotes(initialTaskData?.notes || '');
    } else {
      // Optionally reset when closed, or rely on parent to manage fresh state for new task
      // For now, let's reset to ensure clean state if reopened for a new task without initialData
      // However, if it's reopened for the *same* edit, parent should pass initialTaskData again.
      if (!initialTaskData) {
          setTitle('');
          setTimePeriod('Morning');
          setNotes('');
      }
    }
  }, [isOpen, initialTaskData]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return; // Basic validation
    onSaveTask({ title, timePeriod, notes });
    onClose(); // Explicitly close modal after saving
  };

  return (
    <Modal 
      open={isOpen} 
      onOpenChange={(openValue) => { 
        if (!openValue) onClose(); 
      }} 
      title={initialTaskData?.title ? "Edit Task" : "Add Task Details"}
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <Label htmlFor="detail-task-title">Task Title</Label>
          <Input 
            type="text" 
            id="detail-task-title" 
            value={title} 
            onChange={(e) => setTitle(e.target.value)} 
            placeholder="e.g., Prepare presentation slides"
            className="w-full mt-1"
            required
          />
        </div>

        <div>
          <Label htmlFor="detail-time-period">Time Period</Label>
          <select 
            id="detail-time-period" 
            value={timePeriod} 
            onChange={(e) => setTimePeriod(e.target.value)} 
            className="w-full mt-1 block pl-3 pr-10 py-2 text-base border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option>Morning</option>
            <option>Afternoon</option>
            <option>Evening</option>
          </select>
        </div>

        <div>
          <Label htmlFor="detail-task-notes">Notes (Optional)</Label>
          <textarea // Changed to HTML textarea
            id="detail-task-notes"
            value={notes}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNotes(e.target.value)} // Typed event
            placeholder="Add any details, links, or sub-tasks here..."
            className="w-full mt-1 block pl-3 pr-3 py-2 text-base border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm" // Added common input styling + shadow-sm
            rows={4}
          />
        </div>

        <div className="flex justify-end space-x-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary">
            {initialTaskData?.title ? "Save Changes" : "Save Task"}
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default TaskDetailTray; 