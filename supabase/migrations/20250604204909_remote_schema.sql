

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgjwt" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE TYPE "public"."agent_tool_type" AS ENUM (
    'FileManagementToolkit',
    'CRUDTool',
    'GmailTool',
    'EmailDigestTool'
);


ALTER TYPE "public"."agent_tool_type" OWNER TO "postgres";


CREATE TYPE "public"."task_status" AS ENUM (
    'pending',
    'planning',
    'in_progress',
    'completed',
    'skipped',
    'deferred'
);


ALTER TYPE "public"."task_status" OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."check_connection_status"("p_user_id" "uuid", "p_service_name" "text") RETURNS "json"
    LANGUAGE "plpgsql" SECURITY DEFINER
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


ALTER FUNCTION "public"."check_connection_status"("p_user_id" "uuid", "p_service_name" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."check_connection_status"("p_user_id" "uuid", "p_service_name" "text") IS 'Check if user has active connection for service - convenience function for UI';



CREATE OR REPLACE FUNCTION "public"."get_connection_info"("p_user_id" "uuid", "p_service_name" "text") RETURNS "json"
    LANGUAGE "plpgsql" SECURITY DEFINER
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


ALTER FUNCTION "public"."get_connection_info"("p_user_id" "uuid", "p_service_name" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_connection_info"("p_user_id" "uuid", "p_service_name" "text") IS 'Get connection information without tokens - mirrors VaultTokenService.get_connection_info';



CREATE OR REPLACE FUNCTION "public"."get_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text") RETURNS "json"
    LANGUAGE "plpgsql" SECURITY DEFINER
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


ALTER FUNCTION "public"."get_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text") IS 'Retrieve OAuth tokens for a specific service connection. Users can only access their own tokens.';



CREATE OR REPLACE FUNCTION "public"."get_oauth_tokens_for_scheduler"("p_user_id" "uuid", "p_service_name" "text") RETURNS "json"
    LANGUAGE "plpgsql" SECURITY DEFINER
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


ALTER FUNCTION "public"."get_oauth_tokens_for_scheduler"("p_user_id" "uuid", "p_service_name" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_oauth_tokens_for_scheduler"("p_user_id" "uuid", "p_service_name" "text") IS 'Scheduler-specific function to retrieve OAuth tokens. Only accessible by postgres user for scheduled operations. Returns same format as get_oauth_tokens but bypasses auth.uid() requirement.';



CREATE OR REPLACE FUNCTION "public"."is_record_owner"("record_user_id" "uuid") RETURNS boolean
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
BEGIN
  RETURN record_user_id = auth.uid();
END;
$$;


ALTER FUNCTION "public"."is_record_owner"("record_user_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."list_user_connections"("p_user_id" "uuid") RETURNS "json"
    LANGUAGE "plpgsql" SECURITY DEFINER
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


ALTER FUNCTION "public"."list_user_connections"("p_user_id" "uuid") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."list_user_connections"("p_user_id" "uuid") IS 'List all active connections for a user - mirrors VaultTokenService.list_user_connections';



CREATE OR REPLACE FUNCTION "public"."revoke_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text") RETURNS "json"
    LANGUAGE "plpgsql" SECURITY DEFINER
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


ALTER FUNCTION "public"."revoke_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."revoke_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text") IS 'Revoke and delete OAuth tokens - mirrors VaultTokenService.revoke_tokens';



CREATE OR REPLACE FUNCTION "public"."store_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text", "p_access_token" "text", "p_refresh_token" "text" DEFAULT NULL::"text", "p_expires_at" timestamp with time zone DEFAULT NULL::timestamp with time zone, "p_scopes" "text"[] DEFAULT '{}'::"text"[], "p_service_user_id" "text" DEFAULT NULL::"text", "p_service_user_email" "text" DEFAULT NULL::"text") RETURNS "json"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
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

  -- Upsert connection record (CORRECTED: only vault secret columns)
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
EXCEPTION
  WHEN OTHERS THEN
    RAISE LOG 'Error in store_oauth_tokens: % %', SQLERRM, SQLSTATE;
    RETURN json_build_object('success', false, 'error', SQLERRM);
END;
$$;


ALTER FUNCTION "public"."store_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text", "p_access_token" "text", "p_refresh_token" "text", "p_expires_at" timestamp with time zone, "p_scopes" "text"[], "p_service_user_id" "text", "p_service_user_email" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."store_secret"("p_secret" "text", "p_name" "text", "p_description" "text" DEFAULT ''::"text") RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
  existing_secret_id UUID;
  result_secret_id UUID;
BEGIN
  -- Check if a secret with this name already exists
  SELECT id INTO existing_secret_id FROM vault.secrets WHERE name = p_name;
  
  IF existing_secret_id IS NOT NULL THEN
    -- Update existing secret
    PERFORM vault.update_secret(existing_secret_id, p_secret, p_name, p_description);
    result_secret_id := existing_secret_id;
  ELSE
    -- Create new secret
    SELECT vault.create_secret(p_secret, p_name, p_description) INTO result_secret_id;
  END IF;
  
  RETURN result_secret_id;
END;
$$;


