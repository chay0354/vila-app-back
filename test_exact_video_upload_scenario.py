#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the EXACT scenario: React Native app uploading video to close task
Simulates the exact flow with exact error conditions
"""

import os
import sys
import requests
import json
import time
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

API_URL = "http://127.0.0.1:4000"  # Local backend

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(success, message):
    status = "[✓]" if success else "[✗]"
    print(f"{status} {message}")

def test_backend_accessible():
    """Test if backend is accessible (like other API calls work)"""
    print_section("1. Testing Backend Accessibility (Like Other API Calls)")
    
    try:
        # Test a simple endpoint (like other API calls)
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print_result(True, "Backend is accessible (like other API calls)")
            return True
        else:
            print_result(False, f"Backend returned {response.status_code}")
            return False
    except requests.exceptions.ConnectionError as e:
        print_result(False, f"Connection error: {str(e)}")
        print("\n   ⚠️  THIS IS THE PROBLEM!")
        print("   Backend is not accessible at all")
        return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False

def test_video_upload_with_react_native_format():
    """Test video upload with exact React Native format"""
    print_section("2. Testing Video Upload (Exact React Native Format)")
    
    try:
        # Simulate a video file (10MB - typical phone video)
        file_size = 10 * 1024 * 1024
        video_content = b"VIDEO_DATA_" + (b"x" * (file_size - 11))
        
        url = f"{API_URL}/api/storage/upload"
        
        # React Native FormData format
        files = {
            'file': ('video.mp4', video_content, 'video/mp4')
        }
        
        headers = {
            'Accept': 'application/json',
            # No Content-Type - React Native doesn't set it
        }
        
        print(f"Uploading {file_size / (1024*1024):.1f}MB video...")
        print(f"URL: {url}")
        print("Format: React Native FormData (file field)")
        
        # Simulate 120s timeout (same as app)
        start_time = time.time()
        
        try:
            response = requests.post(
                url,
                files=files,
                headers=headers,
                timeout=120  # Same as app
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print_result(True, f"Upload successful in {elapsed:.1f}s")
                print(f"   Response: {json.dumps(data, indent=2)}")
                return True, data.get('url')
            else:
                print_result(False, f"Upload failed: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                return False, None
                
        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            print_result(False, f"Upload timeout after {elapsed:.1f}s (120s limit)")
            print("\n   ⚠️  Video upload timed out!")
            print("   Solution: Increase timeout or compress video")
            return False, None
            
    except requests.exceptions.ConnectionError as e:
        print_result(False, f"Connection error: {str(e)}")
        print("\n   ⚠️  THIS IS YOUR ERROR!")
        print("   'Cannot reach backend at http://10.0.2.2:4000'")
        print("\n   The connection fails during upload, not before.")
        print("   This suggests:")
        print("   1. Backend not accessible from emulator (10.0.2.2)")
        print("   2. Connection drops during long upload")
        print("   3. Network timeout during upload")
        return False, None
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def test_backend_timeout():
    """Check if backend has timeout issues"""
    print_section("3. Checking Backend Timeout Settings")
    
    print("Backend uses uvicorn with default settings:")
    print("  - Default timeout: 60 seconds")
    print("  - Large video uploads may exceed this")
    print("\nChecking if backend is configured for long uploads...")
    
    # Check run_server.py
    try:
        with open('run_server.py', 'r') as f:
            content = f.read()
            if 'timeout' in content.lower():
                print("   Found timeout configuration")
            else:
                print("   No explicit timeout configuration found")
                print("   Using uvicorn defaults (may timeout on large uploads)")
    except:
        print("   Could not check server configuration")
    
    print("\n⚠️  Potential issue: Backend may timeout during large uploads")
    print("   Solution: Increase backend timeout or use chunked uploads")

def test_connection_stability():
    """Test if connection is stable during long upload"""
    print_section("4. Testing Connection Stability")
    
    try:
        # Test with progressively larger files
        sizes = [1, 5, 10, 20]  # MB
        
        for size_mb in sizes:
            file_size = size_mb * 1024 * 1024
            content = b"TEST_" + (b"x" * (file_size - 5))
            
            print(f"\nTesting {size_mb}MB upload...")
            start = time.time()
            
            try:
                files = {'file': (f'test-{size_mb}mb.mp4', content, 'video/mp4')}
                response = requests.post(
                    f"{API_URL}/api/storage/upload",
                    files=files,
                    timeout=120
                )
                
                elapsed = time.time() - start
                
                if response.status_code == 200:
                    print_result(True, f"{size_mb}MB upload OK ({elapsed:.1f}s)")
                else:
                    print_result(False, f"{size_mb}MB upload failed: {response.status_code}")
                    return False
            except requests.exceptions.Timeout:
                print_result(False, f"{size_mb}MB upload timed out")
                print(f"   Upload took too long (>120s)")
                return False
            except requests.exceptions.ConnectionError:
                print_result(False, f"{size_mb}MB upload - connection error")
                print(f"   Connection dropped during upload")
                return False
        
        return True
        
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  EXACT VIDEO UPLOAD SCENARIO TEST")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing: {API_URL}")
    
    # Test 1: Backend accessible (like other calls)
    accessible = test_backend_accessible()
    if not accessible:
        print("\n[ERROR] Backend not accessible at all")
        print("This explains why video upload fails!")
        print("\nSolution: Start backend: cd back && python run_server.py")
        return 1
    
    # Test 2: Video upload
    upload_works, video_url = test_video_upload_with_react_native_format()
    
    # Test 3: Backend timeout check
    test_backend_timeout()
    
    # Test 4: Connection stability
    stable = test_connection_stability()
    
    # Summary
    print_section("DIAGNOSIS")
    
    if accessible and upload_works and stable:
        print_result(True, "All tests passed - backend works perfectly")
        print("\nIf app still fails, the issue is:")
        print("  1. App using wrong API_BASE_URL")
        print("  2. App not rebuilt after .env changes")
        print("  3. Network issue specific to emulator")
        print("  4. Video file format issue in React Native")
    elif accessible and not upload_works:
        print_result(False, "Backend accessible but video upload fails")
        print("\nMost likely causes:")
        print("  1. Connection drops during long upload")
        print("  2. Backend timeout (60s default)")
        print("  3. Video file too large")
        print("  4. Network instability")
    elif not accessible:
        print_result(False, "Backend not accessible")
        print("\nSolution: Start backend server")
    else:
        print_result(False, "Mixed results - check individual tests above")
    
    return 0 if (accessible and upload_works and stable) else 1

if __name__ == "__main__":
    sys.exit(main())




