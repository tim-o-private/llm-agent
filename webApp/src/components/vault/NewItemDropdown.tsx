import React, { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileTextIcon, PlusIcon } from '@radix-ui/react-icons';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { FolderIcon } from '@/components/ui/icons/FolderIcon';
import { useCreateFile, useCreateFolder } from '@/api/hooks/useVaultHooks';
import { toast } from '@/components/ui/toast';

interface NewItemDropdownProps {
  /** Path prefix for the new item (empty string for vault root) */
  parentPath?: string;
  /** Trigger element — defaults to a "+" icon button */
  trigger?: React.ReactNode;
  align?: 'start' | 'center' | 'end';
}

export const NewItemDropdown: React.FC<NewItemDropdownProps> = ({
  parentPath = '',
  trigger,
  align = 'end',
}) => {
  const navigate = useNavigate();
  const createFile = useCreateFile();
  const createFolder = useCreateFolder();

  const prefix = parentPath ? `${parentPath}/` : '';

  const handleNewFile = useCallback(() => {
    createFile.mutate(
      { path: `${prefix}untitled-${Date.now()}.md`, content: '# Untitled\n' },
      {
        onSuccess: (result) => navigate(`/vault/${result.path}`, { state: { isNew: true } }),
        onError: (err) => toast.error(err.message),
      },
    );
  }, [createFile, navigate, prefix]);

  const handleNewFolder = useCallback(() => {
    createFolder.mutate(
      { path: `${prefix}new-folder-${Date.now()}` },
      {
        onSuccess: (result) => navigate(`/vault/${result.path}/`, { state: { isNew: true } }),
        onError: (err) => toast.error(err.message),
      },
    );
  }, [createFolder, navigate, prefix]);

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        {trigger ?? (
          <button
            className="p-0.5 rounded text-text-muted hover:text-brand-primary hover:bg-ui-interactive-bg-hover transition-colors"
            aria-label="Create new file or folder"
          >
            <PlusIcon className="h-4 w-4" />
          </button>
        )}
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align={align}
          sideOffset={4}
          className="z-50 min-w-[140px] bg-ui-element-bg border border-dashed border-ui-border rounded-md p-1 shadow-lg animate-fade-in"
        >
          <DropdownMenu.Item
            onSelect={handleNewFile}
            className="flex items-center gap-2 px-2 py-1.5 text-sm text-text-secondary rounded cursor-pointer outline-none data-[highlighted]:bg-ui-interactive-bg-hover data-[highlighted]:text-text-primary"
          >
            <FileTextIcon className="h-4 w-4" />
            File
          </DropdownMenu.Item>
          <DropdownMenu.Item
            onSelect={handleNewFolder}
            className="flex items-center gap-2 px-2 py-1.5 text-sm text-text-secondary rounded cursor-pointer outline-none data-[highlighted]:bg-ui-interactive-bg-hover data-[highlighted]:text-text-primary"
          >
            <FolderIcon className="h-4 w-4" />
            Folder
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
};
