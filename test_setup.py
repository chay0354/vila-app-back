#!/usr/bin/env python3
"""
Test script to check if the backend setup is working correctly.
This script verifies:
1. All required dependencies are installed
2. Environment variables are set
3. Imports work correctly
4. Basic functionality
"""

import sys
import os

# Add the app directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    """Test if all required modules can be imported."""
    print("=" * 60)
    print("Testing imports...")
    print("=" * 60)
    
    required_modules = [
        ('fastapi', 'FastAPI'),
        ('pydantic', 'Pydantic'),
        ('bcrypt', 'bcrypt'),
        ('requests', 'requests'),
        ('supabase', 'Supabase'),
        ('dotenv', 'python-dotenv'),
    ]
    
    optional_modules = [
        ('pywebpush', 'pywebpush'),
        ('firebase_admin', 'firebase-admin'),
    ]
    
    all_good = True
    
    # Test required modules
    print("\nRequired modules:")
    for module_name, display_name in required_modules:
        try:
            __import__(module_name)
            print(f"  [OK] {display_name}")
        except ImportError as e:
            print(f"  [FAIL] {display_name} - MISSING")
            print(f"    Error: {e}")
            all_good = False
    
    # Test optional modules
    print("\nOptional modules:")
    for module_name, display_name in optional_modules:
        try:
            __import__(module_name)
            print(f"  [OK] {display_name}")
        except ImportError:
            print(f"  [WARN] {display_name} - Not installed (optional)")
    
    return all_good

def test_environment():
    """Test if required environment variables are set."""
    print("\n" + "=" * 60)
    print("Testing environment variables...")
    print("=" * 60)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_SERVICE_ROLE_KEY',
    ]
    
    optional_vars = [
        'FIREBASE_CREDENTIALS',
        'OPENAI_API_KEY',
    ]
    
    all_good = True
    
    print("\nRequired environment variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            masked = value[:10] + "..." if len(value) > 10 else "***"
            print(f"  [OK] {var} - Set ({masked})")
        else:
            print(f"  [FAIL] {var} - NOT SET")
            all_good = False
    
    print("\nOptional environment variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  [OK] {var} - Set")
        else:
            print(f"  [WARN] {var} - Not set (optional)")
    
    return all_good

def test_app_imports():
    """Test if app modules can be imported."""
    print("\n" + "=" * 60)
    print("Testing app module imports...")
    print("=" * 60)
    
    try:
        from app.supabase_client import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
        print("  [OK] supabase_client")
        
        if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
            print("  [OK] Supabase credentials loaded")
        else:
            print("  [FAIL] Supabase credentials not loaded")
            return False
        
        return True
    except Exception as e:
        print(f"  [FAIL] Failed to import app modules")
        print(f"    Error: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality."""
    print("\n" + "=" * 60)
    print("Testing basic functionality...")
    print("=" * 60)
    
    try:
        import bcrypt
        # Test bcrypt
        password = "test_password"
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        if bcrypt.checkpw(password.encode('utf-8'), hashed):
            print("  [OK] bcrypt - Working correctly")
        else:
            print("  [FAIL] bcrypt - Not working correctly")
            return False
        
        return True
    except Exception as e:
        print(f"  [FAIL] Basic functionality test failed")
        print(f"    Error: {e}")
        return False

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Backend Setup Test Script")
    print("=" * 60)
    
    results = {
        'imports': test_imports(),
        'environment': test_environment(),
        'app_imports': test_app_imports(),
        'functionality': test_basic_functionality(),
    }
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {test_name.upper()}: {status}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] All tests passed! The backend should work correctly.")
        print("\nTo run the server:")
        print("  cd back")
        print("  python run_server.py")
        print("  OR")
        print("  python -m uvicorn app.main:app --reload")
        return 0
    else:
        print("[ERROR] Some tests failed. Please fix the issues above.")
        print("\nTo install dependencies:")
        print("  cd back")
        print("  python -m pip install -r requirements.txt")
        return 1

if __name__ == '__main__':
    sys.exit(main())

