-- Fix: Drop the old 2-arg get_oauth_tokens_for_scheduler to resolve PGRST203.
-- PostgREST cannot disambiguate the 2-arg (uuid, text) and 3-arg (uuid, text, uuid DEFAULT NULL)
-- overloads. The 3-arg version with DEFAULT NULL is backward compatible.

DROP FUNCTION IF EXISTS public.get_oauth_tokens_for_scheduler(uuid, text);
