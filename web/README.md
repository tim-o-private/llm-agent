# Clarity Web Application Structure

This document provides an overview of the `clarity-workspace/web` application, focusing on the frontend React application located in `apps/web`.

## 1. Overall Monorepo Structure

The `web/` directory is a pnpm workspace containing:

-   `apps/`: Houses the individual applications.
    -   `web/`: The main React frontend application (Vite-based).
    -   `api/`: The FastAPI backend application.
-   `package.json`: Root workspace configuration, scripts, and shared dev dependencies.
-   `pnpm-workspace.yaml`: Defines the pnpm workspace packages.

## 2. `apps/web` Frontend Application Structure

The `apps/web/src/` directory contains the core source code for the React application.

### Key Directories:

-   **`components/`**: Contains all React components.
    -   **`ui/`**: **Shared, reusable UI components.** This is where components migrated from the former `packages/ui` library now reside (e.g., `Button.tsx`, `Card.tsx`, `Modal.tsx`, `Input.tsx`, `FAB.tsx`, `TaskCard.tsx`, chat components like `MessageBubble.tsx`, etc.). These are designed to be generic building blocks.
    -   **`tasks/`**: Components specifically related to task management features (e.g., `FABQuickAdd.tsx`, `QuickAddTray.tsx`, `TaskListGroup.tsx`). These often compose components from `ui/`.
    -   **`navigation/`**: Components related to application navigation (e.g., `SideNav.tsx`, `TopBar.tsx` (if it were a component), `SidebarNav.tsx`).
    -   **`auth/`**: Components related to authentication (though most auth logic is in `features/auth/`).
    -   Other specific feature component directories as needed.

-   **`hooks/`**: Contains custom React hooks shared across the application (e.g., `useTheme.tsx`, `useDebounce.tsx`, `useToggle.tsx`). These were also migrated from the former `packages/ui`.

-   **`layouts/`**: Components responsible for the overall page structure and layout (e.g., `AppShell.tsx`, `AppLayout.tsx`). They orchestrate navigation components and the main content area.

-   **`pages/`**: Top-level components that represent different views/screens of the application (e.g., `TodayView.tsx`, `CoachPage.tsx`, `Login.tsx`). These typically assemble layout components and feature-specific components.

-   **`features/`**: Contains directories for feature-specific logic, services, and sometimes components that are tightly coupled to that feature (e.g., `auth/` for authentication logic, stores, and providers).

-   **`stores/`**: Zustand state management stores (e.g., `useChatStore.ts`, `useTaskStore.ts` (if created)).

-   **`styles/`**: Global stylesheets.
    -   `index.css`: Main entry point for global styles. Imports Tailwind base, components, and utilities. Can include global app-wide styles.
    -   `ui-components.css`: Contains base styles for some of the shared UI components from `src/components/ui/`, primarily using Tailwind's `@apply` directive (e.g., for `.btn` classes). This allows for more complex base styling not easily achievable with inline utilities alone.

-   **`main.tsx`**: The main entry point for the React application. Renders the root `App` component and sets up providers.

-   **`App.tsx`**: Root application component. Sets up routing and global providers like `AuthProvider`, `ErrorBoundary`, and `Suspense`.

-   **`vite.config.ts`**: Vite build tool configuration.

-   **`tailwind.config.js`**: Tailwind CSS configuration. **Crucially, `theme.extend.colors` defines the semantic color palette** (e.g., `brand-primary`, `ui-background`, `text-secondary`) used throughout the application for consistent theming.

-   **`tsconfig.json`**: TypeScript configuration, including path aliases like `@/*` (pointing to `src/*`) and `@components/*` for cleaner import paths.

## 3. Key UI Components (`src/components/ui/`)

This directory houses the fundamental building blocks of the application's interface. Most of these were migrated from the `packages/ui` library.

