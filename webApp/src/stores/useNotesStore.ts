import React from 'react';
import { create } from 'zustand';
import { supabase } from '@/lib/supabaseClient';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { Note, NewNoteData, UpdateNoteData } from '@/api/types';
import { toast } from '@/components/ui/toast';

interface NotesStore {
  notes: Note[];
  currentNoteId: string | null;
  isLoading: boolean;
  isSaving: boolean;
  lastSyncedAt: Date | null;

  // Actions
  setCurrentNote: (noteId: string | null) => void;
  createNote: (noteData: Omit<NewNoteData, 'user_id'>) => Promise<Note | null>;
  updateNote: (noteId: string, updates: UpdateNoteData) => Promise<void>;
  deleteNote: (noteId: string) => Promise<void>;
  loadNotes: () => Promise<void>;
  syncNotes: () => Promise<void>;

  // Internal state management
  setNotes: (notes: Note[]) => void;
  setLoading: (loading: boolean) => void;
  setSaving: (saving: boolean) => void;
}

export const useNotesStore = create<NotesStore>((set, get) => ({
  notes: [],
  currentNoteId: null,
  isLoading: false,
  isSaving: false,
  lastSyncedAt: null,

  setCurrentNote: (noteId) => set({ currentNoteId: noteId }),

  setNotes: (notes) => set({ notes }),
  setLoading: (loading) => set({ isLoading: loading }),
  setSaving: (saving) => set({ isSaving: saving }),

  createNote: async (noteData) => {
    const user = useAuthStore.getState().user;
    if (!user) {
      console.error('User not authenticated');
      toast.error('Please log in to create notes');
      return null;
    }

    set({ isSaving: true });

    try {
      const newNote: NewNoteData = {
        ...noteData,
        user_id: user.id,
      };

      const { data, error } = await supabase.from('notes').insert(newNote).select().single();

      if (error) throw error;

      // Update local state
      const currentNotes = get().notes;
      const updatedNotes = [data, ...currentNotes];
      set({
        notes: updatedNotes,
        currentNoteId: data.id,
        lastSyncedAt: new Date(),
      });

      toast.success('Note created');
      return data;
    } catch (error) {
      console.error('Error creating note:', error);
      toast.error('Failed to create note');
      return null;
    } finally {
      set({ isSaving: false });
    }
  },

  updateNote: async (noteId, updates) => {
    const user = useAuthStore.getState().user;
    if (!user) {
      console.error('User not authenticated');
      return;
    }

    set({ isSaving: true });

    try {
      // Optimistic update
      const currentNotes = get().notes;
      const optimisticNotes = currentNotes.map((note) =>
        note.id === noteId ? { ...note, ...updates, updated_at: new Date().toISOString() } : note,
      );
      set({ notes: optimisticNotes });

      const { data, error } = await supabase
        .from('notes')
        .update(updates)
        .eq('id', noteId)
        .eq('user_id', user.id)
        .select()
        .single();

      if (error) throw error;

      // Update with server response
      const serverNotes = currentNotes.map((note) => (note.id === noteId ? data : note));
      set({
        notes: serverNotes,
        lastSyncedAt: new Date(),
      });
    } catch (error) {
      console.error('Error updating note:', error);
      toast.error('Failed to save note');

      // Revert optimistic update
      await get().loadNotes();
    } finally {
      set({ isSaving: false });
    }
  },

  deleteNote: async (noteId) => {
    const user = useAuthStore.getState().user;
    if (!user) {
      console.error('User not authenticated');
      return;
    }

    set({ isSaving: true });

    try {
      // Soft delete
      const { error } = await supabase.from('notes').update({ deleted: true }).eq('id', noteId).eq('user_id', user.id);

      if (error) throw error;

      // Remove from local state
      const currentNotes = get().notes;
      const updatedNotes = currentNotes.filter((note) => note.id !== noteId);
      set({
        notes: updatedNotes,
        currentNoteId: get().currentNoteId === noteId ? null : get().currentNoteId,
        lastSyncedAt: new Date(),
      });

      toast.success('Note deleted');
    } catch (error) {
      console.error('Error deleting note:', error);
      toast.error('Failed to delete note');
    } finally {
      set({ isSaving: false });
    }
  },

  loadNotes: async () => {
    const user = useAuthStore.getState().user;
    if (!user) {
      console.error('User not authenticated');
      return;
    }

    set({ isLoading: true });

    try {
      const { data, error } = await supabase
        .from('notes')
        .select('*')
        .eq('user_id', user.id)
        .eq('deleted', false)
        .order('updated_at', { ascending: false });

      if (error) throw error;

      set({
        notes: data || [],
        lastSyncedAt: new Date(),
      });
    } catch (error) {
      console.error('Error loading notes:', error);
      toast.error('Failed to load notes');
    } finally {
      set({ isLoading: false });
    }
  },

  syncNotes: async () => {
    // For now, just reload notes
    // In the future, this could implement more sophisticated sync logic
    await get().loadNotes();
  },
}));

// Hook to initialize notes store
export const useInitializeNotesStore = () => {
  const user = useAuthStore.getState().user;
  const loadNotes = useNotesStore.getState().loadNotes;
  const notes = useNotesStore((state) => state.notes);

  React.useEffect(() => {
    if (user?.id && notes.length === 0) {
      loadNotes();
    }
  }, [user?.id, loadNotes, notes.length]);
};
