## Pattern 11: Standardized DDL & Row Level Security (RLS) for Data Access

**Goal:** Ensure consistent, coherent, secure, and maintainable Data Definition Language (DDL) through a centralized `ddl.sql` file. Implement robust Row Level Security (RLS) for user data in Supabase, ensuring users can only access and modify their own records or records explicitly shared with them.

*   **DO:** Maintain `memory-bank/clarity/ddl.sql` as an up-to-date representation of the current database schema. This file should reflect the cumulative result of all applied Supabase migrations.
*   **DO:** Manage ALL database schema changes (table creation/alteration, function creation, policy changes, etc.) via Supabase migration scripts located in the `supabase/migrations/` directory. Do not make schema changes directly through the Supabase UI for environments tracked by migrations.
*   **DO:** Ensure all tables containing user-specific data (typically identified by a `user_id` column or similar foreign key to `auth.users`) have Row Level Security enabled (`ALTER TABLE your_table ENABLE ROW LEVEL SECURITY;`).
*   **DO:** Implement RLS policies using a reusable SQL helper function (e.g., `public.is_record_owner(record_user_id uuid)`) that checks if the `auth.uid()` of the currently authenticated user matches the `user_id` associated with a record. This function should typically be created with `SECURITY DEFINER` privileges.
*   **DO:** Create RLS policies for `SELECT`, `INSERT`, `UPDATE`, and `DELETE` operations as needed, utilizing the helper function in both `USING` (for read/delete/update visibility) and `WITH CHECK` (for write/update constraints) clauses.
*   **DO:** For comprehensive instructions on setting up the helper function, creating policies, and managing them via migrations, **strictly follow the detailed guide:** [`../guides/supabaseRLSGuide.md`](../guides/supabaseRLSGuide.md). This is the primary reference for RLS implementation.
*   **DON'T:** Manually create or modify RLS policies directly in the Supabase dashboard for environments managed by migrations, as these changes can be overwritten or cause conflicts.
*   **DON'T:** Write complex, repetitive RLS logic directly in each policy if a helper function can centralize and simplify it.
*   **DON'T:** Forget to test RLS policies thoroughly from the perspective of different user roles and an unauthenticated user to ensure they behave as expected.

**Primary Reference:**

For the definitive guide on implementing this pattern, including SQL function creation, policy examples, and migration management, refer to:
**[`../guides/supabaseRLSGuide.md`](../guides/supabaseRLSGuide.md)** 