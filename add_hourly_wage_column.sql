-- Add hourly_wage column to users table for employee management
-- Run this script to add the hourly_wage column

-- Add hourly_wage column if it doesn't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS hourly_wage numeric;

-- Set default to NULL (wages will be set by managers)
-- You can optionally set a default value like:
-- ALTER TABLE users ALTER COLUMN hourly_wage SET DEFAULT 0;

