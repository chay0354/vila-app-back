-- Fix inventory_orders table to handle ID generation properly
-- Run this in Supabase SQL Editor

-- 1. Check for unique constraints that might cause 409 conflicts
SELECT 
    conname AS constraint_name,
    contype AS constraint_type,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'inventory_orders'::regclass
ORDER BY contype, conname;

-- 2. If there are unique constraints on combinations of fields (like item_id + order_date),
--    you might want to remove them if they're causing conflicts:
-- ALTER TABLE inventory_orders DROP CONSTRAINT IF EXISTS <constraint_name>;

-- 3. Since id is text with no default, make sure it's properly set as primary key
--    and ensure the backend always provides a unique ID
ALTER TABLE inventory_orders 
ADD CONSTRAINT inventory_orders_id_pkey PRIMARY KEY (id);

-- 4. If you want to add a default UUID generation (optional, but backend handles it):
--    Note: This requires changing id to uuid type, which might break existing data
--    So it's better to let the backend generate the ID as it does now

-- 5. Verify the primary key is set
SELECT 
    tc.constraint_name, 
    tc.table_name, 
    kcu.column_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_name = 'inventory_orders' 
  AND tc.constraint_type = 'PRIMARY KEY';

