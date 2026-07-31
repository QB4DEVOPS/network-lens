# Run Network Lens API — kills stale listeners, syncs frontend port, runs smoke tests first.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
    & $python -m pip install -r requirements.txt
}

$port = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "scripts\ensure_port.ps1")
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "Running smoke tests (in-process)..."
& $python scripts\smoke_test.py
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "Starting API on http://127.0.0.1:$port"
Write-Host "Frontend .env synced — restart frontend if it is already running."
& $python -m uvicorn app.main:app --reload --port $port
