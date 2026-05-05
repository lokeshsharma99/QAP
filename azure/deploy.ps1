#!/usr/bin/env pwsh
# =============================================================================
# Quality Autopilot — Azure Container Apps Deployment Script
# =============================================================================
#
# Usage:
#   .\azure\deploy.ps1                     # full deploy (reads azure/parameters.json)
#   .\azure\deploy.ps1 -InfraOnly          # infrastructure only (no image builds)
#   .\azure\deploy.ps1 -AppsOnly           # skip Bicep, rebuild + redeploy apps only
#
# Prerequisites:
#   - Azure CLI 2.50+  (az login already done)
#   - Docker Desktop running
#   - azure/parameters.json created from azure/parameters.example.json
#
# What this script does:
#   Phase 1 — Deploy Azure infrastructure via Bicep:
#              ACR, Log Analytics, Storage (pgdata), ACA Environment,
#              qap-db, github-mcp, ado-mcp, atlassian-mcp
#   Phase 2 — Build + push custom Docker images to ACR:
#              qap-api, playwright-mcp
#   Phase 3 — Create/update qap-api Container App; get its public FQDN
#   Phase 4 — Build qap-ui with NEXT_PUBLIC_AGENTOS_URL baked in; push to ACR
#   Phase 5 — Create/update qap-ui and playwright-mcp Container Apps
# =============================================================================

