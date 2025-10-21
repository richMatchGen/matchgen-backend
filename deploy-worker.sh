#!/bin/bash

# Cloudflare Worker Deployment Script for FA Fulltime Proxy
# This script automates the deployment of the FA Fulltime proxy worker

echo "🚀 Deploying FA Fulltime Proxy Worker to Cloudflare..."

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "❌ Wrangler CLI not found. Installing..."
    npm install -g wrangler
fi

# Create worker directory
echo "📁 Creating worker directory..."
mkdir -p fulltime-proxy
cd fulltime-proxy

# Initialize worker if not already done
if [ ! -f "wrangler.toml" ]; then
    echo "🔧 Initializing worker project..."
    wrangler init --yes
fi

# Copy our worker code
echo "📝 Copying worker code..."
cp ../workers/fulltime-proxy.js src/index.js

# Create/update wrangler.toml
echo "⚙️ Configuring wrangler.toml..."
cat > wrangler.toml << EOF
name = "fulltime-proxy"
main = "src/index.js"
compatibility_date = "2024-01-01"

[env.production]
name = "fulltime-proxy-prod"
EOF

# Login to Cloudflare (if not already logged in)
echo "🔐 Logging in to Cloudflare..."
wrangler login

# Deploy the worker
echo "🚀 Deploying worker..."
wrangler deploy

echo "✅ Worker deployed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Copy the worker URL from the deployment output"
echo "2. Update PROXY_BASE in matchgen-backend/content/views.py"
echo "3. Test the proxy functionality"
echo ""
echo "🔗 Worker URL format: https://fulltime-proxy.your-subdomain.workers.dev"
