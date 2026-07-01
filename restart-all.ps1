# ============================================================
# Hospital + HIS One-Key Restart Script
# ============================================================
# This script stops and restarts all services in background
# ============================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Hospital + HIS Restart Script" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$HospitalBackPath = "d:\Demos\hospital\hospital\hospital_back"
$HospitalFrontPath = "d:\Demos\hospital\hospital\hospital_front"
$HisServerPath = "d:\Demos\hospital\hospital\his\server"
$HisClientPath = "d:\Demos\hospital\hospital\his\client"

$Ports = @(8000, 5175, 3001, 3002)

# Stop all services
Write-Host "`n[1/2] Stopping all services..." -ForegroundColor Yellow

foreach ($port in $Ports) {
    $processes = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($processes) {
        foreach ($proc in $processes) {
            $pid = $proc.OwningProcess
            try {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Host "  Stopped port ${port} process (PID: ${pid})" -ForegroundColor Green
            } catch {
                Write-Host "  Failed to stop port ${port} process" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "  Port ${port} - no process running" -ForegroundColor Gray
    }
}

# Kill any remaining node/python processes for these projects
Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.Path -like "*hospital_back*"} | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process node -ErrorAction SilentlyContinue | Where-Object {$_.Path -like "*hospital*"} | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2
Write-Host "All services stopped" -ForegroundColor Green

# Start all services in background
Write-Host "`n[2/2] Starting all services..." -ForegroundColor Yellow

# 1. hospital_back
Write-Host "  [1/4] Starting hospital_back..." -ForegroundColor Cyan
$job1 = Start-Job -ScriptBlock {
    Set-Location "d:\Demos\hospital\hospital\hospital_back"
    python app.py
}
Write-Host "    hospital_back starting (http://localhost:8000)" -ForegroundColor Green

# 2. hospital_front
Write-Host "  [2/4] Starting hospital_front..." -ForegroundColor Cyan
$job2 = Start-Job -ScriptBlock {
    Set-Location "d:\Demos\hospital\hospital\hospital_front"
    npm run dev
}
Write-Host "    hospital_front starting (http://localhost:5175)" -ForegroundColor Green

# 3. HIS server
Write-Host "  [3/4] Starting HIS server..." -ForegroundColor Cyan
$job3 = Start-Job -ScriptBlock {
    Set-Location "d:\Demos\hospital\hospital\his\server"
    npm run dev
}
Write-Host "    HIS server starting (http://localhost:3001)" -ForegroundColor Green

# 4. HIS client
Write-Host "  [4/4] Starting HIS client..." -ForegroundColor Cyan
$job4 = Start-Job -ScriptBlock {
    Set-Location "d:\Demos\hospital\hospital\his\client"
    npm run dev
}
Write-Host "    HIS client starting (https://localhost:3002)" -ForegroundColor Green

# Wait for services to start
Write-Host "`nWaiting for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Check service status
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  Service Status" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$services = @(
    @{Name="hospital_back"; Port=8000; Url="http://localhost:8000"},
    @{Name="hospital_front"; Port=5175; Url="http://localhost:5175"},
    @{Name="HIS server"; Port=3001; Url="http://localhost:3001"},
    @{Name="HIS client"; Port=3002; Url="https://localhost:3002"}
)

$allRunning = $true
foreach ($service in $services) {
    $connection = Get-NetTCPConnection -LocalPort $service.Port -State Listen -ErrorAction SilentlyContinue
    if ($connection) {
        Write-Host "  [OK] $($service.Name) running - $($service.Url)" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $($service.Name) not running" -ForegroundColor Red
        $allRunning = false
    }
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  Quick Access" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Dashboard: http://localhost:5175"
Write-Host "  HIS System: https://localhost:3002"
Write-Host "  API Docs: http://localhost:8000/docs"

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  HIS Test Accounts" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Doctor: doctor1 / 123456"
Write-Host "  Pharmacist: pharmacist1 / 123456"
Write-Host "  Admin: admin / 123456"

Write-Host "`nScript completed!" -ForegroundColor Cyan

if ($allRunning) {
    Write-Host "All services are running successfully!" -ForegroundColor Green
} else {
    Write-Host "Some services failed to start. Check the job output:" -ForegroundColor Yellow
    Write-Host "  Get-Job | Receive-Job" -ForegroundColor White
}