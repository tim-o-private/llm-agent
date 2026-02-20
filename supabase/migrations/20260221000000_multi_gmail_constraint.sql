-- SPEC-008: Multi-Gmail Account Support
-- Allows users to connect up to 5 Gmail accounts per user.
-- Changes the unique constraint, adds max-5 trigger, creates oauth_states table,
-- and updates all RPCs to support multi-account operations.

-- ============================================
-- 1. Backfill service_user_id from service_user_email for existing gmail rows
-- ============================================
UPDATE external_api_connections
SET service_user_id = service_user_email
WHERE service_name = 'gmail'
  AND service_user_id IS NULL
  AND service_user_email IS NOT NULL;

-- ============================================
-- 2. Drop old unique constraint, add new composite unique
-- ============================================
ALTER TABLE external_api_connections
  DROP CONSTRAINT external_api_connections_user_id_service_name_key;

ALTER TABLE external_api_connections
  ADD CONSTRAINT external_api_connections_user_service_account_key
  UNIQUE (user_id, service_name, service_user_id);

-- Gmail rows must have service_user_id (other services may not yet)
ALTER TABLE external_api_connections
  ADD CONSTRAINT chk_gmail_requires_service_user_id
  CHECK (service_name != 'gmail' OR service_user_id IS NOT NULL);

-- ============================================
-- 3. Max-5 Gmail connections trigger
-- ============================================
CREATE OR REPLACE FUNCTION check_max_gmail_connections()
RETURNS TRIGGER AS $$
DECLARE
  gmail_count INTEGER;
BEGIN
  IF NEW.service_name = 'gmail' AND NEW.is_active = true THEN
    SELECT COUNT(*) INTO gmail_count
    FROM external_api_connections
    WHERE user_id = NEW.user_id
      AND service_name = 'gmail'
      AND is_active = true
      AND id != COALESCE(NEW.id, '00000000-0000-0000-0000-000000000000'::uuid);

    IF gmail_count >= 5 THEN
      RAISE EXCEPTION 'Maximum of 5 Gmail accounts per user reached';
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_max_gmail_connections
  BEFORE INSERT OR UPDATE ON external_api_connections
  FOR EACH ROW EXECUTE FUNCTION check_max_gmail_connections();

COMMENT ON FUNCTION check_max_gmail_connections() IS 'Enforces maximum of 5 active Gmail connections per user';

-- ============================================
-- 4. OAuth states table (for standalone OAuth flow CSRF protection)
-- ============================================
CREATE TABLE IF NOT EXISTS oauth_states (
    nonce TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '10 minutes') NOT NULL
);

-- RLS enabled but no user policies — service role bypasses RLS,
-- effectively restricting access to backend only
ALTER TABLE oauth_states ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE oauth_states IS 'Temporary storage for OAuth state nonces used in standalone Google OAuth flow (CSRF protection). Service-role only access.';

-- Index for cleanup of expired nonces
CREATE INDEX idx_oauth_states_expires_at ON oauth_states(expires_at);

-- ============================================
-- 5. Update check_connection_status — return count
-- ============================================
CREATE OR REPLACE FUNCTION public.check_connection_status(p_user_id uuid, p_service_name text)
RETURNS json
LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
  connection_count INTEGER;
BEGIN
  IF auth.uid() != p_user_id THEN
    RAISE EXCEPTION 'Access denied: cannot check connections for other users';
  END IF;

  SELECT COUNT(*)
  FROM external_api_connections
  WHERE user_id = p_user_id AND service_name = p_service_name AND is_active = true
  INTO connection_count;

  RETURN json_build_object(
    'connected', connection_count > 0,
    'count', connection_count,
    'service', p_service_name
  );
END;
$$;

COMMENT ON FUNCTION public.check_connection_status(uuid, text) IS 'Check if user has active connection(s) for service — returns count for multi-account support';

-- ============================================
-- 6. Update store_oauth_tokens — new conflict target + service_user_id in secret names
-- ============================================
CREATE OR REPLACE FUNCTION public.store_oauth_tokens(
  p_user_id uuid,
  p_service_name text,
  p_access_token text,
  p_refresh_token text DEFAULT NULL,
  p_expires_at timestamptz DEFAULT NULL,
  p_scopes text[] DEFAULT '{}',
  p_service_user_id text DEFAULT NULL,
  p_service_user_email text DEFAULT NULL
)
RETURNS json
LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
  access_secret_id UUID;
  refresh_secret_id UUID;
  connection_result RECORD;
  access_secret_name TEXT;
  refresh_secret_name TEXT;
  v_service_user_id TEXT;
