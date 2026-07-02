# ============================================================
# Hospital + HIS One-Key Stop Script (PowerShell)
# ============================================================
# This script stops all running services
# ============================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Hospital + HIS Stop Script" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$Ports = @(8000, 5175, 3001, 3002)

# Stop all services
Write-Host "`nStopping all services..." -ForegroundColor Yellow

foreach ($port in $Ports) {
    $processes = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($processes) {
        # Get unique process IDs only
        $uniquePids = @($processes | Select-Object -ExpandProperty OwningProcess -Unique)
        
        foreach ($pid in $uniquePids) {
            # Get process name
            try {
                $processName = (Get-Process -Id $pid -ErrorAction SilentlyContinue).ProcessName
            } catch {
                $processName = "Unknown"
            }
            
            # Map port to service name
            $serviceName = ""
            switch ($port) {
                8000 { $serviceName = "hospital_back" }
                5175 { $serviceName = "hospital_front" }
                3001 { $serviceName = "HIS server" }
                3002 { $serviceName = "HIS client" }
            }
            
            try {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Host "  [OK] Stopped $serviceName (port $port, PID: $pid, Process: $processName)" -ForegroundColor Green
            } catch {
                Write-Host "  [FAIL] Failed to stop $serviceName (port $port)" -ForegroundColor Red
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

Start-Sleep -Seconds 2

# Verify all services are stopped
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  Verification" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$allStopped = $true
$services = @(
    @{Name="hospital_back"; Port=8000},
    @{Name="hospital_front"; Port=5175},
    @{Name="HIS server"; Port=3001},
    @{Name="HIS client"; Port=3002}
)

foreach ($service in $services) {
    $connection = Get-NetTCPConnection -LocalPort $service.Port -State Listen -ErrorAction SilentlyContinue
    if ($connection) {
        Write-Host "  [FAIL] $($service.Name) still running on port $($service.Port)" -ForegroundColor Red
        $allStopped = $false
    } else {
        Write-Host "  [OK] $($service.Name) stopped" -ForegroundColor Green
    }
}

Write-Host "`nScript completed!" -ForegroundColor Cyan

if ($allStopped) {
    Write-Host "All services have been stopped successfully!" -ForegroundColor Green
} else {
    Write-Host "Some services failed to stop. Manual intervention required:" -ForegroundColor Red
    Write-Host "  Check processes: Get-Process | Where-Object {$_.ProcessName -eq 'python' -or $_.ProcessName -eq 'node'}"
    Write-Host "  Force kill: Stop-Process -Name python,node -Force"
}