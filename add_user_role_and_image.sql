-- Add role and image_url columns to users table
-- Run this script step by step if you encounter errors

-- Step 1: Add role column if it doesn't exist (with DEFAULT)
ALTER TABLE users ADD COLUMN IF NOT EXISTS role text DEFAULT 'עובד תחזוקה';

-- Step 2: Update any NULL values (in case column existed without default)
UPDATE users SET role = 'עובד תחזוקה' WHERE role IS NULL;

-- Step 3: Add image_url column if it doesn't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS image_url text;
