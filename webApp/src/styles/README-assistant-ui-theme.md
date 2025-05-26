# Assistant-UI Theme Mapping Documentation

## Overview

The `assistant-ui-theme.css` file provides comprehensive theming for all assistant-ui components, mapping them to our existing Radix-based design system. This ensures visual consistency across the entire application.

## Architecture

### Design System Integration
- **Base**: Radix Theme CSS variables (`--gray-*`, `--accent-*`, `--color-panel-solid`, etc.)
- **Dynamic Theming**: Automatically responds to Radix Theme provider changes (accentColor, grayColor, appearance)
- **Typography**: System font stack with proper fallbacks
- **Spacing**: Consistent rem-based spacing scale
- **Borders**: Unified border radius and shadow system

### Component Coverage
The theme file covers all major assistant-ui components:

- **Thread Container**: Background, borders, spacing
- **Message Bubbles**: User/assistant styling, borders, shadows
- **Composer**: Input field, buttons, placeholder text
- **Action Bar**: Buttons, hover states, spacing
- **Branch Picker**: Navigation, indicators, transitions
- **Attachments**: File display, progress indicators
- **Tool UI**: Call displays, results formatting

### Responsive Design
- **Mobile**: Optimized spacing and typography for small screens
- **Tablet**: Balanced layout for medium screens  
- **Desktop**: Full feature set with optimal spacing

### Accessibility Features
- **High Contrast**: Enhanced contrast ratios for better readability
- **Reduced Motion**: Respects user motion preferences
- **Focus Management**: Clear focus indicators and keyboard navigation
- **Screen Reader**: Proper ARIA support and semantic markup

## Dynamic Theme Support

The theme automatically adapts to all Radix Theme configurations:
- **Dark/Light Mode**: Automatically handled by Radix Theme `appearance` prop
- **Accent Colors**: Dynamically changes based on Radix Theme `accentColor` prop (indigo, blue, green, etc.)
- **Gray Scales**: Adapts to Radix Theme `grayColor` prop (slate, mauve, sand, etc.)
- **Contrast**: All components maintain accessibility standards across all theme combinations

## Usage

The theme is automatically imported in `src/styles/index.css` and applies globally to all assistant-ui components. No additional configuration is needed.

### Customization

To customize specific components, override the CSS variables in your component styles:

```css
.my-custom-thread {
  --aui-thread-bg: var(--blue-2);
  --aui-message-user-bg: var(--blue-9);
}
```

## Maintenance

When updating the design system:
1. Update the corresponding CSS variables in `assistant-ui-theme.css`
2. Test in both light and dark modes
3. Verify accessibility compliance
4. Check responsive behavior across devices

## File Structure

```
webApp/src/styles/
├── index.css                 # Main CSS entry point
├── assistant-ui-theme.css    # Assistant-UI theme mapping
└── README-assistant-ui-theme.md # This documentation
``` 