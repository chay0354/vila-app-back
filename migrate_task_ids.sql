-- Migration script to update maintenance_tasks with client-generated IDs to UUIDs
-- This script finds all tasks with IDs starting with "task-" and generates new UUIDs for them
-- 
-- IMPORTANT: Run this script in your Supabase SQL editor if you have existing tasks
-- with client-generated IDs (those starting with "task-")
--
-- Note: This will update the IDs in the database. Make sure to backup first!

-- First, let's see how many tasks have client-generated IDs:
-- SELECT COUNT(*) FROM maintenance_tasks WHERE id LIKE 'task-%';

-- Update all tasks with client-generated IDs to have new UUIDs
-- Note: This uses PostgreSQL's gen_random_uuid() function
UPDATE maintenance_tasks 
SET id = gen_random_uuid()::text
WHERE id LIKE 'task-%';

-- Verify the update:
-- SELECT id FROM maintenance_tasks WHERE id LIKE 'task-%';
-- (Should return 0 rows)





