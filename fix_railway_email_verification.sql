-- Fix email verification table in Railway production database
-- Run this on Railway PostgreSQL database to add missing verified_at column

ALTER TABLE email_verification_tokens ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP;

-- Verify the column was added
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name = 'email_verification_tokens' 
ORDER BY ordinal_position;