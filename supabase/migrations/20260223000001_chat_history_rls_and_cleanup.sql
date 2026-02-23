-- ============================================
-- SPEC-017 FU-4: RLS defense-in-depth
--
-- 1. Add user-scoped SELECT policy on chat_message_history
-- 2. Remove duplicate email_digests policies
-- 3. Standardize CURRENT_USER = 'postgres' → TO "service_role"
-- ============================================

-- -----------------------------------------------
-- 1. User-scoped RLS on chat_message_history
-- -----------------------------------------------
-- chat_message_history has RLS enabled and a service_role policy,
-- but no user-scoped policy. Users should only see messages from
-- their own chat sessions.
CREATE POLICY "Users can view own chat history"
    ON public.chat_message_history FOR SELECT TO authenticated
    USING (session_id IN (
        SELECT session_id FROM public.chat_sessions WHERE user_id = auth.uid()
    ));

-- -----------------------------------------------
-- 2. Remove duplicate email_digests policies
-- -----------------------------------------------
-- Two pairs of duplicates exist (INSERT and SELECT).
-- Keep the longer-named versions ("...their own email digests").
DROP POLICY IF EXISTS "Users can insert their own digests" ON public.email_digests;
DROP POLICY IF EXISTS "Users can view their own digests" ON public.email_digests;

-- -----------------------------------------------
-- 3. Standardize service-role policies
-- -----------------------------------------------
-- Replace CURRENT_USER = 'postgres' checks with proper TO "service_role"
-- grants. The service_role bypasses RLS by default in Supabase, but
-- explicit TO "service_role" is the canonical pattern and clearer than
-- a CURRENT_USER check that couples to an internal username.

-- agent_schedules
DROP POLICY IF EXISTS "Service role can access all schedules" ON public.agent_schedules;
CREATE POLICY "Service role can access all schedules"
    ON public.agent_schedules TO "service_role"
    USING (true);

-- email_digests (service INSERT)
DROP POLICY IF EXISTS "Service role can insert digests" ON public.email_digests;
CREATE POLICY "Service role can insert digests"
    ON public.email_digests FOR INSERT TO "service_role"
    WITH CHECK (true);

-- user_channels
DROP POLICY IF EXISTS "Service role can manage all channels" ON public.user_channels;
CREATE POLICY "Service role can manage all channels"
    ON public.user_channels TO "service_role"
    USING (true);

-- agent_execution_results
DROP POLICY IF EXISTS "Service role can manage all execution results" ON public.agent_execution_results;
CREATE POLICY "Service role can manage all execution results"
    ON public.agent_execution_results TO "service_role"
    USING (true);

-- channel_linking_tokens
DROP POLICY IF EXISTS "Service role can manage all linking tokens" ON public.channel_linking_tokens;
CREATE POLICY "Service role can manage all linking tokens"
    ON public.channel_linking_tokens TO "service_role"
    USING (true);

-- notifications
DROP POLICY IF EXISTS "Service role can manage all notifications" ON public.notifications;
CREATE POLICY "Service role can manage all notifications"
    ON public.notifications TO "service_role"
    USING (true);
