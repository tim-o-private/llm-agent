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

This style guide will evolve as the Clarity application develops. Refer to `memory-bank/techContext.md` for technology choices and `memory-bank/clarity/implementationPatterns.md` for detailed implementation rules. 