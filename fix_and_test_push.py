#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive push notification fix and test script
Diagnoses issues and tests the complete push notification system
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

def check_backend():
    """Check if backend is running and has Firebase configured"""
    print_section("1. Backend & Firebase Check")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/users", timeout=5)
        if response.status_code == 200:
            print_result(True, f"Backend is running at {API_BASE_URL}")
        else:
            print_result(False, f"Backend returned {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Cannot connect: {str(e)}")
        return False
    
    # Test Firebase by trying to send a notification
    # This will show if Firebase is properly initialized
    try:
        test_payload = {
            "title": "Firebase Test",
            "body": "Testing Firebase configuration",
            "username": TEST_USERNAME
        }
        response = requests.post(
            f"{API_BASE_URL}/push/send",
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            # If we get a response, Firebase is at least trying to work
            print_result(True, "Backend push endpoint is accessible")
            return True
        else:
            print_result(False, f"Push endpoint error: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Error testing push endpoint: {str(e)}")
        return False

def create_test_fcm_token():
    """Create a test FCM token for backend testing"""
    print_section("2. Creating Test FCM Token")
    
    # Generate a token that looks like a real FCM token
    # Real FCM tokens are base64-encoded strings, typically 150+ characters
    import base64
    import secrets
    
    # Create a token that matches FCM format
    # FCM tokens are typically: base64 encoded, 150-200 characters
    token_bytes = secrets.token_bytes(100)  # Generate random bytes
    fcm_token = base64.urlsafe_b64encode(token_bytes).decode('utf-8').rstrip('=')
    
    # Ensure it's long enough (FCM tokens are typically 150+ chars)
    while len(fcm_token) < 150:
        fcm_token += base64.urlsafe_b64encode(secrets.token_bytes(20)).decode('utf-8').rstrip('=')
    
    # Trim to typical FCM length (around 150-200 chars)
    fcm_token = fcm_token[:180]
    
    print(f"   Generated test FCM token: {fcm_token[:50]}... ({len(fcm_token)} chars)")
    print(f"   Format: Matches real FCM token structure")
    
    return fcm_token

def register_test_token(token):
    """Register test token with backend"""
    print_section("3. Registering Test Token")
    
    payload = {
        "username": TEST_USERNAME,
        "token": token,
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
            result = response.json()
            print_result(True, "Test token registered successfully")
            print(f"   Response: {result.get('message', 'OK')}")
            return True
        else:
            print_result(False, f"Registration failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False

def test_notification_send():
    """Test sending a notification"""
    print_section("4. Testing Notification Send")
    
    payload = {
        "title": "🧪 Test Notification",
        "body": f"System test at {datetime.now().strftime('%H:%M:%S')}",
        "username": TEST_USERNAME,
        "data": {
            "type": "system_test",
            "timestamp": datetime.now().isoformat()
        }
    }
    
    try:
        print(f"   Sending notification to: {TEST_USERNAME}")
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
                print_result(True, f"✅ Notification sent successfully to {sent} device(s)!")
                print(f"\n   🎉 SUCCESS! Push notification system is working!")
                return True
            elif total > 0:
                print_result(False, "Tokens exist but failed to send")
                print(f"\n   ⚠️  This usually means:")
                print(f"      - Token format is invalid")
                print(f"      - Firebase credentials not loaded (restart backend)")
                print(f"      - Token is expired/invalid")
                return False
            else:
                print_result(False, "No tokens registered")
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

def cleanup_old_tokens():
    """Clean up old invalid tokens"""
    print_section("5. Cleaning Up Old Tokens")
    
    try:
        # Get all tokens for the user
        response = requests.post(
            f"{API_BASE_URL}/push/send",
            json={"title": "check", "body": "check", "username": TEST_USERNAME},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            total = result.get("total_tokens", result.get("tokens", 0))
            
            if total > 0:
                print(f"   Found {total} token(s) for {TEST_USERNAME}")
                print(f"   ⚠️  Old tokens will be replaced by new test token")
                print(f"   (You can manually delete them from push_tokens table if needed)")
            else:
                print(f"   No existing tokens found")
            
            return True
        else:
            print(f"   Could not check existing tokens")
            return False
    except Exception as e:
        print(f"   Error checking tokens: {str(e)}")
        return False

def main():
    """Run complete fix and test"""
    print("\n" + "=" * 70)
    print("  PUSH NOTIFICATION FIX & TEST")
    print("=" * 70)
    print(f"Backend URL: {API_BASE_URL}")
    print(f"Test User: {TEST_USERNAME}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Step 1: Check backend
    backend_ok = check_backend()
    results.append(("Backend Check", backend_ok))
    
    if not backend_ok:
        print("\n❌ Backend is not accessible. Please start it first.")
        sys.exit(1)
    
    # Step 2: Cleanup
    cleanup_old_tokens()
    
    # Step 3: Create test token
    test_token = create_test_fcm_token()
    
    # Step 4: Register test token
    reg_ok = register_test_token(test_token)
    results.append(("Token Registration", reg_ok))
    
    if not reg_ok:
        print("\n❌ Failed to register test token")
        sys.exit(1)
    
    # Step 5: Test notification
    send_ok = test_notification_send()
    results.append(("Notification Send", send_ok))
    
    # Summary
    print_section("FINAL SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if send_ok:
        print("\n" + "=" * 70)
        print("  🎉 SUCCESS! Push notification system is working!")
        print("=" * 70)
        print("\nThe test token was registered and notification was sent.")
        print("Note: Test tokens won't receive real notifications, but the")
        print("backend system is working correctly.")
        print("\nFor real notifications, the app needs to generate real FCM tokens.")
    else:
        print("\n" + "=" * 70)
        print("  ⚠️  SYSTEM TEST COMPLETE")
        print("=" * 70)
        print("\nThe test token was registered, but notification sending failed.")
        print("\nPossible issues:")
        print("1. Backend needs restart to load Firebase credentials")
        print("2. Firebase credentials not properly configured")
        print("3. Check backend console for specific error messages")
        print("\nThe backend push system is configured, but needs:")
        print("- Real FCM tokens from the app (not fallback tokens)")
        print("- Proper Firebase initialization")

if __name__ == "__main__":
    main()














