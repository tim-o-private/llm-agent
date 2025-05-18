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
import { UseQueryResult, UseMutationResult } from '@tanstack/react-query';

// --- Generic Type Definitions ---
// TItem: The type of the items in the list.
// TNewItemData: The type of the data payload for creating new items.

// --- Hook Options Interface ---
export interface ReorderableListOptions<
  TItem extends { id: UniqueIdentifier }, // Ensure TItem has an id compatible with dnd-kit
  TNewItemData // Type for creating a new item
> {
  listName: string; // For logging and potentially for cache keys or context identification
  parentObjectId: string | null; // ID of the parent object this list belongs to, if any

  // Data Hooks
  fetchListQueryHook: (parentId: string | null) => UseQueryResult<TItem[], Error>;
  // Mutation for updating the order of items. Payload includes all items with their new positions.
  updateOrderMutationHook: () => UseMutationResult<
    TItem[], // Expected response: updated list or success indicator
    Error,
    { parentId: string | null; orderedItems: Array<{ id: UniqueIdentifier; position: number } & Partial<TItem>> },
    unknown
  >;
  // Mutation for creating a new item in the list.
  createItemMutationHook?: () => UseMutationResult<
    TItem, // Expected response: the newly created item
    Error,
    { parentId: string | null; newItem: TNewItemData; position?: number }, // position might be auto-assigned or specified
    unknown
  >;

  // Item Configuration & Behavior
  getItemId: (item: TItem) => UniqueIdentifier;
  // Optional: If items have an explicit position field that needs to be managed.
  // If not provided, order is based on array index.
  getItemPosition?: (item: TItem) => number;
  // Optional: Logic to determine the position for a new item.
  // Defaults to end of the list if not provided.
  getNewItemPosition?: (items: TItem[], newItemData: TNewItemData) => number;

  // Callbacks
  onReorderCommit?: (reorderedItems: TItem[]) => void; // After successful backend update of order
  onItemAdded?: (newItem: TItem) => void; // After successful creation of an item
  onFetchError?: (error: Error) => void;
  // Potentially callbacks for onItemEdit, onItemDelete if those operations are integrated here
}

// --- Hook Result Interface ---
export interface ReorderableListResult<TItem extends { id: UniqueIdentifier }, TNewItemData> {
  items: TItem[]; // Current list of items (reflects optimistic updates if any)
  isLoading: boolean; // True if fetching initial list or if a mutation is in progress
  isFetching: boolean; // True if fetching initial list specifically
  isUpdatingOrder: boolean; // True if updateOrderMutation is in progress
  isAddingItem: boolean; // True if createItemMutation is in progress
  error: Error | null; // Fetching or mutation error

  // Dnd-kit related props to be used by the consuming component
  dndSensors: ReturnType<typeof useSensors>;
  handleDragStart: (event: DragStartEvent) => void;
  handleDragEnd: (event: DragEndEvent) => void;
  activeDragItem: TItem | null; // The item currently being dragged

  // Item Actions
  handleAddItem?: (newItemData: TNewItemData) => Promise<TItem | undefined>; // If createItemMutationHook is provided
  
  // Allows manual refetching of the list
  refetchList: () => void;
}

export function useReorderableList<
  TItem extends { id: UniqueIdentifier },
  TNewItemData
