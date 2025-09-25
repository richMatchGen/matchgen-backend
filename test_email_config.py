#!/usr/bin/env python
"""
Test script to verify email configuration for MatchGen backend.
Run this script to check if email settings are properly configured.
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).resolve().parent
sys.path.append(str(project_dir))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matchgen.settings')
django.setup()

from django.conf import settings
from django.core.mail import send_mail
from django.core.mail.backends.smtp import EmailBackend

def test_email_configuration():
    """Test email configuration and send a test email."""
    
    print("🔍 Testing Email Configuration for MatchGen")
    print("=" * 50)
    
    # Check environment variables
    print("\n📧 Email Settings:")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER or 'NOT SET'}")
    print(f"EMAIL_HOST_PASSWORD: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 'NOT SET'}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    
    # Check if email settings are configured
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        print("\n❌ Email configuration is incomplete!")
        print("Please set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD environment variables.")
        print("\nFor Gmail setup:")
        print("1. Enable 2-Factor Authentication")
        print("2. Generate App Password")
        print("3. Set EMAIL_HOST_USER=your-email@gmail.com")
        print("4. Set EMAIL_HOST_PASSWORD=your-app-password")
        return False
    
    print("\n✅ Email settings are configured!")
    
    # Test SMTP connection
    print("\n🔌 Testing SMTP Connection...")
    try:
        backend = EmailBackend(
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            use_tls=settings.EMAIL_USE_TLS,
            fail_silently=False
        )
        backend.open()
        backend.close()
        print("✅ SMTP connection successful!")
    except Exception as e:
        print(f"❌ SMTP connection failed: {str(e)}")
        return False
    
    # Test email sending (optional)
    test_email = input("\n📤 Would you like to send a test email? (y/n): ").lower().strip()
    if test_email == 'y':
        recipient = input("Enter recipient email address: ").strip()
        if recipient:
            try:
                send_mail(
                    subject='MatchGen Email Test',
                    message='This is a test email from MatchGen backend. If you receive this, email configuration is working correctly!',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient],
                    fail_silently=False,
                )
                print(f"✅ Test email sent successfully to {recipient}!")
            except Exception as e:
                print(f"❌ Failed to send test email: {str(e)}")
                return False
    
    print("\n🎉 Email configuration test completed!")
    return True

def check_verification_system():
    """Check if the verification system is properly configured."""
    
    print("\n🔐 Checking Email Verification System")
    print("=" * 50)
    
    # Check if verification fields exist in User model
    try:
        from users.models import User
        
        # Check if user has verification fields
        user_fields = [field.name for field in User._meta.fields]
        required_fields = ['email_verified', 'email_verification_token', 'email_verification_sent_at']
        
        missing_fields = [field for field in required_fields if field not in user_fields]
        
        if missing_fields:
            print(f"❌ Missing verification fields: {missing_fields}")
            print("Run migrations to add verification fields to User model.")
            return False
        else:
            print("✅ All verification fields are present in User model")
            
    except ImportError:
        print("❌ Could not import User model")
        return False
    
    # Check verification endpoints
    try:
        from users.views import RegisterView, VerifyEmailView, ResendVerificationView
        print("✅ Verification views are available")
    except ImportError as e:
        print(f"❌ Missing verification views: {str(e)}")
        return False
    
    print("✅ Email verification system is properly configured!")
    return True

if __name__ == "__main__":
    print("🚀 MatchGen Email Configuration Test")
    print("=" * 50)
    
    # Test email configuration
    email_ok = test_email_configuration()
    
    # Test verification system
    verification_ok = check_verification_system()
    
    print("\n📋 Summary:")
    print(f"Email Configuration: {'✅ OK' if email_ok else '❌ FAILED'}")
    print(f"Verification System: {'✅ OK' if verification_ok else '❌ FAILED'}")
    
    if email_ok and verification_ok:
        print("\n🎉 All systems are ready for email verification!")
    else:
        print("\n⚠️  Please fix the issues above before using email verification.")




