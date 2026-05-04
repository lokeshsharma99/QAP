#!/usr/bin/env pwsh
# start-tunnels.ps1
# Two-account ngrok setup — dedicated permanent domains for UI and API.
#
# Account 1 (ngrok.yml)     → UI  : https://take-corsage-residency.ngrok-free.dev         (port 3000)
# Account 2 (ngrok-api.yml) → API : https://nonelectrized-portia-nonartistically.ngrok-free.dev  (port 8000)
#
# Usage: .\scripts\start-tunnels.ps1

$ngrokBin = (Get-Command ngrok -ErrorAction SilentlyContinue).Source
if (-not $ngrokBin) {
    # fallback: WinGet install path
    $ngrokBin = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\" -Filter "ngrok.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
}
if (-not $ngrokBin) {
    Write-Error "ngrok not found. Run: winget install --id ngrok.ngrok"
    exit 1
}

$cfg1 = "$env:LOCALAPPDATA\ngrok\ngrok.yml"
$cfg2 = "$env:LOCALAPPDATA\ngrok\ngrok-api.yml"

Write-Host ""
Write-Host "Starting QAP tunnels (2 ngrok accounts)..." -ForegroundColor Cyan
Write-Host ""

# ngrok doesn't support two authtokens in a single process — run two separate instances.
# Instance 1: UI tunnel (account 1, port 3000) — uses default ngrok web UI port 4040
$jobUI  = Start-Job -ScriptBlock { param($bin, $cfg) & $bin start --all --config $cfg 2>&1 } -ArgumentList $ngrokBin, $cfg1
# Instance 2: API tunnel (account 2, port 8000) — uses alternate web port 4041
$jobAPI = Start-Job -ScriptBlock { param($bin, $cfg) & $bin start --all --config $cfg --web-addr 127.0.0.1:4041 2>&1 } -ArgumentList $ngrokBin, $cfg2

# Wait for both ngrok local APIs
$ready1 = $false; $ready2 = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    if (-not $ready1) {
        try {
            $t = (Invoke-RestMethod "http://localhost:4040/api/tunnels" -ErrorAction Stop).tunnels
            if ($t.Count -ge 1) { $ready1 = $true }
        } catch {}
    }
    if (-not $ready2) {
        try {
            $t = (Invoke-RestMethod "http://localhost:4041/api/tunnels" -ErrorAction Stop).tunnels
            if ($t.Count -ge 1) { $ready2 = $true }
        } catch {}
    }
    if ($ready1 -and $ready2) { break }
}

if (-not $ready1) { Write-Warning "UI tunnel (4040) did not start. Check: http://localhost:4040"; Receive-Job $jobUI  | Select-Object -Last 10 }
if (-not $ready2) { Write-Warning "API tunnel (4041) did not start. Check: http://localhost:4041"; Receive-Job $jobAPI | Select-Object -Last 10 }

$uiUrl  = ((Invoke-RestMethod "http://localhost:4040/api/tunnels").tunnels | Select-Object -First 1).public_url -replace '^http:', 'https:'
$apiUrl = ((Invoke-RestMethod "http://localhost:4041/api/tunnels").tunnels | Select-Object -First 1).public_url -replace '^http:', 'https:'

Write-Host "╔══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  QAP is live (two permanent domains)                                        ║" -ForegroundColor Green
Write-Host "╠══════════════════════════════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║  UI  (permanent) : $uiUrl" -ForegroundColor Green
Write-Host "║  API (permanent) : $apiUrl" -ForegroundColor Cyan
Write-Host "╠══════════════════════════════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║  API URL is baked into the Docker build — no Settings change needed.        ║" -ForegroundColor Yellow
Write-Host "╚══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Tunnels running. Press Ctrl+C to stop." -ForegroundColor Cyan

try {
    while ($true) { Start-Sleep -Seconds 30 }
} finally {
    Stop-Job $jobUI;  Remove-Job $jobUI
    Stop-Job $jobAPI; Remove-Job $jobAPI
    Write-Host "Tunnels stopped." -ForegroundColor Yellow
}
