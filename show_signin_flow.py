#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shows exactly when push tokens are saved during sign-in
"""

print("""
┌─────────────────────────────────────────────────────────────────┐
│         WHEN IS PUSH TOKEN SAVED?                                 │
└─────────────────────────────────────────────────────────────────┘

YES! The push token is saved automatically when the user signs in.

┌─────────────────────────────────────────────────────────────────┐
│                    PWA (iOS Safari / Android Browser)            │
└─────────────────────────────────────────────────────────────────┘

Location: pwa/src/screens/SignInScreen.tsx

Flow:
  1. User enters username/password and clicks "Sign In"
  2. App sends sign-in request to backend
  3. Backend validates credentials
  4. ✅ IF SIGN-IN SUCCESSFUL:
     → Line 126: registerPushSubscription(username, API_BASE_URL)
     → This happens IMMEDIATELY after successful sign-in
     → Before navigating to the hub screen

Code:
  // Success - set user and navigate to hub
  const username = data.username || name.trim()
  onSignIn(username, data.role, data.image_url)
  
  // Register push notification subscription
  registerPushSubscription(username, API_BASE_URL)  ← SAVED HERE!
  
  navigate('/hub')

What registerPushSubscription does:
  1. Requests notification permission from browser
  2. Creates Web Push subscription (gets unique token)
  3. Sends to backend: POST /push/register
     {
       "username": "john_doe",
       "token": "https://fcm.googleapis.com/fcm/send/ABC123...",
       "platform": "web"
     }
  4. Backend saves to push_tokens table

┌─────────────────────────────────────────────────────────────────┐
│              React Native Android (APK)                          │
└─────────────────────────────────────────────────────────────────┘

Location: front/App.tsx

Flow:
  1. User enters username/password and clicks "Sign In"
  2. App sends sign-in request to backend
  3. Backend validates credentials
  4. ✅ IF SIGN-IN SUCCESSFUL:
     → Line 2107: registerPushToken(username)
     → This happens IMMEDIATELY after successful sign-in

Code:
  // Success - set user
  const username = data.username || name.trim()
  setUser(username)
  setName('')
  setPassword('')
  
  // Register push notification token
  registerPushToken(username)  ← SAVED HERE!
  
  // Navigate to hub...

What registerPushToken does:
  1. Gets FCM token from Firebase (for Android)
  2. Sends to backend: POST /push/register
     {
       "username": "john_doe",
       "token": "dKj3hF8kL9mN2pQ5rS7tU1vW3xY4zA6bC8dE",
       "platform": "android"
     }
  3. Backend saves to push_tokens table

┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND STORAGE                               │
└─────────────────────────────────────────────────────────────────┘

When backend receives POST /push/register:

  1. Checks if token already exists for this username + platform
  2. If exists: Updates the token
  3. If new: Creates new row in push_tokens table

Database table: push_tokens
  ┌─────────────┬──────────────────────────────┬──────────┬─────────────────────┐
  │ username    │ token                        │ platform │ created_at          │
  ├─────────────┼──────────────────────────────┼──────────┼─────────────────────┤
  │ john_doe    │ https://fcm...ABC123         │ web      │ 2025-12-28 10:00:00 │
  │ john_doe    │ dKj3hF8...xyz                │ android  │ 2025-12-28 10:05:00 │
  └─────────────┴──────────────────────────────┴──────────┴─────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    KEY POINTS                                    │
└─────────────────────────────────────────────────────────────────┘

✓ Token is saved AUTOMATICALLY on sign-in
✓ Happens immediately after successful authentication
✓ No user action needed (except allowing notification permission)
✓ If user signs in on multiple devices, each device gets its own token
✓ If user signs in again on same device, token is UPDATED (not duplicated)
✓ Token persists in database until user signs out or token expires

┌─────────────────────────────────────────────────────────────────┐
│                    WHAT IF USER DENIES PERMISSION?               │
└─────────────────────────────────────────────────────────────────┘

If user denies notification permission:
  → App still tries to register, but uses a fallback token
  → Fallback token won't receive real push notifications
  → But the system still works (just no background notifications)

If user grants permission later:
  → Next time they sign in, a real token will be registered
  → Or they can manually trigger registration (if you add that feature)
""")






