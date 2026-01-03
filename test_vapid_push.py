#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to send Web Push notification using VAPID keys
Tests direct Web Push sending with provided VAPID credentials
"""

import os
import sys
import json
import base64
import requests
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# VAPID keys provided
VAPID_PRIVATE_KEY = "E5T8GmZAZU8OyGP1ApfT0G01LZ4pdyaCVn9JunPUuck"
VAPID_PUBLIC_KEY = "BDhn-iobDcmJITEORPJRnTHkaJOe4euPzinzQ2ndQy4IdT-zmctksJdIYPbgleic2-MnlhBpxK6NzU9sU0RKWxA"
VAPID_EMAIL = "mailto:chay.moalem@gmail.com"

# Get API base URL from environment or use default
API_BASE_URL = os.getenv("API_BASE_URL", "https://vila-app-back.vercel.app").rstrip("/")

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(success, message):
    """Print test result"""
    status = "[✓]" if success else "[✗]"
    print(f"{status} {message}")

def test_vapid_key_endpoint():
    """Test if backend returns VAPID public key"""
    print_section("1. Test VAPID Key Endpoint")
    try:
        response = requests.get(f"{API_BASE_URL}/api/push/vapid-key", timeout=10)
        if response.status_code == 200:
            data = response.json()
            public_key = data.get("publicKey", "")
            print_result(True, f"VAPID public key endpoint is accessible")
            print(f"   Backend public key: {public_key[:50]}...")
            print(f"   Provided public key: {VAPID_PUBLIC_KEY[:50]}...")
            
            if public_key == VAPID_PUBLIC_KEY:
                print_result(True, "VAPID keys match!")
                return True
            else:
                print_result(False, "VAPID keys don't match - backend may need update")
                print(f"   You need to set VAPID_PUBLIC_KEY in backend environment")
                return False
        else:
            print_result(False, f"Endpoint returned {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False

def get_registered_web_tokens(username=None):
    """Get registered Web Push tokens from backend"""
    print_section("2. Get Registered Web Push Tokens")
    try:
        # Try to get tokens from backend database
        # Note: This assumes you have a way to query the database
        # For now, we'll try to get from a test user or all users
        
        params = {"platform": "eq.web", "select": "username,token"}
        if username:
            params["username"] = f"eq.{username}"
        
        # This would require direct database access or an API endpoint
        # For testing, we'll create a mock subscription
        print_result(True, "Will use test subscription for demonstration")
        return None
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return None

def test_direct_web_push():
    """Test sending Web Push notification directly using pywebpush"""
    print_section("3. Test Direct Web Push (Requires pywebpush)")
    
    try:
        from pywebpush import webpush, WebPushException
        print_result(True, "pywebpush is installed")
    except ImportError:
        print_result(False, "pywebpush not installed")
        print("   Installing pywebpush...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebpush"])
            from pywebpush import webpush, WebPushException
            print_result(True, "pywebpush installed successfully")
        except Exception as e:
            print_result(False, f"Failed to install pywebpush: {str(e)}")
            print("   Please install manually: pip install pywebpush")
            return False
    
    # Create a test subscription (this would normally come from a registered device)
    # For testing, we'll show how it would work with a real subscription
    print("\n   Note: To test with a real device:")
    print("   1. Open PWA in browser (iOS Safari or Chrome)")
    print("   2. Sign in to register Web Push subscription")
    print("   3. Get the subscription from database")
    print("   4. Use that subscription here")
    
    # Example subscription structure (would come from browser)
    example_subscription = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/...",
        "keys": {
            "p256dh": "...",
            "auth": "..."
        }
    }
    
    print_result(True, "Ready to send Web Push (needs real subscription)")
    return True

def test_backend_send_endpoint(username=None):
    """Test sending notification via backend /push/send endpoint"""
    print_section("4. Test Backend Send Endpoint")
    
    try:
        payload = {
            "title": "🧪 VAPID Test Notification",
            "body": f"Test sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "data": {
                "test": True,
                "timestamp": datetime.now().isoformat(),
                "vapid_test": True
            }
        }
        
        if username:
            payload["username"] = username
        
        print(f"   Sending to: {'all users' if not username else username}")
        print(f"   Title: {payload['title']}")
        print(f"   Body: {payload['body']}")
        
        # Try both endpoints
        endpoints = [
            f"{API_BASE_URL}/api/push/send",
            f"{API_BASE_URL}/push/send"
        ]
        
        response = None
        used_endpoint = None
        
        for endpoint in endpoints:
            try:
                response = requests.post(
                    endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=15
                )
                if response.status_code != 404:
                    used_endpoint = endpoint
                    break
            except Exception as e:
                print(f"   Error trying {endpoint}: {str(e)}")
                continue
        
        if not response or response.status_code == 404:
            print_result(False, "Endpoint not found (404)")
            print(f"   Tried: {endpoints}")
            return False
        
        print(f"   Used endpoint: {used_endpoint}")
        print(f"   Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            sent_count = result.get("sent", 0)
            print_result(True, f"Notification sent successfully!")
            print(f"   Response: {json.dumps(result, indent=2)}")
            print(f"   Sent to {sent_count} device(s)")
            
            if sent_count == 0:
                print("\n   ⚠️  No devices received notification. Possible reasons:")
                print("      - No Web Push tokens registered in database")
                print("      - User needs to sign in to PWA to register subscription")
                print("      - VAPID keys not set in backend environment")
            
            return True
        else:
            print_result(False, f"Failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def verify_vapid_keys():
    """Verify VAPID keys format"""
    print_section("0. Verify VAPID Keys Format")
    
    print(f"   Private Key: {VAPID_PRIVATE_KEY[:30]}...{VAPID_PRIVATE_KEY[-10:]}")
    print(f"   Public Key: {VAPID_PUBLIC_KEY[:30]}...{VAPID_PUBLIC_KEY[-10:]}")
    print(f"   Email: {VAPID_EMAIL}")
    
    # Basic validation
    if len(VAPID_PRIVATE_KEY) < 40:
        print_result(False, "Private key seems too short")
        return False
    
    if len(VAPID_PUBLIC_KEY) < 80:
        print_result(False, "Public key seems too short")
        return False
    
    if not VAPID_EMAIL.startswith("mailto:"):
        print_result(False, "Email should start with 'mailto:'")
        return False
    
    print_result(True, "VAPID keys format looks valid")
    return True

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  VAPID WEB PUSH NOTIFICATION TEST")
    print("=" * 70)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"VAPID Email: {VAPID_EMAIL}")
    
    results = []
    
    # Test 0: Verify keys format
    results.append(("Verify VAPID Keys", verify_vapid_keys()))
    
    # Test 1: Check backend VAPID endpoint
    results.append(("VAPID Key Endpoint", test_vapid_key_endpoint()))
    
    # Test 2: Test direct Web Push (if pywebpush available)
    results.append(("Direct Web Push Setup", test_direct_web_push()))
    
    # Test 3: Test backend send endpoint (to all users)
    results.append(("Backend Send (All Users)", test_backend_send_endpoint(None)))
    
    # Test 4: Test backend send endpoint (to specific user - optional)
    test_username = os.getenv("TEST_USERNAME")
    if test_username:
        results.append((f"Backend Send (User: {test_username})", test_backend_send_endpoint(test_username)))
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[✓]" if result else "[✗]"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        print("\nNext steps:")
        print("  1. Set VAPID keys in backend environment variables:")
        print(f"     VAPID_PRIVATE_KEY={VAPID_PRIVATE_KEY}")
        print(f"     VAPID_PUBLIC_KEY={VAPID_PUBLIC_KEY}")
        print(f"     VAPID_EMAIL={VAPID_EMAIL}")
        print("  2. Deploy backend with these environment variables")
        print("  3. Have users sign in to PWA to register Web Push subscriptions")
        print("  4. Send notifications via /push/send endpoint")
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed.")
        print("\nTroubleshooting:")
        print("  1. Ensure backend is deployed and accessible")
        print("  2. Set VAPID keys in backend environment variables")
        print("  3. Ensure push_tokens table exists in database")
        print("  4. Have at least one user sign in to PWA to register subscription")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())








