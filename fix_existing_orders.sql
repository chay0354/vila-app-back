-- Fix existing orders: Group orders that have the same order_date
-- This will group orders created on the same date together
-- You can run this after the migration to group existing orders

-- First, make sure the column exists (run migration first)
ALTER TABLE inventory_orders 
ADD COLUMN IF NOT EXISTS order_group_id text;

-- Group orders by order_date
-- This creates a unique group ID for each order_date
-- Orders with the same order_date will be grouped together
UPDATE inventory_orders o1
SET order_group_id = (
  SELECT MIN(id) 
  FROM inventory_orders o2 
  WHERE o2.order_date = o1.order_date
)
WHERE order_group_id IS NULL OR order_group_id = id;

-- Alternative: If you want to group specific orders manually, use this:
-- UPDATE inventory_orders 
-- SET order_group_id = 'ORDER-2025-12-21-001' 
-- WHERE id IN ('12b1ca2b-8d9d-4f55-ac68-2bf5e6036796', '145c41c2-8e45-4cc4-899c-9f76683012d1');

-- To see the grouped orders:
-- SELECT order_group_id, COUNT(*) as item_count, array_agg(item_name) as items
-- FROM inventory_orders
-- GROUP BY order_group_id
-- ORDER BY order_group_id;


