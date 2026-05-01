'use client'
import { motion } from 'framer-motion'
import { useEffect, useState, useCallback } from 'react'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { Database, RefreshCw, ChevronDown, ChevronUp, Copy, Search, Bot, Users, Zap, Cpu, Tag } from 'lucide-react'
import { toast } from 'sonner'
import type { AgentDetails, TeamDetails, WorkflowDetails } from '@/types/os'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface RegistryEntry {
  id?: string
  name?: string
  type?: string
  provider?: string
  description?: string
  version?: string
  metadata?: Record<string, unknown>
  [key: string]: unknown
}

type TabId = 'all' | 'agents' | 'teams' | 'workflows' | 'registry'

// ---------------------------------------------------------------------------
// Agent Card
// ---------------------------------------------------------------------------
const AgentCard = ({ agent }: { agent: AgentDetails }) => (
  <div className="rounded-xl border border-accent bg-primaryAccent p-4 flex items-start gap-3">
    <div className="mt-0.5 rounded-lg bg-brand/10 p-2 shrink-0">
      <Bot className="size-4 text-brand" />
    </div>
    <div className="flex-1 min-w-0">
      <div className="flex flex-wrap items-center gap-2 mb-1">
        <span className="text-sm font-medium text-primary">{agent.name}</span>
        <span className="rounded-full bg-accent px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted font-mono">{agent.agent_id}</span>
      </div>
      {agent.description && <p className="text-xs text-muted/70 line-clamp-2">{agent.description}</p>}
      <div className="mt-2 flex flex-wrap gap-1.5">
        {agent.model && (
          <span className="flex items-center gap-1 rounded-full border border-accent bg-background px-2 py-0.5 text-[10px] text-muted">
            <Cpu className="size-2.5" />{agent.model.model ?? agent.model.name ?? 'model'}
          </span>
        )}
        {agent.storage && (
          <span className="flex items-center gap-1 rounded-full border border-accent bg-background px-2 py-0.5 text-[10px] text-muted">
            <Database className="size-2.5" />session storage
          </span>
        )}
      </div>
    </div>
  </div>
)

// ---------------------------------------------------------------------------
// Team Card
// ---------------------------------------------------------------------------
const TeamCard = ({ team }: { team: TeamDetails }) => (
  <div className="rounded-xl border border-accent bg-primaryAccent p-4 flex items-start gap-3">
    <div className="mt-0.5 rounded-lg bg-info/10 p-2 shrink-0">
      <Users className="size-4 text-info" />
    </div>
    <div className="flex-1 min-w-0">
      <div className="flex flex-wrap items-center gap-2 mb-1">
        <span className="text-sm font-medium text-primary">{team.name}</span>
        <span className="rounded-full bg-accent px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted font-mono">{team.team_id}</span>
      </div>
      {team.description && <p className="text-xs text-muted/70 line-clamp-2">{team.description}</p>}
      <div className="mt-2 flex flex-wrap gap-1.5">
        {team.model && (
          <span className="flex items-center gap-1 rounded-full border border-accent bg-background px-2 py-0.5 text-[10px] text-muted">
            <Cpu className="size-2.5" />{team.model.model ?? team.model.name ?? 'model'}
          </span>
        )}
        <span className="flex items-center gap-1 rounded-full border border-info/30 bg-info/10 px-2 py-0.5 text-[10px] text-info">
          <Tag className="size-2.5" />coordinate
        </span>
      </div>
    </div>
  </div>
)

// ---------------------------------------------------------------------------
// Workflow Card
// ---------------------------------------------------------------------------
const WorkflowCard = ({ workflow }: { workflow: WorkflowDetails }) => (
  <div className="rounded-xl border border-accent bg-primaryAccent p-4 flex items-start gap-3">
    <div className="mt-0.5 rounded-lg bg-positive/10 p-2 shrink-0">
      <Zap className="size-4 text-positive" />
    </div>
    <div className="flex-1 min-w-0">
      <div className="flex flex-wrap items-center gap-2 mb-1">
        <span className="text-sm font-medium text-primary">{workflow.name}</span>
        <span className="rounded-full bg-accent px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted font-mono">{workflow.id}</span>
      </div>
      {workflow.description && <p className="text-xs text-muted/70 line-clamp-2">{workflow.description}</p>}
    </div>
  </div>
)

