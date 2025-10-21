#!/usr/bin/env python3
"""
Debug Email Environment Variables
This script helps identify which email environment variable is causing issues.
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent / "matchgen-backend"
sys.path.insert(0, str(project_dir))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matchgen.settings')
django.setup()

from django.conf import settings

def debug_email_variables():
    """Debug email environment variables."""
    print("🔍 EMAIL ENVIRONMENT VARIABLES DEBUG")
    print("=" * 60)
    
    # Check each email setting
    email_settings = [
        ('EMAIL_HOST', 'smtp.sendgrid.net'),
        ('EMAIL_PORT', '587'),
        ('EMAIL_USE_TLS', 'True'),
        ('EMAIL_HOST_USER', 'apikey'),
        ('EMAIL_HOST_PASSWORD', 'SG.your-api-key'),
        ('DEFAULT_FROM_EMAIL', 'your-email@domain.com')
    ]
    
    print("📧 Current Email Settings:")
    print("-" * 60)
    
    for setting_name, expected_value in email_settings:
        current_value = getattr(settings, setting_name, None)
        
        if setting_name == 'EMAIL_HOST_PASSWORD':
            # Mask password for security
            if current_value:
                masked_value = '*' * len(str(current_value))
                status = "✅ SET" if current_value else "❌ NOT SET"
                print(f"{setting_name:20} | {status:10} | {masked_value}")
            else:
                print(f"{setting_name:20} | ❌ NOT SET | (no value)")
        else:
            status = "✅ SET" if current_value else "❌ NOT SET"
            print(f"{setting_name:20} | {status:10} | {current_value}")
    
    print("\n" + "=" * 60)
    print("📋 Expected Values for SendGrid:")
    print("-" * 60)
    
    for setting_name, expected_value in email_settings:
        print(f"{setting_name:20} | {expected_value}")
    
    print("\n" + "=" * 60)
    print("🔧 Troubleshooting:")
    print("-" * 60)
    
    # Check for common issues
    issues = []
    
    if not getattr(settings, 'EMAIL_HOST_USER', None):
        issues.append("❌ EMAIL_HOST_USER is not set - should be 'apikey'")
    elif getattr(settings, 'EMAIL_HOST_USER', None) != 'apikey':
        issues.append(f"❌ EMAIL_HOST_USER is '{getattr(settings, 'EMAIL_HOST_USER', None)}' - should be 'apikey'")
    
    if not getattr(settings, 'EMAIL_HOST_PASSWORD', None):
        issues.append("❌ EMAIL_HOST_PASSWORD is not set - should be your SendGrid API key")
    elif not str(getattr(settings, 'EMAIL_HOST_PASSWORD', '')).startswith('SG.'):
        issues.append("❌ EMAIL_HOST_PASSWORD doesn't start with 'SG.' - check your SendGrid API key")
    
    if not getattr(settings, 'EMAIL_HOST', None):
        issues.append("❌ EMAIL_HOST is not set - should be 'smtp.sendgrid.net'")
    elif getattr(settings, 'EMAIL_HOST', None) != 'smtp.sendgrid.net':
        issues.append(f"❌ EMAIL_HOST is '{getattr(settings, 'EMAIL_HOST', None)}' - should be 'smtp.sendgrid.net'")
    
    if not getattr(settings, 'DEFAULT_FROM_EMAIL', None):
        issues.append("❌ DEFAULT_FROM_EMAIL is not set - should be your email address")
    
    if issues:
        print("🚨 Issues Found:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✅ All email settings appear to be configured correctly!")
    
    print("\n" + "=" * 60)
    print("💡 Next Steps:")
    print("-" * 60)
    print("1. Check your Railway environment variables")
    print("2. Make sure all 6 email variables are set")
    print("3. Verify your SendGrid API key is correct")
    print("4. Ensure Railway has redeployed after adding variables")

if __name__ == "__main__":
    debug_email_variables()











