# Inventory Order Grouping Implementation

## Database Migration

Run the SQL migration to add `order_group_id` column:

```sql
-- Run this in Supabase SQL Editor
ALTER TABLE inventory_orders 
ADD COLUMN IF NOT EXISTS order_group_id text;

CREATE INDEX IF NOT EXISTS idx_inventory_orders_group_id 
ON inventory_orders(order_group_id);

-- For existing orders, set order_group_id to their id (so each existing order is its own group)
UPDATE inventory_orders 
SET order_group_id = id 
WHERE order_group_id IS NULL;
```

## Backend API Updates Needed

The backend needs to:
1. Accept `order_group_id` in POST `/api/inventory/orders`
2. Return `order_group_id` in GET `/api/inventory/orders`
3. Support PATCH `/api/inventory/orders/{id}` to update order status

## Frontend Changes

✅ Already implemented:
- Added `orderGroupId` to `InventoryOrder` type
- Updated `createInventoryOrder` to send `orderGroupId`
- Updated `loadInventoryOrders` to read `orderGroupId`
- Updated `NewWarehouseOrderScreen` to generate and use `orderGroupId` for all items
- Updated `WarehouseScreen` to:
  - Group orders by `orderGroupId`
  - Display one card per group showing item count
  - Allow expanding to see all items
  - Allow changing status for entire order group

## How It Works

1. When creating a new order with multiple items, all items get the same `orderGroupId`
2. The orders list groups items by `orderGroupId` and shows one card per group
3. Clicking an order card expands to show all items in that order
4. Status changes apply to all items in the group


