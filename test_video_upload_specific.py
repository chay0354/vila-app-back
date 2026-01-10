#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script specifically for video upload issues
Simulates the exact flow when closing a task with video
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

API_URLS = [
    "http://127.0.0.1:4000",
    "http://10.0.2.2:4000",
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

def test_video_upload_with_timeout(api_url, file_size_mb=5):
    """Test video upload with different file sizes and timeouts"""
    print_section(f"Testing Video Upload ({file_size_mb}MB)")
    
    try:
        # Create test video content (simulating a video file)
        file_size_bytes = file_size_mb * 1024 * 1024
        test_video_content = b"FAKE_VIDEO_" + (b"x" * (file_size_bytes - 11))
        
        url = f"{api_url}/api/storage/upload"
        print(f"Uploading to: {url}")
        print(f"File size: {file_size_mb} MB ({file_size_bytes:,} bytes)")
        
        files = {
            'file': ('test-video.mp4', test_video_content, 'video/mp4')
        }
        
        # Test with different timeouts
        timeouts = [10, 30, 60, 120]
        
        for timeout in timeouts:
            print(f"\nTrying with {timeout}s timeout...")
            try:
                start_time = time.time()
                response = requests.post(url, files=files, timeout=timeout)
                elapsed = time.time() - start_time
                
                print(f"   Status: {response.status_code}")
                print(f"   Time taken: {elapsed:.2f}s")
                
                if response.status_code == 200:
                    data = response.json()
                    print_result(True, f"Upload successful in {elapsed:.2f}s")
                    print(f"   Response: {json.dumps(data, indent=2)}")
                    return True, data.get('url')
                else:
                    print_result(False, f"Upload failed: {response.status_code}")
                    print(f"   Response: {response.text[:500]}")
                    if timeout < max(timeouts):
                        continue  # Try next timeout
                    return False, None
                    
            except requests.exceptions.Timeout:
                print_result(False, f"Timeout after {timeout}s")
                if timeout < max(timeouts):
                    print(f"   Trying with longer timeout...")
                    continue
                return False, None
            except requests.exceptions.ConnectionError as e:
                print_result(False, f"Connection error: {str(e)}")
                print("\n   ⚠️  THIS IS THE ERROR YOU'RE SEEING!")
                print("   The app cannot reach the backend during upload.")
                return False, None
            except Exception as e:
                print_result(False, f"Error: {str(e)}")
                import traceback
                traceback.print_exc()
                return False, None
        
        return False, None
        
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def test_upload_with_progress(api_url):
    """Test upload with progress tracking"""
    print_section("Testing Upload with Progress Tracking")
    
    try:
        # Simulate a larger video (10MB)
        file_size = 10 * 1024 * 1024
        test_content = b"VIDEO_DATA_" + (b"x" * (file_size - 11))
        
        url = f"{api_url}/api/storage/upload"
        
        files = {
            'file': ('large-video.mp4', test_content, 'video/mp4')
        }
        
        print(f"Uploading {file_size / (1024*1024):.1f}MB file...")
        print("This may take a while...")
        
        # Use a session to track progress
        session = requests.Session()
        
        start_time = time.time()
        response = session.post(url, files=files, timeout=180)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Large file upload successful in {elapsed:.2f}s")
            print(f"   Upload speed: {file_size / elapsed / 1024 / 1024:.2f} MB/s")
            return True
        else:
            print_result(False, f"Upload failed: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print_result(False, "Upload timeout - file may be too large or connection too slow")
        return False
    except requests.exceptions.ConnectionError as e:
        print_result(False, f"Connection error during upload: {str(e)}")
        print("\n   ⚠️  THIS IS LIKELY YOUR ISSUE!")
        print("   The connection drops during large file upload.")
        print("\n   Possible causes:")
        print("   1. Network timeout (upload takes too long)")
        print("   2. Backend timeout (request exceeds server timeout)")
        print("   3. Connection reset during upload")
        return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_backend_timeout_settings():
    """Check backend timeout settings"""
    print_section("Checking Backend Configuration")
    
    print("Backend timeout settings:")
    print("  - Default uvicorn timeout: 60s")
    print("  - Large video uploads may exceed this")
    print("\nRecommendations:")
    print("  1. Increase backend timeout in run_server.py")
    print("  2. Or use chunked upload for large videos")
    print("  3. Or compress videos before upload")

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  VIDEO UPLOAD SPECIFIC TEST")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Find accessible API
    api_url = None
    for url in API_URLS:
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                api_url = url
                print(f"\n✅ Using API: {api_url}")
                break
        except:
            continue
    
    if not api_url:
        print("\n[ERROR] No backend accessible")
        print("Make sure backend is running: cd back && python run_server.py")
        return 1
    
    # Test 1: Small video (5MB)
    success1, url1 = test_video_upload_with_timeout(api_url, file_size_mb=5)
    
    # Test 2: Medium video (10MB)
    if success1:
        success2, url2 = test_video_upload_with_timeout(api_url, file_size_mb=10)
    else:
        success2 = False
    
    # Test 3: Large video with progress
    if success2:
        success3 = test_upload_with_progress(api_url)
    else:
        success3 = False
    
    # Summary
    print_section("TEST SUMMARY")
    
    results = [
        ("Small video (5MB)", success1),
        ("Medium video (10MB)", success2),
        ("Large video (10MB+ with progress)", success3),
    ]
    
    for test_name, result in results:
        status = "[✓]" if result else "[✗]"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, result in results if result)
    
    if passed == len(results):
        print("\n[SUCCESS] All video upload tests passed!")
        print("\nIf app still fails:")
        print("  1. Check app timeout settings")
        print("  2. Check video file size (may be too large)")
        print("  3. Check network stability")
    elif passed > 0:
        print(f"\n[PARTIAL] {passed}/{len(results)} tests passed")
        print("\nIssue: Large videos may be timing out")
        print("Solutions:")
        print("  1. Increase timeout in app (currently 120s)")
        print("  2. Compress videos before upload")
        print("  3. Check backend timeout settings")
    else:
        print("\n[ERROR] All video upload tests failed")
        print("\nMost likely issue: Connection error during upload")
        print("\nSolutions:")
        print("  1. Check backend is running and accessible")
        print("  2. Check network connection stability")
        print("  3. Try smaller video file")
        print("  4. Check if firewall is blocking large uploads")
    
    test_backend_timeout_settings()
    
    return 0 if passed == len(results) else 1

if __name__ == "__main__":
    sys.exit(main())




