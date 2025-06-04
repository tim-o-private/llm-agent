-- Add new columns to email_digests table
ALTER TABLE email_digests
ADD COLUMN digest_type VARCHAR(20),
ADD COLUMN tags TEXT[];

-- Update existing records with default digest_type
UPDATE email_digests
SET digest_type = 'daily'
WHERE digest_type IS NULL;

-- Create index on digest_type for faster queries
CREATE INDEX IF NOT EXISTS idx_email_digests_digest_type 
ON email_digests (digest_type);