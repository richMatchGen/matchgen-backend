# Quick Email Setup for MatchGen

## The Problem
No verification emails are being sent because email settings are not configured.

## Quick Solution

### Step 1: Create .env file
Create a file called `.env` in the `matchgen-backend` directory with these contents:

```bash
# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
DEFAULT_FROM_EMAIL=noreply@matchgen.com

# Frontend URL
FRONTEND_URL=https://matchgen-frontend.vercel.app
```

### Step 2: Gmail Setup (Easiest Option)

1. **Use your Gmail account** (or create a new one for testing)

2. **Enable 2-Factor Authentication**:
   - Go to Google Account settings
   - Security → 2-Step Verification
   - Turn it on

3. **Generate App Password**:
   - In Google Account settings
   - Security → 2-Step Verification → App passwords
   - Select "Mail" and generate password
   - Copy the 16-character password

4. **Update .env file**:
   ```bash
   EMAIL_HOST_USER=your-actual-gmail@gmail.com
   EMAIL_HOST_PASSWORD=your-16-character-app-password
   ```

### Step 3: Test the Setup

1. **Restart your Django server** after creating the .env file

2. **Try creating a new user account** - you should now receive a verification email

3. **Check your spam folder** if you don't see the email

## Alternative: Use Console Logging (Temporary)

If you can't set up email right now, you can temporarily see the verification links in the console:

1. **Check Django logs** when creating a new user
2. **Look for this message**: `Verification URL for user@example.com: https://...`
3. **Copy and paste the URL** in your browser to verify the account

## Verification

After setting up email, new users should:
- ✅ Receive verification email
- ✅ See verification step in signup
- ✅ Be blocked from creating posts until verified
- ✅ See verification banner if not verified

## Troubleshooting

### "Email settings not configured" in logs
- Make sure .env file exists in matchgen-backend directory
- Check that EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are set
- Restart Django server after changes

### "Authentication failed" error
- Make sure you're using App Password, not regular Gmail password
- Verify 2-Factor Authentication is enabled
- Check that EMAIL_HOST_USER is your full Gmail address

### Email goes to spam
- Add noreply@matchgen.com to your safe senders
- Check spam/junk folder

## Production Setup

For production, consider using:
- **SendGrid** (recommended)
- **Mailgun**
- **AWS SES**

These are more reliable than Gmail for production use.





