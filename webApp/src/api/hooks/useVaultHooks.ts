/**
 * React Query hooks for the SPEC-046 Vault browser API.
 *
 * Endpoints consumed:
 *   GET /api/vault/tree
 *   GET /api/vault/file?path=<rel>
 *   GET /api/vault/folder?path=<rel>
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authHeaders } from '@/lib/apiClient';
import type { TreeResponse, VaultFile, FolderResponse } from '@/api/types/vault';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const VAULT_TREE_KEY = ['vault', 'tree'] as const;
const VAULT_FILE_KEY = ['vault', 'file'] as const;
const VAULT_FOLDER_KEY = ['vault', 'folder'] as const;

async function fetchVaultTree(): Promise<TreeResponse> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/vault/tree`, { headers });
  if (!res.ok) throw new Error(`GET /vault/tree failed: ${res.status}`);
  return res.json();
}

async function fetchVaultFile(path: string): Promise<VaultFile> {
  const headers = await authHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/vault/file?path=${encodeURIComponent(path)}`,
    { headers },
  );
  if (!res.ok) throw new Error(`GET /vault/file failed: ${res.status}`);
  return res.json();
}

async function fetchVaultFolder(path: string): Promise<FolderResponse> {
  const headers = await authHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/vault/folder?path=${encodeURIComponent(path)}`,
    { headers },
  );
  if (!res.ok) throw new Error(`GET /vault/folder failed: ${res.status}`);
  return res.json();
}

// --- Queries ---------------------------------------------------------------

export function useVaultTree() {
  return useQuery<TreeResponse, Error>({
    queryKey: [...VAULT_TREE_KEY],
    queryFn: fetchVaultTree,
    staleTime: 60_000,
  });
}

export function useVaultFile(path: string, enabled = true) {
  return useQuery<VaultFile, Error>({
    queryKey: [...VAULT_FILE_KEY, path],
    queryFn: () => fetchVaultFile(path),
    enabled: enabled && !!path,
    staleTime: 30_000,
  });
}

export function useVaultFolder(path: string, enabled = true) {
  return useQuery<FolderResponse, Error>({
    queryKey: [...VAULT_FOLDER_KEY, path],
    queryFn: () => fetchVaultFolder(path),
    enabled,
    staleTime: 30_000,
  });
}

// --- Mutations --------------------------------------------------------------

interface CreateFileArgs {
  path: string;
  content?: string;
}

interface CreateFileResult {
  path: string;
  mtime: number;
}

interface CreateFolderArgs {
  path: string;
}

interface CreateFolderResult {
  path: string;
}

async function postCreateFile(args: CreateFileArgs): Promise<CreateFileResult> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/vault/file`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ path: args.path, content: args.content ?? '' }),
  });
  if (res.status === 409) throw new Error('File already exists');
  if (!res.ok) throw new Error(`POST /vault/file failed: ${res.status}`);
  return res.json();
}

async function postCreateFolder(args: CreateFolderArgs): Promise<CreateFolderResult> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/vault/folder`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ path: args.path }),
  });
  if (res.status === 409) throw new Error('Folder already exists');
  if (!res.ok) throw new Error(`POST /vault/folder failed: ${res.status}`);
  return res.json();
}

function useVaultMutation<TResult, TArgs>(
  mutationFn: (args: TArgs) => Promise<TResult>,
) {
  const qc = useQueryClient();
  return useMutation<TResult, Error, TArgs>({
    mutationFn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...VAULT_TREE_KEY] });
      qc.invalidateQueries({ queryKey: [...VAULT_FOLDER_KEY] });
    },
  });
}

export function useCreateFile() {
  return useVaultMutation<CreateFileResult, CreateFileArgs>(postCreateFile);
}

export function useCreateFolder() {
  return useVaultMutation<CreateFolderResult, CreateFolderArgs>(postCreateFolder);
}

// --- Rename ----------------------------------------------------------------

interface RenameArgs {
  source: string;
  target: string;
}

interface RenameResult {
  path: string;
}

async function patchRename(args: RenameArgs): Promise<RenameResult> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/vault/rename`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify({ source: args.source, target: args.target }),
  });
  if (res.status === 409) throw new Error('An item with that name already exists');
  if (res.status === 404) throw new Error('Source not found');
  if (!res.ok) throw new Error(`PATCH /vault/rename failed: ${res.status}`);
  return res.json();
}

export function useRenameItem() {
  return useVaultMutation<RenameResult, RenameArgs>(patchRename);
}
