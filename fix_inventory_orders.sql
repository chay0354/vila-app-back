-- Fix inventory_orders table to prevent 409 conflicts
-- Run this in Supabase SQL Editor

-- 1. Make sure id column is UUID type and has default
ALTER TABLE inventory_orders 
ALTER COLUMN id TYPE uuid USING id::uuid;

-- If the above fails, drop and recreate the column
-- ALTER TABLE inventory_orders DROP COLUMN id;
-- ALTER TABLE inventory_orders ADD COLUMN id uuid PRIMARY KEY DEFAULT gen_random_uuid();

-- 2. Ensure id has a default value (if not already set)
ALTER TABLE inventory_orders 
ALTER COLUMN id SET DEFAULT gen_random_uuid();

-- 3. Check if there are any unique constraints that might conflict
-- If you see constraints on (item_id, order_date) or similar, you might want to remove them:
-- ALTER TABLE inventory_orders DROP CONSTRAINT IF EXISTS inventory_orders_item_id_order_date_key;

-- 4. Verify the table structure
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'inventory_orders'
ORDER BY ordinal_position;

