-- Migration: Add order_id to inspections table and ensure proper structure for task persistence
-- This allows linking inspections to orders and persisting task completion status

-- Add order_id column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'inspections' AND column_name = 'order_id'
    ) THEN
        ALTER TABLE inspections ADD COLUMN order_id text;
    END IF;
END $$;

-- Ensure inspection_tasks table has the correct structure
-- (It should already exist based on README, but we'll ensure it's correct)
CREATE TABLE IF NOT EXISTS inspection_tasks (
    id text primary key,
    inspection_id text references inspections(id) on delete cascade,
    name text not null,
    completed boolean not null default false
);

-- Add write permissions for inspections and inspection_tasks
-- (Read permissions should already exist)
DROP POLICY IF EXISTS "anon insert inspections" ON inspections;
CREATE POLICY "anon insert inspections" ON inspections FOR INSERT TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon update inspections" ON inspections;
CREATE POLICY "anon update inspections" ON inspections FOR UPDATE TO anon USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon insert inspection_tasks" ON inspection_tasks;
CREATE POLICY "anon insert inspection_tasks" ON inspection_tasks FOR INSERT TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon update inspection_tasks" ON inspection_tasks;
CREATE POLICY "anon update inspection_tasks" ON inspection_tasks FOR UPDATE TO anon USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon delete inspection_tasks" ON inspection_tasks;
CREATE POLICY "anon delete inspection_tasks" ON inspection_tasks FOR DELETE TO anon USING (true);



