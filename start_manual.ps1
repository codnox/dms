param(
    [string]$MySqlHost = "127.0.0.1",
    [int]$MySqlPort = 3306,
    [string]$DbUser = "dms_user",
    [string]$DbPassword = "dms_password",
    [string]$DbName = "distribution_management_system",
    [int]$BackendPort = 8080,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"

if (-not (Test-Path $backendDir)) {
    Write-Host "Backend folder not found: $backendDir" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $frontendDir)) {
    Write-Host "Frontend folder not found: $frontendDir" -ForegroundColor Red
    exit 1
}

$pythonExe = Join-Path $backendDir "venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = Join-Path $backendDir ".venv\Scripts\python.exe"
}
if (-not (Test-Path $pythonExe)) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $pythonExe = $pythonCmd.Source
    } else {
        Write-Host "Python not found. Create a backend venv or install Python first." -ForegroundColor Red
        exit 1
    }
}

$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCmd) {
    Write-Host "npm not found. Install Node.js first." -ForegroundColor Red
    exit 1
}

$apiBaseUrl = "http://localhost:$BackendPort/api"

$backendCommand = @"
`$host.UI.RawUI.WindowTitle = 'DMS Backend (Manual)'
Set-Location '$backendDir'
`$env:DB_HOST = '$MySqlHost'
`$env:DB_PORT = '$MySqlPort'
`$env:DB_USER = '$DbUser'
`$env:DB_PASSWORD = '$DbPassword'
`$env:DB_NAME = '$DbName'
`$env:HOST = '0.0.0.0'
`$env:PORT = '$BackendPort'
Write-Host 'Starting backend on port $BackendPort (MySQL: $MySqlHost:$MySqlPort)...' -ForegroundColor Cyan
& '$pythonExe' -m uvicorn app.main:app --reload --host 0.0.0.0 --port $BackendPort
"@

$frontendCommand = @"
`$host.UI.RawUI.WindowTitle = 'DMS Frontend (Manual)'
Set-Location '$frontendDir'
`$env:VITE_API_URL = '$apiBaseUrl'
Write-Host 'Starting frontend on port $FrontendPort (API: $apiBaseUrl)...' -ForegroundColor Cyan
npm run dev -- --host 0.0.0.0 --port $FrontendPort
"@

Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand) | Out-Null
Start-Sleep -Seconds 1
Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCommand) | Out-Null

Write-Host "Manual startup launched in separate terminals." -ForegroundColor Green
Write-Host "" 
Write-Host "Frontend:  http://localhost:$FrontendPort" -ForegroundColor White
Write-Host "Backend:   http://localhost:$BackendPort" -ForegroundColor White
Write-Host "API Docs:  http://localhost:$BackendPort/docs" -ForegroundColor White
Write-Host "MySQL:     $MySqlHost:$MySqlPort" -ForegroundColor White
Write-Host "" 
Write-Host "Example with custom MySQL port:" -ForegroundColor Yellow
Write-Host "  .\start_manual.ps1 -MySqlPort 3307" -ForegroundColor Gray
