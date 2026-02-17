import { clsx } from 'clsx';

export type FocusState = 'default' | 'focused' | 'selected' | 'disabled' | 'error';
export type InteractionState = 'default' | 'hover' | 'active' | 'disabled';

/**
 * Global focus ring system for consistent interactive states
 */
export const getFocusRing = (state: FocusState = 'default') => {
  const rings = {
    default: '', // No ring by default
    focused: 'ring-1 ring-ui-border-focus shadow-xl', // Keyboard focus - always blue
    selected: 'ring-2 ring-brand-primary/50', // Selection - brand color
    error: 'ring-2 ring-border-destructive/20', // Error state - red
    disabled: '', // No ring when disabled
  };

  return rings[state];
};

/**
 * Global border system for interactive states
 */
export const getInteractiveBorder = (state: InteractionState = 'default', hasError = false) => {
  if (hasError) {
    return 'border-border-destructive';
  }

  const borders = {
    default: 'border-ui-border',
    hover: 'border-ui-border-hover',
    active: 'border-ui-border-focus',
    disabled: 'border-ui-border',
  };

  return borders[state];
};

/**
 * Global background system for interactive elements
 */
export const getInteractiveBackground = (state: InteractionState = 'default') => {
  const backgrounds = {
    default: 'bg-ui-element-bg',
    hover: 'bg-ui-element-bg-hover',
    active: 'bg-ui-interactive-bg-active',
    disabled: 'bg-ui-element-bg/50',
  };

  return backgrounds[state];
};

/**
 * Global text color system for interactive states
 */
export const getInteractiveText = (state: InteractionState = 'default') => {
  const textColors = {
    default: 'text-text-primary',
    hover: 'text-text-primary',
    active: 'text-text-primary',
    disabled: 'text-text-disabled',
  };

  return textColors[state];
};

/**
 * Global transform system for focus states
 */
export const getFocusTransform = (state: FocusState = 'default') => {
  const transforms = {
    default: '',
    focused: '', // Removed transform - no lifting on focus
    selected: '',
    error: '',
    disabled: '',
  };

  return transforms[state];
};

/**
 * Complete interactive element styling
 */
export interface InteractiveElementProps {
  focusState?: FocusState;
  interactionState?: InteractionState;
  hasError?: boolean;
  variant?: 'card' | 'button' | 'input';
}

export const getInteractiveStyles = ({
  focusState = 'default',
  interactionState = 'default',
  hasError = false,
  variant = 'card',
}: InteractiveElementProps) => {
  const baseStyles = 'transition-all duration-200 outline-none focus:outline-none';

  const variantStyles = {
    card: 'rounded-xl border-2 cursor-pointer',
    button: 'rounded-lg border font-medium cursor-pointer',
    input: 'rounded-lg border',
  };

  return clsx(
    baseStyles,
    variantStyles[variant],
    getInteractiveBackground(interactionState),
    getInteractiveBorder(interactionState, hasError),
    getInteractiveText(interactionState),
    getFocusRing(focusState),
    getFocusTransform(focusState),
    // Disabled state overrides
    interactionState === 'disabled' && 'cursor-not-allowed opacity-50',
  );
};

/**
 * Hover state classes for CSS hover pseudo-class
 */
export const getHoverClasses = (variant: 'card' | 'button' | 'input' = 'card') => {
  const hoverClasses = {
    card: 'hover:bg-ui-element-bg-hover hover:border-ui-border-hover',
    button: 'hover:bg-ui-element-bg-hover hover:border-ui-border-hover hover:shadow-md',
    input: 'hover:border-ui-border-hover',
  };

  return hoverClasses[variant];
};

/**
 * Focus state classes for CSS focus pseudo-class
 */
export const getFocusClasses = () => {
  return 'focus:ring-1 focus:ring-ui-border-focus focus:shadow-xl'; // Removed transform classes
};

/**
 * Complete CSS classes for interactive elements (includes hover and focus pseudo-classes)
 */
export const getCompleteInteractiveClasses = ({
  focusState = 'default',
  interactionState = 'default',
  hasError = false,
  variant = 'card',
}: InteractiveElementProps) => {
  return clsx(
    getInteractiveStyles({ focusState, interactionState, hasError, variant }),
    // Add hover classes only if not disabled
    interactionState !== 'disabled' && getHoverClasses(variant),
    // Add focus classes only if not disabled
    interactionState !== 'disabled' && getFocusClasses(),
  );
};
