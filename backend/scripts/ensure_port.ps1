param(
    [int]$PreferredPort = 8000,
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
            Stop-Process -Id $procId -Force
        }
    }
}

function Test-PortFree([int]$Port) {
    return @(Get-LiveListenerPids -Port $Port).Count -eq 0
}

Stop-LiveListeners -Port $PreferredPort

$chosen = $null
for ($port = $PreferredPort; $port -le $MaxPort; $port++) {
    Stop-LiveListeners -Port $port
    Start-Sleep -Milliseconds 400
    if (Test-PortFree -Port $port) {
        $chosen = $port
        break
    }
}

if (-not $chosen) {
    Write-Error "No free port between $PreferredPort and $MaxPort"
}

$backendRoot = Split-Path $PSScriptRoot -Parent
$portFile = Join-Path $backendRoot ".api_port"
$envFile = Join-Path (Split-Path $backendRoot -Parent) "frontend\.env"

Set-Content -Path $portFile -Value $chosen -NoNewline
Set-Content -Path $envFile -Value "VITE_API_PORT=$chosen" -NoNewline

Write-Host "API port: $chosen"
Write-Host "Wrote $portFile and $envFile"
Write-Output $chosen
