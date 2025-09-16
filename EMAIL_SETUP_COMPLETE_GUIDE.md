# 📧 Complete Email Setup Guide for MatchGen

## 🎯 Overview
This guide will help you set up real email functionality for MatchGen's email verification system.

## 🚀 Quick Setup (Gmail - Recommended)

### Step 1: Enable 2-Factor Authentication
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** if not already enabled

### Step 2: Generate App Password
1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
2. Select **Mail** and **Other (Custom name)**
3. Enter "MatchGen Backend" as the name
4. Copy the generated 16-character password (e.g., `abcd efgh ijkl mnop`)

### Step 3: Create Environment File
Create a `.env` file in `matchgen-backend/matchgen-backend/` with:

```bash
# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-character-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# Frontend URL (for verification links)
FRONTEND_URL=https://your-frontend-domain.com
```

### Step 4: Test Email Configuration
Run the test script:
```bash
python test_email_config.py
```

## 🔧 Alternative Email Providers

### Outlook/Hotmail
```bash
EMAIL_HOST=smtp-mail.outlook.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@outlook.com
EMAIL_HOST_PASSWORD=your-password
```

### Yahoo Mail
```bash
EMAIL_HOST=smtp.mail.yahoo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@yahoo.com
EMAIL_HOST_PASSWORD=your-app-password
```

### Custom SMTP Server
```bash
EMAIL_HOST=your-smtp-server.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-username
EMAIL_HOST_PASSWORD=your-password
```

## 🛠️ Advanced Configuration

### Email Template Customization
The system uses a branded HTML template located at:
`matchgen-frontend/src/templates/EmailVerificationTemplate.html`

### Email Settings in Django
All email settings are configured in:
`matchgen-backend/matchgen-backend/matchgen/settings.py`

### Backend Email Logic
Email sending logic is in:
`matchgen-backend/matchgen-backend/users/views.py`

## 🧪 Testing

### Test 1: Configuration Check
```bash
python check_email_settings.py
```

### Test 2: Send Test Email
```bash
python test_email_config.py
```

### Test 3: Full Registration Flow
1. Create a new account
2. Check your email inbox
3. Click the verification link
4. Verify account is activated

## 🚨 Troubleshooting

### Common Issues

#### "Authentication failed"
- Check your app password is correct
- Ensure 2FA is enabled on your Google account
- Verify the email address is correct

#### "Connection refused"
- Check your internet connection
- Verify SMTP server and port settings
- Check firewall settings

#### "Email not received"
- Check spam/junk folder
- Verify email address is correct
- Check email provider's sending limits

### Debug Mode
Enable debug logging by setting in your `.env`:
```bash
DEBUG=True
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

This will print emails to console instead of sending them.

## 🔒 Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use app passwords** instead of your main password
3. **Rotate passwords** regularly
4. **Monitor email logs** for suspicious activity
5. **Use HTTPS** for your frontend URL

## 📊 Monitoring

### Email Logs
Check Django logs for email sending status:
```bash
tail -f logs/django.log
```

### Email Metrics
Monitor email delivery rates and bounce rates through your email provider's dashboard.

## 🎉 Success Indicators

You'll know email is working when:
- ✅ No console logging of verification links
- ✅ Emails appear in user inboxes
- ✅ Verification links work from emails
- ✅ No 500 errors in backend logs

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify your email provider's documentation
3. Test with a simple email first
4. Check Django logs for detailed error messages

---

**Happy emailing! 📧✨**
