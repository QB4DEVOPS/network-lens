# Fail if tracked files contain patterns that should not go to the public repo.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$patterns = @(
    'wwwin-github\.cisco\.com',
    'cx-usps-auto',
    'sac-rohosfor',
    'atlassian\.net',
    'roberthosford',
    'C:\\dev\\',
    'C:/dev/',
    'Users\\rohosfor',
    'Local path:'
)

$exclude = @('docs/PUBLIC_PUSH.md', 'scripts/verify-public-clean.ps1')
$hits = @()

foreach ($pattern in $patterns) {
    $raw = git grep -n -i -E $pattern HEAD 2>$null
    if (-not $raw) { continue }
    foreach ($line in $raw) {
        $skip = $false
        foreach ($ex in $exclude) {
            if ($line.Contains($ex)) {
                $skip = $true
                break
            }
        }
        if (-not $skip) { $hits += $line }
    }
}

if ($hits.Count -gt 0) {
    Write-Host "PUBLIC PUSH BLOCKED - internal metadata in tracked files:" -ForegroundColor Red
    $hits | ForEach-Object { Write-Host $_ }
    Write-Host ""
    Write-Host "Move internal notes to README.internal.md (gitignored) or remove before pushing public."
    exit 1
}

Write-Host "OK - no blocked patterns in tracked files at HEAD." -ForegroundColor Green
exit 0
