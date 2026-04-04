param(
    [string]$MySqlServiceName = "MySQL",
    [string]$MySqlBaseDir = "C:\mysql",
    [string]$RootPassword = "rootpassword",
    [string]$AppUser = "dms_user",
    [string]$AppPassword = "dms_password",
    [string]$DbName = "distribution_management_system"
)

$ErrorActionPreference = "Stop"

function Assert-Admin {
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this script in an Administrator PowerShell window."
    }
}

Assert-Admin

$mysqldExe = Join-Path $MySqlBaseDir "bin\mysqld.exe"
$mysqlExe = Join-Path $MySqlBaseDir "bin\mysql.exe"
$mysqlAdminExe = Join-Path $MySqlBaseDir "bin\mysqladmin.exe"
$defaultsFile = Join-Path $MySqlBaseDir "my.ini"

if (-not (Test-Path $mysqldExe)) { throw "mysqld.exe not found at $mysqldExe" }
if (-not (Test-Path $mysqlExe)) { throw "mysql.exe not found at $mysqlExe" }
if (-not (Test-Path $mysqlAdminExe)) { throw "mysqladmin.exe not found at $mysqlAdminExe" }
if (-not (Test-Path $defaultsFile)) { throw "MySQL config not found at $defaultsFile" }

Write-Host "Stopping service $MySqlServiceName..." -ForegroundColor Cyan
$service = Get-Service -Name $MySqlServiceName -ErrorAction Stop
if ($service.Status -ne "Stopped") {
    Stop-Service -Name $MySqlServiceName -Force
    $stopDeadline = (Get-Date).AddSeconds(45)
    do {
        Start-Sleep -Seconds 1
        $service.Refresh()
    } while ($service.Status -ne "Stopped" -and (Get-Date) -lt $stopDeadline)

    if ($service.Status -ne "Stopped") {
        throw "MySQL service did not stop within timeout."
    }
}

Write-Host "Starting temporary MySQL instance with --skip-grant-tables..." -ForegroundColor Cyan
$tempProcess = Start-Process -FilePath $mysqldExe -ArgumentList @(
    "--defaults-file=$defaultsFile",
    "--skip-grant-tables",
    "--skip-networking=0",
    "--console"
) -PassThru -WindowStyle Hidden

$mysqlErrLog = Get-ChildItem (Join-Path $MySqlBaseDir "data") -Filter "*.err" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

Write-Host "Waiting for temporary MySQL readiness..." -ForegroundColor Cyan
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    if ($tempProcess.HasExited) {
        break
    }

    cmd /c "\"$mysqlAdminExe\" -h 127.0.0.1 -P 3306 -u root ping >nul 2>nul"
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        break
    }

    Start-Sleep -Seconds 1
}

if (-not $ready) {
    if ($tempProcess -and -not $tempProcess.HasExited) {
        try { Stop-Process -Id $tempProcess.Id -Force -ErrorAction SilentlyContinue } catch {}
    }

    if ($mysqlErrLog) {
        Write-Host "MySQL startup log tail ($($mysqlErrLog.FullName)):" -ForegroundColor Yellow
        Get-Content $mysqlErrLog.FullName -Tail 40 | ForEach-Object { Write-Host $_ }
    }

    try {
        Start-Service -Name $MySqlServiceName -ErrorAction SilentlyContinue
    } catch {}

    throw "Temporary MySQL instance did not become ready on 127.0.0.1:3306."
}

$bootstrapSql = @"
FLUSH PRIVILEGES;
ALTER USER 'root'@'localhost' IDENTIFIED BY '$RootPassword';
CREATE DATABASE IF NOT EXISTS $DbName;
CREATE USER IF NOT EXISTS '$AppUser'@'localhost' IDENTIFIED BY '$AppPassword';
ALTER USER '$AppUser'@'localhost' IDENTIFIED BY '$AppPassword';
GRANT ALL PRIVILEGES ON $DbName.* TO '$AppUser'@'localhost';
FLUSH PRIVILEGES;
"@

Write-Host "Applying credential reset and app user grants..." -ForegroundColor Cyan
& $mysqlExe -h 127.0.0.1 -P 3306 -u root -e $bootstrapSql
if ($LASTEXITCODE -ne 0) {
    try { Stop-Process -Id $tempProcess.Id -Force -ErrorAction SilentlyContinue } catch {}
    try {
        Start-Service -Name $MySqlServiceName -ErrorAction SilentlyContinue
    } catch {}
    throw "Failed to apply MySQL credential reset SQL."
}

Write-Host "Stopping temporary MySQL instance..." -ForegroundColor Cyan
try {
    Stop-Process -Id $tempProcess.Id -Force -ErrorAction SilentlyContinue
} catch {}
Start-Sleep -Seconds 2

Write-Host "Starting service $MySqlServiceName..." -ForegroundColor Cyan
Start-Service -Name $MySqlServiceName
Start-Sleep -Seconds 2

Write-Host "Verifying app login..." -ForegroundColor Cyan
& $mysqlExe -h 127.0.0.1 -P 3306 -u $AppUser -p$AppPassword -D $DbName -e "SELECT 1;"
if ($LASTEXITCODE -ne 0) {
    throw "Verification failed for app login."
}

Write-Host "MySQL credentials reset complete." -ForegroundColor Green
Write-Host "App user: $AppUser" -ForegroundColor White
Write-Host "Database: $DbName" -ForegroundColor White
Write-Host "Now run .\start_manual.ps1" -ForegroundColor Yellow
