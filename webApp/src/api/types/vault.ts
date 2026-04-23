/**
 * SPEC-046 Vault browser types matching the backend vault_router.py
 * response models (TreeNodeModel, FileResponse, FolderEntryModel).
 */

export interface TreeNode {
  name: string;
  path: string;
  type: 'file' | 'folder';
  mtime: string;
  size: number;
  children?: TreeNode[];
}

export interface TreeResponse {
  tree: TreeNode[];
}

export interface VaultFile {
  content: string;
  mtime: string;
  size: number;
}

export interface FolderEntry {
  name: string;
  path: string;
  type: 'file' | 'folder';
  mtime: string;
  size: number;
}

export interface FolderResponse {
  entries: FolderEntry[];
}
