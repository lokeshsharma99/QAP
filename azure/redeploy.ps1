#!/usr/bin/env pwsh
# =============================================================================
# Quality Autopilot — One-Click Redeploy Script
# =============================================================================
#
# Usage:
#   .\azure\redeploy.ps1
#
# What this does (zero interaction required):
#   1. Reads azure/.deploy-state.json for ACR + DB + env details
#   2. Reads .env for any local overrides (model keys, etc.)
#   3. Builds a new timestamped qap-api image and pushes to ACR
#   4. Updates qap-api Container App to the new image
#   5. Re-applies ALL secrets + env vars (prevents config drift after --yaml updates)
#   6. Waits for the new revision to reach Running state
#   7. Probes /health — prints final status
#
# Prerequisites:
#   - azure/.deploy-state.json must exist (created by deploy.ps1)
#   - .env must exist (project root)
#   - az login already done (az account show succeeds)
#   - Docker Desktop running
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$REPO_ROOT    = (Resolve-Path "$PSScriptRoot\..").Path
$STATE_FILE   = "$PSScriptRoot\.deploy-state.json"
$ENV_FILE     = "$REPO_ROOT\.env"
$PARAMS_FILE  = "$PSScriptRoot\parameters.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Write-Step { param([string]$Msg) Write-Host "`n▶  $Msg" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Msg) Write-Host "   ✅  $Msg" -ForegroundColor Green }
function Write-Warn { param([string]$Msg) Write-Host "   ⚠   $Msg" -ForegroundColor Yellow }
function Write-Fail { param([string]$Msg) Write-Host "   ✗  $Msg" -ForegroundColor Red; exit 1 }

function Invoke-Az {
    $raw = az @args 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Fail "az $($args[0]) failed: $raw" }
    $result = ($raw | Where-Object { $_ -notmatch '^(WARNING|INFO|ERROR):' }) -join "`n"
    return $result.Trim()
}

function Read-DotEnv {
    param([string]$Path)
    $vars = @{}
    if (-not (Test-Path $Path)) { return $vars }
    foreach ($line in Get-Content $Path) {
        $line = $line.Trim()
        if ($line -eq '' -or $line.StartsWith('#')) { continue }
        if ($line -match '^([^=]+)=(.*)$') {
            $k = $Matches[1].Trim()
            $v = $Matches[2].Trim().Trim('"').Trim("'")
            $vars[$k] = $v
        }
    }
    return $vars
}

# ---------------------------------------------------------------------------
# Validate prerequisites
# ---------------------------------------------------------------------------
Write-Step "Checking prerequisites"

if (-not (Get-Command az -ErrorAction SilentlyContinue))     { Write-Fail "Azure CLI not found" }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Write-Fail "Docker not found" }
if (-not (Test-Path $STATE_FILE))  { Write-Fail "State file not found: $STATE_FILE — run .\azure\deploy.ps1 first" }
if (-not (Test-Path $PARAMS_FILE)) { Write-Fail "Parameters file not found: $PARAMS_FILE" }

$account = az account show --query '{name:name,state:state}' -o json 2>&1 | ConvertFrom-Json
if (-not $account -or $account.state -ne 'Enabled') { Write-Fail "Not logged in to Azure. Run: az login" }
Write-Ok "Azure account: $($account.name)"

# ---------------------------------------------------------------------------
# Load state + params + .env
# ---------------------------------------------------------------------------
Write-Step "Loading deploy state and parameters"

$state = Get-Content $STATE_FILE | ConvertFrom-Json
$params = Get-Content $PARAMS_FILE | ConvertFrom-Json
$env_vars = Read-DotEnv $ENV_FILE

$ACR_SERVER       = $state.acrServer
$ACR_NAME         = $state.acrName
$DB_HOST          = $state.dbHost
$USE_MANAGED_PG   = [bool]$state.useManagedPg
$MAX_API_REPLICAS = if ($state.maxApiReplicas) { [int]$state.maxApiReplicas } else { 3 }

