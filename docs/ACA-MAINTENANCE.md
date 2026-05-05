# Azure Container Apps — Maintenance & Update Guide

> **Stack**: Quality Autopilot on Azure Container Apps (ACA)  
> **Resource group**: `rg-quality-autopilot` (uksouth)  
> **Subscription**: `c3efdcab-3249-4063-8e26-a69191a3a268`

---

## Azure DevOps Pipeline

**Repo**: [vibecode/QAP](https://dev.azure.com/vibecode/QAP/_git/QAP)  
**Pipeline**: [QAP-CICD](https://dev.azure.com/vibecode/QAP/_build?definitionId=14) (defined in `azure-pipelines.yml`)

| Stage | Trigger | Status |
|-------|---------|--------|
| **Validate** — Python lint + TypeScript type-check | every push / PR | ✅ ready |
| **Build** — build & push `qap-api` + `qap-ui` to ACR | push to `main` or `feat/azure-deploy` | ✅ ready |
| **Deploy** — `az containerapp update` for API + UI | after Build | ⚠️ needs 1 manual step (see below) |

### One-time setup: ARM service connection

The Deploy stage uses an `AzureCLI@2` task that needs an Azure Resource Manager service connection named **`qap-azure-sc`**. Creating this requires Entra app registration — which is currently blocked by the Cognizant Conditional Access policy from the local CLI. Create it manually from a browser session:

1. Open [vibecode/QAP → Project Settings → Service connections](https://dev.azure.com/vibecode/QAP/_settings/adminservices)
2. Click **New service connection → Azure Resource Manager**
3. Choose **Workload Identity Federation (automatic)** ← recommended, no SP password to rotate
4. Select subscription `c3efdcab-3249-4063-8e26-a69191a3a268`
5. Leave resource group blank (subscription scope)
6. Name it exactly **`qap-azure-sc`**
7. Check **Grant access permission to all pipelines**
8. Save

Once saved the Deploy stage will activate automatically on the next push to `main`.

The Docker registry service connection (`qap-acr-connection`) and variable group (`qap-deploy-secrets`) are already configured.

---

## Live URLs

| Service | URL |
|---------|-----|
| UI (Control Plane) | `https://qap-dev-ui.nicesand-63588b93.uksouth.azurecontainerapps.io` |
| API (AgentOS) | `https://qap-dev-api.nicesand-63588b93.uksouth.azurecontainerapps.io` |
| API health check | `https://qap-dev-api.nicesand-63588b93.uksouth.azurecontainerapps.io/health` |

---

## Prerequisites

```powershell
az login                        # authenticate Azure CLI
az account set --subscription c3efdcab-3249-4063-8e26-a69191a3a268
az acr login --name qapdevacr   # authenticate Docker to the container registry
```

**Docker Desktop must be running** before any build step.

---

## 1. Full Redeploy (All Services)

Rebuilds every image, pushes to ACR, and updates all Container Apps in one shot.

```powershell
cd C:\Users\Lokesh-PC\Downloads\tests
.\azure\deploy.ps1
```

The script runs 5 phases automatically:

| Phase | What happens |
|-------|-------------|
| 1 | Creates/updates Azure infrastructure via Bicep (ACR, ACA environment, DB, MCP sidecars) |
| 2 | Builds `qap-api` + `playwright-mcp` Docker images, pushes to ACR |
| 3 | Creates/updates the `qap-dev-api` Container App |
| 4 | Builds `qap-ui` with `NEXT_PUBLIC_AGENTOS_URL` baked in, pushes to ACR |
| 5 | Creates/updates `qap-dev-ui` + `qap-dev-playwright-mcp`; patches API CORS |

Image tags use the timestamp format `yyyyMMdd-HHmm` (e.g. `20260505-1430`).

---

## 2. Update Only the API (No UI rebuild)

Use this when you change Python code in `agents/`, `app/`, `contracts/`, `db/`, or `workflows/`.

```powershell
# Set variables
$TAG        = (Get-Date -Format 'yyyyMMdd-HHmm')
$ACR        = "qapdevacr.azurecr.io"
$RG         = "rg-quality-autopilot"
$APP        = "qap-dev-api"
$API_IMAGE  = "${ACR}/qap-api:${TAG}"

# 1 — Build & push
az acr login --name qapdevacr
docker build -t $API_IMAGE -f Dockerfile .
docker push $API_IMAGE

# 2 — Update the Container App (creates a new revision automatically)
az containerapp update `
    --name $APP `
    --resource-group $RG `
    --image $API_IMAGE
```

> **Why no `--revision-suffix`?** ACA creates a new revision automatically on every `update`. You don't need to name it manually unless you want traffic splitting.

Verify the new revision is healthy:

```powershell
az containerapp revision list `
    --name qap-dev-api `
    --resource-group rg-quality-autopilot `
    --query "[].{name:name, state:properties.runningState, health:properties.healthState}" `
    -o table
```

---

## 3. Update Only the UI (Control Plane)

Use this when you change anything under `control-plane/src/`.

> **Important**: The UI image has `NEXT_PUBLIC_AGENTOS_URL` **baked in at build time**. You must pass the API URL as a build argument — do not skip it.

```powershell
$TAG       = (Get-Date -Format 'yyyyMMdd-HHmm')
$ACR       = "qapdevacr.azurecr.io"
$RG        = "rg-quality-autopilot"
$APP       = "qap-dev-ui"
$API_URL   = "https://qap-dev-api.nicesand-63588b93.uksouth.azurecontainerapps.io"
$UI_IMAGE  = "${ACR}/qap-ui:${TAG}"

# 1 — Build (bake API URL) & push
az acr login --name qapdevacr
docker build `
    -t $UI_IMAGE `
    --build-arg "NEXT_PUBLIC_AGENTOS_URL=$API_URL" `
    -f control-plane/Dockerfile `
    control-plane
docker push $UI_IMAGE

# 2 — Update the Container App
az containerapp update `
    --name $APP `
    --resource-group $RG `
    --image $UI_IMAGE
```

---

## 4. Update an Environment Variable (No Rebuild)

For config-only changes that don't require a new image.

```powershell
# Example: change the model provider
az containerapp update `
    --name qap-dev-api `
    --resource-group rg-quality-autopilot `
    --set-env-vars "MODEL_PROVIDER=gemini"

# Example: update CORS origins
az containerapp update `
    --name qap-dev-api `
    --resource-group rg-quality-autopilot `
    --set-env-vars "EXTRA_CORS_ORIGINS=https://qap-dev-ui.nicesand-63588b93.uksouth.azurecontainerapps.io"
```

> `--set-env-vars` **adds or overwrites** individual variables. Other env vars are preserved.

---

## 5. Update a Secret

Secrets (API keys, passwords) are stored as ACA secrets and referenced by env vars.

```powershell
# Step 1: update the secret value
az containerapp secret set `
    --name qap-dev-api `
    --resource-group rg-quality-autopilot `
    --secrets "kilo-api-key=<NEW_KEY>"

# Step 2: restart to pick up the new value
az containerapp revision restart `
    --name qap-dev-api `
    --resource-group rg-quality-autopilot `
    --revision $(az containerapp show --name qap-dev-api --resource-group rg-quality-autopilot --query "properties.latestRevisionName" -o tsv)
```

List current secrets (names only — values are never shown):

```powershell
az containerapp secret list `
    --name qap-dev-api `
    --resource-group rg-quality-autopilot `
    --query "[].name" -o tsv
```

---

## 6. Skip Infrastructure — Apps Only

If Bicep infrastructure already exists and you only want to rebuild/redeploy the application containers:

```powershell
.\azure\deploy.ps1 -AppsOnly
```

This reads the saved `azure/.deploy-state.json` (written by the last full deploy) and skips Phase 1.

---

## 7. Infrastructure Only (No Image Builds)

To update Bicep infrastructure without touching running containers:

```powershell
.\azure\deploy.ps1 -InfraOnly
```

---

## 8. Roll Back to a Previous Revision

Every `az containerapp update` creates a new revision. You can instantly switch traffic back to any previous revision.

```powershell
# 1 — List all revisions
az containerapp revision list `
    --name qap-dev-api `
    --resource-group rg-quality-autopilot `
    --query "[].{name:name, image:properties.template.containers[0].image, active:properties.active}" `
    -o table

# 2 — Activate a previous revision (sends 100% traffic to it)
az containerapp revision activate `
    --name qap-dev-api `
    --resource-group rg-quality-autopilot `
    --revision <PREVIOUS_REVISION_NAME>

# 3 — Set traffic to 100% on that revision
az containerapp ingress traffic set `
    --name qap-dev-api `
    --resource-group rg-quality-autopilot `
    --revision-weight <PREVIOUS_REVISION_NAME>=100
```

---

## 9. View Logs

```powershell
# Tail live logs (last 50 lines)
az containerapp logs show `
    --name qap-dev-api `
    --resource-group rg-quality-autopilot `
    --tail 50 --follow

# Filter for errors or auth events
az containerapp logs show `
    --name qap-dev-api `
    --resource-group rg-quality-autopilot `
    --tail 100 2>&1 | Select-String "ERROR|401|auth"

# UI logs
az containerapp logs show `
    --name qap-dev-ui `
    --resource-group rg-quality-autopilot `
    --tail 30
```

---

## 10. Restart a Container App

```powershell
# Restart all replicas of qap-dev-api (triggers _ensure_superuser re-seed)
az containerapp revision restart `
    --name qap-dev-api `
    --resource-group rg-quality-autopilot `
    --revision $(az containerapp show --name qap-dev-api --resource-group rg-quality-autopilot --query "properties.latestRevisionName" -o tsv)
```

---

## 11. Health Check After Any Update

```powershell
# Wait for startup then confirm API is alive
Start-Sleep -Seconds 30
curl -s "https://qap-dev-api.nicesand-63588b93.uksouth.azurecontainerapps.io/health"

# Confirm login still works
curl -s -X POST "https://qap-dev-api.nicesand-63588b93.uksouth.azurecontainerapps.io/auth/login" `
    -H "Content-Type: application/json" `
    -d '{"email":"admin@quality-autopilot.dev","password":"Admin@QAP123!"}'
```

Expected response from `/health`: `{"status":"healthy"}`  
Expected response from `/auth/login`: JSON with `session_token`, HTTP 200.

---

## Important Notes

### Database is Ephemeral

The `qap-dev-db` container uses **EmptyDir** storage — data is lost if the container restarts. The only account that survives a restart is the seeded superuser:

| Email | Password | Role |
|-------|----------|------|
| `admin@quality-autopilot.dev` | `Admin@QAP123!` | superuser |

To change these defaults, set env vars on `qap-dev-api` **before** first startup:

```powershell
az containerapp update `
    --name qap-dev-api `
    --resource-group rg-quality-autopilot `
    --set-env-vars "SUPERUSER_EMAIL=myemail@example.com" "SUPERUSER_INITIAL_PASSWORD=MyPassword123!"
```

### NEXT_PUBLIC_AGENTOS_URL Must Be Baked In

The UI's API URL is compiled into the Next.js bundle at Docker build time via `--build-arg NEXT_PUBLIC_AGENTOS_URL=...`. If you rebuild the UI image without this argument, the UI will point to nothing. **Always pass the API URL when building the UI image.**

### CORS Must Match the UI's Domain

The API's `EXTRA_CORS_ORIGINS` env var must match the UI's exact FQDN. `deploy.ps1` sets this automatically. If you deploy the UI manually and get CORS errors, run:

```powershell
az containerapp update `
    --name qap-dev-api `
    --resource-group rg-quality-autopilot `
    --set-env-vars "EXTRA_CORS_ORIGINS=https://<UI_FQDN>"
```

### Do Not Use `WARNING:` Output From az CLI in URLs

The Azure CLI can emit `WARNING:` lines mixed with output. The `Invoke-Az` helper in `deploy.ps1` strips these. If you run `az containerapp show ... -o tsv` directly in a script and use the result as a URL, pipe it through `| Where-Object { $_ -notmatch '^WARNING' }` first.

---

## Quick-Reference Cheatsheet

| Task | Command |
|------|---------|
| Full redeploy | `.\azure\deploy.ps1` |
| Apps only (skip Bicep) | `.\azure\deploy.ps1 -AppsOnly` |
| Infra only (skip images) | `.\azure\deploy.ps1 -InfraOnly` |
| Rebuild & push API only | See §2 above |
| Rebuild & push UI only | See §3 above |
| Change an env var | `az containerapp update --set-env-vars KEY=VALUE` |
| Update a secret | `az containerapp secret set --secrets name=value` + restart |
| Roll back | `az containerapp revision activate --revision <name>` |
| View live logs | `az containerapp logs show --tail 50 --follow` |
| Health check | `curl .../health` |
| List revisions | `az containerapp revision list -o table` |
