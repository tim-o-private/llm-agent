/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "../../packages/ui/src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand Colors
        'brand-primary': '#4f46e5', // Indigo 600
        'brand-primary-hover': '#4338ca', // Indigo 700
        'brand-secondary': '#ec4899', // Pink 500

        // UI Element Backgrounds
        'ui-background': '#ffffff', // White
        'ui-background-alt': '#f3f4f6', // Gray 100
        'ui-element': '#e5e7eb', // Gray 200 (for subtle elements)
        'ui-element-hover': '#d1d5db', // Gray 300

        // Borders
        'ui-border': '#e5e7eb', // Gray 200
        'ui-border-focus': '#4f46e5', // Indigo 600 (for focus rings)

        // Text Colors
        'text-primary': '#111827', // Gray 900
        'text-secondary': '#6b7280', // Gray 500
        'text-disabled': '#9ca3af', // Gray 400
        'text-on-brand': '#ffffff', // White (for text on brand-primary bg)
        'text-link': '#3b82f6', // Blue 500

        // Dark Mode (examples, assuming you use dark: prefix)
        // You would use these like: dark:bg-dark-ui-background, dark:text-dark-text-primary
        'dark-ui-background': '#1f2937', // Gray 800
        'dark-ui-background-alt': '#374151', // Gray 700
        'dark-ui-element': '#4b5563', // Gray 600
        'dark-ui-element-hover': '#52525b', // Gray 500 (? zinc-600 is #52525b, gray-500 is #6b7280)
        'dark-ui-border': '#4b5563', // Gray 600
        'dark-text-primary': '#f3f4f6', // Gray 100
        'dark-text-secondary': '#9ca3af', // Gray 400
        'dark-text-on-brand': '#ffffff', // White
      },
      fontFamily: {
        // Add custom fonts here if needed
      },
    },
  },
  plugins: [],
} 