# ============================================================
# Hospital + HIS System Startup Script (PowerShell)
# ============================================================
# This script starts all services using relative paths
# ============================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Hospital + HIS System Startup Script" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Get script directory (relative path support)
$ScriptDir = $PSScriptRoot
$HospitalDir = Join-Path $ScriptDir "hospital"

# Step 1: Stop existing services
Write-Host "`n[1/2] Stopping existing services..." -ForegroundColor Yellow

# Define ports and service names
$Ports = @{
    8000 = "hospital_back"
    5173 = "hospital_front"
    3001 = "HIS server"
    3002 = "HIS client"
}

# Stop services by port
foreach ($port in $Ports.Keys) {
    $serviceName = $Ports[$port]
    
    $processes = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    
    if ($processes) {
        Write-Host "  Stopping $serviceName on port $port..." -ForegroundColor Yellow
        
        foreach ($proc in $processes) {
            $processId = $proc.OwningProcess
            
            try {
                Stop-Process -Id $processId -Force -ErrorAction Stop
                Write-Host "    [OK] Killed PID: $processId" -ForegroundColor Green
            } catch {
                Write-Host "    [FAIL] Could not kill PID: $processId" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "  Port $port ($serviceName) - no process running" -ForegroundColor Gray
    }
}

# Additional cleanup
Write-Host "`n  Cleaning up remaining processes..." -ForegroundColor Yellow

# Kill Python processes
$pythonProcesses = Get-Process python, pythonw -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    foreach ($proc in $pythonProcesses) {
        try {
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)" -ErrorAction SilentlyContinue).CommandLine
            if ($cmdLine -and ($cmdLine -like "*app.py*" -or $cmdLine -like "*hospital*")) {
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                Write-Host "    Killed hospital Python process (PID: $($proc.Id))" -ForegroundColor Green
            }
        } catch {}
    }
}

# Kill Node processes
$nodeProcesses = Get-Process node -ErrorAction SilentlyContinue
if ($nodeProcesses) {
    foreach ($proc in $nodeProcesses) {
        try {
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)" -ErrorAction SilentlyContinue).CommandLine
            if ($cmdLine -and ($cmdLine -like "*hospital*" -or $cmdLine -like "*his*")) {
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                Write-Host "    Killed hospital/HIS Node process (PID: $($proc.Id))" -ForegroundColor Green
            }
        } catch {}
    }
}

# Wait for ports to be freed
Start-Sleep -Seconds 3
Write-Host "  All existing services stopped" -ForegroundColor Green

# Step 2: Start all services
Write-Host "`n[2/2] Starting all services..." -ForegroundColor Yellow

# 1. hospital_back (Python backend)
Write-Host "  [1/4] Starting hospital_back..." -ForegroundColor Cyan
$BackPath = Join-Path $HospitalDir "hospital_back"

# Check which Python command is available
$PythonCmd = ""
if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PythonCmd = "python3"
} else {
    Write-Host "    [ERROR] Python not found! Please install Python." -ForegroundColor Red
    Write-Host "    Skipping hospital_back..." -ForegroundColor Yellow
}

if ($PythonCmd) {
    try {
        $BackProcess = Start-Process -FilePath $PythonCmd -ArgumentList "app.py" -WorkingDirectory $BackPath -PassThru -WindowStyle Normal
        Write-Host "    hospital_back starting (http://localhost:8000) - PID: $($BackProcess.Id)" -ForegroundColor Green
    } catch {
        Write-Host "    [FAIL] Failed to start hospital_back" -ForegroundColor Red
        Write-Host "    Error: $_" -ForegroundColor Red
    }
}

# 等待后端启动
Write-Host "    Waiting for backend to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 8

# 2. HIS server (Node.js backend)
Write-Host "  [2/4] Starting HIS server..." -ForegroundColor Cyan
$HisServerPath = Join-Path $HospitalDir "his\server"

try {
    # 使用 cmd.exe /c 启动，先 cd 到正确目录再运行 npm
    $HisServerProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd /d `"$HisServerPath`" && npm run dev" -PassThru -WindowStyle Normal
    Write-Host "    HIS server starting (http://localhost:3001) - PID: $($HisServerProcess.Id)" -ForegroundColor Green
} catch {
    Write-Host "    [FAIL] Failed to start HIS server" -ForegroundColor Red
    Write-Host "    Error: $_" -ForegroundColor Red
}