param(
    [switch]$InfraOnly,
    [switch]$AppsOnly,
    [string]$ParametersFile = "$PSScriptRoot\parameters.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Write-Step { param([string]$Msg) Write-Host "`n▶  $Msg" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Msg) Write-Host "   ✓  $Msg" -ForegroundColor Green }
function Write-Warn { param([string]$Msg) Write-Host "   ⚠  $Msg" -ForegroundColor Yellow }
function Write-Fail { param([string]$Msg) Write-Host "   ✗  $Msg" -ForegroundColor Red; exit 1 }

function Invoke-Az {
    $result = az @args 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Fail "az $($args[0]) failed: $result" }
    return $result
}

function ContainerAppExists {
    param([string]$Name, [string]$ResourceGroup)
    $out = az containerapp show --name $Name --resource-group $ResourceGroup 2>&1
    return $LASTEXITCODE -eq 0
}

# ---------------------------------------------------------------------------
# Load parameters
# ---------------------------------------------------------------------------
Write-Step "Loading parameters from $ParametersFile"
if (-not (Test-Path $ParametersFile)) {
    Write-Fail "$ParametersFile not found. Copy azure/parameters.example.json → azure/parameters.json and fill in your values."
}
$params = Get-Content $ParametersFile | ConvertFrom-Json

# Mandatory fields
$SUBSCRIPTION  = $params.subscriptionId   ?? (Invoke-Az account show --query id -o tsv).Trim()
$RESOURCE_GROUP = $params.resourceGroup
$PREFIX        = $params.parameters.prefix.value         ?? 'qap'
$ENV_NAME      = $params.parameters.env.value            ?? 'dev'
$LOCATION      = $params.parameters.location.value       ?? 'westeurope'
$DB_PASS       = $params.parameters.dbPass.value
$SESSION_SECRET = $params.parameters.sessionSecret.value ?? (New-Guid).Guid

if (-not $RESOURCE_GROUP) { Write-Fail "resourceGroup is required in $ParametersFile" }
if (-not $DB_PASS)        { Write-Fail "parameters.dbPass.value is required in $ParametersFile" }

$RESOURCE_PREFIX = "${PREFIX}-${ENV_NAME}"
$TAG = (Get-Date -Format 'yyyyMMdd-HHmm')

Write-Ok "Subscription : $SUBSCRIPTION"
Write-Ok "Resource group: $RESOURCE_GROUP ($LOCATION)"
Write-Ok "Resource prefix: $RESOURCE_PREFIX"
Write-Ok "Image tag      : $TAG"

# ---------------------------------------------------------------------------
# Prerequisites check
# ---------------------------------------------------------------------------
Write-Step "Checking prerequisites"
if (-not (Get-Command az -ErrorAction SilentlyContinue))     { Write-Fail "Azure CLI not found. Install from https://aka.ms/installazurecli" }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Write-Fail "Docker not found. Install Docker Desktop." }

$account = az account show --query '{name:name,state:state}' -o json 2>&1 | ConvertFrom-Json
if (-not $account -or $account.state -ne 'Enabled') { Write-Fail "Not logged in to Azure. Run: az login" }
Write-Ok "Logged in as: $($account.name)"

# ---------------------------------------------------------------------------
# Phase 1 — Deploy infrastructure via Bicep
# ---------------------------------------------------------------------------
if (-not $AppsOnly) {
    Write-Step "Phase 1 — Creating resource group '$RESOURCE_GROUP' in $LOCATION"
    az group create --name $RESOURCE_GROUP --location $LOCATION --subscription $SUBSCRIPTION | Out-Null
    Write-Ok "Resource group ready"

    Write-Step "Phase 1 — Deploying infrastructure (Bicep)"

    # Build the parameter overrides from parameters.json
    $bicepParams = @(
        "prefix=$PREFIX"
        "env=$ENV_NAME"
        "location=$LOCATION"
        "dbPass=$DB_PASS"
        "sessionSecret=$SESSION_SECRET"
    )

    # Optional parameters — only pass if provided
    $optionals = @{
        openrouterApiKey  = $params.parameters.openrouterApiKey.value
        kiloApiKey        = $params.parameters.kiloApiKey.value
        openaiApiKey      = $params.parameters.openaiApiKey.value
        googleApiKey      = $params.parameters.googleApiKey.value
        anthropicApiKey   = $params.parameters.anthropicApiKey.value
        githubToken       = $params.parameters.githubToken.value
        azureDevOpsPat    = $params.parameters.azureDevOpsPat.value
        azureDevOpsEmail  = $params.parameters.azureDevOpsEmail.value
        azureDevOpsUrl    = $params.parameters.azureDevOpsUrl.value
        atlassianApiToken = $params.parameters.atlassianApiToken.value
        atlassianEmail    = $params.parameters.atlassianEmail.value
        atlassianUrl      = $params.parameters.atlassianUrl.value
        autBaseUrl        = $params.parameters.autBaseUrl.value
        autGithubOwner    = $params.parameters.autGithubOwner.value
        autGithubRepo     = $params.parameters.autGithubRepo.value
        modelProvider     = $params.parameters.modelProvider.value
        appBaseUrl        = $params.parameters.appBaseUrl.value
    }
    # nvidiaApiKey is not a Bicep parameter (used only in Container App env) — skip Bicep passthrough
    foreach ($k in $optionals.Keys) {
        if ($optionals[$k]) { $bicepParams += "${k}=$($optionals[$k])" }
    }

    $infraResult = az deployment group create `
        --name "qap-infra-$TAG" `
        --resource-group $RESOURCE_GROUP `
        --subscription $SUBSCRIPTION `
        --template-file "$PSScriptRoot\main.bicep" `
        --parameters @bicepParams `
        --query 'properties.outputs' -o json | ConvertFrom-Json

    if (-not $infraResult) { Write-Fail "Bicep deployment failed" }

    $ACR_SERVER = $infraResult.acrLoginServer.value
    $ACR_NAME   = $infraResult.acrName.value
    $DB_HOST    = $infraResult.qapDbHost.value

    Write-Ok "ACR          : $ACR_SERVER"
    Write-Ok "DB host      : $DB_HOST"

    # Persist outputs for AppsOnly re-runs
    @{ acrServer = $ACR_SERVER; acrName = $ACR_NAME; dbHost = $DB_HOST } |
        ConvertTo-Json | Set-Content "$PSScriptRoot\.deploy-state.json"
} else {
    # AppsOnly: load state from previous infra deploy
    $state = Get-Content "$PSScriptRoot\.deploy-state.json" | ConvertFrom-Json
    $ACR_SERVER = $state.acrServer
    $ACR_NAME   = $state.acrName
    $DB_HOST    = $state.dbHost
    Write-Ok "Using saved state — ACR: $ACR_SERVER  DB host: $DB_HOST"
}

if ($InfraOnly) {
    Write-Host "`n✅  Infrastructure deployed. Re-run without -InfraOnly to build and deploy apps." -ForegroundColor Green
    exit 0
}

