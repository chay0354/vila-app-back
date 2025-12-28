# Push Notifications Setup Guide

This guide explains how to set up push notifications for both PWA (Web Push) and Native Android (FCM).

## Prerequisites

1. **VAPID Keys for Web Push** (PWA)
2. **FCM Server Key** (Native Android)

## Step 1: Generate VAPID Keys for Web Push

VAPID keys are required for Web Push notifications in the PWA.

### Option A: Using Python (Recommended)

```bash
pip install py-vapid
python -m py_vapid --gen
```

This will output:
- Private key (save as `VAPID_PRIVATE_KEY`)
- Public key (save as `VAPID_PUBLIC_KEY`)

### Option B: Using Node.js

```bash
npm install -g web-push
web-push generate-vapid-keys
```

## Step 2: Get FCM Server Key (Native Android)

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project (or create one)
3. Go to Project Settings > Cloud Messaging
4. Copy the "Server key" (save as `FCM_SERVER_KEY`)

## Step 3: Configure Environment Variables

Add these to your `.env` file in the `back/` directory:

```env
VAPID_PRIVATE_KEY=your_private_key_here
VAPID_PUBLIC_KEY=your_public_key_here
VAPID_EMAIL=mailto:admin@bolavilla.com
FCM_SERVER_KEY=your_fcm_server_key_here
```

## Step 4: Create Database Table

Run the SQL script to create the push_subscriptions table:

```sql
-- Run this in Supabase SQL Editor
-- See: back/create_push_subscriptions_table.sql
```

Or execute:
```bash
# In Supabase SQL Editor, run:
back/create_push_subscriptions_table.sql
```

## Step 5: Install Backend Dependencies

```bash
cd back
pip install -r requirements.txt
```

## Step 6: Restart Backend Server

```bash
uvicorn app.main:app --reload --port 4000
```

## How It Works

### PWA (Web Push)
1. User logs in to the PWA
2. App requests notification permission
3. App registers for Web Push using VAPID public key
4. Subscription is sent to backend and stored in database
5. When a task is assigned or message is sent, backend sends push notification to all registered devices

### Native Android (FCM)
1. User logs in to the native app
2. App gets FCM token from Firebase
3. Token is sent to backend and stored in database
4. When a task is assigned or message is sent, backend sends FCM notification to all registered devices

## Testing

### Test Web Push (PWA)
1. Open PWA in browser
2. Log in
3. Check browser console for "✅ Web Push subscription registered"
4. Assign a task to yourself from another device
5. You should receive a push notification even when the app is closed

### Test FCM (Native)
1. Open native app
2. Log in
3. Check logs for FCM token registration
4. Assign a task to yourself from another device
5. You should receive a push notification even when the app is closed

## Troubleshooting

### VAPID Keys Not Working
- Ensure keys are properly formatted (no extra spaces)
- Check that `VAPID_EMAIL` starts with `mailto:`
- Verify backend logs for VAPID errors

### FCM Not Working
- Verify FCM server key is correct
- Check Firebase project settings
- Ensure native app has Firebase configured

### No Notifications Received
- Check browser/device notification permissions
- Verify subscription is stored in database
- Check backend logs for push notification errors
- Ensure user is logged in when subscription is registered