BEGIN
  -- Ensure user can only store their own tokens
  IF auth.uid() != p_user_id THEN
    RAISE EXCEPTION 'Access denied: cannot store tokens for other users';
  END IF;

  -- Validate service name
  IF p_service_name NOT IN ('gmail', 'google_calendar', 'slack') THEN
    RAISE EXCEPTION 'Invalid service name: %', p_service_name;
  END IF;

  -- Gmail requires service_user_id
  v_service_user_id := COALESCE(p_service_user_id, p_service_user_email);
  IF p_service_name = 'gmail' AND v_service_user_id IS NULL THEN
    RAISE EXCEPTION 'service_user_id or service_user_email is required for Gmail connections';
  END IF;

  -- Include service_user_id in secret names to avoid collisions between accounts
  access_secret_name := format('%s_%s_%s_access', p_user_id, p_service_name, COALESCE(v_service_user_id, 'default'));
  refresh_secret_name := format('%s_%s_%s_refresh', p_user_id, p_service_name, COALESCE(v_service_user_id, 'default'));

  -- Store access token (upsert)
  SELECT public.store_secret(
    p_access_token,
    access_secret_name,
    format('Access token for %s - User %s - Account %s', p_service_name, p_user_id, COALESCE(v_service_user_id, 'default'))
  ) INTO access_secret_id;

  IF access_secret_id IS NULL THEN
    RAISE EXCEPTION 'Failed to store access token secret in vault';
  END IF;

  -- Store refresh token if provided (upsert)
  IF p_refresh_token IS NOT NULL THEN
    SELECT public.store_secret(
      p_refresh_token,
      refresh_secret_name,
      format('Refresh token for %s - User %s - Account %s', p_service_name, p_user_id, COALESCE(v_service_user_id, 'default'))
    ) INTO refresh_secret_id;

    IF refresh_secret_id IS NULL THEN
      RAISE EXCEPTION 'Failed to store refresh token secret in vault';
    END IF;
  END IF;

  -- Upsert connection record with new composite conflict target
  INSERT INTO external_api_connections (
    user_id, service_name, access_token_secret_id, refresh_token_secret_id,
    token_expires_at, scopes, service_user_id, service_user_email,
    is_active, updated_at
  ) VALUES (
    p_user_id, p_service_name, access_secret_id, refresh_secret_id,
    p_expires_at, p_scopes, v_service_user_id, p_service_user_email,
    true, NOW()
  )
  ON CONFLICT (user_id, service_name, service_user_id)
  DO UPDATE SET
    access_token_secret_id = EXCLUDED.access_token_secret_id,
    refresh_token_secret_id = COALESCE(EXCLUDED.refresh_token_secret_id, external_api_connections.refresh_token_secret_id),
    token_expires_at = EXCLUDED.token_expires_at,
    scopes = EXCLUDED.scopes,
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
$$;

-- ============================================
-- 7. Update get_oauth_tokens — support connection_id, return array when no connection_id
-- ============================================
CREATE OR REPLACE FUNCTION public.get_oauth_tokens(
  p_user_id uuid,
  p_service_name text,
  p_connection_id uuid DEFAULT NULL
)
RETURNS json
LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
  v_connection_record RECORD;
  v_access_token TEXT;
  v_refresh_token TEXT;
  v_result JSON;
  v_results JSON[];
