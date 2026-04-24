/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'brand-primary': 'var(--accent-9)',
        'brand-primary-hover': 'var(--accent-10)',
        'brand-primary-text': 'var(--accent-contrast)',
        'bg-accent-subtle': 'var(--accent-3)',
        'accent-subtle': 'var(--accent-3)',
        'text-accent-strong': 'var(--accent-11)',

        'accent-surface': 'var(--accent-surface)',
        'accent-indicator': 'var(--accent-indicator)',
        'accent-track': 'var(--accent-track)',

        'danger-bg': 'var(--red-9)',
        'danger-bg-hover': 'var(--red-10)',
        'border-destructive': 'var(--red-7)',
        'text-destructive': 'var(--red-11)',
        'bg-destructive-subtle': 'var(--red-3)',
        'text-destructive-strong': 'var(--red-11)',
        'destructive': 'var(--red-11)',

        'bg-info-subtle': 'var(--blue-3)',
        'text-info-strong': 'var(--blue-11)',
        'bg-info-indicator': 'var(--blue-9)',

        'bg-warning-subtle': 'var(--amber-3)',
        'text-warning-strong': 'var(--amber-11)',
        'bg-warning-indicator': 'var(--amber-9)',
        'warning-strong': 'var(--amber-11)',

        'bg-success-subtle': 'var(--green-3)',
        'text-success-strong': 'var(--green-11)',
        'bg-success-indicator': 'var(--green-9)',
        'success-indicator': 'var(--green-7)',
        'success-strong': 'var(--green-11)',

        'bg-neutral-subtle': 'var(--gray-3)',
        'text-neutral-strong': 'var(--gray-11)',
        'bg-neutral-indicator': 'var(--gray-9)',

        'ui-bg': 'var(--color-background)',
        'ui-bg-alt': 'var(--gray-2)',
        'ui-bg-hover': 'var(--gray-3)',

        'ui-element-bg': 'var(--color-panel-solid)',
        'ui-element-bg-hover': 'var(--gray-4)',
        'ui-modal-bg': 'var(--color-panel-solid)',

        'ui-interactive-bg': 'var(--gray-3)',
        'ui-interactive-bg-hover': 'var(--gray-4)',
        'ui-interactive-bg-active': 'var(--accent-3)',

        'ui-surface': 'var(--color-surface)',

        'ui-border': 'var(--gray-6)',
        'ui-border-hover': 'var(--gray-7)',
        'ui-border-focus': 'var(--accent-9)',

        'text-primary': 'var(--gray-12)',
        'text-secondary': 'var(--gray-11)',
        'text-muted': 'var(--gray-9)',
        'text-disabled': 'var(--gray-8)',
        'text-accent': 'var(--accent-11)',
        'text-accent-hover': 'var(--accent-12)',
        'accent-hover': 'var(--accent-12)',
      },

      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.2s ease-out',
        'slide-down': 'slideDown 0.2s ease-out',
        'scale-in': 'scaleIn 0.15s ease-out',
        'slide-in-right': 'slideInRight 0.2s ease-out',
      },

      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        slideInRight: {
          '0%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(0)' },
        },
      },

      boxShadow: {
        'elevated': '0 4px 12px -2px rgba(0, 0, 0, 0.15)',
      },

      fontFamily: {},
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
