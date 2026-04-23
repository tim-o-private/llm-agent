import type { ChatScope } from '@/api/types/chat';

export function scopeLabel(scope: ChatScope): string | null {
  switch (scope.type) {
    case 'global':
      return null;
    case 'today':
      return 'Today';
    case 'folder':
      return `Folder: ${scope.path.replace(/\/$/, '').split('/').pop()}`;
    case 'file':
      return `File: ${scope.path.split('/').pop()}`;
    case 'workflow':
      return `Workflow: ${scope.path.split('/').pop()?.replace('.flow.md', '')}`;
    default:
      return null;
  }
}