ALTER FUNCTION "public"."store_secret"("p_secret" "text", "p_name" "text", "p_description" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_agent_schedules_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_agent_schedules_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_updated_at_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_updated_at_column"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."agent_configurations" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "agent_name" "text" NOT NULL,
    "llm_config" "jsonb" NOT NULL,
    "system_prompt" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."agent_configurations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."agent_logs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "agent_name" character varying(100) NOT NULL,
    "action" character varying(100) NOT NULL,
    "result" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."agent_logs" OWNER TO "postgres";


COMMENT ON TABLE "public"."agent_logs" IS 'General logging table for agent activities';



COMMENT ON COLUMN "public"."agent_logs"."result" IS 'JSON result data from agent execution';



CREATE TABLE IF NOT EXISTS "public"."agent_long_term_memory" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "agent_name" "text" NOT NULL,
    "notes" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."agent_long_term_memory" OWNER TO "postgres";


COMMENT ON TABLE "public"."agent_long_term_memory" IS 'Stores evolving, natural language long-term memory notes curated by agents for specific users.';



COMMENT ON COLUMN "public"."agent_long_term_memory"."agent_name" IS 'Identifier for the agent configuration (e.g., "test_agent") to which these notes pertain.';



COMMENT ON COLUMN "public"."agent_long_term_memory"."notes" IS 'The curated long-term memory notes in natural language or structured text.';



CREATE TABLE IF NOT EXISTS "public"."agent_schedules" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "agent_name" "text" NOT NULL,
    "schedule_cron" "text" NOT NULL,
    "prompt" "text" NOT NULL,
    "active" boolean DEFAULT true,
    "config" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."agent_schedules" OWNER TO "postgres";


COMMENT ON TABLE "public"."agent_schedules" IS 'Stores configuration for scheduled agent execution, including email digest schedules';



COMMENT ON COLUMN "public"."agent_schedules"."schedule_cron" IS 'Cron expression for schedule timing (e.g., "30 7 * * *" for daily at 7:30 AM)';



COMMENT ON COLUMN "public"."agent_schedules"."config" IS 'JSON configuration for the scheduled execution (e.g., hours_back, include_read)';



CREATE TABLE IF NOT EXISTS "public"."agent_sessions" (
    "session_id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "agent_name" "text" NOT NULL,
    "summary" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "agent_id" "text" DEFAULT ''::"text" NOT NULL
);


ALTER TABLE "public"."agent_sessions" OWNER TO "postgres";


COMMENT ON TABLE "public"."agent_sessions" IS 'Stores metadata for agent interaction sessions.';



COMMENT ON COLUMN "public"."agent_sessions"."summary" IS 'Optional summary of the session (less critical in V2 with LTM notes).';



COMMENT ON COLUMN "public"."agent_sessions"."agent_id" IS 'Identifier for the agent configuration used in this session (e.g., "test_agent").';



CREATE TABLE IF NOT EXISTS "public"."agent_tools" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "agent_id" "uuid" NOT NULL,
    "tool_id" "uuid" NOT NULL,
    "config_override" "jsonb" DEFAULT '{}'::"jsonb",
    "is_active" boolean DEFAULT true,
    "is_deleted" boolean DEFAULT false,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."agent_tools" OWNER TO "postgres";


COMMENT ON TABLE "public"."agent_tools" IS 'Many-to-many linking table between agents and tools with optional config overrides';



COMMENT ON COLUMN "public"."agent_tools"."config_override" IS 'Agent-specific configuration overrides (merged with tool default config)';



CREATE TABLE IF NOT EXISTS "public"."agent_tools_backup" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "agent_id" "uuid",
    "name" "text" NOT NULL,
    "type" "public"."agent_tool_type" NOT NULL,
    "config" "jsonb" NOT NULL,
    "is_active" boolean DEFAULT true,
    "order" integer DEFAULT 0,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "description" "text",
    "is_deleted" boolean DEFAULT false NOT NULL
);


ALTER TABLE "public"."agent_tools_backup" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."chat_message_history" (
    "id" integer NOT NULL,
    "session_id" "text" NOT NULL,
    "message" "jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE "public"."chat_message_history" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."chat_message_history_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."chat_message_history_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."chat_message_history_id_seq" OWNED BY "public"."chat_message_history"."id";



CREATE TABLE IF NOT EXISTS "public"."chat_sessions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "agent_name" "text" NOT NULL,
    "is_active" boolean DEFAULT false NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "metadata" "jsonb",
    "chat_id" "uuid"
);


ALTER TABLE "public"."chat_sessions" OWNER TO "postgres";


COMMENT ON TABLE "public"."chat_sessions" IS 'Tracks individual chat sessions, their active status, and interaction timestamps.';



COMMENT ON COLUMN "public"."chat_sessions"."id" IS 'Unique identifier for the chat session.';



COMMENT ON COLUMN "public"."chat_sessions"."user_id" IS 'User who owns this session.';



COMMENT ON COLUMN "public"."chat_sessions"."agent_name" IS 'Conceptual agent type for this session (e.g., assistant).';



COMMENT ON COLUMN "public"."chat_sessions"."is_active" IS 'True if a client considers this session active.';



COMMENT ON COLUMN "public"."chat_sessions"."updated_at" IS 'Timestamp of the last client interaction or message in this session.';



