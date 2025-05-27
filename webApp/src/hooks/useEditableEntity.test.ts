import { renderHook, act, waitFor } from '@testing-library/react';
import { useForm, FormState, Control, SubmitHandler } from 'react-hook-form';
import { z, ZodSchema } from 'zod';
import { vi, describe, test, expect, beforeEach, Mock } from 'vitest';
import { cloneDeep } from 'lodash-es';
import { BaseSyntheticEvent } from 'react';

import { useEditableEntity } from './useEditableEntity';
import { UseEditableEntityConfig, TaskFormData } from '@/types/editableEntityTypes';
import { Task, TaskPriority } from '@/api/types';
import { AppError } from '@/types/error';

// Mock react-hook-form
vi.mock('react-hook-form', async () => {
  const actualRHF = await vi.importActual('react-hook-form');
  return {
    ...actualRHF,
    useForm: vi.fn(),
  };
});

// Mock lodash-es
vi.mock('lodash-es', async () => {
  const actualLodash = await vi.importActual('lodash-es');
  return {
    ...actualLodash,
    cloneDeep: vi.fn(data => {
      if (data === undefined) return undefined; // Handle undefined case
      try {
        return JSON.parse(JSON.stringify(data)); 
      } catch (e) {
        // Fallback or error for complex types not handled by JSON stringify/parse (e.g. functions, Date objects if not stringified properly)
        // For simple test data, this might be okay, but a more robust deep clone might be needed for complex objects.
        // For now, let's assume test data is JSON-friendly or undefined.
        console.error('cloneDeep mock error during JSON.parse(JSON.stringify(data)):', e, 'Data:', data);
        return data; // Or throw, depending on desired strictness for non-JSON-friendly data
      }
    }), 
  };
});


// --- RHF Mock Setup ---
let mockFormStateObject: FormState<TaskFormData>;

const mockGetValues = vi.fn();
const mockReset = vi.fn();
const mockTrigger = vi.fn();

// Typed mockHandleSubmit
const mockHandleSubmit = vi.fn(
  (onValid: SubmitHandler<TaskFormData>) => {
    return async (event?: BaseSyntheticEvent): Promise<void> => {
      const data = mockGetValues(); // mockGetValues() is already set up to return TaskFormData
      try {
        await onValid(data, event);
      } catch (error) { 
        // RHF might handle errors from onValid; for this mock, we can choose to let them propagate or log them.
        // Letting them propagate is often fine for testing the calling code's error handling.
        // console.error('Error in onValid callback during mockHandleSubmit:', error);
        throw error; 
      }
    };
  }
);

const mockUseFormDefaultReturn = {
  getValues: mockGetValues,
  reset: mockReset,
  trigger: mockTrigger,
  handleSubmit: mockHandleSubmit, // Use the new typed mock
  formState: {} as FormState<TaskFormData>,
  control: {} as Control<TaskFormData>,
  register: vi.fn(),
  setValue: vi.fn(),
  clearErrors: vi.fn(),
  setError: vi.fn(),
  watch: vi.fn(),
  getFieldState: vi.fn(),
};
// --- End RHF Mock Setup ---

// --- Test Data and Schemas ---
const testTaskFormSchema: ZodSchema<TaskFormData> = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string().nullable().transform(val => (val === '' ? null : val)),
  status: z.enum(['pending', 'planning', 'in_progress', 'completed', 'skipped', 'deferred']),
  priority: z.union([z.literal(0), z.literal(1), z.literal(2), z.literal(3)]) as ZodSchema<TaskPriority>,
  due_date: z.string().nullable().optional().transform(val => (val === '' ? null : val)),
});

const sampleTaskEntity: Task = {
  id: 'task1',
  user_id: 'user1',
  title: 'Test Task',
  description: 'Test Description',
  status: 'pending',
  priority: 0,
  due_date: null,
  parent_task_id: null,
  completed: false,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  completed_at: null,
};

const taskToFormData = (task?: Task): TaskFormData => {
  if (!task) {
    return { title: '', description: null, status: 'pending', priority: 0, due_date: null };
  }
  return {
    title: task.title,
    description: task.description ?? null,
    status: task.status,
    priority: task.priority,
    due_date: task.due_date ? task.due_date.split('T')[0] : null,
  };
};

