# Email Verification Setup Guide

## Problem
The backend is currently auto-verifying users (`email_verified=True`) when email settings are not configured, bypassing the email verification system.

## Solution
Configure email settings to enable proper email verification.

## Environment Variables Required

Add these environment variables to your `.env` file or deployment environment:

```bash
# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@matchgen.com
```

## Gmail Setup (Recommended for Development)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
   - Use this password as `EMAIL_HOST_PASSWORD`

3. **Update Environment Variables**:
   ```bash
   EMAIL_HOST_USER=your-gmail@gmail.com
   EMAIL_HOST_PASSWORD=your-16-character-app-password
   ```

## Alternative Email Providers

### SendGrid
```bash
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
```

### Mailgun
```bash
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-mailgun-username
EMAIL_HOST_PASSWORD=your-mailgun-password
```

### AWS SES
```bash
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-ses-username
EMAIL_HOST_PASSWORD=your-ses-password
```

## Testing Email Configuration

1. **Check Environment Variables**:
   ```python
   from django.conf import settings
   print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
   print(f"EMAIL_HOST_PASSWORD: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 'Not set'}")
   ```

2. **Test Email Sending**:
   ```python
   from django.core.mail import send_mail
   send_mail(
       'Test Email',
       'This is a test email.',
       'noreply@matchgen.com',
       ['test@example.com'],
       fail_silently=False,
   )
   ```

## Backend Changes Made

1. **Fixed Registration View**: Changed `email_verified=is_development` to `email_verified=False`
2. **Enhanced Logging**: Added warning message when email settings are not configured
3. **Always Require Verification**: Removed auto-verification in development mode

## Frontend Integration

The frontend is already configured to:
- Show verification banner for unverified users
- Block post creation until email is verified
- Provide resend verification functionality
- Display clear messaging about verification requirements

## Verification Flow

1. **User Registration**: Creates account with `email_verified=False`
2. **Email Sent**: Verification email sent to user's email address
3. **User Clicks Link**: Redirects to frontend verification page
4. **Verification Complete**: `email_verified` set to `True`
5. **Access Granted**: User can now create posts and access all features

## Troubleshooting

### Email Not Sending
- Check environment variables are set correctly
- Verify email provider credentials
- Check spam folder
- Review Django logs for error messages

### Verification Link Not Working
- Ensure `FRONTEND_URL` is set correctly in settings
- Check token expiration (24 hours)
- Verify URL routing in frontend

### Users Still Auto-Verified
- Restart Django server after changing environment variables
- Check that `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` are not empty
- Review registration view logs

## Production Considerations

1. **Use Professional Email Service**: Gmail is fine for development, but use SendGrid, Mailgun, or AWS SES for production
2. **Rate Limiting**: Implement rate limiting for verification email resends
3. **Token Security**: Ensure verification tokens are cryptographically secure
4. **Email Templates**: Use the provided HTML template for professional appearance
5. **Monitoring**: Set up email delivery monitoring and alerts





