#!/usr/bin/env python3
"""
Quick script to check if environment variables are loaded correctly
"""

import os
import sys
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent / "matchgen-backend"
sys.path.insert(0, str(project_dir))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

print("🔍 Environment Variables Check")
print("=" * 40)

# Check email-related environment variables
email_vars = [
    'EMAIL_HOST',
    'EMAIL_PORT', 
    'EMAIL_USE_TLS',
    'EMAIL_HOST_USER',
    'EMAIL_HOST_PASSWORD',
    'DEFAULT_FROM_EMAIL'
]

for var in email_vars:
    value = os.getenv(var)
    if var == 'EMAIL_HOST_PASSWORD':
        if value:
            masked_value = '*' * len(value)
            print(f"✅ {var}: {masked_value}")
        else:
            print(f"❌ {var}: NOT SET")
    else:
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NOT SET")

print("\n" + "=" * 40)

# Check if .env file exists
env_path = Path("matchgen-backend") / ".env"
if env_path.exists():
    print(f"✅ .env file found at: {env_path}")
else:
    print(f"❌ .env file NOT found at: {env_path}")

print("\n💡 If any variables show 'NOT SET', check your .env file!")



