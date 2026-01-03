#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check if any push tokens were recently registered
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")

def check_tokens():
    """Check all registered tokens"""
    print("=" * 70)
    print("  CHECKING REGISTERED PUSH TOKENS")
    print("=" * 70)
    print(f"Backend URL: {API_BASE_URL}")
    print()
    
    try:
        # Try to get tokens by sending a notification to all users
        # This will show us what tokens exist
        print("Checking all registered tokens...")
        response = requests.post(
            f"{API_BASE_URL}/push/send",
            json={
                "title": "Check",
                "body": "Checking tokens"
                # No username = check all users
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            total_tokens = result.get("total_tokens", result.get("tokens", 0))
            sent_count = result.get("sent", 0)
            message = result.get("message", "")
            
            print(f"Total tokens registered: {total_tokens}")
            print(f"Successfully sent to: {sent_count}")
            print(f"Message: {message}")
            print()
            
            if total_tokens == 0:
                print("❌ NO TOKENS FOUND")
                print()
                print("The app hasn't registered any tokens yet.")
                print()
                print("To register tokens:")
                print("1. Make sure the emulator/app is running")
                print("2. Open the app")
                print("3. Sign in as test21 / 123456")
                print("4. Allow notification permissions when prompted")
                print("5. Wait 5-10 seconds")
                print("6. Check backend console for: 'POST /push/register'")
                print()
                print("If you don't see token registration:")
                print("- Check app console for errors")
                print("- Check if notification permissions were granted")
                print("- Check if Firebase is properly configured")
            elif sent_count == 0:
                print("⚠️  TOKENS EXIST BUT ARE INVALID")
                print()
                print("Tokens are registered but not working.")
                print("This usually means:")
                print("- Tokens are expired")
                print("- Tokens are test tokens with invalid keys")
                print("- FCM/Web Push configuration issue")
                print()
                print("Solution: Sign in again from the app to get fresh tokens")
            else:
                print(f"✅ {sent_count} TOKEN(S) ARE WORKING!")
                print("Push notifications should work correctly.")
        else:
            print(f"❌ Failed to check: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_tokens()