CREATE TABLE IF NOT EXISTS "public"."email_digest_batches" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "start_time" timestamp with time zone NOT NULL,
    "end_time" timestamp with time zone NOT NULL,
    "duration_seconds" numeric(10,2) NOT NULL,
    "total_users" integer DEFAULT 0 NOT NULL,
    "successful" integer DEFAULT 0 NOT NULL,
    "failed" integer DEFAULT 0 NOT NULL,
    "summary" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."email_digest_batches" OWNER TO "postgres";


COMMENT ON TABLE "public"."email_digest_batches" IS 'Stores batch execution summaries for daily digest runs';



COMMENT ON COLUMN "public"."email_digest_batches"."summary" IS 'Detailed JSON summary of batch execution';



CREATE TABLE IF NOT EXISTS "public"."email_digests" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "generated_at" timestamp with time zone NOT NULL,
    "hours_back" integer DEFAULT 24 NOT NULL,
    "include_read" boolean DEFAULT false NOT NULL,
    "digest_content" "text" NOT NULL,
    "status" character varying(20) DEFAULT 'success'::character varying NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "context" "text" DEFAULT 'on-demand'::"text",
    "email_count" integer DEFAULT 0
);


ALTER TABLE "public"."email_digests" OWNER TO "postgres";


COMMENT ON TABLE "public"."email_digests" IS 'Stores individual email digest results for users';



COMMENT ON COLUMN "public"."email_digests"."hours_back" IS 'Number of hours looked back for emails';



COMMENT ON COLUMN "public"."email_digests"."include_read" IS 'Whether read emails were included';



COMMENT ON COLUMN "public"."email_digests"."digest_content" IS 'The generated email digest content';



COMMENT ON COLUMN "public"."email_digests"."status" IS 'Generation status: success, error, etc.';



COMMENT ON COLUMN "public"."email_digests"."context" IS 'Execution context: "scheduled" for background tasks, "on-demand" for user requests';



COMMENT ON COLUMN "public"."email_digests"."email_count" IS 'Number of emails found in the digest';



CREATE TABLE IF NOT EXISTS "public"."external_api_connections" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "service_name" "text" NOT NULL,
    "token_expires_at" timestamp with time zone,
    "scopes" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "service_user_id" "text",
    "service_user_email" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "access_token_secret_id" "uuid",
    "refresh_token_secret_id" "uuid",
    CONSTRAINT "external_api_connections_service_name_check" CHECK (("service_name" = ANY (ARRAY['gmail'::"text", 'google_calendar'::"text", 'slack'::"text"])))
);


ALTER TABLE "public"."external_api_connections" OWNER TO "postgres";


COMMENT ON TABLE "public"."external_api_connections" IS 'OAuth connections to external APIs with encrypted token storage';



COMMENT ON COLUMN "public"."external_api_connections"."id" IS 'Primary key UUID';



COMMENT ON COLUMN "public"."external_api_connections"."user_id" IS 'Reference to auth.users - owner of the connection';



COMMENT ON COLUMN "public"."external_api_connections"."service_name" IS 'Name of the external service (gmail, google_calendar, slack)';



COMMENT ON COLUMN "public"."external_api_connections"."token_expires_at" IS 'When the access token expires';



COMMENT ON COLUMN "public"."external_api_connections"."scopes" IS 'Array of OAuth scopes granted';



COMMENT ON COLUMN "public"."external_api_connections"."service_user_id" IS 'User ID from the external service';



COMMENT ON COLUMN "public"."external_api_connections"."service_user_email" IS 'User email from the external service';



COMMENT ON COLUMN "public"."external_api_connections"."created_at" IS 'Timestamp when connection was created';



COMMENT ON COLUMN "public"."external_api_connections"."updated_at" IS 'Timestamp when connection was last updated';



COMMENT ON COLUMN "public"."external_api_connections"."is_active" IS 'Whether the connection is currently active';



COMMENT ON COLUMN "public"."external_api_connections"."access_token_secret_id" IS 'Reference to vault secret containing encrypted access token';



COMMENT ON COLUMN "public"."external_api_connections"."refresh_token_secret_id" IS 'Reference to vault secret containing encrypted refresh token';



CREATE TABLE IF NOT EXISTS "public"."focus_sessions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "task_id" "uuid" NOT NULL,
    "started_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "ended_at" timestamp with time zone,
    "duration_seconds" integer,
    "notes" "text",
    "mood" "text",
    "outcome" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "focus_sessions_mood_check" CHECK (("mood" = ANY (ARRAY['energized'::"text", 'neutral'::"text", 'drained'::"text", 'focused'::"text", 'distracted'::"text", 'other'::"text"]))),
    CONSTRAINT "focus_sessions_outcome_check" CHECK (("outcome" = ANY (ARRAY['completed_task'::"text", 'made_progress'::"text", 'got_stuck'::"text", 'interrupted'::"text", 'planned_next'::"text", 'other'::"text"])))
);


ALTER TABLE "public"."focus_sessions" OWNER TO "postgres";


COMMENT ON COLUMN "public"."focus_sessions"."notes" IS 'User reflection or summary of what was done during the session.';



COMMENT ON COLUMN "public"."focus_sessions"."mood" IS 'User-reported mood after the session.';



COMMENT ON COLUMN "public"."focus_sessions"."outcome" IS 'User-reported outcome of the session.';



