# 📧 SendGrid Setup Guide for MatchGen

## 🎯 Overview
This guide will help you set up SendGrid for reliable email delivery in your MatchGen application.

## 🚀 Step 1: Create SendGrid Account

### 1.1 Sign Up
1. Go to [SendGrid.com](https://sendgrid.com)
2. Click **"Start for Free"**
3. Fill out the signup form:
   - **Email**: Use your business email
   - **Password**: Create a strong password
   - **Company**: MatchGen
   - **Website**: Your domain (if you have one)

### 1.2 Verify Your Account
1. Check your email for verification link
2. Click the verification link
3. Complete the account setup

## 🔑 Step 2: Create API Key

### 2.1 Navigate to API Keys
1. Log into SendGrid dashboard
2. Go to **Settings** → **API Keys**
3. Click **"Create API Key"**

### 2.2 Configure API Key
1. **API Key Name**: `MatchGen Backend`
2. **API Key Permissions**: Choose **"Restricted Access"**
3. **Mail Send**: Select **"Full Access"**
4. Click **"Create & View"**

### 2.3 Copy API Key
1. **IMPORTANT**: Copy the API key immediately
2. Store it securely (you won't be able to see it again)
3. The API key will look like: `SG.abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567890`

## ⚙️ Step 3: Configure Railway Environment Variables

### 3.1 Go to Railway Dashboard
1. Open [Railway Dashboard](https://railway.app/dashboard)
2. Find your `matchgen-backend` project
3. Click on it

### 3.2 Add SendGrid Environment Variables
Go to **Variables** tab and add these:

```bash
# SendGrid Configuration
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.your-actual-api-key-here
DEFAULT_FROM_EMAIL=your-email@yourdomain.com

# Keep existing variables
FRONTEND_URL=https://matchgen-frontend.vercel.app
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,matchgen-backend-production.up.railway.app
CORS_ALLOWED_ORIGINS=https://matchgen-frontend.vercel.app,http://localhost:3000
```

### 3.3 Important Notes
- Replace `SG.your-actual-api-key-here` with your real SendGrid API key
- Replace `your-email@yourdomain.com` with your actual email
- Keep all other existing environment variables

## 🔧 Step 4: Update Backend Code

### 4.1 Re-enable Email Sending
The backend code needs to be updated to re-enable email sending now that we have SendGrid configured.

### 4.2 Test Configuration
After Railway redeploys, test the email functionality.

## 🧪 Step 5: Testing

### 5.1 Test Registration
1. Create a new test account
2. Check if verification email is sent
3. Check Railway logs for success/error messages

### 5.2 Test Verification
1. Click the verification link in the email
2. Verify the account is activated
3. Check if user can now create posts

## 📊 Step 6: Monitor Email Delivery

### 6.1 SendGrid Dashboard
- Monitor email delivery in SendGrid dashboard
- Check bounce rates and delivery statistics
- Set up alerts for delivery issues

### 6.2 Email Logs
- Check Railway logs for email sending status
- Monitor for any delivery errors

## 🚨 Troubleshooting

### Common Issues

#### "Authentication failed"
- Check if API key is correct
- Ensure `EMAIL_HOST_USER=apikey` (literally the word "apikey")
- Verify API key has Mail Send permissions

#### "Connection refused"
- Check if `EMAIL_HOST=smtp.sendgrid.net`
- Verify `EMAIL_PORT=587`
- Ensure `EMAIL_USE_TLS=True`

#### "Emails not received"
- Check spam folder
- Verify sender email is correct
- Check SendGrid dashboard for delivery status

## 💰 SendGrid Pricing

### Free Tier
- **100 emails/day** (3,000/month)
- Perfect for development and small applications
- No credit card required

### Paid Plans
- Start at $19.95/month for 50,000 emails
- Better deliverability and features
- Advanced analytics and reporting

## 🎉 Success Indicators

You'll know SendGrid is working when:
- ✅ No timeout errors in Railway logs
- ✅ Verification emails appear in inboxes
- ✅ Email delivery shows in SendGrid dashboard
- ✅ Users can verify accounts via email links

## 📞 Support

If you encounter issues:
1. Check SendGrid documentation
2. Verify environment variables in Railway
3. Check Railway logs for error messages
4. Test with a simple email first

---

**Ready to set up SendGrid? Let's start with creating your account!**
