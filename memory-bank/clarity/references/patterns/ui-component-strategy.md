## Pattern 2: UI Component Strategy: Radix UI Primitives + Tailwind CSS

**Goal:** Use Radix UI Primitives for accessible component behavior and Tailwind CSS for all styling, leveraging the theming capabilities (CSS variables for colors, light/dark mode) provided by `@radix-ui/themes` through its `<Theme>` provider.

*   **DO:** Use components from `@radix-ui/react-*` (Radix UI Primitives) for accessible, unstyled UI behaviors (Dialogs, Dropdowns, Checkboxes, Sliders, etc.).
*   **DO:** Utilize the `@radix-ui/themes` library primarily for its `<Theme>` provider at the root of the application. This provider sets up CSS custom properties for colors (accent, gray scales), appearance (light/dark mode), radius, and scaling, which are then consumed by Tailwind CSS utilities and custom styles.
*   **DO:** Use the built-in properties provided by Radix UI Primitives (e.g., `open`, `onOpenChange`, `value`, `onValueChange`) to control component behavior.
*   **DO:** Apply styling to Radix Primitives using Tailwind CSS utility classes, which should leverage the theme variables exposed by `@radix-ui/themes` (e.g., by mapping Tailwind colors to these CSS variables in `tailwind.config.js`). Encapsulate common styling patterns within wrapper components (see Pattern 6, now detailed in [encapsulating-styling-patterns.md](./encapsulating-styling-patterns.md)).
*   **DO:** Create wrapper components in `components/ui/` around Radix Primitives to encapsulate common styling patterns and provide a consistent API within our project.
*   **DON'T:** Use components for the same purpose from `@headlessui/react`.
*   **DON'T:** Import and use *pre-styled individual components* directly from the `@radix-ui/themes` library (e.g., do not `import { Button } from '@radix-ui/themes';`). Prefer using Radix UI Primitives (e.g., `@radix-ui/react-button`) and styling them with Tailwind CSS, which in turn uses the theme variables.
*   **DON'T:** Rely on `@radix-ui/colors` library directly for color definitions in components; use Tailwind's color system, which is configured to use the Radix theme variables.

**Example (Illustrative):**

```typescript
// DON'T DO THIS (using Radix Themes component directly for individual UI elements)
// import { Button } from '@radix-ui/themes';
// ...

// DO THIS (using Radix UI Primitive + Tailwind Styling, potentially via a wrapper component)
// Ensure your Tailwind config (webApp/tailwind.config.js) is set up to use Radix theme variables for colors.
// Example: Styling a Radix Dialog Primitive
// import * as DialogPrimitive from '@radix-ui/react-dialog';
// import clsx from 'clsx';

// function MyStyledDialog({ open, onOpenChange, children }) {
//   return (
//     <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
//       <DialogPrimitive.Portal>
//         <DialogPrimitive.Overlay className={clsx(
//           "fixed inset-0 bg-black/50 dark:bg-black/70", // Uses Tailwind colors potentially mapped to Radix vars
//           "data-[state=open]:animate-in data-[state=closed]:animate-out",
//           "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0"
//         )} />
//         <DialogPrimitive.Content className={clsx(
//           "fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2",
//           "border bg-ui-bg p-6 shadow-lg duration-200", // bg-ui-bg from tailwind.config.js, mapped to Radix vars
//           "data-[state=open]:animate-in data-[state=closed]:animate-out",
//           "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
//           "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
//           "data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%]",
//           "data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]",
//           "sm:rounded-lg"
//         )}>
//           {children}
//           <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground">
//             {/* <Cross2Icon className="h-4 w-4" /> */}
//             <span className="sr-only">Close</span>
//           </DialogPrimitive.Close>
//         </DialogPrimitive.Content>
//       </DialogPrimitive.Portal>
//     </DialogPrimitive.Root>
//   );
// }


// For overall application theming (typically in webApp/src/main.tsx or webApp/src/App.tsx):
// DO THIS:
// import { Theme } from '@radix-ui/themes';
// import '@radix-ui/themes/styles.css'; // Import Radix Themes base styles

// <Theme accentColor="blue" grayColor="slate" appearance="light">
//   {/* Rest of your application using Radix Primitives styled with Tailwind */}
// </Theme>
```

*Note: The example code is illustrative. Actual import paths, component names, and animation/styling classes might vary. Refer to the project's codebase (`webApp/src/components/ui/` for common primitives like `dialog.tsx`, `button.tsx`, etc.) and `webApp/tailwind.config.js` for concrete implementations.* 