CREATE TABLE IF NOT EXISTS "public"."notes" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "title" "text",
    "content" "text" DEFAULT ''::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "deleted" boolean DEFAULT false NOT NULL
);


ALTER TABLE "public"."notes" OWNER TO "postgres";


COMMENT ON TABLE "public"."notes" IS 'User notes with soft delete support and RLS';



COMMENT ON COLUMN "public"."notes"."id" IS 'Primary key UUID';



COMMENT ON COLUMN "public"."notes"."user_id" IS 'Reference to auth.users - owner of the note';



COMMENT ON COLUMN "public"."notes"."title" IS 'Optional title for the note';



COMMENT ON COLUMN "public"."notes"."content" IS 'Main content of the note';



COMMENT ON COLUMN "public"."notes"."created_at" IS 'Timestamp when note was created';



COMMENT ON COLUMN "public"."notes"."updated_at" IS 'Timestamp when note was last updated (auto-updated)';



COMMENT ON COLUMN "public"."notes"."deleted" IS 'Soft delete flag - when true, note is considered deleted';



CREATE TABLE IF NOT EXISTS "public"."tasks" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "title" "text" NOT NULL,
    "notes" "text",
    "category" "text",
    "completed" boolean DEFAULT false NOT NULL,
    "due_date" "date",
    "time_period" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone,
    "position" integer,
    "priority" integer,
    "status" "public"."task_status",
    "motivation" "text",
    "description" "text",
    "completion_note" "text",
    "parent_task_id" "uuid",
    "subtask_position" integer,
    "deleted" boolean DEFAULT false,
    CONSTRAINT "tasks_status_check" CHECK (("status" = ANY (ARRAY['pending'::"public"."task_status", 'planning'::"public"."task_status", 'in_progress'::"public"."task_status", 'completed'::"public"."task_status", 'skipped'::"public"."task_status", 'deferred'::"public"."task_status"]))),
    CONSTRAINT "tasks_time_period_check" CHECK (("time_period" = ANY (ARRAY['Morning'::"text", 'Afternoon'::"text", 'Evening'::"text"])))
);


ALTER TABLE "public"."tasks" OWNER TO "postgres";


COMMENT ON COLUMN "public"."tasks"."time_period" IS 'Can be Morning, Afternoon, or Evening';



CREATE TABLE IF NOT EXISTS "public"."tools" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "type" "public"."agent_tool_type" NOT NULL,
    "description" "text",
    "config" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "is_active" boolean DEFAULT true,
    "is_deleted" boolean DEFAULT false,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."tools" OWNER TO "postgres";


COMMENT ON TABLE "public"."tools" IS 'Registry of reusable tool definitions';



COMMENT ON COLUMN "public"."tools"."config" IS 'Default configuration for this tool type';



CREATE TABLE IF NOT EXISTS "public"."user_agent_prompt_customizations" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "agent_name" "text" NOT NULL,
    "customization_type" "text" DEFAULT 'instruction_set'::"text" NOT NULL,
    "content" "jsonb" NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "priority" integer DEFAULT 0 NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."user_agent_prompt_customizations" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."user_api_tokens" WITH ("security_invoker"='on') AS
 SELECT "c"."id",
    "c"."user_id",
    "c"."service_name",
    "c"."service_user_id",
    "c"."service_user_email",
    "c"."scopes",
    "c"."token_expires_at",
    "c"."is_active",
    "c"."created_at",
    "c"."updated_at",
    "at_secret"."decrypted_secret" AS "access_token",
    "rt_secret"."decrypted_secret" AS "refresh_token"
   FROM (("public"."external_api_connections" "c"
     LEFT JOIN "vault"."decrypted_secrets" "at_secret" ON (("c"."access_token_secret_id" = "at_secret"."id")))
     LEFT JOIN "vault"."decrypted_secrets" "rt_secret" ON (("c"."refresh_token_secret_id" = "rt_secret"."id")));


ALTER TABLE "public"."user_api_tokens" OWNER TO "postgres";


COMMENT ON VIEW "public"."user_api_tokens" IS 'Secure view providing decrypted OAuth tokens with RLS protection';



ALTER TABLE ONLY "public"."chat_message_history" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."chat_message_history_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."agent_configurations"
    ADD CONSTRAINT "agent_configurations_agent_name_key" UNIQUE ("agent_name");



ALTER TABLE ONLY "public"."agent_configurations"
    ADD CONSTRAINT "agent_configurations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."agent_logs"
    ADD CONSTRAINT "agent_logs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."agent_long_term_memory"
    ADD CONSTRAINT "agent_long_term_memory_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."agent_schedules"
    ADD CONSTRAINT "agent_schedules_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."agent_sessions"
    ADD CONSTRAINT "agent_sessions_pkey" PRIMARY KEY ("session_id");



ALTER TABLE ONLY "public"."agent_tools_backup"
    ADD CONSTRAINT "agent_tools_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."agent_tools"
    ADD CONSTRAINT "agent_tools_pkey1" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."chat_message_history"
    ADD CONSTRAINT "chat_message_history_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."chat_sessions"
    ADD CONSTRAINT "chats_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."email_digest_batches"
    ADD CONSTRAINT "email_digest_batches_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."email_digests"
    ADD CONSTRAINT "email_digests_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."email_digests"
    ADD CONSTRAINT "email_digests_user_id_generated_at_key" UNIQUE ("user_id", "generated_at");



