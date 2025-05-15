# Clarity Frontend Application (`webApp`)

This document provides an overview of the Clarity frontend React application, located in the `webApp/` directory.

## 1. Frontend Application Structure (`src/`)

The `src/` directory contains the core source code for the React application.

### Key Directories:

-   **`components/`**: Contains all React components.
    -   **`ui/`**: **Shared, reusable UI components.** (e.g., `Button.tsx`, `Card.tsx`, `Modal.tsx`, `Input.tsx`, `FAB.tsx`, `TaskCard.tsx`, chat components like `MessageBubble.tsx`, etc.). These are designed to be generic building blocks.
    -   **`tasks/`**: Components specifically related to task management features (e.g., `FABQuickAdd.tsx`, `QuickAddTray.tsx`, `TaskListGroup.tsx`). These often compose components from `ui/`.
    -   **`navigation/`**: Components related to application navigation (e.g., `SideNav.tsx`, `TopBar.tsx` (if it were a component), `SidebarNav.tsx`).
    -   **`auth/`**: Components related to authentication (though most auth logic is in `features/auth/`).
    -   Other specific feature component directories as needed.

-   **`hooks/`**: Contains custom React hooks shared across the application (e.g., `useTheme.tsx`, `useDebounce.tsx`, `useToggle.tsx`).

-   **`layouts/`**: Components responsible for the overall page structure and layout (e.g., `AppShell.tsx`). They orchestrate navigation components and the main content area.

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

## 2. Key UI Components (`src/components/ui/`)

This directory houses the fundamental building blocks of the application's interface.

