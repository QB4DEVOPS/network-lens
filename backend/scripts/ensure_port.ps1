param(
    [int]$PreferredPort = 8000,
    [int]$MaxPort = 8005
)

$ErrorActionPreference = "Stop"

$backendRoot = Split-Path $PSScriptRoot -Parent
$portFile = Join-Path $backendRoot ".api_port"
$envFile = Join-Path (Split-Path $backendRoot -Parent) "frontend\.env"

if (Test-Path $portFile) {
    $fromFile = (Get-Content $portFile -Raw).Trim()
    if ($fromFile -match '^\d+$') {
        $parsed = [int]$fromFile
        if ($parsed -ge 8000 -and $parsed -le $MaxPort) {
            $PreferredPort = $parsed
        }
    }
}

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

function Test-PortFree([int]$Port) {
    return @(Get-LiveListenerPids -Port $Port).Count -eq 0
}

# Clear the whole dev port range so ghost uvicorn reloaders cannot serve stale code.
for ($port = 8000; $port -le $MaxPort; $port++) {
    Stop-LiveListeners -Port $port
}
Start-Sleep -Milliseconds 500

$chosen = $null
for ($port = $PreferredPort; $port -le $MaxPort; $port++) {
    if (Test-PortFree -Port $port) {
        $chosen = $port
        break
    }
}

if (-not $chosen) {
    for ($port = 8000; $port -lt $PreferredPort; $port++) {
        if (Test-PortFree -Port $port) {
            $chosen = $port
            break
        }
    }
}

if (-not $chosen) {
    Write-Error "No free port between 8000 and $MaxPort"
}

Set-Content -Path $portFile -Value $chosen -NoNewline
Set-Content -Path $envFile -Value "VITE_API_PORT=$chosen" -NoNewline

Write-Host "API port: $chosen"
Write-Host "Wrote $portFile and $envFile"
Write-Output $chosen