ALTER TABLE ONLY "public"."external_api_connections"
    ADD CONSTRAINT "external_api_connections_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."external_api_connections"
    ADD CONSTRAINT "external_api_connections_user_id_service_name_key" UNIQUE ("user_id", "service_name");



ALTER TABLE ONLY "public"."focus_sessions"
    ADD CONSTRAINT "focus_sessions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."notes"
    ADD CONSTRAINT "notes_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."tasks"
    ADD CONSTRAINT "tasks_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."tools"
    ADD CONSTRAINT "tools_name_key" UNIQUE ("name");



ALTER TABLE ONLY "public"."tools"
    ADD CONSTRAINT "tools_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."agent_long_term_memory"
    ADD CONSTRAINT "unique_user_agent_ltm" UNIQUE ("user_id", "agent_name");



COMMENT ON CONSTRAINT "unique_user_agent_ltm" ON "public"."agent_long_term_memory" IS 'Ensures that each user can have only one LTM document per agent_id.';



ALTER TABLE ONLY "public"."user_agent_prompt_customizations"
    ADD CONSTRAINT "uq_user_agent_customization_type" UNIQUE ("user_id", "agent_name", "customization_type");



ALTER TABLE ONLY "public"."user_agent_prompt_customizations"
    ADD CONSTRAINT "user_agent_prompt_customizations_pkey" PRIMARY KEY ("id");



CREATE INDEX "idx_agent_logs_agent_name" ON "public"."agent_logs" USING "btree" ("agent_name");



CREATE INDEX "idx_agent_logs_created_at" ON "public"."agent_logs" USING "btree" ("created_at");



CREATE INDEX "idx_agent_logs_user_id" ON "public"."agent_logs" USING "btree" ("user_id");



CREATE INDEX "idx_agent_schedules_active" ON "public"."agent_schedules" USING "btree" ("active") WHERE ("active" = true);



CREATE INDEX "idx_agent_schedules_user_active" ON "public"."agent_schedules" USING "btree" ("user_id", "active");



CREATE INDEX "idx_agent_sessions_user_id" ON "public"."agent_sessions" USING "btree" ("user_id");



CREATE INDEX "idx_agent_tools_active_order" ON "public"."agent_tools_backup" USING "btree" ("agent_id", "is_active", "order");



CREATE INDEX "idx_agent_tools_agent_id" ON "public"."agent_tools_backup" USING "btree" ("agent_id");



CREATE INDEX "idx_agent_tools_tool_id" ON "public"."agent_tools" USING "btree" ("tool_id") WHERE ("is_deleted" = false);



CREATE UNIQUE INDEX "idx_agent_tools_unique_active" ON "public"."agent_tools" USING "btree" ("agent_id", "tool_id") WHERE ("is_deleted" = false);



COMMENT ON INDEX "public"."idx_agent_tools_unique_active" IS 'Ensures one active assignment per agent-tool pair (allows soft deletes)';



CREATE INDEX "idx_chat_message_history_session_id" ON "public"."chat_message_history" USING "btree" ("session_id");



CREATE INDEX "idx_chats_active_last_interaction" ON "public"."chat_sessions" USING "btree" ("is_active", "updated_at") WHERE ("is_active" = true);



CREATE INDEX "idx_chats_user_agent_active" ON "public"."chat_sessions" USING "btree" ("user_id", "agent_name", "is_active") WHERE ("is_active" = true);



CREATE INDEX "idx_email_digest_batches_start_time" ON "public"."email_digest_batches" USING "btree" ("start_time");



CREATE INDEX "idx_email_digest_batches_status" ON "public"."email_digest_batches" USING "btree" ("successful", "failed");



CREATE INDEX "idx_email_digests_context" ON "public"."email_digests" USING "btree" ("context", "generated_at" DESC);



CREATE INDEX "idx_email_digests_generated_at" ON "public"."email_digests" USING "btree" ("generated_at");



CREATE INDEX "idx_email_digests_status" ON "public"."email_digests" USING "btree" ("status");



CREATE INDEX "idx_email_digests_user_id" ON "public"."email_digests" USING "btree" ("user_id");



CREATE INDEX "idx_external_api_connections_active" ON "public"."external_api_connections" USING "btree" ("is_active");



CREATE INDEX "idx_external_api_connections_expires_at" ON "public"."external_api_connections" USING "btree" ("token_expires_at");



CREATE INDEX "idx_external_api_connections_service_name" ON "public"."external_api_connections" USING "btree" ("service_name");



CREATE INDEX "idx_external_api_connections_user_id" ON "public"."external_api_connections" USING "btree" ("user_id");



CREATE INDEX "idx_focus_sessions_created_at" ON "public"."focus_sessions" USING "btree" ("created_at");



CREATE INDEX "idx_focus_sessions_task_id" ON "public"."focus_sessions" USING "btree" ("task_id");



CREATE INDEX "idx_focus_sessions_user_id" ON "public"."focus_sessions" USING "btree" ("user_id");



CREATE INDEX "idx_notes_deleted" ON "public"."notes" USING "btree" ("deleted");



CREATE INDEX "idx_notes_updated_at" ON "public"."notes" USING "btree" ("updated_at" DESC);