# 等待HIS server启动
Write-Host "    Waiting for HIS server to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 8

# 3. hospital_front (Frontend)
Write-Host "  [3/4] Starting hospital_front..." -ForegroundColor Cyan
$FrontPath = Join-Path $HospitalDir "hospital_front"

try {
    $FrontProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd /d `"$FrontPath`" && npm run dev" -PassThru -WindowStyle Normal
    Write-Host "    hospital_front starting (http://localhost:5173) - PID: $($FrontProcess.Id)" -ForegroundColor Green
} catch {
    Write-Host "    [FAIL] Failed to start hospital_front" -ForegroundColor Red
    Write-Host "    Error: $_" -ForegroundColor Red
}

# 等待前端启动
Write-Host "    Waiting for hospital_front to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 8

# 4. HIS client (Frontend)
Write-Host "  [4/4] Starting HIS client..." -ForegroundColor Cyan
$HisClientPath = Join-Path $HospitalDir "his\client"

try {
    $HisClientProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd /d `"$HisClientPath`" && npm run dev" -PassThru -WindowStyle Normal
    Write-Host "    HIS client starting (http://localhost:3002) - PID: $($HisClientProcess.Id)" -ForegroundColor Green
} catch {
    Write-Host "    [FAIL] Failed to start HIS client" -ForegroundColor Red
    Write-Host "    Error: $_" -ForegroundColor Red
}

# Wait for services to initialize
Write-Host "`n  Waiting for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Verify service status
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  Service Status" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$allRunning = $true

foreach ($port in $Ports.Keys) {
    $serviceName = $Ports[$port]
    
    $connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    
    if ($connection) {
        $url = "http://localhost:$port"
        if ($port -eq 3002) {
            $url = "http://localhost:$port"
        }
        Write-Host "  [OK] $serviceName running - $url" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $serviceName not running" -ForegroundColor Red
        $allRunning = $false
    }
}

# Display access information
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  Quick Access" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Dashboard: " -NoNewline
Write-Host "http://localhost:5173" -ForegroundColor Green
Write-Host "  HIS System: " -NoNewline
Write-Host "http://localhost:3002" -ForegroundColor Green
Write-Host "  API Docs: " -NoNewline
Write-Host "http://localhost:8000/docs" -ForegroundColor Green

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  HIS Test Accounts" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Doctor: " -NoNewline
Write-Host "doctor1 / 123456" -ForegroundColor Yellow
Write-Host "  Pharmacist: " -NoNewline
Write-Host "pharmacist1 / 123456" -ForegroundColor Yellow
Write-Host "  Admin: " -NoNewline
Write-Host "admin / 123456" -ForegroundColor Yellow

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  Background Processes" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if ($BackProcess) {
    Write-Host "  hospital_back PID: $($BackProcess.Id)" -ForegroundColor White
}
if ($HisServerProcess) {
    Write-Host "  HIS server PID: $($HisServerProcess.Id)" -ForegroundColor White
}
if ($FrontProcess) {
    Write-Host "  hospital_front PID: $($FrontProcess.Id)" -ForegroundColor White
}
if ($HisClientProcess) {
    Write-Host "  HIS client PID: $($HisClientProcess.Id)" -ForegroundColor White
}

Write-Host "`n  Use " -NoNewline
Write-Host "stop-all.ps1" -ForegroundColor Yellow -NoNewline
Write-Host " to stop all services" -ForegroundColor White

# Final message
Write-Host "`n============================================================" -ForegroundColor Cyan

if ($allRunning) {
    Write-Host "All services are running successfully!" -ForegroundColor Green
    Write-Host "You can now access the services using the links above" -ForegroundColor White
} else {
    Write-Host "Some services failed to start." -ForegroundColor Red
    Write-Host "Please check the terminal windows for error messages." -ForegroundColor Yellow
    Write-Host "Manual start commands:" -ForegroundColor White
    Write-Host "  hospital_back: cd $BackPath; $PythonCmd app.py" -ForegroundColor Gray
    Write-Host "  HIS server: cd $HisServerPath; npm run dev" -ForegroundColor Gray
    Write-Host "  hospital_front: cd $FrontPath; npm run dev" -ForegroundColor Gray
    Write-Host "  HIS client: cd $HisClientPath; npm run dev" -ForegroundColor Gray
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Script completed!" -ForegroundColor Yellow