# Cloudflare Worker Deployment Script for FA Fulltime Proxy
# This script automates the deployment of the FA Fulltime proxy worker

Write-Host "🚀 Deploying FA Fulltime Proxy Worker to Cloudflare..." -ForegroundColor Green

# Check if wrangler is installed
try {
    $null = Get-Command wrangler -ErrorAction Stop
    Write-Host "✅ Wrangler CLI found" -ForegroundColor Green
} catch {
    Write-Host "❌ Wrangler CLI not found. Installing..." -ForegroundColor Red
    npm install -g wrangler
}

# Create worker directory
Write-Host "📁 Creating worker directory..." -ForegroundColor Blue
if (!(Test-Path "fulltime-proxy")) {
    New-Item -ItemType Directory -Name "fulltime-proxy"
}
Set-Location "fulltime-proxy"

# Initialize worker if not already done
if (!(Test-Path "wrangler.toml")) {
    Write-Host "🔧 Initializing worker project..." -ForegroundColor Blue
    wrangler init --yes
}

# Copy our worker code
Write-Host "📝 Copying worker code..." -ForegroundColor Blue
Copy-Item "../workers/fulltime-proxy.js" "src/index.js" -Force

# Create/update wrangler.toml
Write-Host "⚙️ Configuring wrangler.toml..." -ForegroundColor Blue
$wranglerConfig = @"
name = "fulltime-proxy"
main = "src/index.js"
compatibility_date = "2024-01-01"

[env.production]
name = "fulltime-proxy-prod"
"@
$wranglerConfig | Out-File -FilePath "wrangler.toml" -Encoding UTF8

# Login to Cloudflare (if not already logged in)
Write-Host "🔐 Logging in to Cloudflare..." -ForegroundColor Yellow
Write-Host "This will open a browser window for authentication..." -ForegroundColor Yellow
wrangler login

# Deploy the worker
Write-Host "🚀 Deploying worker..." -ForegroundColor Green
$deployOutput = wrangler deploy
Write-Host $deployOutput

Write-Host "✅ Worker deployed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "1. Copy the worker URL from the deployment output above" -ForegroundColor White
Write-Host "2. Update PROXY_BASE in matchgen-backend/content/views.py" -ForegroundColor White
Write-Host "3. Test the proxy functionality" -ForegroundColor White
Write-Host ""
Write-Host "🔗 Worker URL format: https://fulltime-proxy.your-subdomain.workers.dev" -ForegroundColor Yellow





