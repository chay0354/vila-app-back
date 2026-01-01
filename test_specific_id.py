#!/usr/bin/env python3
"""Test push notification for a specific ID"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

# Get Supabase URL from environment
SUPABASE_URL = os.getenv('SUPABASE_URL')
if not SUPABASE_URL:
    print("❌ SUPABASE_URL not found in .env file")
    sys.exit(1)

REST_URL = f"{SUPABASE_URL}/rest/v1"
SERVICE_HEADERS = {
    'apikey': os.getenv('SUPABASE_SERVICE_ROLE_KEY'),
    'Authorization': f'Bearer {os.getenv("SUPABASE_SERVICE_ROLE_KEY")}'
}
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")

TARGET_ID = "4d6a489e-7e38-4829-a931-7800e2dc5f58"

def main():
    print("=" * 70)
    print("  TESTING PUSH NOTIFICATION FOR ID")
    print("=" * 70)
    print(f"Target ID: {TARGET_ID}")
    print()
    
    # First, check if this is a push token ID
    try:
        resp = requests.get(
            f'{REST_URL}/push_tokens',
            headers=SERVICE_HEADERS,
            params={'id': f'eq.{TARGET_ID}'}
        )
        resp.raise_for_status()
        tokens = resp.json()
        
        if tokens:
            token_data = tokens[0]
            username = token_data.get('username', 'unknown')
            platform = token_data.get('platform', 'unknown')
            token_val = token_data.get('token', '')
            
            print(f"✅ Found push token!")
            print(f"   Username: {username}")
            print(f"   Platform: {platform}")
            print(f"   Token type: {'Real Web Push' if token_val.startswith('{') and 'endpoint' in token_val else 'Fallback'}")
            print()
            
            # Send notification to this username
            print(f"Sending push notification to: {username}")
            payload = {
                "title": "Test Notification",
                "body": f"Testing push notification for ID {TARGET_ID}",
                "username": username
            }
            
            response = requests.post(
                f"{API_BASE_URL}/push/send",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Notification sent!")
                print(f"   Sent to: {result.get('sent', 0)} device(s)")
                print(f"   Total tokens: {result.get('total_tokens', 0)}")
                print(f"   Message: {result.get('message', '')}")
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   {response.text}")
            return
    
    except Exception as e:
        print(f"Not a push token ID: {str(e)}")
    
    # Check if it's a user ID
    try:
        resp = requests.get(
            f'{REST_URL}/users',
            headers=SERVICE_HEADERS,
            params={'id': f'eq.{TARGET_ID}', 'select': 'username'}
        )
        resp.raise_for_status()
        users = resp.json()
        
        if users:
            username = users[0].get('username', 'unknown')
            print(f"✅ Found user!")
            print(f"   Username: {username}")
            print()
            
            # Send notification to this username
            print(f"Sending push notification to: {username}")
            payload = {
                "title": "Test Notification",
                "body": f"Testing push notification for user ID {TARGET_ID}",
                "username": username
            }
            
            response = requests.post(
                f"{API_BASE_URL}/push/send",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Notification sent!")
                print(f"   Sent to: {result.get('sent', 0)} device(s)")
                print(f"   Total tokens: {result.get('total_tokens', 0)}")
                print(f"   Message: {result.get('message', '')}")
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   {response.text}")
            return
    
    except Exception as e:
        print(f"Not a user ID: {str(e)}")
    
    print(f"❌ ID {TARGET_ID} not found in push_tokens or users table")
    print("   Please check the ID and try again")

if __name__ == "__main__":
    main()

