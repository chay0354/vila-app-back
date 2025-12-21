-- Create cleaning_schedule table in Supabase
-- Run this in the Supabase SQL Editor

CREATE TABLE IF NOT EXISTS cleaning_schedule (
  id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  date date NOT NULL,
  start_time time NOT NULL,
  end_time time NOT NULL,
  cleaner_name text NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_cleaning_schedule_date ON cleaning_schedule(date);
CREATE INDEX IF NOT EXISTS idx_cleaning_schedule_cleaner ON cleaning_schedule(cleaner_name);

-- Enable Row Level Security (RLS)
ALTER TABLE cleaning_schedule ENABLE ROW LEVEL SECURITY;

-- Create RLS policies to allow all operations (adjust as needed for your security requirements)
DROP POLICY IF EXISTS "anon read cleaning_schedule" ON cleaning_schedule;
CREATE POLICY "anon read cleaning_schedule" 
ON cleaning_schedule FOR SELECT 
TO anon USING (true);

DROP POLICY IF EXISTS "anon insert cleaning_schedule" ON cleaning_schedule;
CREATE POLICY "anon insert cleaning_schedule" 
ON cleaning_schedule FOR INSERT 
TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon update cleaning_schedule" ON cleaning_schedule;
CREATE POLICY "anon update cleaning_schedule" 
ON cleaning_schedule FOR UPDATE 
TO anon USING (true);

DROP POLICY IF EXISTS "anon delete cleaning_schedule" ON cleaning_schedule;
CREATE POLICY "anon delete cleaning_schedule" 
ON cleaning_schedule FOR DELETE 
TO anon USING (true);

