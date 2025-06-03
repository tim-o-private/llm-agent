-- Fix store_oauth_tokens RPC function to match current table schema
-- The function was trying to insert into access_token column which was removed

CREATE OR REPLACE FUNCTION public.store_oauth_tokens(
  p_user_id UUID,
  p_service_name TEXT,
  p_access_token TEXT,
  p_refresh_token TEXT DEFAULT NULL,
  p_expires_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
  p_scopes TEXT[] DEFAULT '{}',
  p_service_user_id TEXT DEFAULT NULL,
  p_service_user_email TEXT DEFAULT NULL
) RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $function$
DECLARE
  access_secret_id UUID;
  refresh_secret_id UUID;
  connection_result RECORD;
  access_secret_name TEXT;
  refresh_secret_name TEXT;
BEGIN
  -- Ensure user can only store their own tokens
  IF auth.uid() != p_user_id THEN
    RAISE EXCEPTION 'Access denied: cannot store tokens for other users';
  END IF;

  -- Validate service name
  IF p_service_name NOT IN ('gmail', 'google_calendar', 'slack') THEN
    RAISE EXCEPTION 'Invalid service name: %', p_service_name;
  END IF;

  -- Generate secret names
  access_secret_name := format('%s_%s_access', p_user_id, p_service_name);
  refresh_secret_name := format('%s_%s_refresh', p_user_id, p_service_name);

  -- Store access token (upsert)
  SELECT public.store_secret(
    p_access_token,
    access_secret_name,
    format('Access token for %s - User %s', p_service_name, p_user_id)
  ) INTO access_secret_id;

  IF access_secret_id IS NULL THEN
    RAISE EXCEPTION 'Failed to store access token secret in vault';
  END IF;

  -- Store refresh token if provided (upsert)
  IF p_refresh_token IS NOT NULL THEN
    SELECT public.store_secret(
      p_refresh_token,
      refresh_secret_name,
      format('Refresh token for %s - User %s', p_service_name, p_user_id)
    ) INTO refresh_secret_id;

    IF refresh_secret_id IS NULL THEN
      RAISE EXCEPTION 'Failed to store refresh token secret in vault';
    END IF;
  END IF;

  -- Upsert connection record (FIXED: removed access_token column)
  INSERT INTO external_api_connections (
    user_id, service_name, access_token_secret_id, refresh_token_secret_id,
    token_expires_at, scopes, service_user_id, service_user_email, 
    is_active, updated_at
  ) VALUES (
    p_user_id, p_service_name, access_secret_id, refresh_token_secret_id,
    p_expires_at, p_scopes, p_service_user_id, p_service_user_email,
    true, NOW()
  )
  ON CONFLICT (user_id, service_name) 
  DO UPDATE SET
    access_token_secret_id = EXCLUDED.access_token_secret_id,
    refresh_token_secret_id = EXCLUDED.refresh_token_secret_id,
    token_expires_at = EXCLUDED.token_expires_at,
    scopes = EXCLUDED.scopes,
    service_user_id = EXCLUDED.service_user_id,
    service_user_email = EXCLUDED.service_user_email,
    is_active = EXCLUDED.is_active,
    updated_at = EXCLUDED.updated_at
  RETURNING * INTO connection_result;

  IF connection_result IS NULL THEN
    RAISE EXCEPTION 'Failed to store connection record';
  END IF;

  RETURN json_build_object(
    'success', true,
    'service_name', p_service_name,
    'user_id', p_user_id,
    'connection_id', connection_result.id
  );
EXCEPTION
  WHEN OTHERS THEN
    RAISE LOG 'Error in store_oauth_tokens: % %', SQLERRM, SQLSTATE;
    RETURN json_build_object('success', false, 'error', SQLERRM);
END;
$function$;

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION public.store_oauth_tokens TO authenticated;
GRANT EXECUTE ON FUNCTION public.store_oauth_tokens TO anon; 