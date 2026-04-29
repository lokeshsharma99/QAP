'use client'
import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { useStore } from '@/store'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import {
  Activity, ExternalLink, Bot, Users,
  ShieldCheck, Zap, MessageSquare, Wrench, BarChart2, RefreshCw,
  AlertCircle, ChevronRight, BookOpen, FlaskConical
} from 'lucide-react'
import { APIRoutes } from '@/api/routes'
import { constructEndpointUrl } from '@/lib/constructEndpointUrl'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

// ─── Recent Traces ────────────────────────────────────────────────────────────

interface TraceSummary {
  trace_id: string
  name: string
  status: string
  duration: string
  start_time: string
  agent_id?: string
  team_id?: string
  error_count: number
}

const traceStatusColor = (status: string) => {
  if (status === 'success' || status === 'ok') return 'text-positive'
  if (status === 'error'   || status === 'failed') return 'text-destructive'
  if (status === 'running') return 'text-warning'
  return 'text-muted'
}

const RecentTracesCard = ({ endpoint, authToken }: { endpoint: string; authToken: string }) => {
  const [traces, setTraces] = useState<TraceSummary[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const url = `${constructEndpointUrl(endpoint)}/traces?limit=6`
      const res = await fetch(url, {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {}
      })
      if (res.ok) {
        const data = await res.json()
        setTraces(Array.isArray(data) ? data.slice(0, 6) : (data.data ?? data.traces ?? []).slice(0, 6))
      }
    } catch { /* offline */ }
    finally { setLoading(false) }
  }, [endpoint, authToken])

  useEffect(() => { load() }, [load])

  return (
    <div className="flex flex-col flex-1 rounded-xl border border-accent bg-primaryAccent p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="size-4 text-brand" />
          <h3 className="text-xs font-medium uppercase text-primary">Recent Runs</h3>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} className="text-muted hover:text-primary">
            <RefreshCw className="size-3.5" />
          </button>
          <Link href="/traces" className="flex items-center gap-1 text-xs text-muted hover:text-primary">
            All <ChevronRight className="size-3" />
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="space-y-1.5">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-8" />)}</div>
      ) : traces.length === 0 ? (
        <p className="flex-1 flex items-center justify-center text-xs text-muted/50">No runs recorded yet</p>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-1">
          {traces.map((t) => (
            <Link
              key={t.trace_id}
              href={`/traces?trace=${t.trace_id}`}
              className="flex items-center gap-3 rounded-lg border border-transparent px-2 py-1.5 hover:border-accent/50 hover:bg-accent/20"
            >
              <span className={cn('size-1.5 shrink-0 rounded-full', t.error_count > 0 || t.status === 'error' ? 'bg-destructive' : t.status === 'running' ? 'bg-warning animate-pulse' : 'bg-positive')} />
              <span className="flex-1 min-w-0 truncate text-xs text-primary">{t.name || t.agent_id || t.team_id || 'run'}</span>
              <span className={cn('shrink-0 text-xs', traceStatusColor(t.status))}>{t.duration || '—'}</span>
              <span className="shrink-0 text-xs text-muted/50">{t.start_time ? dayjs(t.start_time).fromNow() : ''}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Squad Roster ─────────────────────────────────────────────────────────────

const SQUAD_MAP: Record<string, string[]> = {
  'Strategy':    ['architect', 'scribe'],
  'Context':     ['discovery', 'librarian'],
  'Engineering': ['engineer', 'data-agent', 'data_agent', 'technical_tester', 'technical-tester'],
  'Operations':  ['detective', 'medic', 'curator'],
  'Quality':     ['judge', 'healing_judge', 'healing-judge'],
  'Diagnostics': ['ci_log_analyzer', 'ci-log-analyzer', 'pipeline-analyst', 'pipeline_analyst', 'impact-analyst', 'impact_analyst'],
}

const SquadRosterCard = () => {
  const { agents, isEndpointLoading, isEndpointActive } = useStore()

  // group agents by squad
  const squadGroups: { squad: string; members: typeof agents }[] = Object.entries(SQUAD_MAP).map(([squad, ids]) => ({
    squad,
    members: agents.filter((a) => ids.some((id) => a.id === id || (a.name || '').toLowerCase().includes(id.replace('-', ' ').replace('_', ' ')))),
  })).filter((g) => g.members.length > 0)

  const ungrouped = agents.filter((a) =>
    !Object.values(SQUAD_MAP).flat().some((id) => a.id === id || (a.name || '').toLowerCase().includes(id.replace('-', ' ').replace('_', ' ')))
  )

  return (
    <div className="flex flex-col flex-1 rounded-xl border border-accent bg-primaryAccent p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="size-4 text-brand" />
          <h3 className="text-xs font-medium uppercase text-primary">Fleet</h3>
        </div>
        <span className={cn('rounded-full px-2 py-0.5 text-xs', isEndpointActive ? 'bg-positive/10 text-positive' : 'bg-destructive/10 text-destructive')}>
          {isEndpointActive ? 'Online' : 'Offline'}
        </span>
      </div>

      {isEndpointLoading ? (
        <div className="space-y-1.5">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-8" />)}</div>
      ) : agents.length === 0 ? (
        <p className="py-4 text-center text-xs text-muted/50">No agents connected</p>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-3">
          {squadGroups.map(({ squad, members }) => (
            <div key={squad}>
              <div className="mb-1 flex items-center gap-1.5">
                <Users className="size-3 text-muted/50" />
                <span className="text-xs font-medium text-muted/70">{squad}</span>
              </div>
              <div className="space-y-1 pl-2">
                {members.map((agent) => (
                  <div key={agent.id} className="flex items-center gap-2 rounded-md px-2 py-1">
                    <span className={cn('size-1.5 shrink-0 rounded-full', isEndpointActive ? 'bg-positive' : 'bg-muted/40')} />
                    <span className="flex-1 text-xs text-primary">{agent.name || agent.id}</span>
                    <span className="text-xs text-muted/50 font-mono">{agent.model?.model?.split('/').pop()?.slice(0, 12) || '—'}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
          {ungrouped.length > 0 && (
            <div>
              <div className="mb-1 flex items-center gap-1.5">
                <Bot className="size-3 text-muted/50" />
                <span className="text-xs font-medium text-muted/70">Other</span>
              </div>
              <div className="space-y-1 pl-2">
                {ungrouped.map((agent) => (
                  <div key={agent.id} className="flex items-center gap-2 rounded-md px-2 py-1">
                    <span className={cn('size-1.5 shrink-0 rounded-full', isEndpointActive ? 'bg-positive' : 'bg-muted/40')} />
                    <span className="flex-1 text-xs text-primary">{agent.name || agent.id}</span>
                    <span className="text-xs text-muted/50 font-mono">{agent.model?.model?.split('/').pop()?.slice(0, 12) || '—'}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Quick Actions ────────────────────────────────────────────────────────────

const QUICK_ACTIONS = [
  { label: 'Chat with Agent',    href: '/?agent=architect',      icon: MessageSquare, color: 'text-brand'       },
  { label: 'Spec Review',        href: '/spec-review',           icon: BookOpen,      color: 'text-positive'    },
  { label: 'Healing Dashboard',  href: '/healing',               icon: Wrench,        color: 'text-warning'     },
  { label: 'Approvals Queue',    href: '/approvals',             icon: ShieldCheck,   color: 'text-info'        },
  { label: 'Metrics',            href: '/metrics',               icon: BarChart2,     color: 'text-purple-400'  },
  { label: 'Knowledge Base',     href: '/knowledge',             icon: FlaskConical,  color: 'text-muted'       },
]

// ─── Metric Card ─────────────────────────────────────────────────────────────

const MetricCard = ({
  label, value, sub, color, href, alert
}: {
  label: string; value: string | number; sub?: string; color?: string; href?: string; alert?: boolean
}) => {
  const inner = (
    <div className={cn(
      'flex flex-col gap-1 rounded-xl border bg-primaryAccent p-4 transition-colors',
      alert ? 'border-warning/50' : 'border-accent',
      href && 'hover:border-primary/30 cursor-pointer'
    )}>
      <div className="text-xs font-medium uppercase text-muted">{label}</div>
      <div className={cn('text-2xl font-semibold', color || 'text-primary')}>{value}</div>
      {sub && <div className="text-xs text-muted/60">{sub}</div>}
    </div>
  )
  return href ? <Link href={href}>{inner}</Link> : inner
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

export default function Dashboard() {
  const { agents, teams, workflows, isEndpointActive, selectedEndpoint, authToken, envSettings } = useStore()
  const [pendingApprovals, setPendingApprovals] = useState<number | null>(null)
  const [loadingApprovals, setLoadingApprovals] = useState(true)

  useEffect(() => {
    const fetchApprovals = async () => {
      setLoadingApprovals(true)
      try {
        const base = constructEndpointUrl(selectedEndpoint)
        const res = await fetch(`${base}/approvals?status=pending&limit=1`, {
          headers: authToken ? { Authorization: `Bearer ${authToken}` } : {}
        })
        if (res.ok) {
          const data = await res.json()
          // Response may be paginated: { approvals: [...], meta: { total_count: N } } or flat array
          const count = data?.meta?.total_count ?? data?.total_count ?? (Array.isArray(data) ? data.length : null)
          setPendingApprovals(count)
        }
      } catch { /* offline */ }
      finally { setLoadingApprovals(false) }
    }
    fetchApprovals()
  }, [selectedEndpoint, authToken])

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-5xl space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-medium text-primary">Dashboard</h1>
            <p className="mt-0.5 text-xs text-muted">Quality Autopilot — Agentic STLC Control Plane</p>
          </div>
          {pendingApprovals !== null && pendingApprovals > 0 && (
            <Link
              href="/approvals"
              className="flex items-center gap-2 rounded-xl border border-warning/40 bg-warning/5 px-4 py-2 text-xs text-warning transition-colors hover:bg-warning/10"
            >
              <AlertCircle className="size-4" />
              {pendingApprovals} pending approval{pendingApprovals > 1 ? 's' : ''} — Human review required
              <ChevronRight className="size-3.5" />
            </Link>
          )}
        </div>

        {/* Metric bar */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <MetricCard
            label="AgentOS"
            value={isEndpointActive ? 'Online' : 'Offline'}
            sub={selectedEndpoint.replace(/^https?:\/\//, '')}
            color={isEndpointActive ? 'text-positive' : 'text-destructive'}
          />
          <MetricCard label="Agents" value={agents.length} sub="Registered" href="/?mode=agent" />
          <MetricCard label="Squads" value={teams.length} sub="Coordinating" href="/?mode=team" />
          <MetricCard label="Workflows" value={workflows.length} sub="Pipelines" href="/?mode=workflow" />
          <MetricCard
            label="Approvals"
            value={loadingApprovals ? '…' : (pendingApprovals ?? 0)}
            sub="Pending review"
            color={pendingApprovals && pendingApprovals > 0 ? 'text-warning' : 'text-primary'}
            href="/approvals"
            alert={!!(pendingApprovals && pendingApprovals > 0)}
          />
        </div>

        {/* Main content grid */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3 lg:items-stretch">
          {/* Left col */}
          <div className="flex flex-col gap-4 lg:col-span-2">
            <RecentTracesCard endpoint={selectedEndpoint} authToken={authToken} />
          </div>

          {/* Right col */}
          <div className="flex flex-col gap-4">
            <SquadRosterCard />
          </div>
        </div>

        {/* Quick Actions */}
        <div className="rounded-xl border border-accent bg-primaryAccent p-4">
          <h3 className="mb-3 text-xs font-medium uppercase text-primary">Quick Actions</h3>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-6">
            {QUICK_ACTIONS.map(({ label, href, icon: Icon, color }) => (
              <Link
                key={label}
                href={href}
                className="flex flex-col items-center gap-2 rounded-xl border border-accent/50 px-3 py-3 text-center text-xs text-muted transition-colors hover:border-primary/30 hover:bg-accent/30 hover:text-primary"
              >
                <Icon className={cn('size-4', color)} />
                {label}
              </Link>
            ))}
          </div>
        </div>

        {/* External Links */}
        <div className="flex flex-wrap gap-2">
          {[
            { label: 'AgentOS API Docs', href: `${selectedEndpoint}/docs` },
            { label: 'Health Check',     href: `${selectedEndpoint}/health` },
            ...(envSettings.AUT_BASE_URL || process.env.NEXT_PUBLIC_AUT_BASE_URL
              ? [{ label: 'AUT App', href: envSettings.AUT_BASE_URL || process.env.NEXT_PUBLIC_AUT_BASE_URL || '#' }]
              : []),
          ].map((link) => (
            <a
              key={link.label}
              href={link.href}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 rounded-lg border border-accent/50 px-3 py-1.5 text-xs text-muted transition-colors hover:border-primary/30 hover:text-primary"
            >
              {link.label}
              <ExternalLink className="size-3 shrink-0" />
            </a>
          ))}
        </div>

      </div>
    </div>
  )
}
