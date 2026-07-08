# ============================================================
# Hospital + HIS One-Key Stop Script (PowerShell)
# ============================================================
# 修复内容：
# 1. 修复 $pid 自动变量冲突（改用 $procId）
# 2. 补全端口列表（增加 5173）
# 3. 改用命令行匹配（不依赖需要管理员权限的 Path 属性）
# 4. 递归杀死子进程（防止 node 子进程残留）
# 5. 多次验证确保完全停止
# ============================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Hospital + HIS Stop Script" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 服务端口映射（含主端口和旧端口）
$Services = @(
    @{Name="hospital_back";  Port=8000;  Keywords=@("hospital_back", "app.py")},
    @{Name="hospital_front"; Port=5173;  Keywords=@("hospital_front")},
    @{Name="hospital_front_old"; Port=5175; Keywords=@("hospital_front")},
    @{Name="HIS server";     Port=3001;  Keywords=@("his\server", "his/server")},
    @{Name="HIS client";     Port=3002;  Keywords=@("his\client", "his/client")}
)

# ============================================================
# 函数：递归获取所有子进程
# ============================================================
function Get-ChildProcesses($parentId) {
    $children = @()
    try {
        $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$parentId" -ErrorAction SilentlyContinue |
                    Select-Object -ExpandProperty ProcessId
    } catch {}
    $result = @()
    foreach ($childId in $children) {
        $result += $childId
        $result += Get-ChildProcesses $childId
    }
    return $result
}

# ============================================================
# 函数：强制停止进程及其所有子进程
# ============================================================
function Stop-ProcessTree($processId, $serviceName) {
    # 先收集所有子进程
    $allPids = @($processId) + (Get-ChildProcesses $processId)

    foreach ($id in $allPids) {
        try {
            $proc = Get-Process -Id $id -ErrorAction SilentlyContinue
            if ($proc) {
                $procName = $proc.ProcessName
                Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
                Write-Host "    [OK] Killed PID $id ($procName)" -ForegroundColor Green
            }
        } catch {
            # 进程可能已退出，忽略
        }
    }
}

# ============================================================
# 步骤1：按端口停止进程
# ============================================================
Write-Host "`n[1/3] Stopping services by port..." -ForegroundColor Yellow

foreach ($svc in $Services) {
    $port = $svc.Port
    $name = $svc.Name

    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) {
        Write-Host "  Port $port ($name) - not listening" -ForegroundColor Gray
        continue
    }

    # 去重获取 OwningProcess
    $uniquePids = $connections | Select-Object -ExpandProperty OwningProcess -Unique

    foreach ($procId in $uniquePids) {
        # 注意：不能用 $pid（PowerShell 自动变量），用 $procId
        try {
            $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
            $procName = if ($proc) { $proc.ProcessName } else { "Unknown" }
        } catch {
            $procName = "Unknown"
        }

        Write-Host "  Stopping $name (port $port, PID $procId, $procName)..." -ForegroundColor White
        Stop-ProcessTree $procId $name
    }
}

# ============================================================
# 步骤2：按命令行匹配清理残留进程
# ============================================================
Write-Host "`n[2/3] Cleaning up residual processes by command line..." -ForegroundColor Yellow

# 使用 CIM/WMI 查询所有进程的命令行（不需要管理员权限）
$allProcs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine }

foreach ($svc in $Services) {
    foreach ($keyword in $svc.Keywords) {
        $matched = $allProcs | Where-Object { $_.CommandLine -like "*$keyword*" }

        foreach ($proc in $matched) {
            # 跳过当前脚本自身
            if ($proc.ProcessId -eq $PID) { continue }

            # 检查是否还活着
            $alive = Get-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue
            if (-not $alive) { continue }

            Write-Host "  Stopping $($svc.Name) residual process (PID $($proc.ProcessId))..." -ForegroundColor White
            Stop-ProcessTree $proc.ProcessId $svc.Name
        }
    }
}

# ============================================================
# 步骤3：最终清理 python/node 进程（兜底）
# ============================================================
Write-Host "`n[3/3] Final cleanup of python/node processes..." -ForegroundColor Yellow

# 通过命令行匹配项目路径的 python 进程
$pythonProcs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
               Where-Object { $_.CommandLine -like "*hospital*" -or $_.CommandLine -like "*app.py*" }
foreach ($proc in $pythonProcs) {
    Write-Host "  Killing python PID $($proc.ProcessId)..." -ForegroundColor White
    Stop-ProcessTree $proc.ProcessId "python"
}

# 通过命令行匹配项目路径的 node 进程
$nodeProcs = Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
             Where-Object { $_.CommandLine -like "*hospital*" -or $_.CommandLine -like "*his*" }
foreach ($proc in $nodeProcs) {
    Write-Host "  Killing node PID $($proc.ProcessId)..." -ForegroundColor White
    Stop-ProcessTree $proc.ProcessId "node"
}

Start-Sleep -Seconds 2

# ============================================================
# 验证：所有端口是否已释放
# ============================================================
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  Verification" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$allStopped = $true

foreach ($svc in $Services) {
    $connection = Get-NetTCPConnection -LocalPort $svc.Port -State Listen -ErrorAction SilentlyContinue
    if ($connection) {
        Write-Host "  [FAIL] $($svc.Name) still running on port $($svc.Port)" -ForegroundColor Red
        $allStopped = $false
    } else {
        Write-Host "  [OK] $($svc.Name) stopped (port $($svc.Port) free)" -ForegroundColor Green
    }
}

# 二次验证：检查残留进程
$residualPython = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
                  Where-Object { $_.CommandLine -like "*hospital*" -or $_.CommandLine -like "*app.py*" }
$residualNode = Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
                Where-Object { $_.CommandLine -like "*hospital*" -or $_.CommandLine -like "*his*" }

if ($residualPython -or $residualNode) {
    Write-Host "`n[WARN] Residual processes detected, force killing..." -ForegroundColor Yellow
    $residualPython | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    $residualNode | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  Result" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if ($allStopped -and -not $residualPython -and -not $residualNode) {
    Write-Host "  All services stopped successfully!" -ForegroundColor Green
} else {
    Write-Host "  Some services may still be running. Manual check:" -ForegroundColor Yellow
    Write-Host "    Get-Process python,node | Format-Table Id,ProcessName,Path" -ForegroundColor Gray
    Write-Host "    Stop-Process -Name python,node -Force" -ForegroundColor Gray
}
