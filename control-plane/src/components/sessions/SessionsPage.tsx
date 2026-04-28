'use client'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useStore } from '@/store'
import { fetchSessionsPageAPI, deleteSessionAPI, getSessionAPI } from '@/api/os'
import { SessionSchema, PaginatedSessions } from '@/types/os'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  MessageSquare, RefreshCw, Trash2, ChevronLeft, ChevronRight,
  Search, Bot, Users, GitBranch, Clock, Coins, X, ChevronDown,
  Copy, Cpu, Wrench, Brain, PanelRightClose,
} from 'lucide-react'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import { toast } from 'sonner'

dayjs.extend(relativeTime)

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
type SessionTypeFilter = 'all' | 'agent' | 'team' | 'workflow'
type SortOption = 'updated_at_desc' | 'created_at_desc' | 'created_at_asc'
type DetailTab = 'runs' | 'summary' | 'metrics' | 'details'

interface RunRecord {
  run_id: string
  agent_id?: string
  status?: string
  run_input?: string
  content?: string
  reasoning_content?: string
  metrics?: {
    duration?: number
    input_tokens?: number
    output_tokens?: number
    total_tokens?: number
    time_to_first_token?: number
    details?: { model?: Array<{ id?: string; provider?: string; input_tokens?: number; output_tokens?: number; total_tokens?: number }> }
  }
  created_at?: number
  messages?: Array<{ role: string; content: string; created_at?: number }>
  tools?: Array<{ tool_call_id?: string; tool_name?: string; tool_args?: Record<string, unknown> }>
}

const SORT_LABELS: Record<SortOption, string> = {
  updated_at_desc: 'Last Updated',
  created_at_desc: 'Newest First',
  created_at_asc: 'Oldest First',
}

const TYPE_FILTERS: { value: SessionTypeFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'agent', label: 'Agent' },
  { value: 'team', label: 'Team' },
  { value: 'workflow', label: 'Workflow' },
]

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function parseSortOption(opt: SortOption): { sortBy: string; sortOrder: 'asc' | 'desc' } {
  if (opt === 'updated_at_desc') return { sortBy: 'updated_at', sortOrder: 'desc' }
  if (opt === 'created_at_desc') return { sortBy: 'created_at', sortOrder: 'desc' }
  return { sortBy: 'created_at', sortOrder: 'asc' }
}

function getSessionEntity(s: SessionSchema): string {
  return s.agent_id || s.team_id || s.workflow_id || '—'
}

function getTypeColor(type?: string): string {
  switch (type) {
    case 'agent': return 'text-blue-400 bg-blue-400/10 border-blue-400/20'
    case 'team': return 'text-purple-400 bg-purple-400/10 border-purple-400/20'
    case 'workflow': return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20'
    default: return 'text-muted bg-white/5 border-white/10'
  }
}

function getTypeIcon(type?: string) {
  switch (type) {
    case 'agent':    return <Bot       className="size-3" />
    case 'team':     return <Users     className="size-3" />
    case 'workflow': return <GitBranch className="size-3" />
    default:         return <MessageSquare className="size-3" />
  }
}

const copyText = (text: string) =>
  navigator.clipboard.writeText(text).then(() => toast.success('Copied')).catch(() => {})