// ---------------------------------------------------------------------------
// EntryCard (generic registry items)
// ---------------------------------------------------------------------------
const EntryCard = ({ entry }: { entry: RegistryEntry }) => {
  const [expanded, setExpanded] = useState(false)
  const label = entry.name ?? entry.id ?? 'Entry'
  const copyEntry = () => {
    navigator.clipboard.writeText(JSON.stringify(entry, null, 2))
      .then(() => toast.success('Copied'))
      .catch(() => {})
  }

  return (
    <div className="rounded-xl border border-accent bg-primaryAccent">
      <div className="flex items-start gap-3 p-4">
        <Database className="mt-0.5 size-4 shrink-0 text-brand" />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-primary truncate">{label}</span>
            {entry.type && (
              <span className="rounded-full bg-accent px-2 py-0.5 text-xs text-muted uppercase">{entry.type}</span>
            )}
            {entry.provider && (
              <span className="rounded-full bg-brand/10 px-2 py-0.5 text-xs text-brand">{entry.provider}</span>
            )}
            {entry.version && (
              <span className="rounded-full bg-accent px-2 py-0.5 text-xs text-muted/60">v{entry.version}</span>
            )}
          </div>
          {entry.description && (
            <p className="mt-1 text-xs text-muted/70 truncate">{entry.description}</p>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button onClick={copyEntry} className="rounded-lg p-1.5 text-muted hover:bg-accent hover:text-primary" title="Copy JSON">
            <Copy className="size-3.5" />
          </button>
          <button onClick={() => setExpanded(!expanded)} className="rounded-lg p-1.5 text-muted hover:bg-accent hover:text-primary">
            {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          </button>
        </div>
      </div>
      {expanded && (
        <div className="border-t border-accent px-4 pb-4 pt-3">
          <pre className="max-h-80 overflow-y-auto rounded-xl bg-background p-3 text-xs text-primary whitespace-pre-wrap">
            {JSON.stringify(entry, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section header
// ---------------------------------------------------------------------------
const SectionHeader = ({ icon, label, count, color }: { icon: React.ReactNode; label: string; count: number; color: string }) => (
  <div className="flex items-center gap-2">
    <div className="rounded-lg p-1.5" style={{ background: `${color}18` }}>{icon}</div>
    <span className="text-sm font-medium text-primary">{label}</span>
    <span className="rounded-full bg-accent px-2 py-0.5 text-[10px] text-muted ml-1">{count}</span>
  </div>
)

// ---------------------------------------------------------------------------
// RegistryPage
// ---------------------------------------------------------------------------
export default function RegistryPage() {
  const { selectedEndpoint, authToken } = useStore()
  const [agents, setAgents]     = useState<AgentDetails[]>([])
  const [teams, setTeams]       = useState<TeamDetails[]>([])
  const [workflows, setWorkflows] = useState<WorkflowDetails[]>([])
  const [entries, setEntries]   = useState<RegistryEntry[]>([])
  const [loading, setLoading]   = useState(false)
  const [search, setSearch]     = useState('')
  const [activeTab, setActiveTab] = useState<TabId>('all')

  const headers: Record<string, string> = authToken ? { Authorization: `Bearer ${authToken}` } : {}

  const fetchAll = useCallback(async () => {
    if (!selectedEndpoint) return
    setLoading(true)
    try {
      const [agentsRes, teamsRes, workflowsRes, regRes] = await Promise.all([
        fetch(APIRoutes.GetAgents(selectedEndpoint), { headers }).catch(() => null),
        fetch(APIRoutes.GetTeams(selectedEndpoint), { headers }).catch(() => null),
        fetch(APIRoutes.GetWorkflows(selectedEndpoint), { headers }).catch(() => null),
        fetch(APIRoutes.Registry(selectedEndpoint), { headers }).catch(() => null),
      ])

      if (agentsRes?.ok) {
        const d = await agentsRes.json()
        setAgents(Array.isArray(d) ? d : d?.agents ?? d?.data ?? [])
      }
      if (teamsRes?.ok) {
        const d = await teamsRes.json()
        setTeams(Array.isArray(d) ? d : d?.teams ?? d?.data ?? [])
      }
      if (workflowsRes?.ok) {
        const d = await workflowsRes.json()
        setWorkflows(Array.isArray(d) ? d : d?.workflows ?? d?.data ?? [])
      }
      if (regRes?.ok) {
        const d = await regRes.json()
        if (Array.isArray(d)) {
          setEntries(d)
        } else if (d && typeof d === 'object') {
          const flat: RegistryEntry[] = []
          for (const [key, val] of Object.entries(d)) {
            if (Array.isArray(val)) {
              val.forEach((item) => flat.push({ ...item, type: item.type ?? key }))
            } else if (val && typeof val === 'object') {
              flat.push({ ...val as RegistryEntry, type: (val as RegistryEntry).type ?? key })
            }
          }
          setEntries(flat)
        }
      }
    } catch { /* silent */ }
    finally { setLoading(false) }
  }, [selectedEndpoint, authToken]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetchAll() }, [fetchAll])

  const q = search.toLowerCase()
  const filterItems = <T extends { id?: string; name?: string; agent_id?: string; team_id?: string }>(list: T[]) =>
    q ? list.filter((x) => (x.name ?? '').toLowerCase().includes(q) || (x.id ?? '').toLowerCase().includes(q) || (x.agent_id ?? '').toLowerCase().includes(q) || (x.team_id ?? '').toLowerCase().includes(q)) : list

  const filteredAgents    = filterItems(agents)
  const filteredTeams     = filterItems(teams)
  const filteredWorkflows = filterItems(workflows)
  const filteredEntries   = search ? entries.filter((e) => [(e.name ?? ''), (e.id ?? ''), (e.type ?? ''), (e.provider ?? '')].some((s) => s.toLowerCase().includes(q))) : entries

  const TABS: { id: TabId; label: string; count: number }[] = [
    { id: 'all',       label: 'All',       count: agents.length + teams.length + workflows.length + entries.length },
    { id: 'agents',    label: 'Agents',    count: agents.length },
    { id: 'teams',     label: 'Teams',     count: teams.length },
    { id: 'workflows', label: 'Workflows', count: workflows.length },
    { id: 'registry',  label: 'Registry',  count: entries.length },
  ]

  const showAgents    = activeTab === 'all' || activeTab === 'agents'
  const showTeams     = activeTab === 'all' || activeTab === 'teams'
  const showWorkflows = activeTab === 'all' || activeTab === 'workflows'
  const showRegistry  = activeTab === 'all' || activeTab === 'registry'

  return (
    <motion.div className="h-full overflow-y-auto p-6" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2, ease: 'easeOut' }}>
      <div className="mx-auto max-w-4xl space-y-6">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-medium text-primary">
              <Database className="size-5 text-brand" />Registry
            </h1>
            <p className="mt-1 text-xs text-muted">All registered agents, teams, workflows, and runtime resources</p>
          </div>
          <Button size="sm" variant="outline" onClick={fetchAll} disabled={loading} className="gap-1.5">
            <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />Refresh
          </Button>
        </div>

        {/* Summary pills */}
        {!loading && (agents.length + teams.length + workflows.length + entries.length) > 0 && (
          <div className="flex flex-wrap gap-2">
            <div className="flex items-center gap-1.5 rounded-lg border border-brand/30 bg-brand/10 px-3 py-1.5">
              <Bot className="size-3.5 text-brand" />
              <span className="text-xs text-brand font-medium">{agents.length} Agent{agents.length !== 1 ? 's' : ''}</span>
            </div>
            <div className="flex items-center gap-1.5 rounded-lg border border-info/30 bg-info/10 px-3 py-1.5">
              <Users className="size-3.5 text-info" />
              <span className="text-xs text-info font-medium">{teams.length} Team{teams.length !== 1 ? 's' : ''}</span>
            </div>
            <div className="flex items-center gap-1.5 rounded-lg border border-positive/30 bg-positive/10 px-3 py-1.5">
              <Zap className="size-3.5 text-positive" />
              <span className="text-xs text-positive font-medium">{workflows.length} Workflow{workflows.length !== 1 ? 's' : ''}</span>
            </div>
            {entries.length > 0 && (
              <div className="flex items-center gap-1.5 rounded-lg border border-accent bg-accent/30 px-3 py-1.5">
                <Database className="size-3.5 text-muted" />
                <span className="text-xs text-muted font-medium">{entries.length} Registry item{entries.length !== 1 ? 's' : ''}</span>
              </div>
            )}
          </div>
        )}

        {/* Tab bar + search */}
        <div className="space-y-2">
          <div className="flex gap-1 rounded-xl border border-accent bg-primaryAccent p-1 overflow-x-auto">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={cn(
                  'shrink-0 flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
                  activeTab === t.id ? 'bg-accent text-primary' : 'text-muted hover:text-primary'
                )}
              >
                {t.label}
                <span className={cn('rounded-full px-1.5 py-0.5 text-[10px]', activeTab === t.id ? 'bg-background text-primary' : 'bg-accent/50 text-muted/70')}>{t.count}</span>
              </button>
            ))}
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name or ID…"
              className="w-full rounded-xl border border-accent bg-primaryAccent pl-8 pr-3 py-2 text-xs text-primary outline-none focus:border-primary/30"
            />
          </div>
        </div>

        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
          </div>
        ) : (
          <div className="space-y-8">

            {/* Agents */}
            {showAgents && filteredAgents.length > 0 && (
              <section className="space-y-3">
                <SectionHeader icon={<Bot className="size-4 text-brand" />} label="Agents" count={filteredAgents.length} color="#FF4017" />
                <div className="grid gap-3 sm:grid-cols-2">
                  {filteredAgents.map((a) => <AgentCard key={a.agent_id} agent={a} />)}
                </div>
              </section>
            )}

            {/* Teams */}
            {showTeams && filteredTeams.length > 0 && (
              <section className="space-y-3">
                <SectionHeader icon={<Users className="size-4 text-info" />} label="Teams" count={filteredTeams.length} color="#3B82F6" />
                <div className="grid gap-3 sm:grid-cols-2">
                  {filteredTeams.map((t) => <TeamCard key={t.team_id} team={t} />)}
                </div>
              </section>
            )}

            {/* Workflows */}
            {showWorkflows && filteredWorkflows.length > 0 && (
              <section className="space-y-3">
                <SectionHeader icon={<Zap className="size-4 text-positive" />} label="Workflows" count={filteredWorkflows.length} color="#22C55E" />
                <div className="grid gap-3 sm:grid-cols-2">
                  {filteredWorkflows.map((w) => <WorkflowCard key={w.id} workflow={w} />)}
                </div>
              </section>
            )}

            {/* Registry */}
            {showRegistry && filteredEntries.length > 0 && (
              <section className="space-y-3">
                <SectionHeader icon={<Database className="size-4 text-muted" />} label="Registry" count={filteredEntries.length} color="#71717A" />
                <div className="space-y-3">
                  {filteredEntries.map((entry, i) => <EntryCard key={entry.id ?? entry.name ?? i} entry={entry} />)}
                </div>
              </section>
            )}

            {/* Empty state */}
            {!loading && filteredAgents.length === 0 && filteredTeams.length === 0 && filteredWorkflows.length === 0 && filteredEntries.length === 0 && (
              <div className="flex flex-col items-center justify-center rounded-xl border border-accent bg-primaryAccent py-16 text-center">
                <Database className="size-10 text-muted/20" />
                <p className="mt-3 text-sm font-medium text-muted">{search ? 'No results' : 'Registry is empty'}</p>
                <p className="mt-1 text-xs text-muted/60">
                  {search ? 'Try a different search term.' : 'Items are registered automatically when AgentOS starts.'}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}
