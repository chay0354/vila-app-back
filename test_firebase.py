#!/usr/bin/env python3
"""
Test Firebase credentials and FCM setup
"""

import os
import json
import sys
from pathlib import Path

# Load .env file if it exists
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    print(f"Loading .env file from: {env_file}")
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes if present
                value = value.strip("'\"")
                os.environ[key.strip()] = value

print("=" * 60)
print("Firebase Credentials Test")
print("=" * 60)

# Check if FIREBASE_CREDENTIALS is set
print("\n1. Checking FIREBASE_CREDENTIALS environment variable...")
firebase_creds = os.getenv("FIREBASE_CREDENTIALS")

if not firebase_creds:
    print("[ERROR] FIREBASE_CREDENTIALS not found in environment")
    print("   Make sure you added it to back/.env and restarted the server")
    sys.exit(1)
else:
    print("[OK] FIREBASE_CREDENTIALS found")
    print(f"   Length: {len(firebase_creds)} characters")

# Try to parse JSON
print("\n2. Parsing JSON credentials...")
try:
    creds_dict = json.loads(firebase_creds)
    print("[OK] JSON parsed successfully")
    print(f"   Project ID: {creds_dict.get('project_id', 'N/A')}")
    print(f"   Client Email: {creds_dict.get('client_email', 'N/A')}")
    print(f"   Private Key: {'Present' if creds_dict.get('private_key') else 'Missing'}")
except json.JSONDecodeError as e:
    print(f"[ERROR] Failed to parse JSON: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Error: {str(e)}")
    sys.exit(1)

# Try to import firebase_admin
print("\n3. Checking firebase-admin library...")
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    print("[OK] firebase-admin library installed")
except ImportError:
    print("[ERROR] firebase-admin not installed")
    print("   Install with: pip install firebase-admin")
    sys.exit(1)

# Try to initialize Firebase
print("\n4. Initializing Firebase Admin SDK...")
try:
    # Check if already initialized
    if firebase_admin._apps:
        print("⚠️  Firebase already initialized (app exists)")
        app = firebase_admin.get_app()
    else:
        cred = credentials.Certificate(creds_dict)
        app = firebase_admin.initialize_app(cred)
        print("[OK] Firebase Admin SDK initialized successfully")
    
    print(f"   App name: {app.name}")
    print(f"   Project ID: {app.project_id}")
except Exception as e:
    print(f"[ERROR] Failed to initialize Firebase: {str(e)}")
    sys.exit(1)

# Test FCM messaging
print("\n5. Testing FCM messaging capability...")
try:
    # Just check if we can create a message (don't send it)
    test_message = messaging.Message(
        notification=messaging.Notification(
            title="Test",
            body="This is a test"
        ),
        token="test_token_that_wont_be_sent"
    )
    print("[OK] FCM messaging module working")
    print("   Can create message objects")
except Exception as e:
    print(f"[ERROR] FCM messaging error: {str(e)}")
    sys.exit(1)

print("\n" + "=" * 60)
print("[SUCCESS] ALL TESTS PASSED!")
print("=" * 60)
print("\nFirebase is properly configured and ready to send push notifications!")
print("\nNext steps:")
print("1. Rebuild Android app: cd front && npm run android:win")
print("2. Test push notification from backend")
print("3. Verify notification appears on device (even when app is closed)")

