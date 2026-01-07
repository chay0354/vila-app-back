-- Add room column to maintenance_tasks table
ALTER TABLE maintenance_tasks 
ADD COLUMN IF NOT EXISTS room TEXT;






