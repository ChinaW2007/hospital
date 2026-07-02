# ============================================================
# Hospital + HIS One-Key Restart Script (PowerShell)
# ============================================================
# This script stops and restarts all services in separate terminals
# More reliable than using PowerShell background jobs
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
            $processId = $proc.OwningProcess
            
            # Get service name
            $serviceName = ""
            switch ($port) {
                8000 { $serviceName = "hospital_back" }
                5175 { $serviceName = "hospital_front" }
                3001 { $serviceName = "HIS server" }
                3002 { $serviceName = "HIS client" }
            }
            
            try {
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                Write-Host "  [OK] Stopped $serviceName (PID: $processId)" -ForegroundColor Green
            } catch {
                Write-Host "  [FAIL] Failed to stop $serviceName" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "  Port ${port} - no process running" -ForegroundColor Gray
    }
}

# Kill any remaining node/python processes for these projects
Write-Host "`nCleaning up remaining processes..." -ForegroundColor Yellow

$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.Path -like "*hospital_back*"}
if ($pythonProcesses) {
    $pythonProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "  Killed hospital_back Python processes" -ForegroundColor Green
}

$nodeProcesses = Get-Process node -ErrorAction SilentlyContinue | Where-Object {$_.Path -like "*hospital*"}
if ($nodeProcesses) {
    $nodeProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "  Killed hospital Node.js processes" -ForegroundColor Green
}

Start-Sleep -Seconds 3
Write-Host "`nAll services stopped" -ForegroundColor Green

# Start all services using Start-Process (more reliable than Start-Job)
Write-Host "`n[2/2] Starting all services..." -ForegroundColor Yellow

# 1. hospital_back
Write-Host "  [1/4] Starting hospital_back..." -ForegroundColor Cyan
try {
    Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd '$HospitalBackPath'; python app.py" -WindowStyle Normal -ErrorAction Stop
    Write-Host "    hospital_back starting in new terminal (http://localhost:8000)" -ForegroundColor Green
} catch {
    Write-Host "    [FAIL] Failed to start hospital_back" -ForegroundColor Red
}

Start-Sleep -Seconds 2

# 2. hospital_front
Write-Host "  [2/4] Starting hospital_front..." -ForegroundColor Cyan
try {
    Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd '$HospitalFrontPath'; npm run dev" -WindowStyle Normal -ErrorAction Stop
    Write-Host "    hospital_front starting in new terminal (http://localhost:5175)" -ForegroundColor Green
} catch {
    Write-Host "    [FAIL] Failed to start hospital_front" -ForegroundColor Red
}

Start-Sleep -Seconds 2

# 3. HIS server
Write-Host "  [3/4] Starting HIS server..." -ForegroundColor Cyan
try {
    Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd '$HisServerPath'; npm run dev" -WindowStyle Normal -ErrorAction Stop
    Write-Host "    HIS server starting in new terminal (http://localhost:3001)" -ForegroundColor Green
} catch {
    Write-Host "    [FAIL] Failed to start HIS server" -ForegroundColor Red
}

Start-Sleep -Seconds 2

# 4. HIS client
Write-Host "  [4/4] Starting HIS client..." -ForegroundColor Cyan
try {
    Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd '$HisClientPath'; npm run dev" -WindowStyle Normal -ErrorAction Stop
    Write-Host "    HIS client starting in new terminal (https://localhost:3002)" -ForegroundColor Green
} catch {
    Write-Host "    [FAIL] Failed to start HIS client" -ForegroundColor Red
}

# Wait for services to start
Write-Host "`nWaiting for services to initialize..." -ForegroundColor Yellow
Write-Host "  (Services are starting in separate terminal windows)" -ForegroundColor Gray

# Progressive checking with retries
$maxRetries = 5
$retryDelay = 5

Write-Host "`nChecking service status (with retries)..." -ForegroundColor Yellow

$services = @(
    @{Name="hospital_back"; Port=8000; Url="http://localhost:8000"},
    @{Name="hospital_front"; Port=5175; Url="http://localhost:5175"},
    @{Name="HIS server"; Port=3001; Url="http://localhost:3001"},
    @{Name="HIS client"; Port=3002; Url="https://localhost:3002"}
)

$allRunning = $true
$retryCount = 0

while ($retryCount -lt $maxRetries) {
    $retryCount++
    Write-Host "`n  Attempt $retryCount/$maxRetries..." -ForegroundColor Gray
    
    $runningCount = 0
    foreach ($service in $services) {
        $connection = Get-NetTCPConnection -LocalPort $service.Port -State Listen -ErrorAction SilentlyContinue
        if ($connection) {
            $runningCount++
        }
    }
    
    if ($runningCount -eq 4) {
        Write-Host "  All services detected!" -ForegroundColor Green
        break
    } else {
        Write-Host "  Detected $runningCount/4 services running, waiting..." -ForegroundColor Yellow
        Start-Sleep -Seconds $retryDelay
    }
}

# Final status check
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  Final Service Status" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

foreach ($service in $services) {
    $connection = Get-NetTCPConnection -LocalPort $service.Port -State Listen -ErrorAction SilentlyContinue
    if ($connection) {
        Write-Host "  [OK] $($service.Name) running - $($service.Url)" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $($service.Name) not running" -ForegroundColor Red
        $allRunning = $false
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

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  Terminal Windows" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  4 terminal windows have been opened for each service"
Write-Host "  You can monitor logs in those terminals"
Write-Host "  Close terminals to stop individual services"

Write-Host "`nScript completed!" -ForegroundColor Cyan

if ($allRunning) {
    Write-Host "All services are running successfully!" -ForegroundColor Green
    Write-Host "You can now access the services using the links above" -ForegroundColor White
} else {
    Write-Host "Some services failed to start." -ForegroundColor Red
    Write-Host "Please check the terminal windows for error messages." -ForegroundColor Yellow
    Write-Host "Manual restart commands:" -ForegroundColor White
    Write-Host "  hospital_back: cd $HospitalBackPath; python app.py" -ForegroundColor Gray
    Write-Host "  hospital_front: cd $HospitalFrontPath; npm run dev" -ForegroundColor Gray
    Write-Host "  HIS server: cd $HisServerPath; npm run dev" -ForegroundColor Gray
    Write-Host "  HIS client: cd $HisClientPath; npm run dev" -ForegroundColor Gray
}