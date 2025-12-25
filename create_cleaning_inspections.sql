-- Migration: Create cleaning_inspections and cleaning_inspection_tasks tables
-- These are completely separate from regular inspections

-- Create cleaning_inspections table
CREATE TABLE IF NOT EXISTS cleaning_inspections (
    id text PRIMARY KEY,
    order_id text,
    unit_number text NOT NULL,
    guest_name text NOT NULL,
    departure_date text NOT NULL,
    status text NOT NULL DEFAULT 'זמן הביקורות טרם הגיע',
    created_at timestamptz DEFAULT now()
);

-- Create cleaning_inspection_tasks table
CREATE TABLE IF NOT EXISTS cleaning_inspection_tasks (
    id text NOT NULL,
    cleaning_inspection_id text NOT NULL REFERENCES cleaning_inspections(id) ON DELETE CASCADE,
    name text NOT NULL,
    completed boolean NOT NULL DEFAULT false,
    PRIMARY KEY (id, cleaning_inspection_id)
);

-- Enable Row Level Security
ALTER TABLE cleaning_inspections ENABLE ROW LEVEL SECURITY;
ALTER TABLE cleaning_inspection_tasks ENABLE ROW LEVEL SECURITY;

-- Policies for cleaning_inspections
DROP POLICY IF EXISTS "anon read cleaning_inspections" ON cleaning_inspections;
CREATE POLICY "anon read cleaning_inspections" ON cleaning_inspections FOR SELECT TO anon USING (true);

DROP POLICY IF EXISTS "anon insert cleaning_inspections" ON cleaning_inspections;
CREATE POLICY "anon insert cleaning_inspections" ON cleaning_inspections FOR INSERT TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon update cleaning_inspections" ON cleaning_inspections;
CREATE POLICY "anon update cleaning_inspections" ON cleaning_inspections FOR UPDATE TO anon USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon delete cleaning_inspections" ON cleaning_inspections;
CREATE POLICY "anon delete cleaning_inspections" ON cleaning_inspections FOR DELETE TO anon USING (true);

-- Policies for cleaning_inspection_tasks
DROP POLICY IF EXISTS "anon read cleaning_inspection_tasks" ON cleaning_inspection_tasks;
CREATE POLICY "anon read cleaning_inspection_tasks" ON cleaning_inspection_tasks FOR SELECT TO anon USING (true);

DROP POLICY IF EXISTS "anon insert cleaning_inspection_tasks" ON cleaning_inspection_tasks;
CREATE POLICY "anon insert cleaning_inspection_tasks" ON cleaning_inspection_tasks FOR INSERT TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon update cleaning_inspection_tasks" ON cleaning_inspection_tasks;
CREATE POLICY "anon update cleaning_inspection_tasks" ON cleaning_inspection_tasks FOR UPDATE TO anon USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon delete cleaning_inspection_tasks" ON cleaning_inspection_tasks;
CREATE POLICY "anon delete cleaning_inspection_tasks" ON cleaning_inspection_tasks FOR DELETE TO anon USING (true);

