# Supabase Row Level Security (RLS) Implementation Guide

This guide outlines a robust approach to implementing Row Level Security in Supabase using a reusable SQL helper function and database migrations. This method helps ensure consistency and reduces fragility when managing RLS policies across multiple tables.

**Goal:** Enforce that users can only access or modify records they own, based on a `user_id` column, in a standardized way.

## Prerequisites

*   Supabase CLI installed and initialized in your project.
*   Familiarity with creating and running database migrations via the Supabase CLI.

## Step 1: Create the Reusable SQL Helper Function

This function will check if the currently authenticated user is the owner of a given record.

1.  **Create a new migration file:**
    In your terminal, navigate to your Supabase project directory and run:
    ```bash
    supabase migration new create_rls_helper_function
    ```
    This command creates a new SQL file in `supabase/migrations/` (e.g., `supabase/migrations/<timestamp>_create_rls_helper_function.sql`).

2.  **Add the SQL function definition to the migration file:**
    Open the newly created `.sql` file and add the following:
    ```sql
    -- supabase/migrations/<timestamp>_create_rls_helper_function.sql

    CREATE OR REPLACE FUNCTION public.is_record_owner(record_user_id uuid)
    RETURNS boolean
    LANGUAGE sql
    SECURITY DEFINER
    SET search_path = public -- Ensures 'auth.uid()' is found if your function is in a different schema
    AS $$
      SELECT auth.uid() = record_user_id;
    $$;

    -- Optional: Grant execute permission if your default grants are restrictive.
    -- This is often not needed if the 'authenticated' role has default execute
    -- permissions on new functions in the public schema.
    -- GRANT EXECUTE ON FUNCTION public.is_record_owner(uuid) TO authenticated;
    ```
    *   **`SECURITY DEFINER`**: Crucial. Executes the function with the permissions of the user who defined it (owner), allowing reliable access to `auth.uid()`.
    *   **`SET search_path = public`**: Helps ensure `auth.uid()` is found if the `auth` schema isn't in the default search path when RLS policies call this function.

## Step 2: Apply RLS to an Existing Table (Example: `tasks`)

You can add the SQL for applying RLS to a specific table in the *same* migration file created in Step 1, or create a new, separate migration file.

1.  **Edit the migration file (e.g., `<timestamp>_create_rls_helper_function.sql`):**
    If adding to the same file, append the following SQL. Ensure the target table (e.g., `public.tasks`) already exists and has a `user_id` column of type `uuid` that typically references `auth.users(id)`.

    ```sql
    -- ... (SQL for is_record_owner function from above) ...

    -- Enable RLS and apply policy to the 'tasks' table

    -- 1. Enable Row Level Security on the table
    ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;

    -- 2. Create the policy using the helper function
    -- This policy allows full access (SELECT, INSERT, UPDATE, DELETE) if the user is the owner.
    CREATE POLICY "Enable full access for record owners on tasks"
    ON public.tasks
    FOR ALL -- Or be more specific: FOR SELECT, FOR INSERT, etc.
    USING (public.is_record_owner(user_id))        -- Checked for existing rows (SELECT, UPDATE, DELETE)
    WITH CHECK (public.is_record_owner(user_id));   -- Checked for new/modified rows (INSERT, UPDATE)

    -- Optional: Policy to allow service_role keys to bypass RLS for this table
    -- (service_role bypasses RLS by default, but explicit policies can make this clearer or manage other admin roles)
    -- CREATE POLICY "Allow service_role to bypass RLS on tasks"
    -- ON public.tasks
    -- AS PERMISSIVE
    -- FOR ALL
    -- TO service_role -- or a specific admin role you've created
    -- USING (true)
    -- WITH CHECK (true);
    ```

## Step 3: Applying RLS to Future Tables

For each new table requiring this ownership-based RLS:

1.  **Create a new migration file:**
    ```bash
    supabase migration new setup_rls_for_my_new_table
    ```

2.  **Add the RLS DDL to the new migration file:**
    For instance, if you create a table named `projects` with a `user_id` column:
    ```sql
    -- supabase/migrations/<timestamp>_setup_rls_for_my_new_table.sql

    -- Assume 'projects' table is created in this migration or a previous one
    -- with a 'user_id' uuid column.

    -- 1. Enable Row Level Security on the 'projects' table
    ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

    -- 2. Create the policy using the helper function
    CREATE POLICY "Enable full access for record owners on projects"
    ON public.projects
    FOR ALL
    USING (public.is_record_owner(user_id))
    WITH CHECK (public.is_record_owner(user_id));

    -- Optional: Policy for service_role bypass (if not relying on default bypass)
    -- CREATE POLICY "Allow service_role to bypass RLS on projects"
    -- ON public.projects AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true);
    ```

## Step 4: Running Migrations

1.  **Apply migrations to your local Supabase instance:**
    (Ensure your local Supabase services are running, e.g., via `supabase start`)
    ```bash
    supabase db push
    ```
    Alternatively, to apply migrations incrementally:
    ```bash
    supabase migration up
    ```

2.  **Deploy migrations to a linked remote Supabase project (staging/production):**
    First, link your project if you haven't: `supabase link --project-ref <your-project-ref>`
    Commit your migration files to Git.
    Then, to apply pending migrations to the remote database:
    ```bash
    supabase migration up
    ```
    *(Note: The Supabase documentation now often recommends `supabase db push --linked` for direct pushes to linked projects, but `migration up` is the traditional way to apply versioned migrations).*

## Step 5: Testing RLS

*   **Supabase Studio (SQL Editor):**
    Use `SET ROLE authenticated;`
    And `SELECT set_config('request.jwt.claims', '{"sub":"<user_id_to_test_with>", "role":"authenticated"}', true);`
    Then, attempt `SELECT`, `INSERT`, `UPDATE`, `DELETE` operations on the protected tables to verify that only the specified user can access/modify their own records.
*   **Client Application:**
    Thoroughly test through your frontend and/or backend application logic using different user accounts. Verify that data leakage does not occur and that users can perform actions only on data they own.

## Key Benefits of This Approach

*   **Reduced Fragility:** The core ownership check is centralized in the `is_record_owner` SQL function. Updates to this logic (if ever needed) are made in one place.
*   **Consistency:** RLS policy statements for each table become very similar, minimizing errors.
*   **Clarity & Maintainability:** The RLS strategy is easier to understand, review, and manage as part of your version-controlled database migrations.

## Important Considerations

*   **`user_id` Column:** Ensure all tables intended for this RLS pattern have a consistent `user_id` column (e.g., type `uuid`) that stores the user's unique identifier from `auth.users.id`.
*   **Granular Policies:** While `FOR ALL` is used in examples for simplicity, you might need separate policies `FOR SELECT`, `FOR INSERT`, `FOR UPDATE`, `FOR DELETE` if the conditions for each operation differ. Remember:
    *   `USING` clause applies to `SELECT`, `UPDATE`, `DELETE`.
    *   `WITH CHECK` clause applies to `INSERT`, `UPDATE`.
*   **`service_role` Access:** By default, Supabase's `service_role` key bypasses RLS. This is often necessary for administrative backend operations. If you need RLS to apply even to `service_role` (less common), you would need to manage that explicitly.
*   **Error Handling:** Test how your application handles scenarios where RLS prevents an operation. Users should receive appropriate feedback. 