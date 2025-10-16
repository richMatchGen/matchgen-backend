# Start Complete Development Environment
Write-Host "Starting MatchGen Development Environment..." -ForegroundColor Green

Write-Host "This will start both frontend and backend in separate windows" -ForegroundColor Yellow
Write-Host ""

# Start backend in new window
Write-Host "Starting Backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-File", "start-backend.ps1"

# Wait a moment
Start-Sleep -Seconds 3

# Start frontend in new window  
Write-Host "Starting Frontend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-File", "start-frontend.ps1"

Write-Host ""
Write-Host "Development environment started!" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit this launcher..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")