CREATE INDEX "idx_notes_user_id" ON "public"."notes" USING "btree" ("user_id");



CREATE INDEX "idx_tasks_completed" ON "public"."tasks" USING "btree" ("completed");



CREATE INDEX "idx_tasks_due_date" ON "public"."tasks" USING "btree" ("due_date");



CREATE INDEX "idx_tasks_position" ON "public"."tasks" USING "btree" ("position");



CREATE INDEX "idx_tasks_priority" ON "public"."tasks" USING "btree" ("priority");



CREATE INDEX "idx_tasks_status" ON "public"."tasks" USING "btree" ("status");



CREATE INDEX "idx_tasks_user_id" ON "public"."tasks" USING "btree" ("user_id");



CREATE INDEX "idx_tools_name" ON "public"."tools" USING "btree" ("name") WHERE ("is_deleted" = false);



CREATE INDEX "idx_tools_type" ON "public"."tools" USING "btree" ("type") WHERE ("is_deleted" = false);



CREATE INDEX "idx_user_agent_prompt_customizations_user_agent" ON "public"."user_agent_prompt_customizations" USING "btree" ("user_id", "agent_name");



CREATE OR REPLACE TRIGGER "trigger_agent_schedules_updated_at" BEFORE UPDATE ON "public"."agent_schedules" FOR EACH ROW EXECUTE FUNCTION "public"."update_agent_schedules_updated_at"();



CREATE OR REPLACE TRIGGER "update_agent_long_term_memory_updated_at" BEFORE UPDATE ON "public"."agent_long_term_memory" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_agent_sessions_updated_at" BEFORE UPDATE ON "public"."agent_sessions" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_agent_tools_updated_at" BEFORE UPDATE ON "public"."agent_tools" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_email_digests_updated_at" BEFORE UPDATE ON "public"."email_digests" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_external_api_connections_updated_at" BEFORE UPDATE ON "public"."external_api_connections" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_notes_updated_at" BEFORE UPDATE ON "public"."notes" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_tools_updated_at" BEFORE UPDATE ON "public"."tools" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



ALTER TABLE ONLY "public"."agent_logs"
    ADD CONSTRAINT "agent_logs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."agent_long_term_memory"
    ADD CONSTRAINT "agent_long_term_memory_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."agent_schedules"
    ADD CONSTRAINT "agent_schedules_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."agent_sessions"
    ADD CONSTRAINT "agent_sessions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."agent_tools_backup"
    ADD CONSTRAINT "agent_tools_agent_id_fkey" FOREIGN KEY ("agent_id") REFERENCES "public"."agent_configurations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."agent_tools"
    ADD CONSTRAINT "agent_tools_agent_id_fkey1" FOREIGN KEY ("agent_id") REFERENCES "public"."agent_configurations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."agent_tools"
    ADD CONSTRAINT "agent_tools_tool_id_fkey" FOREIGN KEY ("tool_id") REFERENCES "public"."tools"("id");



ALTER TABLE ONLY "public"."chat_sessions"
    ADD CONSTRAINT "chats_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."email_digests"
    ADD CONSTRAINT "email_digests_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."external_api_connections"
    ADD CONSTRAINT "external_api_connections_access_token_secret_id_fkey" FOREIGN KEY ("access_token_secret_id") REFERENCES "vault"."secrets"("id");



ALTER TABLE ONLY "public"."external_api_connections"
    ADD CONSTRAINT "external_api_connections_refresh_token_secret_id_fkey" FOREIGN KEY ("refresh_token_secret_id") REFERENCES "vault"."secrets"("id");



ALTER TABLE ONLY "public"."external_api_connections"
    ADD CONSTRAINT "external_api_connections_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."external_api_connections"
    ADD CONSTRAINT "fk_access_token_secret" FOREIGN KEY ("access_token_secret_id") REFERENCES "vault"."secrets"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."external_api_connections"
    ADD CONSTRAINT "fk_refresh_token_secret" FOREIGN KEY ("refresh_token_secret_id") REFERENCES "vault"."secrets"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."focus_sessions"
    ADD CONSTRAINT "focus_sessions_task_id_fkey" FOREIGN KEY ("task_id") REFERENCES "public"."tasks"("id");



ALTER TABLE ONLY "public"."focus_sessions"
    ADD CONSTRAINT "focus_sessions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id");



ALTER TABLE ONLY "public"."notes"
    ADD CONSTRAINT "notes_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."tasks"
    ADD CONSTRAINT "tasks_parent_task_id_fkey" FOREIGN KEY ("parent_task_id") REFERENCES "public"."tasks"("id");



ALTER TABLE ONLY "public"."tasks"
    ADD CONSTRAINT "tasks_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id");



ALTER TABLE ONLY "public"."user_agent_prompt_customizations"
    ADD CONSTRAINT "user_agent_prompt_customizations_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



