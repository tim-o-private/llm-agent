import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useNotesStore } from '../useNotesStore';

// Simple integration tests for the notes store
describe('useNotesStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useNotesStore.setState({
      notes: [],
      currentNoteId: null,
      isLoading: false,
      isSaving: false,
      lastSyncedAt: null,
    });
  });

  describe('Initial state', () => {
    it('should have correct initial state', () => {
      const state = useNotesStore.getState();

      expect(state.notes).toEqual([]);
      expect(state.currentNoteId).toBe(null);
      expect(state.isLoading).toBe(false);
      expect(state.isSaving).toBe(false);
      expect(state.lastSyncedAt).toBe(null);
    });
  });

  describe('setCurrentNote', () => {
    it('should set current note ID', () => {
      const { setCurrentNote } = useNotesStore.getState();

      setCurrentNote('note-1');

      expect(useNotesStore.getState().currentNoteId).toBe('note-1');
    });

    it('should clear current note ID when passed null', () => {
      const { setCurrentNote } = useNotesStore.getState();

      setCurrentNote('note-1');
      expect(useNotesStore.getState().currentNoteId).toBe('note-1');

      setCurrentNote(null);
      expect(useNotesStore.getState().currentNoteId).toBe(null);
    });
  });

  describe('setNotes', () => {
    it('should update notes array', () => {
      const mockNotes = [
        {
          id: 'note-1',
          user_id: 'user-123',
          title: 'Test Note',
          content: 'Test content',
          created_at: '2025-01-27T10:00:00Z',
          updated_at: '2025-01-27T10:00:00Z',
          deleted: false,
        },
      ];

      const { setNotes } = useNotesStore.getState();
      setNotes(mockNotes);

      expect(useNotesStore.getState().notes).toEqual(mockNotes);
    });
  });

  describe('setLoading', () => {
    it('should update loading state', () => {
      const { setLoading } = useNotesStore.getState();

      setLoading(true);
      expect(useNotesStore.getState().isLoading).toBe(true);

      setLoading(false);
      expect(useNotesStore.getState().isLoading).toBe(false);
    });
  });

  describe('setSaving', () => {
    it('should update saving state', () => {
      const { setSaving } = useNotesStore.getState();

      setSaving(true);
      expect(useNotesStore.getState().isSaving).toBe(true);

      setSaving(false);
      expect(useNotesStore.getState().isSaving).toBe(false);
    });
  });

  describe('Store state management', () => {
    it('should maintain state consistency across multiple operations', () => {
      const { setCurrentNote, setLoading, setSaving, setNotes } = useNotesStore.getState();

      const mockNotes = [
        {
          id: 'note-1',
          user_id: 'user-123',
          title: 'Test Note',
          content: 'Test content',
          created_at: '2025-01-27T10:00:00Z',
          updated_at: '2025-01-27T10:00:00Z',
          deleted: false,
        },
      ];

      // Perform multiple state updates
      setNotes(mockNotes);
      setCurrentNote('note-1');
      setLoading(true);
      setSaving(false);

      const state = useNotesStore.getState();
      expect(state.notes).toEqual(mockNotes);
      expect(state.currentNoteId).toBe('note-1');
      expect(state.isLoading).toBe(true);
      expect(state.isSaving).toBe(false);
    });
  });

  describe('Store subscription', () => {
    it('should notify subscribers when state changes', () => {
      const mockCallback = vi.fn();

      // Subscribe to store changes
      const unsubscribe = useNotesStore.subscribe(mockCallback);

      // Make a state change
      const { setCurrentNote } = useNotesStore.getState();
      setCurrentNote('note-1');

      // Verify callback was called
      expect(mockCallback).toHaveBeenCalled();

      // Cleanup
      unsubscribe();
    });
  });
});