| Component             | Role                                                                                                | Styling Notes                                                                                                                                                                                              |
| --------------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Button.tsx`          | General purpose button with variants (primary, secondary, danger). Supports `asChild` prop.         | Base styles via `.btn`, `.btn-primary`, etc. in `ui-components.css` (using `@apply`). Colors use semantic tokens from `tailwind.config.js`. Inline Tailwind classes for specific layout/spacing.           |
| `Card.tsx`            | A container component with padding, rounded corners, and shadow.                                    | Primarily styled with inline Tailwind classes in its JSX (e.g., `bg-white`, `rounded-lg`, `shadow`).                                                                                                           |
| `Checkbox.tsx`        | Accessible checkbox component (based on Radix UI Checkbox).                                         | Styled with inline Tailwind classes, leveraging `data-[state=checked]` and `data-[disabled]` selectors.                                                                                                  |
| `CoachCard.tsx`       | Specialized card for displaying AI Coach suggestions, with title, suggestion, and action buttons.   | Composes `Card` and `Button`. Styling primarily through inline Tailwind utilities and classes applied to the composed components.                                                                      |
| `ErrorMessage.tsx`    | Displays a standardized error message, often used with form validation.                             | Styled with inline Tailwind classes for typography and color (e.g., `text-red-600`). Can accept an ARIA live region polite.                                                                          |
| `FAB.tsx`             | Floating Action Button, typically for a primary action on a screen.                                 | Fixed positioning and core styling (shape, shadow) via inline Tailwind classes. Icon and size are configurable.                                                                                        |
| `Input.tsx`           | Standard text input field.                                                                          | Core styling (border, padding, focus rings) applied with inline Tailwind classes. Colors use semantic tokens (e.g., `border-gray-300`, `focus:ring-blue-600`).                                             |
| `Label.tsx`           | Standard label for form elements.                                                                   | Styled with inline Tailwind classes (font size, weight, color).                                                                                                                                            |
| `Modal.tsx`           | Accessible modal dialog component (based on Radix UI Dialog).                                         | Overlay and content panel styled with inline Tailwind classes. Uses fixed positioning and transforms. CSS animations for open/close states.                                                                |
| `Spinner.tsx`         | Animated loading spinner.                                                                           | SVG with inline Tailwind classes for animation (`animate-spin`) and color.                                                                                                                                 |
| `TaskCard.tsx`        | Displays individual task details, including checkbox, title, time, and category.                    | Composes `Card` and `Checkbox`. Styling primarily through inline Tailwind utilities. Conditional styling for `completed` state.                                                                          |
| `TaskStatusBadge.tsx` | Small inline badge to show task status (e.g., "Upcoming", "Completed").                             | Styled with inline Tailwind classes. Background and text colors vary based on status, using semantic tokens or direct Tailwind color classes.                                                              |
| `ThemeToggle.tsx`     | Button to toggle between light and dark themes.                                                     | Composes `Button`. Uses `useTheme` hook.                                                                                                                                                                   |
| `ToggleField.tsx`     | Accessible toggle switch with a label (based on Radix UI Switch).                                   | Label and switch styled with inline Tailwind classes, leveraging `data-[state=checked]` for state.                                                                                                      |
| **Chat Components:**  |                                                                                                     |                                                                                                                                                                                                            |
| `chat/MessageBubble.tsx` | Displays a single chat message (user, AI, or system).                                            | Styling for different senders (colors, alignment) applied with inline Tailwind classes.                                                                                                                    |
| `chat/MessageHeader.tsx` | Header for the chat panel, showing title and status.                                              | Inline Tailwind classes for layout and typography.                                                                                                                                                         |
| `chat/MessageInput.tsx`  | Input field and send button for chat messages.                                                    | Composes `Input` and `Button`. Styled with inline Tailwind classes.                                                                                                                                        |

## 3. Styling Strategy

The application primarily uses **Tailwind CSS** for styling, integrated with **Radix UI Themes** for foundational theming, color palettes (light/dark modes, accent colors), and consistency with Radix Primitives.

-   **Utility-First (Tailwind):** Most styling is done directly within component JSX using Tailwind's utility classes (e.g., `p-4`, `flex`, `text-lg`). This is the preferred method for layout, spacing, typography, and component-specific styling.

-   **Radix UI Themes:** The `<Theme>` provider from `@radix-ui/themes` wraps the application (in `main.tsx`), establishing the base appearance (light/dark/system), accent color (e.g., `indigo`), and gray color scale (e.g., `slate`). This provides CSS custom properties (e.g., `var(--accent-9)`, `var(--gray-12)`) that are then used by Tailwind.

-   **Semantic Color Tokens (Tailwind Config):** Colors are defined as semantic tokens in `tailwind.config.js` under `theme.extend.colors`. **These tokens map to the Radix UI Theme CSS variables.** This is the source of truth for application-specific color semantics.
    *   **Examples of Frequently Used Semantic Tokens:**
        *   `brand-primary`: Main brand/accent color (e.g., for primary buttons, active elements). Uses `var(--accent-9)`.
        *   `brand-primary-hover`: Hover state for brand primary. Uses `var(--accent-10)`.
        *   `brand-primary-text`: Text color for on-brand-primary backgrounds. Uses `var(--accent-contrast)`.
        *   `ui-bg`: Default main background for panels/pages. Uses `var(--color-panel-solid)`.
        *   `ui-element-bg`: Default background for elements like cards. Uses `var(--gray-3)`.
        *   `ui-interactive-bg`: Base background for interactive elements. Uses `var(--gray-3)`.
        *   `ui-interactive-bg-hover`: Hover state for interactive elements. Uses `var(--gray-4)`.
        *   `ui-border`: Standard border color. Uses `var(--gray-6)`.
        *   `text-primary`: Primary text color. Uses `var(--gray-12)`.
        *   `text-secondary`: Secondary text color. Uses `var(--gray-11)`.
        *   `text-destructive`: Text color for destructive actions/errors. Uses `var(--red-11)`.
        *   `danger-bg`: Background for destructive buttons/elements. Uses `var(--red-9)`.
    *   Always use these semantic tokens (e.g., `bg-brand-primary`, `text-text-secondary`) when applying colors to ensure consistency and simplify theming.

-   **`ui-components.css` (`@layer components`):** Located at `src/styles/ui-components.css`, this file is used for more complex base styles that are shared by UI components or when a dedicated CSS class is beneficial. It uses Tailwind's `@apply` directive to compose utilities into custom classes (e.g., `.btn`, `.btn-primary`). Edits here will affect all instances of components using these classes.

-   **Global Styles (`index.css`):** Located at `src/styles/index.css`, this file imports Tailwind's base, components, and utilities. It can also be used for truly global styles or CSS resets, but most application-specific styling should be in components or `ui-components.css`.

### How to Change Styles:

1.  **For specific component instances (e.g., margin on one button):** Add/modify Tailwind utility classes directly in the JSX where the component is used.
2.  **For general styling of a shared UI component (e.g., all `Input` fields):**
    *   Modify the inline Tailwind utility classes within the component's definition (e.g., in `src/components/ui/Input.tsx`).
    *   Use the semantic color tokens from `tailwind.config.js` for colors.
3.  **For base styles of components that use `@apply` (e.g., all `.btn`s):**
    *   Modify the corresponding class definition in `src/styles/ui-components.css`.
4.  **To change the overall color scheme (e.g., brand color, light/dark appearance):**
    *   Update the `<Theme>` provider props in `webApp/src/main.tsx` (e.g., `accentColor`, `grayColor`, `appearance` linked to `useThemeStore`).
    *   The underlying Radix variables will change, and since semantic tokens in `tailwind.config.js` point to these variables, the app's theme will update.
    *   For finer-grained control over specific semantic meanings (if Radix defaults aren't enough), you can adjust the mappings in `tailwind.config.js`, but the primary mechanism for broad theme changes (like accent color) is via the Radix `<Theme>` provider.
5.  **For global styles affecting the whole app (e.g., base font):**
    *   Consider `src/styles/index.css` or the `body` tag styling (often in `index.html` or via `index.css`).

Remember to have the Vite development server running (`pnpm dev` when in the `webApp/` directory, or `pnpm --filter clarity-frontend dev` from the project root) to see style changes hot-reload in the browser.

### Environment Variables

Create a `.env` file in the `webApp` root directory and add the following environment variables. These are used by Vite during development and build processes.

```
# Supabase credentials (replace with your actual project details)
VITE_SUPABASE_URL=your_supabase_project_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key