$RESOURCE_GROUP   = $params.resourceGroup
$PREFIX           = $params.parameters.prefix.value   ?? 'qap'
$ENV_NAME         = $params.parameters.env.value      ?? 'dev'
$RESOURCE_PREFIX  = "${PREFIX}-${ENV_NAME}"
$APP_NAME         = "${RESOURCE_PREFIX}-api"
$ACA_ENV_NAME     = "${RESOURCE_PREFIX}-env"

$DB_PASS        = $params.parameters.dbPass.value
$SESSION_SECRET = $params.parameters.sessionSecret.value ?? (New-Guid).Guid

$TAG = (Get-Date -Format 'yyyyMMdd-HHmm')
$API_IMAGE = "${ACR_SERVER}/qap-api:${TAG}"

Write-Ok "ACR           : $ACR_SERVER"
Write-Ok "App           : $APP_NAME"
Write-Ok "DB host       : $DB_HOST"
Write-Ok "New image tag : $TAG"

# ---------------------------------------------------------------------------
# Phase 1 — ACR login + build + push
# ---------------------------------------------------------------------------
Write-Step "Phase 1 — Logging in to ACR"
Invoke-Az acr login --name $ACR_NAME | Out-Null
Write-Ok "ACR login ok"

Write-Step "Phase 1 — Building qap-api Docker image"
docker build -t $API_IMAGE -f "$REPO_ROOT\Dockerfile" $REPO_ROOT
if ($LASTEXITCODE -ne 0) { Write-Fail "Docker build failed" }
Write-Ok "Built: $API_IMAGE"

Write-Step "Phase 1 — Pushing image to ACR"
docker push $API_IMAGE
if ($LASTEXITCODE -ne 0) { Write-Fail "Docker push failed" }
Write-Ok "Pushed: $API_IMAGE"

# ---------------------------------------------------------------------------
# Phase 2 — Assemble full secrets + env var list
# (Mirrors deploy.ps1 Phase 3 exactly so no config drift occurs)
# ---------------------------------------------------------------------------
Write-Step "Phase 2 — Building secrets + env var manifest"

$ACR_USER = Invoke-Az acr credential show --name $ACR_NAME --query username -o tsv
$ACR_PASS = Invoke-Az acr credential show --name $ACR_NAME --query 'passwords[0].value' -o tsv

# Helper: prefer params.json → fallback to .env → fallback to default
function Get-Val {
    param([string]$ParamKey, [string]$EnvKey = '', [string]$Default = '')
    $v = $null
    try { $v = (Invoke-Expression "`$params.parameters.$ParamKey.value") } catch {}
    if ($v) { return $v }
    if ($EnvKey -and $env_vars[$EnvKey]) { return $env_vars[$EnvKey] }
    return $Default
}

$APP_BASE_URL  = Get-Val 'appBaseUrl' 'APP_BASE_URL' "http://localhost:3000"
$AUT_BASE_URL  = Get-Val 'autBaseUrl'  'AUT_BASE_URL' 'https://lokeshsharma99.github.io/GDS-Demo-App/'

