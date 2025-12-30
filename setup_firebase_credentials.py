#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup Firebase credentials from JSON file to .env file
"""

import os
import json
import sys
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def setup_firebase_credentials():
    """Setup Firebase credentials in .env file"""
    print("=" * 70)
    print("  SETUP FIREBASE CREDENTIALS")
    print("=" * 70)
    
    # Find Firebase credentials JSON file
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Look for Firebase credentials file
    cred_files = [
        project_root / "villa-app-7b5fc-c23b6d9476ba.json",
        script_dir / "villa-app-7b5fc-c23b6d9476ba.json",
        project_root / "firebase-credentials.json",
        script_dir / "firebase-credentials.json",
    ]
    
    cred_file = None
    for f in cred_files:
        if f.exists():
            cred_file = f
            break
    
    if not cred_file:
        print("❌ Firebase credentials JSON file not found!")
        print("   Looking for:")
        for f in cred_files:
            print(f"     - {f}")
        return False
    
    print(f"✅ Found credentials file: {cred_file}")
    
    # Read JSON file
    try:
        with open(cred_file, 'r', encoding='utf-8') as f:
            cred_data = json.load(f)
        print(f"✅ Loaded credentials for project: {cred_data.get('project_id', 'N/A')}")
    except Exception as e:
        print(f"❌ Error reading credentials file: {str(e)}")
        return False
    
    # Convert to single-line JSON string
    cred_json_str = json.dumps(cred_data)
    
    # Read or create .env file
    env_file = script_dir / ".env"
    
    # Read existing .env if it exists
    env_lines = []
    firebase_found = False
    
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()
        
        # Check if FIREBASE_CREDENTIALS already exists
        for i, line in enumerate(env_lines):
            if line.strip().startswith('FIREBASE_CREDENTIALS='):
                env_lines[i] = f'FIREBASE_CREDENTIALS={json.dumps(cred_data)}\n'
                firebase_found = True
                print("✅ Updated existing FIREBASE_CREDENTIALS in .env")
                break
    
    # Add if not found
    if not firebase_found:
        env_lines.append(f'\n# Firebase credentials for push notifications\n')
        env_lines.append(f'FIREBASE_CREDENTIALS={json.dumps(cred_data)}\n')
        print("✅ Added FIREBASE_CREDENTIALS to .env")
    
    # Write .env file
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(env_lines)
        print(f"✅ Saved to: {env_file}")
        return True
    except Exception as e:
        print(f"❌ Error writing .env file: {str(e)}")
        return False

def test_firebase():
    """Test Firebase initialization"""
    print("\n" + "=" * 70)
    print("  TESTING FIREBASE INITIALIZATION")
    print("=" * 70)
    
    # Load .env
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
        print(f"✅ Loaded .env from: {env_file}")
    else:
        print(f"❌ .env file not found: {env_file}")
        return False
    
    # Check credentials
    firebase_creds = os.getenv("FIREBASE_CREDENTIALS")
    if not firebase_creds:
        print("❌ FIREBASE_CREDENTIALS not found in environment")
        return False
    
    print("✅ FIREBASE_CREDENTIALS found in environment")
    
    # Test Firebase Admin SDK
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
        
        # Parse credentials
        cred_dict = json.loads(firebase_creds)
        cred = credentials.Certificate(cred_dict)
        
        # Initialize (only if not already initialized)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin initialized successfully")
        else:
            print("✅ Firebase Admin already initialized")
        
        print(f"✅ Project ID: {cred_dict.get('project_id', 'N/A')}")
        print(f"✅ Client Email: {cred_dict.get('client_email', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ Firebase initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n")
    
    # Setup credentials
    if setup_firebase_credentials():
        print("\n")
        # Test Firebase
        if test_firebase():
            print("\n" + "=" * 70)
            print("  ✅ SUCCESS! Firebase credentials are configured")
            print("=" * 70)
            print("\nNext steps:")
            print("1. Restart the backend server")
            print("2. Run: python test_push_system.py")
            print("3. Test push notifications")
        else:
            print("\n" + "=" * 70)
            print("  ⚠️  Credentials saved but initialization failed")
            print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("  ❌ Failed to setup Firebase credentials")
        print("=" * 70)

