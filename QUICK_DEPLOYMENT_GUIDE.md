# Quick Cloudflare Worker Deployment Guide

## 🚀 Fast Track Deployment

### Option 1: Automated Script (Recommended)
```powershell
# Run the PowerShell script
.\deploy-worker.ps1
```

### Option 2: Manual Deployment

#### Step 1: Install Wrangler CLI
```bash
npm install -g wrangler
```

#### Step 2: Login to Cloudflare
```bash
wrangler login
```
*This will open a browser window for authentication*

#### Step 3: Create Worker Project
```bash
mkdir fulltime-proxy
cd fulltime-proxy
wrangler init
```

#### Step 4: Copy Worker Code
```bash
# Copy the worker code
cp ../workers/fulltime-proxy.js src/index.js
```

#### Step 5: Configure wrangler.toml
Create or update `wrangler.toml`:
```toml
name = "fulltime-proxy"
main = "src/index.js"
compatibility_date = "2024-01-01"

[env.production]
name = "fulltime-proxy-prod"
```

#### Step 6: Deploy
```bash
wrangler deploy
```

## 🔧 After Deployment

### 1. Copy the Worker URL
The deployment will output a URL like:
```
https://fulltime-proxy.your-subdomain.workers.dev
```

### 2. Update Backend Settings
Edit `matchgen-backend/content/views.py` and update:
```python
PROXY_BASE = "https://your-actual-worker-url.workers.dev"
```

### 3. Test the Proxy
```bash
curl "https://your-worker.workers.dev?url=https://fulltime.thefa.com/displayTeam.html?id=562720767"
```

## ✅ Verification

Once deployed, the proxy should:
- ✅ Return HTML content from FA Fulltime
- ✅ Include CORS headers
- ✅ Cache responses for 3 hours
- ✅ Handle timeouts gracefully

## 🎯 Result

After deployment, users will be able to use the "FA Proxy" import method without the setup warning!





