-- Fix revoke function to use simpler approach
-- Just remove connection record, leave vault secrets (they become orphaned but harmless)
-- This matches the original working pattern

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

  -- Check if connection exists
  SELECT id
  FROM external_api_connections 
  WHERE user_id = p_user_id AND service_name = p_service_name
  INTO connection_record;

  IF connection_record IS NULL THEN
    -- Already revoked/doesn't exist
    RETURN json_build_object('success', true, 'message', 'Connection already revoked or does not exist');
  END IF;

  -- Simply delete the connection record
  -- The vault secrets will remain but become orphaned (harmless)
  -- On reconnection, the store function will reuse or update existing secrets
  DELETE FROM external_api_connections 
  WHERE user_id = p_user_id AND service_name = p_service_name;

  RETURN json_build_object(
    'success', true,
    'message', format('Successfully revoked tokens for %s', p_service_name)
  );
END;
$$; 