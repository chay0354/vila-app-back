#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify push notifications work for test21 user
Tests if notifications can be sent even when app is closed
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

# Get API base URL from environment or use default local
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")
TEST_USERNAME = "test21"
TEST_PASSWORD = "123456"

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(success, message):
    """Print test result"""
    status = "✅" if success else "❌"
    print(f"{status} {message}")

def test_backend_health():
    """Test if backend is running"""
    print_section("1. Backend Health Check")
    try:
        # Try to get users endpoint as health check
        response = requests.get(f"{API_BASE_URL}/api/users", timeout=5)
        if response.status_code == 200:
            print_result(True, f"Backend is running at {API_BASE_URL}")
            return True
        else:
            print_result(False, f"Backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_result(False, f"Cannot connect to backend at {API_BASE_URL}")
        print(f"   Make sure the backend is running!")
        return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False

def test_user_signin():
    """Test signing in as test21"""
    print_section("2. User Sign-In Test")
    try:
        payload = {
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/auth/login",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            user_data = response.json()
            print_result(True, f"Successfully signed in as {TEST_USERNAME}")
            print(f"   User ID: {user_data.get('id', 'N/A')}")
            print(f"   Role: {user_data.get('role', 'N/A')}")
            return True
        elif response.status_code == 401:
            print_result(False, f"Invalid credentials for {TEST_USERNAME}")
            print(f"   Response: {response.text}")
            return False
        else:
            print_result(False, f"Sign-in failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Exception during sign-in: {str(e)}")
        return False

def check_existing_tokens():
    """Check if test21 has any registered push tokens"""
    print_section("3. Check Existing Push Tokens")
    try:
        # Try to get tokens via a test send (it will tell us if tokens exist)
        payload = {
            "title": "Test - Checking Tokens",
            "body": "This is just a check",
            "username": TEST_USERNAME
        }
        
        response = requests.post(
            f"{API_BASE_URL}/push/send",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            sent_count = result.get("sent", 0)
            message = result.get("message", "")
            total_tokens = result.get("total_tokens", result.get("tokens", 0))
            
            print(f"   Total tokens registered: {total_tokens}")
            print(f"   Successfully sent to: {sent_count} device(s)")
            print(f"   Message: {message}")
            
            if total_tokens > 0 and sent_count == 0:
                print_result(False, f"Found {total_tokens} token(s) but all are INVALID or EXPIRED")
                print(f"\n   ⚠️  TOKEN ISSUES DETECTED:")
                print(f"   - Tokens may be expired (Web Push subscriptions expire)")
                print(f"   - FCM tokens may be invalid (app reinstalled, token refreshed)")
                print(f"   - Tokens need to be refreshed by signing in again")
                print(f"\n   ✅ SOLUTION: Sign in again from the app to refresh tokens")
                print(f"   Steps:")
                print(f"   1. Open the app (PWA or React Native)")
                print(f"   2. Sign in as {TEST_USERNAME} / {TEST_PASSWORD}")
                print(f"   3. Allow notification permissions when prompted")
                print(f"   4. Wait a few seconds for token registration")
                print(f"   5. Close the app completely")
                print(f"   6. Run this test again")
                return False
            elif sent_count > 0:
                print_result(True, f"Found {sent_count} valid push token(s) for {TEST_USERNAME}")
                return True
            else:
                print_result(False, f"No push tokens found for {TEST_USERNAME}")
                print(f"\n   ⚠️  IMPORTANT: User must sign in from the app first!")
                print(f"   The app automatically registers push tokens when signing in.")
                print(f"   Steps:")
                print(f"   1. Open the app (PWA or React Native)")
                print(f"   2. Sign in as {TEST_USERNAME} / {TEST_PASSWORD}")
                print(f"   3. Allow notification permissions when prompted")
                print(f"   4. Wait a few seconds for token registration")
                print(f"   5. Close the app completely")
                print(f"   6. Run this test again")
                return False
        else:
            print_result(False, f"Failed to check tokens: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Exception checking tokens: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def send_test_notification():
    """Send a test push notification to test21"""
    print_section("4. Send Test Push Notification")
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        payload = {
            "title": "🧪 Test Notification",
            "body": f"This is a test notification sent at {timestamp}. If you see this, push notifications work even when the app is closed!",
            "username": TEST_USERNAME,
            "data": {
                "type": "test",
                "timestamp": datetime.now().isoformat(),
                "test": True
            }
        }
        
        print(f"   Sending notification to: {TEST_USERNAME}")
        print(f"   Title: {payload['title']}")
        print(f"   Body: {payload['body']}")
        
        response = requests.post(
            f"{API_BASE_URL}/push/send",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30  # Longer timeout for push sending
        )
        
        if response.status_code == 200:
            result = response.json()
            sent_count = result.get("sent", 0)
            message = result.get("message", "")
            
            if sent_count > 0:
                print_result(True, f"Notification sent successfully!")
                print(f"   Sent to: {sent_count} device(s)")
                print(f"   Message: {message}")
                print(f"\n   ✅ SUCCESS! Check your device(s) for the notification.")
                print(f"   The notification should appear even if the app is closed.")
                return True
            else:
                print_result(False, f"Notification was not sent")
                print(f"   Message: {message}")
                print(f"\n   ⚠️  No push tokens found for {TEST_USERNAME}")
                print(f"   Make sure:")
                print(f"   1. User has signed in from the app")
                print(f"   2. Notification permissions were granted")
                print(f"   3. Push token was registered")
                return False
        else:
            print_result(False, f"Failed to send notification: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Exception sending notification: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  PUSH NOTIFICATION TEST - test21 User")
    print("=" * 70)
    print(f"Backend URL: {API_BASE_URL}")
    print(f"Test User: {TEST_USERNAME}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Test 1: Backend health
    health_ok = test_backend_health()
    results.append(("Backend Health", health_ok))
    
    if not health_ok:
        print("\n❌ Backend is not accessible. Please start the backend server first.")
        print(f"   Run: cd back && python run_server.py")
        sys.exit(1)
    
    # Test 2: User sign-in
    signin_ok = test_user_signin()
    results.append(("User Sign-In", signin_ok))
    
    if not signin_ok:
        print("\n❌ Cannot sign in. Please check credentials.")
        sys.exit(1)
    
    # Test 3: Check existing tokens
    tokens_exist = check_existing_tokens()
    results.append(("Push Tokens Registered", tokens_exist))
    
    # Test 4: Send test notification
    if tokens_exist:
        notification_sent = send_test_notification()
        results.append(("Send Notification", notification_sent))
    else:
        print("\n⚠️  Skipping notification test - no tokens found")
        results.append(("Send Notification", False))
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 SUCCESS! All tests passed!")
        print("   Push notifications are working correctly.")
        print("   Notifications should arrive even when the app is closed.")
    elif tokens_exist and notification_sent:
        print("\n✅ Push notification sent successfully!")
        print("   Check your device(s) for the notification.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        if not tokens_exist:
            print("\n   ACTION REQUIRED:")
            print("   1. Open the app (PWA or React Native)")
            print(f"   2. Sign in as {TEST_USERNAME} / {TEST_PASSWORD}")
            print("   3. Allow notification permissions")
            print("   4. Close the app completely")
            print("   5. Run this test again")

if __name__ == "__main__":
    main()

