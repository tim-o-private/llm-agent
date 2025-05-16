# Style Guide - Clarity Web Application

This document outlines the visual and interaction style guidelines for the Clarity web application. Its purpose is to ensure a consistent, accessible, and emotionally supportive user experience, particularly for users with ADHD.

## 1. Core Philosophy & Design Goals

*   **Calm & Minimal:** The UI should be uncluttered, reducing cognitive load. Avoid visual noise and unnecessary distractions.
*   **Joyful Touches:** While minimal, incorporate subtle, positive feedback and delightful micro-interactions where appropriate (e.g., on task completion).
*   **Accessible (WCAG 2.1 AA Target):** Design with accessibility as a foremost concern. This includes color contrast, keyboard navigation, semantic HTML, and ARIA attributes where necessary.
*   **Neurodivergent-Friendly:** Prioritize clarity, predictability, and low friction. Minimize choices per screen and maintain a strong visual hierarchy.
*   **Emotionally Supportive:** The design and language should be encouraging and non-judgmental.
*   **Consistent:** Maintain consistency in layout, component behavior, and visual styling across the application.

## 2. Color Palette & Theming Engine

*   **Primary Theming Engine:** Radix UI Themes (`@radix-ui/themes`) is the foundation for our color system and base component theming. It manages light/dark modes and allows for various accent color palettes.
*   **TailwindCSS Integration:** TailwindCSS is used for layout, spacing, typography, and custom component styling. Tailwind color utilities should be configured to map to Radix Theme CSS custom properties to ensure consistency (e.g., a Tailwind class like `bg-primary` would use `var(--accent-9)` from Radix Themes).
*   **Color Scales:** Leverage the accessible color scales provided by Radix UI Colors (which are integral to Radix UI Themes).
*   **Accent Colors:** Theme accent colors (e.g., different brand palettes like "blue", "green", "violet") will be managed via the `accentColor` prop on the Radix `<Theme>` provider.
*   **Themes (Modes):** Support for Light and Dark modes is managed by the Radix `<Theme>` provider (`appearance` prop).

## 3. Typography

*   **Font Family:** Use large, readable sans-serif fonts. (Specific font to be determined and defined in Tailwind config).
*   **Hierarchy:** Establish a clear typographic hierarchy for headings, body text, and UI labels to guide the user and improve readability.
*   **Readability:** Ensure sufficient line height, letter spacing, and text size for comfortable reading.

## 4. Component Styling & UI Primitives

*   **Theming Foundation:** Radix UI Themes provides the base theme (colors, radius, scaling) for components.
*   **UI Primitives:** Use Radix UI Primitives (`@radix-ui/react-*`) for core accessible behaviors. These primitives will be styled by the Radix Theme and can be further customized with TailwindCSS.
*   **TailwindCSS for Customization:** TailwindCSS is used for layouts, spacing, and any styling overrides or custom component styling not covered by the Radix Theme.
*   **Wrapper Components (Pattern 6):** For common or repeated Tailwind utility combinations (especially for layout or custom components not directly using Radix Theme styling), create dedicated, reusable wrapper components in `webApp/src/components/ui/`.
*   **State & Interaction:** Clearly indicate interactive states (hover, focus, active, disabled). Radix Themes and Primitives handle many of these; supplement with TailwindCSS as needed for custom components.

## 5. Iconography

*   **Icon Set:** Utilize Lucide Icons (`lucide-react`) for consistent and clean iconography.
*   **Usage:** Icons should be simple, clear, and used purposefully to enhance comprehension, not for decoration alone.
*   **Accessibility:** Ensure icons that convey meaning have appropriate ARIA labels or are accompanied by text.

## 6. Animation

*   **Principle:** Animations should be simple, purposeful, and efficient. They should enhance the user experience, not distract or cause performance issues.
*   **Preference:** Prefer CSS transitions and keyframe animations where possible due to performance and simplicity.
*   **JavaScript Animation:** Use `framer-motion` sparingly and only for complex animation needs that cannot be easily met with CSS. Animations should remain deliberate and not overly flashy.

## 7. Voice & Tone (Language)

*   **Friendly & Approachable:** Use clear, simple language. Avoid jargon.
*   **Non-Judgmental & Supportive:** Language should be encouraging, especially in feedback and coaching interactions.
*   **Concise:** Be brief and to the point, respecting the user's attention.

## 8. Layout Principles

*   **Visual Hierarchy:** Guide the user's attention with clear visual hierarchy (spacing, typography, color).
*   **Consistency:** Maintain consistent layouts for similar types of pages or sections.
*   **Responsiveness:** Ensure layouts adapt gracefully to different screen sizes.
*   **Minimal Choices:** Reduce cognitive load by presenting minimal, relevant choices on each screen.

## 9. Accessibility (WCAG 2.1 AA)

While specific techniques are covered in implementation patterns (like Pattern 10), the style guide reinforces the commitment:
*   **Color Contrast:** Adhere to WCAG AA contrast ratios for text and meaningful visual elements.
*   **Keyboard Navigation:** All interactive elements must be keyboard accessible with visible focus indicators.
*   **Semantic HTML:** Use HTML elements according to their semantic meaning.
*   **ARIA Attributes:** Use ARIA attributes correctly to enhance accessibility for custom components or dynamic content changes.

