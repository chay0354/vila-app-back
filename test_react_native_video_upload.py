#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script that simulates React Native video upload
Tests the exact format React Native uses for FormData uploads
"""

import os
import sys
import requests
import json
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

API_URLS = [
    "http://127.0.0.1:4000",
    "http://10.0.2.2:4000",  # Android emulator localhost
]

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(success, message):
    """Print test result"""
    status = "[✓]" if success else "[✗]"
    print(f"{status} {message}")

def test_react_native_formdata_format(api_url):
    """Test upload using React Native FormData format"""
    print_section("Testing React Native FormData Format")
    
    try:
        # Create a test video file (simulating file:// URI)
        # In React Native, the file object looks like:
        # { uri: 'file:///path/to/video.mp4', type: 'video/mp4', name: 'video.mp4' }
        
        # For testing, we'll use actual file data
        test_video_content = b"REACT_NATIVE_VIDEO_" + (b"x" * (5 * 1024 * 1024))  # 5MB
        
        url = f"{api_url}/api/storage/upload"
        print(f"Testing: {url}")
        print("Simulating React Native FormData format...")
        
        # React Native FormData format
        # The key is 'file' (not 'media')
        files = {
            'file': ('test-video.mp4', test_video_content, 'video/mp4')
        }
        
        # React Native doesn't set Content-Type header - let requests set it
        headers = {
            'Accept': 'application/json',
            # No Content-Type - let requests set it with boundary
        }
        
        print(f"Uploading {len(test_video_content) / (1024*1024):.1f}MB video...")
        
        response = requests.post(
            url,
            files=files,
            headers=headers,
            timeout=60
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, "Upload successful with React Native format")
            print(f"   Response: {json.dumps(data, indent=2)}")
            return True, data.get('url')
        else:
            print_result(False, f"Upload failed: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False, None
            
    except requests.exceptions.ConnectionError as e:
        print_result(False, f"Connection error: {str(e)}")
        print("\n   ⚠️  THIS IS YOUR ERROR!")
        print("   Cannot reach backend from emulator perspective")
        print("\n   Solutions:")
        print("   1. Make sure backend is running: cd back && python run_server.py")
        print("   2. Backend should bind to 0.0.0.0 (already configured)")
        print("   3. Check firewall isn't blocking port 4000")
        print("   4. Try accessing http://10.0.2.2:4000/health from emulator browser")
        return False, None
    except requests.exceptions.Timeout:
        print_result(False, "Upload timeout")
        return False, None
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def test_from_emulator_perspective():
    """Test if backend is accessible from emulator's network perspective"""
    print_section("Testing from Emulator Perspective")
    
    print("Android emulator uses 10.0.2.2 to access host's localhost")
    print("This maps to 127.0.0.1 on the host machine")
    print("\nTesting connectivity...")
    
    accessible_url = None
    
    for url in API_URLS:
        try:
            print(f"\nTesting: {url}")
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print_result(True, f"{url} is accessible")
                accessible_url = url
                break
        except requests.exceptions.ConnectionError:
            print_result(False, f"{url} - Connection refused")
            print("   Backend may not be running or not accessible from this address")
        except Exception as e:
            print_result(False, f"{url} - Error: {str(e)}")
    
    if not accessible_url:
        print("\n⚠️  Backend not accessible from emulator perspective!")
        print("\nTroubleshooting:")
        print("  1. Start backend: cd back && python run_server.py")
        print("  2. Backend should show: 'Starting server on 0.0.0.0:4000'")
        print("  3. Test from host: curl http://127.0.0.1:4000/health")
        print("  4. Test from emulator browser: http://10.0.2.2:4000/health")
        return None
    
    return accessible_url

def test_large_video_upload(api_url):
    """Test with a larger video file (simulating real video)"""
    print_section("Testing Large Video Upload (20MB)")
    
    try:
        # Simulate a 20MB video (typical phone video size)
        file_size = 20 * 1024 * 1024
        test_content = b"LARGE_VIDEO_" + (b"x" * (file_size - 12))
        
        url = f"{api_url}/api/storage/upload"
        files = {'file': ('large-video.mp4', test_content, 'video/mp4')}
        
        print(f"Uploading {file_size / (1024*1024):.1f}MB...")
        print("This simulates a real video upload...")
        
        import time
        start = time.time()
        
        response = requests.post(url, files=files, timeout=180)
        
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Large video upload successful in {elapsed:.1f}s")
            print(f"   Upload speed: {file_size / elapsed / 1024 / 1024:.2f} MB/s")
            return True
        else:
            print_result(False, f"Upload failed: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print_result(False, "Upload timeout - file too large or connection too slow")
        print("\n   Solutions:")
        print("   1. Increase timeout in app (currently 120s)")
        print("   2. Compress video before upload")
        print("   3. Check network stability")
        return False
    except requests.exceptions.ConnectionError as e:
        print_result(False, f"Connection error: {str(e)}")
        print("\n   ⚠️  Connection drops during large upload!")
        print("   This is likely your issue - the connection fails mid-upload")
        return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  REACT NATIVE VIDEO UPLOAD TEST")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Check emulator connectivity
    api_url = test_from_emulator_perspective()
    if not api_url:
        print("\n[ERROR] Cannot proceed - backend not accessible")
        return 1
    
    print(f"\n✅ Using API: {api_url}")
    
    # Test 2: React Native FormData format
    success1, video_url = test_react_native_formdata_format(api_url)
    
    # Test 3: Large video
    if success1:
        success2 = test_large_video_upload(api_url)
    else:
        success2 = False
    
    # Summary
    print_section("TEST SUMMARY")
    
    results = [
        ("React Native FormData Format", success1),
        ("Large Video Upload (20MB)", success2),
    ]
    
    for test_name, result in results:
        status = "[✓]" if result else "[✗]"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, result in results if result)
    
    if passed == len(results):
        print("\n[SUCCESS] All tests passed!")
        print("\nIf app still fails:")
        print("  1. Check app console logs for specific error")
        print("  2. Verify API_BASE_URL in app matches test URL")
        print("  3. Check video file size (may be larger than 20MB)")
        print("  4. Check network stability during upload")
    else:
        print(f"\n[ERROR] {len(results) - passed} test(s) failed")
        print("\nMost likely issue: Connection error during upload")
        print("\nSolutions:")
        print("  1. Make sure backend is running and accessible")
        print("  2. Check if video file is too large (>50MB)")
        print("  3. Try smaller video file first")
        print("  4. Check network connection stability")
        print("  5. Increase timeout in app code (currently 120s)")
    
    return 0 if passed == len(results) else 1

if __name__ == "__main__":
    sys.exit(main())




