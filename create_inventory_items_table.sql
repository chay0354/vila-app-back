-- Create inventory_items table
-- Run this in Supabase SQL Editor

-- Drop table if exists to recreate fresh
DROP TABLE IF EXISTS inventory_items CASCADE;

-- Create inventory_items table with default UUID
CREATE TABLE inventory_items (
    id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name text NOT NULL,
    category text NOT NULL,
    unit text NOT NULL,
    current_stock integer NOT NULL DEFAULT 0,
    min_stock integer NOT NULL DEFAULT 0
);

-- Enable Row Level Security
ALTER TABLE inventory_items ENABLE ROW LEVEL SECURITY;

-- Create policies for RLS
-- Allow anonymous and authenticated users to read
CREATE POLICY "Allow read on inventory_items" 
ON inventory_items FOR SELECT 
TO anon, authenticated 
USING (true);

-- Allow anonymous and authenticated users to insert
CREATE POLICY "Allow insert on inventory_items" 
ON inventory_items FOR INSERT 
TO anon, authenticated 
WITH CHECK (true);

-- Allow anonymous and authenticated users to update
CREATE POLICY "Allow update on inventory_items" 
ON inventory_items FOR UPDATE 
TO anon, authenticated 
USING (true)
WITH CHECK (true);

-- Allow anonymous and authenticated users to delete
CREATE POLICY "Allow delete on inventory_items" 
ON inventory_items FOR DELETE 
TO anon, authenticated 
USING (true);

-- Create indexes for better performance
CREATE INDEX idx_inventory_items_category ON inventory_items(category);
CREATE INDEX idx_inventory_items_name ON inventory_items(name);






