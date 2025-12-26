-- Fix: Ensure completed column is boolean type and convert any string values
-- Run this in your Supabase SQL Editor if tasks are stored as strings

-- First, check current data type
SELECT 
    column_name,
    data_type,
    udt_name
FROM information_schema.columns
WHERE table_name = 'inspection_tasks' AND column_name = 'completed';

-- If completed is text/varchar, convert it to boolean
-- This will convert 'true', '1', 'yes' to true, everything else to false
DO $$
BEGIN
    -- Check if column is text type
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'inspection_tasks' 
        AND column_name = 'completed'
        AND data_type = 'text'
    ) THEN
        -- Convert text to boolean
        ALTER TABLE inspection_tasks 
        ALTER COLUMN completed TYPE boolean 
        USING CASE 
            WHEN LOWER(completed::text) IN ('true', '1', 'yes', 'on', 't') THEN true
            ELSE false
        END;
        
        RAISE NOTICE 'Converted completed column from text to boolean';
    ELSIF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'inspection_tasks' 
        AND column_name = 'completed'
        AND data_type != 'boolean'
    ) THEN
        -- Convert other types to boolean
        ALTER TABLE inspection_tasks 
        ALTER COLUMN completed TYPE boolean 
        USING CASE 
            WHEN completed::text IN ('true', '1', 'yes', 'on', 't') THEN true
            WHEN completed::text IN ('false', '0', 'no', 'off', 'f', '') THEN false
            ELSE false
        END;
        
        RAISE NOTICE 'Converted completed column to boolean';
    ELSE
        RAISE NOTICE 'Column is already boolean type';
    END IF;
END $$;

-- Verify the conversion
SELECT 
    id,
    name,
    completed,
    pg_typeof(completed) as completed_type
FROM inspection_tasks
LIMIT 10;




