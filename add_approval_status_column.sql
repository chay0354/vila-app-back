-- Add approval_status column to users table
-- This migration adds the approval_status field for the new user approval system

-- Add the column if it doesn't exist
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS approval_status TEXT DEFAULT 'approved';

-- Update all existing users to 'approved' status (so they can still log in)
UPDATE users 
SET approval_status = 'approved' 
WHERE approval_status IS NULL;

-- Set default value for future inserts
ALTER TABLE users 
ALTER COLUMN approval_status SET DEFAULT 'approved';

-- Optional: Add a check constraint to ensure only valid values
-- Uncomment if you want to enforce this at the database level
-- ALTER TABLE users 
-- ADD CONSTRAINT check_approval_status 
-- CHECK (approval_status IN ('pending', 'approved'));

-- Verify the column was added
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'approval_status';

