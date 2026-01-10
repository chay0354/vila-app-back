-- Add guest_phone column to orders table
ALTER TABLE orders 
ADD COLUMN IF NOT EXISTS guest_phone TEXT;

-- Add comment to document the column
COMMENT ON COLUMN orders.guest_phone IS 'מספר טלפון אורח';

