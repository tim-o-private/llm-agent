import React from 'react';
import { Button } from '@/components/ui/Button';
import { useTaskModalManagement } from '@/hooks/useTaskModalManagement';
import { TaskDetailView } from '@/components/features/TaskDetail/TaskDetailView';
import { PrioritizeViewModal } from '@/components/features/PrioritizeView/PrioritizeViewModal';

/**
 * Test page for manually testing the modal management hook
 *
 * To use this page:
 * 1. Add it to your router
 * 2. Navigate to /modal-test
 * 3. Click buttons to test modal functionality
 */
const ModalTestPage: React.FC = () => {
  const modalManagement = useTaskModalManagement({
    syncWithStore: true,
  });

  const testTaskId = 'test-task-123';

  const handleDeleteTask = (taskId: string) => {
    console.log('Delete task:', taskId);
    modalManagement.closeModal();
  };

  const handleStartFocusSession = (task: any, config: any) => {
    console.log('Start focus session:', task, config);
    modalManagement.closeModal();
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Modal Management Hook Test</h1>

      {/* Current State Display */}
      <div className="bg-gray-100 p-4 rounded-lg mb-8">
        <h2 className="text-xl font-semibold mb-4">Current Modal State</h2>
        <div className="space-y-2">
          <p>
            <strong>Type:</strong> {modalManagement.modalState.type || 'None'}
          </p>
          <p>
            <strong>Task ID:</strong> {modalManagement.modalState.taskId || 'None'}
          </p>
          <p>
            <strong>Is Open:</strong> {modalManagement.modalState.isOpen ? 'Yes' : 'No'}
          </p>
          <p>
            <strong>Detail Modal Open:</strong> {modalManagement.detailModal.isOpen ? 'Yes' : 'No'}
          </p>
          <p>
            <strong>Prioritize Modal Open:</strong> {modalManagement.prioritizeModal.isOpen ? 'Yes' : 'No'}
          </p>
        </div>
      </div>

      {/* Test Buttons */}
      <div className="space-y-4 mb-8">
        <h2 className="text-xl font-semibold">Test Actions</h2>

        <div className="flex flex-wrap gap-4">
          <Button onClick={() => modalManagement.detailModal.open(testTaskId)} variant="solid">
            Open Detail Modal
          </Button>

          <Button onClick={() => modalManagement.prioritizeModal.open(testTaskId)} variant="solid">
            Open Prioritize Modal
          </Button>

          <Button onClick={() => modalManagement.openModal('detail', 'different-task-456')} variant="outline">
            Open Detail for Different Task
          </Button>

          <Button onClick={() => modalManagement.closeModal()} variant="soft">
            Close Modal
          </Button>
        </div>
      </div>

      {/* Query Tests */}
      <div className="bg-blue-50 p-4 rounded-lg mb-8">
        <h2 className="text-xl font-semibold mb-4">Query Results</h2>
        <div className="space-y-2">
          <p>
            <strong>Is Detail Modal Open:</strong> {modalManagement.isModalOpen('detail') ? 'Yes' : 'No'}
          </p>
          <p>
            <strong>Is Prioritize Modal Open:</strong> {modalManagement.isModalOpen('prioritize') ? 'Yes' : 'No'}
          </p>
          <p>
            <strong>Is Modal Open for Test Task:</strong>{' '}
            {modalManagement.isModalOpenForTask(testTaskId) ? 'Yes' : 'No'}
          </p>
          <p>
            <strong>Current Task ID:</strong> {modalManagement.currentTaskId || 'None'}
          </p>
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-yellow-50 p-4 rounded-lg">
        <h2 className="text-xl font-semibold mb-4">Test Instructions</h2>
        <ol className="list-decimal list-inside space-y-2">
          <li>Click "Open Detail Modal" - should open the task detail modal</li>
          <li>Close it using the X button or ESC key</li>
          <li>Click "Open Prioritize Modal" - should open the prioritize modal</li>
          <li>Try switching between modals - should close one and open the other</li>
          <li>Check that the state display updates correctly</li>
          <li>Verify that query results are accurate</li>
          <li>Test keyboard shortcuts if implemented</li>
        </ol>
      </div>

      {/* Modals */}
      {modalManagement.detailModal.isOpen && (
        <TaskDetailView
          taskId={modalManagement.detailModal.taskId!}
          isOpen={modalManagement.detailModal.isOpen}
          onOpenChange={modalManagement.handleModalOpenChange}
          onTaskUpdated={() => console.log('Task updated')}
          onDeleteTaskFromDetail={handleDeleteTask}
        />
      )}

      {modalManagement.prioritizeModal.isOpen && (
        <PrioritizeViewModal
          taskId={modalManagement.prioritizeModal.taskId!}
          isOpen={modalManagement.prioritizeModal.isOpen}
          onOpenChange={modalManagement.handleModalOpenChange}
          onStartFocusSession={handleStartFocusSession}
        />
      )}
    </div>
  );
};

export default ModalTestPage;
