import React, { useEffect, useState, useCallback } from 'react';
import { useForm, UseFormReturn, SubmitHandler, FieldValues, DefaultValues } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { UseQueryResult, UseMutationResult } from '@tanstack/react-query';

// --- Generic Type Definitions ---
// TData: The type of the original data object (e.g., from the backend). MUST have an 'id' field.
// TFormData: The type of the data managed by React Hook Form.
// TUpdateData: The type of the data payload for update mutations.
// TCreateData: The type of the data payload for create mutations.

// --- Hook Options Interface ---
export interface ObjectEditManagerOptions<
  TData extends { id: string }, // TData itself is expected to be non-null when it exists
  TFormData extends FieldValues,
  TUpdateData extends Record<string, unknown>,
  TCreateData = Omit<TUpdateData, 'id'>
> {
  objectType: string; 
  objectId: string | null; 

  // Data Hooks
  // fetchQueryHook now explicitly can return TData | null in its result
  fetchQueryHook: (id: string | null) => UseQueryResult<TData | null, Error>; 
  updateMutationHook: () => UseMutationResult<TData, Error, { id: string; updates: TUpdateData }, unknown>;
  createMutationHook?: () => UseMutationResult<TData, Error, TCreateData, unknown>;

  // Form and Validation
  zodSchema: z.ZodType<TFormData>;
  defaultValues: DefaultValues<TFormData>; 

  // Data Transformations
  // transformDataToFormData now receives TData | null
  transformDataToFormData: (data: TData | null) => TFormData; 
  // transformFormDataToUpdateData still receives TData | null for originalData reference
  transformFormDataToUpdateData: (formData: TFormData, originalData: TData | null) => TUpdateData; 
  transformFormDataToCreateData?: (formData: TFormData) => TCreateData; 

  // Callbacks
  onSaveSuccess?: (savedData: TData, isNew: boolean) => void;
  onClose?: () => void; 
  onLoadError?: (error: Error) => void;
}

// --- Hook Result Interface ---
// originalData can be TData | null
export interface ObjectEditManagerResult< 
  TData, // No constraint here, it's derived from useObjectEditManager's TData
  TFormData extends FieldValues
> {
  formMethods: UseFormReturn<TFormData>;
  originalData: TData | null; // TData here will be the TData (extends {id:string}) from the hook or null
  isLoading: boolean; 
  isFetching: boolean; 
  isSaving: boolean; 
  error: Error | null; 
  
  handleSave: (e?: React.BaseSyntheticEvent) => Promise<void>; // This is the RHF handleSubmit wrapper
  handleCancel: () => void;
  isDirty: boolean; 
  canSubmit: boolean; 
  
  resetForm: (data?: TData | null) => void; 
}

export function useObjectEditManager<
  TData extends { id: string }, // Constraint remains on TData itself
  TFormData extends FieldValues,
  TUpdateData extends Record<string, unknown>,
  TCreateData = Omit<TUpdateData, 'id'>
