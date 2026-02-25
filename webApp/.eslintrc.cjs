module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  globals: {
    URLSearchParams: 'readonly',
  },
  extends: [
    'eslint:recommended',
    '@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs'],
  parser: '@typescript-eslint/parser',
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
    // Custom rule to prevent hardcoded Tailwind colors
    'no-hardcoded-colors': 'error',
    // Allow unused variables/parameters prefixed with _ (intentionally unused)
    '@typescript-eslint/no-unused-vars': ['error', {
      varsIgnorePattern: '^_',
      argsIgnorePattern: '^_',
      caughtErrorsIgnorePattern: '^_',
    }],
  },
  overrides: [
    {
      files: ['**/*.{ts,tsx}'],
      rules: {
        // Allow unused variables/parameters prefixed with _ (intentionally unused)
        '@typescript-eslint/no-unused-vars': ['error', {
          varsIgnorePattern: '^_',
          argsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        }],
        // Custom rule to detect forbidden color classes
        'no-restricted-syntax': [
          'error',
          {
            selector: 'JSXAttribute[name.name="className"] Literal[value*="bg-blue-"], JSXAttribute[name.name="className"] Literal[value*="bg-red-"], JSXAttribute[name.name="className"] Literal[value*="bg-green-"], JSXAttribute[name.name="className"] Literal[value*="bg-yellow-"], JSXAttribute[name.name="className"] Literal[value*="bg-purple-"], JSXAttribute[name.name="className"] Literal[value*="bg-pink-"], JSXAttribute[name.name="className"] Literal[value*="bg-indigo-"], JSXAttribute[name.name="className"] Literal[value*="bg-gray-"]',
            message: 'Forbidden: Use semantic color tokens (bg-ui-element-bg, bg-brand-primary) instead of hardcoded Tailwind colors (bg-blue-*, bg-gray-*, etc.)',
          },
          {
            selector: 'JSXAttribute[name.name="className"] Literal[value*="text-blue-"], JSXAttribute[name.name="className"] Literal[value*="text-red-"], JSXAttribute[name.name="className"] Literal[value*="text-green-"], JSXAttribute[name.name="className"] Literal[value*="text-yellow-"], JSXAttribute[name.name="className"] Literal[value*="text-purple-"], JSXAttribute[name.name="className"] Literal[value*="text-pink-"], JSXAttribute[name.name="className"] Literal[value*="text-indigo-"], JSXAttribute[name.name="className"] Literal[value*="text-gray-"]',
            message: 'Forbidden: Use semantic color tokens (text-text-primary, text-brand-primary) instead of hardcoded Tailwind colors (text-blue-*, text-gray-*, etc.)',
          },
          {
            selector: 'JSXAttribute[name.name="className"] Literal[value*="border-blue-"], JSXAttribute[name.name="className"] Literal[value*="border-red-"], JSXAttribute[name.name="className"] Literal[value*="border-green-"], JSXAttribute[name.name="className"] Literal[value*="border-yellow-"], JSXAttribute[name.name="className"] Literal[value*="border-purple-"], JSXAttribute[name.name="className"] Literal[value*="border-pink-"], JSXAttribute[name.name="className"] Literal[value*="border-indigo-"], JSXAttribute[name.name="className"] Literal[value*="border-gray-"]',
            message: 'Forbidden: Use semantic color tokens (border-ui-border, border-brand-primary) instead of hardcoded Tailwind colors (border-blue-*, border-gray-*, etc.)',
          },
        ],
      },
    },
  ],
} 