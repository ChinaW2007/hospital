# ============================================================
# Hospital + HIS System Stop Script (PowerShell)
# ============================================================
# This script stops all services forcefully
# ============================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Hospital + HIS System Stop Script" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Write-Host "`n[1/1] Stopping all services..." -ForegroundColor Yellow

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
    
    # Find processes listening on this port
    $processes = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    
    if ($processes) {
        Write-Host "  Stopping $serviceName on port $port..." -ForegroundColor Yellow
        
        foreach ($proc in $processes) {
            $processId = $proc.OwningProcess
            
            try {
                # Get process name for info
                $processName = (Get-Process -Id $processId -ErrorAction SilentlyContinue).ProcessName
                
                # Force kill the process
                Stop-Process -Id $processId -Force -ErrorAction Stop
                Write-Host "    [OK] Killed $processName (PID: $processId)" -ForegroundColor Green
            } catch {
                Write-Host "    [FAIL] Could not kill PID: $processId" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "  Port $port ($serviceName) - no process running" -ForegroundColor Gray
    }
}

# Additional cleanup: Kill Python processes related to hospital
Write-Host "`n  Cleaning up Python processes..." -ForegroundColor Yellow

$pythonProcesses = Get-Process python, pythonw -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    foreach ($proc in $pythonProcesses) {
        try {
            # Check if it's running app.py or related to hospital
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)" -ErrorAction SilentlyContinue).CommandLine
            
            if ($cmdLine -and ($cmdLine -like "*app.py*" -or $cmdLine -like "*hospital*")) {
                Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                Write-Host "    Killed hospital Python process (PID: $($proc.Id))" -ForegroundColor Green
            }
        } catch {
            # Ignore errors for cleanup
        }
    }
}

# Kill Node processes related to hospital/HIS
Write-Host "  Cleaning up Node processes..." -ForegroundColor Yellow

$nodeProcesses = Get-Process node -ErrorAction SilentlyContinue
if ($nodeProcesses) {
    foreach ($proc in $nodeProcesses) {
        try {
            # Check if it's related to hospital or HIS
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)" -ErrorAction SilentlyContinue).CommandLine
            
            if ($cmdLine -and ($cmdLine -like "*hospital*" -or $cmdLine -like "*his*")) {
                Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                Write-Host "    Killed hospital/HIS Node process (PID: $($proc.Id))" -ForegroundColor Green
            }
        } catch {
            # Ignore errors for cleanup
        }
    }
}

# Wait for processes to terminate
Start-Sleep -Seconds 2

# Final verification
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  Verification" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$allStopped = $true

foreach ($port in $Ports.Keys) {
    $serviceName = $Ports[$port]
    
    $connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    
    if ($connection) {
        Write-Host "  [FAIL] $serviceName still running on port $port" -ForegroundColor Red
        $allStopped = $false
    } else {
        Write-Host "  [OK] $serviceName stopped" -ForegroundColor Green
    }
}

Write-Host "`n============================================================" -ForegroundColor Cyan

if ($allStopped) {
    Write-Host "All services stopped successfully!" -ForegroundColor Green
} else {
    Write-Host "Some services may still be running." -ForegroundColor Red
    Write-Host "Try running the script again or manually kill processes." -ForegroundColor Yellow
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Script completed!" -ForegroundColor Yellow