# API Base URL (optional for development if using proxy, required for production builds)
# For development, if you want to be explicit and not rely solely on proxy for constructing full URLs:
# VITE_API_BASE_URL=http://localhost:3001
# For production builds, this will be set via Fly.io secrets (e.g., https://clarity-chatserver.fly.dev)
# VITE_API_BASE_URL=https://your_chat_server_fly_dev_url
```

*   `VITE_SUPABASE_URL`: The URL of your Supabase project.
*   `VITE_SUPABASE_ANON_KEY`: The public anonymous key for your Supabase project.
*   `VITE_API_BASE_URL`: The base URL for the backend API (`chatServer`). For local development, API calls to `/api/*` are typically proxied via `vite.config.ts`. For production, this URL must point to the deployed `chatServer` instance.

Ensure the `.env` file is added to your `.gitignore` to prevent committing sensitive keys.

### API Connection

During local development, the Vite development server (`vite dev`) proxies API requests made from the `webApp` to the `chatServer` backend. This is configured in `vite.config.ts`:

```typescript
// webApp/vite.config.ts excerpt
server: {
  port: 3000, // webApp runs on port 3000
  proxy: {
    '/api': {
      target: 'http://localhost:3001', // chatServer is expected to run on port 3001
      changeOrigin: true,
    },
  },
},
```

This means that any fetch request from the frontend to a path like `/api/chat` will be forwarded to `http://localhost:3001/api/chat` by the Vite dev server.

For production builds, the `webApp` is built with a `VITE_API_BASE_URL` environment variable (e.g., `https://clarity-chatserver.fly.dev`). The frontend code must then use this variable to construct absolute URLs when making API calls, for example: `fetch(\`\\${import.meta.env.VITE_API_BASE_URL}/api/chat\`)` 