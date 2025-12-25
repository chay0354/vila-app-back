#!/usr/bin/env python3
"""
Diagnostic script to understand the inventory_orders table and identify 409 conflict sources
"""
import os
import sys
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    print("Make sure .env file exists in the back/ directory")
    sys.exit(1)

REST_URL = f"{SUPABASE_URL}/rest/v1"
HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Prefer": "return=representation",
}

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def check_table_structure():
    """Check the structure of inventory_orders table"""
    print_section("1. TABLE STRUCTURE")
    
    # Get table info via PostgREST metadata (if available)
    # Or we can query information_schema directly via SQL
    try:
        # Try to get a sample row to see structure
        resp = requests.get(
            f"{REST_URL}/inventory_orders?limit=1",
            headers=HEADERS
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                print("Sample row structure:")
                print(json.dumps(data[0], indent=2, default=str))
            else:
                print("Table is empty")
        else:
            print(f"Error getting sample: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

def check_recent_orders():
    """Check recent inventory orders"""
    print_section("2. RECENT ORDERS (Last 10)")
    
    try:
        resp = requests.get(
            f"{REST_URL}/inventory_orders?order=order_date.desc&limit=10",
            headers=HEADERS
        )
        if resp.status_code == 200:
            orders = resp.json()
            print(f"Found {len(orders)} recent orders:")
            for i, order in enumerate(orders, 1):
                print(f"\n  Order {i}:")
                print(f"    ID: {order.get('id', 'N/A')}")
                print(f"    Item: {order.get('item_name', 'N/A')}")
                print(f"    Quantity: {order.get('quantity', 'N/A')} {order.get('unit', 'N/A')}")
                print(f"    Order Date: {order.get('order_date', 'N/A')}")
                print(f"    Status: {order.get('status', 'N/A')}")
        else:
            print(f"Error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

def check_duplicate_ids():
    """Check for duplicate IDs in inventory_orders"""
    print_section("3. CHECKING FOR DUPLICATE IDs")
    
    try:
        # Get all IDs
        resp = requests.get(
            f"{REST_URL}/inventory_orders?select=id",
            headers=HEADERS
        )
        if resp.status_code == 200:
            orders = resp.json()
            ids = [order['id'] for order in orders if 'id' in order]
            
            # Check for duplicates
            seen = set()
            duplicates = []
            for id_val in ids:
                if id_val in seen:
                    duplicates.append(id_val)
                seen.add(id_val)
            
            print(f"Total orders: {len(ids)}")
            print(f"Unique IDs: {len(seen)}")
            if duplicates:
                print(f"⚠️  DUPLICATE IDs FOUND: {duplicates}")
            else:
                print("✓ No duplicate IDs found")
        else:
            print(f"Error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

def test_create_order():
    """Test creating an order to see what error we get"""
    print_section("4. TEST CREATING AN ORDER")
    
    import uuid
    test_id = str(uuid.uuid4())
    test_order = {
        "id": test_id,
        "item_id": None,  # Set to None to avoid FK constraint
        "item_name": "Test Item Diagnostic",
        "quantity": 1,
        "unit": "יחידה",
        "order_date": datetime.now().strftime("%Y-%m-%d"),
        "status": "ממתין לאישור",
        "order_type": "הזמנה כללית",
    }
    
    print(f"Attempting to create test order with ID: {test_id}")
    print(f"Order data: {json.dumps(test_order, indent=2, default=str)}")
    
    try:
        resp = requests.post(
            f"{REST_URL}/inventory_orders",
            headers=HEADERS,
            json=test_order
        )
        
        print(f"\nResponse Status: {resp.status_code}")
        print(f"Response Headers: {dict(resp.headers)}")
        
        if resp.status_code == 201:
            print("✓ Order created successfully!")
            created = resp.json()
            if isinstance(created, list) and created:
                print(f"Created order: {json.dumps(created[0], indent=2, default=str)}")
            
            # Clean up - delete the test order
            print("\nCleaning up test order...")
            delete_resp = requests.delete(
                f"{REST_URL}/inventory_orders?id=eq.{test_id}",
                headers=HEADERS
            )
            if delete_resp.status_code in [200, 204]:
                print("✓ Test order deleted")
            else:
                print(f"⚠️  Could not delete test order: {delete_resp.status_code}")
                
        elif resp.status_code == 409:
            print("⚠️  409 CONFLICT ERROR!")
            print(f"Error response: {resp.text}")
            print("\nThis means there's a unique constraint violation.")
            print("Possible causes:")
            print("  - Duplicate ID (primary key violation)")
            print("  - Unique constraint on other fields")
        else:
            print(f"⚠️  Error: {resp.status_code}")
            print(f"Response: {resp.text}")
            
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

def check_constraints():
    """Check database constraints (requires direct SQL access)"""
    print_section("5. CONSTRAINT INFORMATION")
    print("Note: This requires SQL access. Run this query in Supabase SQL Editor:")
    print("\n" + "-"*60)
    print("""
SELECT 
    conname AS constraint_name,
    contype AS constraint_type,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'inventory_orders'::regclass
ORDER BY contype, conname;
    """)
    print("-"*60)

def check_item_ids():
    """Check if item_ids in orders reference valid inventory_items"""
    print_section("6. CHECKING ITEM_ID REFERENCES")
    
    try:
        # Get all unique item_ids from orders
        resp = requests.get(
            f"{REST_URL}/inventory_orders?select=item_id",
            headers=HEADERS
        )
        if resp.status_code == 200:
            orders = resp.json()
            item_ids = set(order.get('item_id') for order in orders if order.get('item_id'))
            
            print(f"Found {len(item_ids)} unique item_ids in orders")
            
            # Check if they exist in inventory_items
            if item_ids:
                items_resp = requests.get(
                    f"{REST_URL}/inventory_items?select=id",
                    headers=HEADERS
                )
                if items_resp.status_code == 200:
                    items = items_resp.json()
                    valid_ids = set(item['id'] for item in items if 'id' in item)
                    
                    invalid_ids = item_ids - valid_ids
                    if invalid_ids:
                        print(f"⚠️  Found {len(invalid_ids)} invalid item_ids:")
                        for invalid_id in list(invalid_ids)[:5]:
                            print(f"    - {invalid_id}")
                    else:
                        print("✓ All item_ids reference valid inventory_items")
        else:
            print(f"Error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("\n" + "="*60)
    print("  INVENTORY ORDERS DIAGNOSTIC SCRIPT")
    print("="*60)
    print(f"Supabase URL: {SUPABASE_URL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    check_table_structure()
    check_recent_orders()
    check_duplicate_ids()
    check_item_ids()
    test_create_order()
    check_constraints()
    
    print_section("DIAGNOSIS COMPLETE")
    print("\nReview the output above to identify potential issues.")
    print("Common issues:")
    print("  - 409 Conflict: Usually means duplicate ID or unique constraint violation")
    print("  - Invalid item_id: Foreign key constraint violation")
    print("  - Missing required fields: NOT NULL constraint violation")

if __name__ == "__main__":
    main()






