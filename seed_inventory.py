#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to seed the inventory_items table with initial products
"""
import requests
import uuid
import os
import sys
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables")

REST_URL = f"{SUPABASE_URL}/rest/v1"
SERVICE_HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Prefer": "return=representation",
}

# Initial products list
products = [
    # מצעים (Linens)
    {"name": "סדינים זוגיים", "category": "מצעים", "unit": "סט", "current_stock": 20, "min_stock": 10},
    {"name": "סדינים יחיד", "category": "מצעים", "unit": "סט", "current_stock": 15, "min_stock": 8},
    {"name": "כריות", "category": "מצעים", "unit": "יחידה", "current_stock": 30, "min_stock": 15},
    {"name": "שמיכות", "category": "מצעים", "unit": "יחידה", "current_stock": 25, "min_stock": 12},
    {"name": "מגבות אמבטיה", "category": "מצעים", "unit": "יחידה", "current_stock": 40, "min_stock": 20},
    {"name": "מגבות ידיים", "category": "מצעים", "unit": "יחידה", "current_stock": 50, "min_stock": 25},
    {"name": "מגבות חוף", "category": "מצעים", "unit": "יחידה", "current_stock": 20, "min_stock": 10},
    
    # מוצרי ניקיון (Cleaning Products)
    {"name": "חומר ניקוי רצפות", "category": "מוצרי ניקיון", "unit": "ליטר", "current_stock": 10, "min_stock": 5},
    {"name": "חומר ניקוי שירותים", "category": "מוצרי ניקיון", "unit": "ליטר", "current_stock": 8, "min_stock": 4},
    {"name": "חומר ניקוי זכוכית", "category": "מוצרי ניקיון", "unit": "ליטר", "current_stock": 6, "min_stock": 3},
    {"name": "ספוגים", "category": "מוצרי ניקיון", "unit": "יחידה", "current_stock": 30, "min_stock": 15},
    {"name": "מטליות ניקיון", "category": "מוצרי ניקיון", "unit": "חבילה", "current_stock": 20, "min_stock": 10},
    {"name": "שקיות אשפה", "category": "מוצרי ניקיון", "unit": "רול", "current_stock": 15, "min_stock": 8},
    {"name": "כפפות חד פעמיות", "category": "מוצרי ניקיון", "unit": "חבילה", "current_stock": 25, "min_stock": 12},
    {"name": "מטאטא", "category": "מוצרי ניקיון", "unit": "יחידה", "current_stock": 5, "min_stock": 2},
    {"name": "מגב", "category": "מוצרי ניקיון", "unit": "יחידה", "current_stock": 5, "min_stock": 2},
    
    # ציוד מתכלה (Consumables)
    {"name": "נייר טואלט", "category": "ציוד מתכלה", "unit": "רול", "current_stock": 50, "min_stock": 25},
    {"name": "נייר מטבח", "category": "ציוד מתכלה", "unit": "רול", "current_stock": 30, "min_stock": 15},
    {"name": "סבון ידיים", "category": "ציוד מתכלה", "unit": "בקבוק", "current_stock": 20, "min_stock": 10},
    {"name": "שמפו", "category": "ציוד מתכלה", "unit": "בקבוק", "current_stock": 20, "min_stock": 10},
    {"name": "מרכך שיער", "category": "ציוד מתכלה", "unit": "בקבוק", "current_stock": 20, "min_stock": 10},
    {"name": "סבון גוף", "category": "ציוד מתכלה", "unit": "יחידה", "current_stock": 30, "min_stock": 15},
    {"name": "כוסות חד פעמיים", "category": "ציוד מתכלה", "unit": "חבילה", "current_stock": 15, "min_stock": 8},
    {"name": "צלחות חד פעמיות", "category": "ציוד מתכלה", "unit": "חבילה", "current_stock": 12, "min_stock": 6},
    {"name": "סכו״ם חד פעמי", "category": "ציוד מתכלה", "unit": "חבילה", "current_stock": 10, "min_stock": 5},
    {"name": "קפה", "category": "ציוד מתכלה", "unit": "ק״ג", "current_stock": 5, "min_stock": 2},
    {"name": "תה", "category": "ציוד מתכלה", "unit": "חבילה", "current_stock": 8, "min_stock": 4},
    {"name": "סוכר", "category": "ציוד מתכלה", "unit": "ק״ג", "current_stock": 10, "min_stock": 5},
    
    # אחר (Other)
    {"name": "נרות", "category": "אחר", "unit": "יחידה", "current_stock": 20, "min_stock": 10},
    {"name": "מצית", "category": "אחר", "unit": "יחידה", "current_stock": 5, "min_stock": 2},
    {"name": "תיקי פלסטיק", "category": "אחר", "unit": "חבילה", "current_stock": 15, "min_stock": 8},
]

def seed_products():
    print("Starting to seed inventory products...")
    created = 0
    failed = 0
    
    for product in products:
        product["id"] = str(uuid.uuid4())
        try:
            resp = requests.post(
                f"{REST_URL}/inventory_items",
                headers=SERVICE_HEADERS,
                json=product
            )
            resp.raise_for_status()
            created += 1
            print(f"OK Created: {product['name']}")
        except Exception as e:
            failed += 1
            print(f"ERROR Failed to create {product['name']}: {e}")
    
    print(f"\n=== Summary ===")
    print(f"Created: {created}")
    print(f"Failed: {failed}")
    print(f"Total: {len(products)}")

if __name__ == "__main__":
    seed_products()

