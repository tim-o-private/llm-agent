import React, { Fragment, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { Input, Button } from '@clarity/ui'; // Assuming Button and Input are available

interface AddTaskTrayProps {
  isOpen: boolean;
  onClose: () => void;
  onAddTask: (title: string) => void; // Simplified for now
}

const AddTaskTray: React.FC<AddTaskTrayProps> = ({ isOpen, onClose, onAddTask }) => {
  const [title, setTitle] = useState('');

  const handleSubmit = () => {
    if (title.trim()) {
      onAddTask(title.trim());
      setTitle(''); // Reset title
      onClose(); // Close after adding
    }
  };

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-10" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
                <div>
                  <Dialog.Title as="h3" className="text-lg font-medium leading-6 text-gray-900 dark:text-white">
                    Add New Task
                  </Dialog.Title>
                  <div className="mt-4">
                    <Input
                      type="text"
                      placeholder="Enter task title..."
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      // Assuming Input component can take a className for styling if needed
                      className="w-full" 
                    />
                  </div>
                </div>
                <div className="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
                  <Button
                    variant="primary" // Assuming a primary variant
                    onClick={handleSubmit}
                    className="w-full justify-center sm:col-start-2"
                  >
                    Add Task
                  </Button>
                  <Button
                    variant="secondary" // Assuming a secondary or default variant
                    onClick={onClose}
                    className="mt-3 w-full justify-center sm:col-start-1 sm:mt-0"
                  >
                    Cancel
                  </Button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
};

export default AddTaskTray; 