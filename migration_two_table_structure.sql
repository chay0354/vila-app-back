-- Migration: Restructure inventory orders into two tables
-- 1. inventory_orders: One row per order (metadata)
-- 2. inventory_order_items: Multiple rows per order (items with quantities)

-- Step 1: Create the new inventory_order_items table
CREATE TABLE IF NOT EXISTS inventory_order_items (
  id text PRIMARY KEY,
  order_id text NOT NULL REFERENCES inventory_orders(id) ON DELETE CASCADE,
  item_id text REFERENCES inventory_items(id),
  item_name text NOT NULL,
  quantity numeric NOT NULL,
  unit text NOT NULL DEFAULT '',
  created_at timestamptz DEFAULT now()
);

-- Step 2: Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_inventory_order_items_order_id 
ON inventory_order_items(order_id);

CREATE INDEX IF NOT EXISTS idx_inventory_order_items_item_id 
ON inventory_order_items(item_id);

-- Step 3: Migrate existing data from inventory_orders to the new structure
-- First, ensure all existing orders have unique IDs (they should already)
-- Then create order items from existing order rows

-- Insert order items from existing orders
INSERT INTO inventory_order_items (id, order_id, item_id, item_name, quantity, unit)
SELECT 
  gen_random_uuid()::text as id,
  id as order_id,
  item_id,
  item_name,
  quantity,
  COALESCE(NULLIF(unit, ''), '') as unit
FROM inventory_orders
WHERE item_name IS NOT NULL AND item_name != '';

-- Step 4: Remove item-specific columns from inventory_orders (keep them for now for safety)
-- We'll keep the columns but they'll be deprecated
-- You can drop them later after verifying everything works:
-- ALTER TABLE inventory_orders DROP COLUMN item_id;
-- ALTER TABLE inventory_orders DROP COLUMN item_name;
-- ALTER TABLE inventory_orders DROP COLUMN quantity;
-- ALTER TABLE inventory_orders DROP COLUMN unit;

-- Step 5: Enable RLS on the new table
ALTER TABLE inventory_order_items ENABLE ROW LEVEL SECURITY;

-- Step 6: Create RLS policies
CREATE POLICY "anon read inventory_order_items" 
ON inventory_order_items FOR SELECT 
TO anon USING (true);

CREATE POLICY "anon insert inventory_order_items" 
ON inventory_order_items FOR INSERT 
TO anon WITH CHECK (true);

CREATE POLICY "anon update inventory_order_items" 
ON inventory_order_items FOR UPDATE 
TO anon USING (true);

CREATE POLICY "anon delete inventory_order_items" 
ON inventory_order_items FOR DELETE 
TO anon USING (true);

-- Step 7: Add a comment to document the structure
COMMENT ON TABLE inventory_orders IS 'Main order table - one row per order';
COMMENT ON TABLE inventory_order_items IS 'Order items - multiple rows per order, one per item';


