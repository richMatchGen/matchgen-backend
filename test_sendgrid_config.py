#!/usr/bin/env python3
"""
Test SendGrid Configuration
This script tests if SendGrid is properly configured.
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__parent / "matchgen-backend"
sys.path.insert(0, str(project_dir))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matchgen.settings')
django.setup()

from django.conf import settings
from django.core.mail import send_mail
import smtplib

def test_sendgrid_config():
    """Test SendGrid configuration."""
    print("🔍 Testing SendGrid Configuration")
    print("=" * 50)
    
    # Check environment variables
    email_settings = [
        'EMAIL_HOST',
        'EMAIL_PORT',
        'EMAIL_USE_TLS',
        'EMAIL_HOST_USER',
        'EMAIL_HOST_PASSWORD',
        'DEFAULT_FROM_EMAIL'
    ]
    
    print("📧 Email Settings:")
    for setting in email_settings:
        value = getattr(settings, setting, None)
        if setting == 'EMAIL_HOST_PASSWORD':
            if value:
                masked_value = '*' * len(str(value))
                print(f"✅ {setting}: {masked_value}")
            else:
                print(f"❌ {setting}: NOT SET")
        else:
            print(f"✅ {setting}: {value}")
    
    print("\n" + "=" * 50)
    
    # Test SMTP connection
    print("🔌 Testing SMTP Connection...")
    try:
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        server.starttls()
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        server.quit()
        print("✅ SMTP connection successful!")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ SMTP Authentication failed: {e}")
        print("💡 Check your SendGrid API key and EMAIL_HOST_USER")
        return False
    except Exception as e:
        print(f"❌ SMTP connection failed: {e}")
        return False

def send_test_email():
    """Send a test email."""
    print("\n📧 Sending Test Email...")
    print("=" * 50)
    
    test_email = input("Enter your email address to receive the test: ").strip()
    
    if not test_email:
        print("❌ No email address provided")
        return False
    
    try:
        subject = "MatchGen SendGrid Test"
        message = """
        🎉 SendGrid Test Email!
        
        If you receive this email, your SendGrid configuration is working correctly!
        
        This means:
        ✅ SendGrid API key is correct
        ✅ SMTP settings are configured
        ✅ Email sending is functional
        
        Your verification emails should now work!
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_email],
            fail_silently=False,
        )
        
        print(f"✅ Test email sent successfully to {test_email}!")
        print("📬 Check your inbox (and spam folder)")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send test email: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 SendGrid Configuration Test")
    print("=" * 50)
    
    # Test configuration
    if not test_sendgrid_config():
        print("\n❌ SendGrid configuration test failed")
        print("💡 Please check your Railway environment variables")
        return
    
    # Send test email
    if send_test_email():
        print("\n🎉 SendGrid is working perfectly!")
        print("✅ You can now re-enable email sending in your app")
    else:
        print("\n❌ SendGrid test failed")
        print("💡 Check the error messages above")

if __name__ == "__main__":
    main()










