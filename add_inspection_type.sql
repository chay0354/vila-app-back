-- Add type column to inspections table to distinguish between exit and cleaning inspections

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'inspections' AND column_name = 'type'
    ) THEN
        ALTER TABLE inspections ADD COLUMN type text DEFAULT 'exit';
        -- Update existing inspections to have type 'exit' for backward compatibility
        UPDATE inspections SET type = 'exit' WHERE type IS NULL;
    END IF;
END $$;

