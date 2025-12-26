-- Fix: Make task IDs unique per inspection, not globally
-- The current schema has 'id' as primary key, which means task ID '1' can only exist once
-- We need to allow the same task ID (e.g., '1', '2', '3') to exist for different inspections

-- Step 1: Drop the existing primary key constraint
ALTER TABLE inspection_tasks DROP CONSTRAINT IF EXISTS inspection_tasks_pkey;

-- Step 2: Create a composite primary key on (id, inspection_id)
-- This allows the same task ID to exist for different inspections
ALTER TABLE inspection_tasks ADD PRIMARY KEY (id, inspection_id);

-- Step 3: Verify the change
-- You can run this query to check:
-- SELECT 
--     constraint_name, 
--     constraint_type 
-- FROM information_schema.table_constraints 
-- WHERE table_name = 'inspection_tasks' AND constraint_type = 'PRIMARY KEY';




