import { UseFormReturn, FieldValues, Path, PathValue, useForm } from 'react-hook-form';
import { ZodSchema } from 'zod';
import { DragEndEvent, DndContextProps as CoreDndContextProps, useSensors, useSensor, PointerSensor, KeyboardSensor } from '@dnd-kit/core';
import { sortableKeyboardCoordinates, arrayMove } from '@dnd-kit/sortable'; // Import arrayMove
import { useState, useEffect, useCallback, useMemo } from 'react';
// Placeholder for a robust deep clone and deep equal utility
// You might use lodash, rfdc, fast-deep-equal, etc.
import { cloneDeep, isEqual } from 'lodash-es';
import { zodResolver } from '@hookform/resolvers/zod'; // Assuming zod resolver is installed

// --- Core Type Definitions (from creative-useEditableEntity-design.md) ---

// TEntityData: The complete data structure of the entity as fetched/saved.
// TFormData: The structure for the main entity's form (React Hook Form).
// TSubEntityCollectionData: The raw data for the collection of sub-entities if path is used.
// TSubEntityListItemData: The structure for a single item in the managed sub-entity list.
// TSubEntityListItemFormInputData: Data structure for editing/creating a single sub-entity item's form.

export interface EntityTypeConfig<
  TEntityData,
  TFormData extends FieldValues,
  TSubEntityListItemData = Record<string, any>,
  TSubEntityListItemFormInputData extends FieldValues = FieldValues,
> {
  entityId: string | null | undefined;
  queryHook: (id: string | null | undefined) => {
    data: TEntityData | undefined;
    isLoading: boolean;
    isFetching: boolean;
    error: any;
    // refetch?: () => void; // Consider if needed
  };

  transformDataToForm: (entityData: TEntityData | undefined) => TFormData; // Allow undefined for create mode
  formSchema?: ZodSchema<TFormData>;
  
  // Optional: Provide initial form data for 'create' mode if transformDataToForm needs it
  // Or, transformDataToForm should handle undefined entityData to return default TFormData
  // createEmptyFormData?: () => TFormData; 


  subEntityPath?: Path<TEntityData>;
  transformSubCollectionToList?: (
    // Accepts either the extracted sub-collection OR the parent entity itself if subEntityPath is not defined
    dataForSubList: PathValue<TEntityData, Path<TEntityData>> | TEntityData | undefined
  ) => TSubEntityListItemData[];
  subEntityListItemIdField: keyof TSubEntityListItemData;
  createEmptySubEntityListItem?: () => TSubEntityListItemData | TSubEntityListItemFormInputData;
  // isSubEntityItemDirty?: (originalItem: TSubEntityListItemData, currentItem: TSubEntityListItemData) => boolean;

  saveHandler: (
    originalEntity: TEntityData | null,
    currentFormData: TFormData,
    currentSubEntityList: TSubEntityListItemData[] | undefined,
  ) => Promise<TEntityData | void>;

  isDataEqual?: (a: any, b: any) => boolean;
  cloneData?: <T>(data: T) => T;

  onSaveSuccess?: (savedEntity: TEntityData) => void;
  onSaveError?: (error: any) => void;
  onCancel?: () => void;
  onDirtyStateChange?: (isDirty: boolean) => void;

  enableSubEntityReordering?: boolean;
  // dndSensors?: SensorDescriptor[];
}

export interface UseEditableEntityResult<
  TEntityData,
  TFormData extends FieldValues,
  TSubEntityListItemData = any,
> {
  originalEntity: TEntityData | null;
  currentEntityDataForForm: TFormData | undefined; // This might be redundant if formMethods.getValues() is always used
  isLoading: boolean;
  isFetching: boolean;
  error: any | null;

  formMethods: UseFormReturn<TFormData>;
  isMainFormDirty: boolean;

  subEntityList: TSubEntityListItemData[];
  isSubEntityListDirty: boolean;
  addSubItem: (newItemData: TSubEntityListItemData) => void; // Or TSubEntityListItemFormInputData
  updateSubItem: (
    id: string | number, 
    updatedItemData: Partial<TSubEntityListItemData> | ((prev: TSubEntityListItemData) => TSubEntityListItemData)
  ) => void;
  removeSubItem: (id: string | number) => void;

  isDirty: boolean;
  isSaving: boolean;

  handleSave: () => Promise<void>;
  handleCancel: () => void;
  resetState: (newEntityData?: TEntityData) => void;

  dndContextProps?: Pick<CoreDndContextProps, 'sensors' | 'onDragEnd' | 'modifiers' | 'collisionDetection'>;
  getSortableListProps: () => {
    items: Array<TSubEntityListItemData & { id: string | number }>;
    // Potentially other props for a generic sortable list component
  };
}

