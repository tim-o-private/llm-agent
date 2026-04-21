-- SPEC-045 follow-up: tighten RLS on approval_cards and activity_log.
--
-- The original migrations (20260420000001, 20260420000002) used bare
-- `auth.uid() = user_id` predicates and the UPDATE policy on approval_cards
-- omitted WITH CHECK. That is exploitable two ways:
--
--   1. Bare auth.uid() resolves against the caller's current search_path.
--      public.is_record_owner() is SECURITY DEFINER with a pinned
--      search_path — the project convention elsewhere — and locks the
--      check against search_path manipulation.
--
--   2. UPDATE without WITH CHECK lets an attacker who satisfies USING flip
--      user_id to another account during the update, effectively stealing
--      the row. WITH CHECK is mandatory on any UPDATE policy on a table
--      whose rows are user-scoped.
--
-- This migration drops the two affected policies and recreates them using
-- public.is_record_owner() and (for UPDATE) a matching WITH CHECK clause.

-- approval_cards ---------------------------------------------------------

DROP POLICY IF EXISTS "Users can view own approval cards" ON approval_cards;
DROP POLICY IF EXISTS "Users can update own approval cards" ON approval_cards;

CREATE POLICY "Users can view own approval cards"
    ON approval_cards FOR SELECT
    USING (public.is_record_owner(user_id));

CREATE POLICY "Users can update own approval cards"
    ON approval_cards FOR UPDATE
    USING (public.is_record_owner(user_id))
    WITH CHECK (public.is_record_owner(user_id));

-- activity_log -----------------------------------------------------------

DROP POLICY IF EXISTS "Users can view own activity log" ON activity_log;

CREATE POLICY "Users can view own activity log"
    ON activity_log FOR SELECT
    USING (public.is_record_owner(user_id));
