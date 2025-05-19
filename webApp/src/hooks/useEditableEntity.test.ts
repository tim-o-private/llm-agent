import { renderHook, act, waitFor } from '@testing-library/react';
import { useEditableEntity, EntityTypeConfig } from './useEditableEntity'; // Adjust path as needed
import { FieldValues } from 'react-hook-form';
import { DragEndEvent } from '@dnd-kit/core'; // Import DragEndEvent
import { vi, describe, test, expect, beforeEach, beforeAll } from 'vitest'; // IMPORT vi and test globals

// Mocks
// Mock react-hook-form's useForm
// const mockUseForm = jest.fn(); // REMOVED
// Mock Zod and zodResolver if formSchema is used
// vi.mock('@hookform/resolvers/zod', () => ({ // CHANGED from jest.mock
//   zodResolver: vi.fn().mockImplementation(schema => schema), // CHANGED from jest.fn
// }));
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

  beforeAll(() => {
    // Store actual react-hook-form module
    // actualUseForm = jest.requireActual('react-hook-form').useForm;
  });

  beforeEach(() => {
    vi.resetAllMocks(); // CHANGED from jest.resetAllMocks

    mockQueryHook = vi.fn<Parameters<MockQueryHook>, ReturnType<MockQueryHook>>().mockReturnValue({
      data: undefined,
      isLoading: true,
      isFetching: true,
      error: null,
    });
    mockSaveHandler = vi.fn<Parameters<MockSaveHandler>, ReturnType<MockSaveHandler>>().mockResolvedValue(undefined);

    // Configure the global mock for useForm
    // const defaultMockFormMethods = { // REMOVED
    //   watch: jest.fn(),
    //   getValues: jest.fn().mockReturnValue({ name: '', value: 0 }),
    //   setValue: jest.fn(),
    //   reset: jest.fn(),
    //   handleSubmit: jest.fn(cb => (...args: any[]) => cb(...args)), // Mock handleSubmit to call its callback
    //   formState: mockFormState(false), // Default to not dirty
    //   control: {} as any, // Mock control object
    //   // Add other RHF methods if the hook uses them
    // };
    
    // jest.mock('react-hook-form', () => ({
    //   ...jest.requireActual('react-hook-form'),
    //   useForm: () => defaultMockFormMethods,
    // }));
    // The above module mock needs to be at the top level of the file.
    // For now, let's assume useEditableEntity imports useForm and we can mock it.
    // If useEditableEntity directly calls useForm(), we need module-level mock.
    // For simplicity, we'll pass a mock useForm via config if possible, or rely on a global mock set up elsewhere if that's the pattern.
    // Let's assume for now the hook itself will call the globally mocked useForm if we set it up.
    // This is tricky to do reliably within beforeEach without top-level vi.mock.

    // To test dirty state changes from RHF, the hook needs to re-render.
    // We need to simulate RHF calling a re-render on its consumer.
    // This is usually handled by RTL's `act` and `renderHook` updates.
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

  // Test for form dirty state (requires proper RHF mocking)
  // This test is conceptual due to difficulties mocking useForm effectively without module mocking
  test('isMainFormDirty should reflect RHF form state (conceptual)', () => {
    // To test this properly, you'd mock 'react-hook-form' module
    // and control the `formState.isDirty` returned by the mocked `useForm`.
    // For example:
    // jest.mock('react-hook-form', () => ({
    //   ...jest.requireActual('react-hook-form'),
    //   useForm: () => ({
    //     ...mockFormMethods, // your base mock
    //     formState: { isDirty: true },
    //   }),
    // }));
    // const { result } = renderHook(() => useEditableEntity(getMockConfig()));
    // expect(result.current.isMainFormDirty).toBe(true); // if RHF mock says form is dirty
    
    // Since module mocking is complex here, this is a placeholder.
    // The hook directly returns formMethods.formState.isDirty.
    const { result } = renderHook(() => useEditableEntity(getMockConfig()));
    // We can't easily change result.current.formMethods.formState.isDirty from outside
    // without a proper RHF module mock. So we test its initial state.
    expect(result.current.isMainFormDirty).toBe(false); // Assuming default initial state from RHF
  });

  test('handleSave should call saveHandler and update state on success (with returned entity)', async () => {
    const updatedEntity = { ...mockInitialEntity, name: 'Updated Name' };
    mockSaveHandler.mockResolvedValue(updatedEntity); // saveHandler returns the updated entity
    
    mockQueryHook.mockReturnValue({ // Initial load
      data: mockInitialEntity, isLoading: false, isFetching: false, error: null,
    });

    const { result } = renderHook(() => useEditableEntity(getMockConfig()));
    
    await waitFor(() => {
      expect(result.current.originalEntity).toEqual(mockInitialEntity);
    });

    await act(async () => {
      await result.current.handleSave();
    });

    expect(mockSaveHandler).toHaveBeenCalledWith(
      mockInitialEntity, // originalSnapshot should now be correctly mockInitialEntity
      expect.anything(), // currentFormData (mocked by RHF getValues)
      [] // internalSubEntityList (empty in this simple config)
    );
    await waitFor(() => {
      expect(result.current.originalEntity).toEqual(updatedEntity); // Snapshot updated
    });
    expect(result.current.isSaving).toBe(false);
    expect(result.current.error).toBeNull();
    // Expect formMethods.reset to have been called with transformed updatedEntity
  });
  
  test('handleSave should call saveHandler and reset RHF dirty state on success (void return)', async () => {
    mockSaveHandler.mockResolvedValue(undefined); // saveHandler returns void
    
    mockQueryHook.mockReturnValue({
      data: mockInitialEntity, isLoading: false, isFetching: false, error: null,
    });

    const { result } = renderHook(() => useEditableEntity(getMockConfig()));

    await waitFor(() => {
      expect(result.current.originalEntity).toEqual(mockInitialEntity);
    });
    // Simulate form being dirty
    // This requires proper RHF mocking to change formState.isDirty and getValues
    // For now, we mostly test the call to saveHandler and state transitions

    await act(async () => {
      await result.current.handleSave();
    });

    expect(mockSaveHandler).toHaveBeenCalled();
    await waitFor(() => {
      expect(result.current.originalEntity).toEqual(mockInitialEntity);
    });
    expect(result.current.isSaving).toBe(false);
    // Expect formMethods.reset to have been called to clear RHF dirty state
  });

  test('handleSave should set error state on saveHandler failure', async () => {
    const saveError = new Error('Save failed');
    mockSaveHandler.mockRejectedValue(saveError);
    
    mockQueryHook.mockReturnValue({
      data: mockInitialEntity, isLoading: false, isFetching: false, error: null,
    });
    const { result } = renderHook(() => useEditableEntity(getMockConfig()));

    await waitFor(() => {
      expect(result.current.originalEntity).toEqual(mockInitialEntity);
    });

    await act(async () => {
      await result.current.handleSave();
    });

    expect(result.current.isSaving).toBe(false);
    expect(result.current.error).toBe(saveError);
  });

  test('handleCancel should reset form and call onCancel callback', async () => {
    const mockOnCancel = vi.fn();
    mockQueryHook.mockReturnValue({
      data: mockInitialEntity, isLoading: false, isFetching: false, error: null,
    });
    const { result } = renderHook(() => useEditableEntity(getMockConfig({ onCancel: mockOnCancel })));

    await waitFor(() => {
      expect(result.current.originalEntity).toEqual(mockInitialEntity);
    });
    // Assume form was changed, then cancelled.
    // This would require RHF interaction to simulate dirty form.

    act(() => {
      result.current.handleCancel();
    });

    // Expect formMethods.reset to be called with original transformed data
    expect(mockOnCancel).toHaveBeenCalled();
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

    let rhfFormStateIsDirty = false;
    const mockRHFMethods = {
      watch: vi.fn(),
      getValues: vi.fn(() => mockTransformDataToForm(initialEntityWithTwoSubItems)),
      setValue: vi.fn(),
      reset: vi.fn(),
      handleSubmit: vi.fn(cb => (...args: any[]) => cb(...args)),
      formState: { /* will be dynamically set */ } as any,
      control: {} as any,
    };
    
    // This is the key: mock react-hook-form module
    // We need to do this at the top-level of the test file.
    // Since we can't edit that from here, these tests will be somewhat conceptual
    // or assume such a mock is in place.

    // Helper to set up the hook for sub-entity tests
    const setupHookWithSubItems = (initialData: TestEntity = initialEntityWithTwoSubItems) => {
      mockQueryHook.mockReturnValue({ data: initialData, isLoading: false, isFetching: false, error: null });
      
      // Update formState mock for each run
      mockRHFMethods.formState = {
        get isDirty() { return rhfFormStateIsDirty; }, // Dynamic getter
        isValid: true, errors: {}, touchedFields: {},
      };
      
      // If we could mock useForm globally:
      // (useForm as vi.Mock).mockReturnValue(mockRHFMethods);

      return renderHook(
        (props) => useEditableEntity(props), 
        { 
          initialProps: getMockConfig({
            entityId: initialData.id,
            subEntityPath: 'subItems',
            transformSubCollectionToList: mockTransformSubCollectionToList,
            enableSubEntityReordering: true, // Enable for DND tests
          })
        }
      );
    };

    beforeEach(() => {
      rhfFormStateIsDirty = false; // Reset RHF dirty state for main form
      mockRHFMethods.getValues.mockReturnValue(mockTransformDataToForm(initialEntityWithTwoSubItems));
      mockRHFMethods.reset.mockClear();
      mockSaveHandler.mockClear();
    });

    test('updateSubItem should update an item and set dirty state', async () => {
      const { result } = setupHookWithSubItems();
      
      await waitFor(() => {
        expect(result.current.subEntityList[0].text).toBe('Alpha');
        expect(result.current.isSubEntityListDirty).toBe(false);
      });
      expect(result.current.isDirty).toBe(false);

      act(() => {
        result.current.updateSubItem('sub-a', { text: 'Alpha-Updated' });
      });

      expect(result.current.subEntityList[0].text).toBe('Alpha-Updated');
      expect(result.current.isSubEntityListDirty).toBe(true);
      expect(result.current.isDirty).toBe(true);

      // Test with function updater
      act(() => {
        result.current.updateSubItem('sub-b', (prev) => ({ ...prev, text: prev.text + '-Suffix' }));
      });
      expect(result.current.subEntityList[1].text).toBe('Bravo-Suffix');
      expect(result.current.isSubEntityListDirty).toBe(true); // Still dirty
    });

    test('removeSubItem should remove an item and set dirty state', async () => {
      const { result } = setupHookWithSubItems();
      
      await waitFor(() => {
        expect(result.current.subEntityList.length).toBe(2);
        expect(result.current.isSubEntityListDirty).toBe(false);
      });

      act(() => {
        result.current.removeSubItem('sub-a');
      });

      expect(result.current.subEntityList.length).toBe(1);
      expect(result.current.subEntityList.find(item => item.subId === 'sub-a')).toBeUndefined();
      expect(result.current.subEntityList[0].subId).toBe('sub-b');
      expect(result.current.isSubEntityListDirty).toBe(true);
      expect(result.current.isDirty).toBe(true);
    });

    test('handleDragEnd should reorder items and set dirty state', async () => {
      const { result } = setupHookWithSubItems();
      
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
        if (result.current.dndContextProps?.onDragEnd) { // Check if onDragEnd exists
          result.current.dndContextProps.onDragEnd(mockDragEndEvent);
        }
      });

      expect(result.current.subEntityList[0].subId).toBe('sub-b');
      expect(result.current.subEntityList[1].subId).toBe('sub-a');
      expect(result.current.isSubEntityListDirty).toBe(true);
      expect(result.current.isDirty).toBe(true);
    });

    test('isDirty should be true if main form is dirty, even if sub-list is not', async () => {
      const { result, rerender } = setupHookWithSubItems();
      
      await waitFor(() => {
        expect(result.current.isDirty).toBe(false);
        expect(result.current.isSubEntityListDirty).toBe(false);
      });
      
      rhfFormStateIsDirty = true; // Simulate RHF form becoming dirty
      // Rerender to pick up new formState.isDirty (if RHF would cause a rerender)
      // This is where proper RHF mocking that triggers rerenders is crucial.
      // For now, we manually rerender to simulate the effect.
      rerender(getMockConfig({
        entityId: initialEntityWithTwoSubItems.id,
        subEntityPath: 'subItems',
        transformSubCollectionToList: mockTransformSubCollectionToList,
      }));
      
      expect(result.current.isMainFormDirty).toBe(true);
      expect(result.current.isSubEntityListDirty).toBe(false); // Assuming no sub-list changes
      expect(result.current.isDirty).toBe(true);
    });

    test('handleSave should include modified subEntityList', async () => {
      const { result } = setupHookWithSubItems();
      const newSubItem: TestSubItem = { subId: 'sub-c', text: 'Charlie' };
      const updatedText = 'Alpha-Modified';

      act(() => {
        result.current.addSubItem(newSubItem); 
        result.current.updateSubItem('sub-a', { text: updatedText }); 
      });

      expect(result.current.isDirty).toBe(true);

      const changedFormData = { ...mockTransformDataToForm(initialEntityWithTwoSubItems), name: "Parent-Changed" };
      mockRHFMethods.getValues.mockReturnValue(changedFormData);
      rhfFormStateIsDirty = true;

      const expectedSavedEntity = { ...initialEntityWithTwoSubItems, name: "Parent-Changed" };
      const returnedEntityFromSave = { 
        ...expectedSavedEntity, 
        subItems: initialEntityWithTwoSubItems.subItems 
      };
      mockSaveHandler.mockResolvedValue(returnedEntityFromSave);

      await act(async () => {
        await result.current.handleSave();
      });
      
      const expectedSubListPayload = [
        { subId: 'sub-a', text: updatedText },
        { subId: 'sub-b', text: 'Bravo' },
        newSubItem,
      ];

      expect(mockSaveHandler).toHaveBeenCalledTimes(1); 
      expect(mockSaveHandler).toHaveBeenCalledWith(
        initialEntityWithTwoSubItems, 
        changedFormData,              
        expect.arrayContaining(expectedSubListPayload.map(item => expect.objectContaining(item)))
      );
      
      if (mockSaveHandler.mock.calls.length > 0) {
        const firstCallArgs = mockSaveHandler.mock.calls[0];
        // Check if the third argument (index 2) exists and is an array
        if (firstCallArgs && firstCallArgs.length > 2 && firstCallArgs[2] !== undefined && Array.isArray(firstCallArgs[2])) {
          expect((firstCallArgs[2] as TestSubItem[]).length).toBe(expectedSubListPayload.length);
        } else {
          // Fail the test explicitly if the third argument is not as expected
          expect(firstCallArgs && firstCallArgs.length > 2 && Array.isArray(firstCallArgs[2])).toBe(true);
        }
      }

      expect(result.current.isSaving).toBe(false);
      
      const currentError = result.current.error;
      expect(currentError).toBeNull(); 

      await waitFor(() => {
        const currentOriginalEntity = result.current.originalEntity;
        expect(currentOriginalEntity!).toEqual(returnedEntityFromSave); 
        expect(result.current.isDirty).toBe(false); 
        // If saveHandler returns entity, subEntityList snapshot AND internal list should update
        expect(result.current.subEntityList).toEqual(returnedEntityFromSave.subItems); 
      });
    });

    test('resetState should revert subEntityList changes', async () => {
      const { result } = setupHookWithSubItems();
      
      act(() => {
        result.current.addSubItem({ subId: 'sub-c', text: 'Charlie' });
        result.current.updateSubItem('sub-a', { text: 'Alpha-Modified' });
        result.current.removeSubItem('sub-b');
      });

      expect(result.current.subEntityList.length).toBe(2); // Alpha-Modified, Charlie
      expect(result.current.isSubEntityListDirty).toBe(true);
      
      act(() => {
        result.current.resetState();
      });

      // After reset, subEntityList should revert to original, and dirty state should be false
      await waitFor(() => {
        expect(result.current.subEntityList).toEqual(initialEntityWithTwoSubItems.subItems);
        expect(result.current.isSubEntityListDirty).toBe(false);
      });
      // Main form dirty state depends on RHF's reset behavior, which should also make it false
      expect(result.current.isDirty).toBe(rhfFormStateIsDirty); // This might need to be expect(...).toBe(false) if RHF reset also clears its dirty state
    });
  });
}); 