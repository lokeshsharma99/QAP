'use client'
import { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  Activity, ChevronDown, ChevronRight, RefreshCw, CheckCircle, XCircle,
  Clock, Search, AlertCircle, ArrowLeft, Cpu, Wrench, Bot, Hash, Copy
} from 'lucide-react'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import { toast } from 'sonner'

const PAGE_TRANSITION = { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.2, ease: 'easeOut' as const } }

dayjs.extend(relativeTime)

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface SpanMeta {
  model?: string
  input_tokens?: number
  output_tokens?: number
  [key: string]: unknown
}

interface Span {
  id: string
  name: string
  type: string
  duration: string
  start_time: string
  end_time: string
  status: string
  input?: string
  output?: string
  metadata?: SpanMeta
  spans?: Span[]
}

interface TraceDetail {
  trace_id: string
  name: string
  status: string
  duration: string
  start_time: string
  end_time?: string
  total_spans: number
  error_count: number
  input?: string
  output?: string
  run_id?: string
  session_id?: string
  agent_id?: string
  team_id?: string
  user_id?: string
  created_at: string
  tree?: Span[]
}

interface TraceSummary {
  trace_id: string
  name: string
  status: string
  duration: string
  start_time: string
  total_spans: number
  error_count: number
  input?: string
  run_id?: string
  session_id?: string
  agent_id?: string
  team_id?: string
  created_at: string
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const StatusIcon = ({ status, size = 'sm' }: { status: string; size?: 'xs' | 'sm' }) => {
  const cls = size === 'xs' ? 'size-3' : 'size-3.5'
  if (status === 'OK')    return <CheckCircle className={cn(cls, 'text-positive')} />
  if (status === 'ERROR') return <XCircle     className={cn(cls, 'text-destructive')} />
  return                         <Clock       className={cn(cls, 'text-warning')} />
}

const SpanTypeIcon = ({ type }: { type: string }) => {
  if (type === 'LLM')  return <Cpu    className="size-3 text-info" />
  if (type === 'TOOL') return <Wrench className="size-3 text-warning" />
  return                      <Bot    className="size-3 text-brand" />
}

const TokenBadge = ({ span }: { span: Span }) => {
  const total = (span.metadata?.input_tokens ?? 0) + (span.metadata?.output_tokens ?? 0)
  if (!total) return null
  return (
    <span className="flex items-center gap-0.5 rounded-full bg-info/10 px-1.5 py-0.5 text-xs text-info whitespace-nowrap">
      ⊙ {total.toLocaleString()}
    </span>
  )
}

const copyText = (text: string) => {
  navigator.clipboard.writeText(text).then(() => toast.success('Copied')).catch(() => {})
}

// ---------------------------------------------------------------------------
// IOView — Input or Output panel with Text/Formatted tabs
// ---------------------------------------------------------------------------
const IOView = ({ content, label }: { content?: string; label: string }) => {
  const [tab, setTab] = useState<'text' | 'formatted'>('text')
  const [expanded, setExpanded] = useState(false)
  if (!content) return null
  const PREVIEW_LEN = 2000
  const truncated = content.length > PREVIEW_LEN && !expanded
  const displayed = truncated ? content.slice(0, PREVIEW_LEN) : content

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-medium uppercase text-muted">{label}</span>
        <div className="flex items-center gap-1">
          <div className="flex gap-0.5 rounded-lg border border-accent p-0.5">
            {(['text', 'formatted'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={cn(
                  'rounded px-2 py-0.5 text-xs capitalize transition-colors',
                  tab === t ? 'bg-accent text-primary' : 'text-muted hover:text-primary'
                )}
              >
                {t}
              </button>
            ))}
          </div>
          <button
            onClick={() => copyText(content)}
            className="rounded-lg p-1 text-muted hover:bg-accent hover:text-primary"
          >
            <Copy className="size-3" />
          </button>
        </div>
      </div>
      <div className="relative">
        {tab === 'formatted' ? (
          <div className="max-h-80 overflow-y-auto rounded-xl bg-background p-3 text-xs text-primary leading-relaxed">
            <pre className="whitespace-pre-wrap">{displayed}</pre>
          </div>
        ) : (
          <pre className="max-h-80 overflow-y-auto rounded-xl bg-background p-3 text-xs text-primary leading-relaxed whitespace-pre-wrap">
            {displayed}
          </pre>
        )}
        {truncated && (
          <button
            onClick={() => setExpanded(true)}
            className="mt-1 text-xs text-brand hover:underline"
          >
            Show {(content.length - PREVIEW_LEN).toLocaleString()} more characters…
          </button>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// SpanDetail — shown in right panel when span is selected
// ---------------------------------------------------------------------------
const SpanDetail = ({ span }: { span: Span }) => (
  <div className="space-y-3 p-4">
    <div className="flex flex-wrap items-center gap-2">
      <SpanTypeIcon type={span.type} />
      <span className="text-sm font-medium text-primary">{span.name}</span>
      <span className={cn(
        'rounded-full px-2 py-0.5 text-xs uppercase',
        span.type === 'LLM'  ? 'bg-info/10 text-info' :
        span.type === 'TOOL' ? 'bg-warning/10 text-warning' : 'bg-brand/10 text-brand'
      )}>{span.type}</span>
      <StatusIcon status={span.status} size="xs" />
    </div>

    <div className="grid grid-cols-2 gap-2 text-xs">
      {[
        { label: 'Duration', value: span.duration },
        { label: 'Span ID',  value: span.id },
        { label: 'Start',    value: dayjs(span.start_time).format('HH:mm:ss.SSS') },
        { label: 'End',      value: dayjs(span.end_time).format('HH:mm:ss.SSS') },
      ].map(({ label, value }) => (
        <div
          key={label}
          className="rounded-lg bg-accent/50 px-3 py-2 cursor-pointer"
          onClick={() => copyText(value)}
        >
          <div className="uppercase text-muted">{label}</div>
          <div className="mt-0.5 font-mono truncate text-primary">{value}</div>
        </div>
      ))}
    </div>

    {span.metadata && Object.keys(span.metadata).length > 0 && (
      <div className="rounded-xl border border-accent bg-background p-3 space-y-1.5 text-xs">
        {span.metadata.model && (
          <div className="flex justify-between">
            <span className="text-muted">Model</span>
            <span className="font-mono text-primary">{String(span.metadata.model)}</span>
          </div>
        )}
        {span.metadata.input_tokens !== undefined && (
          <div className="flex justify-between">
            <span className="text-muted">Input tokens</span>
            <span className="text-info">{span.metadata.input_tokens.toLocaleString()}</span>
          </div>
        )}
        {span.metadata.output_tokens !== undefined && (
          <div className="flex justify-between">
            <span className="text-muted">Output tokens</span>
            <span className="text-info">{span.metadata.output_tokens.toLocaleString()}</span>
          </div>
        )}
      </div>
    )}

    <IOView content={span.input}  label="Input"  />
    <IOView content={span.output} label="Output" />
  </div>
)

// ---------------------------------------------------------------------------
// SpanRow — recursive span tree row
// ---------------------------------------------------------------------------
const SpanRow = ({
  span, depth, selected, onSelect, traceStart, traceDuration, viewMode,
}: {
  span: Span; depth: number; selected: string | null
  onSelect: (id: string) => void
  traceStart: number; traceDuration: number; viewMode: 'tree' | 'timeline'
}) => {
  const [collapsed, setCollapsed] = useState(false)
  const hasChildren = !!(span.spans && span.spans.length > 0)
  const isSelected  = selected === span.id

  const spanStart = new Date(span.start_time).getTime()
  const spanEnd   = new Date(span.end_time).getTime()
  const left  = traceDuration > 0 ? Math.min(((spanStart - traceStart) / traceDuration) * 100, 99) : 0
  const width = traceDuration > 0 ? Math.max(((spanEnd - spanStart) / traceDuration) * 100, 0.5) : 1

  return (
    <>
      <div
        onClick={() => onSelect(span.id)}
        className={cn(
          'group flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-xs transition-colors select-none',
          isSelected ? 'bg-brand/10 text-primary' : 'hover:bg-accent/50 text-primary'
        )}
        style={{ paddingLeft: `${8 + depth * 16}px` }}
      >
        <button
          onClick={(e) => { e.stopPropagation(); if (hasChildren) setCollapsed(!collapsed) }}
          className="shrink-0 w-4 flex justify-center"
        >
          {hasChildren
            ? (collapsed
                ? <ChevronRight className="size-3 text-muted" />
                : <ChevronDown  className="size-3 text-muted" />)
            : <span />}
        </button>

        <SpanTypeIcon type={span.type} />

        {viewMode === 'tree' ? (
          <>
            <span className="flex-1 truncate font-medium">{span.name}</span>
            <TokenBadge span={span} />
            <StatusIcon status={span.status} size="xs" />
            <span className="shrink-0 text-muted/60">{span.duration}</span>
          </>
        ) : (
          <>
            <span className="w-40 shrink-0 truncate font-medium">{span.name}</span>
            <div className="relative flex-1 h-4 rounded bg-accent/50 overflow-hidden">
              <div
                className={cn(
                  'absolute top-0.5 h-3 rounded',
                  span.type === 'LLM'  ? 'bg-info/60' :
                  span.type === 'TOOL' ? 'bg-warning/60' : 'bg-brand/60'
                )}
                style={{ left: `${left}%`, width: `${width}%` }}
              />
            </div>
            <span className="w-16 shrink-0 text-right text-muted/60">{span.duration}</span>
          </>
        )}
      </div>

      {!collapsed && hasChildren && span.spans!.map((child) => (
        <SpanRow
          key={child.id} span={child} depth={depth + 1}
          selected={selected} onSelect={onSelect}
          traceStart={traceStart} traceDuration={traceDuration}
          viewMode={viewMode}
        />
      ))}
    </>
  )
}

// ---------------------------------------------------------------------------
// TraceDetailView — full-page view for one trace
// ---------------------------------------------------------------------------
const TraceDetailView = ({ traceId, onBack }: { traceId: string; onBack: () => void }) => {
  const { selectedEndpoint, authToken } = useStore()
  const [trace, setTrace]           = useState<TraceDetail | null>(null)
  const [loading, setLoading]       = useState(true)
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(null)
  const [viewMode, setViewMode]     = useState<'tree' | 'timeline'>('tree')

  const fetchDetail = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(APIRoutes.GetTrace(selectedEndpoint, traceId), {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {}
      })
      if (!res.ok) throw new Error(res.statusText)
      setTrace(await res.json())
    } catch { /* silently handled */ }
    finally { setLoading(false) }
  }, [selectedEndpoint, authToken, traceId])

  useEffect(() => { fetchDetail() }, [fetchDetail])

  const flattenSpans = (spans: Span[]): Span[] =>
    spans.flatMap((s) => [s, ...flattenSpans(s.spans ?? [])])

  const allSpans   = trace?.tree ? flattenSpans(trace.tree) : []
  const activeSpan = allSpans.find((s) => s.id === selectedSpanId) ?? null

  const traceStart    = trace ? new Date(trace.start_time).getTime() : 0
  const traceEnd      = trace?.end_time ? new Date(trace.end_time).getTime() : traceStart
  const traceDuration = Math.max(traceEnd - traceStart, 1)

  if (loading) return (
    <div className="p-6 space-y-4">
      <Skeleton className="h-8 w-48 rounded-xl" />
      <Skeleton className="h-32 rounded-xl" />
      <Skeleton className="h-64 rounded-xl" />
    </div>
  )

  if (!trace) return (
    <div className="flex items-center justify-center p-12 text-sm text-muted">Trace not found</div>
  )

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center gap-3 border-b border-accent p-4 shrink-0">
        <button onClick={onBack} className="rounded-lg p-1.5 text-muted hover:bg-accent hover:text-primary">
          <ArrowLeft className="size-4" />
        </button>
        <StatusIcon status={trace.status} />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-primary truncate">{trace.name}</div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted mt-0.5">
            <span>{parseFloat(trace.duration ?? '0').toFixed(2)}s</span>
            <span>·</span>
            <span>{trace.total_spans} spans</span>
            {trace.agent_id && (
              <span className="rounded-full bg-brand/10 px-2 py-0.5 text-brand">{trace.agent_id}</span>
            )}
            {trace.team_id && (
              <span className="rounded-full bg-info/10 px-2 py-0.5 text-info">{trace.team_id}</span>
            )}
            {trace.error_count > 0 && (
              <span className="flex items-center gap-1 rounded-full bg-destructive/10 px-2 py-0.5 text-destructive">
                <AlertCircle className="size-3" />{trace.error_count} errors
              </span>
            )}
          </div>
        </div>
        <Button size="sm" variant="outline" onClick={fetchDetail} className="gap-1.5 shrink-0">
          <RefreshCw className="size-3.5" />
        </Button>
      </div>

      {/* Metadata row */}
      <div className="grid grid-cols-2 gap-2 p-4 border-b border-accent shrink-0 md:grid-cols-4">
        {[
          { label: 'Created At', value: dayjs(trace.created_at).format('D MMM YYYY, HH:mm:ss') },
          { label: 'Trace ID',   value: trace.trace_id },
          { label: 'Run ID',     value: trace.run_id ?? '—' },
          { label: 'Session ID', value: trace.session_id ?? '—' },
        ].map(({ label, value }) => (
          <div
            key={label}
            className="rounded-lg bg-accent/40 px-3 py-2 text-xs cursor-pointer hover:bg-accent/60"
            onClick={() => value !== '—' && copyText(value)}
            title={value !== '—' ? 'Click to copy' : undefined}
          >
            <div className="uppercase text-muted">{label}</div>
            <div className="mt-0.5 font-mono truncate text-primary">{value}</div>
          </div>
        ))}
      </div>

      {/* Main area: tree + span detail */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: span tree */}
        <div className={cn('flex flex-col border-r border-accent overflow-hidden', activeSpan ? 'w-1/2' : 'flex-1')}>
          {/* Tab row */}
          <div className="flex items-center gap-1 border-b border-accent px-4 py-2 shrink-0">
            {(['tree', 'timeline'] as const).map((m) => (
              <button
                key={m}
                onClick={() => setViewMode(m)}
                className={cn(
                  'rounded-lg px-3 py-1 text-xs font-medium capitalize transition-colors',
                  viewMode === m ? 'bg-accent text-primary' : 'text-muted hover:text-primary'
                )}
              >
                {m === 'tree' ? 'Tree' : 'Timeline'}
              </button>
            ))}
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {(trace.tree ?? []).map((span) => (
              <SpanRow
                key={span.id} span={span} depth={0}
                selected={selectedSpanId} onSelect={setSelectedSpanId}
                traceStart={traceStart} traceDuration={traceDuration}
                viewMode={viewMode}
              />
            ))}
          </div>
        </div>

        {/* Right: span detail or trace I/O */}
        <div className="flex-1 overflow-y-auto">
          {activeSpan ? (
            <SpanDetail span={activeSpan} />
          ) : (
            <div className="space-y-4 p-4">
              <p className="text-xs text-muted/60">Click a span to inspect its input, output, and metadata.</p>
              <IOView content={trace.input}  label="Trace Input"  />
              <IOView content={trace.output} label="Trace Output" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// TraceCard — summary row in list
// ---------------------------------------------------------------------------
const TraceCard = ({ trace, onClick }: { trace: TraceSummary; onClick: () => void }) => (
  <div
    onClick={onClick}
    className={cn(
      'cursor-pointer rounded-xl border bg-primaryAccent p-4 transition-colors hover:border-primary/20',
      trace.error_count > 0 ? 'border-destructive/30' : 'border-accent'
    )}
  >
    <div className="flex items-start gap-3">
      <div className="mt-0.5"><StatusIcon status={trace.status} /></div>
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-primary truncate max-w-xs">{trace.name}</span>
          {trace.agent_id && (
            <span className="rounded-full bg-brand/10 px-2 py-0.5 text-xs text-brand">{trace.agent_id}</span>
          )}
          {trace.team_id && (
            <span className="rounded-full bg-info/10 px-2 py-0.5 text-xs text-info">{trace.team_id}</span>
          )}
          {trace.error_count > 0 && (
            <span className="flex items-center gap-1 rounded-full bg-destructive/10 px-2 py-0.5 text-xs text-destructive">
              <AlertCircle className="size-3" />{trace.error_count} errors
            </span>
          )}
        </div>
        <div className="mt-1 flex flex-wrap gap-3 text-xs text-muted">
          <span>{dayjs(trace.start_time).format('D MMM HH:mm:ss')}</span>
          <span>{parseFloat(trace.duration ?? '0').toFixed(2)}s</span>
          <span>{trace.total_spans} spans</span>
        </div>
        {trace.input && (
          <div className="mt-1.5 truncate text-xs text-muted/60 font-mono">
            &quot;{trace.input.slice(0, 120)}{trace.input.length > 120 ? '…' : ''}&quot;
          </div>
        )}
      </div>
      <ChevronRight className="size-4 shrink-0 text-muted/40 mt-1" />
    </div>
  </div>
)

// ---------------------------------------------------------------------------
// TracesPage — main export
// ---------------------------------------------------------------------------
export default function TracesPage() {
  const { selectedEndpoint, authToken } = useStore()
  const [traces, setTraces]   = useState<TraceSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch]   = useState('')
  const [filter, setFilter]   = useState<'all' | 'OK' | 'ERROR'>('all')
  const [selectedTrace, setSelectedTrace] = useState<string | null>(null)
  const [page, setPage]       = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  // DSL search
  const [dslMode, setDslMode] = useState(false)
  const [dslQuery, setDslQuery] = useState(JSON.stringify({ filters: [], limit: 20 }, null, 2))
  const [dslSearching, setDslSearching] = useState(false)
  const [dslResults, setDslResults] = useState<TraceSummary[] | null>(null)

  const authHeaders: Record<string, string> = authToken ? { Authorization: `Bearer ${authToken}` } : {}

  const fetchTraces = useCallback(async (pg = 1) => {
    if (!selectedEndpoint) return
    setLoading(true)
    try {
      const url = new URL(APIRoutes.GetTraces(selectedEndpoint))
      url.searchParams.set('limit', '20')
      url.searchParams.set('page', String(pg))
      if (filter !== 'all') url.searchParams.set('status', filter)
      const res = await fetch(url.toString(), { headers: authHeaders })
      if (!res.ok) throw new Error(res.statusText)
      const data = await res.json()
      setTraces(data?.data ?? [])
      setTotalPages(data?.meta?.total_pages ?? 1)
      setPage(pg)
    } catch { /* silently handled */ }
    finally { setLoading(false) }
  }, [selectedEndpoint, authToken, filter])

  const handleDslSearch = async () => {
    if (!selectedEndpoint) return
    setDslSearching(true)
    try {
      const body = JSON.parse(dslQuery)
      const res = await fetch(APIRoutes.SearchTracesDSL(selectedEndpoint), {
        method: 'POST',
        headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setDslResults(data?.data ?? data ?? [])
    } catch (e) {
      toast.error(`DSL search failed: ${e instanceof Error ? e.message : String(e)}`)
    } finally { setDslSearching(false) }
  }

  useEffect(() => { fetchTraces(1) }, [fetchTraces])

  const filtered = traces.filter((t) => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      t.name.toLowerCase().includes(q) ||
      (t.agent_id ?? '').toLowerCase().includes(q) ||
      (t.team_id  ?? '').toLowerCase().includes(q) ||
      t.trace_id.includes(q)
    )
  })

  const errCount    = traces.filter((t) => t.error_count > 0).length
  const avgDuration = traces.length > 0
    ? (traces.reduce((s, t) => s + parseFloat(t.duration ?? '0'), 0) / traces.length).toFixed(1)
    : '0'

  // ── Detail view ───────────────────────────────────────────────────────────
  if (selectedTrace) {
    return (
      <motion.div className="h-full overflow-hidden" {...PAGE_TRANSITION}>
        <TraceDetailView traceId={selectedTrace} onBack={() => setSelectedTrace(null)} />
      </motion.div>
    )
  }

  // ── List view ─────────────────────────────────────────────────────────────
  return (
    <motion.div className="h-full overflow-y-auto p-6" {...PAGE_TRANSITION}>
      <div className="mx-auto max-w-5xl space-y-6">

        <div className="flex items-start justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-medium text-primary">
              <Activity className="size-5 text-brand" />Traces
            </h1>
            <p className="mt-1 text-xs text-muted">Full observability of every agent run — spans, tokens, errors, I/O</p>
          </div>
          <Button size="sm" variant="outline" onClick={() => fetchTraces(1)} disabled={loading} className="gap-1.5">
            <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />Refresh
          </Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)
          ) : (
            <>
              <div className="rounded-xl border border-accent bg-primaryAccent p-3">
                <div className="text-xs text-muted uppercase tracking-wide">Runs</div>
                <div className="text-2xl font-semibold text-primary">{traces.length}</div>
              </div>
              <div className="rounded-xl border border-destructive/30 bg-primaryAccent p-3">
                <div className="text-xs text-destructive uppercase tracking-wide">With Errors</div>
                <div className="text-2xl font-semibold text-destructive">{errCount}</div>
              </div>
              <div className="rounded-xl border border-accent bg-primaryAccent p-3">
                <div className="text-xs text-muted uppercase tracking-wide">Avg Duration</div>
                <div className="text-2xl font-semibold text-primary">{avgDuration}s</div>
              </div>
            </>
          )}
        </div>

        {/* Search + filter */}
        <div className="space-y-2">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name, agent, team, trace ID…"
                disabled={dslMode}
                className="w-full rounded-xl border border-accent bg-primaryAccent pl-8 pr-3 py-2 text-xs text-primary outline-none focus:border-primary/30 disabled:opacity-50"
              />
            </div>
            <div className="flex gap-1 rounded-xl border border-accent bg-primaryAccent p-1">
              {(['all', 'OK', 'ERROR'] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  disabled={dslMode}
                  className={cn(
                    'rounded-lg px-3 py-1 text-xs font-medium uppercase transition-colors disabled:opacity-40',
                    filter === f ? 'bg-accent text-primary' : 'text-muted hover:text-primary'
                  )}
                >
                  {f}
                </button>
              ))}
            </div>
            <Button
              size="sm"
              variant={dslMode ? 'default' : 'outline'}
              onClick={() => { setDslMode(!dslMode); setDslResults(null) }}
              className="gap-1.5 text-xs"
            >
              DSL
            </Button>
          </div>

