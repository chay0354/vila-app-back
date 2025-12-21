-- Migration: Add order_group_id to inventory_orders table
-- This allows grouping multiple items into a single order

-- Add the order_group_id column
ALTER TABLE inventory_orders 
ADD COLUMN IF NOT EXISTS order_group_id text;

-- Create an index for faster queries
CREATE INDEX IF NOT EXISTS idx_inventory_orders_group_id 
ON inventory_orders(order_group_id);

-- For existing orders, set order_group_id to their id (so each existing order is its own group)
UPDATE inventory_orders 
SET order_group_id = id 
WHERE order_group_id IS NULL;

-- Add RLS policy if needed (should already exist, but just in case)
-- The existing policies should cover this column automatically


