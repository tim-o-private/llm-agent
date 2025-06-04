import { useState, useCallback, useEffect } from 'react';
import { toast } from '@/components/ui/toast';

export interface DialogStateHook {
  // State
  isFormDirty: boolean;
  isSaving: boolean;
  
  // Combined dirty state (form + additional)
  isDirty: boolean;
  
  // Handlers
  setIsFormDirty: (dirty: boolean) => void;
  setIsSaving: (saving: boolean) => void;
  handleSave: (saveFunction: () => Promise<void>) => Promise<void>;
  handleCancel: () => void;
  handleSaveSuccess: () => void;
  wrappedOnOpenChange: (open: boolean) => void;
  
  // Modal state management
  registerModalState: (modalId: string, isOpen: boolean) => void;
}

export interface DialogStateOptions {
  onOpenChange: (open: boolean) => void;
  onTaskUpdated: () => void;
  setModalOpenState?: (modalId: string, isOpen: boolean) => void;
  additionalDirtyState?: boolean;
  onResetState?: () => void;
}

export function useDialogState({
  onOpenChange,
  onTaskUpdated,
  setModalOpenState,
  additionalDirtyState = false,
  onResetState,
}: DialogStateOptions): DialogStateHook {
  const [isFormDirty, setIsFormDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Combined dirty state
  const isDirty = isFormDirty || additionalDirtyState;

  // Handle dirty state confirmation
  const wrappedOnOpenChange = useCallback((open: boolean) => {
    if (!open && isDirty) {
      if (window.confirm("You have unsaved changes. Are you sure you want to discard them?")) {
        // Reset state when discarding
        onResetState?.();
        setIsFormDirty(false);
        onOpenChange(false);
      } else {
        return; // Prevent closing if user cancels discard
      }
    } else {
      onOpenChange(open);
    }
  }, [isDirty, onOpenChange, onResetState]);

  const handleSave = useCallback(async (saveFunction: () => Promise<void>) => {
    setIsSaving(true);
    try {
      await saveFunction();
      // Success handling will be done by handleSaveSuccess
    } catch (error) {
      console.error('Save failed', error);
      toast.error('Failed to save');
    } finally {
      setIsSaving(false);
    }
  }, []);

  const handleSaveSuccess = useCallback(() => {
    toast.success('Saved successfully!');
    onTaskUpdated();
    onOpenChange(false); // Direct close after successful save
  }, [onTaskUpdated, onOpenChange]);

  const handleCancel = useCallback(() => {
    wrappedOnOpenChange(false);
  }, [wrappedOnOpenChange]);

  const registerModalState = useCallback((modalId: string, isOpen: boolean) => {
    if (setModalOpenState) {
      setModalOpenState(modalId, isOpen);
      
      // Reset state when modal opens to ensure clean state
      if (isOpen) {
        onResetState?.();
        setIsFormDirty(false);
      }
    }
  }, [setModalOpenState, onResetState]);

  return {
    isFormDirty,
    isSaving,
    isDirty,
    setIsFormDirty,
    setIsSaving,
    handleSave,
    handleCancel,
    handleSaveSuccess,
    wrappedOnOpenChange,
    registerModalState,
  };
} 