// ---------------------------------------------------------------------------
// ReasoningBlock
// ---------------------------------------------------------------------------
const ReasoningBlock = ({ content }: { content: string }) => {
  const [open, setOpen] = useState(false)
  const preview = content.slice(0, 120)
  return (
    <div className="rounded-xl border border-purple-400/20 bg-purple-400/5 px-3 py-2">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-1.5 text-left">
        <Brain className="size-3 text-purple-400 shrink-0" />
        <span className="flex-1 truncate text-xs text-purple-400/80">
          {open ? 'Reasoning' : `Reasoning — ${preview}${content.length > 120 ? '…' : ''}`}
        </span>
        {open
          ? <ChevronDown className="size-3 text-purple-400/50" />
          : <ChevronRight className="size-3 text-purple-400/50" />}
      </button>
      {open && (
        <pre className="mt-2 max-h-48 overflow-y-auto whitespace-pre-wrap text-xs text-purple-300/70 font-mono leading-relaxed">
          {content}
        </pre>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// RunItem — one user/agent exchange
// ---------------------------------------------------------------------------
const RunItem = ({ run, index }: { run: RunRecord; index: number }) => {
  const [showDetails, setShowDetails] = useState(false)
  const [tab, setTab] = useState<'formatted' | 'text'>('formatted')

  const userMsg  = run.run_input ?? ''
  const agentMsg = run.content   ?? ''
  const toolNames = (run.tools ?? []).map((t) => t.tool_name ?? t.tool_call_id ?? 'tool').filter(Boolean)
  const hasReasoning = !!run.reasoning_content

  return (
    <div className="border-b border-white/5 last:border-0">
      <button
        onClick={() => setShowDetails(!showDetails)}
        className="flex w-full items-center gap-2 px-4 py-2.5 text-left hover:bg-white/[0.03] transition-colors"
      >
        <span className="text-xs font-mono text-muted/50">#{index + 1}</span>
        <span className="flex-1 truncate text-xs text-muted/70">
          {userMsg.slice(0, 80)}{userMsg.length > 80 ? '…' : ''}
        </span>
        {run.metrics?.duration !== undefined && (
          <span className="shrink-0 text-xs text-muted/40">{run.metrics.duration.toFixed(2)}s</span>
        )}
        {showDetails
          ? <ChevronDown       className="size-3.5 shrink-0 text-muted/40" />
          : <ChevronRight className="size-3.5 shrink-0 text-muted/40" />}
      </button>

      {showDetails && (
        <div className="px-4 pb-4 space-y-3">
          {/* Tab strip */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-muted uppercase tracking-wide">Run {index + 1}</span>
            <span className="ml-auto text-xs text-muted/40">Show Details</span>
            <div className="flex gap-0.5 rounded-lg border border-accent/60 p-0.5">
              {(['formatted', 'text'] as const).map((t) => (
                <button key={t} onClick={() => setTab(t)}
                  className={cn('rounded px-2 py-0.5 text-xs capitalize transition-colors',
                    tab === t ? 'bg-accent text-primary' : 'text-muted hover:text-primary')}>
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* User */}
          <div>
            <div className="mb-1 flex items-center gap-1.5">
              <span className="text-xs font-semibold text-muted/60">user</span>
              {run.created_at && (
                <span className="text-xs text-muted/30">{dayjs.unix(run.created_at).format('D MMM YYYY, h:mma')}</span>
              )}
            </div>
            <div className="rounded-xl bg-white/[0.04] border border-white/5 px-3 py-2 text-xs text-primary">
              {tab === 'formatted'
                ? <p className="whitespace-pre-wrap">{userMsg}</p>
                : <pre className="whitespace-pre-wrap font-mono">{userMsg}</pre>}
            </div>
          </div>

          {/* Tools */}
          {toolNames.length > 0 && (
            <div>
              <div className="mb-1 flex items-center gap-1.5">
                <Wrench className="size-3 text-warning" />
                <span className="text-xs font-semibold text-muted/60">Tools</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {toolNames.map((name, i) => (
                  <span key={i} className="rounded-md bg-warning/10 border border-warning/20 px-2 py-0.5 text-xs text-warning font-mono">
                    {name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Reasoning */}
          {hasReasoning && <ReasoningBlock content={run.reasoning_content!} />}

          {/* Agent */}
          <div>
            <div className="mb-1 flex items-center gap-1.5">
              <Bot className="size-3 text-brand" />
              <span className="text-xs font-semibold text-muted/60">Agent</span>
            </div>
            <div className="rounded-xl bg-brand/5 border border-brand/10 px-3 py-2 text-xs text-primary max-h-64 overflow-y-auto">
              {tab === 'formatted'
                ? <p className="whitespace-pre-wrap">{agentMsg}</p>
                : <pre className="whitespace-pre-wrap font-mono">{agentMsg}</pre>}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Session Detail Panel
// ---------------------------------------------------------------------------
const SessionDetailPanel = ({ session, onClose }: { session: SessionSchema; onClose: () => void }) => {
  const { selectedEndpoint, authToken } = useStore()
  const [tab, setTab]     = useState<DetailTab>('runs')
  const [runs, setRuns]   = useState<RunRecord[]>([])
  const [loading, setLoading] = useState(false)

  const fetchRuns = useCallback(async () => {
    if (!selectedEndpoint) return
    setLoading(true)
    try {
      const type = (session.session_type === 'team' ? 'team' : 'agent') as 'agent' | 'team'
      const data = await getSessionAPI(selectedEndpoint, type, session.session_id, undefined, authToken)
      setRuns(Array.isArray(data) ? data : [])
    } catch { setRuns([]) }
    finally { setLoading(false) }
  }, [selectedEndpoint, authToken, session.session_id, session.session_type])

  useEffect(() => { fetchRuns(); setTab('runs') }, [fetchRuns])

  const TABS: { id: DetailTab; label: string }[] = [
    { id: 'runs',    label: `Runs${runs.length ? ` (${runs.length})` : ''}` },
    { id: 'summary', label: 'Summary' },
    { id: 'metrics', label: 'Metrics' },
    { id: 'details', label: 'Details' },
  ]

  const totalIn  = runs.reduce((s, r) => s + (r.metrics?.input_tokens  ?? 0), 0)
  const totalOut = runs.reduce((s, r) => s + (r.metrics?.output_tokens ?? 0), 0)
  const totalTok = runs.reduce((s, r) => s + (r.metrics?.total_tokens  ?? 0), 0)
  const totalDur = runs.reduce((s, r) => s + (r.metrics?.duration      ?? 0), 0)

  return (
    <div className="flex h-full w-[45%] shrink-0 flex-col border-l border-white/5 bg-background overflow-hidden">
      {/* Panel header */}
      <div className="flex shrink-0 items-center gap-2 border-b border-white/5 px-4 py-3">
        <span className={cn(
          'inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10px] font-medium uppercase',
          getTypeColor(session.session_type)
        )}>
          {getTypeIcon(session.session_type)}
          {session.session_type ?? 'session'}
        </span>
        <span className="flex-1 truncate text-sm font-medium text-primary">
          {session.session_name || session.session_id}
        </span>
        <button onClick={onClose} className="shrink-0 rounded-lg p-1 text-muted hover:bg-accent/50 hover:text-primary">
          <PanelRightClose className="size-4" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex shrink-0 border-b border-white/5 px-4">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={cn('border-b-2 px-3 py-2.5 text-xs font-medium transition-colors',
              tab === t.id ? 'border-brand text-primary' : 'border-transparent text-muted hover:text-primary')}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">

        {/* RUNS */}
        {tab === 'runs' && (
          <div>
            {loading ? (
              <div className="space-y-2 p-4">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-12 rounded-xl" />)}</div>
            ) : runs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <MessageSquare className="size-8 text-muted/20" />
                <p className="mt-2 text-xs text-muted/50">No runs found for this session</p>
              </div>
            ) : (
              runs.map((run, i) => <RunItem key={run.run_id ?? i} run={run} index={i} />)
            )}
          </div>
        )}

        {/* SUMMARY */}
        {tab === 'summary' && (
          <div className="p-4 space-y-3">
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Runs',         value: String(runs.length) },
                { label: 'Total Tokens', value: (session.total_tokens ?? totalTok).toLocaleString() },
                { label: 'Created',      value: session.created_at ? dayjs(session.created_at).format('D MMM, HH:mm') : '—' },
                { label: 'Updated',      value: session.updated_at  ? dayjs(session.updated_at).fromNow()             : '—' },
              ].map(({ label, value }) => (
                <div key={label} className="rounded-xl bg-white/[0.03] border border-white/5 px-3 py-2">
                  <div className="text-xs text-muted uppercase tracking-wide">{label}</div>
                  <div className="mt-0.5 text-sm font-semibold text-primary">{value}</div>
                </div>
              ))}
            </div>
            {session.session_summary ? (
              <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                <div className="mb-1.5 text-xs font-medium uppercase text-muted">Session Summary</div>
                <pre className="whitespace-pre-wrap text-xs text-primary/80 leading-relaxed">
                  {typeof session.session_summary === 'string'
                    ? session.session_summary
                    : JSON.stringify(session.session_summary, null, 2)}
                </pre>
              </div>
            ) : (
              <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4 text-center text-xs text-muted/40">
                No summary available for this session
              </div>
            )}
          </div>
        )}

        {/* METRICS */}
        {tab === 'metrics' && (
          <div className="p-4 space-y-4">
            <div>
              <div className="mb-2 text-xs font-medium uppercase text-muted">Session Totals</div>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: 'Input Tokens',  value: totalIn.toLocaleString(),  color: 'text-info' },
                  { label: 'Output Tokens', value: totalOut.toLocaleString(), color: 'text-positive' },
                  { label: 'Total Tokens',  value: totalTok.toLocaleString(), color: 'text-brand' },
                  { label: 'Total Duration', value: `${totalDur.toFixed(2)}s`, color: 'text-primary' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="rounded-xl bg-white/[0.03] border border-white/5 px-3 py-2">
                    <div className="text-xs text-muted uppercase tracking-wide">{label}</div>
                    <div className={cn('mt-0.5 text-sm font-semibold', color)}>{value}</div>
                  </div>
                ))}
              </div>
            </div>
            {runs.length > 0 && (
              <div>
                <div className="mb-2 text-xs font-medium uppercase text-muted">Per-Run Breakdown</div>
                <div className="space-y-1.5">
                  {runs.map((run, i) => {
                    const model = run.metrics?.details?.model?.[0]
                    return (
                      <div key={run.run_id ?? i} className="rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-mono text-muted/50">Run {i + 1}</span>
                          {model?.id && (
                            <span className="flex items-center gap-1 text-xs text-muted/60">
                              <Cpu className="size-3" />{model.id}
                            </span>
                          )}
                          {run.metrics?.duration !== undefined && (
                            <span className="ml-auto text-xs text-muted/40">{run.metrics.duration.toFixed(2)}s</span>
                          )}
                        </div>
                        <div className="flex gap-4 text-xs">
                          <span className="text-info">↑ {(run.metrics?.input_tokens ?? 0).toLocaleString()}</span>
                          <span className="text-positive">↓ {(run.metrics?.output_tokens ?? 0).toLocaleString()}</span>
                          <span className="text-muted">= {(run.metrics?.total_tokens ?? 0).toLocaleString()}</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
            {session.metrics && (
              <div>
                <div className="mb-2 text-xs font-medium uppercase text-muted">Session Metrics</div>
                <pre className="rounded-xl border border-white/5 bg-white/[0.02] p-3 text-xs text-primary/80 font-mono leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto">
                  {JSON.stringify(session.metrics, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* DETAILS */}
        {tab === 'details' && (
          <div className="p-4 space-y-2">
            {[
              { label: 'Session ID',   value: session.session_id,   mono: true },
              { label: 'Session Name', value: session.session_name, mono: false },
              { label: 'Type',         value: session.session_type ?? '—',      mono: false },
              { label: 'Entity',       value: session.agent_id || session.team_id || session.workflow_id || '—', mono: true },
              { label: 'User ID',      value: session.user_id ?? '—', mono: true },
              { label: 'Created At',   value: session.created_at ? dayjs(session.created_at).format('D MMM YYYY, HH:mm:ss') : '—', mono: false },
              { label: 'Updated At',   value: session.updated_at ? dayjs(session.updated_at).format('D MMM YYYY, HH:mm:ss') : '—', mono: false },
            ].map(({ label, value, mono }) => (
              <div key={label}
                className="group flex items-start justify-between gap-2 rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2 hover:bg-white/[0.04] cursor-pointer"
                onClick={() => value && value !== '—' && copyText(value)}
                title={value && value !== '—' ? 'Click to copy' : undefined}>
                <span className="shrink-0 text-xs text-muted">{label}</span>
                <span className={cn('text-right text-xs text-primary break-all', mono && 'font-mono')}>{value}</span>
                {value && value !== '—' && (
                  <Copy className="size-3 shrink-0 text-muted/0 group-hover:text-muted/50 transition-colors mt-0.5" />
                )}
              </div>
            ))}
            {session.session_state && Object.keys(session.session_state).length > 0 && (
              <div className="rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2">
                <div className="mb-2 text-xs text-muted">Session State Keys</div>
                <div className="flex flex-wrap gap-1.5">
                  {Object.keys(session.session_state).map((k) => (
                    <span key={k} className="rounded-md bg-white/5 border border-white/10 px-2 py-0.5 text-xs font-mono text-muted/70">{k}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Session Row
// ---------------------------------------------------------------------------
const SessionRow = ({
  session,
  isSelected,
  onSelect,
  onDelete,
  deleting,
}: {
  session: SessionSchema
  isSelected: boolean
  onSelect: (s: SessionSchema) => void
  onDelete: (id: string, type?: string) => void
  deleting: boolean
}) => {
  return (
    <div
      onClick={() => onSelect(session)}
      className={cn(
        'group flex cursor-pointer items-start gap-3 rounded-xl border px-4 py-3 transition-colors',
        isSelected
          ? 'border-brand/40 bg-brand/5'
          : 'border-white/5 bg-white/[0.02] hover:bg-white/[0.04] hover:border-white/10'
      )}
    >
      {/* Type badge */}
      <div className="mt-0.5 shrink-0">
        <span className={cn(
          'inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider',
          getTypeColor(session.session_type),
        )}>
          {getTypeIcon(session.session_type)}
          {session.session_type ?? 'unknown'}
        </span>
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-primary">
          {session.session_name || session.session_id}
        </p>
        <p className="mt-0.5 truncate text-xs text-muted">
          <span className="font-mono">{getSessionEntity(session)}</span>
          {session.user_id && <span className="ml-2 opacity-60">· {session.user_id}</span>}
        </p>
      </div>

      {/* Meta */}
      <div className="flex shrink-0 flex-col items-end gap-1 text-xs text-muted">
        {session.total_tokens != null && (
          <span className="flex items-center gap-1">
            <Coins className="size-3" />{session.total_tokens.toLocaleString()}
          </span>
        )}
        <span className="flex items-center gap-1" title={session.updated_at ?? session.created_at}>
          <Clock className="size-3" />
          {session.updated_at
            ? dayjs(session.updated_at).fromNow()
            : session.created_at ? dayjs(session.created_at).fromNow() : '—'}
        </span>
      </div>

      {/* Delete */}
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(session.session_id, session.session_type) }}
        disabled={deleting}
        className="ml-1 shrink-0 rounded p-1 text-muted opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-400 disabled:opacity-30"
        title="Delete session"
      >
        {deleting ? <RefreshCw className="size-3.5 animate-spin" /> : <Trash2 className="size-3.5" />}
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Skeleton rows
// ---------------------------------------------------------------------------
const SkeletonRows = ({ count = 8 }: { count?: number }) => (
  <>
    {Array.from({ length: count }).map((_, i) => (
      <div key={i} className="flex items-start gap-3 rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3">
        <Skeleton className="mt-0.5 h-5 w-14 rounded-md" />
        <div className="flex-1 space-y-1.5">
          <Skeleton className="h-4 w-2/3 rounded" />
          <Skeleton className="h-3 w-1/3 rounded" />
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <Skeleton className="h-3 w-12 rounded" />
          <Skeleton className="h-3 w-16 rounded" />
        </div>
      </div>
    ))}
  </>
)

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------
const SessionsPage = () => {
  const selectedEndpoint = useStore((s) => s.selectedEndpoint)
  const authToken = useStore((s) => s.authToken)

  const [data, setData] = useState<PaginatedSessions | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [typeFilter, setTypeFilter] = useState<SessionTypeFilter>('all')
  const [sortOption, setSortOption] = useState<SortOption>('updated_at_desc')
  const [page, setPage] = useState(1)
  const [limit] = useState(25)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const searchDebounce = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [selectedSession, setSelectedSession] = useState<SessionSchema | null>(null)

  const load = useCallback(async () => {
    if (!selectedEndpoint) return
    setLoading(true)
    setError(null)
    try {
      const { sortBy, sortOrder } = parseSortOption(sortOption)
      const result = await fetchSessionsPageAPI({
        base: selectedEndpoint,
        sessionType: typeFilter === 'all' ? undefined : typeFilter,
        sortBy,
        sortOrder,
        limit,
        page,
        sessionName: search || undefined,
        authToken,
      })
      setData(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load sessions')
    } finally {
      setLoading(false)
    }
  }, [selectedEndpoint, authToken, typeFilter, sortOption, page, limit, search])

  useEffect(() => {
    load()
  }, [load])

  // Reset page when filters change
  useEffect(() => {
    setPage(1)
  }, [typeFilter, sortOption, search])

  const handleSearchChange = (val: string) => {
    setSearchInput(val)
    if (searchDebounce.current) clearTimeout(searchDebounce.current)
    searchDebounce.current = setTimeout(() => setSearch(val), 400)
  }

  const handleDelete = async (sessionId: string, type?: string) => {
    if (!selectedEndpoint) return
    setDeletingId(sessionId)
    try {
      const ok = await deleteSessionAPI(selectedEndpoint, sessionId, authToken)
      if (ok) {
        setData((prev) =>
          prev
            ? {
                ...prev,
                data: prev.data.filter((s) => s.session_id !== sessionId),
                meta: { ...prev.meta, total_count: prev.meta.total_count - 1 },
              }
            : prev,
        )
        if (selectedSession?.session_id === sessionId) setSelectedSession(null)
      }
    } finally {
      setDeletingId(null)
    }
  }

  const sessions = data?.data ?? []
  const meta = data?.meta
  const totalPages = meta?.total_pages ?? 1

  return (
    <div className="flex h-full overflow-hidden bg-background">
      {/* ── Left: list ── */}
      <div className={cn('flex flex-col overflow-hidden transition-all duration-200', selectedSession ? 'w-[55%]' : 'flex-1')}>
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-white/5 px-6 py-4">
        <div className="flex items-center gap-3">
          <MessageSquare className="size-5 text-brand" />
          <div>
            <h1 className="text-sm font-semibold text-primary">Sessions</h1>
            <p className="text-xs text-muted">
              {meta ? `${meta.total_count.toLocaleString()} total` : 'Conversation histories'}
            </p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={load}
          disabled={loading}
          className="gap-1.5 text-xs text-muted hover:text-primary"
        >
          <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />
          Refresh
        </Button>
      </div>

      {/* Filters bar */}
      <div className="flex shrink-0 flex-wrap items-center gap-3 border-b border-white/5 px-6 py-3">
        {/* Type tabs */}
        <div className="flex rounded-lg bg-white/[0.04] p-0.5">
          {TYPE_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setTypeFilter(f.value)}
              className={cn(
                'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                typeFilter === f.value
                  ? 'bg-accent text-primary shadow-sm'
                  : 'text-muted hover:text-primary',
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Sort */}
        <select
          value={sortOption}
          onChange={(e) => setSortOption(e.target.value as SortOption)}
          className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs text-primary focus:outline-none focus:ring-1 focus:ring-brand/50"
        >
          {(Object.keys(SORT_LABELS) as SortOption[]).map((opt) => (
            <option key={opt} value={opt} className="bg-[#111113]">
              {SORT_LABELS[opt]}
            </option>
          ))}
        </select>

        {/* Search */}
        <div className="relative ml-auto">
          <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted" />
          <input
            value={searchInput}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search sessions…"
            className="w-52 rounded-lg border border-white/10 bg-white/[0.04] py-1.5 pl-8 pr-8 text-xs text-primary placeholder:text-muted/50 focus:border-brand/50 focus:outline-none focus:ring-1 focus:ring-brand/30"
          />
          {searchInput && (
            <button
              onClick={() => { setSearchInput(''); setSearch('') }}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-primary"
            >
              <X className="size-3" />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {error ? (
          <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
            <MessageSquare className="size-10 text-muted/30" />
            <p className="text-sm text-red-400">{error}</p>
            <Button variant="ghost" size="sm" onClick={load} className="text-xs">
              Retry
            </Button>
          </div>
        ) : loading ? (
          <div className="flex flex-col gap-2">
            <SkeletonRows count={8} />
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-3 py-20 text-center">
            <MessageSquare className="size-12 text-muted/20" />
            <p className="text-sm font-medium text-muted">No sessions found</p>
            {(typeFilter !== 'all' || search) && (
              <p className="text-xs text-muted/60">Try changing the filter or search query</p>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {sessions.map((session) => (
              <SessionRow
                key={session.session_id}
                session={session}
                isSelected={selectedSession?.session_id === session.session_id}
                onSelect={setSelectedSession}
                onDelete={handleDelete}
                deleting={deletingId === session.session_id}
              />
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      {!loading && sessions.length > 0 && (
        <div className="flex shrink-0 items-center justify-between border-t border-white/5 px-6 py-3">
          <p className="text-xs text-muted">
            Page {page} of {totalPages}{meta ? ` · ${meta.total_count.toLocaleString()} sessions` : ''}
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
              className="h-7 gap-1 px-2 text-xs text-muted hover:text-primary disabled:opacity-30"
            >
              <ChevronLeft className="size-3.5" />
              Prev
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              className="h-7 gap-1 px-2 text-xs text-muted hover:text-primary disabled:opacity-30"
            >
              Next
              <ChevronRight className="size-3.5" />
            </Button>
          </div>
        </div>
      )}
      </div>{/* end left panel */}

      {/* ── Right: detail panel ── */}
      {selectedSession && (
        <SessionDetailPanel
          session={selectedSession}
          onClose={() => setSelectedSession(null)}
        />
      )}
    </div>
  )
}

export default SessionsPage
