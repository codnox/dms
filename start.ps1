# Start Distribution Management System with Docker Compose

Write-Host "Starting Distribution Management System (Docker Compose)..." -ForegroundColor Cyan
Write-Host ""

docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start Docker Compose stack." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Services started successfully." -ForegroundColor Green
Write-Host "Frontend:  http://localhost:5173" -ForegroundColor White
Write-Host "Backend:   http://localhost:8080" -ForegroundColor White
Write-Host "API Docs:  http://localhost:8080/docs" -ForegroundColor White
Write-Host ""
Write-Host "Use .\stop.ps1 to stop all services." -ForegroundColor Yellow
