# Push to the public remote only after a cleanliness scan (and optional validate).
param(
    [switch]$Validate,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

& (Join-Path $PSScriptRoot "verify-public-clean.ps1")
if ($LASTEXITCODE -ne 0) { exit 1 }

if ($Validate) {
    Write-Host "Running validate.bat..."
    & (Join-Path (Get-Location) "validate.bat")
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

if ($DryRun) {
    Write-Host "Dry run - would push: git push public main"
    git log public/main..HEAD --oneline
    exit 0
}

Write-Host "Pushing to public (QB4DEVOPS/network-lens)..."
git push public main
exit $LASTEXITCODE
