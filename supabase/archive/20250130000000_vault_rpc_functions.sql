-- Vault RPC Functions for UI Access
-- Mirrors VaultTokenService methods for direct database access from UI
-- Maintains security through RLS and SECURITY DEFINER functions

-- Function 1: Store OAuth tokens (mirrors VaultTokenService.store_tokens)
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
  INSERT INTO external_api_connections (
    user_id, service_name, access_token_secret_id, refresh_token_secret_id,
    token_expires_at, scopes, service_user_id, service_user_email, 
    is_active, updated_at
  ) VALUES (
    p_user_id, p_service_name, access_secret_id, refresh_secret_id,
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
END;
$$;

-- Function 2: Get connection info (mirrors VaultTokenService.get_connection_info)
CREATE OR REPLACE FUNCTION get_connection_info(
  p_user_id UUID,
  p_service_name TEXT
) RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  connection_record RECORD;
BEGIN
  -- Ensure user can only access their own connections
  IF auth.uid() != p_user_id THEN
    RAISE EXCEPTION 'Access denied: cannot access connections for other users';
  END IF;

  SELECT id, service_name, service_user_id, service_user_email,
         scopes, token_expires_at, is_active, created_at, updated_at
  FROM external_api_connections 
  WHERE user_id = p_user_id AND service_name = p_service_name
  INTO connection_record;

  IF connection_record IS NULL THEN
    RETURN json_build_object('found', false);
  END IF;

  RETURN json_build_object(
    'found', true,
    'id', connection_record.id,
    'service_name', connection_record.service_name,
    'service_user_id', connection_record.service_user_id,
    'service_user_email', connection_record.service_user_email,
    'scopes', connection_record.scopes,
    'token_expires_at', connection_record.token_expires_at,
    'is_active', connection_record.is_active,
    'created_at', connection_record.created_at,
    'updated_at', connection_record.updated_at
  );
END;
$$;

-- Function 3: List user connections (mirrors VaultTokenService.list_user_connections)
CREATE OR REPLACE FUNCTION list_user_connections(
  p_user_id UUID
) RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  connections_array JSON;
BEGIN
  -- Ensure user can only access their own connections
  IF auth.uid() != p_user_id THEN
    RAISE EXCEPTION 'Access denied: cannot access connections for other users';
  END IF;

  SELECT json_agg(
    json_build_object(
      'id', id,
      'service_name', service_name,
      'service_user_id', service_user_id,
      'service_user_email', service_user_email,
      'scopes', scopes,
      'token_expires_at', token_expires_at,
      'is_active', is_active,
      'created_at', created_at,
      'updated_at', updated_at
    )
  )
  FROM external_api_connections 
  WHERE user_id = p_user_id AND is_active = true
  INTO connections_array;

  RETURN json_build_object(
    'connections', COALESCE(connections_array, '[]'::json)
  );
END;
$$;

-- Function 4: Revoke tokens (mirrors VaultTokenService.revoke_tokens)
CREATE OR REPLACE FUNCTION revoke_oauth_tokens(
  p_user_id UUID,
  p_service_name TEXT
) RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  connection_record RECORD;
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

  -- Delete vault secrets
  IF connection_record.access_token_secret_id IS NOT NULL THEN
    DELETE FROM vault.secrets WHERE id = connection_record.access_token_secret_id;
  END IF;

  IF connection_record.refresh_token_secret_id IS NOT NULL THEN
    DELETE FROM vault.secrets WHERE id = connection_record.refresh_token_secret_id;
  END IF;

  -- Delete the connection record
  DELETE FROM external_api_connections 
  WHERE user_id = p_user_id AND service_name = p_service_name;

  RETURN json_build_object(
    'success', true,
    'message', format('Successfully revoked tokens for %s', p_service_name)
  );
END;
$$;

-- Function 5: Check connection status (convenience function for UI)
CREATE OR REPLACE FUNCTION check_connection_status(
  p_user_id UUID,
  p_service_name TEXT
) RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  connection_count INTEGER;
BEGIN
  -- Ensure user can only check their own connections
  IF auth.uid() != p_user_id THEN
    RAISE EXCEPTION 'Access denied: cannot check connections for other users';
  END IF;

  SELECT COUNT(*)
  FROM external_api_connections
  WHERE user_id = p_user_id AND service_name = p_service_name AND is_active = true
  INTO connection_count;

  RETURN json_build_object(
    'connected', connection_count > 0,
    'service', p_service_name
  );
END;
$$;

-- Grant execute permissions to authenticated users
GRANT EXECUTE ON FUNCTION store_oauth_tokens(UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, TEXT[], TEXT, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION get_connection_info(UUID, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION list_user_connections(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION revoke_oauth_tokens(UUID, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION check_connection_status(UUID, TEXT) TO authenticated;

-- Add comments for documentation
COMMENT ON FUNCTION store_oauth_tokens IS 'Store OAuth tokens in Vault with connection record - mirrors VaultTokenService.store_tokens';
COMMENT ON FUNCTION get_connection_info IS 'Get connection information without tokens - mirrors VaultTokenService.get_connection_info';
COMMENT ON FUNCTION list_user_connections IS 'List all active connections for a user - mirrors VaultTokenService.list_user_connections';
COMMENT ON FUNCTION revoke_oauth_tokens IS 'Revoke and delete OAuth tokens - mirrors VaultTokenService.revoke_tokens';
COMMENT ON FUNCTION check_connection_status IS 'Check if user has active connection for service - convenience function for UI'; 