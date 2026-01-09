#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detailed token inspection script
Shows what tokens are registered and why they might be failing
"""

import os
import sys
import requests
import json

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")
TEST_USERNAME = "test21"

def check_tokens():
    """Check tokens in detail"""
    print("=" * 70)
    print("  DETAILED TOKEN INSPECTION")
    print("=" * 70)
    print(f"Backend URL: {API_BASE_URL}")
    print(f"Username: {TEST_USERNAME}")
    print()
    
    try:
        # Try to send a notification to see what happens
        print("1. Testing push notification send...")
        payload = {
            "title": "Test Notification",
            "body": "Testing token validity",
            "username": TEST_USERNAME
        }
        
        response = requests.post(
            f"{API_BASE_URL}/push/send",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            sent_count = result.get("sent", 0)
            total_tokens = result.get("total_tokens", result.get("tokens", 0))
            message = result.get("message", "")
            
            print(f"   Total tokens: {total_tokens}")
            print(f"   Successfully sent: {sent_count}")
            print(f"   Message: {message}")
            print()
            
            if total_tokens == 0:
                print("❌ No tokens registered!")
                print("\n   Make sure:")
                print("   1. You signed in from the app")
                print("   2. You allowed notification permissions")
                print("   3. You waited a few seconds after signing in")
                print("   4. Check app console/logs for registration errors")
                return
            
            if sent_count == 0:
                print("⚠️  Tokens exist but are invalid/expired")
                print("\n   Possible reasons:")
                print("   1. Tokens are expired (Web Push subscriptions expire)")
                print("   2. FCM tokens are invalid (app reinstalled, token changed)")
                print("   3. Tokens are test tokens with invalid keys")
                print("\n   Solution:")
                print("   1. Sign in again from the app")
                print("   2. Make sure notification permissions are granted")
                print("   3. Wait for token registration to complete")
                print("   4. Check backend console for specific error messages")
            else:
                print(f"✅ SUCCESS! {sent_count} notification(s) sent successfully!")
                print("   Check your device(s) for the notification.")
                print("   If you see it, push notifications are working!")
        else:
            print(f"❌ Failed to test: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_tokens()