# Core env vars
$apiEnv = @(
    "RUNTIME_ENV=prod"
    "PYTHONPATH=/app"
    "AGENTOS_URL=http://localhost:8000"
    "DB_HOST=$DB_HOST"
    "DB_PORT=5432"
    "DB_USER=ai"
    "DB_DATABASE=ai"
    "WAIT_FOR_DB=True"
    "DB_SSL_REQUIRED=$(if ($USE_MANAGED_PG) { 'true' } else { 'false' })"
    "MODEL_PROVIDER=$(Get-Val 'modelProvider' 'MODEL_PROVIDER' 'nvidia')"
    "OPENROUTER_BASE_URL=$(Get-Val 'openrouterBaseUrl' 'OPENROUTER_BASE_URL' 'https://api.kilo.ai/api/openrouter/v1')"
    "KILO_API_URL=$(Get-Val 'kiloApiUrl' 'KILO_API_URL' 'https://api.kilo.ai')"
    "AUT_BASE_URL=$AUT_BASE_URL"
    "AUT_GITHUB_OWNER=$(Get-Val 'autGithubOwner' 'AUT_GITHUB_OWNER' 'lokeshsharma99')"
    "AUT_GITHUB_REPO=$(Get-Val 'autGithubRepo' 'AUT_GITHUB_REPO' 'GDS-Demo-App')"
    "GITHUB_MCP_URL=http://${RESOURCE_PREFIX}-github-mcp"
    "PLAYWRIGHT_MCP_URL=http://${RESOURCE_PREFIX}-playwright-mcp:8931"
    "ADO_MCP_URL=http://${RESOURCE_PREFIX}-ado-mcp/mcp"
    "ATLASSIAN_MCP_URL=http://${RESOURCE_PREFIX}-atlassian-mcp/mcp"
    "SESSION_TTL_DAYS=30"
    "AZURE_DEVOPS_URL=$(Get-Val 'azureDevOpsUrl' 'AZURE_DEVOPS_URL' '')"
    "AZURE_DEVOPS_EMAIL=$(Get-Val 'azureDevOpsEmail' 'AZURE_DEVOPS_EMAIL' '')"
    "ATLASSIAN_URL=$(Get-Val 'atlassianUrl' 'ATLASSIAN_URL' '')"
    "ATLASSIAN_EMAIL=$(Get-Val 'atlassianEmail' 'ATLASSIAN_EMAIL' '')"
    "JIRA_URL=$(Get-Val 'atlassianUrl' 'JIRA_URL' '')"
    "JIRA_USERNAME=$(Get-Val 'atlassianEmail' 'JIRA_USERNAME' '')"
    "CONFLUENCE_URL=$(Get-Val 'atlassianUrl' 'CONFLUENCE_URL' '')/wiki"
    "CONFLUENCE_EMAIL=$(Get-Val 'atlassianEmail' 'CONFLUENCE_EMAIL' '')"
    "NVIDIA_MODEL=$(Get-Val 'nvidiaModel' 'NVIDIA_MODEL' 'qwen/qwen3-coder-480b-a35b-instruct')"
    "OLLAMA_BASE_URL=$(Get-Val 'ollamaBaseUrl' 'OLLAMA_BASE_URL' 'http://host.docker.internal:11434')"
    "OLLAMA_MODEL=$(Get-Val 'ollamaModel' 'OLLAMA_MODEL' 'minimax-m2.7:cloud')"
    "SLACK_CHANNEL_ID=$(Get-Val 'slackChannelId' 'SLACK_CHANNEL_ID' '')"
    "SMTP_HOST=$(Get-Val 'smtpHost' 'SMTP_HOST' 'smtp-relay.brevo.com')"
    "SMTP_PORT=$(Get-Val 'smtpPort' 'SMTP_PORT' '587')"
    "SMTP_USER=$(Get-Val 'smtpUser' 'SMTP_USER' '')"
    "FROM_EMAIL=$(Get-Val 'fromEmail' 'FROM_EMAIL' '')"
    "SUPERUSER_EMAIL=$(Get-Val 'superuserEmail' 'SUPERUSER_EMAIL' 'superadmin@quality-autopilot.dev')"
    "SERPER_API_KEY=$(Get-Val 'serperApiKey' 'SERPER_API_KEY' '')"
    "POWER_AUTOMATE_TEAMS_URL=$(Get-Val 'powerAutomateTeamsUrl' 'POWER_AUTOMATE_TEAMS_URL' '')"
    "PARALLEL_API_KEY=$(Get-Val 'parallelApiKey' 'PARALLEL_API_KEY' '')"
    "APP_BASE_URL=$APP_BASE_URL"
    # Azure OpenAI (embedding)
    "EMBEDDING_PROVIDER=$(Get-Val '' 'EMBEDDING_PROVIDER' 'azure_openai')"
    "AZURE_OPENAI_ENDPOINT=$(Get-Val '' 'AZURE_OPENAI_ENDPOINT' '')"
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT=$(Get-Val '' 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT' 'text-embedding-3-small')"
)

# Mandatory secrets
$apiSecrets = @(
    "db-pass=$DB_PASS"
    "session-secret=$SESSION_SECRET"
    "acr-pass=$ACR_PASS"
)
$apiEnv += "SESSION_SECRET=secretref:session-secret"
$apiEnv += "DB_PASS=secretref:db-pass"

# Optional secrets — only added when value is present
$optSecrets = [ordered]@{
    'openrouter-api-key'   = Get-Val 'openrouterApiKey'  'OPENROUTER_API_KEY'  ''
    'kilo-api-key'         = Get-Val 'kiloApiKey'         'KILO_API_KEY'         ''
    'nvidia-api-key'       = Get-Val 'nvidiaApiKey'        'NVIDIA_API_KEY'       ''
    'openai-api-key'       = Get-Val 'openaiApiKey'        'OPENAI_API_KEY'       ''
    'google-api-key'       = Get-Val 'googleApiKey'        'GOOGLE_API_KEY'       ''
    'anthropic-api-key'    = Get-Val 'anthropicApiKey'     'ANTHROPIC_API_KEY'    ''
    'github-token'         = Get-Val 'githubToken'         'GITHUB_TOKEN'         ''
    'ado-pat'              = Get-Val 'azureDevOpsPat'      'AZURE_DEVOPS_EXT_PAT' ''
    'atlassian-token'      = Get-Val 'atlassianApiToken'   'ATLASSIAN_API_TOKEN'  ''
    'ollama-api-key'       = Get-Val ''                    'OLLAMA_API_KEY'       ''
    'slack-bot-token'      = Get-Val 'slackBotToken'       'SLACK_BOT_TOKEN'      ''
    'smtp-pass'            = Get-Val 'smtpPass'            'SMTP_PASS'            ''
    'superuser-password'   = Get-Val 'superuserInitialPassword' 'SUPERUSER_INITIAL_PASSWORD' ''
    'seed-admin-password'  = Get-Val 'seedAdminPassword'   'SEED_ADMIN_PASSWORD'  ''
    'seed-member-password' = Get-Val 'seedMemberPassword'  'SEED_MEMBER_PASSWORD' ''
    'azure-openai-key'     = Get-Val ''                    'AZURE_OPENAI_API_KEY' ''
}
$optEnvMap = [ordered]@{
    'openrouter-api-key'   = 'OPENROUTER_API_KEY'
    'kilo-api-key'         = 'KILO_API_KEY'
    'nvidia-api-key'       = 'NVIDIA_API_KEY'
    'openai-api-key'       = 'OPENAI_API_KEY'
    'google-api-key'       = 'GOOGLE_API_KEY'
    'anthropic-api-key'    = 'ANTHROPIC_API_KEY'
    'github-token'         = 'GITHUB_TOKEN'
    'ado-pat'              = 'AZURE_DEVOPS_EXT_PAT'
    'atlassian-token'      = 'ATLASSIAN_API_TOKEN'
    'ollama-api-key'       = 'OLLAMA_API_KEY'
    'slack-bot-token'      = 'SLACK_BOT_TOKEN'
    'smtp-pass'            = 'SMTP_PASS'
    'superuser-password'   = 'SUPERUSER_INITIAL_PASSWORD'
    'seed-admin-password'  = 'SEED_ADMIN_PASSWORD'
    'seed-member-password' = 'SEED_MEMBER_PASSWORD'
    'azure-openai-key'     = 'AZURE_OPENAI_API_KEY'
}
foreach ($sk in $optSecrets.Keys) {
    if ($optSecrets[$sk]) {
        $apiSecrets += "${sk}=$($optSecrets[$sk])"
        $apiEnv     += "$($optEnvMap[$sk])=secretref:${sk}"
    }
}

Write-Ok "Secrets: $($apiSecrets.Count)  Env vars: $($apiEnv.Count)"

# ---------------------------------------------------------------------------
# Phase 3 — Update Container App (image + secrets + env vars atomically)
# ---------------------------------------------------------------------------
Write-Step "Phase 3 — Updating $APP_NAME in $RESOURCE_GROUP"

$updateArgs = @(
    'containerapp', 'update',
    '--resource-group', $RESOURCE_GROUP,
    '--name', $APP_NAME,
    '--image', $API_IMAGE,
    '--registry-server',   $ACR_SERVER,
    '--registry-username', $ACR_USER,
    '--registry-password', $ACR_PASS,
    '--secrets'
) + $apiSecrets + @('--set-env-vars') + $apiEnv

az @updateArgs | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Fail "Container app update failed" }
Write-Ok "Container app updated — new revision rolling out"

