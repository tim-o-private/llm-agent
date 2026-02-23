-- Fix: Update task tool types in the tools table.
-- The original migration (20260220000000) used ON CONFLICT DO UPDATE but
-- did NOT include 'type' in the update clause, so pre-existing rows with
-- type='CRUDTool' were never corrected. The loader checks 'type' to pick
-- the right Python class, so CRUDTool rows are skipped (missing table_name).

UPDATE tools SET type = 'GetTasksTool'   WHERE name = 'get_tasks'   AND type != 'GetTasksTool';
UPDATE tools SET type = 'GetTaskTool'    WHERE name = 'get_task'     AND type != 'GetTaskTool';
UPDATE tools SET type = 'CreateTaskTool' WHERE name = 'create_task'  AND type != 'CreateTaskTool';
UPDATE tools SET type = 'UpdateTaskTool' WHERE name = 'update_task'  AND type != 'UpdateTaskTool';
UPDATE tools SET type = 'DeleteTaskTool' WHERE name = 'delete_task'  AND type != 'DeleteTaskTool';
