import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  DragEndEvent,
  DragStartEvent,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  UniqueIdentifier,
} from '@dnd-kit/core';
import { arrayMove, sortableKeyboardCoordinates } from '@dnd-kit/sortable';

// --- Generic Type Definitions ---
// TItem: The type of the items in the list.
// TNewItemData: The type of the data payload for creating new items.

// --- Hook Options Interface ---
export interface ReorderableListOptions<TItem extends { id: UniqueIdentifier }> {
  listName: string; 
  initialItems: TItem[];
  getItemId: (item: TItem) => UniqueIdentifier;
  // getItemPosition?: (item: TItem) => number; // Removed as it's not used by the current DND/local management logic
}

// --- Hook Result Interface ---
export interface ReorderableListResult<TItem extends { id: UniqueIdentifier }> {
  items: TItem[]; 
  dndSensors: ReturnType<typeof useSensors>;
  handleDragStart: (event: DragStartEvent) => void;
  handleDragEnd: (event: DragEndEvent, callback?: (reorderedItems: TItem[]) => void) => void; 
  activeDragItem: TItem | null; 
  handleLocalAddItem: (newItem: TItem) => void; 
  handleLocalRemoveItem: (itemId: UniqueIdentifier) => void;
  handleLocalUpdateItem: (itemId: UniqueIdentifier, updates: Partial<TItem>) => void;
  setItems: React.Dispatch<React.SetStateAction<TItem[]>>; 
}

export function useReorderableList<
  TItem extends { id: UniqueIdentifier }
>(
  options: ReorderableListOptions<TItem>
): ReorderableListResult<TItem> {
  const {
    listName,
    initialItems,
    getItemId,
  } = options;

  const dndSensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );
 
  const [items, setItems] = useState<TItem[]>(initialItems);
  const [activeDragItemId, setActiveDragItemId] = useState<UniqueIdentifier | null>(null);

  useEffect(() => {
    console.log(`[${listName}ListManager] Initial items updated. Length: ${initialItems.length}`);
    setItems(initialItems);
  }, [initialItems, listName]);

  const handleDragStartInternal = (event: DragStartEvent) => { 
    const { active } = event;
    setActiveDragItemId(active.id);
  };

  const activeDragItem = useMemo(() => {
    if (!activeDragItemId) return null;
    return items.find(i => getItemId(i) === activeDragItemId) || null;
  }, [activeDragItemId, items, getItemId]);

  const handleDragEndInternal = (event: DragEndEvent, callback?: (reorderedItems: TItem[]) => void) => {
    const { active, over } = event;
    setActiveDragItemId(null); 

    if (over && active.id !== over.id) {
      const oldIndex = items.findIndex((item) => getItemId(item) === active.id);
      const newIndex = items.findIndex((item) => getItemId(item) === over.id);

      if (oldIndex === -1 || newIndex === -1) {
        return;
      }

      const reorderedItems = arrayMove(items, oldIndex, newIndex);
      setItems(reorderedItems); 
      if (callback) callback(reorderedItems); 
    }
  };
  
  const handleLocalAddItem = useCallback((newItem: TItem) => {
    setItems(prevItems => [...prevItems, newItem]);
  }, []);

  const handleLocalRemoveItem = useCallback((itemId: UniqueIdentifier) => {
    setItems(prevItems => prevItems.filter(item => getItemId(item) !== itemId));
  }, [getItemId]);

  const handleLocalUpdateItem = useCallback((itemId: UniqueIdentifier, updates: Partial<TItem>) => {
    setItems(prevItems => 
      prevItems.map(item => 
        getItemId(item) === itemId ? { ...item, ...updates } : item
      )
    );
  }, [getItemId]);

  return {
    items,
    dndSensors,
    handleDragStart: handleDragStartInternal,
    handleDragEnd: handleDragEndInternal,
    activeDragItem,
    handleLocalAddItem,
    handleLocalRemoveItem,
    handleLocalUpdateItem,
    setItems,
  };
} 