BEGIN
  IF auth.uid() IS NULL THEN
    RAISE EXCEPTION 'Authentication required';
  END IF;
  IF auth.uid() != p_user_id THEN
    RAISE EXCEPTION 'Access denied: cannot access tokens for other users';
  END IF;

  -- Single connection mode
  IF p_connection_id IS NOT NULL THEN
    SELECT access_token_secret_id, refresh_token_secret_id,
           service_user_id, service_user_email, scopes, token_expires_at, is_active, id
    INTO v_connection_record
    FROM external_api_connections
    WHERE id = p_connection_id AND user_id = p_user_id AND is_active = true;

    IF NOT FOUND THEN
      RAISE EXCEPTION 'No active OAuth connection found with id: %', p_connection_id;
    END IF;

    -- Decrypt tokens
    IF v_connection_record.access_token_secret_id IS NOT NULL THEN
      SELECT decrypted_secret INTO v_access_token
      FROM vault.decrypted_secrets WHERE id = v_connection_record.access_token_secret_id;
    END IF;
    IF v_connection_record.refresh_token_secret_id IS NOT NULL THEN
      SELECT decrypted_secret INTO v_refresh_token
      FROM vault.decrypted_secrets WHERE id = v_connection_record.refresh_token_secret_id;
    END IF;

    RETURN json_build_object(
      'connection_id', v_connection_record.id,
      'access_token', v_access_token,
      'refresh_token', v_refresh_token,
      'service_user_id', v_connection_record.service_user_id,
      'service_user_email', v_connection_record.service_user_email,
      'scopes', v_connection_record.scopes,
      'expires_at', v_connection_record.token_expires_at,
      'is_active', v_connection_record.is_active
    );
  END IF;

  -- Multi-connection mode: return array of all active connections
  v_results := ARRAY[]::JSON[];
  FOR v_connection_record IN
    SELECT access_token_secret_id, refresh_token_secret_id,
           service_user_id, service_user_email, scopes, token_expires_at, is_active, id
    FROM external_api_connections
    WHERE user_id = p_user_id AND service_name = p_service_name AND is_active = true
    ORDER BY created_at
  LOOP
    v_access_token := NULL;
    v_refresh_token := NULL;

    IF v_connection_record.access_token_secret_id IS NOT NULL THEN
      SELECT decrypted_secret INTO v_access_token
      FROM vault.decrypted_secrets WHERE id = v_connection_record.access_token_secret_id;
    END IF;
    IF v_connection_record.refresh_token_secret_id IS NOT NULL THEN
      SELECT decrypted_secret INTO v_refresh_token
      FROM vault.decrypted_secrets WHERE id = v_connection_record.refresh_token_secret_id;
    END IF;

    v_results := v_results || json_build_object(
      'connection_id', v_connection_record.id,
      'access_token', v_access_token,
      'refresh_token', v_refresh_token,
      'service_user_id', v_connection_record.service_user_id,
      'service_user_email', v_connection_record.service_user_email,
      'scopes', v_connection_record.scopes,
      'expires_at', v_connection_record.token_expires_at,
      'is_active', v_connection_record.is_active
    );
  END LOOP;

  RETURN array_to_json(v_results);

EXCEPTION
  WHEN OTHERS THEN
    RAISE EXCEPTION 'Failed to retrieve OAuth tokens for user % service %: %',
      p_user_id, p_service_name, SQLERRM;
END;
$$;

COMMENT ON FUNCTION public.get_oauth_tokens(uuid, text, uuid) IS 'Retrieve OAuth tokens. With p_connection_id returns single connection; without returns array of all active connections for the service.';

-- ============================================
-- 8. Update get_oauth_tokens_for_scheduler — same multi-account support
-- ============================================
CREATE OR REPLACE FUNCTION public.get_oauth_tokens_for_scheduler(
  p_user_id uuid,
  p_service_name text,
  p_connection_id uuid DEFAULT NULL
)
RETURNS json
LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
  v_connection_record RECORD;
  v_access_token TEXT;
  v_refresh_token TEXT;
  v_results JSON[];