>(
  options: ObjectEditManagerOptions<TData, TFormData, TUpdateData, TCreateData>
): ObjectEditManagerResult<TData, TFormData> { // Result will now use TData (which is constrained) for originalData
  const {
    objectType,
    objectId,
    fetchQueryHook,
    updateMutationHook,
    createMutationHook,
    zodSchema,
    defaultValues,
    transformDataToFormData,
    transformFormDataToUpdateData,
    transformFormDataToCreateData,
    onSaveSuccess,
    onClose,
    onLoadError,
  } = options;

  const formMethods = useForm<TFormData>({
    resolver: zodResolver(zodSchema),
    defaultValues: defaultValues,
  });
  const {
    handleSubmit, // This is RHF's handleSubmit
    reset,
    formState: { isDirty },
  } = formMethods;

  // fetchedData can be TData | null
  const { data: fetchedData, isLoading: isFetchingData, error: fetchError } = fetchQueryHook(objectId);
  
  // originalData is TData | null
  const [originalData, setOriginalData] = useState<TData | null>(null);

  const updateMutation = updateMutationHook();
  const createMutation = createMutationHook ? createMutationHook() : null;

  const isSaving = updateMutation.isPending || (createMutation?.isPending ?? false);
  const isLoading = isFetchingData || isSaving;
  const mutationError = updateMutation.error || createMutation?.error || null;
  const error = fetchError || mutationError;

  useEffect(() => {
    if (objectId && fetchedData !== undefined) { // Check fetchedData is not undefined (can be null)
      console.log(`[${objectType}EditManager] Fetched data for ID ${objectId}, resetting form.`);
      // transformDataToFormData now accepts TData | null
      const formData = transformDataToFormData(fetchedData);
      reset(formData);
      setOriginalData(fetchedData);
    } else if (!objectId) {
      console.log(`[${objectType}EditManager] No objectId, resetting to default form values.`);
      const formData = transformDataToFormData(null); // Pass null explicitly
      reset(formData);
      setOriginalData(null);
    }
    // Explicitly depend on fetchedData being potentially null or TData
  }, [objectId, fetchedData, reset, transformDataToFormData, objectType]);

  useEffect(() => {
    if (fetchError && onLoadError) {
      onLoadError(fetchError);
    }
  }, [fetchError, onLoadError]);
  
  const onValidSubmitInternal: SubmitHandler<TFormData> = async (formData) => {
    console.log(`[${objectType}EditManager] onValidSubmitInternal. ID: ${objectId}`, formData);
    const isCreatingNew = !objectId;

    try {
      let savedData: TData | undefined;

      if (isCreatingNew) {
        if (!createMutation) {
          console.error(`[${objectType}EditManager] Create op initiated but no createMutationHook.`);
          throw new Error("Create not configured.");
        }
        const createPayload = transformFormDataToCreateData
          ? transformFormDataToCreateData(formData)
          : (formData as unknown as TCreateData); 
        
        savedData = await createMutation.mutateAsync(createPayload);
        console.log(`[${objectType}EditManager] Create successful.`, savedData);
      } else {
        // For update, originalData must exist and be of type TData (not null)
        // because we are updating an objectId that implies existence.
        // The fetchedData could be null if not found, which should be an error state earlier.
        // However, originalData state here is TData | null.
        const currentOriginalData = originalData; // Capture for type narrowing
        if (!currentOriginalData) { 
            console.error(`[${objectType}EditManager] Update op for ID '${objectId}' but originalData is null or missing.`);
            throw new Error("Cannot update without valid original data. Ensure data was fetched correctly.");
        }
        // transformFormDataToUpdateData receives TData | null for originalData
        const updatePayload = transformFormDataToUpdateData(formData, currentOriginalData); 
        
        if (Object.keys(updatePayload).length === 0) {
            console.log(`[${objectType}EditManager] No effective changes for ID '${objectId}'.`);
            savedData = currentOriginalData; 
        } else {
            savedData = await updateMutation.mutateAsync({ id: objectId as string, updates: updatePayload });
            console.log(`[${objectType}EditManager] Update successful for ID '${objectId}'.`, savedData);
        }
      }

      const finalSavedData: TData | null = savedData === undefined ? null : savedData;

      if (finalSavedData) { // Check for non-null before calling onSaveSuccess with TData
        if (onSaveSuccess) {
          onSaveSuccess(finalSavedData, isCreatingNew);
        }
      } 
      // Always reset form and originalData, even if finalSavedData is null (e.g. create failed but hook didn't throw)
      const newFormDataToReset = transformDataToFormData(finalSavedData); 
      reset(newFormDataToReset as DefaultValues<TFormData>); 
      setOriginalData(finalSavedData); // finalSavedData is TData | null, originalData state is TData | null. This should be fine.
      

      // Only close if not creating new and save was successful (or no-op)
      // and finalSavedData is not null (indicating a successful operation that returned data)
      if (!isCreatingNew && finalSavedData && onClose) { 
          onClose();
      }

    } catch (err) {
      console.error(`[${objectType}EditManager] Save failed for ID '${objectId}':`, err);
      // TODO: Expose error more directly to the consuming component if needed
    }
  };

  const onInvalidSubmitInternal = (errors: FieldValues) => {
    console.warn(`[${objectType}EditManager] Form validation failed:`, errors);
    // TODO: Expose formErrors more directly or via a callback if needed
  };

  // handleSave is RHF's handleSubmit wrapping our internal onValidSubmit and onInvalidSubmit
  const handleSave = handleSubmit(onValidSubmitInternal, onInvalidSubmitInternal);

  const handleCancel = useCallback(() => {
    console.log(`[${objectType}EditManager] handleCancel. isDirty: ${isDirty}`);
    if (isDirty) {
      if (window.confirm("You have unsaved changes. Are you sure you want to discard them?")) {
        // Pass originalData (which can be TData | null) to transform
        reset(transformDataToFormData(originalData) as DefaultValues<TFormData>); 
        if (onClose) onClose();
      }
    } else {
      if (onClose) onClose();
    }
  }, [isDirty, onClose, reset, originalData, transformDataToFormData, objectType]);

  // resetForm now accepts TData | null
  const resetForm = useCallback((data?: TData | null) => { 
    // If data is undefined (called with no arg), pass null to transformDataToFormData
    const formData = transformDataToFormData(data === undefined ? null : data); 
    reset(formData as DefaultValues<TFormData>);
    setOriginalData(data === undefined ? null : data); 
  }, [reset, transformDataToFormData]);


  return {
    formMethods,
    originalData,
    isLoading,
    isFetching: isFetchingData,
    isSaving,
    error,
    handleSave, // This is the RHF handleSubmit wrapper
    handleCancel,
    isDirty,
    canSubmit: isDirty && !isSaving, 
    resetForm,
  };
} 