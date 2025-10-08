# Environment Setup Guide

This guide explains how to properly configure your MatchGen application for different environments.

## 🎯 **The Problem We're Solving**

The frontend had hardcoded production URLs scattered throughout the codebase, causing:
- Development environment trying to hit production APIs
- Authentication failures in local development
- Inconsistent behavior between environments

## 🔧 **The Solution**

We've implemented a centralized environment configuration system that:
- Uses `env.API_BASE_URL` for all API calls
- Automatically switches between development and production URLs
- Maintains consistency across all components

## 📁 **Environment Configuration**

### Frontend Environment Config
**File**: `matchgen-frontend/src/config/environment.js`

```javascript
const config = {
  development: {
    API_BASE_URL: 'http://localhost:8000/api'
  },
  production: {
    API_BASE_URL: 'https://matchgen-backend-production.up.railway.app/api'
  }
};

const env = config[import.meta.env.MODE] || config.development;
export default env;
```

### Backend Environment Variables
**File**: `.env` (copy from `env.example`)

```bash
# Database
DATABASE_URL=postgresql://matchgen:password@db:5432/matchgen_db

# Django Settings
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email (for development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

## 🚀 **How to Use**

### 1. **In Your Components**
```javascript
import env from '../config/environment';

// Instead of hardcoded URLs:
const response = await axios.get(`${env.API_BASE_URL}/users/me/`);

// Instead of:
// const response = await axios.get('https://matchgen-backend-production.up.railway.app/api/users/me/');
```

### 2. **Environment Detection**
The system automatically detects the environment:
- **Development**: `import.meta.env.MODE === 'development'`
- **Production**: `import.meta.env.MODE === 'production'`

### 3. **Running in Different Environments**

#### Development
```bash
# Frontend (Vite dev server)
cd matchgen-frontend
npm run dev

# Backend (Django dev server)
cd matchgen-backend
python manage.py runserver
```

#### Production
```bash
# Build and run with Docker
docker-compose -f docker-compose.prod.yml up --build
```

## 🔍 **Files That Have Been Fixed**

### ✅ **Authentication & Core**
- `hooks/useAuth.jsx` - Token refresh and user data
- `pages/Login.jsx` - Login functionality
- `pages/Signup.jsx` - User registration
- `pages/Account.jsx` - User profile management

### ✅ **User Management**
- `pages/EnhancedSignup.jsx` - Enhanced signup flow
- `pages/EnhancedSignup2.jsx` - Enhanced signup flow
- `pages/EmailVerification.jsx` - Email verification
- `pages/dashboard2.jsx` - Dashboard user data
- `pages/fixtures.jsx` - Fixtures user data
- `pages/results.jsx` - Results user data

### ✅ **Content Management**
- `pages/createplayer.jsx` - Player management
- `hooks/club.js` - Club data management

### 🔄 **Still Need Fixing** (Run the script)
- `pages/TextElementManagement.jsx`
- `pages/creatematch.jsx`
- `pages/ClubOverview.jsx`
- `pages/FixturesManagement.jsx`
- `components/MatchdayPostGenerator.jsx`
- And many more...

## 🛠️ **Automated Fix Script**

Run this script to fix all remaining hardcoded URLs:

```bash
node scripts/fix-api-urls.js
```

This script will:
1. Find all files with hardcoded production URLs
2. Replace them with `${env.API_BASE_URL}/`
3. Add the environment import if needed
4. Report which files were fixed

## 🧪 **Testing**

### Test Development Environment
1. Clear browser storage (or use incognito)
2. Go to `http://localhost:3000`
3. Login with: `rich@matchgen.co.uk` / `password123`
4. Verify all API calls go to `localhost:8000`

### Test Production Environment
1. Deploy to production
2. Verify all API calls go to production URL
3. Test authentication and core functionality

## 📋 **Checklist**

- [ ] Run the fix script: `node scripts/fix-api-urls.js`
- [ ] Test development environment
- [ ] Test production environment
- [ ] Verify no hardcoded URLs remain
- [ ] Commit changes when everything works

## 🚨 **Important Notes**

1. **Don't merge until tested** - Make sure both environments work
2. **Clear browser storage** - Old tokens will cause issues
3. **Use incognito mode** - For testing without cache issues
4. **Check network tab** - Verify API calls go to correct URLs

## 🔧 **Troubleshooting**

### Still getting production URLs?
1. Check if the file imports `env` from `../config/environment`
2. Verify the file was processed by the fix script
3. Clear browser cache and try again

### Authentication still failing?
1. Clear browser storage completely
2. Use incognito mode
3. Check backend logs for API calls
4. Verify the backend is running on the correct port

### Environment not switching?
1. Check `import.meta.env.MODE` value
2. Verify the environment config file
3. Restart the development server
