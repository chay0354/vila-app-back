#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

base = "http://127.0.0.1:4000"

# Get first item
print("=== Getting inventory items ===")
resp = requests.get(f"{base}/inventory/items")
items = resp.json()
if not items:
    print("No items found!")
    exit(1)

first_item = items[0]
item_id = first_item['id']
print(f"First item: {first_item.get('name', 'N/A')} (ID: {item_id})")
print(f"Current stock: {first_item.get('current_stock', 'N/A')}")
print(f"Min stock: {first_item.get('min_stock', 'N/A')}")

# Update it
print("\n=== Updating inventory item ===")
new_current = first_item.get('current_stock', 0) + 1
new_min = first_item.get('min_stock', 0)

payload = {
    "current_stock": new_current,
    "min_stock": new_min
}

print(f"Updating to: current_stock={new_current}, min_stock={new_min}")

resp = requests.patch(
    f"{base}/inventory/items/{item_id}",
    json=payload,
    headers={"Content-Type": "application/json"}
)

print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:200]}")

if resp.status_code == 200:
    # Verify update
    print("\n=== Verifying update ===")
    resp2 = requests.get(f"{base}/inventory/items")
    items2 = resp2.json()
    updated = next((i for i in items2 if i['id'] == item_id), None)
    if updated:
        print(f"Updated item current_stock: {updated.get('current_stock', 'N/A')}")
        print(f"Updated item min_stock: {updated.get('min_stock', 'N/A')}")
        if updated.get('current_stock') == new_current:
            print("SUCCESS: Update verified!")
        else:
            print("ERROR: Update not reflected in database")
    else:
        print("ERROR: Item not found after update")

