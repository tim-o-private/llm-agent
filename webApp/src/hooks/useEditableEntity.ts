import { UseFormReturn, FieldValues, Path, PathValue, useForm } from 'react-hook-form';
import { ZodSchema } from 'zod';
import { DragEndEvent, DndContextProps as CoreDndContextProps, useSensors, useSensor, PointerSensor, KeyboardSensor } from '@dnd-kit/core';
import { sortableKeyboardCoordinates, arrayMove } from '@dnd-kit/sortable'; // Import arrayMove
import { useState, useEffect, useCallback } from 'react';
// Placeholder for a robust deep clone and deep equal utility
// You might use lodash, rfdc, fast-deep-equal, etc.
import { cloneDeep, isEqual } from 'lodash-es';
import { zodResolver } from '@hookform/resolvers/zod'; // Assuming zod resolver is installed
import type { AppError } from '@/types/error'; // IMPORT AppError

// --- Core Type Definitions (from creative-useEditableEntity-design.md) ---

// TEntityData: The complete data structure of the entity as fetched/saved.
// TFormData: The structure for the main entity's form (React Hook Form).
// TSubEntityCollectionData: The raw data for the collection of sub-entities if path is used.
// TSubEntityListItemData: The structure for a single item in the managed sub-entity list.
// TSubEntityListItemFormInputData: Data structure for editing/creating a single sub-entity item's form.

/**
 * Configuration object for the `useEditableEntity` hook.
 * Defines how the hook fetches, manages, and saves an entity and its potential sub-entities.
 *
 * @template TEntityData The complete data structure of the entity.
 * @template TFormData The structure for the main entity's form (React Hook Form).
 * @template TSubEntityListItemData The structure for a single item in the sub-entity list.
 * @template TSubEntityListItemFormInputData Data structure for the form used to edit/create a sub-entity item.
 */
export interface EntityTypeConfig<
  TEntityData,
  TFormData extends FieldValues,
  TSubEntityListItemData = Record<string, unknown>, // UPDATED default to unknown
  TSubEntityListItemFormInputData extends FieldValues = FieldValues,
