# Close Task with Video - Test Results

## Test Date
2026-01-09 17:20:24

## Test Results: ✅ ALL PASSED

### 1. Backend Flow Works Perfectly
- ✅ Video upload to storage: **SUCCESS**
- ✅ Task update with video: **SUCCESS**
- ✅ Task closes with video stored in `closing_image_uri`: **SUCCESS**

### 2. Test Flow
1. Upload video to `/api/storage/upload` → Returns storage URL
2. Update task with `PATCH /api/maintenance/tasks/{id}` → Status: "סגור", imageUri: video URL
3. Backend stores video URL in `closing_image_uri` field

### 3. Example Response
```json
{
  "id": "fa9a0a06-867b-48a2-a74a-19fc8e6ab3de",
  "status": "סגור",
  "closing_image_uri": "https://szeorawtqqisokuxbihm.supabase.co/storage/v1/object/public/vidoes/e59bd281-20d2-48b7-90fb-f2f7b1e9c621.mp4"
}
```

## Issue Found

The app shows error: **"Cannot reach backend at http://10.0.2.2:4000"**

### Root Cause
The backend flow works, but the app cannot connect to the backend.

### Possible Causes
1. **Backend not running** - Check if backend is started
2. **Wrong API URL in app** - App might be using cached `.env` value
3. **Backend not accessible from emulator** - Firewall or network issue
4. **App not rebuilt** - App needs rebuild after `.env` changes

## Solutions

### Solution 1: Make sure backend is running
```powershell
cd back
python run_server.py
```
Backend should show: `Starting server on 0.0.0.0:4000`

### Solution 2: Check backend is accessible from emulator
Test from command line:
```powershell
# Test from host
curl http://127.0.0.1:4000/health

# Test from emulator perspective (10.0.2.2 maps to host's 127.0.0.1)
# This should work if backend is bound to 0.0.0.0
```

### Solution 3: Rebuild app with correct .env
```powershell
cd front
# Make sure .env has: VITE_API_BASE_URL=http://10.0.2.2:4000
npm run android:win
```

### Solution 4: Use production backend instead
Update `front/.env`:
```
VITE_API_BASE_URL=https://vila-app-back.vercel.app
```
Then rebuild the app.

## Test Script
Run the test script to verify:
```powershell
cd back
python test_close_task_with_video.py
```

This will test the complete flow and show where it fails.




