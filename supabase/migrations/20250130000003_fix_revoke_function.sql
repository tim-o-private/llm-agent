-- Fix revoke function to handle foreign key constraints properly
-- Delete connection record first, then vault secrets

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

  -- Then: Delete vault secrets (no more FK constraints)
  IF access_secret_id IS NOT NULL THEN
    DELETE FROM vault.secrets WHERE id = access_secret_id;
  END IF;

  IF refresh_secret_id IS NOT NULL THEN
    DELETE FROM vault.secrets WHERE id = refresh_secret_id;
  END IF;

  RETURN json_build_object(
    'success', true,
    'message', format('Successfully revoked tokens for %s', p_service_name)
  );
END;
$$; 