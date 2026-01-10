#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Explanation script: How push notifications know which phone to send to
Shows the complete flow from registration to delivery
"""

import os
import sys
import requests
import json
import base64

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

API_BASE_URL = os.getenv("API_BASE_URL", "https://vila-app-back.vercel.app").rstrip("/")

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def explain_flow():
    """Explain the complete push notification flow"""
    print_section("📱 HOW PUSH NOTIFICATIONS KNOW WHICH PHONE TO SEND TO")
    
    print("""
┌─────────────────────────────────────────────────────────────────┐
│                    PUSH NOTIFICATION FLOW                         │
└─────────────────────────────────────────────────────────────────┘

STEP 1: USER SIGNS IN TO APP
─────────────────────────────
When a user signs in (PWA or React Native app):

  1. App requests push notification permission from device
  2. Device generates a UNIQUE PUSH TOKEN (like a phone number)
  
  For PWA (iOS/Android browser):
     → Browser creates Web Push subscription
     → Contains endpoint URL like: "https://fcm.googleapis.com/fcm/send/ABC123..."
     → This is the "address" where notifications go
  
  For React Native Android:
     → Firebase generates FCM token like: "dKj3hF8...xyz"
     → This is the "address" for that specific phone

STEP 2: TOKEN IS REGISTERED WITH BACKEND
─────────────────────────────────────────
The app sends to backend: /push/register

  {
    "username": "john_doe",        ← WHO this token belongs to
    "token": "https://fcm...ABC",  ← WHERE to send (the "phone number")
    "platform": "web"               ← WHAT type of device
  }

Backend stores in database (push_tokens table):
  
  ┌─────────────┬──────────────────────────────┬──────────┐
  │ username    │ token                        │ platform │
  ├─────────────┼──────────────────────────────┼──────────┤
  │ john_doe    │ https://fcm...ABC123         │ web      │
  │ john_doe    │ dKj3hF8...xyz                │ android  │
  │ jane_smith  │ https://fcm...XYZ789         │ web      │
  └─────────────┴──────────────────────────────┴──────────┘

STEP 3: SENDING A NOTIFICATION
───────────────────────────────
When you want to send a notification:

  POST /push/send
  {
    "title": "New message",
    "body": "You have a new task",
    "username": "john_doe"  ← WHO to send to (optional, if null = all users)
  }

Backend process:
  
  1. Looks up tokens by username in database:
     SELECT token, platform FROM push_tokens WHERE username = 'john_doe'
  
  2. Finds all tokens for that user:
     - web token: "https://fcm...ABC123"
     - android token: "dKj3hF8...xyz"
  
  3. Sends notification to EACH token:
     - Web Push → sends to "https://fcm...ABC123" endpoint
     - FCM → sends to "dKj3hF8...xyz" token
  
  4. Push service (Google/Apple) delivers to the actual phone

STEP 4: DELIVERY
────────────────
The push service (FCM for Android, APNs for iOS, Web Push for PWA):
  
  - Knows which physical device has that token
  - Delivers notification to that device
  - Shows notification even if app is closed

┌─────────────────────────────────────────────────────────────────┐
│                    KEY POINTS                                    │
└─────────────────────────────────────────────────────────────────┘

✓ Token = "Phone number" (unique address for each device)
✓ Username = "Who owns this token" (links user to their devices)
✓ Backend looks up: username → finds tokens → sends to each token
✓ One user can have multiple tokens (phone + tablet + browser)
✓ Token is unique per device/browser, even for same user
""")

def show_current_tokens():
    """Show what tokens are currently registered"""
    print_section("📊 CURRENT REGISTERED TOKENS IN DATABASE")
    
    try:
        # Try to get tokens from backend
        # Note: This would normally require database access or an API endpoint
        # For now, we'll explain what would be there
        
        print("""
To see registered tokens, you would query the push_tokens table:

Example query:
  SELECT username, platform, LEFT(token, 50) as token_preview, created_at 
  FROM push_tokens 
  ORDER BY username, platform;

