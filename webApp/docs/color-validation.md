# Color Validation System

This document explains how to use the color validation system to ensure consistent theming across the application.

## Overview

The color validation system enforces the use of semantic color tokens and prevents hardcoded colors that don't respond to theme changes. It includes:

1. **ESLint rules** - Catch forbidden colors during development
2. **Stylelint rules** - Validate CSS files for hardcoded colors  
3. **Build-time validation** - Fail builds with color violations
4. **Test utilities** - Verify components are theme-responsive

## Approved Color Usage

### ✅ Semantic Tailwind Tokens (Preferred)
```tsx
// React components should use semantic tokens
<div className="bg-ui-element-bg text-text-primary border-ui-border">
  <button className="bg-brand-primary text-brand-primary-text">
    Save Changes
  </button>
</div>
```

### ✅ Raw Radix Variables (CSS files only)
```css
/* Standalone CSS files can use Radix variables directly */
.my-component {
  background-color: var(--gray-3);
  color: var(--gray-12);
  border: 1px solid var(--accent-9);
}
```

## Forbidden Color Usage

### ❌ Hardcoded Tailwind Colors
```tsx
// These will trigger ESLint errors
<div className="bg-blue-500 text-gray-900 border-red-400">
```

### ❌ Hardcoded Color Values
```tsx
// These will trigger stylelint errors
<div style={{ backgroundColor: '#3b82f6', color: 'rgb(255, 255, 255)' }}>
```

## Available Semantic Tokens

### Brand & Accent Colors
- `brand-primary` - Primary brand color (var(--accent-9))
- `brand-primary-hover` - Hover state (var(--accent-10))
- `brand-primary-text` - Text on brand backgrounds (var(--accent-contrast))
- `accent-subtle` - Subtle accent backgrounds (var(--accent-3))
- `accent-surface` - Accent surface backgrounds
- `text-accent-strong` - Strong accent text (var(--accent-11))

### UI Element Colors
- `ui-bg` - Page background (var(--color-background))
- `ui-element-bg` - Cards, panels, modals (var(--color-panel-solid))
- `ui-interactive-bg` - Interactive element backgrounds (var(--gray-3))
- `ui-border` - Standard borders (var(--gray-6))
- `ui-border-focus` - Focus ring borders (var(--accent-9))

### Text Colors
- `text-primary` - Primary text (var(--gray-12))
- `text-secondary` - Secondary text (var(--gray-11))
- `text-muted` - Muted text (var(--gray-9))
- `text-accent` - Accent text (var(--accent-11))

### Status Colors
- `text-destructive` - Error text (var(--red-11))
- `success-indicator` - Success borders (var(--green-7))
- `warning-strong` - Warning text (var(--amber-11))

## Validation Commands

### Run All Validations
```bash
npm run validate:all
```

### Individual Validations
```bash
npm run lint              # ESLint (includes color rules)
npm run lint:css          # Stylelint for CSS files
npm run validate:colors   # Build script validation
```

### Build Integration
Color validation runs automatically during build:
```bash
npm run build  # Includes color validation
```

## Development Workflow

### 1. IDE Integration
Configure your IDE to show ESLint errors in real-time:
- VS Code: Install ESLint extension
- WebStorm: Enable ESLint in settings

### 2. Pre-commit Hooks
The validation runs automatically before commits via husky hooks.

### 3. CI/CD Integration
Builds will fail if color violations are detected, preventing deployment of non-compliant code.

## Testing Theme Responsiveness

### Unit Tests
```tsx
import { validateSemanticColors } from '../utils/color-validation';

test('component uses semantic colors', () => {
  const { container } = render(<MyComponent />);
  const element = container.firstChild as HTMLElement;
  
  const validation = validateSemanticColors(element);
  expect(validation.valid).toBe(true);
});
```

### Manual Testing
1. Change accent color in `main.tsx`
2. Verify components update colors accordingly
3. Test both light and dark modes

## Common Violations & Fixes

### Violation: Hardcoded Tailwind Colors
```tsx
// ❌ Before
<div className="bg-blue-500 text-white">

// ✅ After  
<div className="bg-brand-primary text-brand-primary-text">
```

### Violation: Hardcoded CSS Colors
```css
/* ❌ Before */
.button {
  background-color: #3b82f6;
  color: #ffffff;
}

/* ✅ After */
.button {
  background-color: var(--accent-9);
  color: var(--accent-contrast);
}
```

### Violation: Non-semantic Grays
```tsx
// ❌ Before
<div className="bg-gray-100 text-gray-900 border-gray-300">

// ✅ After
<div className="bg-ui-element-bg text-text-primary border-ui-border">
```

## Troubleshooting

### ESLint Not Catching Violations
1. Check `.eslintrc.cjs` includes the color rules
2. Restart your IDE/language server
3. Verify file is included in ESLint scope

### Stylelint Not Working
1. Install stylelint extension for your IDE
2. Check `.stylelintrc.json` configuration
3. Verify CSS files are being processed

### Build Validation Failing
1. Run `npm run validate:colors` locally
2. Check the detailed violation report
3. Fix violations before pushing

## Adding New Semantic Tokens

1. Add to `tailwind.config.js` colors section
2. Update `APPROVED_COLOR_TOKENS` in `color-validation.ts`
3. Update this documentation
4. Add tests for the new token

## Resources

- [Radix UI Themes Documentation](https://www.radix-ui.com/themes/docs)
- [Tailwind CSS Customization](https://tailwindcss.com/docs/customizing-colors)
- [Style Guide](../memory-bank/style-guide.md) 