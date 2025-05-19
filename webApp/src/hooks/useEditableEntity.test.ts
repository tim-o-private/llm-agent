import { renderHook, act, waitFor } from '@testing-library/react';
import { useEditableEntity, EntityTypeConfig } from './useEditableEntity'; // Adjust path as needed
import { FieldValues, useForm, Control } from 'react-hook-form'; // Import necessary RHF types
import { DragEndEvent } from '@dnd-kit/core'; // Import DragEndEvent
import { vi, describe, test, expect, beforeEach } from 'vitest'; // IMPORT vi and test globals

// --- Mock react-hook-form ---
// This object will be the return value of our mocked useForm
const mockUseFormReturnValue = {
  watch: vi.fn(),
  getValues: vi.fn(),
  setValue: vi.fn(),
  reset: vi.fn(),
  handleSubmit: vi.fn((cb) => (...args: any[]) => cb(...args)), // Executes the callback passed to handleSubmit
  control: {} as Control<any>, // Basic mock for Control
  formState: {
    isDirty: false,
    isValid: true,
    errors: {},
    // Add other formState properties if useEditableEntity relies on them
  },
  // Add other RHF methods if the hook uses them, e.g., trigger, setError, clearErrors
};

vi.mock('react-hook-form', async () => {
  const actualRHF = await vi.importActual('react-hook-form');
  return {
    ...actualRHF,
    useForm: vi.fn(() => mockUseFormReturnValue), // Our mock useForm returns the controllable object
  };
});
// --- End Mock react-hook-form ---

// Mocks
// Mock lodash-es
vi.mock('lodash-es', () => ({ 
  cloneDeep: vi.fn(data => JSON.parse(JSON.stringify(data))),
  isEqual: vi.fn((a, b) => JSON.stringify(a) === JSON.stringify(b)), 
}));
// Mock dnd-kit if reordering is tested
// vi.mock('@dnd-kit/core', async () => {
//   const actual = await vi.importActual('@dnd-kit/core');
//   return {
//     ...actual,
//     useSensors: vi.fn(), 
//     useSensor: vi.fn(), 
//     PointerSensor: vi.fn(), 
//     KeyboardSensor: vi.fn(), 
//   };
// });
// vi.mock('@dnd-kit/sortable', async () => {
//   const actual = await vi.importActual('@dnd-kit/sortable');
//   return {
//     ...actual,
//     arrayMove: vi.fn((arr, from, to) => { 
//       const newArr = [...arr];
//       const [item] = newArr.splice(from, 1);
//       newArr.splice(to, 0, item);
//       return newArr;
//     }),
//   };
// });


interface TestEntity {
  id: string;
  name: string;
  value: number;
  subItems?: TestSubItem[];
}

interface TestFormData extends FieldValues {
  name: string;
  value: number;
}

interface TestSubItem {
  subId: string;
  text: string;
}

const mockEntityId = 'entity-1';
const mockInitialEntity: TestEntity = {
  id: mockEntityId,
  name: 'Initial Name',
  value: 100,
  subItems: [{ subId: 'sub-1', text: 'Sub Item 1' }],
};

const mockTransformDataToForm = (entity?: TestEntity): TestFormData => {
  if (!entity) return { name: '', value: 0 };
  return { name: entity.name, value: entity.value };
};

// Updated mock to handle broader input types from PathValue<TEntityData, Path<TEntityData>>
const mockTransformSubCollectionToList = (subCollection: any): TestSubItem[] => {
  // Check if subCollection is specifically the TestSubItem[] we expect from 'subItems' path
  if (Array.isArray(subCollection) && 
      (subCollection.length === 0 || 
       (typeof subCollection[0] === 'object' && subCollection[0] !== null && 'subId' in subCollection[0]))) {
    return subCollection as TestSubItem[];
  }
  // For other path types (string, number from other TestEntity fields), return empty array
  return [];
};

