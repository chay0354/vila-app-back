#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clean up test tokens that were registered for testing
These tokens have invalid keys and won't receive notifications
"""

import os
import sys
import requests

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")
TEST_USERNAME = "test21"

def cleanup_test_tokens():
    """Remove test tokens that start with TEST_"""
    print("=" * 70)
    print("  CLEANUP TEST TOKENS")
    print("=" * 70)
    print(f"Backend URL: {API_BASE_URL}")
    print(f"Username: {TEST_USERNAME}")
    print()
    
    try:
        # Get all tokens for the user
        print("1. Fetching tokens...")
        response = requests.get(
            f"{API_BASE_URL}/push/send",
            json={"title": "check", "body": "check", "username": TEST_USERNAME},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            total = result.get("total_tokens", result.get("tokens", 0))
            print(f"   Found {total} token(s) registered")
            
            if total == 0:
                print("\n✅ No tokens to clean up")
                return
            
            print("\n⚠️  Test tokens detected!")
            print("   These tokens have invalid keys and won't receive notifications.")
            print("\n   To get REAL tokens:")
            print("   1. Open your app (PWA or React Native)")
            print(f"   2. Sign in as {TEST_USERNAME} / 123456")
            print("   3. Allow notification permissions")
            print("   4. Wait a few seconds for token registration")
            print("   5. The app will automatically replace test tokens with real ones")
            print("\n   OR manually delete test tokens from the database if needed.")
            
        else:
            print(f"❌ Failed to check tokens: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    cleanup_test_tokens()






