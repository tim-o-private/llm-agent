-- Create get_oauth_tokens RPC function
-- This function allows authenticated users to retrieve their own OAuth tokens
-- while maintaining proper security isolation

CREATE OR REPLACE FUNCTION get_oauth_tokens(
    p_user_id UUID,
    p_service_name TEXT
)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_connection_record RECORD;
    v_access_token TEXT;
    v_refresh_token TEXT;
    v_result JSON;
BEGIN
    -- Security check: ensure user can only access their own tokens
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'Authentication required';
    END IF;
    
    IF auth.uid() != p_user_id THEN
        RAISE EXCEPTION 'Access denied: cannot access tokens for other users';
    END IF;
    
    -- Get connection record with secret IDs
    SELECT 
        access_token_secret_id,
        refresh_token_secret_id,
        service_user_id,
        service_user_email,
        scopes,
        token_expires_at,
        is_active
    INTO v_connection_record
    FROM external_api_connections
    WHERE user_id = p_user_id 
    AND service_name = p_service_name
    AND is_active = true;
    
    -- Check if connection exists
    IF NOT FOUND THEN
        RAISE EXCEPTION 'No active OAuth connection found for service: %', p_service_name;
    END IF;
    
    -- Get decrypted access token
    IF v_connection_record.access_token_secret_id IS NOT NULL THEN
        SELECT decrypted_secret 
        INTO v_access_token
        FROM vault.decrypted_secrets 
        WHERE id = v_connection_record.access_token_secret_id;
        
        IF v_access_token IS NULL THEN
            RAISE EXCEPTION 'Failed to decrypt access token for service: %', p_service_name;
        END IF;
    ELSE
        RAISE EXCEPTION 'No access token found for service: %', p_service_name;
    END IF;
    
    -- Get decrypted refresh token (optional)
    IF v_connection_record.refresh_token_secret_id IS NOT NULL THEN
        SELECT decrypted_secret 
        INTO v_refresh_token
        FROM vault.decrypted_secrets 
        WHERE id = v_connection_record.refresh_token_secret_id;
    END IF;
    
    -- Build result JSON
    v_result := json_build_object(
        'access_token', v_access_token,
        'refresh_token', v_refresh_token,
        'service_user_id', v_connection_record.service_user_id,
        'service_user_email', v_connection_record.service_user_email,
        'scopes', v_connection_record.scopes,
        'expires_at', v_connection_record.token_expires_at,
        'is_active', v_connection_record.is_active
    );
    
    RETURN v_result;
    
EXCEPTION
    WHEN OTHERS THEN
        -- Log error details for debugging
        RAISE EXCEPTION 'Failed to retrieve OAuth tokens for user % service %: %', 
            p_user_id, p_service_name, SQLERRM;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION get_oauth_tokens(UUID, TEXT) TO authenticated;

-- Add comment for documentation
COMMENT ON FUNCTION get_oauth_tokens(UUID, TEXT) IS 
'Retrieve OAuth tokens for a specific service connection. Users can only access their own tokens.'; 