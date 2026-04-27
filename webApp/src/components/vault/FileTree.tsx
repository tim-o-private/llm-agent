import React, { useMemo, useState, useCallback, useRef, useEffect, createContext, useContext } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Tree } from 'react-arborist';
import type { NodeRendererProps } from 'react-arborist';
import { useVaultTree, useRenameItem } from '@/api/hooks/useVaultHooks';
import { useEntityIndex } from '@/api/hooks/useEntityHooks';
import type { TreeNode } from '@/api/types/vault';
import type { EntitySummary } from '@/api/types/entity';
import {
  FileTextIcon,
  ChevronRightIcon,
  ChevronDownIcon,
  MagnifyingGlassIcon,
  HomeIcon,
  GearIcon,
} from '@radix-ui/react-icons';
import { FolderIcon } from '@/components/ui/icons/FolderIcon';
import { NewItemDropdown } from './NewItemDropdown';
import { toast } from '@/components/ui/toast';

interface TreeRenameCtx {
  editingId: string | null;
  startEditing: (id: string, name: string) => void;
  commitRename: (node: ArboristNode) => void;
  cancelEditing: () => void;
  editValueRef: React.MutableRefObject<string>;
}

const RenameContext = createContext<TreeRenameCtx>({
  editingId: null,
  startEditing: () => {},
  commitRename: () => {},
  cancelEditing: () => {},
  editValueRef: { current: '' },
});

/**
 * Entity type folder icons: person / project / company (AC-21).
 */
const EntityPersonIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M10.5 5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0ZM3 13c0-2.76 2.24-5 5-5s5 2.24 5 5H3Z" />
  </svg>
);

const EntityProjectIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M1.75 1A1.75 1.75 0 0 0 0 2.75v10.5C0 14.216.784 15 1.75 15h12.5A1.75 1.75 0 0 0 16 13.25v-8.5A1.75 1.75 0 0 0 14.25 3H7.5a.25.25 0 0 1-.2-.1l-.9-1.2A1.75 1.75 0 0 0 4.65 1H1.75Z" />
  </svg>
);

const EntityCompanyIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M3 1a1 1 0 0 0-1 1v12h3v-3h6v3h3V2a1 1 0 0 0-1-1H3Zm1 3h2v2H4V4Zm5 0H7v2h2V4ZM4 7h2v2H4V7Zm5 0H7v2h2V7Z" />
  </svg>
);

const entityFolderIcons: Record<string, React.FC<{ className?: string }>> = {
  people: EntityPersonIcon,
  projects: EntityProjectIcon,
  companies: EntityCompanyIcon,
};

/**
 * react-arborist expects { id, name, children? } — we adapt the API TreeNode.
 */
interface ArboristNode {
  id: string;
  name: string;
  /** Display name shown in the tree (may differ from filename for entities) */
  displayName: string;
  isFolder: boolean;
  vaultPath: string;
  /** Entity type folder name (people/projects/companies) if under entities/ */
  entityFolder?: string;
  children?: ArboristNode[];
}

function toArboristNodes(
  nodes: TreeNode[],
  entitySlugMap?: Map<string, EntitySummary>,
): ArboristNode[] {
  return nodes.map((n) => {
    const parts = n.path.split('/');
    const isEntitySubfolder = parts[0] === 'entities' && parts.length >= 2;
    const entityFolder = isEntitySubfolder ? parts[1] : undefined;

    // For entity files: look up display name from entity slug map (O(1))
    let displayName = n.name;
    if (
      entitySlugMap &&
      !n.children &&
      n.type === 'file' &&
      parts[0] === 'entities' &&
      parts.length === 3
    ) {
      const slug = n.name.replace(/\.md$/, '');
      const entity = entitySlugMap.get(slug);
      if (entity) {
        displayName = entity.name;
      }
    }

    // For the entities/ folder itself
    if (n.name === 'entities' && n.type === 'folder') {
      displayName = 'Entities';
    }

    return {
      id: n.path,
      name: n.name,
      displayName,
      isFolder: n.type === 'folder',
      vaultPath: n.path,
      entityFolder,
      children: n.children
        ? toArboristNodes(n.children, entitySlugMap)
        : undefined,
    };
  });
}

