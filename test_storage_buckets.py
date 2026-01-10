#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to check Supabase Storage buckets and their accessibility
"""

import os
import sys
import requests
import json

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Import Supabase config
try:
    from app.supabase_client import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
except ImportError:
    # Fallback to environment variables
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

STORAGE_URL = f"{SUPABASE_URL}/storage/v1"
STORAGE_HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
}

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(success, message):
    """Print test result"""
    status = "[✓]" if success else "[✗]"
    print(f"{status} {message}")

def test_bucket_exists(bucket_name):
    """Test if a bucket exists and is accessible"""
    print(f"\nTesting bucket: {bucket_name}")
    
    # Try to list objects in the bucket (this will fail if bucket doesn't exist)
    list_url = f"{STORAGE_URL}/bucket/{bucket_name}"
    
    try:
        response = requests.get(list_url, headers=STORAGE_HEADERS, timeout=5)
        
        if response.status_code == 200:
            print_result(True, f"Bucket '{bucket_name}' exists and is accessible")
            data = response.json()
            print(f"   Bucket info: {json.dumps(data, indent=2)}")
            return True
        elif response.status_code == 404:
            print_result(False, f"Bucket '{bucket_name}' does not exist (404)")
            return False
        else:
            print_result(False, f"Bucket '{bucket_name}' returned status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
    except Exception as e:
        print_result(False, f"Error checking bucket '{bucket_name}': {str(e)}")
        return False

def test_bucket_upload(bucket_name):
    """Test uploading a small file to the bucket"""
    print(f"\nTesting upload to bucket: {bucket_name}")
    
    test_content = b"This is a test file"
    test_filename = f"test-{bucket_name}.txt"
    upload_url = f"{STORAGE_URL}/object/{bucket_name}/{test_filename}"
    
    upload_headers = {
        **STORAGE_HEADERS,
        "Content-Type": "text/plain",
    }
    
    try:
        response = requests.put(
            upload_url,
            headers=upload_headers,
            data=test_content,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print_result(True, f"Upload to '{bucket_name}' successful")
            
            # Try to get the file back
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket_name}/{test_filename}"
            get_response = requests.get(public_url, timeout=5)
            if get_response.status_code == 200:
                print_result(True, f"File is publicly accessible at: {public_url}")
            else:
                print_result(False, f"File is not publicly accessible (status: {get_response.status_code})")
            
            # Clean up - delete the test file
            delete_url = f"{STORAGE_URL}/object/{bucket_name}/{test_filename}"
            delete_response = requests.delete(delete_url, headers=STORAGE_HEADERS, timeout=5)
            if delete_response.status_code in [200, 204]:
                print_result(True, "Test file cleaned up")
            
            return True
        else:
            print_result(False, f"Upload failed with status {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
    except Exception as e:
        print_result(False, f"Error uploading to '{bucket_name}': {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  SUPABASE STORAGE BUCKET TEST")
    print("=" * 70)
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("\n[ERROR] Supabase credentials not found!")
        print("   Make sure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set")
        return 1
    
    print(f"\nSupabase URL: {SUPABASE_URL}")
    print(f"Storage URL: {STORAGE_URL}")
    
    buckets_to_test = ["vidoes", "images"]
    
    print_section("Testing Bucket Existence")
    results = {}
    
    for bucket in buckets_to_test:
        results[bucket] = test_bucket_exists(bucket)
    
    print_section("Testing Bucket Upload")
    upload_results = {}
    
    for bucket in buckets_to_test:
        if results.get(bucket):
            upload_results[bucket] = test_bucket_upload(bucket)
        else:
            print(f"\nSkipping upload test for '{bucket}' - bucket doesn't exist")
            upload_results[bucket] = False
    
    # Summary
    print_section("Summary")
    
    all_exist = all(results.values())
    all_work = all(upload_results.values())
    
    for bucket in buckets_to_test:
        exists = results.get(bucket, False)
        works = upload_results.get(bucket, False)
        
        if exists and works:
            print_result(True, f"Bucket '{bucket}' exists and upload works")
        elif exists:
            print_result(False, f"Bucket '{bucket}' exists but upload failed")
        else:
            print_result(False, f"Bucket '{bucket}' does not exist")
    
    if all_exist and all_work:
        print("\n[SUCCESS] All buckets exist and are working!")
        print("\nThe storage buckets are properly configured.")
        print("If video uploads still fail in the app, check:")
        print("  1. App is using correct API_BASE_URL")
        print("  2. App was rebuilt after .env changes")
        print("  3. Network connectivity from device")
        return 0
    elif all_exist:
        print("\n[WARNING] Buckets exist but uploads are failing")
        print("Check bucket permissions and policies in Supabase Dashboard")
        return 1
    else:
        print("\n[ERROR] Some buckets are missing")
        missing = [b for b in buckets_to_test if not results.get(b)]
        print(f"Missing buckets: {', '.join(missing)}")
        print("\nCreate these buckets in Supabase Dashboard:")
        print("  1. Go to Storage → Buckets")
        print("  2. Click '+ New bucket'")
        print("  3. Create each missing bucket")
        print("  4. Set as Public: Yes")
        return 1

if __name__ == "__main__":
    sys.exit(main())