CREATE POLICY "Allow full access to own agent_long_term_memory" ON "public"."agent_long_term_memory" USING (("auth"."uid"() = "user_id")) WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Allow full access to own agent_sessions" ON "public"."agent_sessions" USING (("auth"."uid"() = "user_id")) WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Allow individual delete access" ON "public"."tasks" FOR DELETE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Allow individual delete access for focus_sessions" ON "public"."focus_sessions" FOR DELETE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Allow individual insert access" ON "public"."tasks" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Allow individual insert access for focus_sessions" ON "public"."focus_sessions" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Allow individual read access" ON "public"."tasks" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Allow individual read access for focus_sessions" ON "public"."focus_sessions" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Allow individual update access" ON "public"."tasks" FOR UPDATE USING (("auth"."uid"() = "user_id")) WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Allow individual update access for focus_sessions" ON "public"."focus_sessions" FOR UPDATE USING (("auth"."uid"() = "user_id")) WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Allow service role to access all rows" ON "public"."email_digest_batches" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Allow service role to edit all records" ON "public"."external_api_connections" TO "postgres" USING (true) WITH CHECK (true);



CREATE POLICY "Allow service_role to manage all agent configs" ON "public"."agent_configurations" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Allow service_role to manage all agent tools" ON "public"."agent_tools" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Allow service_role to manage all agent tools" ON "public"."agent_tools_backup" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Allow service_role to manage all chat history" ON "public"."chat_message_history" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Allow service_role to manage all tools" ON "public"."tools" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Service role can access all schedules" ON "public"."agent_schedules" USING ((CURRENT_USER = 'postgres'::"name"));



CREATE POLICY "Service role can insert digests" ON "public"."email_digests" FOR INSERT WITH CHECK ((CURRENT_USER = 'postgres'::"name"));



CREATE POLICY "Users can delete their own API connections" ON "public"."external_api_connections" FOR DELETE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can delete their own email digests" ON "public"."email_digests" FOR DELETE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can delete their own notes" ON "public"."notes" FOR DELETE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can delete their own schedules" ON "public"."agent_schedules" FOR DELETE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can delete their own sessions" ON "public"."agent_sessions" FOR DELETE USING ("public"."is_record_owner"("user_id"));



CREATE POLICY "Users can insert their own API connections" ON "public"."external_api_connections" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert their own agent logs" ON "public"."agent_logs" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert their own digests" ON "public"."email_digests" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert their own email digests" ON "public"."email_digests" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert their own notes" ON "public"."notes" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert their own schedules" ON "public"."agent_schedules" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert their own sessions" ON "public"."agent_sessions" FOR INSERT WITH CHECK ("public"."is_record_owner"("user_id"));



CREATE POLICY "Users can manage their own chat chats" ON "public"."chat_sessions" USING (("auth"."uid"() = "user_id")) WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can manage their own prompt customizations" ON "public"."user_agent_prompt_customizations" USING ("public"."is_record_owner"("user_id")) WITH CHECK ("public"."is_record_owner"("user_id"));



CREATE POLICY "Users can select their own sessions" ON "public"."agent_sessions" FOR SELECT USING ("public"."is_record_owner"("user_id"));



CREATE POLICY "Users can update their own API connections" ON "public"."external_api_connections" FOR UPDATE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can update their own email digests" ON "public"."email_digests" FOR UPDATE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can update their own notes" ON "public"."notes" FOR UPDATE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can update their own schedules" ON "public"."agent_schedules" FOR UPDATE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can update their own sessions" ON "public"."agent_sessions" FOR UPDATE USING ("public"."is_record_owner"("user_id")) WITH CHECK ("public"."is_record_owner"("user_id"));



CREATE POLICY "Users can view their own API connections" ON "public"."external_api_connections" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view their own agent logs" ON "public"."agent_logs" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view their own digests" ON "public"."email_digests" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view their own email digests" ON "public"."email_digests" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view their own notes" ON "public"."notes" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view their own schedules" ON "public"."agent_schedules" FOR SELECT USING (("auth"."uid"() = "user_id"));



ALTER TABLE "public"."agent_configurations" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."agent_logs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."agent_long_term_memory" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."agent_schedules" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."agent_sessions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."agent_tools" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."agent_tools_backup" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."chat_message_history" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."chat_sessions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."email_digest_batches" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."email_digests" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."external_api_connections" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."focus_sessions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."notes" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."tasks" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."tools" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."user_agent_prompt_customizations" ENABLE ROW LEVEL SECURITY;




ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";
GRANT USAGE ON SCHEMA "public" TO "supabase_auth_admin";











































































































































































