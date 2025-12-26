-- Add role and image_url columns to users table

-- Add role column if it doesn't exist (with DEFAULT so existing rows get the value)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'role'
    ) THEN
        -- Add column with DEFAULT - this automatically sets the value for existing rows
        ALTER TABLE users ADD COLUMN role text DEFAULT 'עובד תחזוקה';
        -- Keep the default for future inserts
        ALTER TABLE users ALTER COLUMN role SET DEFAULT 'עובד תחזוקה';
    ELSE
        -- Column exists, just update NULL values if any
        UPDATE users SET role = 'עובד תחזוקה' WHERE role IS NULL;
    END IF;
END $$;

-- Add image_url column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'image_url'
    ) THEN
        ALTER TABLE users ADD COLUMN image_url text;
    END IF;
END $$;

