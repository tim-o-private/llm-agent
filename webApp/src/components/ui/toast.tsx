'use client';

import * as React from 'react';
import * as ToastPrimitives from '@radix-ui/react-toast';
import { Cross2Icon } from '@radix-ui/react-icons';
import { cn } from '@/lib/utils';
import { getFocusClasses } from '@/utils/focusStates';

// --- Styled Radix Primitives ---

const StyledToastProvider = ToastPrimitives.Provider;

const StyledToastViewport = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Viewport>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Viewport>
>(({ className, ...props }, ref) => (
  <ToastPrimitives.Viewport
    ref={ref}
    className={cn(
      'fixed top-0 z-[99999] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]',
      className
    )}
    {...props}
  />
));
StyledToastViewport.displayName = ToastPrimitives.Viewport.displayName;

type ToastVariant = 'default' | 'destructive' | 'success';

const StyledToast = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Root>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Root> & { variant?: ToastVariant }
>(({ className, variant = 'default', ...props }, ref) => {
  return (
    <ToastPrimitives.Root
      ref={ref}
      className={cn(
        'group pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-6 pr-8 shadow-lg transition-all data-[swipe=cancel]:translate-x-0 data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)] data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[swipe=move]:transition-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[swipe=end]:animate-out data-[state=closed]:fade-out-80 data-[state=closed]:slide-out-to-right-full data-[state=open]:slide-in-from-top-full data-[state=open]:sm:slide-in-from-bottom-full',
        {
          'border-[var(--accent-7)] bg-[var(--accent-8)] text-foreground': variant === 'default',
          'destructive group border-destructive bg-destructive text-destructive-foreground': variant === 'destructive',
          'success group border-success-indicator bg-bg-success-subtle text-success-strong': variant === 'success',
        },
        className
      )}
      {...props}
    />
  );
});
StyledToast.displayName = ToastPrimitives.Root.displayName;

const StyledToastAction = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Action>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Action>
>(({ className, ...props }, ref) => (
  <ToastPrimitives.Action
    ref={ref}
    className={cn(
      'inline-flex h-8 shrink-0 items-center justify-center rounded-md border px-3 text-sm font-medium ring-offset-background transition-colors hover:bg-secondary disabled:pointer-events-none disabled:opacity-50',
      getFocusClasses(),
      'group-[.destructive]:border-muted/40 group-[.destructive]:hover:border-destructive/30 group-[.destructive]:hover:bg-destructive group-[.destructive]:hover:text-destructive-foreground group-[.destructive]:focus:ring-destructive',
      'group-[.success]:border-success-indicator group-[.success]:hover:border-success-indicator group-[.success]:hover:bg-bg-success-subtle group-[.success]:hover:text-success-strong group-[.success]:focus:ring-success-indicator',
      className
    )}
    {...props}
  />
));
StyledToastAction.displayName = ToastPrimitives.Action.displayName;

const StyledToastClose = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Close>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Close>
>(({ className, ...props }, ref) => (
  <ToastPrimitives.Close
    ref={ref}
    className={cn(
      'absolute right-2 top-2 rounded-md p-1 text-foreground/50 opacity-0 transition-opacity hover:text-foreground focus:opacity-100 group-hover:opacity-100',
      getFocusClasses(),
      'group-[.destructive]:text-text-destructive group-[.destructive]:hover:text-text-destructive group-[.destructive]:focus:ring-destructive group-[.destructive]:focus:ring-offset-destructive',
      'group-[.success]:text-success-strong group-[.success]:hover:text-success-strong',
      className
    )}
    toast-close=""
    {...props}
  >
    <Cross2Icon className="h-4 w-4 color-[var(--gray-5)]" />
  </ToastPrimitives.Close>
));
StyledToastClose.displayName = ToastPrimitives.Close.displayName;

const StyledToastTitle = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Title>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Title>
>(({ className, ...props }, ref) => (
  <ToastPrimitives.Title
    ref={ref}
    className={cn('text-sm font-semibold', className)}
    {...props}
  />
));
StyledToastTitle.displayName = ToastPrimitives.Title.displayName;

const StyledToastDescription = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Description>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Description>
>(({ className, ...props }, ref) => (
  <ToastPrimitives.Description
    ref={ref}
    className={cn('text-sm opacity-90', className)}
    {...props}
  />
));
StyledToastDescription.displayName = ToastPrimitives.Description.displayName;

// --- Global Toast State & Imperative API ---

interface ToastProps {
  id: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactElement<typeof StyledToastAction>;
  variant?: ToastVariant;
  duration?: number;
}

type InternalToast = ToastProps & { open: boolean };

