import js from '@eslint/js';
import typescript from '@typescript-eslint/eslint-plugin';
import typescriptParser from '@typescript-eslint/parser';
import reactHooks from 'eslint-plugin-react-hooks';

export default [
  js.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: typescriptParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        // Browser globals
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
        navigator: 'readonly',
        fetch: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        // DOM types
        HTMLElement: 'readonly',
        HTMLDivElement: 'readonly',
        HTMLInputElement: 'readonly',
        HTMLTextAreaElement: 'readonly',
        HTMLSelectElement: 'readonly',
        HTMLButtonElement: 'readonly',
        HTMLFormElement: 'readonly',
        HTMLLabelElement: 'readonly',
        HTMLAnchorElement: 'readonly',
        HTMLSpanElement: 'readonly',
        SVGSVGElement: 'readonly',
        // Event types
        Event: 'readonly',
        KeyboardEvent: 'readonly',
        FocusEvent: 'readonly',
        BeforeUnloadEvent: 'readonly',
        StorageEvent: 'readonly',
        // Test globals
        describe: 'readonly',
        it: 'readonly',
        expect: 'readonly',
        test: 'readonly',
        beforeEach: 'readonly',
        afterEach: 'readonly',
      },
    },
    plugins: {
      '@typescript-eslint': typescript,
      'react-hooks': reactHooks,
    },
    rules: {
      ...typescript.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      
      // Custom color validation rules
      'no-restricted-syntax': [
        'error',
        {
          selector: 'JSXAttribute[name.name="className"] Literal[value*="bg-blue-"]',
          message: 'Forbidden: Use semantic color tokens (bg-ui-element-bg, bg-brand-primary) instead of hardcoded Tailwind colors (bg-blue-*)',
        },
        {
          selector: 'JSXAttribute[name.name="className"] Literal[value*="bg-red-"]',
          message: 'Forbidden: Use semantic color tokens (bg-ui-element-bg, bg-brand-primary) instead of hardcoded Tailwind colors (bg-red-*)',
        },
        {
          selector: 'JSXAttribute[name.name="className"] Literal[value*="bg-green-"]',
          message: 'Forbidden: Use semantic color tokens (bg-ui-element-bg, bg-brand-primary) instead of hardcoded Tailwind colors (bg-green-*)',
        },
        {
          selector: 'JSXAttribute[name.name="className"] Literal[value*="bg-gray-"]',
          message: 'Forbidden: Use semantic color tokens (bg-ui-element-bg, bg-ui-bg) instead of hardcoded Tailwind colors (bg-gray-*)',
        },
        {
          selector: 'JSXAttribute[name.name="className"] Literal[value*="text-blue-"]',
          message: 'Forbidden: Use semantic color tokens (text-text-primary, text-brand-primary) instead of hardcoded Tailwind colors (text-blue-*)',
        },
        {
          selector: 'JSXAttribute[name.name="className"] Literal[value*="text-red-"]',
          message: 'Forbidden: Use semantic color tokens (text-text-primary, text-destructive) instead of hardcoded Tailwind colors (text-red-*)',
        },
        {
          selector: 'JSXAttribute[name.name="className"] Literal[value*="text-green-"]',
          message: 'Forbidden: Use semantic color tokens (text-text-primary, text-success-strong) instead of hardcoded Tailwind colors (text-green-*)',
        },
        {
          selector: 'JSXAttribute[name.name="className"] Literal[value*="text-gray-"]',
          message: 'Forbidden: Use semantic color tokens (text-text-primary, text-text-secondary, text-text-muted) instead of hardcoded Tailwind colors (text-gray-*)',
        },
        {
          selector: 'JSXAttribute[name.name="className"] Literal[value*="border-blue-"]',
          message: 'Forbidden: Use semantic color tokens (border-ui-border, border-brand-primary) instead of hardcoded Tailwind colors (border-blue-*)',
        },
        {
          selector: 'JSXAttribute[name.name="className"] Literal[value*="border-red-"]',
          message: 'Forbidden: Use semantic color tokens (border-ui-border, border-destructive) instead of hardcoded Tailwind colors (border-red-*)',
        },
        {
          selector: 'JSXAttribute[name.name="className"] Literal[value*="border-green-"]',
          message: 'Forbidden: Use semantic color tokens (border-ui-border, border-success-indicator) instead of hardcoded Tailwind colors (border-green-*)',
        },
        {
          selector: 'JSXAttribute[name.name="className"] Literal[value*="border-gray-"]',
          message: 'Forbidden: Use semantic color tokens (border-ui-border, border-ui-border-hover) instead of hardcoded Tailwind colors (border-gray-*)',
        },
        // Env var allowlist: any import.meta.env.VITE_* access not listed below is an error.
        // To add a new var: add a :not([property.name="VITE_NEW_VAR"]) clause.
        // Also update: webApp/Dockerfile ARG list + .github/workflows/fly-deploy.yml --build-arg list.
        {
          selector: [
            'MemberExpression',
            '[object.object.type="MetaProperty"]',
            '[object.property.name="env"]',
            '[property.name=/^VITE_/]',
            ':not([property.name="VITE_API_BASE_URL"])',
            ':not([property.name="VITE_SUPABASE_URL"])',
            ':not([property.name="VITE_SUPABASE_ANON_KEY"])',
            ':not([property.name="VITE_DEFAULT_CHAT_AGENT_ID"])',
            ':not([property.name="VITE_LOG_LEVEL"])',
            ':not([property.name="VITE_USE_ASSISTANT_UI"])',
            ':not([property.name="VITE_ENABLE_STREAMING_CHAT"])',
            ':not([property.name="VITE_ENABLE_TOOL_VISUALIZATION"])',
            ':not([property.name="VITE_ENABLE_MESSAGE_ACTIONS"])',
            ':not([property.name="VITE_ENABLE_ADVANCED_ACCESSIBILITY"])',
          ].join(''),
          message: 'Unknown VITE_ env var. Only allowlisted vars in eslint.config.js are permitted. If this is a new var, add it to the allowlist, Dockerfile ARGs, and fly-deploy.yml.',
        },
      ],
    },
  },
  // Test files: disable color validation but keep env var allowlist
  {
    files: ['**/*.test.{ts,tsx}', '**/*.spec.{ts,tsx}', '**/__tests__/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-syntax': [
        'error',
        // Only the env var allowlist rule — color rules are off in tests
        {
          selector: [
            'MemberExpression',
            '[object.object.type="MetaProperty"]',
            '[object.property.name="env"]',
            '[property.name=/^VITE_/]',
            ':not([property.name="VITE_API_BASE_URL"])',
            ':not([property.name="VITE_SUPABASE_URL"])',
            ':not([property.name="VITE_SUPABASE_ANON_KEY"])',
            ':not([property.name="VITE_DEFAULT_CHAT_AGENT_ID"])',
            ':not([property.name="VITE_LOG_LEVEL"])',
            ':not([property.name="VITE_USE_ASSISTANT_UI"])',
            ':not([property.name="VITE_ENABLE_STREAMING_CHAT"])',
            ':not([property.name="VITE_ENABLE_TOOL_VISUALIZATION"])',
            ':not([property.name="VITE_ENABLE_MESSAGE_ACTIONS"])',
            ':not([property.name="VITE_ENABLE_ADVANCED_ACCESSIBILITY"])',
          ].join(''),
          message: 'Unknown VITE_ env var. Only allowlisted vars in eslint.config.js are permitted. If this is a new var, add it to the allowlist, Dockerfile ARGs, and fly-deploy.yml.',
        },
      ],
    },
  },
  {
    ignores: ['dist/**', 'node_modules/**', '**/*.d.ts'],
  },
]; 