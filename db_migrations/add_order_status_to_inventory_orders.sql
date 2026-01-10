-- Add order_status column to inventory_orders table for פתוח/סגור status
ALTER TABLE inventory_orders 
ADD COLUMN IF NOT EXISTS order_status TEXT DEFAULT 'פתוח';

-- Add comment to document the column
COMMENT ON COLUMN inventory_orders.order_status IS 'סטטוס הזמנה: פתוח או סגור';

