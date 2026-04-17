# start.ps1
# This script starts both the Python backend and the React frontend simultaneously

Write-Host "Starting Universal EDA Engine..." -ForegroundColor Cyan

# Determine correct paths based on script location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

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
