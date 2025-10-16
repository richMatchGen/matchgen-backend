# Start Backend Development Server
Write-Host "🚀 Starting MatchGen Backend..." -ForegroundColor Green

# Navigate to backend directory
Set-Location matchgen-backend\matchgen-backend

# Activate virtual environment
Write-Host "📦 Activating virtual environment..." -ForegroundColor Yellow
& "..\venv\Scripts\Activate.ps1"

# Set environment variables for local development
$env:DEBUG = "True"
$env:DATABASE_URL = "sqlite:///db.sqlite3"
$env:ALLOWED_HOSTS = "localhost,127.0.0.1"
$env:CORS_ALLOWED_ORIGINS = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"

Write-Host "🗄️ Running database migrations..." -ForegroundColor Yellow
python manage.py migrate

Write-Host "🎯 Starting Django development server..." -ForegroundColor Green
Write-Host "Backend will be available at: http://localhost:8000" -ForegroundColor Cyan
python manage.py runserver 0.0.0.0:8000
