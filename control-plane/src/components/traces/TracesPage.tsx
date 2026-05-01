'use client'
import { useEffect, useState, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  Activity, ChevronDown, ChevronRight, RefreshCw, CheckCircle, XCircle,
  Clock, Search, AlertCircle, ArrowLeft, Cpu, Wrench, Bot, Copy,
  Filter, SlidersHorizontal, TrendingUp
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
          <div className="text-[10px] uppercase tracking-wide text-muted">{label}</div>
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
      <div className="flex items-center gap-3 border-b border-accent px-4 py-3 shrink-0">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-muted hover:bg-accent hover:text-primary transition-colors"
        >
          <ArrowLeft className="size-3.5" />
          All Traces
        </button>
        <div className="h-4 w-px bg-accent" />
        <StatusIcon status={trace.status} />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-primary truncate">{trace.name}</div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted mt-0.5">
            <span>{parseFloat(trace.duration ?? '0').toFixed(2)}s</span>
            <span className="text-muted/30">·</span>
            <span>{trace.total_spans} spans</span>
            <span className="text-muted/30">·</span>
            <span>{dayjs(trace.start_time).format('D MMM HH:mm:ss')}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {trace.agent_id && (
            <span className="rounded-full border border-brand/30 bg-brand/10 px-2 py-0.5 text-xs font-medium text-brand">{trace.agent_id}</span>
          )}
          {trace.team_id && (
            <span className="rounded-full border border-info/30 bg-info/10 px-2 py-0.5 text-xs font-medium text-info">{trace.team_id}</span>
          )}
          {trace.error_count > 0 && (
            <span className="flex items-center gap-1 rounded-full bg-destructive/10 px-2 py-0.5 text-xs text-destructive">
              <AlertCircle className="size-3" />{trace.error_count} error{trace.error_count > 1 ? 's' : ''}
            </span>
          )}
          <button
            onClick={fetchDetail}
            className="rounded-lg p-1.5 text-muted hover:bg-accent hover:text-primary"
            title="Refresh"
          >
            <RefreshCw className="size-3.5" />
          </button>
        </div>
      </div>

      {/* Metadata chips */}
      <div className="flex flex-wrap gap-2 px-4 py-2.5 border-b border-accent shrink-0 bg-background/30">
        {[
          { label: 'Trace ID',   value: trace.trace_id },
          { label: 'Run ID',     value: trace.run_id ?? null },
          { label: 'Session',    value: trace.session_id ?? null },
          { label: 'Created',    value: dayjs(trace.created_at).format('D MMM YYYY, HH:mm:ss'), noCopy: true },
        ].filter((m) => m.value !== null).map(({ label, value, noCopy }) => (
          <div
            key={label}
            className={cn(
              'flex items-center gap-1.5 rounded-lg bg-accent/50 px-2.5 py-1 text-xs',
              !noCopy && 'cursor-pointer hover:bg-accent/80'
            )}
            onClick={() => !noCopy && value && copyText(value!)}
            title={!noCopy ? 'Click to copy' : undefined}
          >
            <span className="text-muted/60">{label}:</span>
            <span className="font-mono text-primary truncate max-w-[140px]">{value}</span>
            {!noCopy && <Copy className="size-2.5 text-muted/40 shrink-0" />}
          </div>
        ))}
      </div>

      {/* Main area: tree + span detail */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: span tree */}
        <div className={cn('flex flex-col border-r border-accent overflow-hidden', activeSpan ? 'w-1/2' : 'flex-1')}>
          {/* View mode tabs */}
          <div className="flex items-center gap-1 border-b border-accent px-3 py-2 shrink-0 bg-background/20">
            <span className="mr-1 text-[10px] uppercase tracking-wide text-muted/50 font-semibold">View</span>
            {(['tree', 'timeline'] as const).map((m) => (
              <button
                key={m}
                onClick={() => setViewMode(m)}
                className={cn(
                  'rounded-lg px-2.5 py-1 text-xs font-medium capitalize transition-colors',
                  viewMode === m ? 'bg-accent text-primary' : 'text-muted hover:text-primary'
                )}
              >
                {m === 'tree' ? '🌲 Tree' : '⏱ Timeline'}
              </button>
            ))}
            <div className="ml-auto flex items-center gap-3 text-[10px] text-muted/50">
              <span className="flex items-center gap-1"><Cpu className="size-2.5 text-info" /> LLM</span>
              <span className="flex items-center gap-1"><Wrench className="size-2.5 text-warning" /> Tool</span>
              <span className="flex items-center gap-1"><Bot className="size-2.5 text-brand" /> Agent</span>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {(trace.tree ?? []).length === 0 ? (
              <div className="flex items-center justify-center py-12 text-xs text-muted/50">No spans recorded</div>
            ) : (trace.tree ?? []).map((span) => (
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
              <div className="rounded-xl border border-accent/50 bg-accent/20 px-4 py-3 text-xs text-muted">
                👆 Click any span in the tree to inspect its input, output, tokens, and metadata.
              </div>
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
const TraceCard = ({ trace, onClick }: { trace: TraceSummary; onClick: () => void }) => {
  const dur = parseFloat(trace.duration ?? '0')
  const isError = trace.error_count > 0

  return (
    <div
      onClick={onClick}
      className={cn(
        'cursor-pointer rounded-xl border bg-primaryAccent p-4 transition-all hover:shadow-sm',
        isError
          ? 'border-destructive/30 hover:border-destructive/50'
          : 'border-accent hover:border-primary/20'
      )}
    >
      <div className="flex items-start gap-3">
        {/* Status */}
        <div className="mt-0.5 shrink-0">
          <StatusIcon status={trace.status} />
        </div>

        {/* Main info */}
        <div className="flex-1 min-w-0">
          {/* Name + badges */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-sm font-semibold text-primary truncate max-w-xs">{trace.name}</span>
            {trace.agent_id && (
              <span className="rounded-full border border-brand/30 bg-brand/10 px-1.5 py-0.5 text-[10px] font-medium text-brand">{trace.agent_id}</span>
            )}
            {trace.team_id && (
              <span className="rounded-full border border-info/30 bg-info/10 px-1.5 py-0.5 text-[10px] font-medium text-info">{trace.team_id}</span>
            )}
            {isError && (
              <span className="flex items-center gap-0.5 rounded-full bg-destructive/10 px-1.5 py-0.5 text-[10px] text-destructive">
                <AlertCircle className="size-2.5" />{trace.error_count} error{trace.error_count > 1 ? 's' : ''}
              </span>
            )}
          </div>

          {/* Meta row */}
          <div className="mt-1.5 flex flex-wrap items-center gap-3 text-xs text-muted">
            <span title={dayjs(trace.start_time).format('D MMM YYYY HH:mm:ss')}>
              {dayjs(trace.start_time).fromNow()}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="size-3" />{dur.toFixed(2)}s
            </span>
            <span className="flex items-center gap-1">
              <Activity className="size-3" />{trace.total_spans} spans
            </span>
          </div>

          {/* Input preview */}
          {trace.input && (
            <div className="mt-2 rounded-lg bg-accent/30 px-2.5 py-1.5 text-xs text-muted/70 font-mono truncate">
              {trace.input.slice(0, 140)}{trace.input.length > 140 ? '…' : ''}
            </div>
          )}
        </div>

        <ChevronRight className="size-4 shrink-0 text-muted/30 mt-1" />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// TracesPage — main export
// ---------------------------------------------------------------------------
export default function TracesPage() {
  const { selectedEndpoint, authToken } = useStore()
  const [traces, setTraces]   = useState<TraceSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch]   = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'OK' | 'ERROR'>('all')
  const [agentFilter, setAgentFilter]   = useState<string>('all')
  const [selectedTrace, setSelectedTrace] = useState<string | null>(null)
  const [page, setPage]       = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  // Advanced DSL (power users)
  const [showAdvanced, setShowAdvanced] = useState(false)
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
      if (statusFilter !== 'all') url.searchParams.set('status', statusFilter)
      const res = await fetch(url.toString(), { headers: authHeaders })
      if (!res.ok) throw new Error(res.statusText)
      const data = await res.json()
      setTraces(data?.data ?? [])
      setTotalPages(data?.meta?.total_pages ?? 1)
      setPage(pg)
    } catch { /* silently handled */ }
    finally { setLoading(false) }
  }, [selectedEndpoint, authToken, statusFilter])

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

  // Derived values
  const agentIds = useMemo(() => {
    const ids = new Set<string>()
    traces.forEach((t) => { if (t.agent_id) ids.add(t.agent_id); if (t.team_id) ids.add(t.team_id) })
    return Array.from(ids).sort()
  }, [traces])

  const filtered = useMemo(() => {
    const source = dslResults !== null ? dslResults : traces
    return source.filter((t) => {
      if (agentFilter !== 'all' && t.agent_id !== agentFilter && t.team_id !== agentFilter) return false
      if (!search) return true
      const q = search.toLowerCase()
      return (
        t.name.toLowerCase().includes(q) ||
        (t.agent_id ?? '').toLowerCase().includes(q) ||
        (t.team_id  ?? '').toLowerCase().includes(q) ||
        t.trace_id.includes(q) ||
        (t.input ?? '').toLowerCase().includes(q)
      )
    })
  }, [traces, dslResults, search, agentFilter])

  const okCount  = traces.filter((t) => t.status === 'OK').length
  const errCount = traces.filter((t) => t.status === 'ERROR').length
  const successRate = traces.length > 0 ? Math.round((okCount / traces.length) * 100) : null
  const avgDuration = traces.length > 0
    ? (traces.reduce((s, t) => s + parseFloat(t.duration ?? '0'), 0) / traces.length).toFixed(1)
    : null

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
    <motion.div className="flex h-full flex-col overflow-hidden" {...PAGE_TRANSITION}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-accent/50 px-6 py-4 shrink-0">
        <div>
          <h1 className="flex items-center gap-2 text-base font-semibold text-primary">
            <Activity className="size-4 text-brand" />Traces
          </h1>
          <p className="mt-0.5 text-xs text-muted">Full observability — every agent run, span, token, and error</p>
        </div>
        <Button size="sm" variant="outline" onClick={() => fetchTraces(1)} disabled={loading} className="gap-1.5 h-8 text-xs">
          <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />Refresh
        </Button>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-4 gap-3 px-6 py-3 border-b border-accent/50 shrink-0">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-14 rounded-xl" />)
        ) : (
          <>
            <div className="rounded-xl border border-accent bg-primaryAccent px-4 py-2.5">
              <div className="text-[10px] font-semibold uppercase tracking-wide text-muted/60">Total Runs</div>
              <div className="mt-0.5 text-2xl font-bold text-primary">{traces.length}</div>
            </div>
            <div className={cn(
              'rounded-xl border px-4 py-2.5',
              successRate !== null && successRate >= 90 ? 'border-positive/30 bg-positive/5' :
              successRate !== null && successRate >= 70 ? 'border-warning/30 bg-warning/5' :
              'border-accent bg-primaryAccent'
            )}>
              <div className="text-[10px] font-semibold uppercase tracking-wide text-muted/60">Success Rate</div>
              <div className={cn(
                'mt-0.5 text-2xl font-bold',
                successRate !== null && successRate >= 90 ? 'text-positive' :
                successRate !== null && successRate >= 70 ? 'text-warning' : 'text-primary'
              )}>
                {successRate !== null ? `${successRate}%` : '—'}
              </div>
            </div>
            <div className={cn(
              'rounded-xl border px-4 py-2.5',
              errCount > 0 ? 'border-destructive/30 bg-destructive/5' : 'border-accent bg-primaryAccent'
            )}>
              <div className="text-[10px] font-semibold uppercase tracking-wide text-muted/60">With Errors</div>
              <div className={cn('mt-0.5 text-2xl font-bold', errCount > 0 ? 'text-destructive' : 'text-primary')}>
                {errCount}
              </div>
            </div>
            <div className="rounded-xl border border-accent bg-primaryAccent px-4 py-2.5">
              <div className="text-[10px] font-semibold uppercase tracking-wide text-muted/60">Avg Duration</div>
              <div className="mt-0.5 text-2xl font-bold text-primary">{avgDuration !== null ? `${avgDuration}s` : '—'}</div>
            </div>
          </>
        )}
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2 px-6 py-3 border-b border-accent/50 shrink-0 bg-background/30">
        {/* Text search */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted/50" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name, agent, input…"
            className="w-full rounded-xl border border-accent bg-primaryAccent pl-8 pr-3 py-1.5 text-xs text-primary outline-none focus:border-primary/30 placeholder:text-muted/40"
          />
        </div>

        {/* Status filter pills */}
        <div className="flex items-center gap-1 rounded-xl border border-accent bg-primaryAccent p-1">
          {([
            { id: 'all',   label: 'All',    count: traces.length },
            { id: 'OK',    label: '✓ OK',   count: okCount },
            { id: 'ERROR', label: '✗ Error', count: errCount },
          ] as const).map((f) => (
            <button
              key={f.id}
              onClick={() => setStatusFilter(f.id)}
              className={cn(
                'flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors',
                statusFilter === f.id ? 'bg-accent text-primary' : 'text-muted hover:text-primary'
              )}
            >
              {f.label}
              {f.count > 0 && (
                <span className={cn(
                  'rounded-full px-1 py-0.5 text-[9px] font-semibold leading-none',
                  statusFilter === f.id
                    ? f.id === 'ERROR' ? 'bg-destructive/20 text-destructive' : 'bg-primary/10 text-primary'
                    : 'bg-accent text-muted/60'
                )}>
                  {f.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Agent / team filter */}
        {agentIds.length > 0 && (
          <div className="flex items-center gap-1.5 rounded-xl border border-accent bg-primaryAccent px-2 py-1">
            <Filter className="size-3 text-muted/50 shrink-0" />
            <select
              value={agentFilter}
              onChange={(e) => setAgentFilter(e.target.value)}
              className="bg-transparent text-xs text-primary outline-none cursor-pointer"
            >
              <option value="all">All agents</option>
              {agentIds.map((id) => <option key={id} value={id}>{id}</option>)}
            </select>
          </div>
        )}

        {/* Advanced toggle */}
        <button
          onClick={() => { setShowAdvanced(!showAdvanced); setDslResults(null) }}
          className={cn(
            'ml-auto flex items-center gap-1.5 rounded-xl border px-2.5 py-1.5 text-xs font-medium transition-colors',
            showAdvanced
              ? 'border-brand/30 bg-brand/10 text-brand'
              : 'border-accent bg-primaryAccent text-muted hover:text-primary'
          )}
        >
          <SlidersHorizontal className="size-3" />
          Advanced
        </button>
      </div>

      {/* Advanced DSL panel */}
      <AnimatePresence>
        {showAdvanced && (
          <motion.div
            initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.15 }}
            className="overflow-hidden border-b border-brand/20 bg-brand/5 shrink-0"
          >
            <div className="px-6 py-4 space-y-2">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-semibold text-primary">DSL Filter Query</p>
                  <p className="text-[10px] text-muted mt-0.5">POST to <code className="font-mono">/traces/search</code> — useful for precise filtering by agent, date range, session ID, etc.</p>
                </div>
                {dslResults !== null && (
                  <button
                    onClick={() => setDslResults(null)}
                    className="rounded-lg border border-accent px-2 py-1 text-[10px] text-muted hover:bg-accent"
                  >
                    Clear Results
                  </button>
                )}
              </div>
              <textarea
                value={dslQuery}
                onChange={(e) => setDslQuery(e.target.value)}
                rows={4}
                className="w-full rounded-xl border border-accent bg-background px-3 py-2 font-mono text-xs text-primary outline-none resize-y focus:border-brand/30"
                placeholder='{"filters":[{"field":"status","operator":"eq","value":"ERROR"}],"limit":20}'
              />
              <Button size="sm" onClick={handleDslSearch} disabled={dslSearching} className="gap-1.5 h-7 text-xs">
                {dslSearching ? <RefreshCw className="size-3 animate-spin" /> : <Search className="size-3" />}
                {dslSearching ? 'Searching…' : 'Run Query'}
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Trace list */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="mx-auto max-w-4xl space-y-2">
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-accent bg-primaryAccent py-16 text-center">
              <Activity className="size-10 text-muted/20 mb-3" />
              <p className="text-sm font-medium text-muted">No traces found</p>
              <p className="mt-1 text-xs text-muted/50">
                {search || agentFilter !== 'all' || statusFilter !== 'all'
                  ? 'Try adjusting your filters'
                  : 'Traces appear here when agents run via Chat or a workflow trigger'}
              </p>
              {(search || agentFilter !== 'all' || statusFilter !== 'all') && (
                <button
                  onClick={() => { setSearch(''); setAgentFilter('all'); setStatusFilter('all') }}
                  className="mt-3 rounded-xl border border-accent px-3 py-1.5 text-xs text-muted hover:bg-accent hover:text-primary"
                >
                  Clear filters
                </button>
              )}
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between pb-1">
                <p className="text-xs text-muted/60">
                  {dslResults !== null ? `${filtered.length} DSL results` : `${filtered.length} of ${traces.length} traces`}
                  {agentFilter !== 'all' && <span className="ml-1 text-brand">· filtered by {agentFilter}</span>}
                </p>
                <div className="flex items-center gap-1 text-[10px] text-muted/40">
                  <Cpu className="size-2.5 text-info" />LLM
                  <Bot className="ml-1.5 size-2.5 text-brand" />Agent
                  <Wrench className="ml-1.5 size-2.5 text-warning" />Tool
                </div>
              </div>
              {filtered.map((t) => (
                <TraceCard key={t.trace_id} trace={t} onClick={() => setSelectedTrace(t.trace_id)} />
              ))}
            </>
          )}
        </div>

        {/* Pagination */}
        {!loading && totalPages > 1 && dslResults === null && (
          <div className="mx-auto mt-4 flex max-w-4xl items-center justify-between text-xs text-muted">
            <span>Page {page} of {totalPages}</span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => fetchTraces(page - 1)} className="h-7 text-xs">← Previous</Button>
              <Button size="sm" variant="outline" disabled={page >= totalPages} onClick={() => fetchTraces(page + 1)} className="h-7 text-xs">Next →</Button>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}
