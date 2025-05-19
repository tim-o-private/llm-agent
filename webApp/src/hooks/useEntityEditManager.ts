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
  console.log('[useEntityEditManager] Hook (re-render/init). EntityId:', entityId, 'Received initialData prop:', initialData === undefined ? "undefined" : JSON.stringify(initialData));
  const [snapshot, setSnapshot] = useState<TData | null>(null);
  const [isDirtyState, _setIsDirty] = useState(false);
  const setIsDirty = (val: boolean) => {
    if (val === true) {
      // Always log the compared objects when setting dirty to true
      try {
        const latestData = getLatestData?.();
        console.log('[EntityEditManager] setIsDirty(true) called. Comparing:', { latestData, snapshot });
      } catch (e) {
        console.log('[EntityEditManager] setIsDirty(true) called, but could not get latestData:', e);
      }
    }
    console.log('[EntityEditManager] setIsDirty called with', val, new Error().stack);
    _setIsDirty(val);
  };
  const isDirty = isDirtyState;
  // const [currentData, setCurrentData] = useState<TData | undefined>(initialData);

  const initializeState = useCallback(
    (currentEntityData: TData) => {
      const newSnapshot = cloneData(currentEntityData);
      console.log('[EEM] initializeState CALLED. Setting snapshot with:', JSON.stringify(newSnapshot));
      setSnapshot(newSnapshot);
      // DO NOT set isDirtyState here. Let the effect handle it.
      // console.log('[EEM] initializeState explicitly setting EEM isDirtyState to false.');
      // _setIsDirty(false); 
    },
    [cloneData]
  );

  const resetState = useCallback(() => {
    const newSnapshotFromInitial = initialData ? cloneData(initialData) : null;
    console.log('[EEM] resetState CALLED. Setting snapshot with current initialData prop:', JSON.stringify(newSnapshotFromInitial));
    setSnapshot(newSnapshotFromInitial);
    // DO NOT set isDirtyState here. Let the effect handle it.
    // console.log('[EEM] resetState explicitly setting EEM isDirtyState to false.');
    // _setIsDirty(false);
  }, [initialData, cloneData]);
  
  // Effect to initialize when initialData is available and hook is first used
  useEffect(() => {
    console.log('[EEM] Snapshot init effect (initialData prop dependency). Current initialData prop:', initialData === undefined ? "undefined" : JSON.stringify(initialData));
    if (initialData) {
      const newInitialSnapshot = cloneData(initialData);
      console.log('[EEM] Snapshot init effect: Setting snapshot to:', JSON.stringify(newInitialSnapshot));
      setSnapshot(newInitialSnapshot);
      // DO NOT set isDirtyState here. Let the main dirty-checking effect determine it.
      // console.log('[EEM] Snapshot init effect: Setting EEM isDirtyState to false (because snapshot is aligned with initialData).');
      // _setIsDirty(false); 
    } else {
      console.log('[EEM] Snapshot init effect: initialData prop is undefined/null. Setting snapshot to null.');
      setSnapshot(null);
      // DO NOT set isDirtyState here.
      // console.log('[EEM] Snapshot init effect: Setting EEM isDirtyState to false (no snapshot).');
      // _setIsDirty(false); 
    }
  // }, [initialData, cloneData]); // Removed _setIsDirty -- This effect should ONLY set the snapshot.
  // The main dirty checking effect will then compare against this new snapshot.
  }, [initialData, cloneData]);

  useEffect(() => {
    const latestData = getLatestData(); 
    const currentSnapshot = snapshot;   
    console.log('[EEM] Dirty Check Effect RUNS. Timestamp:', Date.now());
    console.log('[EEM]   - Internal Snapshot (currentSnapshot):', currentSnapshot === null ? "null" : JSON.stringify(currentSnapshot));
    console.log('[EEM]   - Latest Data (from getLatestData()):', latestData === undefined ? "undefined" : JSON.stringify(latestData));
  
    if (!currentSnapshot) {
      if (isDirtyState) { // isDirtyState is the internal state boolean
        console.log('[EEM]   - No snapshot, current EEM isDirtyState: true. Setting EEM isDirtyState: false.');
        _setIsDirty(false); // _setIsDirty is the setter
      } else {
        console.log('[EEM]   - No snapshot, current EEM isDirtyState: false. No change to EEM isDirtyState.');
      }
      return;
    }
    
    // Ensure latestData is not undefined before comparison, though getLatestData() should ideally always return TData
    if (latestData === undefined) {
        console.warn('[EEM]   - Latest Data is undefined. Cannot perform dirty check. Current EEM isDirtyState:', isDirtyState);
        if (isDirtyState) _setIsDirty(false); // Or handle as an error/specific state
        return;
    }
  
    const dataIsActuallyEqual = isDataEqual(latestData, currentSnapshot);
    const newCalculatedDirtyState = !dataIsActuallyEqual;
    console.log(`[EEM]   - Comparison Result: latestData is ${dataIsActuallyEqual ? "EQUAL" : "NOT EQUAL"} to currentSnapshot.`);
    console.log(`[EEM]   - Calculated newDirtyState for EEM: ${newCalculatedDirtyState}. Current EEM isDirtyState: ${isDirtyState}`);
  
    if (newCalculatedDirtyState !== isDirtyState) {
      console.log(`[EEM]   - FLIPPING EEM isDirtyState from ${isDirtyState} to ${newCalculatedDirtyState}`);
      _setIsDirty(newCalculatedDirtyState);
    } else {
      console.log(`[EEM]   - EEM isDirtyState (${isDirtyState}) remains unchanged based on comparison.`);
    }
  }, [getLatestData, snapshot, isDataEqual, _setIsDirty]); // Removed isDirtyState from here

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