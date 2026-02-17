import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Pencil1Icon, CheckIcon, TrashIcon, PlusIcon } from '@radix-ui/react-icons';
import { Button } from '@/components/ui/Button';
import { toast } from '@/components/ui/toast';
import { useNotesStore, useInitializeNotesStore } from '@/stores/useNotesStore';
import { useAuthStore } from '@/features/auth/useAuthStore';
import clsx from 'clsx';

interface NotesPaneProps {
  className?: string;
}

export const NotesPane: React.FC<NotesPaneProps> = ({ className }) => {
  const user = useAuthStore((state) => state.user);
  const { notes, currentNoteId, isLoading, isSaving, setCurrentNote, createNote, updateNote, deleteNote } =
    useNotesStore();

  // Initialize notes store
  useInitializeNotesStore();

  // Local state for editing
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [editTitle, setEditTitle] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Get current note
  const currentNote = notes.find((note) => note.id === currentNoteId);

  // Auto-save functionality (debounced)
  useEffect(() => {
    if (!currentNote || !isEditing) return;
    if (editContent === currentNote.content && editTitle === (currentNote.title || '')) return;

    const timeoutId = setTimeout(async () => {
      if (currentNote) {
        await updateNote(currentNote.id, {
          content: editContent,
          title: editTitle || null,
        });
      }
    }, 2000); // Auto-save after 2 seconds of inactivity

    return () => clearTimeout(timeoutId);
  }, [editContent, editTitle, currentNote, updateNote, isEditing]);

  // Focus textarea when entering edit mode
  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isEditing]);

  // Set edit content when current note changes
  useEffect(() => {
    if (currentNote) {
      setEditContent(currentNote.content);
      setEditTitle(currentNote.title || '');
    }
  }, [currentNote]);

  const handleCreateNote = useCallback(async () => {
    if (!user) return;

    const newNote = await createNote({
      content: '',
      title: null,
    });

    if (newNote) {
      setIsEditing(true);
      setEditContent('');
      setEditTitle('');
    }
  }, [createNote, user]);

  const handleSave = useCallback(async () => {
    if (!currentNote) return;

    await updateNote(currentNote.id, {
      content: editContent,
      title: editTitle || null,
    });
    setIsEditing(false);
    toast.success('Note saved');
  }, [currentNote, updateNote, editContent, editTitle]);

  const handleDelete = useCallback(async () => {
    if (!currentNote) return;

    if (window.confirm('Are you sure you want to delete this note?')) {
      await deleteNote(currentNote.id);
    }
  }, [currentNote, deleteNote]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsEditing(false);
        // Revert to saved content
        if (currentNote) {
          setEditContent(currentNote.content);
          setEditTitle(currentNote.title || '');
        }
      } else if (e.key === 's' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        handleSave();
      }
    },
    [handleSave, currentNote],
  );

  const handleNoteSelect = useCallback(
    (noteId: string) => {
      setCurrentNote(noteId);
      setIsEditing(false);
    },
    [setCurrentNote],
  );

  if (!user) {
    return (
      <div className={`flex flex-col h-full ${className || ''}`}>
        <div className="flex-1 flex items-center justify-center text-text-muted">
          <div className="text-center">
            <Pencil1Icon className="h-16 w-16 mb-4 opacity-50 mx-auto" />
            <p className="text-lg">Please log in to access notes</p>
          </div>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={`flex flex-col h-full ${className || ''}`}>
        <div className="flex-1 flex items-center justify-center text-text-muted">
          <div className="text-center">
            <div className="animate-spin h-8 w-8 border-2 border-brand-primary border-t-transparent rounded-full mx-auto mb-4"></div>
            <p>Loading notes...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full ${className || ''}`}>
      {/* Header */}
      <div className="flex justify-between items-center mb-6 px-6 pt-6">
        <h2 className="text-2xl font-bold text-text-primary flex items-center">
          <Pencil1Icon className="mr-2 h-6 w-6" />
          Notes
        </h2>
        <div className="flex items-center space-x-2">
          {isSaving && <span className="text-xs text-text-muted">Saving...</span>}
          <Button variant="outline" size="1" onClick={handleCreateNote} disabled={isSaving}>
            <PlusIcon className="mr-1 h-4 w-4" />
            New
          </Button>
          {currentNote && (
            <>
              <Button variant="outline" size="1" onClick={handleSave} disabled={!isEditing || isSaving}>
                <CheckIcon className="mr-1 h-4 w-4" />
                Save
              </Button>
              <Button
                variant="outline"
                size="1"
                onClick={handleDelete}
                disabled={isSaving}
                className="text-destructive hover:text-destructive"
              >
                <TrashIcon className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden px-6 pb-6">
        {/* Notes List Sidebar */}
        {notes.length > 0 && (
          <div className="w-1/3 pr-4 border-r border-ui-border">
            <div className="space-y-2 overflow-y-auto h-full">
              {notes.map((note) => (
                <div
                  key={note.id}
                  onClick={() => handleNoteSelect(note.id)}
                  className={clsx(
                    'p-3 rounded-lg cursor-pointer transition-colors',
                    'hover:bg-ui-element-bg',
                    currentNoteId === note.id
                      ? 'bg-brand-primary/10 border border-brand-primary/30'
                      : 'bg-ui-surface border border-ui-border',
                  )}
                >
                  <div className="text-sm font-medium text-text-primary truncate">{note.title || 'Untitled'}</div>
                  <div className="text-xs text-text-muted mt-1 line-clamp-2">{note.content || 'Empty note'}</div>
                  <div className="text-xs text-text-muted mt-2">{new Date(note.updated_at).toLocaleDateString()}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Notes Content */}
        <div className={clsx('flex-1', notes.length > 0 ? 'pl-4' : '')}>
          {!currentNote ? (
            // Empty state
            <div className="h-full flex items-center justify-center text-text-muted">
              <div className="text-center">
                <Pencil1Icon className="h-16 w-16 mb-4 opacity-50 mx-auto" />
                <p className="text-lg">{notes.length === 0 ? 'Start taking notes' : 'Select a note to edit'}</p>
                <p className="text-sm">
                  {notes.length === 0 ? 'Click "New" to create your first note' : 'Choose from the list on the left'}
                </p>
              </div>
            </div>
          ) : (
            // Notes editor
            <div className="h-full flex flex-col">
              {/* Title input */}
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onFocus={() => setIsEditing(true)}
                placeholder="Note title (optional)"
                className="w-full p-2 mb-4 bg-ui-element-bg border border-ui-border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary text-text-primary placeholder-text-muted font-medium"
              />

              {/* Content textarea */}
              <textarea
                ref={textareaRef}
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                onFocus={() => setIsEditing(true)}
                onKeyDown={handleKeyDown}
                placeholder="Start typing your note here..."
                className="flex-1 w-full p-4 bg-ui-element-bg border border-ui-border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary text-text-primary placeholder-text-muted"
              />

              {isEditing && (
                <div className="mt-4 flex justify-between items-center text-xs text-text-muted">
                  <div className="space-x-4">
                    <span>⌘S to save</span>
                    <span>Esc to cancel</span>
                  </div>
                  <div>{editContent.length} characters</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
