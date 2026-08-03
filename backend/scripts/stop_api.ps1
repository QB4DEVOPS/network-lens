param(
    [int]$MinPort = 8000,
    [int]$MaxPort = 8005
)

$ErrorActionPreference = "Stop"

function Get-LiveListenerPids([int]$Port) {
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { $_.OwningProcess } |
        Select-Object -Unique
}

function Stop-LiveListeners([int]$Port) {
    foreach ($procId in Get-LiveListenerPids -Port $Port) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "Stopping PID $procId ($($proc.ProcessName)) on port $Port"
        } else {
            Write-Host "Force-killing orphaned listener PID $procId on port $Port"
        }
        $prevErrorAction = $ErrorActionPreference
        $ErrorActionPreference = "SilentlyContinue"
        Start-Process -FilePath "taskkill.exe" -ArgumentList "/F", "/PID", "$procId", "/T" -Wait -WindowStyle Hidden | Out-Null
        $ErrorActionPreference = $prevErrorAction
        Start-Sleep -Milliseconds 200
    }
}

for ($port = $MinPort; $port -le $MaxPort; $port++) {
    Stop-LiveListeners -Port $port
}

Start-Sleep -Milliseconds 500

for ($attempt = 0; $attempt -lt 3; $attempt++) {
    $remainingAny = $false
    for ($port = $MinPort; $port -le $MaxPort; $port++) {
        $remaining = @(Get-LiveListenerPids -Port $port)
        if ($remaining.Count -gt 0) {
            $remainingAny = $true
            Write-Warning "Port $port still has listeners: $($remaining -join ', ') - retry $($attempt + 1)"
            Stop-LiveListeners -Port $port
        }
    }
    if (-not $remainingAny) {
        break
    }
    Start-Sleep -Milliseconds 500
}

for ($port = $MinPort; $port -le $MaxPort; $port++) {
    $remaining = @(Get-LiveListenerPids -Port $port)
    if ($remaining.Count -gt 0) {
        Write-Warning "Port $port still has listeners: $($remaining -join ', ')"
    }
}

Write-Host "Cleared API listeners on ports $MinPort-$MaxPort"
