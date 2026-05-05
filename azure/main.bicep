// =============================================================================
// Quality Autopilot — Azure Container Apps Infrastructure
// =============================================================================
// Deploys:
//   • Azure Container Registry (ACR)
//   • Log Analytics Workspace
//   • Storage Account + Azure Files share  (PostgreSQL persistent volume)
//   • Container Apps Environment
//   • Container Apps for public-image services:
//       qap-db, github-mcp, ado-mcp, atlassian-mcp
//
// Custom-image services (qap-api, qap-ui, playwright-mcp) are deployed by
// azure/deploy.ps1 AFTER images are built and pushed to ACR.
// =============================================================================

targetScope = 'resourceGroup'

// ---------------------------------------------------------------------------
// Parameters
// ---------------------------------------------------------------------------

@description('Azure region for all resources. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Short lowercase prefix used in all resource names (3-8 chars).')
@minLength(3)
@maxLength(8)
param prefix string = 'qap'

@description('Environment label appended to resource names (dev / staging / prod).')
@allowed(['dev', 'staging', 'prod'])
param env string = 'dev'

// --- Database ---
@description('PostgreSQL superuser password.')
@secure()
param dbPass string

// --- LLM / Inference ---
@description('OpenRouter / Kilo AI API key.')
@secure()
param openrouterApiKey string = ''

@description('Kilo AI direct API key (KILO_API_KEY).')
@secure()
param kiloApiKey string = ''

@description('OpenAI API key (used when MODEL_PROVIDER=gpt4o_mini).')
@secure()
param openaiApiKey string = ''

@description('Google Gemini API key.')
@secure()
param googleApiKey string = ''

@description('Anthropic API key.')
@secure()
param anthropicApiKey string = ''

// --- Integrations ---
@description('GitHub Personal Access Token.')
@secure()
param githubToken string = ''

@description('Azure DevOps Personal Access Token.')
@secure()
param azureDevOpsPat string = ''

@description('Azure DevOps email (used for PAT basic-auth encoding).')
param azureDevOpsEmail string = ''

@description('Azure DevOps organisation URL (e.g. https://dev.azure.com/myorg).')
param azureDevOpsUrl string = ''

@description('Atlassian (Jira/Confluence) API token.')
@secure()
param atlassianApiToken string = ''

@description('Atlassian account email.')
param atlassianEmail string = ''

@description('Jira / Atlassian base URL (e.g. https://myorg.atlassian.net).')
param atlassianUrl string = ''

// --- AUT ---
@description('Application Under Test base URL.')
param autBaseUrl string = 'https://lokeshsharma99.github.io/GDS-Demo-App/'

@description('AUT GitHub owner.')
param autGithubOwner string = 'lokeshsharma99'

@description('AUT GitHub repository name.')
param autGithubRepo string = 'GDS-Demo-App'

// --- Scaling ---\n@description('Maximum number of qap-api replicas. Increase for higher concurrency.')\n@minValue(1)\n@maxValue(10)\nparam maxApiReplicas int = 3\n\n@description('Maximum number of playwright-mcp replicas. Each replica can serve one browser session at a time.')\n@minValue(1)\n@maxValue(5)\nparam maxPlaywrightReplicas int = 3\n\n// --- Postgres mode ---
@description('When true, deploy Azure Database for PostgreSQL Flexible Server instead of the ephemeral container DB. Recommended for multi-user production use.')
param useManagedPostgres bool = false

// --- Auth ---
@description('Secret key used to sign session tokens (generate with: openssl rand -hex 32).')
@secure()
param sessionSecret string

@description('Public base URL of the UI (used in invite/reset email links).')
param appBaseUrl string = ''

// --- Model provider ---
@description('Which LLM provider to use (kilo | kilo_paid | gemini | gpt4o_mini | haiku | nvidia).')
param modelProvider string = 'kilo'

// ---------------------------------------------------------------------------
// Variables
// ---------------------------------------------------------------------------

var resourcePrefix = '${prefix}-${env}'
var dbUser = 'ai'
var dbName = 'ai'

// Derived: internal hostname used as DB_HOST for the API container
// • Managed PostgreSQL: <server>.postgres.database.azure.com
// • Container DB:       <resourcePrefix>-db  (ACA internal DNS)
var pgHostName = useManagedPostgres
  ? '${resourcePrefix}-postgres.postgres.database.azure.com'
  : '${resourcePrefix}-db'