# Persist new image tag to state
$state | Add-Member -Force -MemberType NoteProperty -Name lastImage -Value $API_IMAGE
$state | Add-Member -Force -MemberType NoteProperty -Name lastDeploy -Value (Get-Date -Format 'o')
$state | ConvertTo-Json | Set-Content $STATE_FILE

# ---------------------------------------------------------------------------
# Phase 4 — Wait for revision to reach Running state (max 3 minutes)
# ---------------------------------------------------------------------------
Write-Step "Phase 4 — Waiting for new revision to start (up to 3 minutes)"

$deadline = (Get-Date).AddMinutes(3)
$revisionName = $null
$revisionRunning = $false

while ((Get-Date) -lt $deadline) {
    $revisions = az containerapp revision list `
        --name $APP_NAME `
        --resource-group $RESOURCE_GROUP `
        --query "[?properties.runningState=='Running'].{name:name,traffic:properties.trafficWeight}" `
        -o json 2>&1 | ConvertFrom-Json

    # Find revision with our image tag
    $allRevisions = az containerapp revision list `
        --name $APP_NAME `
        --resource-group $RESOURCE_GROUP `
        --query "[].{name:name,state:properties.runningState,created:properties.createdTime}" `
        -o json 2>&1 | ConvertFrom-Json

    $newest = $allRevisions | Sort-Object { $_.created } | Select-Object -Last 1
    if ($newest -and $newest.state -eq 'Running') {
        $revisionName = $newest.name
        $revisionRunning = $true
        break
    }

    $stateStr = if ($newest) { $newest.state } else { "unknown" }
    Write-Host "   ... revision state: $stateStr (waiting)" -ForegroundColor Gray
    Start-Sleep -Seconds 10
}

