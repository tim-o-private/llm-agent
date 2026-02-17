import { render, screen } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { NotesPane } from '../NotesPane';

// Mock the stores and dependencies
vi.mock('@/stores/useNotesStore', () => ({
  useNotesStore: vi.fn(),
  useInitializeNotesStore: vi.fn(),
}));

vi.mock('@/features/auth/useAuthStore', () => ({
  useAuthStore: vi.fn(),
}));

vi.mock('@/components/ui/toast', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { useNotesStore } from '@/stores/useNotesStore';
import { useAuthStore } from '@/features/auth/useAuthStore';

// Properly type the mocked functions
const mockUseNotesStore = vi.mocked(useNotesStore);
const mockUseAuthStore = vi.mocked(useAuthStore);

describe('NotesPane', () => {
  const mockUser = {
    id: 'user-123',
    email: 'test@example.com',
  };

  const mockNote = {
    id: 'note-1',
    user_id: 'user-123',
    title: 'Test Note',
    content: 'Test content',
    created_at: '2025-01-27T10:00:00Z',
    updated_at: '2025-01-27T10:00:00Z',
    deleted: false,
  };

  const defaultStoreState = {
    notes: [],
    currentNoteId: null,
    isLoading: false,
    isSaving: false,
    setCurrentNote: vi.fn(),
    createNote: vi.fn(),
    updateNote: vi.fn(),
    deleteNote: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock auth store with authenticated user (component assumes authentication)
    mockUseAuthStore.mockReturnValue({ user: mockUser });

    // Mock notes store
    mockUseNotesStore.mockReturnValue(defaultStoreState);
  });

  describe('Loading state', () => {
    it('should show loading state', () => {
      mockUseNotesStore.mockReturnValue({
        ...defaultStoreState,
        isLoading: true,
      });

      render(<NotesPane />);

      expect(screen.getByText('Loading notes...')).toBeInTheDocument();
    });
  });

  describe('Empty state', () => {
    it('should show empty state when no notes exist', () => {
      render(<NotesPane />);

      expect(screen.getByText('Start taking notes')).toBeInTheDocument();
      expect(screen.getByText('Click "New" to create your first note')).toBeInTheDocument();
    });

    it('should show select note message when notes exist but none selected', () => {
      mockUseNotesStore.mockReturnValue({
        ...defaultStoreState,
        notes: [mockNote],
        currentNoteId: null,
      });

      render(<NotesPane />);

      expect(screen.getByText('Select a note to edit')).toBeInTheDocument();
      expect(screen.getByText('Choose from the list on the left')).toBeInTheDocument();
    });
  });

  describe('Notes list', () => {
    it('should display notes list when notes exist', () => {
      mockUseNotesStore.mockReturnValue({
        ...defaultStoreState,
        notes: [mockNote],
        currentNoteId: null,
      });

      render(<NotesPane />);

      expect(screen.getByText('Test Note')).toBeInTheDocument();
      expect(screen.getByText('Test content')).toBeInTheDocument();
    });

    it('should highlight selected note', () => {
      mockUseNotesStore.mockReturnValue({
        ...defaultStoreState,
        notes: [mockNote],
        currentNoteId: 'note-1',
      });

      render(<NotesPane />);

      // Find the note container div that has the highlighting classes
      const noteContainer = screen.getByText('Test Note').closest('.p-3');
      expect(noteContainer).toHaveClass('bg-brand-primary/10');
    });

    it('should show "Untitled" for notes without title', () => {
      const noteWithoutTitle = { ...mockNote, title: null };
      mockUseNotesStore.mockReturnValue({
        ...defaultStoreState,
        notes: [noteWithoutTitle],
        currentNoteId: null,
      });

      render(<NotesPane />);

      expect(screen.getByText('Untitled')).toBeInTheDocument();
    });

    it('should show "Empty note" for notes without content', () => {
      const noteWithoutContent = { ...mockNote, content: '' };
      mockUseNotesStore.mockReturnValue({
        ...defaultStoreState,
        notes: [noteWithoutContent],
        currentNoteId: null,
      });

      render(<NotesPane />);

      expect(screen.getByText('Empty note')).toBeInTheDocument();
    });
  });

  describe('Note editing', () => {
    it('should display note content when note is selected', () => {
      mockUseNotesStore.mockReturnValue({
        ...defaultStoreState,
        notes: [mockNote],
        currentNoteId: 'note-1',
      });

      render(<NotesPane />);

      expect(screen.getByDisplayValue('Test Note')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Test content')).toBeInTheDocument();
    });
  });

  describe('Loading and saving states', () => {
    it('should show saving indicator when saving', () => {
      mockUseNotesStore.mockReturnValue({
        ...defaultStoreState,
        notes: [mockNote],
        currentNoteId: 'note-1',
        isSaving: true,
      });

      render(<NotesPane />);

      expect(screen.getByText('Saving...')).toBeInTheDocument();
    });

    it('should disable buttons when saving', () => {
      mockUseNotesStore.mockReturnValue({
        ...defaultStoreState,
        notes: [mockNote],
        currentNoteId: 'note-1',
        isSaving: true,
      });

      render(<NotesPane />);

      // Find buttons by their role and check disabled state
      const newButton = screen.getByRole('button', { name: /new/i });
      const saveButton = screen.getByRole('button', { name: /save/i });
      // Delete button has no accessible name, so find it by its position
      const buttons = screen.getAllByRole('button');
      const deleteButton = buttons[2]; // Third button is delete

      expect(newButton).toBeDisabled();
      expect(saveButton).toBeDisabled();
      expect(deleteButton).toBeDisabled();
    });
  });

  describe('Custom className', () => {
    it('should apply custom className', () => {
      const { container } = render(<NotesPane className="custom-class" />);

      expect(container.firstChild).toHaveClass('custom-class');
    });
  });
});
