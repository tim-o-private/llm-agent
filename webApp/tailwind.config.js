/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class', // Radix Themes often uses class-based dark mode detection with `html.dark`
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand & Accent Colors (using Radix generic CSS variables)
        'brand-primary': 'var(--accent-9)',
        'brand-primary-hover': 'var(--accent-10)',
        'brand-primary-text': 'var(--accent-contrast)', // For text on accent-9 backgrounds
        'bg-accent-subtle': 'var(--accent-3)',
        'text-accent-strong': 'var(--accent-11)', // Same as text-accent, maybe a bit darker like accent-12 if needed

        // Destructive Colors
        'danger-bg': 'var(--red-9)',
        'danger-bg-hover': 'var(--red-10)',
        'border-destructive': 'var(--red-7)',
        'text-destructive': 'var(--red-11)', // Already exists
        'bg-destructive-subtle': 'var(--red-3)',
        'text-destructive-strong': 'var(--red-11)', // For text on subtle destructive bg

        // Info Colors (Blue)
        'bg-info-subtle': 'var(--blue-3)',
        'text-info-strong': 'var(--blue-11)',
        'bg-info-indicator': 'var(--blue-9)',

        // Warning Colors (Amber/Yellow)
        'bg-warning-subtle': 'var(--amber-3)',
        'text-warning-strong': 'var(--amber-11)',
        'bg-warning-indicator': 'var(--amber-9)',

        // Success Colors (Green)
        'bg-success-subtle': 'var(--green-3)',
        'text-success-strong': 'var(--green-11)',
        'bg-success-indicator': 'var(--green-9)',

        // Neutral/Muted Colors (for Skipped badge etc.)
        'bg-neutral-subtle': 'var(--gray-3)', // Can reuse or be more specific like mauver-3 etc.
        'text-neutral-strong': 'var(--gray-11)',
        'bg-neutral-indicator': 'var(--gray-9)',

        // UI Element Backgrounds
        'ui-bg': 'var(--color-panel-solid)', // Or var(--gray-1) / var(--mauve-1) etc. for page background
        'ui-bg-alt': 'var(--gray-2)',       // Subtle background variation
        'ui-bg-hover': 'var(--gray-3)',    // Hover for non-interactive elements
        
        'ui-element-bg': 'var(--gray-3)',         // Default background for elements like cards, inputs (non-interactive state)
        'ui-element-bg-hover': 'var(--gray-4)',   // Hover state for non-interactive elements
        'ui-modal-bg': 'var(--gray-2)', // Dedicated background for modal content panels
        
        'ui-interactive-bg': 'var(--gray-3)',       // Base for interactive elements
        'ui-interactive-bg-hover': 'var(--gray-4)', // Hover for interactive elements
        'ui-interactive-bg-active': 'var(--gray-5)',// Active/pressed for interactive elements

        // Borders
        'ui-border': 'var(--gray-6)',
        'ui-border-hover': 'var(--gray-7)', // Border for interactive elements on hover
        'ui-border-focus': 'var(--accent-9)', // Changed from var(--accent-8) to make it stronger, aligns with brand-primary

        // Text Colors
        'text-primary': 'var(--gray-12)',
        'text-secondary': 'var(--gray-11)',
        'text-muted': 'var(--gray-9)', // For less important text
        'text-disabled': 'var(--gray-8)',
        'text-accent': 'var(--accent-11)', // For links or accented text
        'text-accent-hover': 'var(--accent-12)',

        // Specific Radix semantic variables (if using accentColor directly)
        // 'primary-solid': 'var(--accent-9)',
        // 'primary-solid-hover': 'var(--accent-10)',
        // 'primary-bg-subtle': 'var(--accent-3)',
        // 'primary-text': 'var(--accent-11)',
        // 'primary-text-contrast': 'var(--accent-contrast)', // High contrast text on primary-solid
      },
      fontFamily: {
        // Add custom fonts here if needed
      },
    },
  },
  plugins: [],
} 