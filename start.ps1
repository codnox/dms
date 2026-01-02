# Distribution Management System - Quick Start Script

Write-Host "Starting Distribution Management System..." -ForegroundColor Cyan
Write-Host ""

# Check if backend is already running
$backendRunning = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*uvicorn*" }

if (-not $backendRunning) {
    Write-Host "Starting Backend Server..." -ForegroundColor Yellow
    $backendCmd = "cd '$PSScriptRoot\backend'; python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
    Write-Host "Backend server starting on http://localhost:8000" -ForegroundColor Green
    Write-Host ""
    Start-Sleep -Seconds 3
}
else {
    Write-Host "Backend server already running" -ForegroundColor Yellow
    Write-Host ""
}

# Check if frontend is already running
$frontendRunning = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue

if (-not $frontendRunning) {
    Write-Host "Starting Frontend Server..." -ForegroundColor Yellow
    $frontendCmd = "cd '$PSScriptRoot\frontend'; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd
    Write-Host "Frontend server starting on http://localhost:3000" -ForegroundColor Green
    Write-Host ""
}
else {
    Write-Host "Frontend server already running" -ForegroundColor Yellow
    Write-Host ""
}

Start-Sleep -Seconds 2

Write-Host "Distribution Management System is starting!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Frontend:  http://localhost:3000" -ForegroundColor White
Write-Host "Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "API Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Demo Accounts:" -ForegroundColor Yellow
Write-Host "   admin@dms.com / admin123 (Admin)" -ForegroundColor White
Write-Host "   manager@dms.com / manager123 (Manager)" -ForegroundColor White
Write-Host "   distributor@dms.com / dist123 (Distributor)" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to open browser..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Start-Process "http://localhost:3000"

Write-Host "Application opened in browser!" -ForegroundColor Green
Write-Host ""
Write-Host "To stop servers, close the terminal windows." -ForegroundColor Yellow
