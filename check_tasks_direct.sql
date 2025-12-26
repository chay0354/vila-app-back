-- Direct check: See if tasks exist for the specific inspection
-- Run this to verify tasks are actually in the database

-- Check tasks for the inspection that was just saved
SELECT 
    id,
    inspection_id,
    name,
    completed,
    pg_typeof(completed) as completed_type
FROM inspection_tasks
WHERE inspection_id = 'INSP-291e0855-91b5-412e-be5f-658f83149bd7'
ORDER BY CAST(id AS INTEGER);

-- Count tasks per inspection
SELECT 
    inspection_id,
    COUNT(*) as task_count,
    SUM(CASE WHEN completed = true THEN 1 ELSE 0 END) as completed_count
FROM inspection_tasks
GROUP BY inspection_id
ORDER BY inspection_id;

-- Check all inspections
SELECT 
    i.id as inspection_id,
    i.unit_number,
    i.guest_name,
    COUNT(it.id) as task_count
FROM inspections i
LEFT JOIN inspection_tasks it ON i.id = it.inspection_id
GROUP BY i.id, i.unit_number, i.guest_name
ORDER BY i.id;






