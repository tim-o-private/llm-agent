-- Vault OAuth Token Integration Migration
-- Migrates external_api_connections to use Supabase Vault for secure token storage
-- Follows established patterns and maintains data integrity

-- Step 1: Add vault secret reference columns
ALTER TABLE public.external_api_connections 
ADD COLUMN access_token_secret_id UUID REFERENCES vault.secrets(id),
ADD COLUMN refresh_token_secret_id UUID REFERENCES vault.secrets(id);

-- Step 2: Create function to migrate existing tokens to vault
CREATE OR REPLACE FUNCTION migrate_tokens_to_vault()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    conn_record RECORD;
    access_secret_id UUID;
    refresh_secret_id UUID;
BEGIN
    -- Migrate existing connections with tokens
    FOR conn_record IN 
        SELECT id, user_id, service_name, access_token, refresh_token
        FROM public.external_api_connections 
        WHERE access_token IS NOT NULL
    LOOP
        -- Store access token in vault
        SELECT vault.create_secret(
            conn_record.access_token,
            format('%s_%s_access', conn_record.user_id, conn_record.service_name),
            format('Access token for %s - User %s', conn_record.service_name, conn_record.user_id)
        ) INTO access_secret_id;
        
        -- Store refresh token in vault if it exists
        refresh_secret_id := NULL;
        IF conn_record.refresh_token IS NOT NULL THEN
            SELECT vault.create_secret(
                conn_record.refresh_token,
                format('%s_%s_refresh', conn_record.user_id, conn_record.service_name),
                format('Refresh token for %s - User %s', conn_record.service_name, conn_record.user_id)
            ) INTO refresh_secret_id;
        END IF;
        
        -- Update connection with vault secret references
        UPDATE public.external_api_connections 
        SET 
            access_token_secret_id = access_secret_id,
            refresh_token_secret_id = refresh_secret_id,
            updated_at = NOW()
        WHERE id = conn_record.id;
        
        RAISE NOTICE 'Migrated tokens for user % service % to vault', conn_record.user_id, conn_record.service_name;
    END LOOP;
END;
$$;

-- Step 3: Execute migration (only if there are existing tokens)
DO $$
DECLARE
    token_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO token_count 
    FROM public.external_api_connections 
    WHERE access_token IS NOT NULL;
    
    IF token_count > 0 THEN
        RAISE NOTICE 'Migrating % existing token(s) to vault...', token_count;
        PERFORM migrate_tokens_to_vault();
        RAISE NOTICE 'Token migration completed successfully';
    ELSE
        RAISE NOTICE 'No existing tokens found, skipping migration';
    END IF;
END;
$$;

-- Step 5: Grant necessary permissions (views inherit RLS from underlying tables)
GRANT SELECT ON public.user_api_tokens TO authenticated;

-- Step 6: Add constraints for vault secret references
ALTER TABLE public.external_api_connections 
ADD CONSTRAINT fk_access_token_secret 
FOREIGN KEY (access_token_secret_id) REFERENCES vault.secrets(id) ON DELETE SET NULL;

ALTER TABLE public.external_api_connections 
ADD CONSTRAINT fk_refresh_token_secret 
FOREIGN KEY (refresh_token_secret_id) REFERENCES vault.secrets(id) ON DELETE SET NULL;

-- Step 7: Add check constraint to ensure either plaintext or vault tokens exist
ALTER TABLE public.external_api_connections 
ADD CONSTRAINT check_token_storage 
CHECK (
    (access_token IS NOT NULL) OR 
    (access_token_secret_id IS NOT NULL)
);

-- Step 8: Update table comments
COMMENT ON COLUMN public.external_api_connections.access_token_secret_id IS 'Reference to vault secret containing encrypted access token';
COMMENT ON COLUMN public.external_api_connections.refresh_token_secret_id IS 'Reference to vault secret containing encrypted refresh token';
COMMENT ON VIEW public.user_api_tokens IS 'Secure view providing decrypted OAuth tokens with RLS protection';

-- Step 9: Create function to clean up migration function (optional)
DROP FUNCTION IF EXISTS migrate_tokens_to_vault();

-- Migration completed successfully
-- Next step: Update application code to use vault tokens, then drop plaintext columns 