> {
  entityId: string | null | undefined;
  queryHook: (id: string | null | undefined) => {
    data: TEntityData | undefined;
    isLoading: boolean;
    isFetching: boolean;
    error: AppError | Error | null; // UPDATED error type
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

  isDataEqual?: <TData>(a: TData, b: TData) => boolean; // UPDATED with generic TData
  cloneData?: <T>(data: T) => T;

  onSaveSuccess?: (savedEntity: TEntityData) => void;
  onSaveError?: (error: AppError | Error | null) => void; // UPDATED error type
  onCancel?: () => void;
  onDirtyStateChange?: (isDirty: boolean) => void;

  enableSubEntityReordering?: boolean;
  // dndSensors?: SensorDescriptor[];
}

/**
 * Result object returned by the `useEditableEntity` hook.
 * Provides state variables, form management tools, and handlers for interacting with the editable entity.
 *
 * @template TEntityData The complete data structure of the entity.
 * @template TFormData The structure for the main entity's form.
 * @template TSubEntityListItemData The structure for a single item in the sub-entity list.
 */
export interface UseEditableEntityResult<
  TEntityData,
  TFormData extends FieldValues,
  TSubEntityListItemData = unknown, // UPDATED default to unknown
> {
  originalEntity: TEntityData | null;
  currentEntityDataForForm: TFormData | undefined; // This might be redundant if formMethods.getValues() is always used
  isLoading: boolean;
  isFetching: boolean;
  error: AppError | Error | null; // UPDATED error type

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

/**
 * A comprehensive React hook for managing the state and lifecycle of an editable entity,
 * including its main form data and an optional list of sub-entities.
 *
 * It handles data fetching, form state management (via React Hook Form), sub-list CRUD operations,
 * drag-and-drop reordering for sub-lists, dirty state tracking, and save/cancel logic.
 *
 * @template TEntityData The complete data structure of the entity.
 * @template TFormData The structure for the main entity's form (React Hook Form).
 * @template TSubEntityListItemData The structure for a single item in the managed sub-entity list.
 * @template TSubEntityListItemFormInputData Data structure for the form used to edit/create a sub-entity item.
 *
 * @param {EntityTypeConfig<TEntityData, TFormData, TSubEntityListItemData, TSubEntityListItemFormInputData>} config
 *   The configuration object that defines the behavior of the hook for a specific entity type.
 *
 * @returns {UseEditableEntityResult<TEntityData, TFormData, TSubEntityListItemData>}
 *   An object containing state variables, form methods, and handlers to manage the entity.
 */
export function useEditableEntity<
  TEntityData,
  TFormData extends FieldValues,
  TSubEntityListItemData = Record<string, unknown>, // Default remains, constraint might be too strict or removed
  // TSubEntityListItemData extends {} = Record<string, unknown>, // Example of a less strict constraint
  TSubEntityListItemFormInputData extends FieldValues = FieldValues
>(
  config: EntityTypeConfig<
    TEntityData,
    TFormData,
    TSubEntityListItemData,
    TSubEntityListItemFormInputData
  >
): UseEditableEntityResult<TEntityData, TFormData, TSubEntityListItemData> {
  console.log('[useEditableEntity] TOP LEVEL - HOOK CALLED/RE-EXECUTED. Entity ID from config:', config.entityId);
  // Log the entire config object upon entry and specifically enableSubEntityReordering
  console.log('[useEditableEntity] Hook initialized. Config received:', config);
  console.log(`[useEditableEntity] Config.enableSubEntityReordering upon entry: ${config.enableSubEntityReordering}`);

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
  const [errorState, setErrorState] = useState<AppError | Error | null>(null); // UPDATED error type
  const [isSavingState, setIsSavingState] = useState<boolean>(false);

  // State for the original snapshot of the sub-entity list
  const [originalSubEntityListSnapshot, setOriginalSubEntityListSnapshot] = useState<TSubEntityListItemData[]>([]);

  // Step 9.2.3: Integrate React Hook Form (RHF) for Main Entity
  const formMethods = useForm<TFormData>({
    resolver: formSchema ? zodResolver(formSchema) : undefined,
    defaultValues: async () => transformDataToForm(undefined), // WRAP in async function
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
            // If error is an instance of Error or AppError, use it, otherwise wrap it.
            const errToSet = (e instanceof Error) ? e : new Error(String(e));
            setErrorState(errToSet);
            setInternalSubEntityList([]);
            setOriginalSubEntityListSnapshot([]);
          }
        } else {
          console.log('[useEditableEntity CHANGED_LOGIC] No transformSubCollectionToList, setting sublist to [].');
          setInternalSubEntityList([]);
          setOriginalSubEntityListSnapshot([]);
        }
        // Only set errorState to null if it wasn't set by transformSubCollectionToList catcher
        if (!(errorState && errorState instanceof Error)) { // basic check, might need refinement
            setErrorState(null);
        }
      } else {
        setOriginalEntitySnapshot(null);
        formMethods.reset(transformDataToForm(undefined));
        setInternalSubEntityList([]);
        setOriginalSubEntityListSnapshot([]);
        setErrorState(null); // Explicitly clear error if no data, not loading, and no query error
      }
    } // else: still loading/fetching, state will update on next effect run
  }, [entityId, queryHook, transformDataToForm, formSchema, cloneData, subEntityPath, transformSubCollectionToList, formMethods, errorState]);

  // --- Effect for isDirty calculation and onDirtyStateChange callback ---
  const isMainFormDirty = formMethods.formState.isDirty;

  useEffect(() => {
    // Calculate if the sub-entity list is dirty
    const subListDirty = !isDataEqual(originalSubEntityListSnapshot, internalSubEntityList);
    setIsSubEntityListDirtyState(subListDirty);

    const overallDirty = isMainFormDirty || subListDirty;
    if (onDirtyStateChange) {
      onDirtyStateChange(overallDirty);
    }
  }, [isMainFormDirty, internalSubEntityList, originalSubEntityListSnapshot, isDataEqual, onDirtyStateChange]);

  // --- Sub-entity CRUD operations ---
  const addSubItem = useCallback((newItemData: TSubEntityListItemData) => {
    // When adding, we expect the full item, not TSubEntityListItemFormInputData, 
    // as createEmptySubEntityListItem (if used for form) should produce TSubEntityListItemData
    setInternalSubEntityList(prev => [...prev, newItemData]);
  }, []);

  const updateSubItem = useCallback((
    id: string | number, 
    updatedItemDataOrUpdater: Partial<TSubEntityListItemData> | ((prev: TSubEntityListItemData) => TSubEntityListItemData)
  ) => {
    setInternalSubEntityList(prevList =>
      prevList.map(item => {
        if (String(item[subEntityListItemIdField] as string | number) === String(id)) {
          if (typeof updatedItemDataOrUpdater === 'function') {
            return updatedItemDataOrUpdater(item);
          }
          return { ...item, ...updatedItemDataOrUpdater };
        }
        return item;
      })
    );
  }, [subEntityListItemIdField]);

  const removeSubItem = useCallback((id: string | number) => {
    setInternalSubEntityList(prevList =>
      prevList.filter(item => String(item[subEntityListItemIdField] as string | number) !== String(id))
    );
  }, [subEntityListItemIdField]);
  
  // --- Save and Cancel Handlers ---
  const handleSave = useCallback(async () => {
    setIsSavingState(true);
    setErrorState(null);
    try {
      // Ensure form validation runs if schema is provided
      if (formSchema) {
        await formMethods.trigger(); // Trigger validation for all fields
        if (!formMethods.formState.isValid) {
          throw new Error('Form validation failed.'); // Or a custom AppError
        }
      }
      const currentFormData = formMethods.getValues();
      const savedEntity = await saveHandler(
        originalEntitySnapshot,
        currentFormData,
        internalSubEntityList
      );
      
      // If saveHandler returns the updated entity, use it to reset the state
      if (savedEntity) {
        const newSnapshot = cloneData(savedEntity);
        setOriginalEntitySnapshot(newSnapshot);
        formMethods.reset(transformDataToForm(savedEntity)); // Reset form with new pristine state
        
        if (transformSubCollectionToList) {
            const dataForSubList = subEntityPath 
                ? getPathValue(savedEntity, subEntityPath as string) 
                : savedEntity;
            const transformedSubList = transformSubCollectionToList(dataForSubList) || [];
            setInternalSubEntityList(transformedSubList);
            setOriginalSubEntityListSnapshot(cloneData(transformedSubList));
        } else {
            setInternalSubEntityList([]);
            setOriginalSubEntityListSnapshot([]);
        }
      } else {
        // If saveHandler doesn't return data, we assume it updated in place or re-query will happen.
        // Re-snapshot based on current form values if no entity returned. This is a common pattern.
        // Or, we might need a re-fetch mechanism here if saveHandler doesn't return the entity.
        // For now, optimistic update based on current form data. 
        // THIS MIGHT NOT BE IDEAL - re-fetching or relying on queryHook invalidation is better.
        const optimisticEntity = { 
            ...(originalEntitySnapshot || {} as TEntityData), 
            ...formMethods.getValues() 
        } as TEntityData;
        setOriginalEntitySnapshot(cloneData(optimisticEntity));
        // Sub-items were already updated in internalSubEntityList, so snapshot them.
        setOriginalSubEntityListSnapshot(cloneData(internalSubEntityList));
        // Form is reset to current values, effectively making them the new "original" state
        formMethods.reset(formMethods.getValues()); 
      }
      
      setIsSavingState(false);
      if (onSaveSuccess && savedEntity) {
        onSaveSuccess(savedEntity as TEntityData);
      }
    } catch (err) {
      const errorToSet = (err instanceof Error || (err as AppError)?.message) 
        ? (err as AppError | Error) 
        : new Error(String(err));
      setErrorState(errorToSet);
      setIsSavingState(false);
      if (onSaveError) {
        onSaveError(errorToSet);
      }
    }
  }, [originalEntitySnapshot, internalSubEntityList, saveHandler, formMethods, onSaveSuccess, onSaveError, cloneData, transformDataToForm, transformSubCollectionToList, subEntityPath, formSchema]);

  const handleCancel = useCallback(() => {
    // Reset form to original entity data
    formMethods.reset(transformDataToForm(originalEntitySnapshot || undefined));
    // Reset sub-entity list to original snapshot
    setInternalSubEntityList(cloneData(originalSubEntityListSnapshot));
    setErrorState(null);
    if (onCancel) {
      onCancel();
    }
  }, [originalEntitySnapshot, originalSubEntityListSnapshot, transformDataToForm, cloneData, onCancel, formMethods.reset]);
  
  const resetState = useCallback((newEntityData?: TEntityData) => {
    const entityToReset = newEntityData !== undefined ? newEntityData : originalEntitySnapshot;
    const newSnapshot = entityToReset ? cloneData(entityToReset) : null;
    setOriginalEntitySnapshot(newSnapshot);
    formMethods.reset(transformDataToForm(entityToReset || undefined));

    if (transformSubCollectionToList && entityToReset) {
      const dataForSubList = subEntityPath 
        ? getPathValue(entityToReset, subEntityPath as string) 
        : entityToReset;
      const transformedSubList = transformSubCollectionToList(dataForSubList) || [];
      setInternalSubEntityList(transformedSubList);
      setOriginalSubEntityListSnapshot(cloneData(transformedSubList));
    } else {
      setInternalSubEntityList([]);
      setOriginalSubEntityListSnapshot([]);
    }
    setErrorState(null);
    setIsSavingState(false);
  }, [originalEntitySnapshot, cloneData, formMethods, transformDataToForm, transformSubCollectionToList, subEntityPath]);

  // --- Derived State ---
  const isDirty = formMethods.formState.isDirty || isSubEntityListDirtyState;
  
  // --- DND-kit Setup ---
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      setInternalSubEntityList((items) => {
        const oldIndex = items.findIndex(item => String(item[subEntityListItemIdField] as string | number) === String(active.id));
        const newIndex = items.findIndex(item => String(item[subEntityListItemIdField] as string | number) === String(over.id));
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  }, [subEntityListItemIdField]);
  
  const dndContextProps: UseEditableEntityResult<TEntityData, TFormData, TSubEntityListItemData>['dndContextProps'] = enableSubEntityReordering
    ? {
        sensors,
        onDragEnd: handleDragEnd,
        // modifiers: [], // Add modifiers if needed (e.g., restrictToVerticalAxis)
        // collisionDetection: closestCenter, // Default or choose another strategy
      }
    : undefined;

  const getSortableListProps = useCallback((): ReturnType<UseEditableEntityResult<TEntityData, TFormData, TSubEntityListItemData>['getSortableListProps']> => {
    const itemsWithDndId = internalSubEntityList.map(item => ({
      ...item,
      id: String(item[subEntityListItemIdField] as string | number)
    }));
    return {
      items: itemsWithDndId as Array<TSubEntityListItemData & { id: string | number }>,
    };
  }, [internalSubEntityList, subEntityListItemIdField]);


  // Final return statement
  return {
    originalEntity: originalEntitySnapshot,
    currentEntityDataForForm: formMethods.getValues(), // Provide current form values
    isLoading: isLoadingState,
    isFetching: isFetchingState,
    error: errorState,
    formMethods,
    isMainFormDirty: formMethods.formState.isDirty,
    subEntityList: internalSubEntityList,
    isSubEntityListDirty: isSubEntityListDirtyState,
    addSubItem,
    updateSubItem,
    removeSubItem,
    isDirty,
    isSaving: isSavingState,
    handleSave,
    handleCancel,
    resetState,
    dndContextProps,
    getSortableListProps,
  };
}

// --- Utility Functions (Potentially move to a utils file) ---

// Helper to get a value from an object by path string (e.g., 'a.b.c')
// This is a simplified version; a robust one would handle arrays, etc.
// Consider using lodash.get or similar if complex paths are needed.
function getPathValue<
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _TObj extends Record<string, unknown> = Record<string, unknown>, 
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _TPath extends string = string
>(
  obj: any, // Changed TObj to any for broader compatibility with RHF Path
  path: string // Changed TPath to string
): any | undefined { // Return type also any or undefined
  if (!obj || typeof path !== 'string') {
    return undefined;
  }
  return path.split('.').reduce((acc, part) => acc && acc[part], obj);
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