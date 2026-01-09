#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test backend connectivity and endpoints
Tests if the backend at https://vila-app-back.vercel.app is accessible
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

API_BASE_URL = "https://vila-app-back.vercel.app"

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(success, message):
    """Print test result"""
    status = "[✓]" if success else "[✗]"
    print(f"{status} {message}")

def test_basic_connectivity():
    """Test basic HTTP connectivity"""
    print_section("1. Basic Connectivity Test")
    
    try:
        print(f"Testing: {API_BASE_URL}")
        response = requests.get(API_BASE_URL, timeout=10)
        print_result(True, f"Backend is reachable (status: {response.status_code})")
        print(f"   Response: {response.text[:200]}")
        return True
    except requests.exceptions.Timeout:
        print_result(False, "Connection timeout - backend not responding")
        return False
    except requests.exceptions.ConnectionError:
        print_result(False, "Connection error - cannot reach backend")
        print("   Possible causes:")
        print("   - No internet connection")
        print("   - Backend is down")
        print("   - Firewall blocking connection")
        return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False

def test_health_endpoint():
    """Test health endpoint"""
    print_section("2. Health Endpoint Test")
    
    try:
        url = f"{API_BASE_URL}/health"
        print(f"Testing: {url}")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, "Health endpoint is working")
            print(f"   Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print_result(False, f"Health endpoint returned {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False

def test_storage_upload_endpoint():
    """Test storage upload endpoint"""
    print_section("3. Storage Upload Endpoint Test")
    
    try:
        url = f"{API_BASE_URL}/api/storage/upload"
        print(f"Testing: {url}")
        
        # Test with a small file
        test_content = b"This is a test file"
        files = {'file': ('test.txt', test_content, 'text/plain')}
        
        response = requests.post(url, files=files, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, "Storage upload endpoint is working")
            print(f"   Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print_result(False, f"Upload endpoint returned {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
    except requests.exceptions.Timeout:
        print_result(False, "Upload timeout")
        return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False

def test_auth_endpoints():
    """Test authentication endpoints"""
    print_section("4. Authentication Endpoints Test")
    
    endpoints = [
        ("/api/auth/login", "POST"),
        ("/api/auth/signup", "POST"),
    ]
    
    results = []
    for endpoint, method in endpoints:
        try:
            url = f"{API_BASE_URL}{endpoint}"
            print(f"\nTesting: {method} {url}")
            
            if method == "POST":
                # Test with empty/invalid data to see if endpoint exists
                response = requests.post(
                    url,
                    json={},
                    timeout=5
                )
            else:
                response = requests.get(url, timeout=5)
            
            if response.status_code == 404:
                print_result(False, f"Endpoint not found (404)")
                results.append(False)
            elif response.status_code in [400, 422]:
                print_result(True, f"Endpoint exists (returns {response.status_code} for invalid data - expected)")
                results.append(True)
            elif response.status_code == 200:
                print_result(True, f"Endpoint is working")
                results.append(True)
            else:
                print_result(True, f"Endpoint exists (status: {response.status_code})")
                results.append(True)
        except Exception as e:
            print_result(False, f"Error: {str(e)}")
            results.append(False)
    
    return all(results)

def test_dns_resolution():
    """Test DNS resolution"""
    print_section("5. DNS Resolution Test")
    
    try:
        import socket
        hostname = "vila-app-back.vercel.app"
        print(f"Resolving: {hostname}")
        
        ip = socket.gethostbyname(hostname)
        print_result(True, f"DNS resolution successful: {ip}")
        return True
    except socket.gaierror:
        print_result(False, "DNS resolution failed - cannot resolve hostname")
        return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False

def test_ssl_certificate():
    """Test SSL certificate"""
    print_section("6. SSL Certificate Test")
    
    try:
        import ssl
        import socket
        
        hostname = "vila-app-back.vercel.app"
        context = ssl.create_default_context()
        
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                print_result(True, "SSL certificate is valid")
                print(f"   Issuer: {cert.get('issuer', 'Unknown')}")
                return True
    except Exception as e:
        print_result(False, f"SSL error: {str(e)}")
        return False

def test_from_android_emulator_perspective():
    """Test connectivity as if from Android emulator"""
    print_section("7. Android Emulator Network Test")
    
    print("\nNote: Android emulator uses 10.0.2.2 to access localhost")
    print("For production URL, emulator should use regular internet connection")
    
    try:
        # Test if we can reach the backend
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print_result(True, "Backend is accessible from network")
            print("\nIf app still can't connect:")
            print("  1. Check emulator has internet (open browser in emulator)")
            print("  2. Check app is using correct API_BASE_URL")
            print("  3. Check Metro bundler is running")
            print("  4. Try: adb reverse tcp:8081 tcp:8081")
            return True
        else:
            print_result(False, f"Backend returned {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  BACKEND CONNECTIVITY TEST")
    print("=" * 70)
    print(f"Testing: {API_BASE_URL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Test 1: DNS
    results.append(("DNS Resolution", test_dns_resolution()))
    
    # Test 2: SSL
    results.append(("SSL Certificate", test_ssl_certificate()))
    
    # Test 3: Basic connectivity
    results.append(("Basic Connectivity", test_basic_connectivity()))
    
    # Test 4: Health endpoint
    results.append(("Health Endpoint", test_health_endpoint()))
    
    # Test 5: Storage upload
    results.append(("Storage Upload", test_storage_upload_endpoint()))
    
    # Test 6: Auth endpoints
    results.append(("Auth Endpoints", test_auth_endpoints()))
    
    # Test 7: Android emulator perspective
    results.append(("Android Emulator Network", test_from_android_emulator_perspective()))
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[✓]" if result else "[✗]"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed! Backend is fully accessible.")
        print("\nIf app still shows network error:")
        print("  1. Rebuild the app: npm run android:win")
        print("  2. Check .env file has correct VITE_API_BASE_URL")
        print("  3. Clear app data and restart")
    elif passed >= 4:
        print("\n[PARTIAL] Most tests passed. Backend is mostly accessible.")
        print("Some endpoints may have issues, but basic connectivity works.")
    else:
        print("\n[ERROR] Multiple tests failed. Backend may be down or unreachable.")
        print("\nTroubleshooting:")
        print("  1. Check your internet connection")
        print("  2. Try accessing https://vila-app-back.vercel.app in a browser")
        print("  3. Check if backend is deployed and running")
        print("  4. Check firewall/antivirus settings")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())

