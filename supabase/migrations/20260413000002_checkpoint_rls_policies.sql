-- RLS policies for LangGraph checkpoint tables
-- These tables are auto-created by AsyncPostgresSaver.setup() and have no user_id column.
-- Access is server-internal only (direct Postgres via psycopg pool).
-- Per-user scoping happens at the workflow_runs layer, which already has user-scoped RLS.
-- These policies lock down the PostgREST surface: deny anon/authenticated, allow service_role.

CREATE POLICY "Service role full access to checkpoint_migrations"
    ON checkpoint_migrations FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access to checkpoints"
    ON checkpoints FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access to checkpoint_blobs"
    ON checkpoint_blobs FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access to checkpoint_writes"
    ON checkpoint_writes FOR ALL
    USING (auth.role() = 'service_role');
