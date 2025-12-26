-- Add role and image_url columns to users table

-- Add role column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'role'
    ) THEN
        ALTER TABLE users ADD COLUMN role text DEFAULT 'עובד תחזוקה';
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

-- Update existing users to have default role if null
UPDATE users SET role = 'עובד תחזוקה' WHERE role IS NULL;