This would show something like:

┌──────────────┬──────────┬──────────────────────────────────────┬─────────────────────┐
│ username     │ platform │ token_preview                       │ created_at          │
├──────────────┼──────────┼──────────────────────────────────────┼─────────────────────┤
│ john_doe     │ web      │ https://fcm.googleapis.com/fcm/send/│ 2025-12-28 10:00:00│
│ john_doe     │ android  │ dKj3hF8kL9mN2pQ5rS7tU1vW3xY4zA6bC8dE│ 2025-12-28 10:05:00│
│ jane_smith   │ web      │ https://fcm.googleapis.com/fcm/send/│ 2025-12-28 11:00:00│
└──────────────┴──────────┴──────────────────────────────────────┴─────────────────────┘

Each row = one device that can receive notifications
Same user can have multiple rows (multiple devices)
""")
        
        # Try to test the send endpoint to see how many tokens exist
        print("\nTesting send endpoint to see token count...")
        try:
            response = requests.post(
                f"{API_BASE_URL}/push/send",
                json={
                    "title": "Test",
                    "body": "Counting tokens",
                    "username": None  # All users
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                token_count = result.get("tokens", 0)
                sent_count = result.get("sent", 0)
                queued_count = result.get("queued", 0)
                
                print(f"\n✓ Found {token_count} registered token(s) in database")
                print(f"  - Successfully sent to: {sent_count} device(s)")
                print(f"  - Queued for: {queued_count} device(s)")
                
                if token_count > 0:
                    print(f"\n💡 These {token_count} tokens are linked to usernames in the database")
                    print("   When you send a notification with a username, it finds that user's tokens")
                    print("   When you send without username, it sends to ALL tokens")
                else:
                    print("\n⚠️  No tokens registered yet. Users need to sign in to register.")
                    
        except Exception as e:
            print(f"   Could not test endpoint: {str(e)}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

def show_example():
    """Show a concrete example"""
    print_section("💡 CONCRETE EXAMPLE")
    
    print("""
SCENARIO: You want to send a notification to user "john_doe"

1. Backend receives request:
   POST /push/send
   {
     "title": "New task assigned",
     "body": "You have a new maintenance task",
     "username": "john_doe"
   }

2. Backend queries database:
   SELECT token, platform FROM push_tokens WHERE username = 'john_doe'
   
   Returns:
   [
     {"token": "https://fcm.googleapis.com/fcm/send/ABC123...", "platform": "web"},
     {"token": "dKj3hF8kL9mN2pQ5rS7tU1vW3xY4zA6bC8dE", "platform": "android"}
   ]

3. Backend sends to EACH token:
   
   Token 1 (web):
     → Sends Web Push to: "https://fcm.googleapis.com/fcm/send/ABC123..."
     → Google's FCM service knows this endpoint belongs to John's iPhone
     → iPhone receives notification (even if Safari is closed)
   
   Token 2 (android):
     → Sends FCM message to: "dKj3hF8kL9mN2pQ5rS7tU1vW3xY4zA6bC8dE"
     → Google's FCM service knows this token belongs to John's Android phone
     → Android phone receives notification (even if app is closed)

4. Result:
   ✓ John gets notification on his iPhone (PWA)
   ✓ John gets notification on his Android phone (React Native app)
   ✓ Both notifications arrive even if apps are closed!

KEY INSIGHT:
  The token IS the "phone number" - it's the unique address for that device.
  The username is just how we LOOK UP which tokens belong to which user.
""")

def main():
    explain_flow()
    show_current_tokens()
    show_example()
    
    print_section("🎯 SUMMARY")
    print("""
How does it know which phone?
  → Each device has a UNIQUE TOKEN (like a phone number)
  → Token is registered with USERNAME when user signs in
  → Backend looks up: username → finds all tokens for that user
  → Sends notification to each token
  → Push service (Google/Apple) delivers to the actual device

The token = the "address" where to send
The username = how we find which tokens belong to which user
""")

if __name__ == "__main__":
    main()


















