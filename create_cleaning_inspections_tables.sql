-- Create cleaning_inspections and cleaning_inspection_tasks tables
-- These are completely separate from the regular inspections tables

-- Create cleaning_inspections table
CREATE TABLE IF NOT EXISTS cleaning_inspections (
    id text PRIMARY KEY,
    order_id text,
    unit_number text,
    guest_name text,
    departure_date date NOT NULL,
    status text NOT NULL,
    created_at timestamptz DEFAULT now()
);

-- Create cleaning_inspection_tasks table with composite primary key
CREATE TABLE IF NOT EXISTS cleaning_inspection_tasks (
    id text NOT NULL,
    inspection_id text NOT NULL REFERENCES cleaning_inspections(id) ON DELETE CASCADE,
    name text NOT NULL,
    completed boolean NOT NULL DEFAULT false,
    PRIMARY KEY (id, inspection_id)
);

-- Enable Row Level Security
ALTER TABLE cleaning_inspections ENABLE ROW LEVEL SECURITY;
ALTER TABLE cleaning_inspection_tasks ENABLE ROW LEVEL SECURITY;

-- Create policies for cleaning_inspections
DROP POLICY IF EXISTS "anon read cleaning_inspections" ON cleaning_inspections;
CREATE POLICY "anon read cleaning_inspections" ON cleaning_inspections FOR SELECT TO anon USING (true);

DROP POLICY IF EXISTS "anon insert cleaning_inspections" ON cleaning_inspections;
CREATE POLICY "anon insert cleaning_inspections" ON cleaning_inspections FOR INSERT TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon update cleaning_inspections" ON cleaning_inspections;
CREATE POLICY "anon update cleaning_inspections" ON cleaning_inspections FOR UPDATE TO anon USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon delete cleaning_inspections" ON cleaning_inspections;
CREATE POLICY "anon delete cleaning_inspections" ON cleaning_inspections FOR DELETE TO anon USING (true);

-- Create policies for cleaning_inspection_tasks
DROP POLICY IF EXISTS "anon read cleaning_inspection_tasks" ON cleaning_inspection_tasks;
CREATE POLICY "anon read cleaning_inspection_tasks" ON cleaning_inspection_tasks FOR SELECT TO anon USING (true);

DROP POLICY IF EXISTS "anon insert cleaning_inspection_tasks" ON cleaning_inspection_tasks;
CREATE POLICY "anon insert cleaning_inspection_tasks" ON cleaning_inspection_tasks FOR INSERT TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon update cleaning_inspection_tasks" ON cleaning_inspection_tasks;
CREATE POLICY "anon update cleaning_inspection_tasks" ON cleaning_inspection_tasks FOR UPDATE TO anon USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon delete cleaning_inspection_tasks" ON cleaning_inspection_tasks;
CREATE POLICY "anon delete cleaning_inspection_tasks" ON cleaning_inspection_tasks FOR DELETE TO anon USING (true);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_cleaning_inspections_departure_date ON cleaning_inspections(departure_date);
CREATE INDEX IF NOT EXISTS idx_cleaning_inspections_order_id ON cleaning_inspections(order_id);
CREATE INDEX IF NOT EXISTS idx_cleaning_inspection_tasks_inspection_id ON cleaning_inspection_tasks(inspection_id);