BEGIN
  IF current_user != 'postgres' THEN
    RAISE EXCEPTION 'Access denied: This function is only for scheduled operations';
  END IF;

  -- Single connection mode
  IF p_connection_id IS NOT NULL THEN
    SELECT access_token_secret_id, refresh_token_secret_id,
           service_user_id, service_user_email, scopes, token_expires_at, is_active, id
    INTO v_connection_record
    FROM external_api_connections
    WHERE id = p_connection_id AND user_id = p_user_id AND is_active = true;

    IF NOT FOUND THEN
      RAISE EXCEPTION 'No active OAuth connection found with id: %', p_connection_id;
    END IF;

    IF v_connection_record.access_token_secret_id IS NOT NULL THEN
      SELECT decrypted_secret INTO v_access_token
      FROM vault.decrypted_secrets WHERE id = v_connection_record.access_token_secret_id;
    END IF;
    IF v_connection_record.refresh_token_secret_id IS NOT NULL THEN
      SELECT decrypted_secret INTO v_refresh_token
      FROM vault.decrypted_secrets WHERE id = v_connection_record.refresh_token_secret_id;
    END IF;

    RETURN json_build_object(
      'connection_id', v_connection_record.id,
      'access_token', v_access_token,
      'refresh_token', v_refresh_token,
      'service_user_id', v_connection_record.service_user_id,
      'service_user_email', v_connection_record.service_user_email,
      'scopes', v_connection_record.scopes,
      'expires_at', v_connection_record.token_expires_at,
      'is_active', v_connection_record.is_active
    );
  END IF;

  -- Multi-connection mode
  v_results := ARRAY[]::JSON[];
  FOR v_connection_record IN
    SELECT access_token_secret_id, refresh_token_secret_id,
           service_user_id, service_user_email, scopes, token_expires_at, is_active, id
    FROM external_api_connections
    WHERE user_id = p_user_id AND service_name = p_service_name AND is_active = true
    ORDER BY created_at
  LOOP
    v_access_token := NULL;
    v_refresh_token := NULL;

    IF v_connection_record.access_token_secret_id IS NOT NULL THEN
      SELECT decrypted_secret INTO v_access_token
      FROM vault.decrypted_secrets WHERE id = v_connection_record.access_token_secret_id;
    END IF;
    IF v_connection_record.refresh_token_secret_id IS NOT NULL THEN
      SELECT decrypted_secret INTO v_refresh_token
      FROM vault.decrypted_secrets WHERE id = v_connection_record.refresh_token_secret_id;
    END IF;

    v_results := v_results || json_build_object(
      'connection_id', v_connection_record.id,
      'access_token', v_access_token,
      'refresh_token', v_refresh_token,
      'service_user_id', v_connection_record.service_user_id,
      'service_user_email', v_connection_record.service_user_email,
      'scopes', v_connection_record.scopes,
      'expires_at', v_connection_record.token_expires_at,
      'is_active', v_connection_record.is_active
    );
  END LOOP;

  RETURN array_to_json(v_results);

EXCEPTION
  WHEN OTHERS THEN
    RAISE EXCEPTION 'Failed to retrieve OAuth tokens for user % service %: %',
      p_user_id, p_service_name, SQLERRM;
END;
$$;

COMMENT ON FUNCTION public.get_oauth_tokens_for_scheduler(uuid, text, uuid) IS 'Scheduler-specific token retrieval. With p_connection_id returns single; without returns array of all active connections.';

-- ============================================
-- 9. Update revoke_oauth_tokens — support targeted revocation by connection_id
-- ============================================
CREATE OR REPLACE FUNCTION public.revoke_oauth_tokens(
  p_user_id uuid,
  p_service_name text,
  p_connection_id uuid DEFAULT NULL
)
RETURNS json
LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
  v_deleted_count INTEGER;
BEGIN
  IF auth.uid() != p_user_id THEN
    RAISE EXCEPTION 'Access denied: cannot revoke tokens for other users';
  END IF;

  IF p_connection_id IS NOT NULL THEN
    -- Targeted: revoke specific connection
    DELETE FROM external_api_connections
    WHERE id = p_connection_id AND user_id = p_user_id;
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;

    IF v_deleted_count = 0 THEN
      RETURN json_build_object('success', true, 'message', 'Connection not found or already revoked');
    END IF;

    RETURN json_build_object(
      'success', true,
      'message', format('Successfully revoked connection %s', p_connection_id)
    );
  ELSE
    -- Bulk: revoke all connections for this service (backward-compatible)
    DELETE FROM external_api_connections
    WHERE user_id = p_user_id AND service_name = p_service_name;
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;

    RETURN json_build_object(
      'success', true,
      'message', format('Successfully revoked %s connection(s) for %s', v_deleted_count, p_service_name)
    );
  END IF;
END;
$$;

COMMENT ON FUNCTION public.revoke_oauth_tokens(uuid, text, uuid) IS 'Revoke OAuth tokens. With p_connection_id revokes specific connection; without revokes all for the service.';
