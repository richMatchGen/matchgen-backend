#!/usr/bin/env python3
"""
Generate a secure Django secret key for MatchGen
"""

import secrets
import string

def generate_secret_key():
    """Generate a secure Django secret key."""
    
    # Django secret key characters
    chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    
    # Generate a 50-character secret key
    secret_key = ''.join(secrets.choice(chars) for _ in range(50))
    
    return secret_key

def main():
    """Generate and display the secret key."""
    print("🔐 Django Secret Key Generator")
    print("=" * 40)
    
    secret_key = generate_secret_key()
    
    print(f"\n✅ Generated Secret Key:")
    print(f"SECRET_KEY={secret_key}")
    
    print(f"\n📋 Copy this to your .env file:")
    print(f"SECRET_KEY={secret_key}")
    
    print(f"\n⚠️  Important Security Notes:")
    print("- Keep this key secret and never commit it to version control")
    print("- Use different keys for development and production")
    print("- If compromised, generate a new key immediately")
    
    return secret_key

if __name__ == "__main__":
    main()