// ---------------------------------------------------------------------------
// Log Analytics Workspace
// ---------------------------------------------------------------------------
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${resourcePrefix}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ---------------------------------------------------------------------------
// Azure Container Registry
// ---------------------------------------------------------------------------
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: replace('${resourcePrefix}acr', '-', '')   // ACR names: alphanumeric only
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: true
  }
}

// ---------------------------------------------------------------------------
// Storage Account + Azure Files share  (PostgreSQL /var/lib/postgresql)
// ---------------------------------------------------------------------------
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: replace('${resourcePrefix}storage', '-', '')
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource fileServices 'Microsoft.Storage/storageAccounts/fileServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource pgdataShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-01-01' = {
  parent: fileServices
  name: 'pgdata'
  properties: {
    shareQuota: 32           // 32 GiB — adjust as needed
    enabledProtocols: 'SMB'
  }
}

// ---------------------------------------------------------------------------
// Container Apps Environment
// ---------------------------------------------------------------------------
resource acaEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${resourcePrefix}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

// ---------------------------------------------------------------------------
// Container App: qap-db  (ephemeral PostgreSQL — used when useManagedPostgres=false)
// ---------------------------------------------------------------------------
// NOTE: EmptyDir is ephemeral — data is lost on container restart.
// For multi-user production, set useManagedPostgres=true in parameters.json
// to use Azure Database for PostgreSQL Flexible Server instead.
resource qapDb 'Microsoft.App/containerApps@2023-05-01' = if (!useManagedPostgres) {
  name: '${resourcePrefix}-db'
  location: location
  properties: {
    managedEnvironmentId: acaEnv.id
    configuration: {
      ingress: {
        external: false
        targetPort: 5432
        transport: 'tcp'
        exposedPort: 5432
      }
      secrets: [
        { name: 'db-pass', value: dbPass }
      ]
    }
    template: {
      volumes: [
        {
          name: 'pgdata'
          storageType: 'EmptyDir'   // SMB lacks chmod support; use ephemeral storage
        }
      ]
      containers: [
        {
          name: 'qap-db'
          image: 'docker.io/agnohq/pgvector:18'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'POSTGRES_USER',     value: dbUser }
            { name: 'POSTGRES_PASSWORD', secretRef: 'db-pass' }
            { name: 'POSTGRES_DB',       value: dbName }
          ]
          volumeMounts: [
            { volumeName: 'pgdata', mountPath: '/var/lib/postgresql' }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}

// ---------------------------------------------------------------------------
// Azure Database for PostgreSQL Flexible Server
// Deployed only when useManagedPostgres=true.
// SKU: Burstable B1ms (~$12.50/month) — upgrade to GeneralPurpose for high load.
// pgvector extension is enabled via the configurations resource below.
// ---------------------------------------------------------------------------
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = if (useManagedPostgres) {
  name: '${resourcePrefix}-postgres'
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: dbUser
    administratorLoginPassword: dbPass
    storage: {
      storageSizeGB: 32
      autoGrow: 'Enabled'
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'   // Enable 'ZoneRedundant' for production HA
    }
    authConfig: {
      activeDirectoryAuth: 'Disabled'
      passwordAuth: 'Enabled'
    }
  }
}

// Allow all Azure services to connect (required for ACA → Flexible Server)
resource postgresFirewallAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-06-01-preview' = if (useManagedPostgres) {
  parent: postgresServer
  name: 'AllowAllAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Enable pgvector extension
resource postgresConfigPgVector 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-06-01-preview' = if (useManagedPostgres) {
  parent: postgresServer
  name: 'azure.extensions'
  properties: {
    value: 'VECTOR,PG_TRGM'
    source: 'user-override'
  }
}

// Create the target database
resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-06-01-preview' = if (useManagedPostgres) {
  parent: postgresServer
  name: dbName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// ---------------------------------------------------------------------------
// Container App: github-mcp  (GitHub MCP — internal HTTP)
// ---------------------------------------------------------------------------
resource githubMcp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${resourcePrefix}-github-mcp'
  location: location
  properties: {
    managedEnvironmentId: acaEnv.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8080
        transport: 'http'
      }
      secrets: [
        { name: 'github-token', value: githubToken }
      ]
    }
    template: {
      containers: [
        {
          name: 'github-mcp'
          image: 'ghcr.io/github/github-mcp-server'
          command: ['http', '--port=8080', '--toolsets=repos,issues,pull_requests,actions,discussions,git,users']
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            { name: 'GITHUB_PERSONAL_ACCESS_TOKEN', secretRef: 'github-token' }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}

// ---------------------------------------------------------------------------
// Container App: ado-mcp  (Azure DevOps MCP via supergateway — internal HTTP)
// ---------------------------------------------------------------------------
resource adoMcp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${resourcePrefix}-ado-mcp'
  location: location
  properties: {
    managedEnvironmentId: acaEnv.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8932
        transport: 'http'
      }
      secrets: [
        { name: 'ado-pat', value: azureDevOpsPat }
      ]
    }
    template: {
      containers: [
        {
          name: 'ado-mcp'
          image: 'docker.io/node:22-alpine'
          command: ['/bin/sh', '-c']
          args: [
            // Replicates the ado-mcp compose entrypoint exactly
            // Note: avoid ${VAR:-default} bash syntax — Bicep treats ${ as interpolation
            'export PERSONAL_ACCESS_TOKEN=$(printf \'%s:%s\' "$AZURE_DEVOPS_EMAIL" "$AZURE_DEVOPS_EXT_PAT" | base64 | tr -d \'\\n\'); ORG=$(echo "$AZURE_DEVOPS_URL" | sed \'s|.*dev.azure.com/||\' | cut -d/ -f1); [ -n "$ORG" ] || ORG=QEA; exec npx -y supergateway --stdio "npx -y @azure-devops/mcp $ORG --authentication pat -d core pipelines repositories work-items" --outputTransport streamableHttp --streamableHttpPath /mcp --port 8932'
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            { name: 'AZURE_DEVOPS_URL',       value: azureDevOpsUrl }
            { name: 'AZURE_DEVOPS_EMAIL',      value: azureDevOpsEmail }
            { name: 'AZURE_DEVOPS_EXT_PAT',    secretRef: 'ado-pat' }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}

// ---------------------------------------------------------------------------
// Container App: atlassian-mcp  (Jira + Confluence — internal HTTP)
// ---------------------------------------------------------------------------
resource atlassianMcp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${resourcePrefix}-atlassian-mcp'
  location: location
  properties: {
    managedEnvironmentId: acaEnv.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8933
        transport: 'http'
      }
      secrets: [
        { name: 'atlassian-token', value: atlassianApiToken }
      ]
    }
    template: {
      containers: [
        {
          name: 'atlassian-mcp'
          image: 'ghcr.io/sooperset/mcp-atlassian:latest'
          command: ['--transport', 'streamable-http', '--port', '8933', '--stateless']
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            { name: 'JIRA_URL',                value: atlassianUrl }
            { name: 'JIRA_USERNAME',           value: atlassianEmail }
            { name: 'JIRA_API_TOKEN',          secretRef: 'atlassian-token' }
            // Confluence URL always needs the /wiki path suffix
            { name: 'CONFLUENCE_URL',          value: '${atlassianUrl}/wiki' }
            { name: 'CONFLUENCE_USERNAME',     value: atlassianEmail }
            { name: 'CONFLUENCE_API_TOKEN',    secretRef: 'atlassian-token' }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}

// ---------------------------------------------------------------------------
// Outputs  (consumed by azure/deploy.ps1)
// ---------------------------------------------------------------------------

@description('ACR login server (e.g. qapdevacr.azurecr.io)')
output acrLoginServer string = acr.properties.loginServer

@description('ACR resource name')
output acrName string = acr.name

@description('Container Apps Environment resource ID')
output acaEnvId string = acaEnv.id

@description('PostgreSQL hostname (used as DB_HOST in qap-api). Points to Flexible Server when useManagedPostgres=true, container DB otherwise.')
output qapDbHost string = pgHostName

@description('Whether Azure Database for PostgreSQL Flexible Server is being used')
output useManagedPostgres bool = useManagedPostgres

@description('Resource prefix used to derive Container App names in deploy.ps1')
output resourcePrefix string = resourcePrefix

@description('Max API replicas — passed to deploy.ps1 for qap-api scaling rule')
output maxApiReplicas int = maxApiReplicas

@description('Max playwright-mcp replicas — passed to deploy.ps1')
output maxPlaywrightReplicas int = maxPlaywrightReplicas

@description('Resource group location')
output location string = location