# ---------------------------------------------------------------------------
# Phase 2 — ACR login + build + push qap-api and playwright-mcp
# ---------------------------------------------------------------------------
Write-Step "Phase 2 — Logging in to ACR ($ACR_NAME)"
Invoke-Az acr login --name $ACR_NAME | Out-Null
Write-Ok "ACR login ok"

$REPO_ROOT = (Resolve-Path "$PSScriptRoot\..").Path

Write-Step "Phase 2 — Building qap-api image"
$API_IMAGE = "${ACR_SERVER}/qap-api:${TAG}"
docker build -t $API_IMAGE -f "$REPO_ROOT\Dockerfile" $REPO_ROOT
if ($LASTEXITCODE -ne 0) { Write-Fail "Docker build qap-api failed" }
Write-Ok "Built $API_IMAGE"

Write-Step "Phase 2 — Building playwright-mcp image"
$PLAYWRIGHT_IMAGE = "${ACR_SERVER}/playwright-mcp:${TAG}"
docker build -t $PLAYWRIGHT_IMAGE -f "$REPO_ROOT\Dockerfile.playwright-mcp" $REPO_ROOT
if ($LASTEXITCODE -ne 0) { Write-Fail "Docker build playwright-mcp failed" }
Write-Ok "Built $PLAYWRIGHT_IMAGE"

Write-Step "Phase 2 — Pushing images to ACR"
docker push $API_IMAGE
docker push $PLAYWRIGHT_IMAGE
Write-Ok "Pushed to ACR"

# ACR credentials for Container App image pull
$ACR_USER     = Invoke-Az acr credential show --name $ACR_NAME --query username -o tsv
$ACR_PASS     = Invoke-Az acr credential show --name $ACR_NAME --query 'passwords[0].value' -o tsv

# ---------------------------------------------------------------------------
# Phase 3 — Deploy qap-api Container App
# ---------------------------------------------------------------------------
Write-Step "Phase 3 — Deploying qap-api Container App"

$qapApiName = "${RESOURCE_PREFIX}-api"

# Build environment variable list for qap-api
$apiEnv = @(
    "RUNTIME_ENV=prod"
    "PYTHONPATH=/app"
    "AGENTOS_URL=http://localhost:8000"
    "DB_HOST=$DB_HOST"
    "DB_PORT=5432"
    "DB_USER=ai"
    "DB_DATABASE=ai"
    "WAIT_FOR_DB=True"
    "MODEL_PROVIDER=$($params.parameters.modelProvider.value ?? 'kilo')"
    "OPENROUTER_BASE_URL=$($params.parameters.openrouterBaseUrl.value ?? 'https://api.kilo.ai/api/openrouter/v1')"
    "KILO_API_URL=$($params.parameters.kiloApiUrl.value ?? 'https://api.kilo.ai')"
    "AUT_BASE_URL=$($params.parameters.autBaseUrl.value ?? 'https://lokeshsharma99.github.io/GDS-Demo-App/')"
    "AUT_GITHUB_OWNER=$($params.parameters.autGithubOwner.value ?? 'lokeshsharma99')"
    "AUT_GITHUB_REPO=$($params.parameters.autGithubRepo.value ?? 'GDS-Demo-App')"
    "GITHUB_MCP_URL=http://${RESOURCE_PREFIX}-github-mcp"
    "PLAYWRIGHT_MCP_URL=http://${RESOURCE_PREFIX}-playwright-mcp:8931"
    "ADO_MCP_URL=http://${RESOURCE_PREFIX}-ado-mcp/mcp"
    "ATLASSIAN_MCP_URL=http://${RESOURCE_PREFIX}-atlassian-mcp/mcp"
    "SESSION_TTL_DAYS=30"
    "AZURE_DEVOPS_URL=$($params.parameters.azureDevOpsUrl.value)"
    "AZURE_DEVOPS_EMAIL=$($params.parameters.azureDevOpsEmail.value)"
    "ATLASSIAN_URL=$($params.parameters.atlassianUrl.value)"
    "ATLASSIAN_EMAIL=$($params.parameters.atlassianEmail.value)"
)

# Secrets for qap-api (passed as --secrets and referenced in --env-vars)
$apiSecrets = @(
    "db-pass=$DB_PASS"
    "session-secret=$SESSION_SECRET"
)
$apiEnv += "SESSION_SECRET=secretref:session-secret"
$apiEnv += "DB_PASS=secretref:db-pass"

