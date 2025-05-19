import { useCallback } from 'react';
import { useForm, UseFormReturn, FieldValues, DefaultValues } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

// --- Generic Type Definitions ---
// TData: The type of the original data object (e.g., from the backend). MUST have an 'id' field.
// TFormData: The type of the data managed by React Hook Form.
// TUpdateData: The type of the data payload for update mutations.
// TCreateData: The type of the data payload for create mutations.

// --- Hook Options Interface ---
export interface ObjectEditManagerOptions<
  TFormData extends FieldValues
  // TUpdateData extends Record<string, unknown>, // This seems unused if we remove mutations
  // TCreateData = Omit<TUpdateData, 'id'> // This also seems unused
> {
  // objectType: string; // Removed, was only used in commented out logs
  // objectId: string | null; // No longer needed as data is passed in

  // Data Hooks - REMOVE THESE
  // fetchQueryHook: (id: string | null) => UseQueryResult<TData | null, Error>; 
  // updateMutationHook: () => UseMutationResult<TData, Error, { id: string; updates: TUpdateData }, unknown>;
  // createMutationHook?: () => UseMutationResult<TData, Error, TCreateData, unknown>;

  // Form and Validation
  zodSchema: z.ZodType<TFormData>;
  defaultValues: DefaultValues<TFormData>; 
  initialData?: DefaultValues<TFormData>; // Ensure initialData is also DefaultValues

  // Data Transformations - Potentially simplify or remove if data is already in TFormData format
  // transformDataToFormData: (data: TData | null) => TFormData; 
  // transformFormDataToUpdateData: (formData: TFormData, originalData: TData | null) => TUpdateData; 
  // transformFormDataToCreateData?: (formData: TFormData) => TCreateData; 

  // Callbacks - REMOVE OR RE-EVALUATE
  // onSaveSuccess?: (savedData: TData, isNew: boolean) => void;
  // onClose?: () => void; 
  // onLoadError?: (error: Error) => void;
}

// --- Hook Result Interface ---
export interface ObjectEditManagerResult< 
  // TData, // No longer directly managing TData
  TFormData extends FieldValues
> {
  formMethods: UseFormReturn<TFormData>;
  // originalData: TData | null; // No longer directly managing original TData
  // isLoading: boolean; // Related to fetching/saving, remove
  // isFetching: boolean; // Related to fetching, remove
  // isSaving: boolean; // Related to saving, remove
  // error: Error | null; // Related to fetching/saving, remove
  
  // handleSave: (e?: React.BaseSyntheticEvent) => Promise<void>; // RHF's handleSubmit will be returned by formMethods
  // handleCancel: () => void; // Component specific, remove
  isDirty: boolean; 
  // canSubmit: boolean; // Component specific, derived from isDirty & other states
  
  resetForm: (data?: DefaultValues<TFormData>) => void 
}

export function useObjectEditManager<
  // TData extends { id: string }, // No longer generic over TData in this way
  TFormData extends FieldValues
  // TUpdateData extends Record<string, unknown>, // Keeping for now, but likely to be removed
  // TCreateData = Omit<TUpdateData, 'id'> // Keeping for now
>(
  options: ObjectEditManagerOptions<TFormData>
): ObjectEditManagerResult<TFormData> { 
  const {
    // objectType, // Removed for logging
    // objectId, // Removed
    // fetchQueryHook, // Removed
    // updateMutationHook, // Removed
    // createMutationHook, // Removed
    zodSchema,
    defaultValues,
    initialData, // ADDED
    // transformDataToFormData, // Potentially remove/simplify
    // transformFormDataToUpdateData, // Removed
    // transformFormDataToCreateData, // Removed
    // onSaveSuccess, // Removed
    // onClose, // Removed
    // onLoadError, // Removed
  } = options;

  const formMethods = useForm<TFormData>({
    resolver: zodResolver(zodSchema),
    // Use initialData if provided, otherwise fallback to defaultValues
    defaultValues: initialData || defaultValues, 
  });
  const {
    // handleSubmit, // Exported via formMethods
    reset,
    formState: { isDirty },
  } = formMethods;

  // REMOVE ALL useEffects related to fetching and data transformation based on objectId/fetchedData
  // useEffect(() => {
  //   if (objectId && fetchedData !== undefined) { 
  //     console.log(`[${objectType}EditManager] Fetched data for ID ${objectId}, resetting form.`);
  //     const formData = transformDataToFormData(fetchedData);
  //     reset(formData);
  //     setOriginalData(fetchedData);
  //   } else if (!objectId) {
  //     console.log(`[${objectType}EditManager] No objectId, resetting to default form values.`);
  //     const formData = transformDataToFormData(null); 
  //     reset(formData);
  //     setOriginalData(null);
  //   }
  // }, [objectId, fetchedData, reset, transformDataToFormData, objectType]);

  // useEffect(() => {
  //   if (fetchError && onLoadError) {
  //     onLoadError(fetchError);
  //   }
  // }, [fetchError, onLoadError]);
  
  // REMOVE onValidSubmitInternal and onInvalidSubmitInternal as persistence is handled by the component
  // const onValidSubmitInternal: SubmitHandler<TFormData> = async (formData) => { ... }
  // const onInvalidSubmitInternal = (errors: FieldValues) => { ... }

  // REMOVE handleSave as it's component's responsibility to call formMethods.handleSubmit
  // const handleSave = handleSubmit(onValidSubmitInternal, onInvalidSubmitInternal);

  // REMOVE handleCancel as it's component specific
  // const handleCancel = useCallback(() => { ... });

  // resetForm now accepts TFormData or uses initialData/defaultValues
  const resetForm = useCallback((data?: DefaultValues<TFormData>) => { 
    // Ensure that the type passed to reset is compatible.
    // If data is provided, use it. Otherwise, use initialData if available, or fallback to defaultValues.
    const valuesToReset = data || initialData || defaultValues;
    reset(valuesToReset);
  }, [reset, initialData, defaultValues]);


  return {
    formMethods,
    // originalData, // Removed
    // isLoading: false, // Removed
    // isFetching: false, // Removed
    // isSaving: false, // Removed
    // error: null, // Removed
    // handleSave, // Removed
    // handleCancel, // Removed
    isDirty,
    // canSubmit: isDirty && !isSaving, // Removed, saving state is external now
    resetForm,
  };
} 