import React, { useState } from 'react';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';

export const DebugTaskForm: React.FC = () => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [status, setStatus] = useState('pending');
  const [priority, setPriority] = useState<0 | 1 | 2 | 3>(0);
  const [dueDate, setDueDate] = useState('');

  // Removed console.log to prevent infinite render loop

  return (
    <div className="p-4 border border-gray-300 rounded-md space-y-4">
      <h3 className="text-lg font-semibold">Debug Task Form (No DnD Context)</h3>
      
      <div>
        <label htmlFor="debug-title" className="block text-sm font-medium">Title</label>
        <Input 
          id="debug-title"
          value={title}
          onChange={(e) => {
            console.log('Title onChange:', e.target.value);
            setTitle(e.target.value);
          }}
          onKeyDown={(e) => console.log('Title onKeyDown:', e.key)}
          placeholder="Type here..."
        />
        <p className="text-xs text-gray-500">Current value: "{title}"</p>
      </div>

      <div>
        <label htmlFor="debug-description" className="block text-sm font-medium">Description</label>
        <Textarea 
          id="debug-description"
          value={description}
          onChange={(e) => {
            console.log('Description onChange:', e.target.value);
            setDescription(e.target.value);
          }}
          onKeyDown={(e) => console.log('Description onKeyDown:', e.key)}
          placeholder="Type description..."
          rows={3}
        />
        <p className="text-xs text-gray-500">Current value: "{description}"</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="debug-status" className="block text-sm font-medium">Status</label>
          <select 
            id="debug-status"
            value={status}
            onChange={(e) => {
              console.log('Status onChange:', e.target.value);
              setStatus(e.target.value);
            }}
            className="mt-1 block w-full border border-ui-border rounded-md shadow-sm p-2 focus:ring-accent-focus focus:border-accent-focus sm:text-sm bg-ui-input-bg text-text-primary"
          >
            <option value="pending">Pending</option>
            <option value="planning">Planning</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="skipped">Skipped</option>
            <option value="deferred">Deferred</option>
          </select>
          <p className="text-xs text-gray-500">Current value: "{status}"</p>
        </div>

        <div>
          <label htmlFor="debug-priority" className="block text-sm font-medium">Priority</label>
          <select 
            id="debug-priority"
            value={priority}
            onChange={(e) => {
              console.log('Priority onChange:', e.target.value);
              const value = Number(e.target.value) as 0 | 1 | 2 | 3;
              setPriority(value);
            }}
            className="mt-1 block w-full border border-ui-border rounded-md shadow-sm p-2 focus:ring-accent-focus focus:border-accent-focus sm:text-sm bg-ui-input-bg text-text-primary"
          >
            <option value={0}>None</option>
            <option value={1}>Low</option>
            <option value={2}>Medium</option>
            <option value={3}>High</option>
          </select>
          <p className="text-xs text-gray-500">Current value: {priority}</p>
        </div>
      </div>

      <div>
        <label htmlFor="debug-due-date" className="block text-sm font-medium">Due Date</label>
        <input 
          type="date"
          id="debug-due-date"
          value={dueDate}
          onChange={(e) => {
            console.log('Due Date onChange:', e.target.value);
            setDueDate(e.target.value);
          }}
          className="mt-1 block w-full border border-ui-border rounded-md shadow-sm p-2 focus:ring-accent-focus focus:border-accent-focus sm:text-sm bg-ui-input-bg text-text-primary"
        />
        <p className="text-xs text-gray-500">Current value: "{dueDate}"</p>
      </div>
    </div>
  );
}; 