const defaultTestFormValues: TaskFormData = taskToFormData(undefined);
// --- End Test Data and Schemas ---

// --- Default Hook Config ---
const getDefaultHookConfig = (
  overrides: Partial<UseEditableEntityConfig<Task, TaskFormData>> = {}
): UseEditableEntityConfig<Task, TaskFormData> => ({
  entityId: null,
  getEntityDataFn: vi.fn() as Mock<[string | undefined], Task | undefined>,
  saveEntityFn: vi.fn() as Mock<[TaskFormData, Task | undefined, string | undefined], Promise<void | Task>>,
  transformDataToForm: vi.fn(taskToFormData) as Mock<[Task | undefined], TaskFormData>,
  formSchema: testTaskFormSchema,
  defaultFormValues: defaultTestFormValues,
  entityName: 'TestEntity',
  isCreatable: true,
  onSaveSuccess: vi.fn(),
  onSaveError: vi.fn(),
  ...overrides,
});
// --- End Default Hook Config ---

describe('useEditableEntity', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFormStateObject = { 
      errors: {}, 
      isDirty: false, 
      isValid: true, 
      isSubmitting: false, 
      isLoading: false, 
      isSubmitted: false, 
      isSubmitSuccessful: false, 
      isValidating: false,
      touchedFields: {},
      dirtyFields: {},
      submitCount: 0,
      disabled: false,
      defaultValues: undefined,
      validatingFields: {},
      isReady: false,
    };
    mockUseFormDefaultReturn.formState = mockFormStateObject;
    (useForm as Mock).mockReturnValue(mockUseFormDefaultReturn);
    
    mockGetValues.mockReturnValue(defaultTestFormValues);
    mockTrigger.mockResolvedValue(true);
    mockReset.mockImplementation((values) => {
      mockGetValues.mockReturnValue(values);
      if (mockFormStateObject) mockFormStateObject.isDirty = false; 
    });
  });

  describe('Initialization', () => {
    test('should initialize for creating a new entity', () => {
      const config = getDefaultHookConfig({ entityId: null, isCreatable: true });
      (config.getEntityDataFn as Mock).mockReturnValue(undefined);
      const expectedInitialFormValues = config.defaultFormValues!;
      // const expectedResolver = zodResolver(config.formSchema); // Keep for clarity, but not for direct comparison if instance equality fails

      const { result } = renderHook(() => useEditableEntity<Task, TaskFormData>(config));

      expect(result.current.isCreating).toBe(true);
      expect(config.getEntityDataFn).toHaveBeenCalledWith(undefined);
      expect(useForm).toHaveBeenCalledWith(
        expect.objectContaining({
          resolver: expect.any(Function), // Loosen resolver check to expect.any(Function)
          defaultValues: expectedInitialFormValues,
        })
      );
      expect(mockReset).toHaveBeenCalledWith(expectedInitialFormValues);
      expect(result.current.initialData).toBeUndefined();
      expect(result.current.saveError).toBeNull();
      expect(result.current.initialDataError).toBeNull();
    });

    test('should initialize for editing an existing entity', () => {
      const config = getDefaultHookConfig({ entityId: sampleTaskEntity.id, isCreatable: false });
      (config.getEntityDataFn as Mock).mockReturnValue(sampleTaskEntity);
      const expectedInitialFormValues = taskToFormData(sampleTaskEntity);
      (config.transformDataToForm as Mock).mockReturnValue(expectedInitialFormValues);
      // const expectedResolver = zodResolver(config.formSchema); // Keep for clarity

      const { result } = renderHook(() => useEditableEntity<Task, TaskFormData>(config));

      expect(result.current.isCreating).toBe(false);
      expect(config.getEntityDataFn).toHaveBeenCalledWith(sampleTaskEntity.id);
      expect(config.transformDataToForm).toHaveBeenCalledWith(sampleTaskEntity);
      expect(useForm).toHaveBeenCalledWith(
        expect.objectContaining({
          resolver: expect.any(Function), // Loosen resolver check
          defaultValues: expectedInitialFormValues,
        })
      );
      expect(mockReset).toHaveBeenCalledWith(expectedInitialFormValues);
      expect(result.current.initialData).toEqual(sampleTaskEntity);
    });
  });

  describe('handleSave', () => {
    test('should not call saveEntityFn if form validation fails', async () => {
      mockTrigger.mockResolvedValue(false); // Simulate validation failure
      const config = getDefaultHookConfig();
      const currentFormValues = { ...defaultTestFormValues, title: "Invalid Data" };
      
      const { result } = renderHook(() => useEditableEntity<Task, TaskFormData>(config));
      
      // Set mockGetValues to return specific data for this save attempt
      mockGetValues.mockReturnValue(currentFormValues);

      await act(async () => { 
        await result.current.handleSave(); 
      });

      // First, ensure the saveError state itself is updated.
      await waitFor(() => {
        expect(result.current.saveError).toBeInstanceOf(Error);
      });
      
      // Now that saveError state is confirmed, check its message and other callbacks/states.
      expect(result.current.saveError?.message).toBe('Form validation failed.');
      expect(config.onSaveError).toHaveBeenCalledTimes(1);
      const onSaveErrorArgs = (config.onSaveError as Mock).mock.calls[0];
      expect(onSaveErrorArgs[0]).toEqual(result.current.saveError); // Match the error instance from state
      expect(onSaveErrorArgs[1]).toEqual(currentFormValues);

      expect(mockTrigger).toHaveBeenCalled();
      expect(config.saveEntityFn).not.toHaveBeenCalled();
      expect(result.current.isSaving).toBe(false);
    });

    test('should call saveEntityFn and onSaveSuccess for CREATE if validation passes', async () => {
      const config = getDefaultHookConfig({ entityId: null, isCreatable: true });
      const formDataToSave = { ...defaultTestFormValues, title: 'New Task' };
      
      (config.getEntityDataFn as Mock).mockReturnValue(undefined);
      const mockSavedEntity = { ...sampleTaskEntity, ...formDataToSave, id: 'newTask1' };
      (config.saveEntityFn as Mock).mockResolvedValue(mockSavedEntity);

      const { result } = renderHook(() => useEditableEntity<Task, TaskFormData>(config));
      
      // Set mockGetValues to return specific data for this save attempt
      mockGetValues.mockReturnValue(formDataToSave);

      await act(async () => { await result.current.handleSave(); });

      expect(config.saveEntityFn).toHaveBeenCalledWith(formDataToSave, undefined, undefined);
      expect(config.onSaveSuccess).toHaveBeenCalledWith(mockSavedEntity, formDataToSave);
      expect(result.current.isSaving).toBe(false);
      expect(result.current.saveError).toBeNull();
    });

    test('should call saveEntityFn and onSaveSuccess for UPDATE if validation passes', async () => {
      const config = getDefaultHookConfig({ entityId: sampleTaskEntity.id, isCreatable: false });
      const formDataToSave = { ...taskToFormData(sampleTaskEntity), title: 'Updated Title' };
      
      (config.getEntityDataFn as Mock).mockReturnValue(sampleTaskEntity); // This sets up initialData
      const mockUpdatedEntity = { ...sampleTaskEntity, ...formDataToSave };
      (config.saveEntityFn as Mock).mockResolvedValue(mockUpdatedEntity);

      const { result } = renderHook(() => useEditableEntity<Task, TaskFormData>(config));

      // Set mockGetValues to return specific data for this save attempt
      mockGetValues.mockReturnValue(formDataToSave);

      await act(async () => { await result.current.handleSave(); });

      expect(config.saveEntityFn).toHaveBeenCalledWith(formDataToSave, cloneDeep(sampleTaskEntity), sampleTaskEntity.id);
      expect(config.onSaveSuccess).toHaveBeenCalledWith(mockUpdatedEntity, formDataToSave);
      expect(result.current.isSaving).toBe(false);
    });

    test('should set saveError and call onSaveError if saveEntityFn throws AppError-like object', async () => {
      const errorObj: AppError = { message: 'Save Failed', code: 'SAVE_OPERATION_FAILED' }; 
      const config = getDefaultHookConfig();
      const formData = { ...defaultTestFormValues, title: "Bad Save" };
      
      (config.saveEntityFn as Mock).mockRejectedValue(errorObj);

      const { result } = renderHook(() => useEditableEntity<Task, TaskFormData>(config));

      // Set mockGetValues to return specific data for this save attempt
      mockGetValues.mockReturnValue(formData);

      await act(async () => { await result.current.handleSave(); });

      expect(result.current.isSaving).toBe(false);
      expect(result.current.saveError).toEqual(errorObj);
      expect(config.onSaveError).toHaveBeenCalledWith(errorObj, formData);
    });

     test('should set saveError and call onSaveError if saveEntityFn throws a generic Error', async () => {
      const error = new Error('Generic Network Error');
      const config = getDefaultHookConfig();
      const formData = { ...defaultTestFormValues, title: "Another Bad Save" };
      
      (config.saveEntityFn as Mock).mockRejectedValue(error);

      const { result } = renderHook(() => useEditableEntity<Task, TaskFormData>(config));
      
      // Set mockGetValues to return specific data for this save attempt
      mockGetValues.mockReturnValue(formData);

      await act(async () => { await result.current.handleSave(); });

      expect(result.current.isSaving).toBe(false);
      expect(result.current.saveError).toEqual(error);
      expect(config.onSaveError).toHaveBeenCalledWith(error, formData);
    });
  });

  describe('resetFormToInitial', () => {
    test('should reset form to default values for create mode and clear saveError', async () => {
      const config = getDefaultHookConfig({ entityId: null, isCreatable: true });
      (config.getEntityDataFn as Mock).mockReturnValue(undefined);
      const expectedResetValues = config.defaultFormValues!;
      
      const { result } = renderHook(() => useEditableEntity<Task, TaskFormData>(config));

      // Simulate a failed save to set saveError
      const saveErrorToSet = new Error("Previous save error");
      (config.saveEntityFn as Mock).mockRejectedValueOnce(saveErrorToSet);
      mockGetValues.mockReturnValueOnce({ ...expectedResetValues, title: "Trigger Save Fail Create" });
      
      await act(async () => {
        await result.current.handleSave();
      });
      
      expect(result.current.saveError).toEqual(saveErrorToSet); // Verify saveError is set

      act(() => { result.current.resetFormToInitial(); });

      expect(mockReset).toHaveBeenCalledWith(expectedResetValues);
      expect(result.current.saveError).toBeNull();
      if (mockFormStateObject) expect(result.current.formMethods.formState.isDirty).toBe(false);
    });

    test('should reset form to original entity values for edit mode and clear saveError', async () => {
      const config = getDefaultHookConfig({ entityId: sampleTaskEntity.id, isCreatable: false });
      (config.getEntityDataFn as Mock).mockReturnValue(sampleTaskEntity); // Initial data for the hook
      const expectedResetValues = taskToFormData(sampleTaskEntity);
      (config.transformDataToForm as Mock).mockReturnValue(expectedResetValues); // Ensure transform returns this

      const { result } = renderHook(() => useEditableEntity<Task, TaskFormData>(config));
      
      // Simulate a failed save to set saveError
      const saveErrorToSet = new Error("Old save error");
      (config.saveEntityFn as Mock).mockRejectedValueOnce(saveErrorToSet);
      mockGetValues.mockReturnValueOnce({ ...expectedResetValues, title: "Trigger Save Fail Edit" });

      await act(async () => { 
        await result.current.handleSave();
      });
      
      expect(result.current.saveError).toEqual(saveErrorToSet); // Verify saveError is set
      
      act(() => { result.current.resetFormToInitial(); });
      
      expect(mockReset).toHaveBeenCalledWith(expectedResetValues);
      expect(result.current.saveError).toBeNull();
      if (mockFormStateObject) expect(result.current.formMethods.formState.isDirty).toBe(false);
    });
  });

  describe('useEffect for entityId changes', () => {
    test('should reset form when entityId changes (editing to another entity)', () => {
      const task1 = { ...sampleTaskEntity, id: 'id1', title: 'Task One' };
      const task1FormData = taskToFormData(task1);
      const initialTransformMock = vi.fn(taskToFormData).mockReturnValue(task1FormData);
      const initialConfig = getDefaultHookConfig({ entityId: 'id1', getEntityDataFn: vi.fn().mockReturnValue(task1), transformDataToForm: initialTransformMock as Mock<[Task | undefined], TaskFormData> });

      const { rerender } = renderHook((props) => useEditableEntity(props), { initialProps: initialConfig });
      expect(initialTransformMock).toHaveBeenCalledWith(task1);
      expect(mockReset).toHaveBeenCalledWith(task1FormData);
      
      mockReset.mockClear(); // Clear mockReset before next action

      const task2 = { ...sampleTaskEntity, id: 'id2', title: 'Task Two' };
      const task2FormData = taskToFormData(task2);
      const newTransformMock = vi.fn(taskToFormData).mockReturnValue(task2FormData);
      const newConfig = { ...initialConfig, entityId: 'id2', getEntityDataFn: vi.fn().mockReturnValue(task2), transformDataToForm: newTransformMock as Mock<[Task | undefined], TaskFormData> };
      
      act(() => rerender(newConfig));

      expect(newConfig.getEntityDataFn).toHaveBeenCalledWith('id2');
      expect(newTransformMock).toHaveBeenCalledWith(task2);
      expect(mockReset).toHaveBeenCalledWith(task2FormData);
      expect(mockReset).toHaveBeenCalledTimes(1); // Only once since clear
    });

    test('should reset form to default for creation when entityId changes from existing to null', () => {
      const task1 = { ...sampleTaskEntity, id: 'id1', title: 'Task One' };
      const task1FormData = taskToFormData(task1);
      const initialTransformMock = vi.fn(taskToFormData).mockReturnValue(task1FormData);
      const initialGetEntityDataFnMock = vi.fn().mockReturnValue(task1);

      const initialConfig = getDefaultHookConfig({ 
        entityId: 'id1', 
        getEntityDataFn: initialGetEntityDataFnMock, 
        transformDataToForm: initialTransformMock as Mock<[Task | undefined], TaskFormData>, 
        isCreatable: true 
      });

      const { rerender, result } = renderHook((props) => useEditableEntity(props), { initialProps: initialConfig });
      expect(initialGetEntityDataFnMock).toHaveBeenCalledWith('id1');
      expect(initialTransformMock).toHaveBeenCalledWith(task1);
      expect(mockReset).toHaveBeenCalledWith(task1FormData);

      mockReset.mockClear(); // Clear reset mock
      initialGetEntityDataFnMock.mockClear(); // Clear getEntity mock
      initialTransformMock.mockClear(); // Clear transform mock

      const createDefaults = { ...defaultTestFormValues, title: "New Create Mode" };
      const createGetEntityDataFnMock = vi.fn().mockReturnValue(undefined);
      const createTransformMock = vi.fn((d?: Task) => {
        if (d === undefined) return createDefaults;
        return taskToFormData(d);
      });
      
      const createConfig = { 
        ...initialConfig, 
        entityId: null, 
        defaultFormValues: createDefaults, 
        getEntityDataFn: createGetEntityDataFnMock, 
        transformDataToForm: createTransformMock as Mock<[Task | undefined], TaskFormData> 
      };
      
      act(() => rerender(createConfig));

      expect(createGetEntityDataFnMock).toHaveBeenCalledWith(undefined);
      expect(mockReset).toHaveBeenCalledWith(createDefaults);
      expect(mockReset).toHaveBeenCalledTimes(1); // Called once after mockClear
      expect(result.current.isCreating).toBe(true);
      expect(result.current.initialData).toBeUndefined();
    });
  });
  
  describe('canSave logic', () => {
    test('should be true if form is dirty and not saving', () => {
      const config = getDefaultHookConfig();
      const { result, rerender } = renderHook(() => useEditableEntity(config));
      act(() => { if (mockFormStateObject) { mockFormStateObject.isDirty = true; } });
      rerender(); 
      expect(result.current.canSave).toBe(true);
    });

    test('should be false if form is not dirty', () => {
      const config = getDefaultHookConfig();
      const { result, rerender } = renderHook(() => useEditableEntity(config));
      act(() => { if (mockFormStateObject) { mockFormStateObject.isDirty = false; } });
      rerender();
      expect(result.current.canSave).toBe(false);
    });

    test('should be false if form is saving', () => {
      const config = getDefaultHookConfig();
      const { result, rerender } = renderHook(() => useEditableEntity(config));
      
      // Set form as dirty first
      act(() => { if (mockFormStateObject) { mockFormStateObject.isDirty = true; } });
      rerender();
      expect(result.current.canSave).toBe(true); // Should be true when dirty and not saving
      
      // Now simulate saving state
      act(() => { 
        // Trigger a save to set isSaving to true
        result.current.handleSave();
      });
      
      expect(result.current.canSave).toBe(false); // Should be false when saving
    });
  });
});
