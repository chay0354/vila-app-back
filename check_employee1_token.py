#!/usr/bin/env python3
"""Check the latest push token for employee1"""

import requests
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

REST_URL = os.getenv('REST_URL')
SERVICE_HEADERS = {
    'apikey': os.getenv('SUPABASE_SERVICE_ROLE_KEY'),
    'Authorization': f'Bearer {os.getenv("SUPABASE_SERVICE_ROLE_KEY")}'
}

# Get latest token for employee1
resp = requests.get(
    f'{REST_URL}/push_tokens',
    headers=SERVICE_HEADERS,
    params={
        'username': 'eq.employee1',
        'order': 'created_at.desc',
        'limit': '1'
    }
)
resp.raise_for_status()
tokens = resp.json()

if not tokens:
    print("❌ No tokens found for employee1")
    exit(1)

token_data = tokens[0]
token_val = token_data.get('token', '')

print("=" * 60)
print("Latest token for employee1:")
print("=" * 60)
print(json.dumps(token_data, indent=2))
print()

# Check if it's a real Web Push subscription
if token_val.startswith('{') and '"endpoint"' in token_val:
    print("✅ REAL Web Push subscription!")
    print("   This will work for push notifications")
    try:
        sub_data = json.loads(token_val)
        endpoint = sub_data.get('endpoint', '')
        print(f"   Endpoint: {endpoint[:60]}...")
        if 'keys' in sub_data:
            print("   Keys: ✅ Present (p256dh, auth)")
    except:
        pass
elif token_val.startswith('web-'):
    print("❌ FALLBACK token (NOT WORKING)")
    print("   This is a dummy token - push notifications will NOT work")
    print("   Web Push subscription failed - check browser console for errors")
else:
    print("⚠️  Unknown token format")
    print(f"   Token: {token_val[:100]}...")