if (-not $revisionRunning) {
    Write-Warn "Revision did not reach Running within 3 minutes — check ACA portal"
} else {
    Write-Ok "Revision running: $revisionName"
}

# ---------------------------------------------------------------------------
# Phase 5 — Health check
# ---------------------------------------------------------------------------
Write-Step "Phase 5 — Health check"

$API_FQDN = Invoke-Az containerapp show `
    --name $APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --query 'properties.configuration.ingress.fqdn' -o tsv

$API_URL = "https://$API_FQDN"
Write-Ok "API URL: $API_URL"

# Give the app 5 extra seconds to initialise before probing
Start-Sleep -Seconds 5

$healthOk = $false
for ($i = 1; $i -le 3; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "$API_URL/health" -UseBasicParsing -TimeoutSec 15 -ErrorAction SilentlyContinue
        if ($resp.StatusCode -eq 200) {
            $healthOk = $true
            Write-Ok "/health → $($resp.StatusCode) ✅"
            break
        } else {
            Write-Warn "/health attempt $i → $($resp.StatusCode)"
        }
    } catch {
        Write-Warn "/health attempt $i → error: $($_.Exception.Message)"
    }
    if ($i -lt 3) { Start-Sleep -Seconds 10 }
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor $(if ($healthOk) { 'Green' } else { 'Yellow' })
Write-Host "║   Redeploy Complete                                           ║"
Write-Host "╠═══════════════════════════════════════════════════════════════╣"
Write-Host "║  Image    : $($API_IMAGE.PadRight(49)) ║"
Write-Host "║  Revision : $($revisionName.PadRight(49)) ║"
Write-Host "║  API URL  : $($API_URL.PadRight(49)) ║"
Write-Host "║  Health   : $(if ($healthOk) { '✅ OK' } else { '⚠️  check logs' })$((' ' * 44).Substring(0, [Math]::Max(0, 44 - (if ($healthOk) { 6 } else { 14 })))) ║"
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor $(if ($healthOk) { 'Green' } else { 'Yellow' })
