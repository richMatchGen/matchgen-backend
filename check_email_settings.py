#!/usr/bin/env python
"""
Simple script to check email settings without Django shell.
Run this to verify your email configuration.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def check_email_settings():
    print("🔍 Checking Email Settings for MatchGen")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        print("✅ .env file found")
    else:
        print("❌ .env file not found")
        print("Create a .env file in the matchgen-backend directory")
        return False
    
    # Check email settings
    email_host = os.getenv('EMAIL_HOST')
    email_port = os.getenv('EMAIL_PORT')
    email_user = os.getenv('EMAIL_HOST_USER')
    email_password = os.getenv('EMAIL_HOST_PASSWORD')
    email_from = os.getenv('DEFAULT_FROM_EMAIL')
    
    print(f"\n📧 Email Configuration:")
    print(f"EMAIL_HOST: {email_host or 'NOT SET'}")
    print(f"EMAIL_PORT: {email_port or 'NOT SET'}")
    print(f"EMAIL_HOST_USER: {email_user or 'NOT SET'}")
    print(f"EMAIL_HOST_PASSWORD: {'*' * len(email_password) if email_password else 'NOT SET'}")
    print(f"DEFAULT_FROM_EMAIL: {email_from or 'NOT SET'}")
    
    # Check if required settings are present
    if not email_user or not email_password:
        print("\n❌ Email configuration incomplete!")
        print("Please set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in your .env file")
        print("\nFor Gmail:")
        print("1. Enable 2-Factor Authentication")
        print("2. Generate App Password")
        print("3. Set EMAIL_HOST_USER=your-email@gmail.com")
        print("4. Set EMAIL_HOST_PASSWORD=your-app-password")
        return False
    
    print("\n✅ Email settings are configured!")
    print("Restart your Django server and try creating a new user account.")
    return True

if __name__ == "__main__":
    check_email_settings()