| Component             | Role                                                                                                | Styling Notes                                                                                                                                                                                              |
| --------------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Button.tsx`          | General purpose button with variants (primary, secondary, danger). Supports `asChild` prop.         | Base styles via `.btn`, `.btn-primary`, etc. in `ui-components.css` (using `@apply`). Colors use semantic tokens from `tailwind.config.js`. Inline Tailwind classes for specific layout/spacing.           |
| `Card.tsx`            | A container component with padding, rounded corners, and shadow.                                    | Primarily styled with inline Tailwind classes in its JSX (e.g., `bg-white`, `rounded-lg`, `shadow`).                                                                                                           |
| `Checkbox.tsx`        | Accessible checkbox component (based on Headless UI).                                               | Styled with inline Tailwind classes, leveraging `data-[checked]` and `data-[disabled]` selectors.                                                                                                           |
| `CoachCard.tsx`       | Specialized card for displaying AI Coach suggestions, with title, suggestion, and action buttons.   | Composes `Card` and `Button`. Styling primarily through inline Tailwind utilities and classes applied to the composed components.                                                                      |
| `FAB.tsx`             | Floating Action Button, typically for a primary action on a screen.                                 | Fixed positioning and core styling (shape, shadow) via inline Tailwind classes. Icon and size are configurable.                                                                                        |
| `Input.tsx`           | Standard text input field.                                                                          | Core styling (border, padding, focus rings) applied with inline Tailwind classes. Colors use semantic tokens (e.g., `border-gray-300`, `focus:ring-blue-600`).                                             |
| `Label.tsx`           | Standard label for form elements.                                                                   | Styled with inline Tailwind classes (font size, weight, color).                                                                                                                                            |
| `Modal.tsx`           | Accessible modal dialog component (based on Radix UI Dialog).                                         | Overlay and content panel styled with inline Tailwind classes. Uses fixed positioning and transforms.                                                                                                       |
| `Spinner.tsx`         | Animated loading spinner.                                                                           | SVG with inline Tailwind classes for animation (`animate-spin`) and color.                                                                                                                                 |
| `TaskCard.tsx`        | Displays individual task details, including checkbox, title, time, and category.                    | Composes `Card` and `Checkbox`. Styling primarily through inline Tailwind utilities. Conditional styling for `completed` state.                                                                          |
| `TaskStatusBadge.tsx` | Small inline badge to show task status (e.g., "Upcoming", "Completed").                             | Styled with inline Tailwind classes. Background and text colors vary based on status, using semantic tokens or direct Tailwind color classes.                                                              |
| `ThemeToggle.tsx`     | Button to toggle between light and dark themes.                                                     | Composes `Button`. Uses `useTheme` hook.                                                                                                                                                                   |
| `ToggleField.tsx`     | Accessible toggle switch with a label (based on Headless UI Switch).                                | Label and switch styled with inline Tailwind classes, leveraging `data-[checked]` for state.                                                                                                                 |
| **Chat Components:**  |                                                                                                     |                                                                                                                                                                                                            |
| `chat/MessageBubble.tsx` | Displays a single chat message (user, AI, or system).                                            | Styling for different senders (colors, alignment) applied with inline Tailwind classes.                                                                                                                    |
| `chat/MessageHeader.tsx` | Header for the chat panel, showing title and status.                                              | Inline Tailwind classes for layout and typography.                                                                                                                                                         |
| `chat/MessageInput.tsx`  | Input field and send button for chat messages.                                                    | Composes `Input` and `Button`. Styled with inline Tailwind classes.                                                                                                                                        |

## 4. Styling Strategy

The application primarily uses **Tailwind CSS** for styling.

-   **Utility-First:** Most styling is done directly within component JSX using Tailwind's utility classes (e.g., `p-4`, `flex`, `text-lg`, `bg-brand-primary`). This is the preferred method for layout, spacing, typography, and component-specific styling.

-   **Semantic Color Tokens:** Colors are defined as semantic tokens in `web/apps/web/tailwind.config.js` under `theme.extend.colors` (e.g., `brand-primary`, `ui-background`, `text-primary`, `dark-ui-background`). These tokens should be used whenever applying colors (e.g., `bg-brand-primary`, `text-text-secondary`) to ensure consistency and simplify theming (especially for dark mode).

-   **`ui-components.css` (`@layer components`):** Located at `web/apps/web/src/styles/ui-components.css`, this file is used for more complex base styles that are shared by UI components or when a dedicated CSS class is beneficial. It uses Tailwind's `@apply` directive to compose utilities into custom classes (e.g., `.btn`, `.btn-primary`). Edits here will affect all instances of components using these classes.

-   **Global Styles (`index.css`):** Located at `web/apps/web/src/styles/index.css`, this file imports Tailwind's base, components, and utilities. It can also be used for truly global styles or CSS resets, but most application-specific styling should be in components or `ui-components.css`.

### How to Change Styles:

1.  **For specific component instances (e.g., margin on one button):** Add/modify Tailwind utility classes directly in the JSX where the component is used.
2.  **For general styling of a shared UI component (e.g., all `Input` fields):**
    *   Modify the inline Tailwind utility classes within the component's definition (e.g., in `src/components/ui/Input.tsx`).
    *   Use the semantic color tokens from `tailwind.config.js` for colors.
3.  **For base styles of components that use `@apply` (e.g., all `.btn`s):**
    *   Modify the corresponding class definition in `src/styles/ui-components.css`.
4.  **To change the overall color scheme (e.g., brand color):**
    *   Update the semantic color token definitions in `web/apps/web/tailwind.config.js`. Changes here will propagate throughout the app.
5.  **For global styles affecting the whole app (e.g., base font):**
    *   Consider `src/styles/index.css` or the `body` tag styling (often in `index.html` or via `index.css`).

Remember to have the Vite development server running (`pnpm --filter @clarity/web dev`) to see style changes hot-reload in the browser. 