## Advanced Theming with Radix UI Themes

The primary theming capabilities are provided by Radix UI Themes, which is integrated with Tailwind CSS for utility styling. Here's how to manage and customize the theme:

### 1. Changing the Core Theme (Accent Color, Gray Color, Appearance)

The broadest theme changes are controlled via the `<Theme>` provider in `webApp/src/main.tsx`.

*   **Appearance (Light/Dark/System):**
    *   Managed by `useThemeStore` (in `webApp/src/stores/useThemeStore.ts`).
    *   The `appearance` prop of `<Theme>` is dynamically set based on the store's state.
    *   Users can toggle this via the `ThemeToggle.tsx` component.

*   **Accent Color:**
    *   The `accentColor` prop of the `<Theme>` provider in `main.tsx` controls the primary brand color used throughout the application (e.g., for buttons, focus rings, active states).
    *   **To change the accent color globally:** Modify the `accentColor` value in `main.tsx`. For example, to change from `indigo` to `green`:
        ```tsx
        // webApp/src/main.tsx
        <Theme accentColor="green" grayColor="slate" appearance={effectiveAppearance}>
          <App />
        </Theme>
        ```
    *   Radix Themes supports a variety of accent colors. Refer to the Radix Themes documentation for the full list of available color names.

*   **Gray Color Scale:**
    *   The `grayColor` prop of the `<Theme>` provider in `main.tsx` controls the neutral gray palette used for backgrounds, text, borders, etc.
    *   Changing this (e.g., from `slate` to `mauve` or `sand`) can significantly alter the app's look and feel.
        ```tsx
        // webApp/src/main.tsx
        <Theme accentColor="indigo" grayColor="mauve" appearance={effectiveAppearance}>
          <App />
        </Theme>
        ```

### 2. Fine-tuning with Other `<Theme>` Props

Radix UI Themes offers additional props on the `<Theme>` provider for more granular control:

*   `panelBackground`: Can be set to `solid` or `translucent`. Our current default is `solid` via the Radix Theme defaults, reflected in semantic tokens like `ui-bg` mapping to `var(--color-panel-solid)`.
*   `radius`: Controls the default border-radius for Radix components (e.g., `none`, `small`, `medium`, `large`, `full`). Tailwind utilities can override this on a per-component basis.
*   `scaling`: Adjusts the density of UI elements (e.g., `90%`, `100%`, `110%`).

    These can be set in `main.tsx` as needed:
    ```tsx
    // webApp/src/main.tsx
    <Theme accentColor="indigo" grayColor="slate" appearance={effectiveAppearance} radius="medium" scaling="100%">
      <App />
    </Theme>
    ```

### 3. Styling Individual Components: Radix Props vs. Tailwind Utilities

Many Radix UI Theme components (and Radix UI Primitives, if used directly) expose their own props for styling (e.g., `color`, `size`, `variant` on a Radix Button).

*   **When to use Radix Component Props:**
    *   For properties directly supported by the Radix component that align with the overall theme (e.g., using a Radix Button's `color="red"` prop will use the themed red, which is good).
    *   When you want to leverage built-in variants or states that Radix components provide.

*   **When to use Tailwind CSS Utilities:**
    *   For layout (margins, padding, flexbox, grid), typography (font size, weight, if not covered by Radix defaults), and specific sizing not available via Radix props.
    *   When you need to apply one of the semantic color tokens defined in `tailwind.config.js` (e.g., `bg-brand-primary`, `text-text-secondary`) because these are guaranteed to be theme-aware.
    *   For overriding Radix styles when a more custom look is needed that Radix props don't allow.
    *   For responsive styling (`sm:`, `md:` prefixes).

*   **Combining Both:** It's common to use both. For example, a Radix `Button` might use its `variant` and `color` props, while Tailwind utilities are used for margins around it.

    ```tsx
    // Example: Using Radix Button props and Tailwind for margin
    import { Button } from '@radix-ui/themes';

    <Button color="grass" variant="solid" highContrast className="mt-4">
      Save Changes
    </Button>
    ```
    In this example, `color`, `variant`, `highContrast` are Radix props. `className="mt-4"` uses a Tailwind utility.

*   **Custom Components using `@apply`:** For more complex, reusable styles on custom components (like `.btn-primary` in `ui-components.css`), continue to use `@apply` with semantic Tailwind tokens. These tokens, in turn, use the Radix CSS variables, ensuring theme consistency.

### 4. Future: User-Selectable Palettes

While the current setup allows developers to change `accentColor` and `grayColor` globally, future enhancements could involve allowing users to select from a predefined list of accent/gray color combinations. This would likely involve: 

*   Expanding `useThemeStore` to store user preferences for `accentColor` and `grayColor`.
*   Updating `main.tsx` to read these values from the store and pass them to the `<Theme>` provider.
*   Creating UI elements (e.g., in a settings panel) for users to make these selections.

This approach maintains the benefits of Radix Theming while offering personalization.

This style guide will evolve as the Clarity application develops. Refer to `memory-bank/techContext.md` for technology choices and `memory-bank/clarity/implementationPatterns.md` for detailed implementation rules. 