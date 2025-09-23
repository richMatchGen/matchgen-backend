# Temporary Email Disable Solution

## 🚨 Current Issue
Railway is experiencing SMTP connection timeouts that are causing 30-second request timeouts.

## 🔧 Quick Fix: Disable Email Temporarily

### Option 1: Disable Email in Settings
Add this environment variable to Railway:

```bash
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

This will print emails to console instead of sending them.

### Option 2: Use Console Backend
Add this environment variable to Railway:

```bash
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Option 3: Disable Email Verification Temporarily
Set this environment variable:

```bash
DISABLE_EMAIL_VERIFICATION=True
```

## 🧪 Test the Fix
1. Add the environment variable to Railway
2. Railway will auto-redeploy
3. Try creating a new account
4. Check logs for verification links

## 📧 Current Status
The system now:
- ✅ Attempts to send emails in background
- ✅ Always logs verification links to console
- ✅ Doesn't block user registration
- ✅ Provides fallback verification method

## 🎯 Next Steps
1. **Immediate**: Use console logging for verification
2. **Short-term**: Set up SendGrid or Mailgun
3. **Long-term**: Implement proper email queue system



