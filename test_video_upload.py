#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to diagnose video upload failures
Tests connectivity, endpoints, and upload functionality
"""

import os
import sys
import requests
import json
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Test both possible API URLs
API_URLS = [
    "https://vila-app-back.vercel.app",
    "http://10.0.2.2:4000",
    "http://127.0.0.1:4000",
]

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(success, message):
    """Print test result"""
    status = "[✓]" if success else "[✗]"
    print(f"{status} {message}")

def test_api_connectivity():
    """Test which API URL is accessible"""
    print_section("1. Testing API Connectivity")
    
    accessible_urls = []
    
    for url in API_URLS:
        try:
            print(f"\nTesting: {url}")
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print_result(True, f"{url} is accessible")
                accessible_urls.append(url)
                print(f"   Response: {response.json()}")
            else:
                print_result(False, f"{url} returned {response.status_code}")
        except requests.exceptions.Timeout:
            print_result(False, f"{url} - Connection timeout")
        except requests.exceptions.ConnectionError:
            print_result(False, f"{url} - Connection refused (not running)")
        except Exception as e:
            print_result(False, f"{url} - Error: {str(e)}")
    
    if not accessible_urls:
        print("\n⚠️  No API URLs are accessible!")
        print("   Make sure:")
        print("   1. Backend is running (if using local URL)")
        print("   2. Internet connection is working (if using production URL)")
        return None
    
    print(f"\n✅ Found {len(accessible_urls)} accessible API URL(s)")
    return accessible_urls[0]  # Return first accessible URL

def test_storage_upload_endpoint(api_url):
    """Test if storage upload endpoint exists"""
    print_section("2. Testing Storage Upload Endpoint")
    
    endpoints_to_test = [
        f"{api_url}/api/storage/upload",
        f"{api_url}/storage/upload",
    ]
    
    for endpoint in endpoints_to_test:
        try:
            print(f"\nTesting: {endpoint}")
            # Try a HEAD request first (lighter)
            try:
                response = requests.head(endpoint, timeout=5)
                if response.status_code in [200, 405, 400]:  # 405 = method not allowed (but endpoint exists)
                    print_result(True, f"Endpoint exists (status: {response.status_code})")
                    return endpoint
            except:
                pass
            
            # Try a POST with empty body to see if endpoint exists
            response = requests.post(endpoint, timeout=5)
            if response.status_code != 404:
                print_result(True, f"Endpoint exists (status: {response.status_code})")
                if response.status_code == 400:
                    print("   (400 is expected - missing file, but endpoint exists)")
                return endpoint
            else:
                print_result(False, f"Endpoint not found (404)")
        except requests.exceptions.Timeout:
            print_result(False, f"Timeout")
        except Exception as e:
            print_result(False, f"Error: {str(e)}")
    
    return None

def test_upload_small_file(api_url, endpoint):
    """Test uploading a small test file"""
    print_section("3. Testing File Upload")
    
    # Create a small test file in memory
    test_content = b"This is a test file for upload"
    test_file = ("test.txt", test_content, "text/plain")
    
    try:
        print(f"\nUploading test file to: {endpoint}")
        print(f"File size: {len(test_content)} bytes")
        
        files = {'file': test_file}
        
        response = requests.post(
            endpoint,
            files=files,
            timeout=30
        )
        
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print_result(True, "Upload successful!")
                print(f"   Response: {json.dumps(data, indent=2)}")
                return True
            except:
                print(f"   Response text: {response.text[:200]}")
                print_result(True, "Upload successful (non-JSON response)")
                return True
        else:
            print_result(False, f"Upload failed with status {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print_result(False, "Upload timeout (file too large or connection too slow)")
        return False
    except requests.exceptions.ConnectionError as e:
        print_result(False, f"Connection error: {str(e)}")
        return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_cors_headers(api_url):
    """Test CORS headers (important for React Native)"""
    print_section("4. Testing CORS Headers")
    
    try:
        # Make an OPTIONS request (preflight)
        response = requests.options(
            f"{api_url}/api/storage/upload",
            headers={
                'Origin': 'http://localhost',
                'Access-Control-Request-Method': 'POST',
            },
            timeout=5
        )
        
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
        }
        
        print("\nCORS Headers:")
        for header, value in cors_headers.items():
            if value:
                print_result(True, f"{header}: {value}")
            else:
                print_result(False, f"{header}: Not set")
        
        if cors_headers['Access-Control-Allow-Origin']:
            return True
        else:
            print("\n⚠️  CORS headers may be missing - this could cause upload failures")
            return False
            
    except Exception as e:
        print_result(False, f"Error checking CORS: {str(e)}")
        return False

def check_backend_storage_endpoint():
    """Check if backend has storage upload endpoint"""
    print_section("5. Checking Backend Code")
    
    backend_file = "app/main.py"
    if os.path.exists(backend_file):
        print(f"\nChecking {backend_file} for storage upload endpoint...")
        try:
            with open(backend_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '/api/storage/upload' in content or '/storage/upload' in content:
                    print_result(True, "Storage upload endpoint found in backend code")
                    # Find the endpoint definition
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'storage/upload' in line.lower() or 'storage' in line.lower() and 'upload' in line.lower():
                            if '@app.post' in line or '@app.put' in line:
                                print(f"   Found at line {i+1}: {line.strip()}")
                                # Show a few lines of context
                                for j in range(max(0, i-2), min(len(lines), i+3)):
                                    marker = ">>>" if j == i else "   "
                                    print(f"{marker} {j+1}: {lines[j]}")
                                break
                    return True
                else:
                    print_result(False, "Storage upload endpoint NOT found in backend code")
                    print("   The backend may not have this endpoint implemented")
                    return False
        except Exception as e:
            print_result(False, f"Error reading backend file: {str(e)}")
            return False
    else:
        print_result(False, f"Backend file not found at {backend_file}")
        print("   Cannot check if endpoint exists in code")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  VIDEO UPLOAD DIAGNOSTIC TEST")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Test 1: API Connectivity
    api_url = test_api_connectivity()
    results.append(("API Connectivity", api_url is not None))
    
    if not api_url:
        print("\n[ERROR] Cannot proceed - no API is accessible")
        print("\nTroubleshooting:")
        print("  1. If using local backend (10.0.2.2:4000):")
        print("     - Make sure backend is running: cd back && python -m uvicorn app.main:app --port 4000")
        print("  2. If using production (vila-app-back.vercel.app):")
        print("     - Check internet connection")
        print("     - Verify backend is deployed")
        return 1
    
    # Test 2: Storage Upload Endpoint
    endpoint = test_storage_upload_endpoint(api_url)
    results.append(("Storage Upload Endpoint", endpoint is not None))
    
    if not endpoint:
        print("\n⚠️  Storage upload endpoint not found!")
        print("   This is likely the problem - the backend may not have this endpoint")
        check_backend_storage_endpoint()
        return 1
    
    # Test 3: CORS Headers
    results.append(("CORS Headers", test_cors_headers(api_url)))
    
    # Test 4: Actual Upload
    if endpoint:
        results.append(("File Upload", test_upload_small_file(api_url, endpoint)))
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[✓]" if result else "[✗]"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed! Upload should work.")
        print(f"\n✅ Working API URL: {api_url}")
        print(f"✅ Working endpoint: {endpoint}")
        print("\nIf upload still fails in app:")
        print("  1. Make sure .env file has correct API_BASE_URL")
        print("  2. Rebuild the app (not just reload)")
        print("  3. Check app console logs for specific error")
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed.")
        print("\nMost likely issues:")
        if not results[0][1]:
            print("  - Backend is not running or not accessible")
        if not results[1][1]:
            print("  - Storage upload endpoint doesn't exist in backend")
            print("  - Check backend code for /api/storage/upload endpoint")
        if len(results) > 2 and not results[2][1]:
            print("  - CORS headers may be missing (less likely to cause complete failure)")
        if len(results) > 3 and not results[3][1]:
            print("  - Upload endpoint exists but upload is failing")
            print("  - Check backend logs for errors")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())

