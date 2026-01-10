# Android FCM Push Notifications Setup

## Quick Setup for Android Push Notifications (When App is Closed)

### Option 1: Firebase Admin SDK (Recommended)

1. **Create Firebase Project:**
   - Go to https://console.firebase.google.com/
   - Create a new project or use existing
   - Add Android app to project

2. **Get Service Account Key:**
   - Go to Project Settings → Service Accounts
   - Click "Generate new private key"
   - Download the JSON file

3. **Add to Backend Environment:**
   ```bash
   FIREBASE_CREDENTIALS='{"type":"service_account","project_id":"...","private_key_id":"...","private_key":"...","client_email":"...","client_id":"...","auth_uri":"...","token_uri":"...","auth_provider_x509_cert_url":"...","client_x509_cert_url":"..."}'
   ```
   (Paste the entire JSON content as a single-line string)

4. **Add google-services.json to Android App:**
   - Download `google-services.json` from Firebase Console
   - Place it in `front/android/app/`

### Option 2: Legacy FCM Server Key (Simpler, but less secure)

1. **Get FCM Server Key:**
   - Go to Firebase Console → Project Settings → Cloud Messaging
   - Copy the "Server key"

2. **Add to Backend Environment:**
   ```bash
   FCM_SERVER_KEY=your-server-key-here
   ```

## Current Implementation

The app will:
- ✅ Try to get FCM token automatically on Android
- ✅ Register token with backend
- ✅ Backend sends via FCM API when notifications are sent
- ✅ Notifee displays notifications even when app is closed

## Testing

After setup, test with:
```bash
curl -X POST https://vila-app-back.vercel.app/api/push/send \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","body":"Hello from FCM!","username":"your_username"}'
```

## Status

- ✅ Code ready for FCM
- ⚠️ Requires Firebase project setup
- ⚠️ Requires google-services.json in Android app
- ⚠️ Requires FIREBASE_CREDENTIALS or FCM_SERVER_KEY in backend

Once Firebase is configured, Android will receive push notifications even when the app is completely closed!



















