-- Complete Migration: Two-Table Structure for Inventory Orders
-- Run this in Supabase SQL Editor

-- ============================================
-- PART 1: Create the new structure
-- ============================================

-- Create inventory_order_items table
CREATE TABLE IF NOT EXISTS inventory_order_items (
  id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  order_id text NOT NULL REFERENCES inventory_orders(id) ON DELETE CASCADE,
  item_id text REFERENCES inventory_items(id),
  item_name text NOT NULL,
  quantity numeric NOT NULL,
  unit text NOT NULL DEFAULT '',
  created_at timestamptz DEFAULT now()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_inventory_order_items_order_id 
ON inventory_order_items(order_id);

CREATE INDEX IF NOT EXISTS idx_inventory_order_items_item_id 
ON inventory_order_items(item_id);

-- Enable RLS
ALTER TABLE inventory_order_items ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
DROP POLICY IF EXISTS "anon read inventory_order_items" ON inventory_order_items;
CREATE POLICY "anon read inventory_order_items" 
ON inventory_order_items FOR SELECT 
TO anon USING (true);

DROP POLICY IF EXISTS "anon insert inventory_order_items" ON inventory_order_items;
CREATE POLICY "anon insert inventory_order_items" 
ON inventory_order_items FOR INSERT 
TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon update inventory_order_items" ON inventory_order_items;
CREATE POLICY "anon update inventory_order_items" 
ON inventory_order_items FOR UPDATE 
TO anon USING (true);

DROP POLICY IF EXISTS "anon delete inventory_order_items" ON inventory_order_items;
CREATE POLICY "anon delete inventory_order_items" 
ON inventory_order_items FOR DELETE 
TO anon USING (true);

-- ============================================
-- PART 2: Migrate existing data
-- ============================================

-- Migrate existing orders to the new structure
-- Each existing order row becomes one order with one item
INSERT INTO inventory_order_items (id, order_id, item_id, item_name, quantity, unit)
SELECT 
  gen_random_uuid()::text as id,
  id as order_id,
  item_id,
  item_name,
  quantity,
  COALESCE(NULLIF(unit, ''), '') as unit
FROM inventory_orders
WHERE item_name IS NOT NULL AND item_name != ''
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- PART 3: Optional - Clean up old columns (run after verifying everything works)
-- ============================================

-- Uncomment these after verifying the migration works:
-- ALTER TABLE inventory_orders DROP COLUMN IF EXISTS item_id;
-- ALTER TABLE inventory_orders DROP COLUMN IF EXISTS item_name;
-- ALTER TABLE inventory_orders DROP COLUMN IF EXISTS quantity;
-- ALTER TABLE inventory_orders DROP COLUMN IF EXISTS unit;
-- ALTER TABLE inventory_orders DROP COLUMN IF EXISTS order_group_id;

-- ============================================
-- Verification queries
-- ============================================

-- Check the structure:
-- SELECT 
--   o.id as order_id,
--   o.order_date,
--   o.status,
--   COUNT(oi.id) as item_count,
--   json_agg(json_build_object('item_name', oi.item_name, 'quantity', oi.quantity, 'unit', oi.unit)) as items
-- FROM inventory_orders o
-- LEFT JOIN inventory_order_items oi ON o.id = oi.order_id
-- GROUP BY o.id, o.order_date, o.status
-- ORDER BY o.order_date DESC;


