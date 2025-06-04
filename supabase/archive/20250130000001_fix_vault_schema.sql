-- Fix schema mismatch for vault token storage
-- Make access_token nullable since we're using vault secret references

-- Step 1: Make access_token nullable (it was NOT NULL before)
ALTER TABLE public.external_api_connections 
ALTER COLUMN access_token DROP NOT NULL;

-- Step 2: Update the check constraint to work with vault pattern
ALTER TABLE public.external_api_connections 
DROP CONSTRAINT IF EXISTS check_token_storage;

ALTER TABLE public.external_api_connections 
ADD CONSTRAINT check_token_storage 
CHECK (
    (access_token IS NOT NULL) OR 
    (access_token_secret_id IS NOT NULL)
);

-- Step 3: Update the RPC function to handle the schema correctly
CREATE OR REPLACE FUNCTION store_oauth_tokens(
  p_user_id UUID,
  p_service_name TEXT,
  p_access_token TEXT,
  p_refresh_token TEXT DEFAULT NULL,
  p_expires_at TIMESTAMPTZ DEFAULT NULL,
  p_scopes TEXT[] DEFAULT '{}',
  p_service_user_id TEXT DEFAULT NULL,
  p_service_user_email TEXT DEFAULT NULL
) RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  access_secret_id UUID;
  refresh_secret_id UUID;
  connection_result RECORD;
BEGIN
  -- Ensure user can only store their own tokens
  IF auth.uid() != p_user_id THEN
    RAISE EXCEPTION 'Access denied: cannot store tokens for other users';
  END IF;

  -- Validate service name
  IF p_service_name NOT IN ('gmail', 'google_calendar', 'slack') THEN
    RAISE EXCEPTION 'Invalid service name: %', p_service_name;
  END IF;

  -- Store access token in vault
  SELECT vault.create_secret(
    p_access_token,
    format('%s_%s_access', p_user_id, p_service_name),
    format('Access token for %s - User %s', p_service_name, p_user_id)
  ) INTO access_secret_id;

  IF access_secret_id IS NULL THEN
    RAISE EXCEPTION 'Failed to create access token secret in vault';
  END IF;

  -- Store refresh token if provided
  IF p_refresh_token IS NOT NULL THEN
    SELECT vault.create_secret(
      p_refresh_token,
      format('%s_%s_refresh', p_user_id, p_service_name),
      format('Refresh token for %s - User %s', p_service_name, p_user_id)
    ) INTO refresh_secret_id;

    IF refresh_secret_id IS NULL THEN
      RAISE EXCEPTION 'Failed to create refresh token secret in vault';
    END IF;
  END IF;

  -- Upsert connection record (update if exists, insert if new)
  -- Note: access_token is now NULL since we're using vault storage
  INSERT INTO external_api_connections (
    user_id, service_name, access_token, access_token_secret_id, refresh_token_secret_id,
    token_expires_at, scopes, service_user_id, service_user_email, 
    is_active, updated_at
  ) VALUES (
    p_user_id, p_service_name, NULL, access_secret_id, refresh_secret_id,
    p_expires_at, p_scopes, p_service_user_id, p_service_user_email,
    true, NOW()
  )
  ON CONFLICT (user_id, service_name) 
  DO UPDATE SET
    access_token = NULL,
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
END;
$$;

-- Step 4: Update table comments
COMMENT ON COLUMN public.external_api_connections.access_token IS 'OAuth access token (deprecated - use access_token_secret_id for vault storage)'; 