/**
 * Recursively filter tree nodes by a search term (case-insensitive name match).
 */
function filterTree(nodes: ArboristNode[], term: string): ArboristNode[] {
  const lower = term.toLowerCase();
  const result: ArboristNode[] = [];
  for (const node of nodes) {
    if (node.name.toLowerCase().includes(lower)) {
      result.push(node);
    } else if (node.children) {
      const filtered = filterTree(node.children, term);
      if (filtered.length > 0) {
        result.push({ ...node, children: filtered });
      }
    }
  }
  return result;
}

/**
 * Separate pinned items from the main tree.
 */
function partitionTree(nodes: ArboristNode[]) {
  let todayNode: ArboristNode | null = null;
  let workflowsNode: ArboristNode | null = null;
  const rest: ArboristNode[] = [];

  for (const node of nodes) {
    if (node.name === 'today.md') {
      todayNode = node;
    } else if (node.name === '_workflows') {
      workflowsNode = node;
    } else {
      rest.push(node);
    }
  }

  return { todayNode, workflowsNode, rest };
}

/**
 * Custom node renderer for the tree.
 * Supports inline rename via double-click.
 */
function NodeRenderer({ node, style, dragHandle }: NodeRendererProps<ArboristNode>) {
  const data = node.data;
  const indent = node.level * 16;
  const { editingId, editValueRef, startEditing, commitRename, cancelEditing } =
    useContext(RenameContext);
  const inputRef = useRef<HTMLInputElement>(null);
  const isEditing = editingId === data.id;
  const [localValue, setLocalValue] = useState('');

  useEffect(() => {
    if (isEditing) {
      setLocalValue(editValueRef.current);
      setTimeout(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      }, 0);
    }
  }, [isEditing, editValueRef]);

  let FolderIconComponent: React.FC<{ className?: string }> = FolderIcon;
  let FileIconComponent: React.FC<{ className?: string }> = FileTextIcon;

  if (data.entityFolder && entityFolderIcons[data.entityFolder]) {
    if (data.isFolder) {
      FolderIconComponent = entityFolderIcons[data.entityFolder];
    } else {
      FileIconComponent = entityFolderIcons[data.entityFolder];
    }
  }

  const handleDoubleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (data.name === 'today.md') return;
    const dotIdx = data.name.lastIndexOf('.');
    const nameOnly = dotIdx > 0 ? data.name.slice(0, dotIdx) : data.name;
    startEditing(data.id, nameOnly);
  };

  return (
    <div
      ref={dragHandle}
      style={{ ...style, paddingLeft: `${indent + 8}px` }}
      className={`flex items-center gap-1.5 py-1 px-2 cursor-pointer text-sm rounded-sm transition-colors group
        ${node.isSelected ? 'bg-accent-surface text-text-accent' : 'text-text-secondary hover:bg-ui-interactive-bg-hover hover:text-text-primary'}
      `}
      onClick={() => { if (!isEditing) node.activate(); }}
      onDoubleClick={handleDoubleClick}
    >
      {data.isFolder ? (
        <>
          <button
            className="p-0.5 flex-shrink-0"
            onClick={(e) => {
              e.stopPropagation();
              node.toggle();
            }}
          >
            {node.isOpen ? (
              <ChevronDownIcon className="h-3.5 w-3.5" />
            ) : (
              <ChevronRightIcon className="h-3.5 w-3.5" />
            )}
          </button>
          <FolderIconComponent className="h-4 w-4 flex-shrink-0 text-text-muted" />
        </>
      ) : (
        <>
          <span className="w-[18px] flex-shrink-0" />
          <FileIconComponent className="h-4 w-4 flex-shrink-0 text-text-muted" />
        </>
      )}
      {isEditing ? (
        <input
          ref={inputRef}
          type="text"
          value={localValue}
          onChange={(e) => { setLocalValue(e.target.value); editValueRef.current = e.target.value; }}
          onBlur={() => commitRename(data)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { e.preventDefault(); commitRename(data); }
            else if (e.key === 'Escape') cancelEditing();
          }}
          onClick={(e) => e.stopPropagation()}
          className="flex-1 min-w-0 bg-transparent border-b border-dashed border-brand-primary outline-none text-sm text-text-primary px-0"
        />
      ) : (
        <span className="truncate">{data.displayName}</span>
      )}
    </div>
  );
}

