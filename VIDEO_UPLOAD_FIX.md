# Video Upload Fix - Storage Bucket Issue

## Problem Identified

The video upload is failing with error:
```
"Bucket not found"
```

## Root Cause

The backend code expects Supabase Storage buckets that don't exist:
- `vidoes` (for videos - note the typo)
- `images` (for images)

## Test Results

✅ API is accessible: `https://vila-app-back.vercel.app`
✅ Storage upload endpoint exists: `/api/storage/upload`
✅ CORS headers are configured
❌ **Upload fails: "Bucket not found"**

## Solution

You need to create the storage buckets in your Supabase project:

### Step 1: Go to Supabase Dashboard

1. Go to https://supabase.com/dashboard
2. Select your project
3. Navigate to **Storage** in the left sidebar

### Step 2: Create Storage Buckets

Create two buckets:

1. **Bucket name:** `vidoes` (keep the typo to match backend code)
   - **Public:** ✅ Yes (so videos can be accessed via public URLs)
   - **File size limit:** Set appropriate limit (e.g., 100MB for videos)
   - **Allowed MIME types:** `video/*` (or leave empty for all)

2. **Bucket name:** `images`
   - **Public:** ✅ Yes
   - **File size limit:** Set appropriate limit (e.g., 10MB for images)
   - **Allowed MIME types:** `image/*` (or leave empty for all)

### Step 3: Set Bucket Policies (Optional but Recommended)

For each bucket, set policies to allow uploads:

1. Click on the bucket
2. Go to **Policies** tab
3. Add policy:
   - **Policy name:** Allow authenticated uploads
   - **Allowed operation:** INSERT
   - **Target roles:** authenticated (or anon if you want public uploads)
   - **Policy definition:** 
     ```sql
     (bucket_id = 'vidoes' OR bucket_id = 'images')
     ```

### Step 4: Test Again

After creating the buckets, run the test script again:
```bash
cd back
python test_video_upload.py
```

## Alternative: Fix the Typo

If you prefer to fix the typo in the backend code:

1. Change `"vidoes"` to `"videos"` in `back/app/main.py`
2. Create a bucket named `videos` instead of `vidoes`

**Note:** The typo appears in multiple places in the code, so you'll need to replace all instances.

## Quick Fix Script

You can also create the buckets via SQL in Supabase SQL Editor:

```sql
-- Note: Buckets must be created via the Supabase Dashboard or API
-- This is just for reference - use the dashboard method above
```

Actually, buckets need to be created via the dashboard or API, not SQL.

## Verification

After creating the buckets, the upload should work. The test script will show:
```
[✓] File Upload
```

And you'll be able to upload videos from the app!




