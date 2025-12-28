#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for push notification endpoints
Tests registration and sending of push notifications
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

# Get API base URL from environment or use default
API_BASE_URL = os.getenv("API_BASE_URL", "https://vila-app-back.vercel.app").rstrip("/")

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_result(success, message):
    """Print test result"""
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status}: {message}")

def test_health_check():
    """Test if the API is accessible"""
    print_section("1. Health Check")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print_result(True, f"API is accessible at {API_BASE_URL}")
            print(f"   Response: {response.json()}")
            return True
        else:
            print_result(False, f"API returned status {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Failed to connect to API: {str(e)}")
        return False

def test_register_token(username="test_user", platform="android"):
    """Test push token registration"""
    print_section(f"2. Register Push Token ({platform})")
    try:
        token = f"test-token-{platform}-{datetime.now().timestamp()}"
        payload = {
            "username": username,
            "token": token,
            "platform": platform
        }
        
        # Try both /api/push/register and /push/register
        endpoints = [f"{API_BASE_URL}/api/push/register", f"{API_BASE_URL}/push/register"]
        response = None
        
        for endpoint in endpoints:
            try:
                response = requests.post(
                    endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                if response.status_code != 404:
                    print(f"   Using endpoint: {endpoint}")
                    break
            except:
                continue
        
        if not response or response.status_code == 404:
            print_result(False, f"Endpoint not found (404)")
            print(f"   Tried: {endpoints}")
            print(f"   NOTE: Backend may need to be deployed with new push endpoints")
            print(f"   NOTE: Database tables (push_tokens) may need to be created")
            return None
        
        if response.status_code == 200:
            result = response.json()
            print_result(True, f"Token registered successfully")
            print(f"   Response: {result}")
            return token
        else:
            print_result(False, f"Registration failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print_result(False, f"Exception during registration: {str(e)}")
        return None

def test_send_notification(username=None):
    """Test sending a push notification"""
    print_section(f"3. Send Push Notification {'(to all users)' if username is None else f'(to {username})'}")
    try:
        payload = {
            "title": "Test Notification",
            "body": f"This is a test notification sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "data": {
                "test": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        if username:
            payload["username"] = username
        
        # Try both /api/push/send and /push/send
        endpoints = [f"{API_BASE_URL}/api/push/send", f"{API_BASE_URL}/push/send"]
        response = None
        
        for endpoint in endpoints:
            try:
                response = requests.post(
                    endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                if response.status_code != 404:
                    print(f"   Using endpoint: {endpoint}")
                    break
            except:
                continue
        
        if not response or response.status_code == 404:
            print_result(False, f"Endpoint not found (404)")
            print(f"   Tried: {endpoints}")
            print(f"   NOTE: Backend may need to be deployed with new push endpoints")
            return False
        
        if response.status_code == 200:
            result = response.json()
            print_result(True, f"Notification sent successfully")
            print(f"   Response: {result}")
            print(f"   Sent to {result.get('sent', 0)} device(s)")
            return True
        else:
            print_result(False, f"Sending failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Exception during sending: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  PUSH NOTIFICATION TEST SUITE")
    print("=" * 60)
    print(f"Testing API at: {API_BASE_URL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Test 1: Health check
    results.append(("Health Check", test_health_check()))
    
    if not results[0][1]:
        print("\n[ERROR] API is not accessible. Please check the API_BASE_URL.")
        print("   You can set it with: export API_BASE_URL='your-api-url'")
        sys.exit(1)
    
    # Test 2: Register Android token
    android_token = test_register_token("test_user", "android")
    results.append(("Register Android Token", android_token is not None))
    
    # Test 3: Register iOS token
    ios_token = test_register_token("test_user", "ios")
    results.append(("Register iOS Token", ios_token is not None))
    
    # Test 4: Register Web token
    web_token = test_register_token("test_user", "web")
    results.append(("Register Web Token", web_token is not None))
    
    # Test 5: Send notification to specific user
    results.append(("Send Notification (Specific User)", test_send_notification("test_user")))
    
    # Test 6: Send notification to all users
    results.append(("Send Notification (All Users)", test_send_notification(None)))
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed! Push notification system is working.")
        sys.exit(0)
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed. Please check the errors above.")
        if passed == 1:
            print("\nNOTE: The endpoints are returning 404, which means:")
            print("  1. Backend needs to be deployed with the new push endpoints")
            print("  2. Database tables (push_tokens) need to be created")
            print("  3. Run: back/create_push_tables.sql in your Supabase database")
        sys.exit(1)

if __name__ == "__main__":
    main()
