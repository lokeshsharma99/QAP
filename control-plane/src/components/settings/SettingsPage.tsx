'use client'
import { motion } from 'framer-motion'
import { useState, useEffect, useCallback } from 'react'
import { useStore } from '@/store'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { isValidUrl } from '@/lib/utils'
import { constructEndpointUrl } from '@/lib/constructEndpointUrl'
import useChatActions from '@/hooks/useChatActions'
import {
  Server, KeyRound, Bot, Database, Globe, Wrench,
  ShieldCheck, RefreshCw, Save, Eye, EyeOff, CheckCircle2,
  AlertCircle, CircleDot, Cpu, Zap, Users, GitBranch, WifiOff, Wifi
} from 'lucide-react'
import AgentConfigPanel from '@/components/chat/AgentConfigPanel'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FieldDef {
  key: string
  label: string
  placeholder: string
  secret?: boolean
  description?: string
  wide?: boolean
}

interface SectionDef {
  id: string
  title: string
  icon: React.ElementType
  fields: FieldDef[]
}

// ---------------------------------------------------------------------------
// Nav tab definitions — each tab may contain one or more SectionDef groups
// ---------------------------------------------------------------------------

type NavTab = {
  id: string
  label: string
  icon: React.ElementType
  sections: SectionDef[]
}