>(
  options: ReorderableListOptions<TItem, TNewItemData>
): ReorderableListResult<TItem, TNewItemData> {
  const {
    listName,
    parentObjectId,
    fetchListQueryHook,
    updateOrderMutationHook,
    createItemMutationHook,
    getItemId,
    getItemPosition, // May not be used if order is implicit by array index in display
    getNewItemPosition,
    onReorderCommit,
    onItemAdded,
    onFetchError,
  } = options;

  // const queryClient = useQueryClient(); // Remove unused queryClient

  // --- Dnd-kit Sensor Setup ---
  const dndSensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // --- Data Fetching ---
  const { 
    data: fetchedItems = [], // Default to empty array if data is undefined
    isLoading: isFetchingItems, 
    error: fetchError, 
    refetch: refetchList 
  } = fetchListQueryHook(parentObjectId);

  // --- Internal State for Optimistic Updates & Drag State ---
  // `displayItems` is what gets rendered. It reflects optimistic updates immediately.
  const [displayItems, setDisplayItems] = useState<TItem[]>(fetchedItems);
  const [activeDragItemId, setActiveDragItemId] = useState<UniqueIdentifier | null>(null); // Store ID of active drag item

  // Sync displayItems with fetchedItems when fetchedItems changes (e.g., after a refetch not triggered by optimistic update)
  useEffect(() => {
    console.log(`[${listName}ListManager] Fetched items updated. Length: ${fetchedItems.length}`);
    setDisplayItems(fetchedItems);
  }, [fetchedItems, listName]);

  // --- Mutations ---
  const updateOrderMutation = updateOrderMutationHook();
  const createItemMutation = createItemMutationHook ? createItemMutationHook() : null;

  // --- Combined Loading and Error States ---
  const isUpdatingOrder = updateOrderMutation.isPending;
  const isAddingItem = createItemMutation?.isPending ?? false;
  const isLoading = isFetchingItems || isUpdatingOrder || isAddingItem;
  const mutationError = updateOrderMutation.error || createItemMutation?.error || null;
  const error = fetchError || mutationError;

  // Effect to call onFetchError if fetchError occurs
  useEffect(() => {
    if (fetchError && onFetchError) {
      onFetchError(fetchError);
    }
  }, [fetchError, onFetchError]);

  // --- Drag and Drop Handlers ---
  const handleDragStartInternal = (event: DragStartEvent) => { 
    const { active } = event;
    console.log(`[${listName}ListManager] Drag Start. Active ID: ${active.id}`);
    setActiveDragItemId(active.id);
  };

  // Memoize activeDragItem based on activeDragItemId and displayItems
  const activeDragItem = useMemo(() => {
    if (!activeDragItemId) return null;
    const item = displayItems.find(i => getItemId(i) === activeDragItemId);
    console.log(`[${listName}ListManager] Active drag item derived: ${item ? getItemId(item) : null}`);
    return item || null;
  }, [activeDragItemId, displayItems, getItemId, listName]);

  const handleDragEndInternal = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveDragItemId(null); // Clear active item on drag end
    console.log(`[${listName}ListManager] Drag End. Active ID: ${active.id}, Over ID: ${over?.id}. Active item cleared.`);

    if (over && active.id !== over.id) {
      const oldIndex = displayItems.findIndex((item) => getItemId(item) === active.id);
      const newIndex = displayItems.findIndex((item) => getItemId(item) === over.id);

      if (oldIndex === -1 || newIndex === -1) {
        console.warn(`[${listName}ListManager] DragEnd: Item not found in list. Active: ${active.id}, Over: ${over.id}`);
        return;
      }

      const reorderedItems = arrayMove(displayItems, oldIndex, newIndex);
      setDisplayItems(reorderedItems); // Optimistic UI update
      console.log(`[${listName}ListManager] Optimistically reordered items.`);

      // Prepare payload for mutation: array of {id, position} objects
      const itemsWithNewPositions = reorderedItems.map((item, index) => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { id, ...restOfItem } = item; // Destructure to avoid id collision if TItem has more than just id and position
        return {
          id: getItemId(item), // Use the definitive id from getItemId
          position: getItemPosition ? getItemPosition(item) : index + 1, // Use explicit position if available, else index
          ...restOfItem, // Spread the rest of the item properties
        };
      });

      updateOrderMutation.mutate(
        // Ensure the payload matches the expected type for the mutation hook
        { parentId: parentObjectId, orderedItems: itemsWithNewPositions as Array<{ id: UniqueIdentifier; position: number } & Partial<TItem>> }, 
        {
          onSuccess: (dataFromServer) => {
            console.log(`[${listName}ListManager] Update order successful.`, dataFromServer);
            if (onReorderCommit) onReorderCommit(dataFromServer || reorderedItems); 
          },
          onError: (err) => {
            console.error(`[${listName}ListManager] Update order failed:`, err);
            setDisplayItems(fetchedItems); 
          },
        }
      );
    }
  };
  
  // --- Add Item Handler ---
  const handleAddItem = useCallback(async (newItemData: TNewItemData): Promise<TItem | undefined> => {
    if (!createItemMutation) {
      console.error(`[${listName}ListManager] Add item called but no createItemMutationHook provided.`);
      return undefined;
    }

    const currentItems = displayItems || fetchedItems || [];
    const position = getNewItemPosition 
      ? getNewItemPosition(currentItems, newItemData) 
      : currentItems.length + 1;

    try {
      console.log(`[${listName}ListManager] Attempting to add item. ParentID: ${parentObjectId}, Position: ${position}`, newItemData);
      const addedItem = await createItemMutation.mutateAsync({ parentId: parentObjectId, newItem: newItemData, position });
      console.log(`[${listName}ListManager] Add item successful.`, addedItem);
      
      if (onItemAdded) {
        onItemAdded(addedItem);
      }
      refetchList(); 
      return addedItem;
    } catch (err) {
      console.error(`[${listName}ListManager] Add item failed:`, err);
      return undefined;
    }
  }, [createItemMutation, displayItems, fetchedItems, getNewItemPosition, onItemAdded, parentObjectId, listName, refetchList]);


  // --- Return Values ---
  return {
    items: displayItems, // Render this list
    isLoading,
    isFetching: isFetchingItems,
    isUpdatingOrder,
    isAddingItem,
    error,
    dndSensors,
    handleDragStart: handleDragStartInternal,
    handleDragEnd: handleDragEndInternal,
    activeDragItem,
    handleAddItem: createItemMutationHook ? handleAddItem : undefined,
    refetchList,
  };
} 