-- Fix dangerous permissions on store_oauth_tokens function
-- This function should only be accessible to service_role, not authenticated users

-- Revoke the dangerous permissions
REVOKE EXECUTE ON FUNCTION public.store_oauth_tokens FROM authenticated;
REVOKE EXECUTE ON FUNCTION public.store_oauth_tokens FROM anon;
REVOKE EXECUTE ON FUNCTION public.store_oauth_tokens FROM public;

-- Grant only to service_role (this is what should have been done)
GRANT EXECUTE ON FUNCTION public.store_oauth_tokens TO service_role;

-- Verify current permissions (for logging)
SELECT 
    routine_name,
    grantee,
    privilege_type
FROM information_schema.routine_privileges 
WHERE routine_name = 'store_oauth_tokens'; 