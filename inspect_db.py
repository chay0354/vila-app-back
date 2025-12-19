#!/usr/bin/env python3
"""
Script to inspect Supabase database structure
Shows all tables and their columns
"""
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_supabase_config():
    """Get Supabase configuration"""
    supabase_url = os.environ.get('SUPABASE_URL', '').rstrip('/')
    supabase_key = os.environ.get('SUPABASE_ANON_KEY', '')
    
    # Also try service_role key if anon key is not available
    if not supabase_key:
        supabase_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    
    if not supabase_url:
        print("ERROR: SUPABASE_URL not found in environment variables")
        return None, None
    
    if not supabase_key:
        print("ERROR: SUPABASE_ANON_KEY or SUPABASE_SERVICE_ROLE_KEY not found")
        return None, None
    
    return supabase_url, supabase_key

def query_table(url: str, key: str, table_name: str, limit: int = 1):
    """Query a table using REST API"""
    headers = {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }
    
    # Use PostgREST API
    api_url = f"{url}/rest/v1/{table_name}?limit={limit}"
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None  # Table doesn't exist
        else:
            print(f"  [HTTP {response.status_code}] {response.text[:100]}")
            return None
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None

def inspect_table_structure(url: str, key: str, table_name: str):
    """Inspect a single table structure"""
    data = query_table(url, key, table_name, limit=1)
    
    if data is None:
        print(f"\n[TABLE] {table_name} - Not accessible or doesn't exist")
        return
    
    if isinstance(data, list) and len(data) > 0:
        print(f"\n[TABLE] {table_name}")
        print("=" * 60)
        sample_row = data[0]
        print("Columns:")
        for col_key, value in sample_row.items():
            value_type = type(value).__name__
            try:
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:50] + "..."
                # Encode to handle Unicode in Windows console
                value_str = value_str.encode('ascii', 'replace').decode('ascii')
            except:
                value_str = repr(value)[:50]
            print(f"  - {col_key}: {value_type} (example: {value_str})")
    elif isinstance(data, list) and len(data) == 0:
        print(f"\n[TABLE] {table_name} (empty)")
        print("=" * 60)
        print("  (No data to infer structure)")
    else:
        print(f"\n[TABLE] {table_name} - Unexpected response format")

def get_all_tables(url: str, key: str):
    """Get list of all tables by trying common table names"""
    # Common table names based on the app
    common_tables = [
        'users',
        'orders',
        'maintenance_tasks',
        'inventory_items',
        'inventory_orders',
        'inspection_missions',
        'attendance_logs',
    ]
    
    existing_tables = []
    
    for table_name in common_tables:
        data = query_table(url, key, table_name, limit=1)
        if data is not None:
            existing_tables.append(table_name)
    
    return existing_tables

def inspect_users_table(url: str, key: str):
    """Detailed inspection of users table"""
    print("\n" + "=" * 60)
    print("[USERS TABLE] DETAILED INSPECTION")
    print("=" * 60)
    
    # Get all users (limit to 100 for inspection)
    data = query_table(url, key, 'users', limit=100)
    
    if data and isinstance(data, list):
        print(f"\nTotal users found: {len(data)}")
        print("\nSample data:")
        for i, user in enumerate(data[:5], 1):  # Show first 5
            print(f"\n  User {i}:")
            for key, value in user.items():
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:100] + "..."
                print(f"    {key}: {value_str}")
        
        if len(data) > 5:
            print(f"\n  ... and {len(data) - 5} more users")
    elif data is None:
        print("Cannot access users table")
    else:
        print("No users found in database")

def main():
    print("Supabase Database Structure Inspector")
    print("=" * 60)
    
    url, key = get_supabase_config()
    if not url or not key:
        return 1
    
    print("\n[OK] Loaded Supabase configuration")
    url_display = url
    if len(url_display) > 50:
        url_display = url_display[:50] + "..."
    print(f"   URL: {url_display}")
    
    # Get all tables
    print("\n[INFO] Discovering tables...")
    tables = get_all_tables(url, key)
    
    if not tables:
        print("\n[WARNING] No tables found or unable to access tables")
        print("   Make sure your API key has proper permissions")
        return 1
    
    print(f"\n[OK] Found {len(tables)} table(s): {', '.join(tables)}")
    
    # Inspect each table
    for table in tables:
        inspect_table_structure(url, key, table)
    
    # Detailed inspection of users table
    if 'users' in tables:
        inspect_users_table(url, key)
    
    print("\n" + "=" * 60)
    print("[OK] Inspection complete!")
    print("=" * 60)
    
    return 0

if __name__ == '__main__':
    exit(main())

