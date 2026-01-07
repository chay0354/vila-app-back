-- Add closing_image_uri column to maintenance_tasks table
-- This column stores the image/video URI for when a task is closed
-- while keeping the original image_uri for when it was opened

ALTER TABLE maintenance_tasks 
ADD COLUMN IF NOT EXISTS closing_image_uri TEXT;

-- Add a comment to document the column
COMMENT ON COLUMN maintenance_tasks.closing_image_uri IS 'Image or video URI uploaded when the task was closed. The original image_uri is preserved for the opening media.';


