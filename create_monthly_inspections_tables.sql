-- Create monthly_inspections and monthly_inspection_tasks tables
-- These are for monthly inspections that happen on the 1st of each month for each hotel

-- Create monthly_inspections table
CREATE TABLE IF NOT EXISTS monthly_inspections (
    id text PRIMARY KEY,
    unit_number text NOT NULL,
    inspection_month date NOT NULL, -- First day of the month (YYYY-MM-01)
    status text NOT NULL,
    created_at timestamptz DEFAULT now(),
    UNIQUE(unit_number, inspection_month) -- One inspection per hotel per month
);

-- Create monthly_inspection_tasks table with composite primary key
CREATE TABLE IF NOT EXISTS monthly_inspection_tasks (
    id text NOT NULL,
    inspection_id text NOT NULL REFERENCES monthly_inspections(id) ON DELETE CASCADE,
    name text NOT NULL,
    completed boolean NOT NULL DEFAULT false,
    PRIMARY KEY (id, inspection_id)
);

-- Enable Row Level Security
ALTER TABLE monthly_inspections ENABLE ROW LEVEL SECURITY;
ALTER TABLE monthly_inspection_tasks ENABLE ROW LEVEL SECURITY;

-- Create policies for monthly_inspections
DROP POLICY IF EXISTS "anon read monthly_inspections" ON monthly_inspections;
CREATE POLICY "anon read monthly_inspections" ON monthly_inspections FOR SELECT TO anon USING (true);

DROP POLICY IF EXISTS "anon insert monthly_inspections" ON monthly_inspections;
CREATE POLICY "anon insert monthly_inspections" ON monthly_inspections FOR INSERT TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon update monthly_inspections" ON monthly_inspections;
CREATE POLICY "anon update monthly_inspections" ON monthly_inspections FOR UPDATE TO anon USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon delete monthly_inspections" ON monthly_inspections;
CREATE POLICY "anon delete monthly_inspections" ON monthly_inspections FOR DELETE TO anon USING (true);

-- Create policies for monthly_inspection_tasks
DROP POLICY IF EXISTS "anon read monthly_inspection_tasks" ON monthly_inspection_tasks;
CREATE POLICY "anon read monthly_inspection_tasks" ON monthly_inspection_tasks FOR SELECT TO anon USING (true);

DROP POLICY IF EXISTS "anon insert monthly_inspection_tasks" ON monthly_inspection_tasks;
CREATE POLICY "anon insert monthly_inspection_tasks" ON monthly_inspection_tasks FOR INSERT TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon update monthly_inspection_tasks" ON monthly_inspection_tasks;
CREATE POLICY "anon update monthly_inspection_tasks" ON monthly_inspection_tasks FOR UPDATE TO anon USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon delete monthly_inspection_tasks" ON monthly_inspection_tasks;
CREATE POLICY "anon delete monthly_inspection_tasks" ON monthly_inspection_tasks FOR DELETE TO anon USING (true);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_monthly_inspections_month ON monthly_inspections(inspection_month);
CREATE INDEX IF NOT EXISTS idx_monthly_inspections_unit ON monthly_inspections(unit_number);
CREATE INDEX IF NOT EXISTS idx_monthly_inspection_tasks_inspection_id ON monthly_inspection_tasks(inspection_id);



