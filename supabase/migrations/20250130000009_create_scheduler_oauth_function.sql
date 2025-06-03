-- Create scheduler-specific OAuth token function
-- This function allows the postgres user (scheduler context) to retrieve OAuth tokens
-- without requiring auth.uid() to be set

CREATE OR REPLACE FUNCTION get_oauth_tokens_for_scheduler(
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
    -- Security check: Only allow postgres role (scheduler context)
    IF current_user != 'postgres' THEN
        RAISE EXCEPTION 'Access denied: This function is only for scheduled operations';
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
        RAISE EXCEPTION 'No active OAuth connection found for user % service %', p_user_id, p_service_name;
    END IF;
    
    -- Get decrypted access token
    IF v_connection_record.access_token_secret_id IS NOT NULL THEN
        SELECT decrypted_secret 
        INTO v_access_token
        FROM vault.decrypted_secrets 
        WHERE id = v_connection_record.access_token_secret_id;
        
        IF v_access_token IS NULL THEN
            RAISE EXCEPTION 'Failed to decrypt access token for user % service %', p_user_id, p_service_name;
        END IF;
    ELSE
        RAISE EXCEPTION 'No access token found for user % service %', p_user_id, p_service_name;
    END IF;
    
    -- Get decrypted refresh token (optional)
    IF v_connection_record.refresh_token_secret_id IS NOT NULL THEN
        SELECT decrypted_secret 
        INTO v_refresh_token
        FROM vault.decrypted_secrets 
        WHERE id = v_connection_record.refresh_token_secret_id;
    END IF;
    
    -- Build result JSON (same format as get_oauth_tokens)
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
        RAISE EXCEPTION 'Failed to retrieve OAuth tokens for user % service %: %', 
            p_user_id, p_service_name, SQLERRM;
END;
$$;

-- Grant execute permission to postgres user (scheduler)
GRANT EXECUTE ON FUNCTION get_oauth_tokens_for_scheduler(UUID, TEXT) TO postgres;

-- Add comment for documentation
COMMENT ON FUNCTION get_oauth_tokens_for_scheduler(UUID, TEXT) IS 
'Scheduler-specific function to retrieve OAuth tokens. Only accessible by postgres user for scheduled operations. Returns same format as get_oauth_tokens but bypasses auth.uid() requirement.'; 