#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive push notification system test
Tests backend configuration and push notification flow
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

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")
TEST_USERNAME = "test21"

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(success, message):
    status = "✅" if success else "❌"
    print(f"{status} {message}")

def test_backend():
    """Test if backend is running"""
    print_section("1. Backend Health Check")
    try:
        response = requests.get(f"{API_BASE_URL}/api/users", timeout=5)
        if response.status_code == 200:
            print_result(True, f"Backend is running at {API_BASE_URL}")
            return True
        else:
            print_result(False, f"Backend returned status {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Cannot connect: {str(e)}")
        return False

def test_firebase_config():
    """Test Firebase configuration"""
    print_section("2. Firebase Configuration Check")
    
    # Check environment variables
    firebase_creds = os.getenv("FIREBASE_CREDENTIALS")
    fcm_server_key = os.getenv("FCM_SERVER_KEY")
    
    if firebase_creds:
        try:
            creds_json = json.loads(firebase_creds)
            project_id = creds_json.get("project_id", "N/A")
            print_result(True, f"FIREBASE_CREDENTIALS found (project: {project_id})")
        except:
            print_result(False, "FIREBASE_CREDENTIALS exists but is invalid JSON")
    else:
        print_result(False, "FIREBASE_CREDENTIALS not found in environment")
    
    if fcm_server_key:
        print_result(True, f"FCM_SERVER_KEY found ({len(fcm_server_key)} chars)")
    else:
        print_result(False, "FCM_SERVER_KEY not found (optional, but recommended)")
    
    # Check if Firebase Admin SDK is available
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
        print_result(True, "Firebase Admin SDK is installed and importable")
        return True
    except ImportError:
        print_result(False, "Firebase Admin SDK not installed (pip install firebase-admin)")
        return False
    except Exception as e:
        print_result(False, f"Firebase Admin SDK error: {str(e)}")
        return False

def test_webpush_config():
    """Test Web Push configuration"""
    print_section("3. Web Push Configuration Check")
    
    vapid_private = os.getenv("VAPID_PRIVATE_KEY")
    vapid_public = os.getenv("VAPID_PUBLIC_KEY")
    vapid_email = os.getenv("VAPID_EMAIL")
    
    if vapid_private:
        print_result(True, f"VAPID_PRIVATE_KEY found ({len(vapid_private)} chars)")
    else:
        print_result(False, "VAPID_PRIVATE_KEY not found")
    
    if vapid_public:
        print_result(True, f"VAPID_PUBLIC_KEY found ({len(vapid_public)} chars)")
    else:
        print_result(False, "VAPID_PUBLIC_KEY not found")
    
    if vapid_email:
        print_result(True, f"VAPID_EMAIL found: {vapid_email}")
    else:
        print_result(False, "VAPID_EMAIL not found")
    
    # Check pywebpush
    try:
        from pywebpush import webpush
        print_result(True, "pywebpush is installed and importable")
        return True
    except ImportError:
        print_result(False, "pywebpush not installed (pip install pywebpush)")
        return False

def test_token_registration():
    """Test token registration endpoint"""
    print_section("4. Token Registration Endpoint Test")
    
    # Create a test token (simulated FCM token format)
    test_token = "d" + "K" * 150  # Simulated FCM token format (long string)
    
    payload = {
        "username": TEST_USERNAME,
        "token": test_token,
        "platform": "android"
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/push/register",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            print_result(True, "Token registration endpoint works")
            print(f"   Response: {response.json()}")
            return True
        else:
            print_result(False, f"Registration failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False

def test_notification_sending():
    """Test notification sending"""
    print_section("5. Notification Sending Test")
    
    payload = {
        "title": "🧪 System Test",
        "body": f"Backend push notification test at {datetime.now().strftime('%H:%M:%S')}",
        "username": TEST_USERNAME,
        "data": {"test": True, "timestamp": datetime.now().isoformat()}
    }
    
    try:
        print(f"   Sending test notification to: {TEST_USERNAME}")
        response = requests.post(
            f"{API_BASE_URL}/push/send",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            total = result.get("total_tokens", result.get("tokens", 0))
            sent = result.get("sent", 0)
            message = result.get("message", "")
            
            print(f"   Total tokens: {total}")
            print(f"   Sent to: {sent}")
            print(f"   Message: {message}")
            
            if sent > 0:
                print_result(True, f"Notification sent successfully to {sent} device(s)")
                return True
            elif total > 0:
                print_result(False, f"Tokens exist but notifications failed to send")
                print(f"   This usually means tokens are invalid/expired")
                return False
            else:
                print_result(False, "No tokens registered for this user")
                return False
        else:
            print_result(False, f"Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  PUSH NOTIFICATION SYSTEM TEST")
    print("=" * 70)
    print(f"Backend URL: {API_BASE_URL}")
    print(f"Test User: {TEST_USERNAME}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Test 1: Backend
    backend_ok = test_backend()
    results.append(("Backend", backend_ok))
    
    if not backend_ok:
        print("\n❌ Backend is not running. Please start it first.")
        sys.exit(1)
    
    # Test 2: Firebase
    firebase_ok = test_firebase_config()
    results.append(("Firebase Config", firebase_ok))
    
    # Test 3: Web Push
    webpush_ok = test_webpush_config()
    results.append(("Web Push Config", webpush_ok))
    
    # Test 4: Token Registration
    reg_ok = test_token_registration()
    results.append(("Token Registration", reg_ok))
    
    # Test 5: Notification Sending
    send_ok = test_notification_sending()
    results.append(("Notification Sending", send_ok))
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Push notification system is configured correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        print("\nNext steps:")
        if not firebase_ok:
            print("  - Install Firebase Admin SDK: pip install firebase-admin")
            print("  - Set FIREBASE_CREDENTIALS in .env file")
        if not webpush_ok:
            print("  - Install pywebpush: pip install pywebpush")
            print("  - Set VAPID keys in .env file")
        if not send_ok and reg_ok:
            print("  - Register real tokens from the app")
            print("  - Make sure app has proper Firebase configuration")

if __name__ == "__main__":
    main()