let toastsStore: InternalToast[] = [];
const toastListeners: Array<(toasts: InternalToast[]) => void> = [];
let toastIdCounter = 0;

const TOAST_LIMIT = 5;
const DEFAULT_TOAST_DURATION = 2000;
const ANIMATION_DURATION = 1000; // Estimated time for Radix close animation

function generateId(): string {
  toastIdCounter = (toastIdCounter + 1) % Number.MAX_SAFE_INTEGER;
  return toastIdCounter.toString();
}

function notifyListeners(): void {
  for (const listener of toastListeners) {
    listener([...toastsStore]);
  }
}

// The imperative function to show a toast
function showToast(props: Omit<ToastProps, 'id'>): { id: string } {
  const id = generateId();
  const newToast: InternalToast = {
    ...props,
    id,
    open: true,
    duration: props.duration ?? DEFAULT_TOAST_DURATION,
  };

  toastsStore = [newToast, ...toastsStore].slice(0, TOAST_LIMIT);
  notifyListeners();
  return { id };
}

// Called when Radix signals a toast should close (via onOpenChange)
function dismissToast(toastId: string): void {
  toastsStore = toastsStore.map(t => (t.id === toastId ? { ...t, open: false } : t));
  notifyListeners();

  setTimeout(() => {
    toastsStore = toastsStore.filter(t => t.id !== toastId);
    notifyListeners();
  }, ANIMATION_DURATION);
}

// --- Toaster Component (for App.tsx) ---

function ToasterContainer() {
  const [currentToasts, setCurrentToasts] = React.useState<InternalToast[]>(toastsStore);

  React.useEffect(() => {
    const listener = (updatedToasts: InternalToast[]) => {
      setCurrentToasts(updatedToasts);
    };
    toastListeners.push(listener);
    setCurrentToasts([...toastsStore]); // Initial sync

    return () => {
      toastListeners.splice(toastListeners.indexOf(listener), 1);
    };
  }, []);

  return (
    <StyledToastProvider swipeDirection="right" duration={DEFAULT_TOAST_DURATION}>
      {currentToasts.map(toastItem => {
        console.log(`Rendering toast: ${toastItem.id}, duration: ${toastItem.duration}, title: ${toastItem.title}`);
        return (
          <StyledToast
            key={toastItem.id}
            open={toastItem.open}
            onOpenChange={(isOpen: boolean) => {
              if (!isOpen) {
                dismissToast(toastItem.id);
              }
            }}
            duration={toastItem.duration}
            variant={toastItem.variant}
          >
            <div className="grid gap-1">
              {toastItem.title && <StyledToastTitle>{toastItem.title}</StyledToastTitle>}
              {toastItem.description && (
                <StyledToastDescription>{toastItem.description}</StyledToastDescription>
              )}
            </div>
            {toastItem.action}
            <StyledToastClose />
          </StyledToast>
        );
      })}
      <StyledToastViewport />
    </StyledToastProvider>
  );
}

// --- useToast Hook ---

function useToast() {
  return {
    toast: toast,
  };
}

// --- Exports ---

// Helper for the new toast object
const createToastWithOptions = (
    variant: ToastVariant,
    title: React.ReactNode,
    description?: React.ReactNode,
    options?: Omit<ToastProps, 'id' | 'title' | 'description' | 'variant'>
): { id: string } => {
    return showToast({
        title,
        description,
        variant,
        ...options,
    });
};

const toast = {
  show: showToast, // For direct object-based calls
  success: (
    title: React.ReactNode,
    description?: React.ReactNode,
    options?: Omit<ToastProps, 'id' | 'title' | 'description' | 'variant'>
  ) => createToastWithOptions('success', title, description, options),
  error: (
    title: React.ReactNode,
    description?: React.ReactNode,
    options?: Omit<ToastProps, 'id' | 'title' | 'description' | 'variant'>
  ) => createToastWithOptions('destructive', title, description, options),
  default: (
    title: React.ReactNode,
    description?: React.ReactNode,
    options?: Omit<ToastProps, 'id' | 'title' | 'description' | 'variant'>
  ) => createToastWithOptions('default', title, description, options),
};

export {
  type ToastProps as RadixToastProps, // Props for individual toast content
  StyledToastProvider as ToastProvider,
  StyledToastViewport as ToastViewport,
  StyledToast as ToastRoot, // Renamed to avoid conflict with hook/function
  StyledToastTitle as ToastTitle,
  StyledToastDescription as ToastDescription,
  StyledToastAction as ToastAction,
  StyledToastClose as ToastClose,
  useToast,
  ToasterContainer as Toaster, // The main Toaster component for App.tsx
  toast, // The new toast object
}; 