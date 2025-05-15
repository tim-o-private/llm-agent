# WebApp Import Strategy

This document outlines the canonical import strategy for the `webApp/` (Clarity UI) part of the project. Consistent adherence to this strategy is crucial for code maintainability and to prevent module resolution errors.

## 1. Path Aliases Configuration

The project (`webApp/`) is configured with the following path aliases in `vite.config.ts` and `tsconfig.json`:

*   `@/`: Maps to `webApp/src/`
*   `@components/`: Maps to `webApp/src/components/`
*   `@features/`: Maps to `webApp/src/features/`
*   `@hooks/`: Maps to `webApp/src/hooks/` (Note: API hooks are in `src/api/hooks/`)
*   `@lib/`: Maps to `webApp/src/lib/`
*   `@styles/`: Maps to `webApp/src/styles/`

## 2. Canonical Import Rules

**Rule 1: Prioritize the Primary Alias (`@/`)**

*   For all imports that access a top-level directory within `webApp/src/` (e.g., `components`, `api`, `lib`, `utils`, `features`, `stores`), **use the primary `@/` alias.**
*   This is the most general and universally recommended alias for consistency.
*   **Examples:**
    *   `import { Button } from '@/components/ui/Button';`
    *   `import { TaskCard } from '@/components/ui/TaskCard';`
    *   `import { useFetchTasks } from '@/api/hooks/useTaskHooks';`
    *   `import { cn } from '@/lib/utils';`
    *   `import { taskParser } from '@/utils/taskParser';`
    *   `import { useAuthStore } from '@/stores/useAuthStore';` (assuming stores are in `src/stores`)
    *   `import { MySpecificFeatureComponent } from '@/features/myFeature/MySpecificFeatureComponent';`

**Rule 2: Specific Aliases (e.g., `@components/`)**

*   While functional, the more specific aliases (e.g., `@components/`, `@features/`) are **discouraged in favor of the primary `@/` alias** to maintain a single, simple, and memorable convention. Using `@/components/` is preferred over `@components/`.

**Rule 3: API Hooks Import Path**

*   All React Query hooks for API interactions are located in `webApp/src/api/hooks/`.
*   Always import these using the `@/` alias directly pointing to this path:
    *   `import { useCreateTask } from '@/api/hooks/useTaskHooks';`
*   The `@hooks/` alias (pointing to `src/hooks/`) should only be used if a separate directory `src/hooks/` exists for non-API, UI-specific React hooks. If such a directory isn't actively used or is causing confusion, consider removing this alias in the future.

**Rule 4: Relative Paths (`../`, `./`)**

*   Relative paths are **permitted and encouraged ONLY for imports *within the same logical module or a closely-nested feature directory*.**
*   The goal is to keep imports local when files are inherently part of the same, tightly-coupled unit.
*   **Examples:**
    *   If `MyComponent.tsx` and `MyHelper.ts` are both inside `webApp/src/features/MyFeature/`, then `MyComponent.tsx` can import `MyHelper.ts` using `import { myHelperUtil } from './MyHelper';`.
    *   If `SubComponent.tsx` is in `webApp/src/features/MyFeature/subparts/`, it can import from `MyComponent.tsx` (in `webApp/src/features/MyFeature/`) using `import { MyComponent } from '../MyComponent';`.
*   **CRITICAL: Do NOT use relative paths to traverse *out* of a major feature directory or up to other top-level `src/` directories (like `components`, `api`, `lib`, `utils`). Use the `@/` alias for such cases.**
    *   **Incorrect:** `import { Button } from '../../components/ui/Button';` (from within a feature)
    *   **Correct:** `import { Button } from '@/components/ui/Button';`

**Rule 5: External Libraries**

*   Import directly by their package name.
*   **Examples:**
    *   `import React from 'react';`
    *   `import { useQueryClient } from '@tanstack/react-query';`
    *   `import { defineConfig } from 'vite';`

## 3. Linting & Enforcement (Future Consideration)

To further improve consistency, ESLint rules can be configured to enforce these pathing conventions. This is not yet implemented but should be considered if issues persist.

## 4. Addressing Past Issues

Previous import errors often stemmed from:
*   Inconsistent use of aliases vs. relative paths.
*   Incorrectly assuming or constructing aliases (e.g., `@components/ui/Button` vs. `@/components/ui/Button`).
*   Typographical errors in paths.

By strictly following the rules above, particularly **Rule 1 (Prioritize `@/`)** and **Rule 4 (Limit Relative Paths)**, these issues should be minimized. 