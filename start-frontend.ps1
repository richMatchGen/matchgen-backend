# Start Frontend Development Server
Write-Host "🚀 Starting MatchGen Frontend..." -ForegroundColor Green

# Navigate to frontend directory
Set-Location matchgen-frontend

Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
npm install

Write-Host "🎯 Starting Vite development server..." -ForegroundColor Green
Write-Host "Frontend will be available at: http://localhost:5173" -ForegroundColor Cyan
npm run dev