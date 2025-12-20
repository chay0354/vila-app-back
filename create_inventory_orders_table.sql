-- Create inventory_orders table
-- Run this in Supabase SQL Editor

-- Drop table if exists to recreate fresh
DROP TABLE IF EXISTS inventory_orders CASCADE;

CREATE TABLE inventory_orders (
    id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    item_id text REFERENCES inventory_items(id) ON DELETE SET NULL,
    item_name text NOT NULL,
    quantity integer NOT NULL,
    unit text NOT NULL,
    order_date date NOT NULL,
    delivery_date date,
    status text NOT NULL,
    order_type text NOT NULL,
    ordered_by text,
    unit_number text
);

-- Enable Row Level Security
ALTER TABLE inventory_orders ENABLE ROW LEVEL SECURITY;

-- Create policies for RLS
-- Allow anonymous and authenticated users to read
CREATE POLICY "Allow read on inventory_orders" 
ON inventory_orders FOR SELECT 
TO anon, authenticated 
USING (true);

-- Allow anonymous and authenticated users to insert
CREATE POLICY "Allow insert on inventory_orders" 
ON inventory_orders FOR INSERT 
TO anon, authenticated 
WITH CHECK (true);

-- Allow anonymous and authenticated users to update
CREATE POLICY "Allow update on inventory_orders" 
ON inventory_orders FOR UPDATE 
TO anon, authenticated 
USING (true)
WITH CHECK (true);

-- Allow anonymous and authenticated users to delete
CREATE POLICY "Allow delete on inventory_orders" 
ON inventory_orders FOR DELETE 
TO anon, authenticated 
USING (true);

-- Create index on item_id for better performance
CREATE INDEX IF NOT EXISTS idx_inventory_orders_item_id 
ON inventory_orders(item_id);

-- Create index on order_date for better query performance
CREATE INDEX IF NOT EXISTS idx_inventory_orders_order_date 
ON inventory_orders(order_date);

-- Create index on status for filtering
CREATE INDEX IF NOT EXISTS idx_inventory_orders_status 
ON inventory_orders(status);

