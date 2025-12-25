-- Diagnostic query to check inspection tasks in the database
-- Run this in your Supabase SQL Editor to see what's actually stored

-- Check if tables exist
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name IN ('inspections', 'inspection_tasks')
ORDER BY table_name, ordinal_position;

-- Check all inspections
SELECT 
    id,
    order_id,
    unit_number,
    guest_name,
    departure_date,
    status,
    created_at
FROM inspections
ORDER BY created_at DESC
LIMIT 10;

-- Check all inspection tasks with their completion status
SELECT 
    it.id,
    it.inspection_id,
    it.name,
    it.completed,
    pg_typeof(it.completed) as completed_type,  -- Shows the actual data type
    i.unit_number,
    i.guest_name
FROM inspection_tasks it
LEFT JOIN inspections i ON it.inspection_id = i.id
ORDER BY it.inspection_id, it.name
LIMIT 50;

-- Count tasks by completion status
SELECT 
    inspection_id,
    COUNT(*) as total_tasks,
    SUM(CASE WHEN completed = true THEN 1 ELSE 0 END) as completed_count,
    SUM(CASE WHEN completed = false THEN 1 ELSE 0 END) as incomplete_count
FROM inspection_tasks
GROUP BY inspection_id
ORDER BY inspection_id;

-- Check a specific inspection's tasks (replace 'INSP-xxx' with actual inspection ID)
-- SELECT 
--     it.id,
--     it.name,
--     it.completed,
--     pg_typeof(it.completed) as completed_type
-- FROM inspection_tasks it
-- WHERE it.inspection_id = 'INSP-xxx'
-- ORDER BY it.name;



