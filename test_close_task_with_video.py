#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to simulate closing a maintenance task with a video
Tests the complete flow: upload video -> update task with status 'סגור'
"""

import os
import sys
import requests
import json
import uuid
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Test both local and production
API_URLS = [
    "http://127.0.0.1:4000",
    "http://10.0.2.2:4000",  # Android emulator localhost
    "https://vila-app-back.vercel.app",
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

def test_api_connectivity():
    """Test which API URL is accessible"""
    print_section("1. Testing API Connectivity")
    
    accessible_url = None
    
    for url in API_URLS:
        try:
            print(f"\nTesting: {url}")
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print_result(True, f"{url} is accessible")
                accessible_url = url
                print(f"   Response: {response.json()}")
                break
        except requests.exceptions.Timeout:
            print_result(False, f"{url} - Connection timeout")
        except requests.exceptions.ConnectionError:
            print_result(False, f"{url} - Connection refused")
        except Exception as e:
            print_result(False, f"{url} - Error: {str(e)}")
    
    if not accessible_url:
        print("\n⚠️  No API URLs are accessible!")
        print("   Make sure backend is running locally on port 4000")
        return None
    
    return accessible_url

def test_upload_video(api_url):
    """Test uploading a video file to storage"""
    print_section("2. Testing Video Upload to Storage")
    
    try:
        # Create a small test video file (simulating a video)
        # In reality, this would be a file:// URI from the device
        test_video_content = b"FAKE_VIDEO_CONTENT_" + b"x" * 1000  # Simulate video data
        
        url = f"{api_url}/api/storage/upload"
        print(f"Uploading test video to: {url}")
        
        files = {
            'file': ('test-video.mp4', test_video_content, 'video/mp4')
        }
        
        response = requests.post(url, files=files, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, "Video upload successful")
            print(f"   Response: {json.dumps(data, indent=2)}")
            video_url = data.get('url')
            return video_url
        else:
            print_result(False, f"Upload failed with status {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return None
    except requests.exceptions.Timeout:
        print_result(False, "Upload timeout")
        return None
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def get_or_create_test_task(api_url):
    """Get an existing task or create a test task"""
    print_section("3. Getting/Creating Test Task")
    
    try:
        # Try to get existing tasks
        url = f"{api_url}/api/maintenance/tasks"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            tasks = response.json()
            if tasks and len(tasks) > 0:
                task = tasks[0]
                print_result(True, f"Found existing task: {task.get('id', 'unknown')}")
                print(f"   Title: {task.get('title', 'N/A')}")
                print(f"   Status: {task.get('status', 'N/A')}")
                return task.get('id')
        
        # If no tasks, try to create one
        print("No existing tasks found, attempting to create test task...")
        create_url = f"{api_url}/api/maintenance/tasks"
        create_payload = {
            "unit_id": "1",  # Assuming unit 1 exists
            "title": "Test Task for Video Close",
            "description": "Test task created for video upload testing",
            "status": "פתוח",
        }
        
        create_response = requests.post(
            create_url,
            json=create_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if create_response.status_code in [200, 201]:
            task_data = create_response.json()
            task_id = task_data.get('id') or (task_data.get('tasks', [{}])[0] if isinstance(task_data.get('tasks'), list) else {}).get('id')
            if task_id:
                print_result(True, f"Created test task: {task_id}")
                return task_id
        
        print_result(False, "Could not get or create test task")
        return None
        
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_close_task_with_video(api_url, task_id, video_url):
    """Test closing a task with video URL"""
    print_section("4. Testing Close Task with Video")
    
    try:
        url = f"{api_url}/api/maintenance/tasks/{task_id}"
        print(f"Updating task: {url}")
        
        payload = {
            "status": "סגור",
            "imageUri": video_url  # The video URL from storage upload
        }
        
        print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        response = requests.patch(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code in [200, 204]:
            print_result(True, "Task closed successfully with video")
            if response.text:
                try:
                    data = response.json()
                    print(f"   Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                except:
                    print(f"   Response: {response.text[:200]}")
            return True
        else:
            print_result(False, f"Failed with status {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print_result(False, "Request timeout")
        return False
    except requests.exceptions.ConnectionError as e:
        print_result(False, f"Connection error: {str(e)}")
        print("\n   This is the error you're seeing in the app!")
        print("   The app cannot reach the backend.")
        return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_complete_flow(api_url):
    """Test the complete flow: upload video -> close task"""
    print_section("5. Complete Flow Test")
    
    # Step 1: Upload video
    video_url = test_upload_video(api_url)
    if not video_url:
        print("\n⚠️  Cannot proceed - video upload failed")
        return False
    
    # Step 2: Get or create task
    task_id = get_or_create_test_task(api_url)
    if not task_id:
        print("\n⚠️  Cannot proceed - no task available")
        return False
    
    # Step 3: Close task with video
    success = test_close_task_with_video(api_url, task_id, video_url)
    
    return success

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  CLOSE TASK WITH VIDEO - COMPLETE FLOW TEST")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Find accessible API
    api_url = test_api_connectivity()
    if not api_url:
        print("\n[ERROR] Cannot proceed - no backend is accessible")
        print("\nTroubleshooting:")
        print("  1. Make sure backend is running: cd back && python -m uvicorn app.main:app --port 4000")
        print("  2. Check if port 4000 is available")
        print("  3. Try accessing http://127.0.0.1:4000/health in browser")
        return 1
    
    print(f"\n✅ Using API: {api_url}")
    
    # Test 2: Complete flow
    success = test_complete_flow(api_url)
    
    # Summary
    print_section("TEST SUMMARY")
    
    if success:
        print_result(True, "Complete flow test PASSED")
        print("\n[SUCCESS] Closing task with video works!")
        print("\nIf app still fails:")
        print("  1. Check app is using correct API_BASE_URL")
        print("  2. Make sure backend is running on port 4000")
        print("  3. Check app console logs for specific error")
        return 0
    else:
        print_result(False, "Complete flow test FAILED")
        print("\n[ERROR] Found issues in the flow")
        print("\nCommon issues:")
        print("  1. Video upload fails -> Check storage buckets exist")
        print("  2. Task update fails -> Check task ID format")
        print("  3. Connection error -> Check backend is running")
        return 1

if __name__ == "__main__":
    sys.exit(main())




