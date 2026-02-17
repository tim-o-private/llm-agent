import { useForm, FieldValues, DefaultValues } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useState, useEffect, useCallback } from 'react';
import { cloneDeep } from 'lodash-es';

import { UseEditableEntityConfig, UseEditableEntityReturn } from '@/types/editableEntityTypes';
import { AppError } from '@/types/error';

export function useEditableEntity<TEntityData, TFormData extends FieldValues>(
  config: UseEditableEntityConfig<TEntityData, TFormData>,
): UseEditableEntityReturn<TEntityData, TFormData> {
  const {
    entityId,
    getEntityDataFn,
    saveEntityFn,
    transformDataToForm,
    formSchema,
    defaultFormValues,
    entityName,
    onSaveSuccess,
    onSaveError,
    isCreatable = false,
  } = config;

  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveError, setSaveError] = useState<AppError | Error | null>(null);

  const isCreating = (entityId === null || entityId === undefined) && isCreatable;
  const effectiveEntityId = entityId === null ? undefined : entityId;

  const formMethods = useForm<TFormData, undefined, TFormData>({
    resolver: zodResolver(formSchema),
    mode: 'onChange',
    defaultValues: (isCreating
      ? defaultFormValues || transformDataToForm(undefined)
      : transformDataToForm(getEntityDataFn(effectiveEntityId))) as DefaultValues<TFormData>,
  });

  useEffect(() => {
    const currentInitialData = getEntityDataFn(isCreating ? undefined : effectiveEntityId);
    const newFormValues = isCreating
      ? defaultFormValues || transformDataToForm(undefined)
      : transformDataToForm(currentInitialData);
    formMethods.reset(newFormValues);
  }, [
    entityId,
    // Removed unstable function dependencies that cause constant resets
    // getEntityDataFn, transformDataToForm, and formMethods are now excluded
    // to prevent infinite reset loops
    isCreating,
    effectiveEntityId,
  ]);

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    setSaveError(null);

    const isValid = await formMethods.trigger();
    if (!isValid) {
      console.warn(`[useEditableEntity: ${entityName}] Form validation failed.`);
      setIsSaving(false);
      const validationError = new Error('Form validation failed.');
      setSaveError(validationError);
      if (onSaveError) {
        onSaveError(validationError, formMethods.getValues());
      }
      return;
    }

    const formData = formMethods.getValues();
    const currentInitialData = getEntityDataFn(isCreating ? undefined : effectiveEntityId);

    try {
      const result = await saveEntityFn(
        formData,
        cloneDeep(currentInitialData),
        isCreating ? undefined : effectiveEntityId,
      );
      setIsSaving(false);
      if (onSaveSuccess) {
        onSaveSuccess(result, formData);
      }
    } catch (error) {
      const err =
        error instanceof Error || (error as AppError)?.message ? (error as AppError | Error) : new Error(String(error));
      console.error(`[useEditableEntity: ${entityName}] Save failed:`, err);
      setSaveError(err);
      setIsSaving(false);
      if (onSaveError) {
        onSaveError(err, formData);
      }
    }
  }, [
    formMethods,
    saveEntityFn,
    onSaveSuccess,
    onSaveError,
    entityName,
    entityId,
    getEntityDataFn,
    isCreating,
    effectiveEntityId,
  ]);

  const resetFormToInitial = useCallback(() => {
    const currentInitialData = getEntityDataFn(isCreating ? undefined : effectiveEntityId);
    formMethods.reset(
      isCreating ? defaultFormValues || transformDataToForm(undefined) : transformDataToForm(currentInitialData),
    );
    setSaveError(null);
  }, [getEntityDataFn, transformDataToForm, formMethods, defaultFormValues, isCreating, effectiveEntityId]);

  const canSave = formMethods.formState.isDirty && !isSaving;

  return {
    formMethods,
    isSaving,
    saveError,
    canSave,
    handleSave,
    resetFormToInitial,
    initialData: getEntityDataFn(isCreating ? undefined : effectiveEntityId),
    isCreating,
    initialDataError: null,
  };
}

// Removed unused getPathValue function

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
