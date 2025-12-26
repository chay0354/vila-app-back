-- Verify what's actually stored in inspection_tasks
-- Run this to see if tasks are being saved and what their values are

-- Check all tasks with their actual values
SELECT 
    it.id,
    it.inspection_id,
    it.name,
    it.completed,
    CASE 
        WHEN it.completed = true THEN 'TRUE'
        WHEN it.completed = false THEN 'FALSE'
        ELSE 'NULL'
    END as completed_display,
    i.unit_number,
    i.guest_name,
    i.departure_date
FROM inspection_tasks it
LEFT JOIN inspections i ON it.inspection_id = i.id
ORDER BY i.departure_date DESC, it.inspection_id, it.name
LIMIT 100;

-- Count completed vs incomplete tasks per inspection
SELECT 
    i.id as inspection_id,
    i.unit_number,
    i.guest_name,
    COUNT(it.id) as total_tasks,
    SUM(CASE WHEN it.completed = true THEN 1 ELSE 0 END) as completed_tasks,
    SUM(CASE WHEN it.completed = false THEN 1 ELSE 0 END) as incomplete_tasks
FROM inspections i
LEFT JOIN inspection_tasks it ON i.id = it.inspection_id
GROUP BY i.id, i.unit_number, i.guest_name
ORDER BY i.departure_date DESC
LIMIT 20;

-- Check the most recent inspection tasks
SELECT 
    it.*,
    i.unit_number,
    i.guest_name
FROM inspection_tasks it
LEFT JOIN inspections i ON it.inspection_id = i.id
ORDER BY it.id DESC
LIMIT 50;





