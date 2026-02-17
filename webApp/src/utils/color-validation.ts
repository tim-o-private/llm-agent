// Utility to validate semantic color usage in components
export const validateSemanticColors = (
  element: HTMLElement,
): {
  valid: boolean;
  violations: string[];
} => {
  const violations: string[] = [];

  // Check for forbidden Tailwind color classes
  const forbiddenPatterns = [
    { pattern: /bg-(blue|red|green|yellow|purple|pink|indigo|gray)-\d+/, type: 'background' },
    { pattern: /text-(blue|red|green|yellow|purple|pink|indigo|gray)-\d+/, type: 'text' },
    { pattern: /border-(blue|red|green|yellow|purple|pink|indigo|gray)-\d+/, type: 'border' },
  ];

  const className = element.className;

  forbiddenPatterns.forEach(({ pattern, type }) => {
    if (pattern.test(className)) {
      violations.push(`Found forbidden ${type} color class in: ${className}`);
    }
  });

  // Check for inline styles with hardcoded colors
  const style = element.getAttribute('style');
  if (style) {
    const colorPatterns = [
      { pattern: /#[0-9a-fA-F]{3,6}/, type: 'hex' },
      { pattern: /rgb\(/, type: 'rgb' },
      { pattern: /hsl\(/, type: 'hsl' },
    ];

    colorPatterns.forEach(({ pattern, type }) => {
      if (pattern.test(style)) {
        violations.push(`Found hardcoded ${type} color in inline style: ${style}`);
      }
    });
  }

  return {
    valid: violations.length === 0,
    violations,
  };
};

// Utility to scan entire DOM for color violations
export const scanForColorViolations = (
  container: HTMLElement = document.body,
): {
  totalElements: number;
  violatingElements: number;
  violations: Array<{
    element: string;
    violations: string[];
  }>;
} => {
  const allElements = container.querySelectorAll('*');
  const results = {
    totalElements: allElements.length,
    violatingElements: 0,
    violations: [] as Array<{ element: string; violations: string[] }>,
  };

  allElements.forEach((element, index) => {
    const validation = validateSemanticColors(element as HTMLElement);
    if (!validation.valid) {
      results.violatingElements++;
      results.violations.push({
        element: `Element ${index}: ${element.tagName.toLowerCase()}${element.className ? '.' + element.className.split(' ').join('.') : ''}`,
        violations: validation.violations,
      });
    }
  });

  return results;
};

// Approved semantic color tokens
export const APPROVED_COLOR_TOKENS = {
  // Brand & Accent Colors
  brand: [
    'brand-primary',
    'brand-primary-hover',
    'brand-primary-text',
    'bg-accent-subtle',
    'accent-subtle',
    'text-accent-strong',
    'accent-surface',
    'accent-indicator',
    'accent-track',
    'accent-hover',
  ],

  // UI Element Colors
  ui: [
    'ui-bg',
    'ui-bg-alt',
    'ui-bg-hover',
    'ui-element-bg',
    'ui-element-bg-hover',
    'ui-modal-bg',
    'ui-interactive-bg',
    'ui-interactive-bg-hover',
    'ui-interactive-bg-active',
    'ui-surface',
    'ui-border',
    'ui-border-hover',
    'ui-border-focus',
  ],

  // Text Colors
  text: ['text-primary', 'text-secondary', 'text-muted', 'text-disabled', 'text-accent', 'text-accent-hover'],

  // Status Colors
  status: [
    'destructive',
    'success-indicator',
    'success-strong',
    'warning-strong',
    'text-destructive',
    'text-success-strong',
    'text-warning-strong',
  ],
};

// Get all approved color tokens as flat array
export const getAllApprovedTokens = (): string[] => {
  return Object.values(APPROVED_COLOR_TOKENS).flat();
};

// Check if a color token is approved
export const isApprovedColorToken = (token: string): boolean => {
  return getAllApprovedTokens().includes(token);
};

// Extract color classes from className string
export const extractColorClasses = (className: string): string[] => {
  const colorPrefixes = ['bg-', 'text-', 'border-', 'ring-'];
  const classes = className.split(' ');

  return classes.filter((cls) => colorPrefixes.some((prefix) => cls.startsWith(prefix)));
};

// Validate color classes in a className string
export const validateColorClasses = (
  className: string,
): {
  valid: boolean;
  approvedClasses: string[];
  forbiddenClasses: string[];
} => {
  const colorClasses = extractColorClasses(className);
  const approvedTokens = getAllApprovedTokens();

  const approvedClasses: string[] = [];
  const forbiddenClasses: string[] = [];

  colorClasses.forEach((cls) => {
    // Remove prefix to get token name
    const token = cls.replace(/^(bg-|text-|border-|ring-)/, '');

    if (approvedTokens.includes(token)) {
      approvedClasses.push(cls);
    } else {
      forbiddenClasses.push(cls);
    }
  });

  return {
    valid: forbiddenClasses.length === 0,
    approvedClasses,
    forbiddenClasses,
  };
};
