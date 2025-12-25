-- Test query to check if tasks are being saved with completion status
-- Run this after marking some tasks as completed and clicking "שמור"

-- Check a specific inspection's tasks with their completion status
SELECT 
    it.id,
    it.name,
    it.completed,
    CASE 
        WHEN it.completed = true THEN 'TRUE'
        WHEN it.completed = false THEN 'FALSE'
        ELSE 'NULL'
    END as completed_display,
    pg_typeof(it.completed) as completed_type
FROM inspection_tasks it
WHERE it.inspection_id = 'INSP-39d40125-ec41-4815-b9d7-d33970b91b5a'
ORDER BY CAST(it.id AS INTEGER);

-- Check if any tasks are marked as completed
SELECT 
    COUNT(*) as total_tasks,
    SUM(CASE WHEN completed = true THEN 1 ELSE 0 END) as completed_count,
    SUM(CASE WHEN completed = false THEN 1 ELSE 0 END) as incomplete_count
FROM inspection_tasks
WHERE inspection_id = 'INSP-39d40125-ec41-4815-b9d7-d33970b91b5a';

-- Check the most recent task updates (if you have a updated_at column)
-- SELECT 
--     id,
--     name,
--     completed,
--     updated_at
-- FROM inspection_tasks
-- WHERE inspection_id = 'INSP-39d40125-ec41-4815-b9d7-d33970b91b5a'
-- ORDER BY updated_at DESC
-- LIMIT 10;

