# start.ps1
# This script starts both the Python backend and the React frontend simultaneously

Write-Host "Starting Universal EDA Engine..." -ForegroundColor Cyan

# Determine correct paths based on script location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Check for existing processes on ports 8000 and 5173
Write-Host "Checking for port conflicts..." -ForegroundColor Cyan
$Port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
$Port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue

if ($Port8000) {
    $ConflictPID = $Port8000[0].OwningProcess
    Write-Host "Warning: Port 8000 is already in use by PID $ConflictPID." -ForegroundColor Yellow
    Write-Host "Please stop the existing process or run: taskkill /F /ConflictPID $ConflictPID" -ForegroundColor Red
}

if ($Port5173) {
    $ConflictPID = $Port5173[0].OwningProcess
    Write-Host "Warning: Port 5173 is already in use by PID $ConflictPID." -ForegroundColor Yellow
    Write-Host "Please stop the existing process or run: taskkill /F /ConflictPID $ConflictPID" -ForegroundColor Red
}

if ($Port8000 -or $Port5173) {
    Write-Host "`nStartup may fail due to port conflicts (WinError 10013)." -ForegroundColor Yellow
}

# Start Backend
Write-Host "Launching Backend (Port 8000)..." -ForegroundColor Green
Start-Process -Wait:$false -NoNewWindow:$false -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir'; .\venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000"

# Start Frontend
Write-Host "Launching Frontend (Port 5173)..." -ForegroundColor Green
Start-Process -Wait:$false -NoNewWindow:$false -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir\frontend'; npm run dev"
Write-Host "Services are starting in separate windows. Close those windows to stop them." -ForegroundColor Yellow

# Wait a few seconds for the frontend to initialize, then open the browser
Write-Host "Waiting for servers to start before opening the browser..." -ForegroundColor Cyan
Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"
