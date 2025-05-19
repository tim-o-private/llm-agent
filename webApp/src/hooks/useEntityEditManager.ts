import { useState, useEffect, useCallback } from 'react';
import { isEqual, cloneDeep } from 'lodash-es';
import { toast } from '@/components/ui/toast';

export interface EntityEditManagerOptions<TData, TStoreActions> {
  entityId?: string | null; // Optional: for context or if saveHandler needs it
  initialData: TData | undefined;
  storeActions: TStoreActions; // Actions to be passed to saveHandler
  onSaveComplete: () => void;
  saveHandler: (
    currentData: TData,
    originalData: TData,
    actions: TStoreActions,
    entityId?: string | null
  ) => Promise<boolean | void>; // Returns true if save was attempted, void otherwise. Or just Promise<void>
  isDataEqual?: (a: TData | null | undefined, b: TData | null | undefined) => boolean;
  cloneData?: (data: TData) => TData;
  getLatestData: () => TData; // Function to get the most current form data
}

export interface EntityEditManagerResult<TData> {
  isDirty: boolean;
  // currentData: TData | undefined; // The hook now relies on getLatestData
  // setCurrentData: React.Dispatch<React.SetStateAction<TData | undefined>>;
  initializeState: (currentEntityData: TData) => void;
  resetState: () => void;
  handleSaveChanges: () => Promise<void>;
  internalSnapshot: TData | null; // Exposed for debugging or advanced scenarios if needed
}

export function useEntityEditManager<TData, TStoreActions>({
  entityId,
  initialData,
  storeActions,
  onSaveComplete,
  saveHandler,
  isDataEqual = isEqual,
  cloneData = cloneDeep,
  getLatestData,
}: EntityEditManagerOptions<TData, TStoreActions>): EntityEditManagerResult<TData> {
  const [snapshot, setSnapshot] = useState<TData | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  // const [currentData, setCurrentData] = useState<TData | undefined>(initialData);

  const initializeState = useCallback(
    (currentEntityData: TData) => {
      // setCurrentData(cloneData(currentEntityData));
      setSnapshot(cloneData(currentEntityData));
      setIsDirty(false);
    },
    [cloneData]
  );

  const resetState = useCallback(() => {
    // setCurrentData(initialData ? cloneData(initialData) : undefined);
    setSnapshot(initialData ? cloneData(initialData) : null);
    setIsDirty(false);
    // Also re-initialize with current form values if modal is still open
    // This will be handled by calling initializeState when the modal opens or data loads.
  }, [initialData, cloneData]);
  
  // Effect to initialize when initialData is available and hook is first used
  useEffect(() => {
    if (initialData) {
      // setCurrentData(cloneData(initialData));
      setSnapshot(cloneData(initialData));
    } else {
      // setCurrentData(undefined);
      setSnapshot(null);
    }
  }, [initialData, cloneData]);


  useEffect(() => {
    if (!snapshot) {
      if (isDirty) setIsDirty(false);
      return;
    }
    const latestData = getLatestData();
    const newDirtyState = !isDataEqual(latestData, snapshot);

    if (newDirtyState !== isDirty) {
      setIsDirty(newDirtyState);
    }
  }, [getLatestData, snapshot, isDirty, isDataEqual]);

  const handleSaveChanges = useCallback(async () => {
    const latestData = getLatestData();
    if (!isDirty || !snapshot || !latestData) {
      // if (!isDataEqual(latestData, snapshot)) { // Check one last time if not relying on isDirty state solely
      //   toast.error(\\"Data integrity issue or snapshot missing. Cannot save.\\");
      //   return;
      // }
      toast.default('No changes to save.');
      onSaveComplete();
      return;
    }

    try {
      await saveHandler(latestData, snapshot, storeActions, entityId);
      // Assuming saveHandler updates the source of truth, re-initialize snapshot with latest saved data
      setSnapshot(cloneData(latestData));
      setIsDirty(false);
      toast.success('Changes saved!'); // Generic success message
      onSaveComplete();
    } catch (error) {
      console.error('Save operation failed:', error);
      toast.error('Failed to save changes. Please try again.');
      // Do not call onSaveComplete here if we want the modal to stay open on error.
      // Or, call it if the desired behavior is to close regardless.
      // For now, let's assume we keep it open for the user to retry or see the error.
    }
  }, [
    isDirty,
    snapshot,
    getLatestData,
    saveHandler,
    storeActions,
    entityId,
    onSaveComplete,
    cloneData,
  ]);

  return {
    isDirty,
    // currentData,
    // setCurrentData,
    initializeState,
    resetState,
    handleSaveChanges,
    internalSnapshot: snapshot, // Exposing for transparency or specific needs
  };
} 