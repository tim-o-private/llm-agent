import { ZodSchema } from 'zod';
import { UseFormReturn, FieldValues } from 'react-hook-form';
import { AppError } from './error'; // Assuming AppError is in a sibling file or imported correctly
import { /* Task, */ TaskStatus, TaskPriority } from '@/api/types'; // Ensure correct path. Task itself is not directly used by these generic types.

// Type for the function that retrieves entity data, likely from a Zustand store
export type GetEntityDataFn<TEntityData> = (entityId: string | undefined) => TEntityData | undefined;

// Type for the function that saves entity data, by dispatching to a Zustand store
// Returns a Promise that can resolve upon optimistic update or after queuing.
export type SaveEntityFn<TFormData, TEntityData> = (
  formData: TFormData,
  originalEntityData: TEntityData | undefined, // To help Zustand action with diffing or context
  entityId?: string | undefined
) => Promise<void | TEntityData>; // Returns void or the optimistically updated/created entity

export interface UseEditableEntityConfig<
  TEntityData,
  TFormData extends FieldValues,
> {
  entityId: string | null | undefined;
  getEntityDataFn: GetEntityDataFn<TEntityData>;
  saveEntityFn: SaveEntityFn<TFormData, TEntityData>;
  transformDataToForm: (entityData: TEntityData | undefined) => TFormData;
  // transformFormToSaveData is implicitly handled by what's passed to saveEntityFn
  formSchema: ZodSchema<TFormData>;
  defaultFormValues?: TFormData; // For creating new entities or as a fallback
  entityName: string; // For logging, UI messages
  onSaveSuccess?: (updatedData: TEntityData | void, formValues: TFormData) => void; // Callback after successful Zustand dispatch
  onSaveError?: (error: AppError | Error, formValues: TFormData) => void; // Callback if Zustand dispatch fails (e.g., validation within store action)
  isCreatable?: boolean;
}

export interface UseEditableEntityReturn<
  TEntityData,
  TFormData extends FieldValues,
> {
  formMethods: UseFormReturn<TFormData>;
  isSaving: boolean; // Reflects the state of the saveEntityFn call
  // isLoadingInitialData is now more about whether data is present from getEntityDataFn
  // and if the store itself has a loading state for that data.
  // This might need to be derived or passed in if Zustand has per-entity loading states.
  // For simplicity, we'll assume data is available or undefined synchronously from Zustand for the form.
  initialDataError: AppError | Error | null; // Errors from attempting to save (Zustand dispatch phase)
  saveError: AppError | Error | null;
  canSave: boolean; // formMethods.formState.isDirty && formMethods.formState.isValid
  handleSave: () => Promise<void>;
  resetFormToInitial: () => void;
  initialData: TEntityData | undefined; // Data as sourced from getEntityDataFn
  isCreating: boolean;
}

// Example FormData for a Task
export interface TaskFormData {
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date?: string | null;
  // ... other editable fields from Task interface
} 