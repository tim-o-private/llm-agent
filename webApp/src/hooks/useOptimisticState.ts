import { useState, useCallback } from 'react';

export interface PendingChanges<T> {
  creates: Array<Partial<T>>;
  updates: Array<{ id: string; updates: Partial<T> }>;
  deletes: Array<string>;
  reorders: Array<{ items: T[] }>;
}

export interface OptimisticStateHook<T> {
  optimisticItems: T[] | null;
  pendingChanges: PendingChanges<T>;
  isDirty: boolean;
  
  // Actions
  setOptimisticItems: (items: T[] | null) => void;
  handleCreate: (item: Partial<T>, tempIdGenerator: () => string, itemFactory: (data: Partial<T>, tempId: string) => T) => void;
  handleUpdate: (id: string, updates: Partial<T>) => void;
  handleDelete: (id: string) => void;
  handleReorder: (reorderedItems: T[]) => void;
  
  // State management
  clearPendingChanges: () => void;
  resetState: () => void;
}

export function useOptimisticState<T extends { id: string }>(
  getStoreItems: () => T[]
): OptimisticStateHook<T> {
  const [optimisticItems, setOptimisticItems] = useState<T[] | null>(null);
  const [pendingChanges, setPendingChanges] = useState<PendingChanges<T>>({
    creates: [],
    updates: [],
    deletes: [],
    reorders: [],
  });

  const isDirty = pendingChanges.creates.length > 0 || 
                  pendingChanges.updates.length > 0 || 
                  pendingChanges.deletes.length > 0 || 
                  pendingChanges.reorders.length > 0;

  const handleCreate = useCallback((
    itemData: Partial<T>, 
    tempIdGenerator: () => string,
    itemFactory: (data: Partial<T>, tempId: string) => T
  ) => {
    // Add to pending changes
    setPendingChanges(prev => ({
      ...prev,
      creates: [...prev.creates, itemData],
    }));

    // Update optimistic state
    const currentItems = optimisticItems || getStoreItems();
    const tempId = tempIdGenerator();
    const newItem = itemFactory(itemData, tempId);
    setOptimisticItems([...currentItems, newItem]);
  }, [optimisticItems, getStoreItems]);

  const handleUpdate = useCallback((id: string, updates: Partial<T>) => {
    // Add to pending changes
    setPendingChanges(prev => ({
      ...prev,
      updates: [...prev.updates.filter(u => u.id !== id), { id, updates }],
    }));

    // Update optimistic state
    const currentItems = optimisticItems || getStoreItems();
    const updatedItems = currentItems.map(item => 
      item.id === id ? { ...item, ...updates } : item
    );
    setOptimisticItems(updatedItems);
  }, [optimisticItems, getStoreItems]);

  const handleDelete = useCallback((id: string) => {
    // Add to pending changes
    setPendingChanges(prev => ({
      ...prev,
      deletes: [...prev.deletes, id],
    }));

    // Update optimistic state
    const currentItems = optimisticItems || getStoreItems();
    const filteredItems = currentItems.filter(item => item.id !== id);
    setOptimisticItems(filteredItems);
  }, [optimisticItems, getStoreItems]);

  const handleReorder = useCallback((reorderedItems: T[]) => {
    // Set optimistic state for immediate UI feedback
    setOptimisticItems(reorderedItems);
    
    // Add to pending changes
    setPendingChanges(prev => ({
      ...prev,
      reorders: [{ items: reorderedItems }], // Replace with latest reorder
    }));
  }, []);

  const clearPendingChanges = useCallback(() => {
    setPendingChanges({
      creates: [],
      updates: [],
      deletes: [],
      reorders: [],
    });
    setOptimisticItems(null);
  }, []);

  const resetState = useCallback(() => {
    setOptimisticItems(null);
    setPendingChanges({
      creates: [],
      updates: [],
      deletes: [],
      reorders: [],
    });
  }, []);

  return {
    optimisticItems,
    pendingChanges,
    isDirty,
    setOptimisticItems,
    handleCreate,
    handleUpdate,
    handleDelete,
    handleReorder,
    clearPendingChanges,
    resetState,
  };
} 