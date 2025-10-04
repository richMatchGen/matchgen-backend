#!/usr/bin/env python3
"""
Test script to check if environment variables are loaded correctly
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matchgen.settings')
django.setup()

from django.conf import settings

print("🔍 Environment Variables Test")
print("=" * 50)

# Check email settings
email_settings = [
    'EMAIL_HOST',
    'EMAIL_PORT',
    'EMAIL_USE_TLS',
    'EMAIL_HOST_USER',
    'EMAIL_HOST_PASSWORD',
    'DEFAULT_FROM_EMAIL'
]

print("📧 Email Settings from Django:")
for setting in email_settings:
    value = getattr(settings, setting, None)
    if setting == 'EMAIL_HOST_PASSWORD':
        if value:
            masked_value = '*' * len(str(value))
            print(f"✅ {setting}: {masked_value}")
        else:
            print(f"❌ {setting}: NOT SET")
    else:
        if value:
            print(f"✅ {setting}: {value}")
        else:
            print(f"❌ {setting}: NOT SET")

print("\n" + "=" * 50)

# Check the specific condition that's failing
print("🔍 Checking the condition that's causing the warning:")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"EMAIL_HOST_PASSWORD: {'*' * len(str(settings.EMAIL_HOST_PASSWORD)) if settings.EMAIL_HOST_PASSWORD else 'NOT SET'}")

if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
    print("❌ The condition 'not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD' is TRUE")
    print("   This is why emails are not being sent!")
else:
    print("✅ The condition 'not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD' is FALSE")
    print("   Emails should be sent!")

print("\n" + "=" * 50)
print("💡 If the condition is TRUE, the issue is:")
print("   - Either EMAIL_HOST_USER is empty/None")
print("   - Or EMAIL_HOST_PASSWORD is empty/None")
print("   - Or both")