GRANT ALL ON FUNCTION "public"."check_connection_status"("p_user_id" "uuid", "p_service_name" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."check_connection_status"("p_user_id" "uuid", "p_service_name" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."check_connection_status"("p_user_id" "uuid", "p_service_name" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_connection_info"("p_user_id" "uuid", "p_service_name" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_connection_info"("p_user_id" "uuid", "p_service_name" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_connection_info"("p_user_id" "uuid", "p_service_name" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_oauth_tokens_for_scheduler"("p_user_id" "uuid", "p_service_name" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_oauth_tokens_for_scheduler"("p_user_id" "uuid", "p_service_name" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_oauth_tokens_for_scheduler"("p_user_id" "uuid", "p_service_name" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."is_record_owner"("record_user_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."is_record_owner"("record_user_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."is_record_owner"("record_user_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."list_user_connections"("p_user_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."list_user_connections"("p_user_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_user_connections"("p_user_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."revoke_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."revoke_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."revoke_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."store_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text", "p_access_token" "text", "p_refresh_token" "text", "p_expires_at" timestamp with time zone, "p_scopes" "text"[], "p_service_user_id" "text", "p_service_user_email" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."store_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text", "p_access_token" "text", "p_refresh_token" "text", "p_expires_at" timestamp with time zone, "p_scopes" "text"[], "p_service_user_id" "text", "p_service_user_email" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."store_oauth_tokens"("p_user_id" "uuid", "p_service_name" "text", "p_access_token" "text", "p_refresh_token" "text", "p_expires_at" timestamp with time zone, "p_scopes" "text"[], "p_service_user_id" "text", "p_service_user_email" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."store_secret"("p_secret" "text", "p_name" "text", "p_description" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."store_secret"("p_secret" "text", "p_name" "text", "p_description" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."store_secret"("p_secret" "text", "p_name" "text", "p_description" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."update_agent_schedules_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_agent_schedules_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_agent_schedules_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "service_role";


















GRANT ALL ON TABLE "public"."agent_configurations" TO "anon";
GRANT ALL ON TABLE "public"."agent_configurations" TO "authenticated";
GRANT ALL ON TABLE "public"."agent_configurations" TO "service_role";



GRANT ALL ON TABLE "public"."agent_logs" TO "anon";
GRANT ALL ON TABLE "public"."agent_logs" TO "authenticated";
GRANT ALL ON TABLE "public"."agent_logs" TO "service_role";



GRANT ALL ON TABLE "public"."agent_long_term_memory" TO "anon";
GRANT ALL ON TABLE "public"."agent_long_term_memory" TO "authenticated";
GRANT ALL ON TABLE "public"."agent_long_term_memory" TO "service_role";



GRANT ALL ON TABLE "public"."agent_schedules" TO "anon";
GRANT ALL ON TABLE "public"."agent_schedules" TO "authenticated";
GRANT ALL ON TABLE "public"."agent_schedules" TO "service_role";



GRANT ALL ON TABLE "public"."agent_sessions" TO "anon";
GRANT ALL ON TABLE "public"."agent_sessions" TO "authenticated";
GRANT ALL ON TABLE "public"."agent_sessions" TO "service_role";



GRANT ALL ON TABLE "public"."agent_tools" TO "anon";
GRANT ALL ON TABLE "public"."agent_tools" TO "authenticated";
GRANT ALL ON TABLE "public"."agent_tools" TO "service_role";



GRANT ALL ON TABLE "public"."agent_tools_backup" TO "anon";
GRANT ALL ON TABLE "public"."agent_tools_backup" TO "authenticated";
GRANT ALL ON TABLE "public"."agent_tools_backup" TO "service_role";



GRANT ALL ON TABLE "public"."chat_message_history" TO "anon";
GRANT ALL ON TABLE "public"."chat_message_history" TO "authenticated";
GRANT ALL ON TABLE "public"."chat_message_history" TO "service_role";



GRANT ALL ON SEQUENCE "public"."chat_message_history_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."chat_message_history_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."chat_message_history_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."chat_sessions" TO "anon";
GRANT ALL ON TABLE "public"."chat_sessions" TO "authenticated";
GRANT ALL ON TABLE "public"."chat_sessions" TO "service_role";



GRANT ALL ON TABLE "public"."email_digest_batches" TO "anon";
GRANT ALL ON TABLE "public"."email_digest_batches" TO "authenticated";
GRANT ALL ON TABLE "public"."email_digest_batches" TO "service_role";



GRANT ALL ON TABLE "public"."email_digests" TO "anon";
GRANT ALL ON TABLE "public"."email_digests" TO "authenticated";
GRANT ALL ON TABLE "public"."email_digests" TO "service_role";



GRANT ALL ON TABLE "public"."external_api_connections" TO "anon";
GRANT ALL ON TABLE "public"."external_api_connections" TO "authenticated";
GRANT ALL ON TABLE "public"."external_api_connections" TO "service_role";



GRANT ALL ON TABLE "public"."focus_sessions" TO "anon";
GRANT ALL ON TABLE "public"."focus_sessions" TO "authenticated";
GRANT ALL ON TABLE "public"."focus_sessions" TO "service_role";



GRANT ALL ON TABLE "public"."notes" TO "anon";
GRANT ALL ON TABLE "public"."notes" TO "authenticated";
GRANT ALL ON TABLE "public"."notes" TO "service_role";



GRANT ALL ON TABLE "public"."tasks" TO "anon";
GRANT ALL ON TABLE "public"."tasks" TO "authenticated";
GRANT ALL ON TABLE "public"."tasks" TO "service_role";



GRANT ALL ON TABLE "public"."tools" TO "anon";
GRANT ALL ON TABLE "public"."tools" TO "authenticated";
GRANT ALL ON TABLE "public"."tools" TO "service_role";



GRANT ALL ON TABLE "public"."user_agent_prompt_customizations" TO "anon";
GRANT ALL ON TABLE "public"."user_agent_prompt_customizations" TO "authenticated";
GRANT ALL ON TABLE "public"."user_agent_prompt_customizations" TO "service_role";









GRANT ALL ON TABLE "public"."user_api_tokens" TO "anon";
GRANT ALL ON TABLE "public"."user_api_tokens" TO "authenticated";
GRANT ALL ON TABLE "public"."user_api_tokens" TO "service_role";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "service_role";






























RESET ALL;
