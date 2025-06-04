-- Fix vault permissions by using proper vault functions instead of direct table access
-- The vault.secrets table requires special permissions that RPC functions don't have by default

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
  access_secret_name TEXT;
  refresh_secret_name TEXT;
  existing_connection RECORD;
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

  -- Check if connection already exists to handle updates
  SELECT access_token_secret_id, refresh_token_secret_id
  FROM external_api_connections 
  WHERE user_id = p_user_id AND service_name = p_service_name
  INTO existing_connection;

  -- Handle access token
  IF existing_connection.access_token_secret_id IS NOT NULL THEN
    -- Update existing secret using vault.update_secret
    SELECT vault.update_secret(
      existing_connection.access_token_secret_id,
      p_access_token
    ) INTO access_secret_id;
  ELSE
    -- Create new secret
    SELECT vault.create_secret(
      p_access_token,
      access_secret_name,
      format('Access token for %s - User %s', p_service_name, p_user_id)
    ) INTO access_secret_id;
  END IF;

  IF access_secret_id IS NULL THEN
    RAISE EXCEPTION 'Failed to create/update access token secret in vault';
  END IF;

  -- Handle refresh token if provided
  IF p_refresh_token IS NOT NULL THEN
    IF existing_connection.refresh_token_secret_id IS NOT NULL THEN
      -- Update existing secret
      SELECT vault.update_secret(
        existing_connection.refresh_token_secret_id,
        p_refresh_token
      ) INTO refresh_secret_id;
    ELSE
      -- Create new secret
      SELECT vault.create_secret(
        p_refresh_token,
        refresh_secret_name,
        format('Refresh token for %s - User %s', p_service_name, p_user_id)
      ) INTO refresh_secret_id;
    END IF;

    IF refresh_secret_id IS NULL THEN
      RAISE EXCEPTION 'Failed to create/update refresh token secret in vault';
    END IF;
  END IF;

  -- Upsert connection record (update if exists, insert if new)
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

-- Also fix the revoke function to use proper vault functions
CREATE OR REPLACE FUNCTION revoke_oauth_tokens(
  p_user_id UUID,
  p_service_name TEXT
) RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  connection_record RECORD;
  access_secret_id UUID;
  refresh_secret_id UUID;
BEGIN
  -- Ensure user can only revoke their own tokens
  IF auth.uid() != p_user_id THEN
    RAISE EXCEPTION 'Access denied: cannot revoke tokens for other users';
  END IF;

  -- Get connection with secret IDs
  SELECT access_token_secret_id, refresh_token_secret_id
  FROM external_api_connections 
  WHERE user_id = p_user_id AND service_name = p_service_name
  INTO connection_record;

  IF connection_record IS NULL THEN
    -- Already revoked/doesn't exist
    RETURN json_build_object('success', true, 'message', 'Connection already revoked or does not exist');
  END IF;

  -- Store secret IDs for deletion after removing FK references
  access_secret_id := connection_record.access_token_secret_id;
  refresh_secret_id := connection_record.refresh_token_secret_id;

  -- First: Delete the connection record (removes FK references)
  DELETE FROM external_api_connections 
  WHERE user_id = p_user_id AND service_name = p_service_name;

  -- Then: Delete vault secrets using proper vault functions
  IF access_secret_id IS NOT NULL THEN
    PERFORM vault.delete_secret(access_secret_id);
  END IF;

  IF refresh_secret_id IS NOT NULL THEN
    PERFORM vault.delete_secret(refresh_secret_id);
  END IF;

  RETURN json_build_object(
    'success', true,
    'message', format('Successfully revoked tokens for %s', p_service_name)
  );
END;
$$; 