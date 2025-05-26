import { render, RenderOptions } from '@testing-library/react';
import { ReactElement, ReactNode } from 'react';
import { Theme } from '@radix-ui/themes';

// Test wrapper that provides theme context
interface ThemeWrapperProps {
  children: ReactNode;
  accentColor?: string;
  grayColor?: string;
  appearance?: 'light' | 'dark';
}

const ThemeWrapper = ({ 
  children, 
  accentColor = 'indigo', 
  grayColor = 'slate',
  appearance = 'light'
}: ThemeWrapperProps) => {
  return (
    <Theme accentColor={accentColor}; grayColor={grayColor} appearance={appearance} >
      {children}
    </Theme>
  );
};

// Custom render function with theme wrapper
export const renderWithTheme = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'> & {
    accentColor?: string;
    grayColor?: string;
    appearance?: 'light' | 'dark';
  }
) => {
  const { accentColor, grayColor, appearance, ...renderOptions } = options || {};
  
  return render(ui, {
    wrapper: ({ children }: { children: ReactNode }) => {
      return (
        <ThemeWrapper 
          accentColor={accentColor} 
          grayColor={grayColor} 
          appearance={appearance}
        >
          {children}
        </ThemeWrapper>
      );
    },
    ...renderOptions,
  });
};

// Utility to test theme responsiveness
export const testThemeResponsiveness = async (
  component: ReactElement,
  testCases: Array<{
    accentColor: string;
    expectedStyles: Record<string, string>;
    description: string;
  }>
) => {
  const results: Array<{ description: string; passed: boolean; error?: string }> = [];

  for (const testCase of testCases) {
    try {
      const { container } = renderWithTheme(component, {
        accentColor: testCase.accentColor,
      });

      // Check if expected styles are applied
      let passed = true;
      let error = '';

      for (const [selector, expectedValue] of Object.entries(testCase.expectedStyles)) {
        const element = container.querySelector(selector);
        if (!element) {
          passed = false;
          error = `Element with selector "${selector}" not found`;
          break;
        }

        const computedStyle = window.getComputedStyle(element);
        const actualValue = computedStyle.getPropertyValue(expectedValue);
        
        if (!actualValue) {
          passed = false;
          error = `CSS property "${expectedValue}" not found or empty on element "${selector}"`;
          break;
        }
      }

      results.push({
        description: testCase.description,
        passed,
        error,
      });
    } catch (err) {
      results.push({
        description: testCase.description,
        passed: false,
        error: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  }

  return results;
};

// Utility to validate semantic color usage
export const validateSemanticColors = (element: HTMLElement): {
  valid: boolean;
  violations: string[];
} => {
  const violations: string[] = [];
  
  // Check for forbidden Tailwind color classes
  const forbiddenPatterns = [
    /bg-(blue|red|green|yellow|purple|pink|indigo|gray)-\d+/,
    /text-(blue|red|green|yellow|purple|pink|indigo|gray)-\d+/,
    /border-(blue|red|green|yellow|purple|pink|indigo|gray)-\d+/,
  ];

  const className = element.className;
  
  forbiddenPatterns.forEach((pattern, index) => {
    if (pattern.test(className)) {
      const type = ['background', 'text', 'border'][index];
      violations.push(`Found forbidden ${type} color class in: ${className}`);
    }
  });

  // Check for inline styles with hardcoded colors
  const style = element.getAttribute('style');
  if (style) {
    const colorPatterns = [
      /#[0-9a-fA-F]{3,6}/,  // Hex colors
      /rgb\(/,               // RGB colors
      /hsl\(/,               // HSL colors
    ];

    colorPatterns.forEach(pattern => {
      if (pattern.test(style)) {
        violations.push(`Found hardcoded color in inline style: ${style}`);
      }
    });
  }

  return {
    valid: violations.length === 0,
    violations,
  };
};

// Jest matcher for theme responsiveness
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeThemeResponsive(): R;
      toUseSemanticColors(): R;
    }
  }
}

// Custom Jest matchers
export const themeMatchers = {
  toBeThemeResponsive(received: HTMLElement) {
    const validation = validateSemanticColors(received);
    
    return {
      message: () => 
        validation.valid 
          ? `Expected element to NOT be theme responsive`
          : `Expected element to be theme responsive but found violations:\n${validation.violations.join('\n')}`,
      pass: validation.valid,
    };
  },

  toUseSemanticColors(received: HTMLElement) {
    const validation = validateSemanticColors(received);
    
    return {
      message: () => 
        validation.valid 
          ? `Expected element to NOT use semantic colors`
          : `Expected element to use semantic colors but found violations:\n${validation.violations.join('\n')}`,
      pass: validation.valid,
    };
  },
}; 