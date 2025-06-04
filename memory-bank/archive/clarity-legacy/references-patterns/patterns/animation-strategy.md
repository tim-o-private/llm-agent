## Pattern 3: Re-evaluated Animation Strategy

**Goal:** Use animations deliberately and efficiently, favoring simplicity.

*   **DO:** Use standard CSS transitions or keyframe animations for simple visual feedback (fades, slides, hover effects) where possible. Define these using Tailwind utilities or standard CSS, potentially within wrapper components (see [encapsulating-styling-patterns.md](./encapsulating-styling-patterns.md)).
*   **DO:** Ensure any implemented animations align with the "low-stim" and "minimal cognitive load" design principles of the Clarity project.
*   **DON'T:** Add or retain `framer-motion` for animations that can be achieved simply and efficiently with CSS.
*   **DON'T:** Implement complex, distracting, or unnecessary animations.

This approach prioritizes performance and a calm user experience, especially beneficial for users who may be sensitive to excessive motion. 