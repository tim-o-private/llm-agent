import { TaskStatus, TaskPriority } from '@/api/types';
import clsx from 'clsx';

export interface StatusStyleOptions {
  completed?: boolean;
  status?: TaskStatus;
  priority?: TaskPriority;
  variant?: 'card' | 'item' | 'compact';
  isHovered?: boolean;
  isFocused?: boolean;
  isSelected?: boolean;
  isDragging?: boolean;
}

/**
 * Get status-based styles for task containers (cards, items, etc.)
 */
export const getStatusContainerStyles = (options: StatusStyleOptions): string => {
  const { completed, status, priority, variant = 'card', isHovered, isFocused, isSelected, isDragging } = options;
  
  const baseStyles = [
    'transition-all duration-300 ease-out',
    'border-2',
    variant === 'card' && 'rounded-xl shadow-elevated backdrop-blur-sm',
    variant === 'item' && 'rounded-md shadow-sm',
    variant === 'compact' && 'rounded-md shadow-sm',
  ];

  // Status-based background and border styles
  const statusStyles = getStatusStyles(status, completed);
  
  // Priority-based glow effects
  const priorityGlow = getPriorityGlow(priority, completed);
  
  // Interactive states
  const interactiveStyles = [
    !completed && !isDragging && isHovered && 'hover:shadow-lg hover:scale-[1.02] hover:-translate-y-1',
    completed && !isDragging && isHovered && 'hover:shadow-md hover:scale-[1.01] hover:-translate-y-0.5',
    isFocused && 'ring-4 ring-blue-500/50 shadow-xl transform -translate-y-1 scale-[1.02]',
    isSelected && !completed && 'ring-2 ring-brand-primary/50',
    isSelected && completed && 'ring-2 ring-ui-border/50',
    status === 'in_progress' && isFocused && 'shadow-brand-primary/20 animate-pulse',
  ];

  return clsx(baseStyles, statusStyles, priorityGlow, interactiveStyles);
};

/**
 * Get status-based text styles
 */
export const getStatusTextStyles = (options: StatusStyleOptions): string => {
  const { completed, isHovered } = options;
  
  return clsx(
    'transition-all duration-200',
    !completed && !isHovered && 'text-text-primary',
    !completed && isHovered && 'text-brand-primary',
    completed && 'line-through text-text-muted'
  );
};

/**
 * Get status-based priority indicator styles
 */
export const getPriorityIndicatorStyles = (options: StatusStyleOptions): string => {
  const { completed, priority } = options;
  
  if (!priority) return 'hidden';
  
  return clsx(
    'absolute top-2 right-2 w-2 h-2 rounded-full z-10',
    !completed && priority === 3 && 'bg-red-500',
    !completed && priority === 2 && 'bg-amber-500',
    !completed && priority === 1 && 'bg-blue-500',
    completed && 'bg-gray-400 opacity-50'
  );
};

/**
 * Get status-based button styles for interactive elements
 */
export const getStatusButtonStyles = (options: StatusStyleOptions): string => {
  const { completed } = options;
  
  return clsx(
    'p-2 rounded-lg transition-all duration-200 relative z-10',
    !completed && 'hover:bg-ui-interactive-bg-hover backdrop-blur-sm hover:shadow-lg',
    completed && 'hover:bg-ui-interactive-bg-hover/60 backdrop-blur-sm',
    'active:scale-95'
  );
};

/**
 * Get status-based icon styles
 */
export const getStatusIconStyles = (options: StatusStyleOptions): string => {
  const { completed } = options;
  
  return clsx(
    'h-5 w-5 transition-colors duration-200',
    !completed && 'text-text-muted group-hover:text-text-secondary',
    completed && 'text-text-muted/60'
  );
};

/**
 * Get status-based background overlay styles for enhanced depth
 */
export const getStatusOverlayStyles = (options: StatusStyleOptions): string => {
  const { completed, status, isFocused } = options;
  
  return clsx(
    'absolute inset-0 rounded-xl pointer-events-none',
    // Glassy overlay for extra depth
    'bg-gradient-to-br from-ui-surface/10 to-transparent',
    // Animated background gradient for active states - only for non-completed
    (status === 'in_progress' || isFocused) && !completed && 
      'bg-gradient-to-r from-brand-primary/5 via-brand-secondary/5 to-brand-primary/5 animate-gradient-shift opacity-50'
  );
};

// Internal helper functions
const getStatusStyles = (status: TaskStatus | undefined, completed: boolean | undefined): string => {
  if (completed || status === 'completed') return 'opacity-70 border-ui-border bg-ui-element-bg/60';
  if (status === 'in_progress') return 'border-brand-primary bg-ui-element-bg/80';
  if (status === 'planning') return 'border-brand-primary bg-ui-element-bg/80';
  return 'border-ui-border bg-ui-element-bg/80 hover:border-ui-border-hover';
};

const getPriorityGlow = (priority: TaskPriority | undefined, completed: boolean | undefined): string => {
  if (completed || !priority) return '';
  
  switch (priority) {
    case 3: return 'shadow-lg shadow-danger/30';
    case 2: return 'shadow-md shadow-warning/20';
    case 1: return 'shadow-sm';
    default: return '';
  }
}; 