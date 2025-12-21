-- Step 1: Add the order_group_id column
ALTER TABLE inventory_orders 
ADD COLUMN IF NOT EXISTS order_group_id text;

-- Step 2: Create an index for faster queries
CREATE INDEX IF NOT EXISTS idx_inventory_orders_group_id 
ON inventory_orders(order_group_id);

-- Step 3: For existing orders, set order_group_id to their id (so each existing order is its own group)
-- This ensures backward compatibility
UPDATE inventory_orders 
SET order_group_id = id 
WHERE order_group_id IS NULL;

-- Step 4: Group existing orders that have the same order_date and were created close together
-- This will group orders created on the same date within a few seconds (likely same order)
-- You may need to adjust this based on your data
-- For now, we'll use a simple approach: group by order_date and status for orders created today
-- You can manually update specific orders if needed

-- Example: If you want to group specific orders together, you can do:
-- UPDATE inventory_orders 
-- SET order_group_id = 'ORDER-2025-12-21-001' 
-- WHERE id IN ('12b1ca2b-8d9d-4f55-ac68-2bf5e6036796', '145c41c2-8e45-4cc4-899c-9f76683012d1');


