## Pattern 7: Consistent Error Display

**Goal:** Show errors to the user in a clear, consistent, and predictable way, enhancing user experience and aiding troubleshooting.

*   **DO:** Display clear, user-friendly error messages that explain what went wrong in simple terms. Avoid jargon.
*   **DO:** Show validation errors (from form inputs, etc.) directly next to or below the form field they relate to. Make it obvious which input needs correction.
*   **DO:** Show general application errors (e.g., failed API calls not tied to a specific form, unexpected system issues) in a prominent global area. This could be a toast notification system (Pattern 2 implies Radix Toast is preferred), a banner at the top of the page, or a dedicated section in the UI.
*   **DO:** Use dedicated, reusable UI components for displaying error messages (e.g., a component like `ErrorMessage.tsx` or integrating error display into input wrappers). This component should reside in `webApp/src/components/ui/` if it's a general-purpose error display atom.
*   **DO:** Ensure error messages are accessible (e.g., associated with inputs via `aria-describedby`, sufficient color contrast).
*   **DO:** Log detailed technical error information (stack traces, API response details) to the browser console or a dedicated monitoring service for debugging purposes, but *never* show these raw details directly to the end-user.
*   **DON'T:** Show raw backend error messages, JSON responses, or technical stack traces directly to the user. Abstract these into user-friendly messages.
*   **DON'T:** Fail silently. If an operation fails or an error occurs that impacts the user, they should be informed.
*   **DON'T:** Use inconsistent methods, styling, or placement for displaying errors across different parts of the application.

**Example (Illustrative - Conceptual `ErrorMessage` component):**

```typescript
// In: webApp/src/components/ui/ErrorMessage.tsx (Conceptual)
// import React from 'react';
// import clsx from 'clsx';
// import { ExclamationTriangleIcon } from '@radix-ui/react-icons'; // Example icon

// interface ErrorMessageProps {
//   message?: string | null;
//   className?: string;
//   isInline?: boolean; // To differentiate styling/placement if needed
// }

// export function ErrorMessage({ message, className, isInline = true }: ErrorMessageProps) {
//   if (!message) return null;

//   return (
//     <div
//       role="alert" // Important for accessibility
//       className={clsx(
//         "flex items-center gap-x-2 text-sm",
//         isInline ? "text-destructive-text dark:text-destructive-text-dark" : "p-3 rounded-md bg-destructive-bg dark:bg-destructive-bg-dark text-destructive-text dark:text-destructive-text-dark border border-destructive-border dark:border-destructive-border-dark",
//         className
//       )}
//     >
//       <ExclamationTriangleIcon className="h-4 w-4" />
//       <span>{message}</span>
//     </div>
//   );
// }

// Usage in a form component (inline validation error):
// function MyForm() {
//   const [emailError, setEmailError] = useState<string | null>(null);
//   // ... form state and validation logic ...

//   const handleSubmit = () => {
//     if (!isValidEmail(email)) { // Assume isValidEmail is a validation function
//       setEmailError("Please enter a valid email address.");
//       return;
//     }
//     setEmailError(null); // Clear error on successful validation
//     // ... submit logic ...
//   };

//   return (
//     <form onSubmit={handleSubmit}>
//       <div>
//         <label htmlFor="email">Email:</label>
//         <input id="email" type="email" aria-describedby={emailError ? "email-error" : undefined} />
//         {emailError && <ErrorMessage message={emailError} id="email-error" className="mt-1" />}
//       </div>
//       <button type="submit">Submit</button>
//     </form>
//   );
// }

// Usage for a general API error (e.g., using a toast, assuming toast setup elsewhere):
// import { toast } from "your-toast-library"; // e.g., Radix Toast via a custom hook

// function someApiCall() {
//   fetch("/api/data")
//     .then(async response => {
//       if (!response.ok) {
//         const err = await response.json();
//         throw new Error(err.message || "Failed to fetch data.");
//       }
//       return response.json();
//     })
//     .catch(error => {
//       // Show a user-friendly global error message
//       // toast.error(error.message || "An unexpected error occurred.");
//       console.error("API call failed:", error); // Log technical details
//     });
// }
```

*Note: The example code is illustrative. Specific component implementations (`ErrorMessage.tsx`), class names (like `text-destructive-text`), and integration with form libraries or toast systems will depend on the project's actual setup in `webApp/src/components/ui/` and `tailwind.config.js`.* 