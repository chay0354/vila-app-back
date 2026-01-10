#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to simulate the exact video upload scenario from the React Native app.
This tests the complete flow including the exact FormData format used by React Native.
"""

import requests
import os
import tempfile
import time
from pathlib import Path

# Configuration
API_BASE_URL = "http://127.0.0.1:4000"
# For emulator testing, use: http://10.0.2.2:4000
# But this script runs on host, so use 127.0.0.1

def create_test_video(size_mb=5):
    """Create a test video file of specified size."""
    # Create a dummy video file (just binary data, not a real video)
    # In real scenario, this would be from the camera
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    temp_file.write(b'\x00' * (size_mb * 1024 * 1024))
    temp_file.close()
    return temp_file.name

def test_video_upload():
    """Test video upload exactly as React Native app does it."""
    print("=" * 70)
    print("  REACT NATIVE VIDEO UPLOAD SIMULATION")
    print("=" * 70)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing: {API_BASE_URL}")
    print()
    
    # Test 1: Check backend accessibility
    print("=" * 70)
    print("  1. Testing Backend Accessibility")
    print("=" * 70)
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("[OK] Backend is accessible")
        else:
            print(f"[FAIL] Backend returned status {response.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("[FAIL] Cannot connect to backend")
        print(f"   Make sure backend is running: cd back && python run_server.py")
        return
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return
    
    # Test 2: Upload small video (1MB)
    print()
    print("=" * 70)
    print("  2. Testing Small Video Upload (1MB)")
    print("=" * 70)
    test_file = create_test_video(1)
    try:
        with open(test_file, 'rb') as f:
            files = {'file': ('test-video.mp4', f, 'video/mp4')}
            start_time = time.time()
            response = requests.post(
                f"{API_BASE_URL}/api/storage/upload",
                files=files,
                timeout=180  # 3 minutes
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"[OK] Upload successful in {elapsed:.1f}s")
                print(f"   URL: {data.get('url', 'N/A')}")
            else:
                print(f"[FAIL] Upload failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
    except requests.exceptions.Timeout:
        print("[FAIL] Upload timed out (>3 minutes)")
    except Exception as e:
        print(f"[FAIL] Error: {e}")
    finally:
        os.unlink(test_file)
    
    # Test 3: Upload medium video (5MB)
    print()
    print("=" * 70)
    print("  3. Testing Medium Video Upload (5MB)")
    print("=" * 70)
    test_file = create_test_video(5)
    try:
        with open(test_file, 'rb') as f:
            files = {'file': ('test-video.mp4', f, 'video/mp4')}
            start_time = time.time()
            response = requests.post(
                f"{API_BASE_URL}/api/storage/upload",
                files=files,
                timeout=180
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"[OK] Upload successful in {elapsed:.1f}s")
                print(f"   URL: {data.get('url', 'N/A')}")
            else:
                print(f"[FAIL] Upload failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
    except requests.exceptions.Timeout:
        print("[FAIL] Upload timed out (>3 minutes)")
    except Exception as e:
        print(f"[FAIL] Error: {e}")
    finally:
        os.unlink(test_file)
    
    # Test 4: Upload large video (10MB)
    print()
    print("=" * 70)
    print("  4. Testing Large Video Upload (10MB)")
    print("=" * 70)
    test_file = create_test_video(10)
    try:
        with open(test_file, 'rb') as f:
            files = {'file': ('test-video.mp4', f, 'video/mp4')}
            start_time = time.time()
            response = requests.post(
                f"{API_BASE_URL}/api/storage/upload",
                files=files,
                timeout=180
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"[OK] Upload successful in {elapsed:.1f}s")
                print(f"   URL: {data.get('url', 'N/A')}")
            else:
                print(f"[FAIL] Upload failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
    except requests.exceptions.Timeout:
        print("[FAIL] Upload timed out (>3 minutes)")
    except Exception as e:
        print(f"[FAIL] Error: {e}")
    finally:
        os.unlink(test_file)
    
    # Test 5: Check backend timeout settings
    print()
    print("=" * 70)
    print("  5. Backend Configuration Check")
    print("=" * 70)
    print("Backend timeout settings:")
    print("  - uvicorn timeout_keep_alive: 300s (5 minutes)")
    print("  - App timeout: 120s (2 minutes)")
    print("  - Test timeout: 180s (3 minutes)")
    print()
    print("If uploads fail, check:")
    print("  1. Backend is running: python run_server.py")
    print("  2. Backend is accessible from emulator: http://10.0.2.2:4000")
    print("  3. Network connection is stable")
    print("  4. Video file size is reasonable (<50MB)")
    
    print()
    print("=" * 70)
    print("  DIAGNOSIS COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    test_video_upload()

