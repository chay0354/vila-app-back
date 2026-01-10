# Video Upload Fix Summary

## Issue
Video uploads fail with "Network request failed" error, while other API calls work fine.

## Changes Made

### 1. Backend Timeout Increase
- **File**: `back/run_server.py`
- **Change**: Increased `timeout_keep_alive` to 300 seconds (5 minutes) for large file uploads
- **Reason**: Large video files need more time to upload

### 2. Enhanced Error Logging
- **File**: `front/App.tsx`
- **Changes**:
  - Added health check before upload to verify backend connectivity
  - Increased upload timeout from 2 minutes to 3 minutes
  - Added detailed logging for upload process
  - Better error messages to identify the exact failure point

### 3. Diagnostic Scripts
- **File**: `back/test_video_upload_from_app.py`
- **Purpose**: Test video uploads from host machine to verify backend works

## Current Status

✅ **Backend is working** - All tests pass (1MB, 5MB, 10MB videos)
✅ **Backend is accessible** - Listening on `0.0.0.0:4000`
✅ **Other API calls work** - Confirms backend is reachable from emulator

❌ **Video uploads fail** - "Network request failed" error

## Diagnosis

The error "Network request failed" when uploading videos (but other API calls work) suggests:

1. **FormData with file:// URIs** - React Native might have issues sending large files via FormData
2. **Request size** - Large video files might exceed some limit
3. **Connection timeout** - Upload might be timing out before completing

## Next Steps

1. **Check app console logs** when uploading a video:
   - Look for `[Upload]` prefixed logs
   - Check if health check passes
   - See exact error message

2. **Verify backend is running**:
   ```powershell
   cd back
   python run_server.py
   ```

3. **Test with smaller video**:
   - Try a 1-2 second video first
   - If that works, the issue is file size related

4. **Check Windows Firewall**:
   - Ensure port 4000 is not blocked
   - Since other API calls work, this is likely not the issue

## Testing

Run the diagnostic script:
```powershell
cd back
python test_video_upload_from_app.py
```

This confirms the backend works from the host machine. The issue is specific to the React Native app's network handling.



