#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick push notification test - run this after app registers real tokens
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

def main():
    print("=" * 70)
    print("  QUICK PUSH NOTIFICATION TEST")
    print("=" * 70)
    print(f"Testing: {TEST_USERNAME}")
    print()
    
    try:
        payload = {
            "title": "🧪 Test Notification",
            "body": f"Test at {datetime.now().strftime('%H:%M:%S')}",
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
            total = result.get("total_tokens", result.get("tokens", 0))
            sent = result.get("sent", 0)
            
            print(f"Total tokens: {total}")
            print(f"Sent to: {sent}")
            print()
            
            if sent > 0:
                print("✅ SUCCESS! Push notifications are working!")
                print(f"   {sent} notification(s) sent successfully")
            elif total > 0:
                print("⚠️  Tokens exist but failed to send")
                print("   Check backend console for error details")
            else:
                print("❌ No tokens registered")
                print("   Sign in from the app to register tokens")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()












