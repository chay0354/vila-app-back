-- Create invoices table in Supabase
-- Run this in the Supabase SQL Editor

CREATE TABLE IF NOT EXISTS invoices (
  id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  image_data text NOT NULL,
  total_price numeric,
  currency text DEFAULT 'ILS',
  vendor text,
  date text,
  invoice_number text,
  extracted_data jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_invoices_vendor ON invoices(vendor);
CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(date);

-- Enable Row Level Security (RLS)
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

-- Create RLS policies to allow all operations
DROP POLICY IF EXISTS "anon read invoices" ON invoices;
CREATE POLICY "anon read invoices" 
ON invoices FOR SELECT 
TO anon USING (true);

DROP POLICY IF EXISTS "anon insert invoices" ON invoices;
CREATE POLICY "anon insert invoices" 
ON invoices FOR INSERT 
TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon update invoices" ON invoices;
CREATE POLICY "anon update invoices" 
ON invoices FOR UPDATE 
TO anon USING (true)
WITH CHECK (true);

DROP POLICY IF EXISTS "anon delete invoices" ON invoices;
CREATE POLICY "anon delete invoices" 
ON invoices FOR DELETE 
TO anon USING (true);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_invoices_updated_at ON invoices;
CREATE TRIGGER update_invoices_updated_at
    BEFORE UPDATE ON invoices
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

