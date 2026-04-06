-- SPEC-035: RLS policies for config bucket on storage.objects
-- The bucket itself is created via the Supabase Storage API at app startup (not raw SQL).
-- These policies provide defense-in-depth for direct client access.

-- RLS: authenticated users can read system config
CREATE POLICY "Users can read system config"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'config'
    AND name LIKE 'system/%'
);

-- RLS: authenticated users can read their own user config
CREATE POLICY "Users can read own config"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'config'
    AND name LIKE 'users/' || auth.uid()::text || '/%'
);

-- RLS: authenticated users can write (insert) their own user config
CREATE POLICY "Users can write own config"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'config'
    AND name LIKE 'users/' || auth.uid()::text || '/%'
);

-- RLS: authenticated users can update their own user config
CREATE POLICY "Users can update own config"
ON storage.objects FOR UPDATE
TO authenticated
USING (
    bucket_id = 'config'
    AND name LIKE 'users/' || auth.uid()::text || '/%'
);
