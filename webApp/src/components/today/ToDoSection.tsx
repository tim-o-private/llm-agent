import React from 'react';
import { Checkbox } from '@/components/ui/Checkbox';
import { useToggleTodo } from '@/api/hooks/useTodayHooks';
import type { TodoItem } from '@/api/types/today';
import { clsx } from 'clsx';

const HEADING_ID = 'today-to-do-heading';

export const ToDoSection: React.FC<{ items: TodoItem[] }> = ({ items }) => {
  const toggle = useToggleTodo();

  return (
    <section aria-labelledby={HEADING_ID} className="py-6">
      <h2 id={HEADING_ID} className="text-lg font-medium text-text-secondary tracking-tight mb-3">
        To do
      </h2>
      {items.length === 0 ? (
        <p className="text-sm text-text-muted italic">
          No to-dos — the agent hasn&apos;t surfaced anything yet.
        </p>
      ) : (
        <ul className="space-y-2">
          {items.map((todo) => (
            <li key={todo.line_id} className="flex items-start gap-2 text-sm">
              <Checkbox
                checked={todo.checked}
                srLabel={todo.text}
                onCheckedChange={(c) =>
                  toggle.mutate({ line_id: todo.line_id, checked: c === true })
                }
                className="mt-0.5"
              />
              <span
                className={clsx(
                  'text-text-primary',
                  todo.checked && 'line-through text-text-muted',
                )}
              >
                {todo.text}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};

export default ToDoSection;