const NAV_TABS: NavTab[] = [
  {
    id: 'provider',
    label: 'Provider & Model',
    icon: Cpu,
    sections: [], // rendered separately via ModelProviderSection
  },
  {
    id: 'agents',
    label: 'Agents',
    icon: Users,
    sections: [], // rendered separately via AgentSettingsSection
  },
  {
    id: 'connection',
    label: 'Connection',
    icon: Server,
    sections: [
      {
        id: 'connection',
        title: 'Connection',
        icon: Server,
        fields: [
          { key: '_endpoint', label: 'AgentOS Backend URL', placeholder: 'http://localhost:8000', description: 'The FastAPI AgentOS endpoint this UI connects to.' },
          { key: '_authToken', label: 'Auth Token', placeholder: 'Bearer token (optional)', secret: true, description: 'JWT Bearer token — required when RUNTIME_ENV=prd.' },
        ],
      },
    ],
  },
  {
    id: 'llm',
    label: 'LLM Keys',
    icon: KeyRound,
    sections: [
      {
        id: 'kilo',
        title: 'Kilo AI (Default)',
        icon: Zap,
        fields: [
          { key: 'KILO_API_KEY', label: 'Kilo API Key', placeholder: 'kilo-...', secret: true, description: 'Free tier works without a key. Get one at: app.kilo.ai — unlocks kilo-auto/balanced.' },
          { key: 'OPENROUTER_BASE_URL', label: 'Base URL', placeholder: 'https://api.kilo.ai/api/openrouter/v1', wide: true },
        ],
      },
      {
        id: 'github_copilot',
        title: 'GitHub Copilot (Local Proxy)',
        icon: Bot,
        fields: [
          { key: 'GITHUB_COPILOT_BASE_URL', label: 'Proxy Base URL', placeholder: 'http://127.0.0.1:3030/v1', wide: true, description: 'The Copilot Chat VS Code extension exposes an OpenAI-compatible server on 127.0.0.1:3030.' },
          { key: 'GITHUB_COPILOT_API_KEY', label: 'API Key', placeholder: 'optional', secret: true, description: 'Not required — the extension handles auth. Leave as "optional".' },
        ],
      },
      {
        id: 'nvidia',
        title: 'NVIDIA NIM',
        icon: Cpu,
        fields: [
          { key: 'NVIDIA_API_KEY', label: 'NVIDIA API Key', placeholder: 'nvapi-...', secret: true, description: 'Get a free key at: build.nvidia.com — supports Qwen3 Coder, Llama 3.3, Nemotron, Phi-3, Gemma 2.' },
        ],
      },
      {
        id: 'ollama',
        title: 'Ollama',
        icon: Bot,
        fields: [
          { key: 'OLLAMA_API_KEY', label: 'Ollama API Key', placeholder: 'd73713...', secret: true },
          { key: 'OLLAMA_BASE_URL', label: 'Ollama Base URL', placeholder: 'http://host.docker.internal:11434' },
          { key: 'OLLAMA_MODEL', label: 'Model', placeholder: 'minimax-m2.7:cloud' },
          { key: 'OLLAMA_MODELS', label: 'Available Models (comma-separated)', placeholder: 'minimax-m2.7:cloud,glm-5.1:cloud', wide: true },
        ],
      },
      {
        id: 'fallback',
        title: 'Fallback LLM Keys',
        icon: KeyRound,
        fields: [
          { key: 'OPENAI_API_KEY', label: 'OpenAI API Key', placeholder: 'sk-...', secret: true },
          { key: 'ANTHROPIC_API_KEY', label: 'Anthropic API Key', placeholder: 'sk-ant-...', secret: true },
          { key: 'GOOGLE_API_KEY', label: 'Google / Gemini API Key', placeholder: 'AIza...', secret: true },
        ],
      },
    ],
  },
  {
    id: 'integrations',
    label: 'Integrations',
    icon: Wrench,
    sections: [
      {
        id: 'integrations',
        title: 'Integrations',
        icon: Wrench,
        fields: [
          { key: 'GITHUB_TOKEN', label: 'GitHub Token', placeholder: 'ghp_...', secret: true, description: 'Used by Engineer agent for PR creation. Also enables GitHub MCP (repos, issues, actions).' },
          { key: 'SERPER_API_KEY', label: 'Serper API Key (Search)', placeholder: 'a8e7e6...', secret: true },
        ],
      },
      {
        id: 'mcp_servers',
        title: 'MCP Servers',
        icon: GitBranch,
        fields: [
          { key: '_mcp_info', label: 'GitHub MCP', placeholder: 'Enabled when GITHUB_TOKEN is set — uses @modelcontextprotocol/server-github via npx', description: 'Active on: Architect, Discovery, Engineer, Detective, Pipeline Analyst, Impact Analyst' },
          { key: '_ado_mcp_info', label: 'Azure DevOps MCP', placeholder: 'Enabled when AZURE_DEVOPS_URL + AZURE_DEVOPS_PAT are set — uses @azure-devops/mcp via npx', description: 'Active on: Pipeline Analyst (pipelines), CI Log Analyzer (pipelines + work-items), Architect (work-items)' },
          { key: '_atlassian_mcp_info', label: 'Atlassian Rovo MCP', placeholder: 'Enabled when ATLASSIAN_EMAIL + ATLASSIAN_API_TOKEN are set — uses mcp-remote proxy to mcp.atlassian.com', description: 'Active on: Architect (Jira), Scribe (Jira + Confluence), CI Log Analyzer (Jira bugs)' },
          { key: '_playwright_mcp_info', label: 'Playwright MCP', placeholder: 'Auto-mode: set PLAYWRIGHT_MCP_URL for Docker service, or leave unset to spawn npx headless inline', description: 'Active on: Discovery (AUT crawling, Site Manifesto), Medic (verify healed locators on live AUT)' },
          { key: 'PLAYWRIGHT_MCP_URL', label: 'Playwright MCP Service URL (optional)', placeholder: 'http://playwright-mcp:8931', description: 'Leave blank to use inline npx headless mode. Set to http://playwright-mcp:8931 when using: docker compose --profile mcp up -d' },
        ],
      },
    ],
  },
  {
    id: 'aut',
    label: 'AUT',
    icon: Globe,
    sections: [
      {
        id: 'aut',
        title: 'Application Under Test (AUT)',
        icon: Globe,
        fields: [
          { key: 'AUT_BASE_URL', label: 'AUT Base URL', placeholder: 'https://example.com/', wide: true },
          { key: 'AUT_AUTH_USER', label: 'AUT Auth Username', placeholder: 'admin@example.com' },
          { key: 'AUT_AUTH_PASS', label: 'AUT Auth Password', placeholder: '••••••••', secret: true },
        ],
      },
    ],
  },
  {
    id: 'database',
    label: 'Database',
    icon: Database,
    sections: [
      {
        id: 'database',
        title: 'Database (PostgreSQL)',
        icon: Database,
        fields: [
          { key: 'DB_USER', label: 'DB User', placeholder: 'ai' },
          { key: 'DB_PASS', label: 'DB Password', placeholder: '••••••••', secret: true },
          { key: 'DB_HOST', label: 'DB Host', placeholder: 'localhost' },
          { key: 'DB_PORT', label: 'DB Port', placeholder: '5432' },
          { key: 'DB_DATABASE', label: 'DB Name', placeholder: 'ai' },
        ],
      },
    ],
  },
  {
    id: 'trackers',
    label: 'Issue Trackers',
    icon: ShieldCheck,
    sections: [
      {
        id: 'jira',
        title: 'Jira',
        icon: ShieldCheck,
        fields: [
          { key: 'JIRA_URL', label: 'Jira URL', placeholder: 'https://yourorg.atlassian.net', wide: true },
          { key: 'JIRA_USERNAME', label: 'Jira Username / Email', placeholder: 'user@example.com' },
          { key: 'JIRA_API_TOKEN', label: 'Jira API Token', placeholder: 'ATATT3x...', secret: true },
        ],
      },
      {
        id: 'confluence',
        title: 'Confluence',
        icon: ShieldCheck,
        fields: [
          { key: 'CONFLUENCE_URL', label: 'Confluence URL', placeholder: 'https://yourorg.atlassian.net/wiki', wide: true },
          { key: 'CONFLUENCE_EMAIL', label: 'Confluence Email', placeholder: 'user@example.com' },
          { key: 'CONFLUENCE_API_TOKEN', label: 'Confluence API Token', placeholder: 'ATATT3x...', secret: true },
        ],
      },
      {
        id: 'azuredevops',
        title: 'Azure DevOps',
        icon: ShieldCheck,
        fields: [
          { key: 'AZURE_DEVOPS_URL', label: 'Azure DevOps URL', placeholder: 'https://dev.azure.com/yourorg', wide: true, description: 'Org name is auto-extracted for the ADO MCP server (@azure-devops/mcp).' },
          { key: 'AZURE_DEVOPS_EMAIL', label: 'Email', placeholder: 'user@example.com' },
          { key: 'AZURE_DEVOPS_PAT', label: 'Personal Access Token', placeholder: 'PAT...', secret: true, description: 'Also used as AZURE_DEVOPS_EXT_PAT for headless MCP auth (no browser required).' },
          { key: 'AZURE_DEVOPS_PROJECT', label: 'Default Project Name', placeholder: 'MyProject' },
        ],
      },
      {
        id: 'atlassian_mcp',
        title: 'Atlassian Rovo MCP (Jira + Confluence)',
        icon: ShieldCheck,
        fields: [
          { key: 'ATLASSIAN_URL', label: 'Atlassian Site URL', placeholder: 'https://yourorg.atlassian.net', wide: true, description: 'Your Atlassian Cloud site. Admin must enable API token auth in Atlassian Administration → Security → Rovo MCP Server settings.' },
          { key: 'ATLASSIAN_EMAIL', label: 'Atlassian Email', placeholder: 'user@example.com' },
          { key: 'ATLASSIAN_API_TOKEN', label: 'Atlassian API Token', placeholder: 'ATATT3x...', secret: true, description: 'Create at: id.atlassian.com/manage-profile/security/api-tokens' },
          { key: 'ATLASSIAN_CLOUD_ID', label: 'Cloud ID (optional)', placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx', description: 'Skips discovery round-trips. Find at: yourorg.atlassian.net/_edge/tenant_info' },
          { key: 'ATLASSIAN_JIRA_PROJECT', label: 'Default Jira Project Key (optional)', placeholder: 'QAP' },
          { key: 'ATLASSIAN_CONFLUENCE_SPACE', label: 'Default Confluence SpaceId (optional)', placeholder: '123456' },
        ],
      },
    ],
  },
  {
    id: 'runtime',
    label: 'Runtime',
    icon: CircleDot,
    sections: [
      {
        id: 'runtime',
        title: 'Runtime',
        icon: CircleDot,
        fields: [
          { key: 'RUNTIME_ENV', label: 'Runtime Environment', placeholder: 'dev', description: '"dev" enables hot-reload. "prd" enables JWT RBAC.' },
        ],
      },
    ],
  },
]

// ---------------------------------------------------------------------------
// Provider & Model section (custom — not in generic SECTIONS)
// ---------------------------------------------------------------------------

interface ProviderModel { id: string; label: string }
interface ProviderInfo {
  name: string; description: string; base_url: string
  models: ProviderModel[]; default_model: string; requires_key: boolean; key_env: string | null
}
interface ProvidersData {
  providers: Record<string, ProviderInfo>
  active_provider: string
  active_model: string
}

const PROVIDER_EMOJI: Record<string, string> = {
  kilo: '⚡', nvidia: '🟢', github_copilot: '🐙', openai: '◈', ollama: '🦙', openrouter: '🔄',
}

const ModelProviderSection = ({ endpointUrl, authToken }: { endpointUrl: string; authToken: string }) => {
  const { setActiveProvider, setActiveModelId, activeProvider, activeModelId } = useStore()
  const [providers, setProviders] = useState<ProvidersData | null>(null)
  const [localKeys, setLocalKeys] = useState<Record<string, string>>({})
  const [localModels, setLocalModels] = useState<Record<string, string>>({})
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({})
  const [activating, setActivating] = useState<string | null>(null)
  // Live model lists fetched from provider APIs (keyed by provider id)
  const [liveModelLists, setLiveModelLists] = useState<Record<string, ProviderModel[]>>({})
  const [fetchingModels, setFetchingModels] = useState<Record<string, boolean>>({})

  useEffect(() => {
    fetchProviders()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchProviders = async () => {
    try {
      const res = await fetch(`${endpointUrl}/model/providers`, {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      })
      if (res.ok) {
        const data: ProvidersData = await res.json()
        setProviders(data)
        // Sync store
        if (data.active_provider) setActiveProvider(data.active_provider)
        if (data.active_model) setActiveModelId(data.active_model)
        // Init model selection per provider
        const init: Record<string, string> = {}
        for (const [id, info] of Object.entries(data.providers)) {
          init[id] = id === data.active_provider ? data.active_model : info.default_model
        }
        setLocalModels(init)
      }
    } catch { /* backend may not support this endpoint */ }
  }

  const fetchLiveModels = async (pid: string) => {
    setFetchingModels((p) => ({ ...p, [pid]: true }))
    try {
      const res = await fetch(`${endpointUrl}/model/list/${pid}`, {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      })
      if (res.ok) {
        const data: { models: ProviderModel[]; source: string } = await res.json()
        if (data.models.length > 0) {
          setLiveModelLists((p) => ({ ...p, [pid]: data.models }))
          // If current selection not in new list, reset to first
          setLocalModels((prev) => {
            const cur = prev[pid]
            const valid = data.models.some((m) => m.id === cur)
            return valid ? prev : { ...prev, [pid]: data.models[0].id }
          })
          if (data.source === 'live') toast.success(`${pid}: ${data.models.length} models loaded`)
          else toast.info(`${pid}: using static model list`)
        }
      }
    } catch { /* ignore */ }
    setFetchingModels((p) => ({ ...p, [pid]: false }))
  }

  const handleActivate = async (providerId: string) => {
    if (!providers) return
    const modelId = localModels[providerId] || providers.providers[providerId]?.default_model || ''
    const apiKey = localKeys[providerId]

    setActivating(providerId)
    try {
      const body: Record<string, string> = { provider: providerId, model_id: modelId }
      if (apiKey) body.api_key = apiKey

      const res = await fetch(`${endpointUrl}/model/switch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify(body),
      })
      if (res.ok) {
        const data = await res.json()
        setActiveProvider(providerId)
        setActiveModelId(modelId)
        toast.success(data.message ?? `Switched to ${modelId}`)
        await fetchProviders()
      } else {
        toast.error('Failed to switch model — check API key if required')
      }
    } catch {
      toast.error('Backend unreachable')
    }
    setActivating(null)
  }

  const effectiveActive = providers?.active_provider ?? activeProvider
  const effectiveModel = providers?.active_model ?? activeModelId

  return (
    <div className="rounded-2xl border border-primary/10 bg-primaryAccent p-5">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="size-4 text-brand" />
          <h2 className="text-sm font-semibold text-primary">Provider &amp; Model</h2>
        </div>
        {providers && (
          <div className="flex items-center gap-1.5 rounded-lg border border-positive/25 bg-positive/5 px-2.5 py-1 text-xs">
            <Zap className="size-3 text-positive" />
            <span className="font-medium text-positive">
              {providers.providers[effectiveActive]?.name ?? effectiveActive}
            </span>
            <span className="text-muted/50">/</span>
            <span className="font-mono text-muted">{effectiveModel}</span>
          </div>
        )}
      </div>

      {!providers ? (
        <div className="text-xs text-muted/50">Connect to backend to load providers…</div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          {Object.entries(providers.providers).map(([pid, pInfo]) => {
            const isActive = effectiveActive === pid
            const selectedModel = localModels[pid] || pInfo.default_model
            const showKey = showKeys[pid] ?? false
            const modelList = liveModelLists[pid] ?? pInfo.models
            const isFetching = fetchingModels[pid] ?? false

            return (
              <div
                key={pid}
                className={cn(
                  'rounded-xl border p-3 transition-colors',
                  isActive
                    ? 'border-brand/40 bg-brand/5'
                    : 'border-primary/10 bg-background hover:border-primary/20'
                )}
              >
                {/* Provider header */}
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="text-base leading-none">{PROVIDER_EMOJI[pid] ?? '◈'}</span>
                    <span className="text-xs font-semibold text-primary">{pInfo.name}</span>
                  </div>
                  {isActive && (
                    <span className="rounded-full bg-brand/15 px-1.5 py-0.5 text-[10px] font-medium text-brand">
                      Active
                    </span>
                  )}
                </div>

                <p className="mb-2 text-[10px] leading-relaxed text-muted/60">{pInfo.description}</p>

                {/* Model selector with live-refresh button */}
                <div className="mb-2">
                  <div className="mb-1 flex items-center justify-between">
                    <label className="text-[10px] font-medium text-muted/70">Model</label>
                    <button
                      type="button"
                      onClick={() => fetchLiveModels(pid)}
                      disabled={isFetching}
                      title="Fetch live models from provider"
                      className="flex items-center gap-0.5 rounded px-1 py-0.5 text-[9px] text-muted/50 hover:bg-accent hover:text-primary disabled:opacity-40"
                    >
                      <RefreshCw className={cn('size-2.5', isFetching && 'animate-spin')} />
                      {liveModelLists[pid] ? 'live' : 'refresh'}
                    </button>
                  </div>
                  <select
                    value={selectedModel}
                    onChange={(e) => setLocalModels((p) => ({ ...p, [pid]: e.target.value }))}
                    className="w-full rounded-lg border border-primary/15 bg-accent px-2 py-1.5 text-xs text-primary outline-none focus:border-primary/40"
                  >
                    {modelList.map((m) => (
                      <option key={m.id} value={m.id}>{m.label}</option>
                    ))}
                  </select>
                </div>

                {/* API key (if required) */}
                {pInfo.requires_key && (
                  <div className="mb-2">
                    <label className="mb-1 block text-[10px] font-medium text-muted/70">
                      API Key
                      {isActive && <span className="ml-1 text-positive">(active)</span>}
                    </label>
                    <div className="relative">
                      <input
                        type={showKey ? 'text' : 'password'}
                        value={localKeys[pid] ?? ''}
                        onChange={(e) => setLocalKeys((p) => ({ ...p, [pid]: e.target.value }))}
                        placeholder={isActive ? '••••••••' : `Enter ${pInfo.name} API key`}
                        className="w-full rounded-lg border border-primary/15 bg-accent px-2 py-1.5 pr-7 text-xs text-primary outline-none placeholder:text-muted/40 focus:border-primary/40"
                      />
                      <button
                        type="button"
                        onClick={() => setShowKeys((p) => ({ ...p, [pid]: !showKey }))}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-primary"
                      >
                        {showKey ? <EyeOff className="size-3" /> : <Eye className="size-3" />}
                      </button>
                    </div>
                  </div>
                )}

                {/* Activate button */}
                <button
                  onClick={() => handleActivate(pid)}
                  disabled={activating === pid || (isActive && !localKeys[pid])}
                  className={cn(
                    'w-full rounded-lg py-1.5 text-xs font-medium transition-colors',
                    isActive && !localKeys[pid]
                      ? 'cursor-default bg-brand/10 text-brand'
                      : 'bg-primary text-primaryAccent hover:opacity-90 disabled:opacity-50'
                  )}
                >
                  {activating === pid
                    ? 'Activating…'
                    : isActive && !localKeys[pid]
                      ? '✓ Active'
                      : isActive
                        ? 'Update Key & Re-activate'
                        : 'Activate'}
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

const MASK = '••••••••'

// ---------------------------------------------------------------------------
// MCP Status Section
// ---------------------------------------------------------------------------

interface MCPServiceStatus {
  name: string
  url: string
  reachable: boolean
  tools: number
  configured: boolean
  agents: string[]
}

interface MCPStatusData {
  services: Record<string, MCPServiceStatus>
}

const MCP_SERVICE_ORDER = ['github', 'ado', 'playwright'] as const

const MCPStatusSection = ({ endpointUrl, authToken }: { endpointUrl: string; authToken: string }) => {
  const [data, setData] = useState<MCPStatusData | null>(null)
  const [checking, setChecking] = useState(false)
  const [lastChecked, setLastChecked] = useState<string | null>(null)

  const check = async () => {
    setChecking(true)
    try {
      const res = await fetch(`${endpointUrl}/mcp/status`, {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      })
      if (res.ok) {
        setData(await res.json())
        setLastChecked(new Date().toLocaleTimeString())
      }
    } catch { /* backend unreachable */ }
    setChecking(false)
  }

  useEffect(() => { check() }, [endpointUrl]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="rounded-2xl border border-primary/10 bg-primaryAccent p-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitBranch className="size-4 text-brand" />
          <h2 className="text-sm font-semibold text-primary">MCP Servers</h2>
        </div>
        <div className="flex items-center gap-2">
          {lastChecked && <span className="text-[10px] text-muted/40">checked {lastChecked}</span>}
          <button
            onClick={check}
            disabled={checking}
            className="flex items-center gap-1 rounded-lg border border-primary/15 px-2 py-1 text-[10px] font-medium text-muted hover:bg-accent hover:text-primary disabled:opacity-50"
          >
            <RefreshCw className={cn('size-3', checking && 'animate-spin')} />
            {checking ? 'Checking…' : 'Test All'}
          </button>
        </div>
      </div>

      {!data ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => <div key={i} className="h-16 rounded-xl bg-accent/50 animate-pulse" />)}
        </div>
      ) : (
        <div className="space-y-2">
          {MCP_SERVICE_ORDER.map((key) => {
            const svc = data.services[key]
            if (!svc) return null
            const ok = svc.reachable && svc.configured
            const warn = svc.reachable && !svc.configured
            return (
              <div
                key={key}
                className={cn(
                  'flex items-center gap-3 rounded-xl border px-3 py-2.5 transition-colors',
                  ok ? 'border-positive/20 bg-positive/5'
                    : warn ? 'border-warning/20 bg-warning/5'
                      : 'border-primary/10 bg-background'
                )}
              >
                {/* Status icon */}
                <div className="shrink-0">
                  {ok
                    ? <CheckCircle2 className="size-4 text-positive" />
                    : svc.reachable
                      ? <AlertCircle className="size-4 text-warning" />
                      : <WifiOff className="size-4 text-muted/40" />}
                </div>

                {/* Name + URL */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-primary">{svc.name}</span>
                    {svc.tools > 0 && (
                      <span className="rounded-full bg-positive/15 px-1.5 py-0.5 text-[10px] font-medium text-positive">
                        {svc.tools} tools
                      </span>
                    )}
                  </div>
                  <p className="truncate text-[10px] text-muted/50">{svc.url}</p>
                </div>

                {/* Status text + agents */}
                <div className="shrink-0 text-right">
                  <p className={cn(
                    'text-[10px] font-medium',
                    ok ? 'text-positive' : svc.reachable ? 'text-warning' : 'text-muted/50'
                  )}>
                    {ok ? 'Connected' : svc.reachable ? 'No credentials' : 'Offline'}
                  </p>
                  <p className="text-[10px] text-muted/40">{svc.agents.slice(0, 2).join(', ')}{svc.agents.length > 2 ? ` +${svc.agents.length - 2}` : ''}</p>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Agent Settings Section
// ---------------------------------------------------------------------------

const AgentSettingsSection = ({ endpointUrl, authToken }: { endpointUrl: string; authToken: string }) => {
  const [agentList, setAgentList] = useState<Array<{ id: string; name: string }>>([])
  const [teamList, setTeamList] = useState<Array<{ id: string; name: string }>>([])
  const [entityType, setEntityType] = useState<'agent' | 'team'>('agent')
  const [selectedId, setSelectedId] = useState<string>('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const headers: HeadersInit = authToken ? { Authorization: `Bearer ${authToken}` } : {}
    Promise.all([
      fetch(`${endpointUrl}/agents`, { headers }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch(`${endpointUrl}/teams`, { headers }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
    ]).then(([agentsData, teamsData]) => {
      const agents: Array<{ id: string; name: string }> = Array.isArray(agentsData)
        ? agentsData
        : (agentsData?.agents ?? [])
      const teams: Array<{ id: string; name: string }> = Array.isArray(teamsData)
        ? teamsData
        : (teamsData?.teams ?? [])
      setAgentList(agents)
      setTeamList(teams)
      if (agents.length > 0) setSelectedId(agents[0].id)
    }).finally(() => setLoading(false))
  }, [endpointUrl, authToken])

  const handleTypeChange = (type: 'agent' | 'team') => {
    setEntityType(type)
    const list = type === 'agent' ? agentList : teamList
    setSelectedId(list[0]?.id ?? '')
  }

  const items = entityType === 'agent' ? agentList : teamList

  if (loading) {
    return (
      <div className="rounded-2xl border border-primary/10 bg-primaryAccent p-5 space-y-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-10 rounded-xl bg-accent/60 animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-primary/10 bg-primaryAccent overflow-hidden">
      {/* Top bar: type switcher + entity selector */}
      <div className="flex items-center gap-3 border-b border-accent/50 bg-background/50 px-4 py-3">
        {/* Agents / Teams toggle */}
        <div className="flex rounded-lg border border-primary/15 overflow-hidden shrink-0">
          {(['agent', 'team'] as const).map((t) => (
            <button
              key={t}
              onClick={() => handleTypeChange(t)}
              className={cn(
                'px-3 py-1.5 text-xs font-medium transition-colors',
                entityType === t
                  ? 'bg-primary text-primaryAccent'
                  : 'text-muted hover:bg-accent hover:text-primary'
              )}
            >
              {t === 'agent' ? 'Agents' : 'Teams'}
            </button>
          ))}
        </div>

        {/* Entity selector */}
        <select
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
          className="flex-1 rounded-xl border border-primary/15 bg-accent px-3 py-1.5 text-xs text-primary outline-none focus:border-primary/40"
        >
          {items.length === 0 && (
            <option value="">No {entityType === 'agent' ? 'agents' : 'teams'} available</option>
          )}
          {items.map((item) => (
            <option key={item.id} value={item.id}>{item.name ?? item.id}</option>
          ))}
        </select>
      </div>

      {/* Config panel */}
      <div className="h-[600px]">
        {selectedId ? (
          <AgentConfigPanel entityId={selectedId} entityType={entityType} />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-muted/50">
            Select an {entityType} to configure
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const FieldInput = ({
  field,
  value,
  onChange,
  fromBackend,
}: {
  field: FieldDef
  value: string
  onChange: (v: string) => void
  fromBackend?: boolean
}) => {
  const [show, setShow] = useState(false)

  return (
    <div className={cn('flex flex-col gap-1', field.wide ? 'col-span-2' : '')}>
      <label className="text-xs font-medium text-muted/80">{field.label}</label>
      <div className="relative">
        <input
          type={field.secret && !show ? 'password' : 'text'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
          className="w-full rounded-xl border border-primary/15 bg-accent px-3 py-2 text-xs text-primary outline-none placeholder:text-muted/40 focus:border-primary/40"
        />
        {field.secret && (
          <button
            type="button"
            onClick={() => setShow((s) => !s)}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-primary"
          >
            {show ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
          </button>
        )}
      </div>
      {field.description && (
        <p className="text-[10px] text-muted/50">{field.description}</p>
      )}
      {fromBackend && value === MASK && (
        <p className="text-[10px] text-warning/70">Value set in backend — enter a new value to override</p>
      )}
    </div>
  )
}

const Section = ({
  section,
  values,
  backendValues,
  onChange,
}: {
  section: SectionDef
  values: Record<string, string>
  backendValues: Record<string, string>
  onChange: (key: string, value: string) => void
}) => {
  const Icon = section.icon
  return (
    <div className="rounded-2xl border border-primary/10 bg-primaryAccent p-5">
      <div className="mb-4 flex items-center gap-2">
        <Icon className="size-4 text-brand" />
        <h2 className="text-sm font-semibold text-primary">{section.title}</h2>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {section.fields.map((f) => (
          <FieldInput
            key={f.key}
            field={f}
            value={values[f.key] ?? ''}
            onChange={(v) => onChange(f.key, v)}
            fromBackend={!!backendValues[f.key] && backendValues[f.key] === MASK}
          />
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main SettingsPage
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  const {
    selectedEndpoint, setSelectedEndpoint,
    authToken, setAuthToken,
    envSettings, setEnvSettings,
    setAgents, setTeams, setWorkflows, setSessionsData, setMessages,
  } = useStore()
  const { initialize } = useChatActions()

  // Local working copy of all field values
  const [values, setValues] = useState<Record<string, string>>({})
  // What we loaded from the backend (to detect masked secrets)
  const [backendValues, setBackendValues] = useState<Record<string, string>>({})
  const [isSaving, setIsSaving] = useState(false)
  const [isLoadingBackend, setIsLoadingBackend] = useState(false)
  const [endpointStatus, setEndpointStatus] = useState<'checking' | 'ok' | 'error'>('checking')
  const [activeTab, setActiveTab] = useState('provider')

  // Initialise from store on mount
  useEffect(() => {
    const initial: Record<string, string> = {
      _endpoint: selectedEndpoint,
      _authToken: authToken,
      ...envSettings,
    }
    setValues(initial)
    // Try to load current backend values
    loadFromBackend(selectedEndpoint)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadFromBackend = useCallback(async (ep: string) => {
    setIsLoadingBackend(true)
    try {
      const base = ep.replace(/\/$/, '')
      const res = await fetch(`${base}/settings`, {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      })
      if (res.ok) {
        const data: Record<string, string> = await res.json()
        setBackendValues(data)
        // Merge: only fill in keys that are empty locally
        setValues((prev) => {
          const merged = { ...prev }
          for (const [k, v] of Object.entries(data)) {
            if (!merged[k] || merged[k] === '') {
              merged[k] = v
            }
          }
          return merged
        })
        setEndpointStatus('ok')
      } else {
        setEndpointStatus('error')
      }
    } catch {
      setEndpointStatus('error')
    } finally {
      setIsLoadingBackend(false)
    }
  }, [authToken])

  const handleChange = (key: string, value: string) => {
    setValues((prev) => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    const newEndpoint = (values['_endpoint'] ?? selectedEndpoint).replace(/\/$/, '').trim()
    const newAuthToken = values['_authToken'] ?? authToken

    // Validate endpoint
    if (newEndpoint && !isValidUrl(newEndpoint)) {
      toast.error('AgentOS Backend URL is not a valid URL')
      return
    }

    setIsSaving(true)

    // 1. Update connection state
    if (newEndpoint !== selectedEndpoint) {
      setSelectedEndpoint(newEndpoint)
      setAgents([])
      setTeams([])
      setWorkflows([])
      setSessionsData([])
      setMessages([])
    }
    if (newAuthToken !== authToken) {
      setAuthToken(newAuthToken)
    }

    // 2. Build backend payload (strip internal _keys)
    const backendPayload: Record<string, string> = {}
    for (const [k, v] of Object.entries(values)) {
      if (!k.startsWith('_') && v !== '') {
        backendPayload[k] = v
      }
    }

    // 3. Persist to local store
    setEnvSettings(backendPayload)

    // 4. POST to backend
    try {
      const base = newEndpoint.replace(/\/$/, '')
      const res = await fetch(`${base}/settings/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(newAuthToken ? { Authorization: `Bearer ${newAuthToken}` } : {}),
        },
        body: JSON.stringify({ settings: backendPayload }),
      })

      if (res.ok) {
        const data = await res.json()
        toast.success(`Settings saved — ${data.count} variable${data.count !== 1 ? 's' : ''} applied to backend`)
        // Re-initialize agents/teams/workflows
        await initialize()
        // Reload backend values to get fresh masked secrets
        await loadFromBackend(newEndpoint)
      } else {
        toast.warning('Settings saved locally — could not reach backend to apply')
      }
    } catch {
      toast.warning('Settings saved locally — backend unreachable')
    } finally {
      setIsSaving(false)
    }
  }

  const StatusDot = () => (
    <span
      className={cn(
        'inline-block size-2 rounded-full',
        endpointStatus === 'checking' ? 'animate-pulse bg-warning' :
          endpointStatus === 'ok' ? 'bg-positive' : 'bg-destructive'
      )}
    />
  )

  const activeNavTab = NAV_TABS.find((t) => t.id === activeTab) ?? NAV_TABS[0]

  return (
    <motion.div className="flex h-full flex-col overflow-hidden" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2, ease: 'easeOut' }}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-accent/50 px-6 py-4">
        <div>
          <h1 className="text-base font-semibold text-primary">Settings</h1>
          <p className="mt-0.5 text-xs text-muted">
            Configure connection, LLM keys, and integration credentials.
            Changes are saved to browser storage and applied to the backend.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-muted">
            <StatusDot />
            <span>
              {endpointStatus === 'checking' ? 'Connecting…' :
                endpointStatus === 'ok' ? 'Backend connected' : 'Backend unreachable'}
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => loadFromBackend(values['_endpoint'] ?? selectedEndpoint)}
            disabled={isLoadingBackend}
            className="h-8 gap-1.5 text-xs"
          >
            <RefreshCw className={cn('size-3.5', isLoadingBackend && 'animate-spin')} />
            Reload
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={isSaving}
            className="h-8 gap-1.5 bg-primary text-xs text-primaryAccent"
          >
            {isSaving ? (
              <RefreshCw className="size-3.5 animate-spin" />
            ) : (
              <Save className="size-3.5" />
            )}
            Save &amp; Apply
          </Button>
        </div>
      </div>

      {/* Status banner */}
      {endpointStatus === 'ok' ? (
        <div className="flex items-center gap-2 border-b border-positive/10 bg-positive/5 px-6 py-2 text-xs text-positive">
          <CheckCircle2 className="size-3.5 shrink-0" />
          Backend connected — values shown reflect current runtime configuration.
          Secrets are masked; enter a new value to override.
        </div>
      ) : endpointStatus === 'error' ? (
        <div className="flex items-center gap-2 border-b border-warning/10 bg-warning/5 px-6 py-2 text-xs text-warning">
          <AlertCircle className="size-3.5 shrink-0" />
          Backend unreachable — settings will be saved locally and applied when connected.
        </div>
      ) : null}

      {/* Body: sidebar + content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left nav */}
        <nav className="flex w-48 shrink-0 flex-col gap-0.5 border-r border-accent/50 p-3 overflow-y-auto">
          {NAV_TABS.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors text-left',
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted hover:bg-accent hover:text-primary'
                )}
              >
                <Icon className={cn('size-3.5 shrink-0', isActive ? 'text-brand' : 'text-muted/60')} />
                {tab.label}
              </button>
            )
          })}
        </nav>

        {/* Content area */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className={cn('mx-auto space-y-4', activeTab === 'agents' ? 'max-w-3xl' : 'max-w-2xl')}>
            {activeTab === 'provider' ? (
              <ModelProviderSection
                endpointUrl={constructEndpointUrl(values['_endpoint'] ?? selectedEndpoint)}
                authToken={values['_authToken'] ?? authToken}
              />
            ) : activeTab === 'agents' ? (
              <AgentSettingsSection
                endpointUrl={constructEndpointUrl(values['_endpoint'] ?? selectedEndpoint)}
                authToken={values['_authToken'] ?? authToken}
              />
            ) : activeTab === 'integrations' ? (
              <>
                {activeNavTab.sections
                  .filter((s) => s.id !== 'mcp_servers')
                  .map((section) => (
                    <Section
                      key={section.id}
                      section={section}
                      values={values}
                      backendValues={backendValues}
                      onChange={handleChange}
                    />
                  ))}
                <MCPStatusSection
                  endpointUrl={constructEndpointUrl(values['_endpoint'] ?? selectedEndpoint)}
                  authToken={values['_authToken'] ?? authToken}
                />
              </>
            ) : (
              activeNavTab.sections.map((section) => (
                <Section
                  key={section.id}
                  section={section}
                  values={values}
                  backendValues={backendValues}
                  onChange={handleChange}
                />
              ))
            )}

            {/* Save button at bottom of content — hidden on Agents tab (panel has its own) */}
            {activeTab !== 'agents' && (
              <div className="flex justify-end pb-4">
                <Button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="gap-1.5 bg-primary text-primaryAccent"
                >
                  {isSaving ? <RefreshCw className="size-4 animate-spin" /> : <Save className="size-4" />}
                  Save &amp; Apply
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