# Add optional secrets only when provided
$optSecrets = @{
    'openrouter-api-key'  = $params.parameters.openrouterApiKey.value
    'kilo-api-key'        = $params.parameters.kiloApiKey.value
    'nvidia-api-key'      = $params.parameters.nvidiaApiKey.value
    'openai-api-key'      = $params.parameters.openaiApiKey.value
    'google-api-key'      = $params.parameters.googleApiKey.value
    'anthropic-api-key'   = $params.parameters.anthropicApiKey.value
    'github-token'        = $params.parameters.githubToken.value
    'ado-pat'             = $params.parameters.azureDevOpsPat.value
    'atlassian-token'     = $params.parameters.atlassianApiToken.value
}
$optEnvMap = @{
    'openrouter-api-key'  = 'OPENROUTER_API_KEY'
    'kilo-api-key'        = 'KILO_API_KEY'
    'nvidia-api-key'      = 'NVIDIA_API_KEY'
    'openai-api-key'      = 'OPENAI_API_KEY'
    'google-api-key'      = 'GOOGLE_API_KEY'
    'anthropic-api-key'   = 'ANTHROPIC_API_KEY'
    'github-token'        = 'GITHUB_TOKEN'
    'ado-pat'             = 'AZURE_DEVOPS_EXT_PAT'
    'atlassian-token'     = 'ATLASSIAN_API_TOKEN'
}
foreach ($sk in $optSecrets.Keys) {
    if ($optSecrets[$sk]) {
        $apiSecrets += "${sk}=$($optSecrets[$sk])"
        $apiEnv     += "$($optEnvMap[$sk])=secretref:${sk}"
    }
}

# NOTE: Each secret and env-var must be a separate array element.
# DO NOT use -join ' ' — on Windows az CLI receives it as one argument.
$createOrUpdateArgs = @(
    '--resource-group', $RESOURCE_GROUP
    '--name',           $qapApiName
    '--environment',    "${RESOURCE_PREFIX}-env"
    '--image',          $API_IMAGE
    '--registry-server',   $ACR_SERVER
    '--registry-username', $ACR_USER
    '--registry-password', $ACR_PASS
    '--target-port',    '8000'
    '--ingress',        'external'
    '--transport',      'http'
    '--cpu',            '1'
    '--memory',         '2Gi'
    '--min-replicas',   '1'
    '--max-replicas',   '2'
    '--command',        'uvicorn'
    '--args',           'app.main:app,--host,0.0.0.0,--port,8000,--workers,2'
    '--secrets'
) + $apiSecrets + @('--env-vars') + $apiEnv

if (ContainerAppExists $qapApiName $RESOURCE_GROUP) {
    Write-Warn "qap-api already exists — updating image"
    $updateArgs = @('containerapp', 'update',
        '--resource-group', $RESOURCE_GROUP,
        '--name', $qapApiName,
        '--image', $API_IMAGE,
        '--secrets') + $apiSecrets + @('--set-env-vars') + $apiEnv
    az @updateArgs | Out-Null
} else {
    az containerapp create @createOrUpdateArgs | Out-Null
}

if ($LASTEXITCODE -ne 0) { Write-Fail "qap-api deployment failed" }

