-- Check for unique constraints on inventory_orders table
SELECT 
    conname AS constraint_name,
    contype AS constraint_type,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'inventory_orders'::regclass
ORDER BY contype, conname;

-- Check table structure
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'inventory_orders'
ORDER BY ordinal_position;

