#!/usr/bin/env python3
"""
Test script to verify bcrypt module is working correctly.
"""

import bcrypt
import sys

def test_bcrypt():
    """Test bcrypt functionality."""
    print("Testing bcrypt module...")
    
    try:
        # Test 1: Import check
        print("✓ bcrypt imported successfully")
        
        # Test 2: Hash a password
        test_password = "test_password_123"
        print(f"\nTest 2: Hashing password '{test_password}'...")
        hashed = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt())
        print(f"✓ Password hashed successfully: {hashed.decode('utf-8')[:50]}...")
        
        # Test 3: Verify the password
        print(f"\nTest 3: Verifying password...")
        is_valid = bcrypt.checkpw(test_password.encode('utf-8'), hashed)
        if is_valid:
            print("✓ Password verification successful")
        else:
            print("✗ Password verification failed")
            return False
        
        # Test 4: Verify wrong password fails
        print(f"\nTest 4: Testing wrong password...")
        wrong_password = "wrong_password"
        is_invalid = bcrypt.checkpw(wrong_password.encode('utf-8'), hashed)
        if not is_invalid:
            print("✓ Wrong password correctly rejected")
        else:
            print("✗ Wrong password incorrectly accepted")
            return False
        
        print("\n" + "="*50)
        print("All bcrypt tests passed! ✓")
        print("="*50)
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import bcrypt: {e}")
        return False
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bcrypt()
    sys.exit(0 if success else 1)








