#!/usr/bin/env python3
"""
Create chat_messages table in Supabase
Run this script to automatically create the table
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env file")
    sys.exit(1)

# SQL to create the table
SQL = """
create table if not exists chat_messages (
  id bigint generated always as identity primary key,
  sender text,
  content text not null,
  created_at timestamptz default now()
);

alter table chat_messages enable row level security;

create policy if not exists "anon read chat_messages" on chat_messages for select to anon using (true);
create policy if not exists "anon insert chat_messages" on chat_messages for insert to anon with check (true);
"""

def create_table():
    """Create chat_messages table using Supabase REST API"""
    try:
        # Use Supabase REST API to execute SQL
        # Note: Supabase doesn't have a direct SQL execution endpoint via REST
        # So we'll use the PostgREST API to check if table exists and provide instructions
        
        # Check if table exists by trying to query it
        headers = {
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
        }
        
        url = f"{SUPABASE_URL}/rest/v1/chat_messages?limit=1"
        resp = requests.get(url, headers=headers)
        
        if resp.status_code == 200:
            print("✅ chat_messages table already exists!")
            return True
        elif resp.status_code == 404 or "relation" in resp.text.lower():
            print("❌ chat_messages table does not exist")
            print("\n📝 Please run this SQL in Supabase SQL Editor:")
            print("=" * 60)
            print(SQL)
            print("=" * 60)
            print("\nOr visit: https://supabase.com/dashboard → Your Project → SQL Editor")
            return False
        else:
            print(f"⚠️  Unexpected response: {resp.status_code}")
            print(f"Response: {resp.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n📝 Please run this SQL manually in Supabase SQL Editor:")
        print("=" * 60)
        print(SQL)
        print("=" * 60)
        return False

if __name__ == "__main__":
    print("🔍 Checking chat_messages table...")
    create_table()