/**
 * AC-06..AC-11: File tree component using react-arborist.
 */
export const FileTree: React.FC = () => {
  const { data, isLoading, error } = useVaultTree();
  const { data: entityIndex } = useEntityIndex();
  const navigate = useNavigate();
  const location = useLocation();
  const [search, setSearch] = useState('');
  const renameMutation = useRenameItem();
  const [editingId, setEditingId] = useState<string | null>(null);
  const editValueRef = useRef('');

  const entitySlugMap = useMemo(() => {
    if (!entityIndex) return undefined;
    const map = new Map<string, EntitySummary>();
    for (const e of entityIndex) {
      map.set(e.slug, e);
    }
    return map;
  }, [entityIndex]);

  const treeData = useMemo(() => {
    if (!data?.tree) return [];
    return toArboristNodes(data.tree, entitySlugMap);
  }, [data, entitySlugMap]);

  const { todayNode, workflowsNode, rest } = useMemo(
    () => partitionTree(treeData),
    [treeData],
  );

  const filteredRest = useMemo(
    () => (search ? filterTree(rest, search) : rest),
    [rest, search],
  );

  const filteredWorkflows = useMemo(
    () =>
      search && workflowsNode?.children
        ? filterTree(workflowsNode.children, search)
        : workflowsNode?.children ?? [],
    [workflowsNode, search],
  );

  const handleActivate = useCallback(
    (node: { data: ArboristNode }) => {
      const d = node.data;
      if (d.name === 'today.md') {
        navigate('/');
      } else if (d.isFolder) {
        navigate(`/vault/${d.vaultPath}/`);
      } else {
        navigate(`/vault/${d.vaultPath}`);
      }
    },
    [navigate],
  );

  // Determine selected node from current route
  const selectedId = useMemo(() => {
    const path = location.pathname;
    if (path === '/' || path === '/today') return 'today.md';
    if (path.startsWith('/vault/')) return path.replace('/vault/', '').replace(/\/$/, '');
    return '';
  }, [location.pathname]);

  const startEditing = useCallback((id: string, name: string) => {
    editValueRef.current = name;
    setEditingId(id);
  }, []);

  const cancelEditing = useCallback(() => {
    setEditingId(null);
    editValueRef.current = '';
  }, []);

  const commitRename = useCallback(
    (node: ArboristNode) => {
      const trimmed = editValueRef.current.trim();
      const dotIdx = node.name.lastIndexOf('.');
      const ext = dotIdx > 0 ? node.name.slice(dotIdx) : '';
      const nameOnly = dotIdx > 0 ? node.name.slice(0, dotIdx) : node.name;

      if (!trimmed || trimmed === nameOnly) {
        cancelEditing();
        return;
      }

      if (/[/\\]/.test(trimmed)) {
        toast.error('Name cannot contain slashes');
        return;
      }

      const newFilename = ext ? `${trimmed}${ext}` : trimmed;
      const parts = node.vaultPath.split('/');
      parts[parts.length - 1] = newFilename;
      const newPath = parts.join('/');

      renameMutation.mutate(
        { source: node.vaultPath, target: newPath },
        {
          onSuccess: (result) => {
            cancelEditing();
            if (node.isFolder) {
              navigate(`/vault/${result.path}/`, { replace: true });
            } else {
              navigate(`/vault/${result.path}`, { replace: true });
            }
          },
          onError: (err) => {
            toast.error(err.message);
            cancelEditing();
          },
        },
      );
    },
    [renameMutation, navigate, cancelEditing],
  );

  const renameCtx = useMemo<TreeRenameCtx>(
    () => ({ editingId, editValueRef, startEditing, commitRename, cancelEditing }),
    [editingId, startEditing, commitRename, cancelEditing],
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full text-text-muted text-sm">
        Loading...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-3 text-sm text-text-secondary">
        Failed to load file tree.
      </div>
    );
  }

  return (
    <RenameContext.Provider value={renameCtx}>
    <div className="flex flex-col h-full bg-ui-element-bg/50">
      {/* Header + search (AC-07) */}
      <div className="p-2 border-b border-dashed border-ui-border space-y-2">
        <div className="flex items-center justify-between px-1">
          <span className="text-xs font-medium text-text-muted uppercase tracking-wider">Vault</span>
          <NewItemDropdown />
        </div>
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-muted" />
          <input
            type="text"
            placeholder="search files & content"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-7 pr-2 py-1.5 text-xs rounded-md bg-ui-bg border border-dashed border-ui-border text-text-primary placeholder:text-text-muted focus:outline-none focus:border-brand-primary transition-colors"
          />
        </div>
      </div>

      {/* Pinned: today.md (AC-08) */}
      {todayNode && (!search || todayNode.name.toLowerCase().includes(search.toLowerCase())) && (
        <div className="px-2 pt-2">
          <button
            onClick={() => navigate('/')}
            className={`flex items-center gap-2 w-full px-2 py-1.5 text-sm rounded-md transition-colors ${
              selectedId === 'today.md'
                ? 'bg-accent-surface text-text-accent'
                : 'text-text-secondary hover:bg-ui-interactive-bg-hover hover:text-text-primary'
            }`}
          >
            <HomeIcon className="h-4 w-4 flex-shrink-0" />
            <span className="font-medium">today.md</span>
          </button>
        </div>
      )}

      {/* Main tree */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {filteredRest.length > 0 && (
          <Tree
            data={filteredRest}
            openByDefault={false}
            width="100%"
            indent={16}
            rowHeight={28}
            onActivate={handleActivate}
            selection={selectedId}
          >
            {NodeRenderer}
          </Tree>
        )}
      </div>

      {/* Pinned: _workflows section (AC-09) — always visible */}
      <div className="border-t border-dashed border-ui-border">
        <div className="px-3 py-1.5 text-xs font-medium text-text-muted uppercase tracking-wider">
          Pinned Workflows
        </div>
        <div className="px-2 pb-2 space-y-0.5">
          {filteredWorkflows.length > 0 ? (
            filteredWorkflows.map((wf) => (
              <button
                key={wf.id}
                onClick={() => navigate(`/vault/${wf.vaultPath}`)}
                className={`flex items-center gap-2 w-full px-2 py-1 text-sm rounded-md transition-colors ${
                  selectedId === wf.vaultPath
                    ? 'bg-accent-surface text-text-accent'
                    : 'text-text-secondary hover:bg-ui-interactive-bg-hover hover:text-text-primary'
                }`}
              >
                <GearIcon className="h-3.5 w-3.5 flex-shrink-0" />
                <span className="truncate">{wf.name}</span>
              </button>
            ))
          ) : (
            <p className="px-2 py-1 text-xs text-text-muted italic">No workflows yet</p>
          )}
          <button
            onClick={() => navigate('/vault/_workflows/')}
            data-testid="tree-new-workflow"
            className="flex items-center gap-1.5 w-full px-2 py-1 text-xs text-brand-primary hover:bg-ui-interactive-bg-hover rounded-md transition-colors"
          >
            <span className="text-sm leading-none">+</span>
            <span>New workflow</span>
          </button>
        </div>
      </div>

    </div>
    </RenameContext.Provider>
  );
};
