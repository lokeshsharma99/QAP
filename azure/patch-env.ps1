#Requires -Version 7
<#
.SYNOPSIS
    Sync .env credentials to all running Azure Container App services.

.DESCRIPTION
    Reads .env from the repo root and pushes every credential to the correct ACA
    container WITHOUT a full Bicep redeploy.

    Uses the correct az CLI pattern:
      az containerapp secret set  → create/update ACA secrets
      az containerapp update --set-env-vars → bind plain values and secretrefs

    POWER_AUTOMATE_TEAMS_URL is stored as a secret (not plain env var) because
    its query-string & characters are interpreted as cmd separators by Windows.

    Containers patched:
      qap-dev-api            — all env vars + secrets
      qap-dev-atlassian-mcp  — Jira + Confluence (fixes Jira integration)
      qap-dev-ado-mcp        — Azure DevOps credentials
      qap-dev-github-mcp     — GitHub token

.EXAMPLE
    .\azure\patch-env.ps1
    .\azure\patch-env.ps1 -EnvFile "C:\my\custom.env"
    .\azure\patch-env.ps1 -DryRun
#>

[CmdletBinding()]
param(
    [string]$EnvFile       = (Join-Path $PSScriptRoot ".." ".env"),
    [string]$ResourceGroup = "rg-quality-autopilot",
    [string]$Prefix        = "qap-dev",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Write-Step { param($m) Write-Host "`n▶  $m" -ForegroundColor Cyan }
function Write-Ok   { param($m) Write-Host "   ✅ $m"  -ForegroundColor Green }
function Write-Warn { param($m) Write-Host "   ⚠️  $m" -ForegroundColor Yellow }
function Write-Fail { param($m) Write-Host "   ❌ $m"  -ForegroundColor Red; exit 1 }

function Read-DotEnv {
    param([string]$Path)
    $vars = @{}
    if (-not (Test-Path $Path)) { Write-Fail ".env not found at: $Path" }
    foreach ($line in (Get-Content $Path)) {
        $line = $line.Trim()
        if ($line -match '^[^#\s]' -and $line -match '=') {
            $idx = $line.IndexOf('=')
            $key = $line.Substring(0, $idx).Trim()
            $val = $line.Substring($idx + 1).Trim()
            if (($val -match '^".*"$') -or ($val -match "^'.*'$")) {
                $val = $val.Substring(1, $val.Length - 2)
            }
            if ($key -and $val) { $vars[$key] = $val }
        }
    }
    return $vars
}

# Run az; strip WARNING lines; fail on non-zero exit
function Invoke-Az {
    param([string[]]$Cmd, [switch]$AllowWarning)
    if ($DryRun) { Write-Host "   [DRY-RUN] az $Cmd" -ForegroundColor Gray; return }
    $out = az @Cmd 2>&1
    $filtered = ($out | Where-Object { $_ -notmatch '^WARNING:' }) -join "`n"
    if ($LASTEXITCODE -ne 0) {
        # Check if the real error is phantom cmd.exe & splitting (sp/sv/sig not recognized)
        # This happens when a URL value contains & on Windows with az.cmd.
        # If the filtered output contains valid JSON (secret list), treat as success.
        $looksLikePhantomCmdError = ($filtered -match "'sp' is not recognized|'sv' is not recognized|'sig' is not recognized")
        if (-not $looksLikePhantomCmdError) {
            Write-Fail "az $($Cmd[0]) $($Cmd[1]) $($Cmd[2]) failed:`n$filtered"
        }
    }
}

# Set/update secrets on a container app (az containerapp secret set)
function Set-AppSecrets {
    param([string]$AppName, [string[]]$Pairs)
    $validPairs = @($Pairs | Where-Object { $_ -match '=.+' })
    if ($validPairs.Count -eq 0) { return }
    $cmd = @('containerapp', 'secret', 'set',
        '--name',           $AppName,
        '--resource-group', $ResourceGroup,
        '--secrets')        + $validPairs
    Invoke-Az -Cmd $cmd
}

# Update env vars on a container app (az containerapp update --set-env-vars)
function Set-AppEnvVars {
    param([string]$AppName, [string[]]$Pairs)
    $nonEmpty = @($Pairs | Where-Object { $_ -match '=.+' })
    if ($nonEmpty.Count -eq 0) { return }
    $cmd = @('containerapp', 'update',
        '--name',           $AppName,
        '--resource-group', $ResourceGroup,
        '--set-env-vars')   + $nonEmpty
    Invoke-Az -Cmd $cmd
}

# ---------------------------------------------------------------------------
# Parse .env
# ---------------------------------------------------------------------------
Write-Step "Parsing .env: $EnvFile"
$e = Read-DotEnv -Path $EnvFile
Write-Ok "Loaded $($e.Count) variables"
function G { param($k) if ($e.ContainsKey($k)) { return $e[$k] } else { return '' } }

# ---------------------------------------------------------------------------
# Resolve live UI FQDN for APP_BASE_URL
# ---------------------------------------------------------------------------
Write-Step "Resolving UI FQDN"
$uiFqdn = ''
try {
    $uiFqdn = (az containerapp show `
        --name "${Prefix}-ui" `
        --resource-group $ResourceGroup `
        --query 'properties.configuration.ingress.fqdn' -o tsv 2>\$null)
} catch {}
$appBaseUrl = if ($uiFqdn) { "https://$uiFqdn" } else { G 'APP_BASE_URL' }
Write-Ok "APP_BASE_URL = $appBaseUrl"

# Derive Atlassian/Jira/Confluence values
$atlassianUrl  = G 'ATLASSIAN_URL'
$atlassianEmail = G 'ATLASSIAN_EMAIL'
$jiraUrl       = if ($atlassianUrl)   { $atlassianUrl }   else { G 'JIRA_URL' }
$confluenceUrl = if ($atlassianUrl)   { "${atlassianUrl}/wiki" } else { G 'CONFLUENCE_URL' }
$jiraUsername  = if ($atlassianEmail) { $atlassianEmail } else { G 'JIRA_USERNAME' }

# ---------------------------------------------------------------------------
# ① qap-dev-api — set secrets first, then bind env vars
# ---------------------------------------------------------------------------
Write-Step "Setting secrets on ${Prefix}-api"

$secretMap = [ordered]@{
    'atlassian-token'     = G 'ATLASSIAN_API_TOKEN'
    'ado-pat'             = G 'AZURE_DEVOPS_EXT_PAT'
    'github-token'        = G 'GITHUB_TOKEN'
    'nvidia-api-key'      = G 'NVIDIA_API_KEY'
    'openai-api-key'      = G 'OPENAI_API_KEY'
    'google-api-key'      = G 'GOOGLE_API_KEY'
    'ollama-api-key'      = G 'OLLAMA_API_KEY'
    'kilo-api-key'        = G 'KILO_API_KEY'
    'slack-bot-token'     = G 'SLACK_BOT_TOKEN'
    'smtp-pass'           = G 'SMTP_PASS'
    'serper-api-key'      = G 'SERPER_API_KEY'
    'superuser-password'  = G 'SUPERUSER_INITIAL_PASSWORD'
    'seed-admin-password' = G 'SEED_ADMIN_PASSWORD'
    'seed-member-password'= G 'SEED_MEMBER_PASSWORD'
    # NOTE: POWER_AUTOMATE_TEAMS_URL intentionally excluded.
    # Its query-string & characters cause cmd.exe to split the argument when
    # passed through az.cmd on Windows. Set it manually in the Azure portal or
    # via the full deploy.ps1 if it ever changes.
}

$apiSecretPairs = [System.Collections.Generic.List[string]]::new()
foreach ($sName in $secretMap.Keys) {
    $sVal = $secretMap[$sName]
    if ($sVal) { $apiSecretPairs.Add("${sName}=${sVal}") }
}

Set-AppSecrets -AppName "${Prefix}-api" -Pairs $apiSecretPairs.ToArray()
Write-Ok "Secrets set ($($apiSecretPairs.Count) secrets)"

# Helper: only emit secretref if that secret was actually set
function SR { param($n) if ($secretMap[$n]) { "secretref:$n" } else { '' } }

Write-Step "Updating env vars on ${Prefix}-api"

$apiEnvMap = [ordered]@{
    'MODEL_PROVIDER'             = G 'MODEL_PROVIDER'
    'NVIDIA_MODEL'               = G 'NVIDIA_MODEL'
    'NVIDIA_API_KEY'             = SR 'nvidia-api-key'
    'OPENAI_API_KEY'             = SR 'openai-api-key'
    'GOOGLE_API_KEY'             = SR 'google-api-key'
    'OLLAMA_API_KEY'             = SR 'ollama-api-key'
    'KILO_API_KEY'               = SR 'kilo-api-key'
    'OLLAMA_BASE_URL'            = G 'OLLAMA_BASE_URL'
    'OLLAMA_MODEL'               = G 'OLLAMA_MODEL'
    'OLLAMA_MODELS'              = G 'OLLAMA_MODELS'
    # Embedding provider: "openai" works in ACA without Ollama sidecar.
    # Switch to "ollama" only if an Ollama service is deployed in the same env.
    # After switching provider, set RECREATE_VECTOR_TABLES=1 for ONE restart,
    # then remove it — the tables will be rebuilt with the correct dimensions.
    'EMBEDDING_PROVIDER'         = if (G 'EMBEDDING_PROVIDER') { G 'EMBEDDING_PROVIDER' } else { 'openai' }
    'RECREATE_VECTOR_TABLES'     = G 'RECREATE_VECTOR_TABLES'
    'GITHUB_TOKEN'               = SR 'github-token'
    'SLACK_BOT_TOKEN'            = SR 'slack-bot-token'
    'SLACK_CHANNEL_ID'           = G 'SLACK_CHANNEL_ID'
    'SLACK_CHANNEL'              = G 'SLACK_CHANNEL'
    'SERPER_API_KEY'             = SR 'serper-api-key'
    'ATLASSIAN_URL'              = $atlassianUrl
    'ATLASSIAN_EMAIL'            = $atlassianEmail
    'ATLASSIAN_API_TOKEN'        = SR 'atlassian-token'
    'ATLASSIAN_CONFLUENCE_URL'   = $confluenceUrl
    'JIRA_URL'                   = $jiraUrl
    'JIRA_USERNAME'              = $jiraUsername
    'JIRA_API_TOKEN'             = SR 'atlassian-token'
    'CONFLUENCE_URL'             = $confluenceUrl
    'CONFLUENCE_EMAIL'           = $jiraUsername
    'CONFLUENCE_API_TOKEN'       = SR 'atlassian-token'
    'AZURE_DEVOPS_URL'           = G 'AZURE_DEVOPS_URL'
    'AZURE_DEVOPS_EMAIL'         = G 'AZURE_DEVOPS_EMAIL'
    'AZURE_DEVOPS_EXT_PAT'       = SR 'ado-pat'
    'SMTP_HOST'                  = G 'SMTP_HOST'
    'SMTP_PORT'                  = G 'SMTP_PORT'
    'SMTP_USER'                  = G 'SMTP_USER'
    'SMTP_PASS'                  = SR 'smtp-pass'
    'FROM_EMAIL'                 = G 'FROM_EMAIL'
    'APP_BASE_URL'               = $appBaseUrl
    'SUPERUSER_EMAIL'            = G 'SUPERUSER_EMAIL'
    'SUPERUSER_INITIAL_PASSWORD' = SR 'superuser-password'
    'SEED_ADMIN_PASSWORD'        = SR 'seed-admin-password'
    'SEED_MEMBER_PASSWORD'       = SR 'seed-member-password'
    # POWER_AUTOMATE_TEAMS_URL excluded — & in the URL breaks az.cmd on Windows.
    # It retains its value from the initial deployment. Update via Azure portal if needed.
    'AUT_BASE_URL'               = G 'AUT_BASE_URL'
}

$apiEnvPairs = [System.Collections.Generic.List[string]]::new()
foreach ($eKey in $apiEnvMap.Keys) {
    $eVal = $apiEnvMap[$eKey]
    if ($eVal) { $apiEnvPairs.Add("${eKey}=${eVal}") }
}

Set-AppEnvVars -AppName "${Prefix}-api" -Pairs $apiEnvPairs.ToArray()
Write-Ok "Env vars updated ($($apiEnvPairs.Count) entries)"

# ---------------------------------------------------------------------------
# ② qap-dev-atlassian-mcp — Jira/Confluence fix
# ---------------------------------------------------------------------------
Write-Step "Patching ${Prefix}-atlassian-mcp (Jira/Confluence)"

$atlToken = G 'ATLASSIAN_API_TOKEN'
if ($atlToken) {
    Set-AppSecrets -AppName "${Prefix}-atlassian-mcp" -Pairs @("atlassian-token=${atlToken}")
    Set-AppEnvVars -AppName "${Prefix}-atlassian-mcp" -Pairs @(
        "JIRA_URL=${jiraUrl}"
        "JIRA_USERNAME=${jiraUsername}"
        "JIRA_API_TOKEN=secretref:atlassian-token"
        "CONFLUENCE_URL=${confluenceUrl}"
        "CONFLUENCE_USERNAME=${jiraUsername}"
        "CONFLUENCE_API_TOKEN=secretref:atlassian-token"
    )
    Write-Ok "Jira=$jiraUrl  Confluence=$confluenceUrl  User=$jiraUsername"
} else {
    Write-Warn "ATLASSIAN_API_TOKEN not set — skipping atlassian-mcp"
}

# ---------------------------------------------------------------------------
# ③ qap-dev-ado-mcp
# ---------------------------------------------------------------------------
Write-Step "Patching ${Prefix}-ado-mcp (Azure DevOps)"

$adoPat = G 'AZURE_DEVOPS_EXT_PAT'
if ($adoPat) {
    Set-AppSecrets -AppName "${Prefix}-ado-mcp" -Pairs @("ado-pat=${adoPat}")
    Set-AppEnvVars -AppName "${Prefix}-ado-mcp" -Pairs @(
        "AZURE_DEVOPS_URL=$(G 'AZURE_DEVOPS_URL')"
        "AZURE_DEVOPS_EMAIL=$(G 'AZURE_DEVOPS_EMAIL')"
        "AZURE_DEVOPS_EXT_PAT=secretref:ado-pat"
    )
    Write-Ok "ADO credentials updated"
} else {
    Write-Warn "AZURE_DEVOPS_EXT_PAT not set — skipping ado-mcp"
}

# ---------------------------------------------------------------------------
# ④ qap-dev-github-mcp
# ---------------------------------------------------------------------------
Write-Step "Patching ${Prefix}-github-mcp (GitHub)"

$ghToken = G 'GITHUB_TOKEN'
if ($ghToken) {
    Set-AppSecrets -AppName "${Prefix}-github-mcp" -Pairs @("github-token=${ghToken}")
    Set-AppEnvVars -AppName "${Prefix}-github-mcp" -Pairs @(
        "GITHUB_PERSONAL_ACCESS_TOKEN=secretref:github-token"
    )
    Write-Ok "GitHub token updated"
} else {
    Write-Warn "GITHUB_TOKEN not set — skipping github-mcp"
}

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   patch-env complete                                          ║" -ForegroundColor Green
Write-Host "╠═══════════════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║  ✅ ${Prefix}-api             secrets + env vars updated     ║" -ForegroundColor Green
Write-Host "║  ✅ ${Prefix}-atlassian-mcp   Jira/Confluence credentials    ║" -ForegroundColor Green
Write-Host "║  ✅ ${Prefix}-ado-mcp         Azure DevOps PAT               ║" -ForegroundColor Green
Write-Host "║  ✅ ${Prefix}-github-mcp      GitHub token                   ║" -ForegroundColor Green
Write-Host "╠═══════════════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║  New revisions roll out automatically (30-90 sec).            ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Green

