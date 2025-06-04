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
        // Enhanced Brand & Accent Colors with gradients
        'brand-primary': 'var(--accent-9)',
        'brand-primary-hover': 'var(--accent-10)',
        'brand-primary-text': 'var(--accent-contrast)',
        'bg-accent-subtle': 'var(--accent-3)',
        'accent-subtle': 'var(--accent-3)',
        'text-accent-strong': 'var(--accent-11)',
        
        // Dynamic gradient colors for modern effects
        'gradient-primary': 'linear-gradient(135deg, var(--violet-9), var(--blue-9))',
        'gradient-secondary': 'linear-gradient(135deg, var(--violet-6), var(--blue-6))',
        'gradient-accent': 'linear-gradient(135deg, var(--violet-11), var(--purple-11))',
        
        // Vibrant accent variations
        'accent-electric': 'var(--violet-11)',
        'accent-neon': 'var(--blue-11)',
        'accent-glow': 'var(--purple-9)',
        
        // Strategic accent usage for key UI elements
        'accent-surface': 'var(--accent-surface)',
        'accent-indicator': 'var(--accent-indicator)',
        'accent-track': 'var(--accent-track)',

        // Enhanced Destructive Colors with more punch
        'danger-bg': 'var(--red-9)',
        'danger-bg-hover': 'var(--red-10)',
        'danger-glow': 'var(--red-11)',
        'border-destructive': 'var(--red-7)',
        'text-destructive': 'var(--red-11)',
        'bg-destructive-subtle': 'var(--red-3)',
        'text-destructive-strong': 'var(--red-11)',
        'destructive': 'var(--red-11)',

        // Enhanced Info Colors (Blue) with vibrancy
        'bg-info-subtle': 'var(--blue-3)',
        'text-info-strong': 'var(--blue-11)',
        'bg-info-indicator': 'var(--blue-9)',
        'info-electric': 'var(--cyan-11)',

        // Enhanced Warning Colors (Amber/Yellow) with energy
        'bg-warning-subtle': 'var(--amber-3)',
        'text-warning-strong': 'var(--amber-11)',
        'bg-warning-indicator': 'var(--amber-9)',
        'warning-strong': 'var(--amber-11)',
        'warning-glow': 'var(--yellow-11)',

        // Enhanced Success Colors (Green) with vitality
        'bg-success-subtle': 'var(--green-3)',
        'text-success-strong': 'var(--green-11)',
        'bg-success-indicator': 'var(--green-9)',
        'success-indicator': 'var(--green-7)',
        'success-strong': 'var(--green-11)',
        'success-electric': 'var(--mint-11)',

        // Neutral/Muted Colors with more character
        'bg-neutral-subtle': 'var(--gray-3)',
        'text-neutral-strong': 'var(--gray-11)',
        'bg-neutral-indicator': 'var(--gray-9)',

        // Enhanced UI Element Backgrounds with depth
        'ui-bg': 'var(--color-background)',
        'ui-bg-alt': 'var(--gray-2)',
        'ui-bg-hover': 'var(--gray-3)',
        'ui-bg-glow': 'var(--violet-2)', // Subtle glow effect
        
        'ui-element-bg': 'var(--color-panel-solid)',
        'ui-element-bg-hover': 'var(--gray-4)',
        'ui-element-bg-elevated': 'var(--gray-1)', // For elevated cards
        'ui-modal-bg': 'var(--color-panel-solid)',
        
        'ui-interactive-bg': 'var(--gray-3)',
        'ui-interactive-bg-hover': 'var(--gray-4)',
        'ui-interactive-bg-active': 'var(--accent-3)',
        'ui-interactive-bg-glow': 'var(--violet-4)', // Glowing interactive states
        
        // Enhanced surface backgrounds
        'ui-surface': 'var(--color-surface)',
        'ui-surface-elevated': 'var(--gray-1)',
        'ui-surface-glow': 'var(--violet-1)',

        // Enhanced Borders with more definition
        'ui-border': 'var(--gray-6)',
        'ui-border-hover': 'var(--gray-7)',
        'ui-border-focus': 'var(--accent-9)',
        'ui-border-glow': 'var(--violet-7)', // Glowing borders
        'ui-border-electric': 'var(--blue-8)', // Electric borders

        // Enhanced Text Colors with more personality
        'text-primary': 'var(--gray-12)',
        'text-secondary': 'var(--gray-11)',
        'text-muted': 'var(--gray-9)',
        'text-disabled': 'var(--gray-8)',
        'text-accent': 'var(--accent-11)',
        'text-accent-hover': 'var(--accent-12)',
        'accent-hover': 'var(--accent-12)',
        'text-electric': 'var(--violet-12)', // Electric text
        'text-glow': 'var(--blue-12)', // Glowing text
      },
      
      // Enhanced animations and effects
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'glow-pulse': 'glowPulse 2s ease-in-out infinite',
        'gradient-shift': 'gradientShift 3s ease-in-out infinite',
        'float': 'float 3s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
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
        glowPulse: {
          '0%, 100%': { boxShadow: '0 0 5px var(--violet-9)' },
          '50%': { boxShadow: '0 0 20px var(--violet-9), 0 0 30px var(--violet-7)' },
        },
        gradientShift: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-5px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      
      // Enhanced shadows and effects
      boxShadow: {
        'glow': '0 0 15px rgba(139, 92, 246, 0.3)',
        'glow-lg': '0 0 25px rgba(139, 92, 246, 0.4)',
        'electric': '0 0 20px rgba(59, 130, 246, 0.5)',
        'neon': '0 0 30px rgba(168, 85, 247, 0.6)',
        'elevated': '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
      },
      
      // Enhanced backdrop blur
      backdropBlur: {
        'xs': '2px',
        'glass': '12px',
      },
      
      fontFamily: {
        // Add custom fonts here if needed
      },
    },
  },
  plugins: [],
} 