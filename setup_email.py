#!/usr/bin/env python3
"""
Email Setup Helper Script for MatchGen
This script helps you configure email settings for the MatchGen backend.
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

from django.core.mail import send_mail
from django.conf import settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def check_email_settings():
    """Check if email settings are properly configured."""
    print("🔍 Checking Email Configuration...")
    print("=" * 50)
    
    # Check required settings
    required_settings = [
        'EMAIL_HOST',
        'EMAIL_PORT', 
        'EMAIL_USE_TLS',
        'EMAIL_HOST_USER',
        'EMAIL_HOST_PASSWORD',
        'DEFAULT_FROM_EMAIL'
    ]
    
    missing_settings = []
    for setting in required_settings:
        value = getattr(settings, setting, None)
        if not value:
            missing_settings.append(setting)
            print(f"❌ {setting}: Not configured")
        else:
            # Mask password for security
            if 'PASSWORD' in setting:
                masked_value = '*' * len(str(value))
                print(f"✅ {setting}: {masked_value}")
            else:
                print(f"✅ {setting}: {value}")
    
    print("\n" + "=" * 50)
    
    if missing_settings:
        print(f"❌ Missing {len(missing_settings)} email settings")
        print("\n📝 To fix this, create a .env file with:")
        print("EMAIL_HOST=smtp.gmail.com")
        print("EMAIL_PORT=587")
        print("EMAIL_USE_TLS=True")
        print("EMAIL_HOST_USER=your-email@gmail.com")
        print("EMAIL_HOST_PASSWORD=your-app-password")
        print("DEFAULT_FROM_EMAIL=your-email@gmail.com")
        return False
    else:
        print("✅ All email settings are configured!")
        return True

def test_smtp_connection():
    """Test SMTP connection without sending an email."""
    print("\n🔌 Testing SMTP Connection...")
    print("=" * 50)
    
    try:
        # Create SMTP connection
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        server.starttls()
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        server.quit()
        
        print("✅ SMTP connection successful!")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("❌ SMTP Authentication failed")
        print("💡 Check your EMAIL_HOST_USER and EMAIL_HOST_PASSWORD")
        return False
        
    except smtplib.SMTPConnectError:
        print("❌ SMTP connection failed")
        print("💡 Check your EMAIL_HOST and EMAIL_PORT settings")
        return False
        
    except Exception as e:
        print(f"❌ SMTP test failed: {str(e)}")
        return False

def send_test_email():
    """Send a test email to verify everything works."""
    print("\n📧 Sending Test Email...")
    print("=" * 50)
    
    # Get test email from user
    test_email = input("Enter your email address to receive the test email: ").strip()
    
    if not test_email:
        print("❌ No email address provided")
        return False
    
    try:
        subject = "MatchGen Email Test"
        message = """
        🎉 Congratulations!
        
        Your MatchGen email configuration is working perfectly!
        
        This is a test email to verify that:
        ✅ Email settings are configured correctly
        ✅ SMTP connection is working
        ✅ Email sending functionality is operational
        
        Your verification emails will now be sent automatically.
        
        Best regards,
        The MatchGen Team
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
        print(f"❌ Failed to send test email: {str(e)}")
        return False

def main():
    """Main setup function."""
    print("🚀 MatchGen Email Setup Helper")
    print("=" * 50)
    
    # Step 1: Check settings
    if not check_email_settings():
        print("\n❌ Please configure email settings first")
        return
    
    # Step 2: Test connection
    if not test_smtp_connection():
        print("\n❌ Please fix SMTP connection issues")
        return
    
    # Step 3: Send test email
    if send_test_email():
        print("\n🎉 Email setup completed successfully!")
        print("✅ Your MatchGen backend is ready to send verification emails")
    else:
        print("\n❌ Email setup failed")
        print("💡 Check the error messages above and try again")

if __name__ == "__main__":
    main()


