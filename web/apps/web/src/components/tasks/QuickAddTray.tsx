import React, { useState, useEffect } from 'react';
import { Button, Input, Label } from '@clarity/ui'; // Removed Modal import
import { motion } from 'framer-motion'; // Import motion

interface QuickAddTrayProps {
  isOpen: boolean;
  onClose: () => void;
  onAddTask: (task: { title: string; timePeriod: string }) => void;
  onOpenDetails?: (data: { title: string; timePeriod: string }) => void; // Added prop
}

const trayVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 20 },
  visible: { opacity: 1, scale: 1, y: 0, transition: { duration: 0.2, ease: "easeInOut" } },
  exit: { opacity: 0, scale: 0.95, y: 20, transition: { duration: 0.15, ease: "easeInOut" } },
};

const QuickAddTray: React.FC<QuickAddTrayProps> = ({ isOpen, onClose, onAddTask, onOpenDetails }) => {
  const [title, setTitle] = useState('');
  const [timePeriod, setTimePeriod] = useState('Morning'); // Default time period

  // Log if onOpenDetails is provided
  useEffect(() => {
    if (onOpenDetails) {
      console.log('[QuickAddTray] onOpenDetails prop received.');
    } else {
      console.log('[QuickAddTray] onOpenDetails prop NOT received.');
    }
  }, [onOpenDetails]);

  useEffect(() => {
    // Reset form when tray is opened/closed if it was closed while having data
    if (!isOpen) {
      setTitle('');
      setTimePeriod('Morning');
    }
  }, [isOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    onAddTask({ title, timePeriod });
    onClose();
  };

  const handleOpenDetails = () => {
    console.log('[QuickAddTray] handleOpenDetails called.');
    if (onOpenDetails) {
      console.log('[QuickAddTray] Calling props.onOpenDetails with:', { title, timePeriod });
      onOpenDetails({ title, timePeriod });
      console.log('[QuickAddTray] Calling props.onClose after onOpenDetails.');
      onClose();
    } else {
      console.error('[QuickAddTray] onOpenDetails is undefined!');
    }
  };

  if (!isOpen) {
    return null;
  }

  // Styling this as a tray/panel that slides up or appears near the FAB
  // For now, using a div with fixed positioning and some basic styling.
  // A proper slide-in animation could be added with Framer Motion later.
  return (
    <motion.div 
      className="fixed inset-x-0 bottom-0 bg-white dark:bg-gray-800 p-4 shadow-2xl rounded-t-lg md:max-w-md md:mx-auto md:bottom-4 md:rounded-lg z-50 border-t border-gray-200 dark:border-gray-700"
      variants={trayVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
    >
      <form onSubmit={handleSubmit}>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Add Quick Task</h2>
        
        <div className="mb-4">
          <Label htmlFor="task-title">Task Title</Label>
          <Input 
            type="text" 
            id="task-title" 
            value={title} 
            onChange={(e) => setTitle(e.target.value)} 
            placeholder="e.g., Water the plants"
            className="w-full"
            required
          />
        </div>

        <div className="mb-6">
          <Label htmlFor="time-period">Time Period</Label>
          <select 
            id="time-period" 
            value={timePeriod} 
            onChange={(e) => setTimePeriod(e.target.value)} 
            className="w-full mt-1 block pl-3 pr-10 py-2 text-base border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option>Morning</option>
            <option>Afternoon</option>
            <option>Evening</option>
          </select>
        </div>

        <div className="flex justify-end space-x-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          {onOpenDetails && (
            <Button type="button" variant="secondary" onClick={handleOpenDetails}>
              Add Details
            </Button>
          )}
          <Button type="submit" variant="primary">
            Add Task
          </Button>
        </div>
      </form>
    </motion.div>
  );
};

export default QuickAddTray; 