// --- Main Hook Function ---

export function useEditableEntity<
  TEntityData,
  TFormData extends FieldValues,
  TSubEntityListItemData extends Record<string, any> = Record<string, any>,
  TSubEntityListItemFormInputData extends FieldValues = FieldValues
>(
  config: EntityTypeConfig<
    TEntityData,
    TFormData,
    TSubEntityListItemData,
    TSubEntityListItemFormInputData
  >
): UseEditableEntityResult<TEntityData, TFormData, TSubEntityListItemData> {
  
  const {
    entityId,
    queryHook,
    transformDataToForm,
    formSchema, // Destructure formSchema
    saveHandler, // Destructure saveHandler
    onSaveSuccess,
    onSaveError,
    onCancel,
    onDirtyStateChange, // Destructure for later use
    subEntityPath, // Destructure
    transformSubCollectionToList, // Destructure
    subEntityListItemIdField, // Destructure
    // createEmptySubEntityListItem, // Destructure
    enableSubEntityReordering, // Destructure
    cloneData = cloneDeep, // Default cloneDeep
    isDataEqual = isEqual, // Default isEqual
  } = config;

  // Step 9.2.2: Implement Data Fetching & State Initialization (Skeleton)
  const [originalEntitySnapshot, setOriginalEntitySnapshot] = useState<TEntityData | null>(null);
  const [isLoadingState, setIsLoadingState] = useState<boolean>(true); // Initial loading
  const [isFetchingState, setIsFetchingState] = useState<boolean>(false); // Subsequent fetching
  const [errorState, setErrorState] = useState<any | null>(null);
  const [isSavingState, setIsSavingState] = useState<boolean>(false);

  // State for the original snapshot of the sub-entity list
  const [originalSubEntityListSnapshot, setOriginalSubEntityListSnapshot] = useState<TSubEntityListItemData[]>([]);

  // Step 9.2.3: Integrate React Hook Form (RHF) for Main Entity
  const formMethods = useForm<TFormData>({
    resolver: formSchema ? zodResolver(formSchema) : undefined,
    defaultValues: transformDataToForm(undefined) as any, // Initial empty state or default, will be reset
  });

  // Step 9.3.1: Initialize Sub-Entity State (Skeleton)
  const [internalSubEntityList, setInternalSubEntityList] = useState<TSubEntityListItemData[]>([]);
  const [isSubEntityListDirtyState, setIsSubEntityListDirtyState] = useState<boolean>(false);
  
  // Placeholder for RHF - will be properly set up in useEffect
  // const formMethodsHook = {} as UseFormReturn<TFormData>; 


  // --- Effect for data fetching and initialization ---
  useEffect(() => {
    const queryResult = queryHook(entityId); // Call queryHook once at the start of the effect.

    // Update loading states based on the queryHook's immediate return
    setIsLoadingState(queryResult.isLoading);
    setIsFetchingState(queryResult.isFetching);

    if (queryResult.error) {
      setErrorState(queryResult.error);
      setOriginalEntitySnapshot(null);
      formMethods.reset(transformDataToForm(undefined));
      setInternalSubEntityList([]);
      setOriginalSubEntityListSnapshot([]);
    } else if (!queryResult.isLoading && !queryResult.isFetching) {
      if (queryResult.data) {
        const newSnapshot = cloneData(queryResult.data);
        setOriginalEntitySnapshot(newSnapshot);
        formMethods.reset(transformDataToForm(queryResult.data));

        if (transformSubCollectionToList) {
          const dataForSubList = subEntityPath 
            ? getPathValue(queryResult.data, subEntityPath as string) 
            : queryResult.data;
          
          console.log('[useEditableEntity CHANGED_LOGIC] Calling transformSubCollectionToList with dataForSubList:', dataForSubList);
          try {
            const transformedSubList = transformSubCollectionToList(dataForSubList) || [];
            console.log('[useEditableEntity CHANGED_LOGIC] transformSubCollectionToList returned:', transformedSubList);
            setInternalSubEntityList(transformedSubList);
            setOriginalSubEntityListSnapshot(cloneData(transformedSubList));
          } catch (e) {
            console.error('[useEditableEntity CHANGED_LOGIC] Error calling transformSubCollectionToList:', e);
            setInternalSubEntityList([]);
            setOriginalSubEntityListSnapshot([]);
          }
        } else {
          console.log('[useEditableEntity CHANGED_LOGIC] No transformSubCollectionToList, setting sublist to [].');
          setInternalSubEntityList([]);
          setOriginalSubEntityListSnapshot([]);
        }
        setErrorState(null);
      } else {
        setOriginalEntitySnapshot(null);
        formMethods.reset(transformDataToForm(undefined));
        setInternalSubEntityList([]);
        setOriginalSubEntityListSnapshot([]);
        if (entityId) {
          setErrorState(new Error(`Entity with ID '${entityId}' not found.`));
        } else {
          setErrorState(null);
        }
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    entityId, 
    queryHook, 
    transformDataToForm, 
    cloneData, 
    formMethods,
    subEntityPath, 
    transformSubCollectionToList
  ]);

  // Step 9.3.3: Implement Sub-Entity Dirty Checking
  useEffect(() => {
    // Compare internalSubEntityList with originalSubEntityListSnapshot directly
    if (!isDataEqual(internalSubEntityList, originalSubEntityListSnapshot)) {
        setIsSubEntityListDirtyState(true);
    } else {
        setIsSubEntityListDirtyState(false);
    }
  }, [internalSubEntityList, originalSubEntityListSnapshot, isDataEqual]);


  // Step 9.2.4: Combined Dirty Check
  const isMainFormDirty = formMethods.formState.isDirty;
  const combinedIsDirty = isMainFormDirty || isSubEntityListDirtyState;

  // Notify on dirty state change
  useEffect(() => {
    if (onDirtyStateChange) {
      onDirtyStateChange(combinedIsDirty);
    }
  }, [combinedIsDirty, onDirtyStateChange]);

  // Step 9.2.5: Implement handleSave
  const handleSave = useCallback(async () => {
    setErrorState(null);
    setIsSavingState(true);
    try {
      const currentFormData = formMethods.getValues();
      // Ensure originalEntitySnapshot is correctly passed
      const snapshotForSave = originalEntitySnapshot;
      const savedEntityOrVoid = await saveHandler(
        snapshotForSave, // Use the captured snapshot
        currentFormData,
        internalSubEntityList // Pass current sub-entity list
      );

      if (savedEntityOrVoid) { 
        const newSnapshot = cloneData(savedEntityOrVoid as TEntityData);
        setOriginalEntitySnapshot(newSnapshot);
        formMethods.reset(transformDataToForm(savedEntityOrVoid as TEntityData));
        // Re-initialize sub-entity list from newSnapshot (9.3.4)
        if (subEntityPath && transformSubCollectionToList) {
          const rawSubCollection = getPathValue(newSnapshot, subEntityPath);
          const transformedSubList = transformSubCollectionToList(rawSubCollection) || [];
          setInternalSubEntityList(transformedSubList);
          setOriginalSubEntityListSnapshot(cloneData(transformedSubList)); // Set sub-list snapshot
        } else {
          setInternalSubEntityList([]);
          setOriginalSubEntityListSnapshot([]); // Reset sub-list snapshot
        }
        if (onSaveSuccess) {
          onSaveSuccess(savedEntityOrVoid as TEntityData);
        }
      } else { // If saveHandler returns void, assume data is refetched or managed by caller
        // We should refetch or trust the external update. For now, just reset RHF dirty state.
        // A more robust approach might involve a refetch from queryHook or new data from saveHandler
        formMethods.reset(formMethods.getValues()); // Resets dirty state but keeps current values
        // originalEntitySnapshot remains unchanged if saveHandler returns void.
        if (onSaveSuccess) {
          // Pass the snapshot that was used for the save operation if no new entity is returned.
          onSaveSuccess(snapshotForSave as TEntityData); 
        }
      }
    } catch (e) {
      setErrorState(e);
      if (onSaveError) {
        onSaveError(e);
      }
    } finally {
      setIsSavingState(false);
    }
  }, [formMethods, saveHandler, originalEntitySnapshot, cloneData, transformDataToForm, onSaveSuccess, onSaveError, internalSubEntityList, subEntityPath, transformSubCollectionToList]); // Added subEntityPath and transformSubCollectionToList to handleSave deps as they are used for re-initializing sub-list

  // Step 9.2.6: Implement handleCancel & resetState
  const internalResetState = useCallback((newEntityData?: TEntityData) => {
    setErrorState(null);
    let subListToReset: TSubEntityListItemData[] = [];
    let formValuesToReset: TFormData;

    if (newEntityData !== undefined) {
        const newSnapshot = cloneData(newEntityData);
        setOriginalEntitySnapshot(newSnapshot);
        formValuesToReset = transformDataToForm(newSnapshot);
        if (subEntityPath && transformSubCollectionToList) {
            const rawSubCollection = getPathValue(newSnapshot, subEntityPath);
            subListToReset = transformSubCollectionToList(rawSubCollection) || [];
        }
        setOriginalSubEntityListSnapshot(cloneData(subListToReset)); 
    } else if (originalEntitySnapshot) { 
        formValuesToReset = transformDataToForm(originalEntitySnapshot);
        subListToReset = cloneData(originalSubEntityListSnapshot); // Use the dedicated sub-list snapshot
    } else { 
        formValuesToReset = transformDataToForm(undefined); 
        setOriginalSubEntityListSnapshot([]); 
    }
    formMethods.reset(formValuesToReset);
    setInternalSubEntityList(subListToReset);
  }, [
    cloneData, formMethods, originalEntitySnapshot, transformDataToForm,
    subEntityPath, transformSubCollectionToList, originalSubEntityListSnapshot // Include originalSubEntityListSnapshot in deps
  ]);

  const handleCancel = useCallback(() => {
    internalResetState(); // Reset to original snapshot or empty
    if (onCancel) {
      onCancel();
    }
  }, [internalResetState, onCancel]);

  const resetState = useCallback((newEntityData?: TEntityData) => {
    internalResetState(newEntityData);
  }, [internalResetState]);

  // Step 9.3.2: Implement Sub-Entity CRUD Operations
  const addSubItem = useCallback((newItemData: TSubEntityListItemData | TSubEntityListItemFormInputData) => {
    // If createEmptySubEntityListItem is more about transforming form input to list item data,
    // the newItemData passed here should ideally be TSubEntityListItemData.
    // Or, this function could take TSubEntityListItemFormInputData and use a transform function.
    // For simplicity now, assume newItemData is of TSubEntityListItemData or compatible.
    setInternalSubEntityList(prevList => [...prevList, newItemData as TSubEntityListItemData]);
  }, []);

  const updateSubItem = useCallback((itemId: string | number, updatedDataOrFn: Partial<TSubEntityListItemData> | ((prev: TSubEntityListItemData) => TSubEntityListItemData)) => {
    if (!subEntityListItemIdField) {
      console.error("updateSubItem: subEntityListItemIdField is not configured.");
      return;
    }
    setInternalSubEntityList(prevList => 
      prevList.map((item: TSubEntityListItemData) => { // Explicitly type item
        if (String(item[subEntityListItemIdField]) === String(itemId)) {
          if (typeof updatedDataOrFn === 'function') {
            return updatedDataOrFn(item);
          }
          return { ...item, ...updatedDataOrFn };
        }
        return item;
      })
    );
  }, [subEntityListItemIdField]);

  const removeSubItem = useCallback((itemId: string | number) => {
    if (!subEntityListItemIdField) {
      console.error("removeSubItem: subEntityListItemIdField is not configured.");
      return;
    }
    setInternalSubEntityList(prevList => 
      prevList.filter((item: TSubEntityListItemData) => String(item[subEntityListItemIdField]) !== String(itemId)) // Explicitly type item
    );
  }, [subEntityListItemIdField]);

  // Step 9.3.6: Implement dnd-kit Integration
  const dndSensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;

    // Prevent default actions and stop propagation to avoid unintended side effects
    // For example, if dragging text, it might try to do a browser drag-n-drop action.
    if (event.originalEvent) {
        event.originalEvent.preventDefault();
        event.originalEvent.stopPropagation();
    }

    if (over && active.id !== over.id) {
      setInternalSubEntityList((items: TSubEntityListItemData[]) => { 
        const oldIndex = items.findIndex((item: TSubEntityListItemData) => String(item[subEntityListItemIdField]) === String(active.id));
        const newIndex = items.findIndex((item: TSubEntityListItemData) => String(item[subEntityListItemIdField]) === String(over.id)); 
        if (oldIndex === -1 || newIndex === -1) {
          console.warn('[useEditableEntity] DragEnd: कुड नॉट फाइंड आइटम इंडेक्स.', { activeId: active.id, overId: over.id, oldIndex, newIndex });
          return items; // Return original items if something is wrong
        }
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  }, [subEntityListItemIdField]);

  const dndContextProps = useMemo(() => {
    if (!enableSubEntityReordering) return undefined;
    return {
      sensors: dndSensors,
      onDragEnd: handleDragEnd,
      // modifiers: ..., // Add if needed
      // collisionDetection: closestCenter, // Add if needed
    };
  }, [enableSubEntityReordering, dndSensors, handleDragEnd]);

  const getSortableListProps = useCallback(() => {
    if (!enableSubEntityReordering || !subEntityListItemIdField) {
        // Ensure it always returns items, even if empty, to prevent destructuring errors in consumer.
        return { items: [] }; 
    }
    return {
      items: internalSubEntityList.map((item: TSubEntityListItemData) => ({ // Explicitly type item
        ...item,
        id: String(item[subEntityListItemIdField]), // Ensure id is a string for dnd-kit consistency
      })),
    };
  }, [internalSubEntityList, enableSubEntityReordering, subEntityListItemIdField]);


  // --- Placeholder return structure ---
  return {
    originalEntity: originalEntitySnapshot,
    currentEntityDataForForm: undefined, // placeholder
    isLoading: isLoadingState,
    isFetching: isFetchingState,
    error: errorState,
    formMethods: formMethods, // Use the actual formMethods instance
    isMainFormDirty: isMainFormDirty,
    subEntityList: internalSubEntityList,
    isSubEntityListDirty: isSubEntityListDirtyState,
    addSubItem: addSubItem, // Expose CRUD
    updateSubItem: updateSubItem,
    removeSubItem: removeSubItem,
    isDirty: combinedIsDirty,
    isSaving: isSavingState,
    handleSave: handleSave,
    handleCancel: handleCancel,
    resetState: resetState,
    dndContextProps: dndContextProps, // Expose dndContextProps
    getSortableListProps: getSortableListProps, // Expose getSortableListProps
  } as UseEditableEntityResult<TEntityData, TFormData, TSubEntityListItemData>; // Type assertion needed for now
}

// Helper function to safely get a value from a path
function getPathValue(
  obj: any, // Changed TObj to any for broader compatibility with RHF Path
  path: string // Changed TPath to string
): any | undefined { // Return type also any or undefined
  if (!obj || !path) return undefined;
  const keys = path.split(/[.\[\]]+/).filter(Boolean);
  let current: any = obj;
  for (const key of keys) {
    if (current && typeof current === 'object' && key in current) {
      current = current[key];
    } else {
      return undefined;
    }
  }
  return current;
}

// TODO:
// - Implement actual RHF hook initialization (useForm)
// - Implement data fetching logic in useEffect
// - Implement snapshot setting
// - Implement form reset logic
// - Implement sub-entity list initialization
// - Implement dirty checking logic (main form, sub-list, overall)
// - Implement save, cancel, reset handlers
// - Implement sub-entity CRUD and DND handlers
// - Add proper default functions for cloneData and isDataEqual using lodash-es
// - Ensure all config options are utilized correctly.
// - Add comprehensive JSDoc comments. 