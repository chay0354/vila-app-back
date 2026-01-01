#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to check if images/videos are being fetched correctly from the backend.
"""

import os
import sys
import requests
from dotenv import load_dotenv
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:4000")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    print("Make sure .env file exists with these variables")
    sys.exit(1)

REST_URL = f"{SUPABASE_URL}/rest/v1"
SERVICE_HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}

def test_list_endpoint():
    """Test the list endpoint (should exclude images by default)"""
    print("\n" + "="*60)
    print("TEST 1: List endpoint (default - should exclude images)")
    print("="*60)
    
    try:
        # Test without include_image
        url = f"{API_BASE_URL}/api/maintenance/tasks"
        print(f"\n📡 Fetching: {url}")
        resp = requests.get(url, timeout=10)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            tasks = resp.json()
            print(f"✅ Got {len(tasks)} tasks")
            if tasks:
                task = tasks[0]
                print(f"\nFirst task fields: {list(task.keys())}")
                has_image = "image_uri" in task
                print(f"Has image_uri field: {has_image}")
                if has_image:
                    img_uri = task.get("image_uri")
                    if img_uri:
                        print(f"Image URI length: {len(str(img_uri))} chars")
                        print(f"Image URI preview: {str(img_uri)[:100]}...")
                    else:
                        print("⚠️ image_uri field exists but is None/empty")
                else:
                    print("OK - Correctly excluded image_uri (as expected)")
        else:
            print(f"ERROR: {resp.status_code}")
            print(resp.text[:200])
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_list_with_images():
    """Test the list endpoint with include_image=true"""
    print("\n" + "="*60)
    print("TEST 2: List endpoint WITH images (include_image=true)")
    print("="*60)
    
    try:
        url = f"{API_BASE_URL}/api/maintenance/tasks?include_image=true"
        print(f"\n📡 Fetching: {url}")
        resp = requests.get(url, timeout=10)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            tasks = resp.json()
            print(f"✅ Got {len(tasks)} tasks")
            if tasks:
                task = tasks[0]
                print(f"\nFirst task fields: {list(task.keys())}")
                has_image = "image_uri" in task
                print(f"Has image_uri field: {has_image}")
                if has_image:
                    img_uri = task.get("image_uri")
                    if img_uri:
                        print(f"✅ Image URI found!")
                        print(f"Image URI length: {len(str(img_uri))} chars")
                        print(f"Image URI preview: {str(img_uri)[:100]}...")
                        if "data:video" in str(img_uri) or ".mp4" in str(img_uri) or "/vidoes/" in str(img_uri):
                            print("🎥 This is a VIDEO")
                        elif "data:image" in str(img_uri) or "/images/" in str(img_uri):
                            print("🖼️ This is an IMAGE")
                    else:
                        print("⚠️ image_uri field exists but is None/empty")
                else:
                    print("❌ image_uri field missing even with include_image=true!")
        else:
            print(f"❌ Error: {resp.status_code}")
            print(resp.text[:200])
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_single_task_endpoint():
    """Test the single task endpoint (should include images by default)"""
    print("\n" + "="*60)
    print("TEST 3: Single task endpoint (should include images by default)")
    print("="*60)
    
    try:
        # First, get a task ID
        url = f"{API_BASE_URL}/api/maintenance/tasks"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            print(f"❌ Can't get task list: {resp.status_code}")
            return
        
        tasks = resp.json()
        if not tasks:
            print("⚠️ No tasks found to test")
            return
        
        task_id = tasks[0].get("id")
        print(f"\n📋 Testing with task ID: {task_id}")
        
        # Test single task endpoint
        url = f"{API_BASE_URL}/api/maintenance/tasks/{task_id}"
        print(f"\n📡 Fetching: {url}")
        resp = requests.get(url, timeout=10)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            task = resp.json()
            print(f"\nTask fields: {list(task.keys())}")
            has_image = "image_uri" in task
            print(f"Has image_uri field: {has_image}")
            if has_image:
                img_uri = task.get("image_uri")
                if img_uri:
                    print(f"✅ Image URI found!")
                    print(f"Image URI length: {len(str(img_uri))} chars")
                    print(f"Image URI preview: {str(img_uri)[:100]}...")
                    if "data:video" in str(img_uri) or ".mp4" in str(img_uri) or "/vidoes/" in str(img_uri) or "/storage/" in str(img_uri):
                        print("🎥 This is a VIDEO")
                    elif "data:image" in str(img_uri) or "/images/" in str(img_uri):
                        print("🖼️ This is an IMAGE")
                    else:
                        print(f"❓ Unknown type: {str(img_uri)[:50]}")
                else:
                    print("⚠️ image_uri field exists but is None/empty")
            else:
                print("❌ image_uri field missing from single task endpoint!")
        else:
            print(f"❌ Error: {resp.status_code}")
            print(resp.text[:200])
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_direct_supabase():
    """Test direct Supabase query to see what's actually in the database"""
    print("\n" + "="*60)
    print("TEST 4: Direct Supabase query (checking database)")
    print("="*60)
    
    try:
        url = f"{REST_URL}/maintenance_tasks"
        params = {
            "select": "id,title,image_uri",
            "limit": "5",
            "order": "created_date.desc"
        }
        print(f"\nQuerying Supabase directly: {url}")
        resp = requests.get(url, headers=SERVICE_HEADERS, params=params, timeout=10)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            tasks = resp.json()
            print(f"OK - Got {len(tasks)} tasks from database")
            for i, task in enumerate(tasks, 1):
                print(f"\n--- Task {i} ---")
                print(f"ID: {task.get('id')}")
                print(f"Title: {task.get('title')}")
                img_uri = task.get("image_uri")
                if img_uri:
                    print(f"OK - Has image_uri: {len(str(img_uri))} chars")
                    print(f"Preview: {str(img_uri)[:100]}...")
                    if "data:video" in str(img_uri) or ".mp4" in str(img_uri) or "/vidoes/" in str(img_uri):
                        print("VIDEO detected")
                    elif "data:image" in str(img_uri) or "/images/" in str(img_uri):
                        print("IMAGE detected")
                else:
                    print("WARNING - No image_uri (None or empty)")
        else:
            print(f"ERROR: {resp.status_code}")
            print(resp.text[:200])
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    print("="*60)
    print("Testing Image/Video Fetching from Backend")
    print("="*60)
    print(f"\nAPI Base URL: {API_BASE_URL}")
    print(f"Supabase URL: {SUPABASE_URL}")
    
    # Run all tests
    test_list_endpoint()
    test_list_with_images()
    test_single_task_endpoint()
    test_direct_supabase()
    
    print("\n" + "="*60)
    print("Testing complete!")
    print("="*60)