          {dslMode && (
            <div className="rounded-xl border border-brand/30 bg-primaryAccent p-3 space-y-2">
              <div className="text-xs text-muted">JSON filter query — send POST to <code>/traces/search</code></div>
              <textarea
                value={dslQuery}
                onChange={(e) => setDslQuery(e.target.value)}
                rows={6}
                className="w-full rounded-xl border border-accent bg-background px-3 py-2 font-mono text-xs text-primary outline-none resize-y focus:border-primary/30"
                placeholder='{"filters":[{"field":"status","operator":"eq","value":"ERROR"}],"limit":20}'
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={handleDslSearch} disabled={dslSearching} className="gap-1.5">
                  {dslSearching ? <RefreshCw className="size-3.5 animate-spin" /> : <Search className="size-3.5" />}
                  {dslSearching ? 'Searching…' : 'Run DSL Search'}
                </Button>
                {dslResults !== null && (
                  <Button size="sm" variant="outline" onClick={() => setDslResults(null)}>Clear Results</Button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* List */}
        <div className="space-y-2">
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)
          ) : (dslResults !== null ? dslResults : filtered).length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-accent bg-primaryAccent py-16 text-center">
              <Activity className="size-10 text-muted/20" />
              <p className="mt-3 text-sm font-medium text-muted">No traces found</p>
              <p className="mt-1 text-xs text-muted/60">Traces are recorded every time an agent or team runs.</p>
            </div>
          ) : (
            (dslResults !== null ? dslResults : filtered).map((t) => (
              <TraceCard key={t.trace_id} trace={t} onClick={() => setSelectedTrace(t.trace_id)} />
            ))
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between text-xs text-muted">
            <span>Page {page} of {totalPages}</span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => fetchTraces(page - 1)}>Previous</Button>
              <Button size="sm" variant="outline" disabled={page >= totalPages} onClick={() => fetchTraces(page + 1)}>Next</Button>
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="flex flex-wrap gap-4 text-xs text-muted/60">
          <span className="flex items-center gap-1"><Hash className="size-3" />Trace ID = full run</span>
          <span className="flex items-center gap-1"><Cpu className="size-3" />LLM spans show ⊙ token counts</span>
          <span className="flex items-center gap-1"><Bot className="size-3" />AGENT</span>
          <span className="flex items-center gap-1"><Wrench className="size-3" />TOOL</span>
        </div>
      </div>
    </motion.div>
  )
}