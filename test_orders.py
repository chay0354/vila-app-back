#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
import uuid
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

base = "http://127.0.0.1:4000"
order_id = f"ORD-{uuid.uuid4()}"

print("=== Creating Order ===")
create_data = {
    "id": order_id,
    "guest_name": "Test Guest",
    "unit_number": "101",
    "arrival_date": "2025-03-01",
    "departure_date": "2025-03-03",
    "status": "חדש",
    "guests_count": 2,
    "paid_amount": 0,
    "total_amount": 1500,
    "payment_method": "מזומן"
}

try:
    resp = requests.post(f"{base}/orders", json=create_data)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
    resp.raise_for_status()
    print(f"OK Created: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"ERROR creating: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"  Response text: {e.response.text}")
    exit(1)

print("\n=== Getting All Orders ===")
try:
    resp = requests.get(f"{base}/orders")
    resp.raise_for_status()
    all_orders = resp.json()
    print(f"OK Found {len(all_orders)} orders")
    found = next((o for o in all_orders if o.get("id") == order_id), None)
    if found:
        print(f"OK Found our order: {json.dumps(found, indent=2, ensure_ascii=False)}")
    else:
        print("WARN Order not found in list")
except Exception as e:
    print(f"ERROR getting orders: {e}")

print("\n=== Updating Order ===")
update_data = {
    "status": "שולם",
    "paid_amount": 1500
}

try:
    resp = requests.patch(f"{base}/orders/{order_id}", json=update_data)
    print(f"Status: {resp.status_code}")
    resp.raise_for_status()
    print(f"OK Updated: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"ERROR updating: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"  Response text: {e.response.text}")

print("\n=== Deleting Order ===")
try:
    resp = requests.delete(f"{base}/orders/{order_id}")
    print(f"Status: {resp.status_code}")
    resp.raise_for_status()
    print(f"OK Deleted order {order_id}")
except Exception as e:
    print(f"ERROR deleting: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"  Response text: {e.response.text}")

print("\n=== Verifying Deletion ===")
try:
    resp = requests.get(f"{base}/orders")
    resp.raise_for_status()
    all_orders = resp.json()
    found = next((o for o in all_orders if o.get("id") == order_id), None)
    if found:
        print(f"ERROR: Order still exists!")
    else:
        print(f"SUCCESS: Order deleted from DB")
except Exception as e:
    print(f"ERROR verifying: {e}")

print("\n=== Test Complete ===")
