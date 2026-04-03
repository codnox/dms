# Stop Distribution Management System Docker Compose stack

Write-Host "Stopping Distribution Management System (Docker Compose)..." -ForegroundColor Red
Write-Host ""

docker compose down
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to stop Docker Compose stack." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "All services stopped." -ForegroundColor Green
