# Railway Email Configuration Fix

## 🚨 Current Issue
Railway is experiencing SMTP connection timeouts when trying to connect to Gmail's SMTP server.

## 🔧 Solutions

### Solution 1: Alternative SMTP Settings (Recommended)
Add these environment variables to Railway:

```bash
# Try these alternative settings
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=465
EMAIL_USE_TLS=False
EMAIL_USE_SSL=True
EMAIL_TIMEOUT=10
```

### Solution 2: Use SendGrid (Most Reliable)
1. Sign up for SendGrid (free tier available)
2. Get API key from SendGrid
3. Add these environment variables to Railway:

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
DEFAULT_FROM_EMAIL=your-email@yourdomain.com
```

### Solution 3: Use Mailgun (Alternative)
1. Sign up for Mailgun
2. Add these environment variables to Railway:

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-mailgun-smtp-username
EMAIL_HOST_PASSWORD=your-mailgun-smtp-password
DEFAULT_FROM_EMAIL=your-email@yourdomain.com
```

## 🧪 Testing
After updating the environment variables:
1. Railway will automatically redeploy
2. Try creating a new account
3. Check logs for email sending success

## 📧 Current Workaround
The system now falls back to console logging if email fails, so verification links are still available in the logs.




