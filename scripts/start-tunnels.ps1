#!/usr/bin/env pwsh
# start-tunnels.ps1
# Starts the ngrok tunnel for the QAP Control Plane UI.
# API calls are proxied through Next.js (/api/agentOS/*) so only 1 tunnel is needed.
#
# Usage: .\scripts\start-tunnels.ps1
#
# UI URL (permanent): https://take-corsage-residency.ngrok-free.dev
# API calls route via: https://take-corsage-residency.ngrok-free.dev/api/agentOS/*

$ngrokBin = (Get-Command ngrok -ErrorAction SilentlyContinue).Source
if (-not $ngrokBin) {
    # fallback: WinGet install path
    $ngrokBin = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\" -Filter "ngrok.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
}
if (-not $ngrokBin) {
    Write-Error "ngrok not found. Run: winget install --id ngrok.ngrok"
    exit 1
}

Write-Host ""
Write-Host "Starting QAP tunnel via ngrok..." -ForegroundColor Cyan
Write-Host ""

$job = Start-Job -ScriptBlock { param($bin) & $bin start --all 2>&1 } -ArgumentList $ngrokBin

# Wait for ngrok local API
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    try {
        $t = (Invoke-RestMethod "http://localhost:4040/api/tunnels" -ErrorAction Stop).tunnels
        if ($t.Count -ge 1) { $ready = $true; break }
    } catch {}
}

if (-not $ready) {
    Write-Warning "ngrok may not have started. Check: http://localhost:4040"
    Receive-Job $job | Select-Object -Last 20; exit 1
}

$uiUrl = ((Invoke-RestMethod "http://localhost:4040/api/tunnels").tunnels | Where-Object { $_.config.addr -match ':3000' }).public_url -replace '^http:', 'https:'

Write-Host "╔═══════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  QAP is live                                                      ║" -ForegroundColor Green
Write-Host "╠═══════════════════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║  UI  (permanent) : $uiUrl" -ForegroundColor Green
Write-Host "║  API (proxied)   : $uiUrl/api/agentOS" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "The API URL is auto-detected — no Settings change needed." -ForegroundColor Yellow
Write-Host "Tunnels running. Press Ctrl+C to stop." -ForegroundColor Cyan

try {
    while ($true) { Start-Sleep -Seconds 30 }
} finally {
    Stop-Job $job; Remove-Job $job
    Write-Host "Tunnel stopped." -ForegroundColor Yellow
}