$API_FQDN = Invoke-Az containerapp show `
    --name $qapApiName `
    --resource-group $RESOURCE_GROUP `
    --query 'properties.configuration.ingress.fqdn' -o tsv
$API_URL  = "https://$API_FQDN"
Write-Ok "qap-api live  : $API_URL"

# Persist API URL for future AppsOnly re-runs
$state = Get-Content "$PSScriptRoot\.deploy-state.json" | ConvertFrom-Json
$state | Add-Member -Force -MemberType NoteProperty -Name apiUrl -Value $API_URL
$state | ConvertTo-Json | Set-Content "$PSScriptRoot\.deploy-state.json"

# ---------------------------------------------------------------------------
# Phase 4 — Build qap-ui with NEXT_PUBLIC_AGENTOS_URL baked in
# ---------------------------------------------------------------------------
Write-Step "Phase 4 — Building qap-ui (baking API URL: $API_URL)"

$UI_IMAGE = "${ACR_SERVER}/qap-ui:${TAG}"
$UI_URL   = $params.parameters.appBaseUrl.value

docker build `
    -t $UI_IMAGE `
    --build-arg "NEXT_PUBLIC_AGENTOS_URL=$API_URL" `
    -f "$REPO_ROOT\control-plane\Dockerfile" `
    "$REPO_ROOT\control-plane"
if ($LASTEXITCODE -ne 0) { Write-Fail "Docker build qap-ui failed" }

docker push $UI_IMAGE
Write-Ok "Pushed $UI_IMAGE"

# ---------------------------------------------------------------------------
# Phase 5 — Deploy qap-ui and playwright-mcp Container Apps
# ---------------------------------------------------------------------------
Write-Step "Phase 5 — Deploying qap-ui Container App"

$qapUiName = "${RESOURCE_PREFIX}-ui"
$uiEnv = @(
    "AGENTOS_URL=http://${RESOURCE_PREFIX}-api"
    "NEXT_PUBLIC_OS_SECURITY_KEY="
)

if (ContainerAppExists $qapUiName $RESOURCE_GROUP) {
    $uiUpdateArgs = @('containerapp', 'update',
        '--resource-group', $RESOURCE_GROUP,
        '--name', $qapUiName,
        '--image', $UI_IMAGE,
        '--set-env-vars') + $uiEnv
    az @uiUpdateArgs | Out-Null
} else {
    $uiCreateArgs = @('containerapp', 'create',
        '--resource-group', $RESOURCE_GROUP,
        '--name', $qapUiName,
        '--environment', "${RESOURCE_PREFIX}-env",
        '--image', $UI_IMAGE,
        '--registry-server', $ACR_SERVER,
        '--registry-username', $ACR_USER,
        '--registry-password', $ACR_PASS,
        '--target-port', '3000',
        '--ingress', 'external',
        '--transport', 'http',
        '--cpu', '0.5',
        '--memory', '1Gi',
        '--min-replicas', '1',
        '--max-replicas', '2',
        '--env-vars') + $uiEnv
    az @uiCreateArgs | Out-Null
}
if ($LASTEXITCODE -ne 0) { Write-Fail "qap-ui deployment failed" }

$UI_FQDN = Invoke-Az containerapp show `
    --name $qapUiName `
    --resource-group $RESOURCE_GROUP `
    --query 'properties.configuration.ingress.fqdn' -o tsv
Write-Ok "qap-ui live   : https://$UI_FQDN"

Write-Step "Phase 5 — Deploying playwright-mcp Container App"

$playwrightName = "${RESOURCE_PREFIX}-playwright-mcp"

if (ContainerAppExists $playwrightName $RESOURCE_GROUP) {
    az containerapp update `
        --resource-group $RESOURCE_GROUP `
        --name $playwrightName `
        --image $PLAYWRIGHT_IMAGE | Out-Null
} else {
    az containerapp create `
        --resource-group $RESOURCE_GROUP `
        --name $playwrightName `
        --environment "${RESOURCE_PREFIX}-env" `
        --image $PLAYWRIGHT_IMAGE `
        --registry-server $ACR_SERVER `
        --registry-username $ACR_USER `
        --registry-password $ACR_PASS `
        --target-port 8931 `
        --ingress internal `
        --transport http `
        --cpu 1 `
        --memory '2Gi' `
        --min-replicas 1 `
        --max-replicas 1 | Out-Null
}
if ($LASTEXITCODE -ne 0) { Write-Fail "playwright-mcp deployment failed" }
Write-Ok "playwright-mcp deployed (internal)"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  Quality Autopilot — Azure Deployment Complete                          ║" -ForegroundColor Green
Write-Host "╠══════════════════════════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║  UI  (public) : https://$UI_FQDN" -ForegroundColor Green
Write-Host "║  API (public) : $API_URL" -ForegroundColor Cyan
Write-Host "╠══════════════════════════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║  Resource group : $RESOURCE_GROUP" -ForegroundColor White
Write-Host "║  ACR            : $ACR_SERVER" -ForegroundColor White
Write-Host "║  Image tag      : $TAG" -ForegroundColor White
Write-Host "╚══════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "To redeploy apps only (no infra):" -ForegroundColor Yellow
Write-Host "  .\azure\deploy.ps1 -AppsOnly" -ForegroundColor Yellow
