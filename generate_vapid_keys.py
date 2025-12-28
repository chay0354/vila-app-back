#!/usr/bin/env python3
"""
Generate VAPID keys for Web Push notifications
Run this once to generate keys, then add them to your environment variables
"""

import subprocess
import sys

def install_package(package):
    """Install a package if not available"""
    try:
        __import__(package)
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def generate_vapid_keys():
    """Generate VAPID public and private keys using pywebpush"""
    try:
        install_package("pywebpush")
        from pywebpush import webpush
        
        # Use pywebpush's key generation
        install_package("cryptography")
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.backends import default_backend
        import base64
        
        # Generate EC key pair
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        public_key = private_key.public_key()
        
        # Get public key in uncompressed format (65 bytes: 0x04 + 32 bytes X + 32 bytes Y)
        public_numbers = public_key.public_numbers()
        x_bytes = public_numbers.x.to_bytes(32, 'big')
        y_bytes = public_numbers.y.to_bytes(32, 'big')
        public_key_bytes = b'\x04' + x_bytes + y_bytes
        
        # Get private key (32 bytes)
        private_key_bytes = private_key.private_numbers().private_value.to_bytes(32, 'big')
        
        # Convert to base64 URL-safe strings (no padding)
        public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')
        private_key_b64 = base64.urlsafe_b64encode(private_key_bytes).decode('utf-8').rstrip('=')
        
        print("=" * 60)
        print("VAPID Keys Generated Successfully!")
        print("=" * 60)
        print("\nAdd these to your .env file or environment variables:\n")
        print(f"VAPID_PUBLIC_KEY={public_key_b64}")
        print(f"VAPID_PRIVATE_KEY={private_key_b64}")
        print(f"VAPID_EMAIL=mailto:admin@bolavilla.com")
        print("\n" + "=" * 60)
        print("\nFor PWA, expose VAPID_PUBLIC_KEY to the frontend.")
        print("Keep VAPID_PRIVATE_KEY secret on the backend only.")
        print("=" * 60)
        
        return public_key_b64, private_key_b64
    except Exception as e:
        print(f"Error generating keys: {e}")
        print("\nAlternative: Use online tool at https://web-push-codelab.glitch.me/")
        print("Or install manually: pip install py-vapid && python -m py_vapid --gen")
        return None, None

if __name__ == "__main__":
    generate_vapid_keys()

