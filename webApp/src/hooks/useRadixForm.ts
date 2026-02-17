import React from 'react';
import { ZodSchema } from 'zod';
import { AppError } from '@/types/error';

export interface UseRadixFormConfig<EntityType, FormData> {
  // Entity identification
  entityId: string | null | undefined;

  // Data access
  getEntity: (id: string | undefined) => EntityType | undefined;

  // Data transformation
  transformToForm: (entity: EntityType | undefined) => FormData;

  // Validation
  schema: ZodSchema<FormData>;

  // Persistence
  saveEntity: (formData: FormData, entityId: string | undefined, isCreating: boolean) => Promise<void>;

  // Callbacks
  onSaveSuccess?: () => void;
  onCancel?: () => void;
  onDirtyStateChange?: (isDirty: boolean) => void;
}

export interface UseRadixFormReturn<FormData> {
  // Form data
  formData: FormData;
  setFormData: React.Dispatch<React.SetStateAction<FormData>>;

  // State
  isDirty: boolean;
  isSaving: boolean;
  isCreating: boolean;
  saveError: AppError | null;

  // Actions
  handleSave: () => Promise<void>;
  handleCancel: () => void;
  handleFieldChange: (field: keyof FormData, value: any) => void;

  // Form state for external components
  formState: {
    canSave: boolean;
    isSaving: boolean;
    isCreating: boolean;
    saveError: AppError | null;
    handleSave: () => void;
    handleCancel: () => void;
  };
}

export function useRadixForm<EntityType, FormData>({
  entityId,
  getEntity,
  transformToForm,
  schema,
  saveEntity,
  onSaveSuccess,
  onCancel,
  onDirtyStateChange,
}: UseRadixFormConfig<EntityType, FormData>): UseRadixFormReturn<FormData> {
  const [isSaving, setIsSaving] = React.useState(false);
  const [saveError, setSaveError] = React.useState<AppError | null>(null);
  const [isDirty, setIsDirty] = React.useState(false);

  // Get entity data if editing
  const entity = React.useMemo(() => {
    if (!entityId) return undefined;
    return getEntity(entityId);
  }, [entityId, getEntity]);

  const isCreating = !entityId;

  // Initialize form data
  const [formData, setFormData] = React.useState<FormData>(() => transformToForm(entity));

  // Track dirty state
  React.useEffect(() => {
    const initialData = transformToForm(entity);
    const hasChanges = JSON.stringify(formData) !== JSON.stringify(initialData);
    setIsDirty(hasChanges);
    onDirtyStateChange?.(hasChanges);
  }, [formData, entity, transformToForm, onDirtyStateChange]);

  // Reset form data when entity changes
  React.useEffect(() => {
    setFormData(transformToForm(entity));
    setIsDirty(false);
  }, [entity, transformToForm]);

  const handleSave = React.useCallback(async () => {
    try {
      setIsSaving(true);
      setSaveError(null);

      // Validate form data
      const validatedData = schema.parse(formData);

      // Save entity
      await saveEntity(validatedData, entityId || undefined, isCreating);

      // Reset dirty state
      setIsDirty(false);

      onSaveSuccess?.();
    } catch (error) {
      console.error('Save failed', error);
      setSaveError(error as AppError);
    } finally {
      setIsSaving(false);
    }
  }, [formData, schema, saveEntity, entityId, isCreating, onSaveSuccess]);

  const handleCancel = React.useCallback(() => {
    // Reset form to initial state
    setFormData(transformToForm(entity));
    setIsDirty(false);
    onCancel?.();
  }, [entity, transformToForm, onCancel]);

  const handleFieldChange = React.useCallback((field: keyof FormData, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  }, []);

  const formState = React.useMemo(
    () => ({
      canSave: isDirty && !isSaving,
      isSaving,
      isCreating,
      saveError,
      handleSave,
      handleCancel,
    }),
    [isDirty, isSaving, isCreating, saveError, handleSave, handleCancel],
  );

  return {
    formData,
    setFormData,
    isDirty,
    isSaving,
    isCreating,
    saveError,
    handleSave,
    handleCancel,
    handleFieldChange,
    formState,
  };
}
