'use client'
import { useState, useEffect, useCallback } from 'react'
import { useStore, AgentConfigOverride } from '@/store'
import { constructEndpointUrl } from '@/lib/constructEndpointUrl'
import { APIRoutes } from '@/api/routes'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'
import {
  Bot, Cpu, MessageSquare, Settings, ChevronDown, ChevronRight,
  RefreshCw, Save, RotateCcw, ToggleLeft, ToggleRight, Info, Brain, Trash2
} from 'lucide-react'
import dayjs from 'dayjs'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AgentConfigSnapshot {
  id: string
  name: string
  instructions: string
  model: { id?: string; name?: string; provider?: string; base_url?: string }
  num_history_runs: number
  add_history_to_context: boolean
  session_state: Record<string, unknown>
  add_session_state_to_context: boolean
  enable_agentic_state: boolean
  enable_agentic_memory: boolean
  update_memory_on_run: boolean
  metadata: Record<string, unknown>
}

interface ProviderModel { id: string; label: string }
interface ProviderInfo { name: string; models: ProviderModel[]; default_model: string }
interface ProvidersResp { providers: Record<string, ProviderInfo>; active_provider: string; active_model: string }

interface UserMemory {
  id: string
  memory?: string
  summary?: string
  topics?: string[]
  user_id?: string
  created_at?: string
  updated_at?: string
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const Toggle = ({ value, onChange, disabled }: { value: boolean; onChange: (v: boolean) => void; disabled?: boolean }) => (
  <button
    type="button"
    onClick={() => !disabled && onChange(!value)}
    className={cn(
      'flex h-5 w-9 items-center rounded-full border transition-colors',
      value ? 'border-brand bg-brand/20' : 'border-primary/20 bg-accent',
      disabled && 'opacity-40 cursor-not-allowed'
    )}
  >
    <span className={cn(
      'mx-0.5 size-3.5 rounded-full transition-transform',
      value ? 'translate-x-4 bg-brand' : 'translate-x-0 bg-muted'
    )} />
  </button>
)

const ToggleRow = ({ label, desc, value, onChange }: {
  label: string; desc?: string; value: boolean; onChange: (v: boolean) => void
}) => (
  <div className="flex items-center justify-between gap-3">
    <div>
      <div className="text-xs font-medium text-primary">{label}</div>
      {desc && <div className="text-[10px] text-muted/50">{desc}</div>}
    </div>
    <Toggle value={value} onChange={onChange} />
  </div>
)

const SectionHeader = ({ title, open, onToggle }: { title: string; open: boolean; onToggle: () => void }) => (
  <button
    onClick={onToggle}
    className="flex w-full items-center justify-between py-2 text-xs font-semibold uppercase tracking-wide text-muted hover:text-primary"
  >
    {title}
    {open ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
  </button>
)

const Label = ({ children, optional }: { children: React.ReactNode; optional?: boolean }) => (
  <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-muted/70">
    {children}
    {optional && <span className="ml-1 normal-case font-normal text-muted/40">optional</span>}
  </label>
)

const Input = ({ value, onChange, placeholder, className }: {
  value: string; onChange: (v: string) => void; placeholder?: string; className?: string
}) => (
  <input
    type="text"
    value={value}
    onChange={(e) => onChange(e.target.value)}
    placeholder={placeholder}
    className={cn(
      'w-full rounded-xl border border-primary/15 bg-accent px-3 py-2 text-xs text-primary outline-none placeholder:text-muted/40 focus:border-primary/40',
      className
    )}
  />
)

const Textarea = ({ value, onChange, placeholder, rows = 3 }: {
  value: string; onChange: (v: string) => void; placeholder?: string; rows?: number
}) => (
  <textarea
    rows={rows}
    value={value}
    onChange={(e) => onChange(e.target.value)}
    placeholder={placeholder}
    className="w-full rounded-xl border border-primary/15 bg-accent px-3 py-2 text-xs text-primary outline-none placeholder:text-muted/40 focus:border-primary/40 resize-none font-mono"
  />
)

const JsonArea = ({ value, onChange, placeholder }: {
  value: string; onChange: (v: string) => void; placeholder?: string
}) => {
  const [err, setErr] = useState(false)

  const handleChange = (raw: string) => {
    onChange(raw)
    try { if (raw.trim()) JSON.parse(raw); setErr(false) } catch { setErr(true) }
  }

  return (
    <div>
      <textarea
        rows={4}
        value={value}
        onChange={(e) => handleChange(e.target.value)}
        placeholder={placeholder ?? '{}'}
        className={cn(
          'w-full rounded-xl border px-3 py-2 text-xs text-primary outline-none resize-none font-mono bg-accent placeholder:text-muted/40',
          err ? 'border-destructive/50 focus:border-destructive' : 'border-primary/15 focus:border-primary/40'
        )}
      />
      {err && <p className="mt-0.5 text-[10px] text-destructive">Invalid JSON</p>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Team metadata
// ---------------------------------------------------------------------------
const TEAM_META: Record<string, { purpose: string; responsibility: string; outputContract: string }> = {
  'strategy': {
    purpose: 'Spec Writing Squad — bridges Business Analysts and the Technical team.',
    responsibility: 'Parse Jira tickets into structured RequirementContext (Architect), then author BDD Gherkin specs with full traceability to every acceptance criterion (Scribe).',
    outputContract: 'RequirementContext → GherkinSpec',
  },
  'context': {
    purpose: 'Discovery & Indexing Squad — maintain the Digital Twin of your AUT and codebase.',
    responsibility: 'Crawl the AUT to generate the Site Manifesto with Accessibility Tree snapshots (Discovery), re-index Page Objects and Step Definitions into PgVector on every Git commit (Librarian).',
    outputContract: 'SiteManifesto + PgVector Automation KB',
  },
  'engineering': {
    purpose: 'Code Generation Squad — generate production-grade Playwright automation code.',
    responsibility: 'Write modular POMs and Step Definitions using the Look-Before-You-Leap pattern (Engineer), provision fresh test data with PII masking and cleanup queries (Data Agent), submit GitHub PRs.',
    outputContract: 'RunContext → POM + StepDefs → GitHub PR',
  },
  'operations': {
    purpose: 'Self-Healing Squad — keep the regression suite green autonomously.',
    responsibility: 'Classify failures from trace.zip as LOCATOR_STALE / LOGIC_CHANGE / DATA_MISMATCH / ENV_FAILURE (Detective), apply surgical one-locator healing patches verified 3× (Medic).',
    outputContract: 'RCAReport → HealingPatch (verified 3×)',
  },
  'diagnostics': {
    purpose: 'CI Failure Squad — correlate pipeline logs with Playwright traces.',
    responsibility: 'Analyse GitHub Actions / ADO pipeline failures with log-level detail (CI Log Analyzer), cross-reference with Playwright trace analysis (Detective), create Jira/ADO tickets after HITL approval.',
    outputContract: 'PipelineRCAReport + RCAReport → ADO ticket (HITL)',
  },
  'grooming_team': {
    purpose: 'Backlog Grooming Squad — collaborative backlog refinement from three perspectives.',
    responsibility: 'BA perspective on testability (Architect), SDET assessment of automation feasibility and edge cases (Impact Analyst), combined into actionable grooming assessment posted to Jira.',
    outputContract: 'GroomingAssessment → Jira comment',
  },
  'intelligence': {
    purpose: 'Impact Analysis Squad — answers “what needs to change?” and “why did this fail?”',
    responsibility: 'Analyse PRs and Issues to identify missing/obsolete/stale tests and compute regression risk (Impact Analyst), analyse CI pipeline failures and produce remediation plans (Pipeline Analyst).',
    outputContract: 'ImpactReport + PipelineRCAReport',
  },
}

// ---------------------------------------------------------------------------
// Main AgentConfigPanel
// ---------------------------------------------------------------------------

export default function AgentConfigPanel({
  entityId,
  entityType,
}: {
  entityId: string
  entityType: 'agent' | 'team'
}) {
  const { selectedEndpoint, authToken, agentOverrides, setAgentOverride, clearAgentOverride } = useStore()
  const endpointUrl = constructEndpointUrl(selectedEndpoint)
  const headers: HeadersInit = authToken ? { Authorization: `Bearer ${authToken}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' }

  // Server snapshot (live agent state)
  const [snapshot, setSnapshot] = useState<AgentConfigSnapshot | null>(null)
  const [providers, setProviders] = useState<ProvidersResp | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  // Local form state — merges server snapshot + any persisted overrides
  const [name, setName] = useState('')
  const [instructions, setInstructions] = useState('')
  const [selectedProvider, setSelectedProvider] = useState('')
  const [selectedModel, setSelectedModelLocal] = useState('')
  const [numHistoryRuns, setNumHistoryRuns] = useState('5')
  const [addHistoryCtx, setAddHistoryCtx] = useState(true)
  const [sessionStateStr, setSessionStateStr] = useState('{}')
  const [addSessionStateCtx, setAddSessionStateCtx] = useState(false)
  const [enableAgenticState, setEnableAgenticState] = useState(false)
  const [enableAgenticMemory, setEnableAgenticMemory] = useState(true)
  const [updateMemoryOnRun, setUpdateMemoryOnRun] = useState(false)
  const [metadataStr, setMetadataStr] = useState('{}')
  const [extraConfigStr, setExtraConfigStr] = useState('')

  // Collapsible sections
  const [openBasics, setOpenBasics] = useState(true)
  const [openContext, setOpenContext] = useState(true)
  const [openSession, setOpenSession] = useState(false)
  const [openMemory, setOpenMemory] = useState(false)
  const [openUserMemory, setOpenUserMemory] = useState(false)
  const [openAdvanced, setOpenAdvanced] = useState(false)

  // User memory records
  const [userMemories, setUserMemories] = useState<UserMemory[]>([])
  const [loadingMemories, setLoadingMemories] = useState(false)

  // ---------------------------------------------------------------------------
  // Load
  // ---------------------------------------------------------------------------

  const loadSnapshot = useCallback(async () => {
    setLoading(true)
    try {
      const url = entityType === 'agent'
        ? APIRoutes.GetAgentConfig(endpointUrl, entityId)
        : APIRoutes.GetTeamConfig(endpointUrl, entityId)

      const res = await fetch(url, { headers })
      if (res.ok) {
        const data: AgentConfigSnapshot = await res.json()
        setSnapshot(data)

        // Merge with any persisted local overrides
        const saved = agentOverrides[entityId]

        setName(saved?.name ?? data.name ?? '')
        setInstructions(saved?.instructions ?? (typeof data.instructions === 'string' ? data.instructions : '') ?? '')
        setSelectedProvider(saved?.model_provider ?? data.model?.provider ?? 'kilo')
        setSelectedModelLocal(saved?.model_id ?? data.model?.id ?? '')
        setNumHistoryRuns(String(saved?.num_history_runs ?? data.num_history_runs ?? 5))
        setAddHistoryCtx(saved?.add_history_to_context ?? data.add_history_to_context ?? true)
        setSessionStateStr(JSON.stringify(saved?.session_state ?? data.session_state ?? {}, null, 2))
        setAddSessionStateCtx(saved?.add_session_state_to_context ?? data.add_session_state_to_context ?? false)
        setEnableAgenticState(saved?.enable_agentic_state ?? data.enable_agentic_state ?? false)
        setEnableAgenticMemory(saved?.enable_agentic_memory ?? data.enable_agentic_memory ?? true)
        setUpdateMemoryOnRun(saved?.update_memory_on_run ?? data.update_memory_on_run ?? false)
        setMetadataStr(JSON.stringify(saved?.metadata ?? data.metadata ?? {}, null, 2))
      }
    } catch { /* backend may not have this endpoint yet */ }
    setLoading(false)
  }, [entityId, entityType, endpointUrl])  // eslint-disable-line react-hooks/exhaustive-deps

  const loadProviders = useCallback(async () => {
    try {
      const res = await fetch(`${endpointUrl}/model/providers`, { headers: authToken ? { Authorization: `Bearer ${authToken}` } : {} })
      if (res.ok) setProviders(await res.json())
    } catch { /* ok */ }
  }, [endpointUrl, authToken])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    loadSnapshot()
    loadProviders()
  }, [entityId])  // eslint-disable-line react-hooks/exhaustive-deps

  // ---------------------------------------------------------------------------
  // Save — persists to backend + local store
  // ---------------------------------------------------------------------------

  const handleSave = async () => {
    let sessionStateParsed: Record<string, unknown> = {}
    let metadataParsed: Record<string, unknown> = {}
    let extraConfigParsed: Record<string, unknown> | undefined

    try { if (sessionStateStr.trim()) sessionStateParsed = JSON.parse(sessionStateStr) } catch { toast.error('Session State is not valid JSON'); return }
    try { if (metadataStr.trim()) metadataParsed = JSON.parse(metadataStr) } catch { toast.error('Metadata is not valid JSON'); return }
    if (extraConfigStr.trim()) {
      try { extraConfigParsed = JSON.parse(extraConfigStr) } catch { toast.error('Config JSON is not valid JSON'); return }
    }

    const currentProvider = providers?.providers?.[selectedProvider]
    const baseUrl = currentProvider
      ? (currentProvider as unknown as { base_url?: string }).base_url ?? ''
      : ''

    const payload: AgentConfigOverride = {
      name: name || undefined,
      instructions: instructions || undefined,
      model_id: selectedModel || undefined,
      model_provider: selectedProvider || undefined,
      model_base_url: baseUrl || undefined,
      num_history_runs: parseInt(numHistoryRuns) || undefined,
      add_history_to_context: addHistoryCtx,
      session_state: sessionStateParsed,
      add_session_state_to_context: addSessionStateCtx,
      enable_agentic_state: enableAgenticState,
      enable_agentic_memory: enableAgenticMemory,
      update_memory_on_run: updateMemoryOnRun,
      metadata: metadataParsed,
      extra_config: extraConfigParsed,
    }

    // 1. Persist to local store (so overrides survive page navigation)
    setAgentOverride(entityId, payload)

    // 2. Push to backend
    setSaving(true)
    try {
      const url = entityType === 'agent'
        ? APIRoutes.PatchAgentConfig(endpointUrl, entityId)
        : APIRoutes.PatchTeamConfig(endpointUrl, entityId)

      const res = await fetch(url, {
        method: 'PATCH',
        headers,
        body: JSON.stringify(payload),
      })

      if (res.ok) {
        const data = await res.json()
        toast.success(`Config saved — ${data.changed_fields?.length ?? 0} field(s) updated`)
        // Refresh snapshot
        await loadSnapshot()
      } else {
        toast.warning('Saved locally — backend returned an error. Changes will apply on next run.')
      }
    } catch {
      toast.warning('Saved locally — backend unreachable. Changes will apply on next run.')
    }
    setSaving(false)
  }

  const handleReset = async () => {
    clearAgentOverride(entityId)
    await loadSnapshot()
    toast.success('Config reset to server defaults')
  }

  const loadUserMemories = useCallback(async () => {
    if (!endpointUrl || entityType !== 'agent') return
    setLoadingMemories(true)
    try {
      const res = await fetch(APIRoutes.GetAgentMemories(endpointUrl, entityId), { headers })
      if (res.ok) {
        const data = await res.json()
        setUserMemories(data?.data ?? [])
      }
    } catch { /* offline */ }
    finally { setLoadingMemories(false) }
  }, [entityId, entityType, endpointUrl])  // eslint-disable-line react-hooks/exhaustive-deps

  const handleDeleteMemory = async (memId: string) => {
    try {
      const res = await fetch(APIRoutes.GetMemory(endpointUrl, memId), { method: 'DELETE', headers })
      if (res.ok) {
        setUserMemories((prev) => prev.filter((m) => m.id !== memId))
        toast.success('Memory deleted')
      } else {
        toast.error('Delete failed')
      }
    } catch { toast.error('Delete failed') }
  }

  useEffect(() => {
    if (openUserMemory) loadUserMemories()
  }, [openUserMemory])  // eslint-disable-line react-hooks/exhaustive-deps

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const hasOverride = !!agentOverrides[entityId]

  const teamMeta = entityType === 'team' ? TEAM_META[entityId] : undefined

  if (loading) {
    return (
      <div className="space-y-2 p-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-8 rounded-xl bg-accent/60 animate-pulse" />
        ))}
      </div>
    )
  }

  const providerOptions = providers ? Object.entries(providers.providers) : []
  const modelOptions = providers?.providers?.[selectedProvider]?.models ?? []

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-accent/50 px-3 py-2.5 shrink-0">
        <div className="flex items-center gap-2">
          <Bot className="size-3.5 text-brand" />
          <span className="text-xs font-semibold text-primary">
            {name || entityId} Config
          </span>
          {hasOverride && (
            <span className="rounded-full bg-warning/15 px-1.5 py-0.5 text-[9px] font-medium text-warning">
              Modified
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => { loadSnapshot(); loadProviders() }}
            title="Reload from server"
            className="rounded-lg p-1 text-muted hover:bg-accent hover:text-primary"
          >
            <RefreshCw className="size-3.5" />
          </button>
          {hasOverride && (
            <button
              onClick={handleReset}
              title="Reset to server defaults"
              className="rounded-lg p-1 text-muted hover:bg-accent hover:text-destructive"
            >
              <RotateCcw className="size-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Scrollable form */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-0">

        {/* ── TEAM PURPOSE BANNER ── */}
        {entityType === 'team' && teamMeta && (
          <div className="mb-3 rounded-xl border border-info/20 bg-info/5 p-3 space-y-2">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-info/70 mb-0.5">Purpose</p>
              <p className="text-xs text-primary leading-relaxed">{teamMeta.purpose}</p>
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-info/70 mb-0.5">Responsibility</p>
              <p className="text-xs text-muted/80 leading-relaxed">{teamMeta.responsibility}</p>
            </div>
            <div className="flex items-center gap-2 pt-0.5">
              <span className="text-[9px] font-semibold uppercase text-info/50">Output</span>
              <span className="rounded-full bg-info/10 border border-info/20 px-2 py-0.5 text-[10px] font-mono text-info">{teamMeta.outputContract}</span>
            </div>
          </div>
        )}

        {/* ── BASICS ── */}
        <div className="border-b border-accent/30 pb-2">
          <SectionHeader title="Basics" open={openBasics} onToggle={() => setOpenBasics(o => !o)} />
          {openBasics && (
            <div className="space-y-3 pt-1 pb-2">
              <p className="text-[10px] text-muted/50">
                {entityType === 'team'
                  ? 'Configure the leader instructions and coordination behaviour of this team.'
                  : 'Configure the core identity and behaviour of this agent.'}
              </p>

              <div>
                <Label>{entityType === 'team' ? 'Team Name' : 'Agent Name'}</Label>
                <Input value={name} onChange={setName} placeholder={entityType === 'team' ? 'Enter team name' : 'Enter agent name'} />
              </div>

              <div>
                <Label>Model</Label>
                <div className="flex gap-1.5">
                  <select
                    value={selectedProvider}
                    onChange={(e) => {
                      setSelectedProvider(e.target.value)
                      setSelectedModelLocal(providers?.providers?.[e.target.value]?.default_model ?? '')
                    }}
                    className="flex-1 rounded-xl border border-primary/15 bg-accent px-2 py-2 text-xs text-primary outline-none focus:border-primary/40"
                  >
                    {providerOptions.length === 0 && (
                      <option value="">Loading…</option>
                    )}
                    {providerOptions.map(([pid, pInfo]) => (
                      <option key={pid} value={pid}>{pInfo.name}</option>
                    ))}
                  </select>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModelLocal(e.target.value)}
                    className="flex-1 rounded-xl border border-primary/15 bg-accent px-2 py-2 text-xs text-primary outline-none focus:border-primary/40"
                  >
                    {modelOptions.length === 0 && (
                      <option value={snapshot?.model?.id ?? ''}>{snapshot?.model?.id ?? 'No models'}</option>
                    )}
                    {modelOptions.map((m) => (
                      <option key={m.id} value={m.id}>{m.label}</option>
                    ))}
                  </select>
                </div>
                {snapshot?.model && (
                  <p className="mt-0.5 text-[10px] text-muted/40">
                    Current: <span className="font-mono">{snapshot.model.id}</span>
                    {snapshot.model.provider && <span> ({snapshot.model.provider})</span>}
                  </p>
                )}
              </div>

              <div>
                <Label optional>{entityType === 'team' ? 'Leader Instructions (System Prompt)' : 'Instructions'}</Label>
                <Textarea
                  value={instructions}
                  onChange={setInstructions}
                  placeholder={entityType === 'team' ? 'Enter leader instructions that guide how this team coordinates its members…' : 'Enter instructions…'}
                  rows={5}
                />
              </div>
            </div>
          )}
        </div>

        {/* ── CONTEXT MANAGEMENT ── */}
        <div className="border-b border-accent/30 pb-2">
          <SectionHeader title="Context Management" open={openContext} onToggle={() => setOpenContext(o => !o)} />
          {openContext && (
            <div className="space-y-3 pt-1 pb-2">
              <p className="text-[10px] text-muted/50">Control the information sent to language models.</p>

              <div>
                <Label optional>Number of History Runs</Label>
                <Input
                  value={numHistoryRuns}
                  onChange={setNumHistoryRuns}
                  placeholder="e.g., 3"
                />
                <p className="mt-0.5 text-[10px] text-muted/40">Number of historical runs to include in messages.</p>
              </div>

              <ToggleRow
                label="Add History to Context"
                value={addHistoryCtx}
                onChange={setAddHistoryCtx}
              />
            </div>
          )}
        </div>

        {/* ── SESSION STATE ── */}
        <div className="border-b border-accent/30 pb-2">
          <SectionHeader title="Session State" open={openSession} onToggle={() => setOpenSession(o => !o)} />
          {openSession && (
            <div className="space-y-3 pt-1 pb-2">
              <div>
                <Label>Session State</Label>
                <JsonArea value={sessionStateStr} onChange={setSessionStateStr} placeholder="{}" />
              </div>

              <ToggleRow
                label="Add Session State to Context"
                value={addSessionStateCtx}
                onChange={setAddSessionStateCtx}
              />

              <ToggleRow
                label="Enable Agentic State"
                value={enableAgenticState}
                onChange={setEnableAgenticState}
              />
            </div>
          )}
        </div>

        {/* ── AGENT MEMORY ── */}
        <div className="border-b border-accent/30 pb-2">
          <SectionHeader title="Agent Memory" open={openMemory} onToggle={() => setOpenMemory(o => !o)} />
          {openMemory && (
            <div className="space-y-3 pt-1 pb-2">
              <p className="text-[10px] text-muted/50">Long-term user memory management.</p>

              <ToggleRow
                label="Enable Agentic Memory"
                value={enableAgenticMemory}
                onChange={setEnableAgenticMemory}
              />

              <div className="flex items-center gap-1.5 text-[10px] text-muted/40">
                <Info className="size-3 shrink-0" /> OR
              </div>

              <ToggleRow
                label="Update Memory on Run"
                value={updateMemoryOnRun}
                onChange={setUpdateMemoryOnRun}
              />
            </div>
          )}
        </div>

        {/* ── USER MEMORY ── */}
        {entityType === 'agent' && (
          <div className="border-b border-accent/30 pb-2">
            <SectionHeader title="User Memory" open={openUserMemory} onToggle={() => setOpenUserMemory(o => !o)} />
            {openUserMemory && (
              <div className="pt-1 pb-2">
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-[10px] text-muted/50">Memories stored by this agent across sessions.</p>
                  <button
                    onClick={loadUserMemories}
                    title="Refresh"
                    className="rounded-lg p-1 text-muted hover:bg-accent hover:text-primary"
                  >
                    <RefreshCw className={cn('size-3', loadingMemories && 'animate-spin')} />
                  </button>
                </div>
                {loadingMemories ? (
                  <div className="space-y-1.5">
                    {[...Array(3)].map((_, i) => (
                      <div key={i} className="h-8 rounded-xl bg-accent/60 animate-pulse" />
                    ))}
                  </div>
                ) : userMemories.length === 0 ? (
                  <div className="flex flex-col items-center justify-center rounded-xl border border-accent bg-accent/10 py-4 text-center">
                    <Brain className="size-5 text-muted/20" />
                    <p className="mt-1 text-[10px] text-muted/40">No memories yet</p>
                  </div>
                ) : (
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {userMemories.map((mem) => (
                      <div key={mem.id} className="flex items-start gap-2 rounded-xl border border-accent bg-accent/10 px-2.5 py-2">
                        <Brain className="mt-0.5 size-3 shrink-0 text-brand" />
                        <div className="flex-1 min-w-0">
                          <p className="text-[10px] text-primary line-clamp-2 leading-relaxed">{mem.memory || mem.summary || ''}</p>
                          {mem.updated_at && (
                            <p className="mt-0.5 text-[9px] text-muted/40 font-mono">{dayjs(mem.updated_at).format('MMM D, HH:mm')}</p>
                          )}
                          {mem.topics && mem.topics.length > 0 && (
                            <div className="mt-1 flex flex-wrap gap-1">
                              {mem.topics.slice(0, 3).map((t) => (
                                <span key={t} className="rounded-full bg-accent px-1.5 py-0.5 text-[9px] text-muted">{t}</span>
                              ))}
                            </div>
                          )}
                        </div>
                        <button
                          onClick={() => handleDeleteMemory(mem.id)}
                          className="shrink-0 rounded-lg p-0.5 text-muted hover:bg-destructive/10 hover:text-destructive"
                        >
                          <Trash2 className="size-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                {userMemories.length > 0 && (
                  <p className="mt-1.5 text-center text-[9px] text-muted/30">{userMemories.length} memor{userMemories.length === 1 ? 'y' : 'ies'}</p>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── ADVANCED ── */}
        <div className="pb-2">
          <SectionHeader title="Advanced" open={openAdvanced} onToggle={() => setOpenAdvanced(o => !o)} />
          {openAdvanced && (
            <div className="space-y-3 pt-1 pb-2">
              <div>
                <Label optional>Agent ID</Label>
                <Input
                  value={snapshot?.id ?? entityId}
                  onChange={() => { }}
                  placeholder="Auto-generated if not provided"
                  className="opacity-60 cursor-not-allowed"
                />
                <p className="mt-0.5 text-[10px] text-muted/40">Read-only — set at agent construction.</p>
              </div>

              <div>
                <Label>Metadata</Label>
                <JsonArea value={metadataStr} onChange={setMetadataStr} placeholder="{}" />
              </div>

              <div>
                <Label optional>Config JSON</Label>
                <JsonArea
                  value={extraConfigStr}
                  onChange={setExtraConfigStr}
                  placeholder='{"cache_session": true, "enable_user_memories": true}'
                />
                <p className="mt-0.5 text-[10px] text-muted/40">
                  Pass any additional advanced configuration. These are applied as direct attribute overrides.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Save / Reset footer */}
      <div className="border-t border-accent/50 px-3 py-2.5 shrink-0">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl bg-primary py-2 text-xs font-medium text-primaryAccent transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {saving ? <RefreshCw className="size-3.5 animate-spin" /> : <Save className="size-3.5" />}
          {saving ? 'Saving…' : 'Save & Apply'}
        </button>
        {hasOverride && (
          <p className="mt-1.5 text-center text-[10px] text-muted/50">
            Local overrides active — <button onClick={handleReset} className="text-muted hover:text-primary underline">reset to defaults</button>
          </p>
        )}
      </div>
    </div>
  )
}
