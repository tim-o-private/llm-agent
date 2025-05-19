## Pattern 9: Form Management with React Hook Form & Zod

**Goal:** Handle forms, validation, and submission logic in a structured, maintainable, and type-safe way using industry-standard libraries.

*   **DO:** Use React Hook Form (`react-hook-form`) for managing all form state (input values, touched fields, dirty state, submission status, etc.).
*   **DO:** Define form data schemas using Zod (`zod`). This includes data types, required fields, string formats (email, URL), number ranges, etc.
*   **DO:** Integrate Zod schemas with React Hook Form for validation using the `@hookform/resolvers/zod` resolver.
*   **DO:** Display validation errors provided by React Hook Form (derived from Zod schema) next to the respective form fields, using a consistent error display component (see Pattern 7).
*   **DO:** Handle form submission logic within the `onSubmit` function provided to React Hook Form's `handleSubmit` method. This function will only be called if validation passes.
*   **DO:** Inside the `onSubmit` handler, call the appropriate React Query mutation hook (see Pattern 5) to send data to the backend.
*   **DO:** Create reusable, controlled input components (e.g., `Input`, `Textarea`, `Select`, `Checkbox`) that integrate with React Hook Form's `register` method or `Controller` component for more complex/custom inputs.
*   **DON'T:** Manage form state (input values, errors, submission status) manually using multiple `useState` hooks for any non-trivial form.
*   **DON'T:** Write custom validation logic directly within components if it can be defined declaratively in a Zod schema.
*   **DON'T:** Mix form state management logic deeply within presentational UI components; keep it managed by React Hook Form.

**Example (Illustrative - SignUpForm):**

```typescript
// DON'T DO THIS (Manual form state/validation for a complex form)
// function ComplexFormManual() {
//   const [name, setName] = useState('');
//   const [email, setEmail] = useState('');
//   const [password, setPassword] = useState('');
//   const [nameError, setNameError] = useState(null);
//   const [emailError, setEmailError] = useState(null);
//   // ... more state and validation logic ...
//   const handleSubmit = () => { /* ... manual validation and submission ... */ };
//   return ( /* ... inputs and errors ... */ );
// }

// DO THIS (Using React Hook Form with Zod)
// import { useForm, SubmitHandler } from 'react-hook-form';
// import { z } from 'zod';
// import { zodResolver } from '@hookform/resolvers/zod';
// import { ErrorMessage } from '@/components/ui/ErrorMessage'; // From Pattern 7
// import { useSignUpMutation } from '@/api/hooks/useAuthHooks'; // Hypothetical RQ mutation hook (Pattern 5)

// 1. Define the Zod schema for form data and validation
// const signUpSchema = z.object({
//   name: z.string().min(1, "Name is required").max(100, "Name is too long"),
//   email: z.string().email("Invalid email address"),
//   password: z.string().min(8, "Password must be at least 8 characters"),
//   confirmPassword: z.string(),
// }).refine(data => data.password === data.confirmPassword, {
//   message: "Passwords don't match",
//   path: ["confirmPassword"], // Path of error
// });

// Infer the TypeScript type from the Zod schema
// type SignUpFormData = z.infer<typeof signUpSchema>;

// function SignUpForm() {
//   const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<SignUpFormData>({
//     resolver: zodResolver(signUpSchema),
//     defaultValues: {
//       name: '',
//       email: '',
//       password: '',
//       confirmPassword: ''
//     }
//   });

//   const signUpMutation = useSignUpMutation(); // Your React Query mutation hook

//   const processForm: SubmitHandler<SignUpFormData> = async (data) => {
//     // Data is validated by Zod at this point
//     try {
//       // Destructure to avoid sending confirmPassword to backend if not needed
//       const { confirmPassword, ...submissionData } = data;
//       await signUpMutation.mutateAsync(submissionData);
//       // toast.success("Sign up successful!");
//       // router.push("/dashboard"); // Example redirect
//     } catch (error: any) {
//       // toast.error(error.message || "Sign up failed. Please try again.");
//     }
//   };

//   return (
//     <form onSubmit={handleSubmit(processForm)} className="space-y-4">
//       <div>
//         <label htmlFor="name">Name:</label>
//         <input id="name" {...register("name")} />
//         <ErrorMessage message={errors.name?.message} />
//       </div>

//       <div>
//         <label htmlFor="email">Email:</label>
//         <input id="email" type="email" {...register("email")} />
//         <ErrorMessage message={errors.email?.message} />
//       </div>

//       <div>
//         <label htmlFor="password">Password:</label>
//         <input id="password" type="password" {...register("password")} />
//         <ErrorMessage message={errors.password?.message} />
//       </div>

//       <div>
//         <label htmlFor="confirmPassword">Confirm Password:</label>
//         <input id="confirmPassword" type="password" {...register("confirmPassword")} />
//         <ErrorMessage message={errors.confirmPassword?.message} />
//       </div>

//       <button type="submit" disabled={isSubmitting}>
//         {isSubmitting ? "Signing Up..." : "Sign Up"}
//       </button>
//       {/* Display general form error from mutation if needed */}
//       {/* {signUpMutation.error && <ErrorMessage message={signUpMutation.error.message} />} */}
//     </form>
//   );
// }
```

*Note: The example code is illustrative. Actual setup for `ErrorMessage`, toast notifications, React Query mutation hooks (`useSignUpMutation`), and routing will depend on the project's specific implementation in `webApp/`.* 