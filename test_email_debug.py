#!/usr/bin/env python3
"""
Email Debug Script for MatchGen
This script helps diagnose email configuration issues.
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
from django.core.mail import send_mail
import smtplib
from email.mime.text import MIMEText

def check_env_file():
    """Check if .env file exists and is readable."""
    print("🔍 Checking .env file...")
    print("=" * 40)
    
    env_path = Path("matchgen-backend") / ".env"
    
    if not env_path.exists():
        print(f"❌ .env file not found at {env_path}")
        return False
    
    print(f"✅ .env file found at {env_path}")
    
    # Read and display email settings (masked)
    try:
        with open(env_path, 'r') as f:
            content = f.read()
            
        print("\n📧 Email settings in .env file:")
        for line in content.split('\n'):
            if line.strip().startswith('EMAIL_') or line.strip().startswith('DEFAULT_FROM_EMAIL'):
                if 'PASSWORD' in line:
                    # Mask password
                    key, value = line.split('=', 1)
                    masked_value = '*' * len(value.strip())
                    print(f"  {key}={masked_value}")
                else:
                    print(f"  {line}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
        return False

def check_django_settings():
    """Check Django email settings."""
    print("\n🔧 Checking Django email settings...")
    print("=" * 40)
    
    email_settings = [
        'EMAIL_BACKEND',
        'EMAIL_HOST',
        'EMAIL_PORT',
        'EMAIL_USE_TLS',
        'EMAIL_HOST_USER',
        'EMAIL_HOST_PASSWORD',
        'DEFAULT_FROM_EMAIL'
    ]
    
    for setting in email_settings:
        value = getattr(settings, setting, None)
        if setting == 'EMAIL_HOST_PASSWORD':
            if value:
                masked_value = '*' * len(str(value))
                print(f"✅ {setting}: {masked_value}")
            else:
                print(f"❌ {setting}: Not set")
        else:
            print(f"✅ {setting}: {value}")

def test_smtp_connection():
    """Test SMTP connection."""
    print("\n🔌 Testing SMTP connection...")
    print("=" * 40)
    
    try:
        # Create SMTP connection
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        server.starttls()
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        server.quit()
        
        print("✅ SMTP connection successful!")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ SMTP Authentication failed: {e}")
        print("💡 Check your EMAIL_HOST_USER and EMAIL_HOST_PASSWORD")
        print("💡 For Gmail, make sure you're using an App Password, not your regular password")
        return False
        
    except smtplib.SMTPConnectError as e:
        print(f"❌ SMTP connection failed: {e}")
        print("💡 Check your EMAIL_HOST and EMAIL_PORT settings")
        return False
        
    except Exception as e:
        print(f"❌ SMTP test failed: {e}")
        return False

def send_test_email():
    """Send a test email."""
    print("\n📧 Sending test email...")
    print("=" * 40)
    
    test_email = input("Enter your email address to receive the test: ").strip()
    
    if not test_email:
        print("❌ No email address provided")
        return False
    
    try:
        subject = "MatchGen Email Test"
        message = """
        🎉 Test Email from MatchGen!
        
        If you receive this email, your email configuration is working correctly.
        
        This means:
        ✅ Email settings are configured
        ✅ SMTP connection is working
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
    """Main debug function."""
    print("🚀 MatchGen Email Debug Tool")
    print("=" * 50)
    
    # Step 1: Check .env file
    if not check_env_file():
        print("\n❌ Please create and configure your .env file first")
        return
    
    # Step 2: Check Django settings
    check_django_settings()
    
    # Step 3: Test SMTP connection
    if not test_smtp_connection():
        print("\n❌ SMTP connection failed. Please fix the issues above.")
        return
    
    # Step 4: Send test email
    if send_test_email():
        print("\n🎉 Email configuration is working!")
        print("✅ Your verification emails should now be sent automatically")
    else:
        print("\n❌ Email sending failed. Check the error messages above.")

if __name__ == "__main__":
    main()











