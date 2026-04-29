'use client'
import { motion } from 'framer-motion'
import { useEffect, useState, useCallback } from 'react'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { BarChart2, RefreshCw, Cpu, Users, Bot, Activity } from 'lucide-react'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface TokenMetrics {
  input_tokens: number
  total_tokens: number
  output_tokens: number
  reasoning_tokens: number
  cache_read_tokens: number
  cache_write_tokens: number
}

interface ModelMetric {
  count: number
  model_id: string
  model_provider: string
}

interface MetricEntry {
  id: string
  date: string
  agent_runs_count: number
  agent_sessions_count: number
  team_runs_count: number
  team_sessions_count: number
  workflow_runs_count: number
  workflow_sessions_count: number
  users_count: number
  token_metrics: TokenMetrics
  model_metrics: ModelMetric[]
  created_at: string
  updated_at: string
}

interface MetricsResponse {
  metrics: MetricEntry[]
  updated_at: string | null
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const formatNum = (n: number): string => {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

/** Build a 30-day padded series for sparklines (day 0 = 30 days ago, day 29 = today). */
const buildSeries = (entries: MetricEntry[], getValue: (e: MetricEntry) => number): number[] => {
  const today = dayjs().startOf('day')
  const series = Array(30).fill(0)
  for (const entry of entries) {
    const d = dayjs(entry.date).startOf('day')
    const diff = today.diff(d, 'day')
    if (diff >= 0 && diff < 30) {
      series[29 - diff] = getValue(entry)
    }
  }
  return series
}

// ---------------------------------------------------------------------------
// Sparkline (pure SVG, zero dependencies)
// ---------------------------------------------------------------------------
const Sparkline = ({ data, color, id }: { data: number[]; color: string; id: string }) => {
  const hasData = data.some((v) => v > 0)
  const W = 200
  const H = 52
  const PADY = 6
  const gradId = `spark-${id}`

  if (!hasData) {
    return (
      <div className="flex flex-col items-center justify-center gap-1.5 py-3">
        <div
          className="h-8 w-full rounded"
          style={{
            background: 'repeating-linear-gradient(90deg, rgba(255,255,255,0.03) 0px, rgba(255,255,255,0.03) 1px, transparent 1px, transparent 14px)',
            backgroundColor: 'rgba(255,255,255,0.02)',
          }}
        />
        <p className="text-center text-xs uppercase tracking-widest text-muted/40">No data available yet</p>
      </div>
    )
  }

  const max = Math.max(...data, 1)
  const n = data.length
  const pts = data.map((v, i) => ({
    x: (i / (n - 1)) * W,
    y: H - PADY - (v / max) * (H - PADY * 2),
  }))

  const linePath = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const areaPath = `${linePath} L${W},${H} L0,${H} Z`
  const xLabels = [1, 8, 15, 22, 29]

  return (
    <svg viewBox={`0 0 ${W} ${H + 16}`} className="w-full" style={{ height: '72px' }} aria-hidden>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {/* Subtle grid */}
      {[0.33, 0.66].map((f) => {
        const y = (H - PADY) * (1 - f) + PADY
        return (
          <line key={f} x1="0" y1={y.toFixed(1)} x2={W} y2={y.toFixed(1)}
            stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
        )
      })}
      <path d={areaPath} fill={`url(#${gradId})`} />
      <path d={linePath} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      {/* X-axis labels */}
      {xLabels.map((day) => {
        const idx = day - 1
        const x = (idx / (n - 1)) * W
        return (
          <text key={day} x={x.toFixed(1)} y={(H + 13).toFixed(1)}
            textAnchor="middle" fontSize="9" fill="#52525B">
            {day}
          </text>
        )
      })}
    </svg>
  )
}

// ---------------------------------------------------------------------------
// Stat card config
// ---------------------------------------------------------------------------
const CARDS = [
  { key: 'total_tokens',      label: 'Total tokens',      color: '#3B82F6', getValue: (e: MetricEntry) => e.token_metrics.total_tokens,   format: formatNum },
  { key: 'users',             label: 'Users',             color: '#22C55E', getValue: (e: MetricEntry) => e.users_count,                  format: formatNum },
  { key: 'agent_runs',        label: 'Agent Runs',        color: '#FF4017', getValue: (e: MetricEntry) => e.agent_runs_count,             format: formatNum },
  { key: 'agent_sessions',    label: 'Agent Sessions',    color: '#F59E0B', getValue: (e: MetricEntry) => e.agent_sessions_count,        format: formatNum },
  { key: 'team_runs',         label: 'Team Runs',         color: '#8B5CF6', getValue: (e: MetricEntry) => e.team_runs_count,             format: formatNum },
  { key: 'team_sessions',     label: 'Team Sessions',     color: '#EC4899', getValue: (e: MetricEntry) => e.team_sessions_count,        format: formatNum },
  { key: 'workflow_runs',     label: 'Workflow Runs',     color: '#06B6D4', getValue: (e: MetricEntry) => e.workflow_runs_count,         format: formatNum },
  { key: 'workflow_sessions', label: 'Workflow Sessions', color: '#10B981', getValue: (e: MetricEntry) => e.workflow_sessions_count,     format: formatNum },
] as const

// ---------------------------------------------------------------------------
// MetricCard — stat + sparkline
// ---------------------------------------------------------------------------
const MetricCard = ({ card, entries }: { card: typeof CARDS[number]; entries: MetricEntry[] }) => {
  const latest  = entries.length > 0 ? entries[entries.length - 1] : null
  const current = latest ? card.getValue(latest) : 0
  const series  = buildSeries(entries, card.getValue)

  return (
    <div className="rounded-xl border border-accent bg-primaryAccent overflow-hidden">
      <div className="px-4 pt-4 pb-1 flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted">{card.label}</p>
          <p className="mt-0.5 text-2xl font-semibold text-primary">{card.format(current)}</p>
        </div>
        <div className="size-2 rounded-full mt-2" style={{ backgroundColor: card.color }} />
      </div>
      <div className="px-3 pb-2">
        <Sparkline data={series} color={card.color} id={card.key} />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// ModelRunsCard — horizontal bar per model
// ---------------------------------------------------------------------------
const MODEL_COLORS = ['#3B82F6', '#22C55E', '#F59E0B', '#EC4899', '#8B5CF6', '#06B6D4', '#10B981', '#FF4017']

const ModelRunsCard = ({ entries }: { entries: MetricEntry[] }) => {
  const latest = entries.length > 0 ? entries[entries.length - 1] : null
  const models = latest?.model_metrics ?? []
  const total  = models.reduce((s, m) => s + m.count, 0)

  return (
    <div className="rounded-xl border border-accent bg-primaryAccent overflow-hidden">
      <div className="px-4 pt-4 pb-3 flex items-center gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted">Model Runs</p>
          <p className="mt-0.5 text-2xl font-semibold text-primary">{formatNum(total)}</p>
        </div>
        {models.length > 0 && (
          <div className="ml-auto flex items-center gap-1 rounded-lg border border-accent bg-accent/30 px-2 py-1 text-xs font-medium text-muted">
            <Activity className="size-3" />
            {models.length} model{models.length !== 1 ? 's' : ''}
          </div>
        )}
      </div>

      {models.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-1.5 px-4 pb-6">
          <div
            className="h-8 w-full rounded"
            style={{
              background: 'repeating-linear-gradient(90deg, rgba(255,255,255,0.03) 0px, rgba(255,255,255,0.03) 1px, transparent 1px, transparent 14px)',
              backgroundColor: 'rgba(255,255,255,0.02)',
            }}
          />
          <p className="text-xs uppercase tracking-widest text-muted/40">No data available yet</p>
        </div>
      ) : (
        <div className="px-4 pb-4 space-y-3">
          {models.map((m, i) => {
            const pct   = total > 0 ? (m.count / total) * 100 : 0
            const color = MODEL_COLORS[i % MODEL_COLORS.length]
            const label = m.model_id.length > 16 ? m.model_id.slice(0, 14) + '…' : m.model_id
            return (
              <div key={m.model_id}>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <div className="size-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
                    <span className="text-xs font-mono text-primary" title={m.model_id}>{label}</span>
                    <span className="text-xs text-muted/60">{m.model_provider}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted">{m.count} runs</span>
                    <span className="w-8 text-right text-xs font-semibold text-primary">{pct.toFixed(0)}%</span>
                  </div>
                </div>
                <div className="h-1.5 w-full rounded-full bg-accent/60 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{ width: `${pct}%`, backgroundColor: color }}
                  />
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
// TokenBreakdownCard
// ---------------------------------------------------------------------------
const TokenBreakdownCard = ({ entries }: { entries: MetricEntry[] }) => {
  const latest = entries.length > 0 ? entries[entries.length - 1] : null
  const tm     = latest?.token_metrics
  const total  = tm?.total_tokens ?? 0

  const rows = [
    { label: 'Input',      value: tm?.input_tokens    ?? 0, color: '#3B82F6' },
    { label: 'Output',     value: tm?.output_tokens   ?? 0, color: '#22C55E' },
    { label: 'Cache read', value: tm?.cache_read_tokens ?? 0, color: '#F59E0B' },
    { label: 'Cache write',value: tm?.cache_write_tokens ?? 0, color: '#8B5CF6' },
    { label: 'Reasoning',  value: tm?.reasoning_tokens ?? 0, color: '#EC4899' },
  ].filter((r) => r.value > 0)

  return (
    <div className="rounded-xl border border-accent bg-primaryAccent overflow-hidden">
      <div className="px-4 pt-4 pb-3">
        <p className="text-xs font-medium uppercase tracking-wide text-muted">Token Breakdown</p>
        <p className="mt-0.5 text-2xl font-semibold text-primary">{formatNum(total)}</p>
      </div>

      {rows.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-1.5 px-4 pb-6">
          <div
            className="h-8 w-full rounded"
            style={{
              background: 'repeating-linear-gradient(90deg, rgba(255,255,255,0.03) 0px, rgba(255,255,255,0.03) 1px, transparent 1px, transparent 14px)',
              backgroundColor: 'rgba(255,255,255,0.02)',
            }}
          />
          <p className="text-xs uppercase tracking-widest text-muted/40">No data available yet</p>
        </div>
      ) : (
        <div className="px-4 pb-4 space-y-3">
          {rows.map((r) => {
            const pct = total > 0 ? (r.value / total) * 100 : 0
            return (
              <div key={r.label}>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <div className="size-2.5 rounded-full shrink-0" style={{ backgroundColor: r.color }} />
                    <span className="text-xs text-muted">{r.label}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted">{formatNum(r.value)}</span>
                    <span className="w-10 text-right text-xs font-semibold text-primary">{pct.toFixed(1)}%</span>
                  </div>
                </div>
                <div className="h-1.5 w-full rounded-full bg-accent/60 overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${pct}%`, backgroundColor: r.color }}
                  />
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
// MetricsPage — main export
// ---------------------------------------------------------------------------
export default function MetricsPage() {
  const { selectedEndpoint, authToken } = useStore()
  const [data, setData]           = useState<MetricsResponse | null>(null)
  const [loading, setLoading]     = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError]         = useState<string | null>(null)

  // Date range filter (YYYY-MM-DD)
  const defaultEnd   = dayjs().format('YYYY-MM-DD')
  const defaultStart = dayjs().subtract(29, 'day').format('YYYY-MM-DD')
  const [startDate, setStartDate] = useState(defaultStart)
  const [endDate, setEndDate]     = useState(defaultEnd)

  const headers: Record<string, string> = {}
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`

  // GET /metrics — read pre-computed metrics for the selected date range
  const fetchMetrics = useCallback(async (start = startDate, end = endDate) => {
    if (!selectedEndpoint) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(APIRoutes.Metrics(selectedEndpoint, start, end), { headers })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.detail ?? `HTTP ${res.status}`)
      }
      const json = await res.json()
      // Agno returns { metrics: [...], updated_at: "..." }
      // Guard against both shapes just in case
      setData(Array.isArray(json) ? { metrics: json, updated_at: null } : json)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load metrics')
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedEndpoint, authToken, startDate, endDate])

  // POST /metrics/refresh — trigger recalculation, then update state from response
  const recalculate = useCallback(async () => {
    if (!selectedEndpoint) return
    setRefreshing(true)
    setError(null)
    try {
      const res = await fetch(APIRoutes.MetricsRefresh(selectedEndpoint), {
        method: 'POST',
        headers,
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.detail ?? `HTTP ${res.status}`)
      }
      // POST /metrics/refresh returns DayAggregatedMetrics[] directly
      const fresh: MetricEntry[] = await res.json()
      setData({ metrics: fresh, updated_at: new Date().toISOString() })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Recalculation failed')
    } finally {
      setRefreshing(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedEndpoint, authToken])

  useEffect(() => { fetchMetrics() }, [fetchMetrics])

  const entries = data?.metrics ?? []
  const latest  = entries.length > 0 ? entries[entries.length - 1] : null

  return (
    <motion.div className="h-full overflow-y-auto p-6" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2, ease: 'easeOut' }}>
      <div className="mx-auto max-w-6xl space-y-6">

        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-medium text-primary">
              <BarChart2 className="size-5 text-brand" />Metrics
            </h1>
            <p className="mt-1 text-xs text-muted">
              Daily usage statistics from{' '}
              <span className="font-mono text-muted/80">agno_metrics</span>
              {data?.updated_at && (
                <span> · updated {dayjs(data.updated_at).fromNow()}</span>
              )}
            </p>
          </div>

          {/* Controls */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Date range */}
            <div className="flex items-center gap-1.5 rounded-lg border border-accent bg-primaryAccent px-2 py-1.5 text-xs text-muted">
              <input
                type="date"
                value={startDate}
                max={endDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="bg-transparent text-xs text-primary outline-none cursor-pointer"
              />
              <span className="text-muted/50">→</span>
              <input
                type="date"
                value={endDate}
                min={startDate}
                max={dayjs().format('YYYY-MM-DD')}
                onChange={(e) => setEndDate(e.target.value)}
                className="bg-transparent text-xs text-primary outline-none cursor-pointer"
              />
              <Button
                size="sm"
                variant="ghost"
                onClick={() => fetchMetrics(startDate, endDate)}
                disabled={loading}
                className="h-5 px-1.5 text-xs"
              >
                Go
              </Button>
            </div>

            {/* Re-fetch (GET) */}
            <Button size="sm" variant="outline" onClick={() => fetchMetrics()} disabled={loading || refreshing} className="gap-1.5">
              <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />Reload
            </Button>

            {/* Recalculate (POST /metrics/refresh) */}
            <Button size="sm" variant="outline" onClick={recalculate} disabled={loading || refreshing} className="gap-1.5 border-brand/40 text-brand hover:bg-brand/10">
              <Activity className={cn('size-3.5', refreshing && 'animate-spin')} />Recalculate
            </Button>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs text-red-400">
            {error}
          </div>
        )}

        {/* Quick stat summary row */}
        {loading && !data ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
          </div>
        ) : latest ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[
              { label: 'Total Tokens', value: formatNum(latest.token_metrics.total_tokens), icon: Cpu,      color: 'text-info' },
              { label: 'Users',        value: String(latest.users_count),                   icon: Users,    color: 'text-positive' },
              { label: 'Agent Runs',   value: String(latest.agent_runs_count),              icon: Bot,      color: 'text-brand' },
              { label: 'Model Calls',  value: String(latest.model_metrics.reduce((s, m) => s + m.count, 0)), icon: Activity, color: 'text-warning' },
            ].map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="rounded-xl border border-accent bg-primaryAccent px-4 py-3">
                <div className={cn('flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide mb-1', color)}>
                  <Icon className="size-3.5" />{label}
                </div>
                <div className="text-2xl font-semibold text-primary">{value}</div>
              </div>
            ))}
          </div>
        ) : null}

        {/* Sparkline grid — 4 cols */}
        {loading && !data ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-36 rounded-xl" />)}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {CARDS.map((card) => (
              <MetricCard key={card.key} card={card} entries={entries} />
            ))}
          </div>
        )}

        {/* Bottom row: model runs + token breakdown */}
        {loading && !data ? (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-48 rounded-xl" />)}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <ModelRunsCard entries={entries} />
            <TokenBreakdownCard entries={entries} />
          </div>
        )}

        {/* Empty state */}
        {!loading && !refreshing && entries.length === 0 && !error && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-accent bg-primaryAccent py-20 text-center">
            <BarChart2 className="size-10 text-muted/20" />
            <p className="mt-3 text-sm font-medium text-muted">No metrics yet</p>
            <p className="mt-1 text-xs text-muted/60">
              Click <span className="font-semibold">Recalculate</span> to compute metrics from existing run data,
              or metrics will appear automatically as agents run.
            </p>
            <Button size="sm" variant="outline" onClick={recalculate} className="mt-4 gap-1.5 border-brand/40 text-brand hover:bg-brand/10">
              <Activity className="size-3.5" />Recalculate now
            </Button>
          </div>
        )}
      </div>
    </motion.div>
  )
}
