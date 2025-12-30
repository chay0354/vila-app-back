#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script that simulates sign-in and tests push notifications for test21 user
Includes token registration simulation and actual push notification testing
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

def simulate_signin():
    """Simulate user sign-in"""
    print_section("2. Simulate User Sign-In")
    try:
        payload = {
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD
        }
        
        print(f"   Signing in as: {TEST_USERNAME}")
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
            print(f"   Username: {user_data.get('username', 'N/A')}")
            print(f"   Role: {user_data.get('role', 'N/A')}")
            return user_data
        elif response.status_code == 401:
            print_result(False, f"Invalid credentials for {TEST_USERNAME}")
            print(f"   Response: {response.text}")
            return None
        else:
            print_result(False, f"Sign-in failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print_result(False, f"Exception during sign-in: {str(e)}")
        return None

def register_test_token(username, platform="web", token=None):
    """Register a test push token for the user"""
    print_section(f"3. Register Test Push Token ({platform})")
    
    # Generate a test token if not provided
    if not token:
        if platform == "web":
            # Simulate a Web Push subscription JSON
            token = json.dumps({
                "endpoint": f"https://fcm.googleapis.com/fcm/send/TEST_TOKEN_{datetime.now().timestamp()}",
                "keys": {
                    "p256dh": "TEST_P256DH_KEY_" + "A" * 88,  # 88 chars for base64 URL-safe
                    "auth": "TEST_AUTH_KEY_" + "B" * 22  # 22 chars for base64 URL-safe
                }
            })
        elif platform == "android":
            token = f"TEST_FCM_TOKEN_{datetime.now().timestamp()}_{'C' * 100}"
        else:
            token = f"TEST_TOKEN_{platform}_{datetime.now().timestamp()}"
    
    try:
        payload = {
            "username": username,
            "token": token,
            "platform": platform
        }
        
        print(f"   Registering {platform} token for: {username}")
        print(f"   Token preview: {token[:100]}...")
        
        response = requests.post(
            f"{API_BASE_URL}/push/register",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print_result(True, f"Token registered successfully")
            print(f"   Response: {result.get('message', 'OK')}")
            return True
        else:
            print_result(False, f"Token registration failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Exception during token registration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_existing_tokens():
    """Check existing push tokens for the user"""
    print_section("4. Check Existing Push Tokens")
    try:
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
            
            if total_tokens > 0:
                if sent_count > 0:
                    print_result(True, f"Found {sent_count} valid push token(s)")
                    return True
                else:
                    print_result(False, f"Found {total_tokens} token(s) but all are INVALID or EXPIRED")
                    return False
            else:
                print_result(False, f"No push tokens found")
                return False
        else:
            print_result(False, f"Failed to check tokens: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Exception checking tokens: {str(e)}")
        return False

def send_test_notification():
    """Send a test push notification"""
    print_section("5. Send Test Push Notification")
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
            timeout=30
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

def show_instructions_for_real_tokens():
    """Show instructions for getting real tokens from the app"""
    print_section("📱 How to Get Real Push Tokens")
    print("""
To get REAL push tokens that actually work, you need to sign in from the actual app:

FOR PWA (Web Browser):
─────────────────────
1. Open the PWA in your browser (Chrome/Safari)
2. Navigate to: http://localhost:5173 (or your PWA URL)
3. Sign in as test21 / 123456
4. Allow notification permissions when prompted
5. The app will automatically register a Web Push token
6. Check browser console for: "Push subscription registered"

FOR REACT NATIVE ANDROID:
─────────────────────────
1. Open the React Native app on your Android device/emulator
2. Sign in as test21 / 123456
3. Allow notification permissions when prompted
4. The app will automatically register an FCM token
5. Check Metro bundler logs for: "FCM token registered"

VERIFY TOKEN REGISTRATION:
──────────────────────────
After signing in, run this script again to verify tokens are registered.

NOTE: Test tokens registered by this script won't actually receive notifications.
      They're only useful for testing the backend registration flow.
""")

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  PUSH NOTIFICATION TEST WITH SIGN-IN SIMULATION")
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
    
    # Test 2: Simulate sign-in
    user_data = simulate_signin()
    results.append(("User Sign-In", user_data is not None))
    
    if not user_data:
        print("\n❌ Cannot sign in. Please check credentials.")
        sys.exit(1)
    
    # Test 3: Check existing tokens
    tokens_exist = check_existing_tokens()
    results.append(("Existing Valid Tokens", tokens_exist))
    
    # Test 4: Register test tokens (for backend testing) - ONLY if no tokens exist at all
    if not tokens_exist:
        # Check if there are ANY tokens (even invalid ones)
        try:
            check_payload = {
                "title": "check",
                "body": "check",
                "username": TEST_USERNAME
            }
            check_response = requests.post(
                f"{API_BASE_URL}/push/send",
                json=check_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            if check_response.status_code == 200:
                check_result = check_response.json()
                total_tokens = check_result.get("total_tokens", check_result.get("tokens", 0))
                
                if total_tokens > 0:
                    print("\n⚠️  Found existing tokens (but they're invalid/expired)")
                    print("   These are likely expired tokens from previous sign-ins.")
                    print("   Solution: Sign in from the app to register fresh tokens.")
                    print("   The app will automatically replace old tokens with new ones.\n")
                    results.append(("Register Test Web Token", False))
                    results.append(("Register Test Android Token", False))
                else:
                    print("\n⚠️  No tokens found. Registering test tokens for backend testing...")
                    print("   NOTE: Test tokens won't actually receive notifications.")
                    print("   For real notifications, sign in from the actual app.\n")
                    
                    # Register test web token
                    web_ok = register_test_token(TEST_USERNAME, "web")
                    results.append(("Register Test Web Token", web_ok))
                    
                    # Register test android token
                    android_ok = register_test_token(TEST_USERNAME, "android")
                    results.append(("Register Test Android Token", android_ok))
                    
                    # Check tokens again
                    print("\n   Checking tokens after registration...")
                    tokens_exist = check_existing_tokens()
        except:
            # If check fails, skip test token registration
            results.append(("Register Test Web Token", False))
            results.append(("Register Test Android Token", False))
    
    # Test 5: Send test notification
    if tokens_exist:
        notification_sent = send_test_notification()
        results.append(("Send Notification", notification_sent))
    else:
        print("\n⚠️  Skipping notification test - no valid tokens")
        results.append(("Send Notification", False))
        show_instructions_for_real_tokens()
    
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
        if tokens_exist and notification_sent:
            print("   Push notifications are working correctly.")
            print("   Notifications should arrive even when the app is closed.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        if not tokens_exist:
            show_instructions_for_real_tokens()

if __name__ == "__main__":
    main()