// Type for the queryHook mock
type MockQueryHook = (id: string | null | undefined) => {
  data: TestEntity | undefined;
  isLoading: boolean;
  isFetching: boolean;
  error: any;
};

// Type for the saveHandler mock
type MockSaveHandler = (
  originalEntity: TestEntity | null,
  currentFormData: TestFormData,
  currentSubEntityList: TestSubItem[] | undefined
) => Promise<TestEntity | void>;

describe('useEditableEntity', () => {
  let mockQueryHook: ReturnType<typeof vi.fn<Parameters<MockQueryHook>, ReturnType<MockQueryHook>>>;
  let mockSaveHandler: ReturnType<typeof vi.fn<Parameters<MockSaveHandler>, ReturnType<MockSaveHandler>>>;
  // let mockFormMethods: Partial<UseFormReturn<TestFormData>>; // REMOVED
  // let actualUseForm: any; // REMOVED

  // Define a reusable mock for RHF's formState
  //const mockFormState = (isDirty: boolean) => ({
  //  isDirty,
  //  isValid: true, // Add other relevant properties
  //  errors: {},
    //  touchedFields: {},
    // ... any other formState properties used by the hook
  //});

  beforeEach(() => {
    // vi.resetAllMocks(); // DO NOT use vi.resetAllMocks()

    if (mockQueryHook) mockQueryHook.mockClear();
    if (mockSaveHandler) mockSaveHandler.mockClear();

    // Clear the mocked react-hook-form's useForm function itself
    // After vi.mock, useForm is a Vitest mock function.
    if (useForm && typeof (useForm as any).mockClear === 'function') {
      (useForm as any).mockClear();
    }
    // The top-level vi.mock ensures useForm still returns mockUseFormReturnValue.

    // Reset the state/methods of the object *returned* by the mocked useForm
    mockUseFormReturnValue.watch.mockClear();
    mockUseFormReturnValue.getValues.mockClear().mockReturnValue({ name: 'Initial Name', value: 100 }); 
    mockUseFormReturnValue.setValue.mockClear();
    mockUseFormReturnValue.reset.mockClear();
    mockUseFormReturnValue.handleSubmit.mockClear().mockImplementation((cb) => async (...args:any[]) => await cb(...args));
    
    let currentIsDirty = false;
    Object.defineProperty(mockUseFormReturnValue, 'formState', {
      value: {
        get isDirty() { return currentIsDirty; },
        set isDirty(val: boolean) { currentIsDirty = val; },
        isValid: true,
        errors: {},
      },
      configurable: true, 
    });
    mockUseFormReturnValue.formState.isDirty = false; 

    // Re-initialize mockQueryHook and mockSaveHandler by assignment (this also clears them)
    mockQueryHook = vi.fn<Parameters<MockQueryHook>, ReturnType<MockQueryHook>>().mockReturnValue({
      data: undefined,
      isLoading: true,
      isFetching: true,
      error: null,
    });
    mockSaveHandler = vi.fn<Parameters<MockSaveHandler>, ReturnType<MockSaveHandler>>().mockResolvedValue(undefined);
  });

  const getMockConfig = (overrides: Partial<EntityTypeConfig<TestEntity, TestFormData, TestSubItem, TestSubItem>> = {}): EntityTypeConfig<TestEntity, TestFormData, TestSubItem, TestSubItem> => ({
    entityId: mockEntityId,
    queryHook: mockQueryHook,
    transformDataToForm: mockTransformDataToForm,
    saveHandler: mockSaveHandler,
    subEntityListItemIdField: 'subId', // This should now be keyof TestSubItem
    // Ensure other relevant sub-entity config fields are provided if needed by tests below, e.g.:
    subEntityPath: 'subItems', // Assuming this is the path in TestEntity
    transformSubCollectionToList: mockTransformSubCollectionToList, // Add this
    ...overrides,
  });

  test('should initialize with loading state', () => {
    const { result } = renderHook(() => useEditableEntity(getMockConfig()));
    expect(result.current.isLoading).toBe(true);
    expect(result.current.isFetching).toBe(true);
    expect(result.current.error).toBeNull();
    expect(result.current.originalEntity).toBeNull();
  });

  test('should update state on successful data fetch', async () => {
    mockQueryHook.mockReturnValue({
      data: mockInitialEntity,
      isLoading: false,
      isFetching: false,
      error: null,
    });
    const { result } = renderHook(() => useEditableEntity(getMockConfig()));

    await waitFor(() => {
      expect(result.current.originalEntity).toEqual(mockInitialEntity);
    });
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isFetching).toBe(false);
    });
  });
  
  test('should handle create mode (entityId is null)', async () => {
    mockQueryHook.mockReturnValue({ // queryHook might return undefined for null id
      data: undefined,
      isLoading: false,
      isFetching: false,
      error: null,
    });
    const { result } = renderHook(() => useEditableEntity(getMockConfig({ entityId: null })));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isFetching).toBe(false);
    });
    expect(result.current.originalEntity).toBeNull();
    // Expect formMethods.reset to have been called with default empty form data
  });

  test('should set error state on fetch error', async () => {
    const fetchError = new Error('Fetch failed');
    mockQueryHook.mockReturnValue({
      data: undefined,
      isLoading: false,
      isFetching: false,
      error: fetchError,
    });
    const { result } = renderHook(() => useEditableEntity(getMockConfig()));

    await waitFor(() => {
      expect(result.current.error).toBe(fetchError);
    });
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
  });

  // Test for form dirty state
  test('isMainFormDirty should reflect RHF form state', async () => {
    const { result, rerender } = renderHook((props) => useEditableEntity(props), {
      initialProps: getMockConfig(),
    });

    // Initial state from mock
    expect(result.current.isMainFormDirty).toBe(false);

    // Simulate form becoming dirty
    act(() => {
      // Directly modify the isDirty property of the object returned by the mocked useForm
      mockUseFormReturnValue.formState.isDirty = true;
    });

    // Rerender the hook to pick up the changed mock state
    // This simulates React re-rendering the component that uses useEditableEntity,
    // which in turn causes useEditableEntity to re-evaluate based on the new formState.
    rerender(getMockConfig()); 

    expect(result.current.isMainFormDirty).toBe(true);

    // Simulate form becoming clean again
    act(() => {
      mockUseFormReturnValue.formState.isDirty = false;
    });
    rerender(getMockConfig());
    expect(result.current.isMainFormDirty).toBe(false);
  });

  test('handleSave should call saveHandler and update state on success (with returned entity)', async () => {
    const updatedEntity = { ...mockInitialEntity, name: 'Updated Name' };
    mockSaveHandler.mockResolvedValue(updatedEntity); // saveHandler returns the updated entity
    
    mockQueryHook.mockReturnValue({ // Initial load
      data: mockInitialEntity, isLoading: false, isFetching: false, error: null,
    });

    // Simulate form data that would be passed to saveHandler
    const formDataForSave = { name: 'Updated Name', value: 100 };
    mockUseFormReturnValue.getValues.mockReturnValue(formDataForSave);

    const { result, rerender } = renderHook(() => useEditableEntity(getMockConfig()));
    
    await waitFor(() => {
      expect(result.current.originalEntity).toEqual(mockInitialEntity);
    });

    // Simulate form being dirty before save
    act(() => {
      mockUseFormReturnValue.formState.isDirty = true;
    });
    rerender(); // Rerender to reflect dirty state if necessary for the hook's logic

    await act(async () => {
      await result.current.handleSave(); // This will internally call the mocked handleSubmit
    });

    expect(mockSaveHandler).toHaveBeenCalledWith(
      mockInitialEntity, 
      formDataForSave, // Check that getValues was used
      mockInitialEntity.subItems || [] // Expect subItems if originalEntity has them
    );
    await waitFor(() => {
      expect(result.current.originalEntity).toEqual(updatedEntity); // Snapshot updated
    });
    expect(result.current.isSaving).toBe(false);
    expect(result.current.error).toBeNull();
    // Verify RHF reset was called with the new data to clear dirty state
    expect(mockUseFormReturnValue.reset).toHaveBeenCalledWith(mockTransformDataToForm(updatedEntity));
    // After reset, form should not be dirty (assuming RHF mock handles this)
    act(() => {
        mockUseFormReturnValue.formState.isDirty = false; // Simulate RHF resetting its dirty state
    });
    rerender();
    expect(result.current.isMainFormDirty).toBe(false);
  });
  
  test('handleSave should call saveHandler and reset RHF dirty state on success (void return)', async () => {
    mockSaveHandler.mockResolvedValue(undefined); // saveHandler returns void
    
    mockQueryHook.mockReturnValue({
      data: mockInitialEntity, isLoading: false, isFetching: false, error: null,
    });

    const formDataForSave = { name: 'Current Form Name', value: 120 }; // Different from initial
    mockUseFormReturnValue.getValues.mockReturnValue(formDataForSave);

    const { result, rerender } = renderHook(() => useEditableEntity(getMockConfig()));

    await waitFor(() => {
      expect(result.current.originalEntity).toEqual(mockInitialEntity);
    });

    // Simulate form being dirty
    act(() => {
      mockUseFormReturnValue.formState.isDirty = true;
    });
    rerender();

    await act(async () => {
      await result.current.handleSave();
    });

    expect(mockSaveHandler).toHaveBeenCalledWith(mockInitialEntity, formDataForSave, mockInitialEntity.subItems || []);
    await waitFor(() => {
      // Original entity should remain unchanged if saveHandler returns void
      expect(result.current.originalEntity).toEqual(mockInitialEntity);
    });
    expect(result.current.isSaving).toBe(false);
    // Verify RHF reset was called with the current form data (or transformed original if non-destructive save)
    // Hook resets with transformed original entity if saveHandler is void and successful
    expect(mockUseFormReturnValue.reset).toHaveBeenCalledWith(mockTransformDataToForm(mockInitialEntity));
    act(() => {
        mockUseFormReturnValue.formState.isDirty = false; // Simulate RHF resetting its dirty state
    });
    rerender();
    expect(result.current.isMainFormDirty).toBe(false);
  });

  test('handleSave should set error state on saveHandler failure', async () => {
    const saveError = new Error('Save failed');
    mockSaveHandler.mockRejectedValue(saveError);
    
    mockQueryHook.mockReturnValue({
      data: mockInitialEntity, isLoading: false, isFetching: false, error: null,
    });
    const { result, rerender } = renderHook(() => useEditableEntity(getMockConfig()));

    await waitFor(() => {
      expect(result.current.originalEntity).toEqual(mockInitialEntity);
    });

    // Simulate form being dirty to allow saveHandler to be called
    act(() => {
      mockUseFormReturnValue.formState.isDirty = true;
    });
    rerender(); // Ensure the hook re-evaluates combinedIsDirty

    await act(async () => {
      await result.current.handleSave();
    });

    expect(result.current.isSaving).toBe(false);
    await waitFor(() => expect(result.current.error?.message).toBe(saveError.message));
  });

  test('handleCancel should reset form and call onCancel callback', async () => {
    const mockOnCancel = vi.fn();
    mockQueryHook.mockReturnValue({
      data: mockInitialEntity, isLoading: false, isFetching: false, error: null,
    });

    // Simulate form data being different from initial to be resettable
    mockUseFormReturnValue.getValues.mockReturnValue({ name: 'Changed Name', value: 150 });
    act(() => {
      mockUseFormReturnValue.formState.isDirty = true; // Simulate form was dirty
    });

    const { result, rerender } = renderHook(() => useEditableEntity(getMockConfig({ onCancel: mockOnCancel })));

    await waitFor(() => {
      expect(result.current.originalEntity).toEqual(mockInitialEntity);
    });
    rerender(); // To pick up dirty state if needed for hook logic before cancel

    act(() => {
      result.current.handleCancel();
    });

    // Expect formMethods.reset to be called with original transformed data
    expect(mockUseFormReturnValue.reset).toHaveBeenCalledWith(mockTransformDataToForm(mockInitialEntity));
    expect(mockOnCancel).toHaveBeenCalled();
    // Simulate RHF form becoming clean after reset
    act(() => {
      mockUseFormReturnValue.formState.isDirty = false;
    });
    rerender();
    expect(result.current.isMainFormDirty).toBe(false);
  });

  // Tests for sub-entity CRUD, dirty state, and DND would follow a similar pattern:
  // - Configure the hook with subEntityPath, transformSubCollectionToList, etc.
  // - Use `act` to call addSubItem, updateSubItem, removeSubItem, handleDragEnd.
  // - Assert changes to `result.current.subEntityList` and `result.current.isSubEntityListDirty`.
  // - Assert `isDirty` reflects combined state.

  test('addSubItem should add an item to subEntityList and set dirty states', async () => {
    // Initial entity with one sub-item
    const initialEntityWithSubItem: TestEntity = {
      ...mockInitialEntity,
      subItems: [{ subId: 'sub-1', text: 'Sub Item 1' }],
    };
    mockQueryHook.mockReturnValue({ data: initialEntityWithSubItem, isLoading: false, isFetching: false, error: null });
    
    // Mock useForm to return a controllable formState
    // const formMethodsInstance = { // REMOVED
    //   watch: jest.fn(),
    //   getValues: jest.fn().mockReturnValue(mockTransformDataToForm(initialEntityWithSubItem)),
    //   setValue: jest.fn(),
    //   reset: jest.fn(),
    //   handleSubmit: jest.fn(cb => (...args: any[]) => cb(...args)),
    //   formState: mockFormState(false), // Start not dirty
    //   control: {} as any,
    // };
    // This direct mock of useForm import is problematic here. 
    // It's better to use vi.mock at the top of the file.
    // For now, assuming the hook uses a passed useForm or a globally available one.
    // (useForm as vi.Mock).mockReturnValue(formMethodsInstance); // This won't work as useForm is an import

    const { result } = renderHook(
      (props) => useEditableEntity(props), 
      { initialProps: getMockConfig({ subEntityPath: 'subItems', transformSubCollectionToList: mockTransformSubCollectionToList }) }
    );
    
    await waitFor(() => {
      expect(result.current.subEntityList).toEqual(initialEntityWithSubItem.subItems);
      expect(result.current.isSubEntityListDirty).toBe(false);
    });
    expect(result.current.isDirty).toBe(false); // Combined dirty state

    const newSubItem: TestSubItem = { subId: 'sub-2', text: 'New Sub Item' };
    act(() => {
      result.current.addSubItem(newSubItem);
    });
    
    expect(result.current.subEntityList).toContainEqual(newSubItem);
    expect(result.current.subEntityList.length).toBe(2);
    expect(result.current.isSubEntityListDirty).toBe(true);
    expect(result.current.isDirty).toBe(true); // Combined dirty state
  });

  describe('Sub-entity list management', () => {
    const initialEntityWithTwoSubItems: TestEntity = {
      id: 'entity-1',
      name: 'Parent',
      value: 1,
      subItems: [
        { subId: 'sub-a', text: 'Alpha' },
        { subId: 'sub-b', text: 'Bravo' },
      ],
    };

    // rhfFormStateIsDirty and mockRHFMethods are no longer needed here,
    // as these are handled by the global mockUseFormReturnValue and its setup in beforeEach.

    const setupHookWithSubItems = (initialData: TestEntity = initialEntityWithTwoSubItems) => {
      mockQueryHook.mockReturnValue({ data: initialData, isLoading: false, isFetching: false, error: null });
      
      // Configure getValues for the main form based on initialData for this specific setup
      mockUseFormReturnValue.getValues.mockReturnValue(mockTransformDataToForm(initialData));
      // Ensure main form starts as not dirty for these sub-entity tests unless specified
      mockUseFormReturnValue.formState.isDirty = false;

      return renderHook(
        (props) => useEditableEntity(props), 
        { 
          initialProps: getMockConfig({
            entityId: initialData.id,
            subEntityPath: 'subItems',
            transformSubCollectionToList: mockTransformSubCollectionToList,
            enableSubEntityReordering: true, 
          })
        }
      );
    };

    beforeEach(() => {
      // Reset main form dirty state for tests within this describe block
      // This is already handled by the top-level beforeEach, but explicit here for clarity if needed.
      // mockUseFormReturnValue.formState.isDirty = false;
      // mockUseFormReturnValue.getValues.mockReturnValue(mockTransformDataToForm(initialEntityWithTwoSubItems));
      mockSaveHandler.mockClear(); // Ensure save handler is clean for save tests
    });

    test('updateSubItem should update an item and set dirty state', async () => {
      const { result, rerender } = setupHookWithSubItems(); // Use rerender if needed
      
      await waitFor(() => {
        expect(result.current.subEntityList[0].text).toBe('Alpha');
        expect(result.current.isSubEntityListDirty).toBe(false);
      });
      expect(result.current.isDirty).toBe(false); // Combined dirty state

      act(() => {
        result.current.updateSubItem('sub-a', { text: 'Alpha-Updated' });
      });
      rerender(getMockConfig({
        entityId: initialEntityWithTwoSubItems.id,
        subEntityPath: 'subItems',
        transformSubCollectionToList: mockTransformSubCollectionToList,
        enableSubEntityReordering: true,
      }));

      expect(result.current.subEntityList[0].text).toBe('Alpha-Updated');
      expect(result.current.isSubEntityListDirty).toBe(true);
      expect(result.current.isDirty).toBe(true);

      act(() => {
        result.current.updateSubItem('sub-b', (prev) => ({ ...prev, text: prev.text + '-Suffix' }));
      });
      rerender(getMockConfig({
        entityId: initialEntityWithTwoSubItems.id,
        subEntityPath: 'subItems',
        transformSubCollectionToList: mockTransformSubCollectionToList,
        enableSubEntityReordering: true,
      }));
      expect(result.current.subEntityList[1].text).toBe('Bravo-Suffix');
      expect(result.current.isSubEntityListDirty).toBe(true); 
    });

    test('removeSubItem should remove an item and set dirty state', async () => {
      const { result, rerender } = setupHookWithSubItems();
      
      await waitFor(() => {
        expect(result.current.subEntityList.length).toBe(2);
        expect(result.current.isSubEntityListDirty).toBe(false);
      });

      act(() => {
        result.current.removeSubItem('sub-a');
      });
      rerender(getMockConfig({
        entityId: initialEntityWithTwoSubItems.id,
        subEntityPath: 'subItems',
        transformSubCollectionToList: mockTransformSubCollectionToList,
        enableSubEntityReordering: true,
      }));

      expect(result.current.subEntityList.length).toBe(1);
      expect(result.current.subEntityList.find(item => item.subId === 'sub-a')).toBeUndefined();
      expect(result.current.subEntityList[0].subId).toBe('sub-b');
      expect(result.current.isSubEntityListDirty).toBe(true);
      expect(result.current.isDirty).toBe(true);
    });

    test('handleDragEnd should reorder items and set dirty state', async () => {
      const { result, rerender } = setupHookWithSubItems();
      
      await waitFor(() => {
        expect(result.current.subEntityList[0].subId).toBe('sub-a');
        expect(result.current.subEntityList[1].subId).toBe('sub-b');
        expect(result.current.isSubEntityListDirty).toBe(false);
      });

      const mockDragEndEvent = {
        active: { id: 'sub-a' },
        over: { id: 'sub-b' },
      } as DragEndEvent;

      act(() => {
        if (result.current.dndContextProps?.onDragEnd) { 
          result.current.dndContextProps.onDragEnd(mockDragEndEvent);
        }
      });
      rerender(getMockConfig({
        entityId: initialEntityWithTwoSubItems.id,
        subEntityPath: 'subItems',
        transformSubCollectionToList: mockTransformSubCollectionToList,
        enableSubEntityReordering: true, 
      }));

      expect(result.current.subEntityList[0].subId).toBe('sub-b');
      expect(result.current.subEntityList[1].subId).toBe('sub-a');
      expect(result.current.isSubEntityListDirty).toBe(true);
      expect(result.current.isDirty).toBe(true);
    });

    test('isDirty should be true if main form is dirty, even if sub-list is not', async () => {
      const { result, rerender } = setupHookWithSubItems(); // Sub-list will be clean initially
      
      await waitFor(() => {
        expect(result.current.isDirty).toBe(false);
        expect(result.current.isSubEntityListDirty).toBe(false);
        expect(result.current.isMainFormDirty).toBe(false);
      });
      
      act(() => {
        mockUseFormReturnValue.formState.isDirty = true; // Simulate RHF form becoming dirty
      });
      rerender(getMockConfig({
        entityId: initialEntityWithTwoSubItems.id,
        subEntityPath: 'subItems',
        transformSubCollectionToList: mockTransformSubCollectionToList,
        enableSubEntityReordering: true, 
      }));

      expect(result.current.isMainFormDirty).toBe(true);
      expect(result.current.isSubEntityListDirty).toBe(false); 
      expect(result.current.isDirty).toBe(true);
    });

    test('handleSave should include modified subEntityList', async () => {
      const { result, rerender } = setupHookWithSubItems();
      const newSubItem: TestSubItem = { subId: 'sub-c', text: 'Charlie' };
      const updatedText = 'Alpha-Modified';

      act(() => {
        result.current.addSubItem(newSubItem); 
        result.current.updateSubItem('sub-a', { text: updatedText }); 
      });
      rerender(getMockConfig({
        entityId: initialEntityWithTwoSubItems.id,
        subEntityPath: 'subItems',
        transformSubCollectionToList: mockTransformSubCollectionToList,
        enableSubEntityReordering: true, 
      }));

      expect(result.current.isDirty).toBe(true); // Both sub-list and main form (potentially) are dirty

      const changedMainFormData = { ...mockTransformDataToForm(initialEntityWithTwoSubItems), name: "Parent-Changed" };
      mockUseFormReturnValue.getValues.mockReturnValue(changedMainFormData); // Simulate main form changes
      act(() => {
          mockUseFormReturnValue.formState.isDirty = true; // Ensure main form is marked dirty for combined isDirty state
      });
      rerender(getMockConfig({
        entityId: initialEntityWithTwoSubItems.id,
        subEntityPath: 'subItems',
        transformSubCollectionToList: mockTransformSubCollectionToList,
        enableSubEntityReordering: true, 
      }));

      // Mock saveHandler to return an entity that reflects the save
      // For this test, let's assume the backend returns the full entity with updated subitems
      const savedEntityStateFromBackend = {
        ...initialEntityWithTwoSubItems, // Base original entity
        name: changedMainFormData.name, // Updated name from form
        subItems: [ // Expected subItem state AFTER save
          { subId: 'sub-a', text: updatedText },
          { subId: 'sub-b', text: 'Bravo' },
          newSubItem,
        ],
      };
      mockSaveHandler.mockResolvedValue(savedEntityStateFromBackend);

      await act(async () => {
        await result.current.handleSave();
      });
      
      const expectedSubListPayloadForBackend = [
        { subId: 'sub-a', text: updatedText },
        { subId: 'sub-b', text: 'Bravo' },
        newSubItem,
      ];

      expect(mockSaveHandler).toHaveBeenCalledTimes(1); 
      expect(mockSaveHandler).toHaveBeenCalledWith(
        initialEntityWithTwoSubItems, 
        changedMainFormData,              
        expect.arrayContaining(expectedSubListPayloadForBackend.map(item => expect.objectContaining(item)))
      );
      
      const saveHandlerCallArgs = mockSaveHandler.mock.calls[0];
      expect(saveHandlerCallArgs[2]).toHaveLength(expectedSubListPayloadForBackend.length);

      expect(result.current.isSaving).toBe(false);
      await waitFor(() => expect(result.current.error).toBeNull());

      // Verify RHF reset was called with the new data
      expect(mockUseFormReturnValue.reset).toHaveBeenCalledWith(mockTransformDataToForm(savedEntityStateFromBackend));
      // After reset, form should not be dirty. Simulate this effect on the mock.
      act(() => {
        mockUseFormReturnValue.formState.isDirty = false;
      });
      // Rerender to ensure hook picks up the change in mockUseFormReturnValue.formState.isDirty
      rerender(getMockConfig({
        entityId: initialEntityWithTwoSubItems.id,
        subEntityPath: 'subItems',
        transformSubCollectionToList: mockTransformSubCollectionToList,
        enableSubEntityReordering: true, 
      }));

      await waitFor(() => { 
        expect(result.current.originalEntity!).toEqual(savedEntityStateFromBackend); 
        // Form and sub-list should be reset and not dirty
        expect(result.current.isMainFormDirty).toBe(false); // Check main form first
        expect(result.current.subEntityList).toEqual(savedEntityStateFromBackend.subItems); 
        expect(result.current.isSubEntityListDirty).toBe(false); 
        expect(result.current.isDirty).toBe(false); // Then check combined dirty state
      });
    });

    test('resetState should revert subEntityList changes and main form', async () => {
      // Define the specific config for this test instance
      const currentTestConfig = getMockConfig({
        entityId: initialEntityWithTwoSubItems.id,
        subEntityPath: 'subItems',
        transformSubCollectionToList: mockTransformSubCollectionToList,
        enableSubEntityReordering: true, // Assuming this is intended for the initial setup
      });

      // Ensure mocks are configured according to initialEntityWithTwoSubItems for this test config
      mockQueryHook.mockReturnValue({ data: initialEntityWithTwoSubItems, isLoading: false, isFetching: false, error: null });
      mockUseFormReturnValue.getValues.mockReturnValue(mockTransformDataToForm(initialEntityWithTwoSubItems));
      mockUseFormReturnValue.formState.isDirty = false; // Start clean for main form

      const { result, rerender } = renderHook(
        (props) => useEditableEntity(props),
        { initialProps: currentTestConfig }
      );
      
      act(() => {
        result.current.addSubItem({ subId: 'sub-c', text: 'Charlie' });
        result.current.updateSubItem('sub-a', { text: 'Alpha-Modified' });
        result.current.removeSubItem('sub-b');
        mockUseFormReturnValue.formState.isDirty = true; // Also make main form dirty
      });
      rerender(currentTestConfig); // Pass config explicitly

      expect(result.current.subEntityList.length).toBe(2); 
      expect(result.current.isSubEntityListDirty).toBe(true);
      expect(result.current.isMainFormDirty).toBe(true);
      expect(result.current.isDirty).toBe(true);
      
      act(() => {
        result.current.resetState();
      });
      rerender(currentTestConfig); // Pass config explicitly - This was the failing line (approx line 500)

      await waitFor(() => {
        expect(result.current.subEntityList).toEqual(initialEntityWithTwoSubItems.subItems);
        expect(result.current.isSubEntityListDirty).toBe(false);
        expect(mockUseFormReturnValue.reset).toHaveBeenCalledWith(mockTransformDataToForm(initialEntityWithTwoSubItems));
        // Simulate RHF reset effect for the next check
        mockUseFormReturnValue.formState.isDirty = false; 
      });
      
      // We need to rerender again for the hook to pick up the changed mockUseFormReturnValue.formState.isDirty
      rerender(currentTestConfig); 

      expect(result.current.isMainFormDirty).toBe(false); 
      expect(result.current.isDirty).toBe(false);
    });
  });
}); 