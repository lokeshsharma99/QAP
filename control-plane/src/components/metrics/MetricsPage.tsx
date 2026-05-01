'use client'
import { motion } from 'framer-motion'
import { useEffect, useState, useCallback } from 'react'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { BarChart2, RefreshCw, Activity, ChevronLeft, ChevronRight } from 'lucide-react'
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

/** Build a 30-day padded series aligned to selected date range */
const buildSeries = (entries: MetricEntry[], getValue: (e: MetricEntry) => number): number[] => {
  const today = dayjs().startOf('day')
  const series = Array(30).fill(0)
  for (const entry of entries) {
    const d = dayjs(entry.date).startOf('day')
    const diff = today.diff(d, 'day')
    if (diff >= 0 && diff < 30) series[29 - diff] = getValue(entry)
  }
  return series
}

const CHART_COLORS = ['#3B82F6', '#22C55E', '#F59E0B', '#EC4899', '#8B5CF6', '#06B6D4', '#10B981', '#FF4017']

// ---------------------------------------------------------------------------
// Sparkline — area line chart with x-axis day labels + y-axis value labels
// ---------------------------------------------------------------------------
const Sparkline = ({ data, color, id, format }: { data: number[]; color: string; id: string; format: (n: number) => string }) => {
  const hasData = data.some((v) => v > 0)
  const Y_LABEL_W = 34   // left margin reserved for y-axis labels
  const W = 200; const H = 56; const PADY = 8
  const totalW = W + Y_LABEL_W
  const gradId = `spark-${id}`

  if (!hasData) return (
    <div className="flex flex-col items-center justify-center gap-1.5 py-3">
      <div className="h-8 w-full rounded" style={{
        background: 'repeating-linear-gradient(90deg,rgba(255,255,255,0.04) 0,rgba(255,255,255,0.04) 1px,transparent 1px,transparent 14px)',
        backgroundColor: 'rgba(255,255,255,0.02)',
      }} />
      <p className="text-center text-[10px] uppercase tracking-widest text-muted/40">No data yet</p>
    </div>
  )

  const max = Math.max(...data, 1); const n = data.length
  // 4 y-axis ticks: 0, 33%, 66%, 100% of max
  const yTicks = [0, 0.33, 0.66, 1].map((f) => ({ value: f * max, y: H - PADY - f * (H - PADY * 2) }))

  const toX = (i: number) => Y_LABEL_W + (i / (n - 1)) * W
  const toY = (v: number) => H - PADY - (v / max) * (H - PADY * 2)

  const pts = data.map((v, i) => ({ x: toX(i), y: toY(v) }))
  const linePath = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const areaPath = `${linePath} L${toX(n - 1)},${H} L${toX(0)},${H} Z`

  return (
    <svg viewBox={`0 0 ${totalW} ${H + 16}`} className="w-full" style={{ height: '84px' }} aria-hidden>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {/* horizontal grid lines + y-axis labels */}
      {yTicks.map(({ value, y }, i) => (
        <g key={i}>
          <line x1={Y_LABEL_W} y1={y.toFixed(1)} x2={totalW} y2={y.toFixed(1)}
            stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
          <text x={(Y_LABEL_W - 3).toFixed(1)} y={(y + 3).toFixed(1)}
            textAnchor="end" fontSize="8" fill="#52525B">{format(value)}</text>
        </g>
      ))}
      {/* area fill + line */}
      <path d={areaPath} fill={`url(#${gradId})`} />
      <path d={linePath} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      {/* x-axis day labels */}
      {[1, 8, 15, 22, 29].map((day) => {
        const x = toX(day - 1)
        return <text key={day} x={x.toFixed(1)} y={(H + 13).toFixed(1)} textAnchor="middle" fontSize="8" fill="#52525B">{day}</text>
      })}
    </svg>
  )
}

// ---------------------------------------------------------------------------
// BarChart — vertical bar chart for 30-day trends
// ---------------------------------------------------------------------------
const BarChart = ({ data, color, id }: { data: number[]; color: string; id: string }) => {
  const hasData = data.some((v) => v > 0)
  if (!hasData) return (
    <div className="flex items-end justify-between gap-0.5 h-14 px-1">
      {data.map((_, i) => (
        <div key={i} className="flex-1 rounded-sm bg-accent/20" style={{ height: '20%' }} />
      ))}
    </div>
  )
  const max = Math.max(...data, 1)
  return (
    <div className="flex items-end justify-between gap-px h-14 px-1" title={`Max: ${max}`}>
      {data.map((v, i) => {
        const pct = (v / max) * 100
        return (
          <div
            key={i}
            className="flex-1 rounded-sm transition-all duration-300"
            style={{ height: `${Math.max(pct, 4)}%`, backgroundColor: pct > 0 ? color : 'rgba(255,255,255,0.05)', opacity: 0.7 + (pct / max) * 0.3 }}
            title={`Day ${i + 1}: ${v}`}
          />
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// DonutChart — pure SVG donut
// ---------------------------------------------------------------------------
interface DonutSlice { value: number; color: string; label: string }

const DonutChart = ({ slices, size = 120 }: { slices: DonutSlice[]; size?: number }) => {
  const total = slices.reduce((s, sl) => s + sl.value, 0)
  if (total === 0) return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size / 2} cy={size / 2} r={size * 0.38} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={size * 0.14} />
      <text x={size / 2} y={size / 2 + 4} textAnchor="middle" fontSize="10" fill="#52525B">—</text>
    </svg>
  )

  const cx = size / 2; const cy = size / 2
  const r = size * 0.38; const strokeW = size * 0.14

  // Use arc paths for reliable multi-segment rendering across all browsers
  const polarToCartesian = (angleDeg: number) => {
    const rad = ((angleDeg - 90) * Math.PI) / 180
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
  }
  const GAP_DEG = slices.length > 1 ? 1.5 : 0
  let startAngle = 0
  const paths = slices.map((sl) => {
    const fullSweep = (sl.value / total) * 360
    const sweep = Math.max(fullSweep - GAP_DEG, 0.01)
    const start = polarToCartesian(startAngle)
    const end   = polarToCartesian(startAngle + sweep)
    const largeArc = sweep > 180 ? 1 : 0
    const d = `M ${start.x.toFixed(2)} ${start.y.toFixed(2)} A ${r} ${r} 0 ${largeArc} 1 ${end.x.toFixed(2)} ${end.y.toFixed(2)}`
    startAngle += fullSweep
    return { d, color: sl.color, fullCircle: sweep >= 359 }
  })

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* background ring */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={strokeW} />
      {paths.map((p, i) =>
        p.fullCircle ? (
          <circle key={i} cx={cx} cy={cy} r={r} fill="none" stroke={p.color} strokeWidth={strokeW} />
        ) : (
          <path key={i} d={p.d} fill="none" stroke={p.color} strokeWidth={strokeW} strokeLinecap="butt" />
        )
      )}
    </svg>
  )
}

// ---------------------------------------------------------------------------
// Stat card config
// ---------------------------------------------------------------------------
const CARDS = [
  { key: 'total_tokens',      label: 'Total Tokens',      color: '#3B82F6', getValue: (e: MetricEntry) => e.token_metrics.total_tokens,      format: formatNum },
  { key: 'users',             label: 'Users',             color: '#22C55E', getValue: (e: MetricEntry) => e.users_count,                     format: formatNum },
  { key: 'agent_runs',        label: 'Agent Runs',        color: '#FF4017', getValue: (e: MetricEntry) => e.agent_runs_count,                format: formatNum },
  { key: 'agent_sessions',    label: 'Agent Sessions',    color: '#F59E0B', getValue: (e: MetricEntry) => e.agent_sessions_count,           format: formatNum },
  { key: 'team_runs',         label: 'Team Runs',         color: '#8B5CF6', getValue: (e: MetricEntry) => e.team_runs_count,                format: formatNum },
  { key: 'team_sessions',     label: 'Team Sessions',     color: '#EC4899', getValue: (e: MetricEntry) => e.team_sessions_count,           format: formatNum },
  { key: 'workflow_runs',     label: 'Workflow Runs',     color: '#06B6D4', getValue: (e: MetricEntry) => e.workflow_runs_count,            format: formatNum },
  { key: 'workflow_sessions', label: 'Workflow Sessions', color: '#10B981', getValue: (e: MetricEntry) => e.workflow_sessions_count,        format: formatNum },
] as const

// ---------------------------------------------------------------------------
// MetricCard
// ---------------------------------------------------------------------------
const MetricCard = ({ card, entries }: { card: typeof CARDS[number]; entries: MetricEntry[] }) => {
  const total30 = entries.reduce((s, e) => s + card.getValue(e), 0)
  const series  = buildSeries(entries, card.getValue)

  return (
    <div className="rounded-xl border border-accent bg-primaryAccent overflow-hidden">
      <div className="px-4 pt-3 pb-0 flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wide text-muted">{card.label}</p>
        <div className="size-1.5 rounded-full" style={{ backgroundColor: card.color }} />
      </div>
      <div className="px-4 pb-1">
        <p className="text-2xl font-semibold text-primary">{card.format(total30)}</p>
      </div>
      <div className="px-2 pb-2">
        <Sparkline data={series} color={card.color} id={card.key} format={card.format} />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// ModelRunsCard — donut + horizontal bars
// ---------------------------------------------------------------------------
const ModelRunsCard = ({ entries }: { entries: MetricEntry[] }) => {
  // Aggregate across all entries in range
  const modelTotals: Record<string, { count: number; provider: string }> = {}
  for (const entry of entries) {
    for (const m of entry.model_metrics) {
      if (!modelTotals[m.model_id]) modelTotals[m.model_id] = { count: 0, provider: m.model_provider }
      modelTotals[m.model_id].count += m.count
    }
  }
  const models = Object.entries(modelTotals)
    .map(([id, v]) => ({ model_id: id, count: v.count, model_provider: v.provider }))
    .sort((a, b) => b.count - a.count)
  const total = models.reduce((s, m) => s + m.count, 0)

  const donutSlices: DonutSlice[] = models.map((m, i) => ({
    value: m.count,
    color: CHART_COLORS[i % CHART_COLORS.length],
    label: m.model_id,
  }))

  const noDataPlaceholder = (
    <div className="flex flex-col items-center justify-center gap-1.5 px-4 pb-6">
      <div className="h-8 w-full rounded" style={{
        background: 'repeating-linear-gradient(90deg,rgba(255,255,255,0.03) 0,rgba(255,255,255,0.03) 1px,transparent 1px,transparent 14px)',
        backgroundColor: 'rgba(255,255,255,0.02)',
      }} />
      <p className="text-xs uppercase tracking-widest text-muted/40">No data available yet</p>
    </div>
  )

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

      {models.length === 0 ? noDataPlaceholder : (
        <div className="px-4 pb-4">
          {/* Donut + legend row */}
          <div className="flex items-center gap-4 mb-4">
            <div className="relative shrink-0">
              <DonutChart slices={donutSlices} size={100} />
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-sm font-semibold text-primary">{formatNum(total)}</span>
                <span className="text-[9px] uppercase text-muted/60">runs</span>
              </div>
            </div>
            {/* Top 4 legend */}
            <div className="flex flex-col gap-1.5 flex-1 min-w-0">
              {models.slice(0, 4).map((m, i) => {
                const color = CHART_COLORS[i % CHART_COLORS.length]
                const pct = total > 0 ? (m.count / total) * 100 : 0
                const label = m.model_id.length > 18 ? m.model_id.slice(0, 16) + '…' : m.model_id
                return (
                  <div key={m.model_id} className="flex items-center gap-1.5 min-w-0">
                    <div className="size-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
                    <span className="text-xs font-mono text-primary truncate flex-1" title={m.model_id}>{label}</span>
                    <span className="text-xs text-muted/70 shrink-0">{pct.toFixed(0)}%</span>
                  </div>
                )
              })}
            </div>
          </div>
          {/* Horizontal bars */}
          <div className="space-y-2.5">
            {models.map((m, i) => {
              const pct = total > 0 ? (m.count / total) * 100 : 0
              const color = CHART_COLORS[i % CHART_COLORS.length]
              const label = m.model_id.length > 20 ? m.model_id.slice(0, 18) + '…' : m.model_id
              return (
                <div key={m.model_id}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <div className="size-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
                      <span className="text-xs font-mono text-primary" title={m.model_id}>{label}</span>
                      <span className="text-xs text-muted/50">{m.model_provider}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted">{m.count}</span>
                      <span className="w-8 text-right text-xs font-semibold text-primary">{pct.toFixed(0)}%</span>
                    </div>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-accent/60 overflow-hidden">
                    <motion.div
                      className="h-full rounded-full"
                      style={{ backgroundColor: color }}
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.6, ease: 'easeOut', delay: i * 0.05 }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// TokenBreakdownCard — donut + breakdown bars
// ---------------------------------------------------------------------------
const TokenBreakdownCard = ({ entries }: { entries: MetricEntry[] }) => {
  // Aggregate across all entries in range
  const agg = { input: 0, output: 0, cache_read: 0, cache_write: 0, reasoning: 0 }
  for (const entry of entries) {
    const tm = entry.token_metrics
    agg.input      += tm.input_tokens    ?? 0
    agg.output     += tm.output_tokens   ?? 0
    agg.cache_read += tm.cache_read_tokens ?? 0
    agg.cache_write+= tm.cache_write_tokens ?? 0
    agg.reasoning  += tm.reasoning_tokens ?? 0
  }

  const rows = [
    { label: 'Input',       value: agg.input,       color: '#3B82F6' },
    { label: 'Output',      value: agg.output,      color: '#22C55E' },
    { label: 'Cache read',  value: agg.cache_read,  color: '#F59E0B' },
    { label: 'Cache write', value: agg.cache_write, color: '#8B5CF6' },
    { label: 'Reasoning',   value: agg.reasoning,   color: '#EC4899' },
  ].filter((r) => r.value > 0)

  // total = sum of all displayed rows — used for headline, donut centre, and percentages
  const total = rows.reduce((s, r) => s + r.value, 0)

  const donutSlices: DonutSlice[] = rows.map((r) => ({ value: r.value, color: r.color, label: r.label }))

  return (
    <div className="rounded-xl border border-accent bg-primaryAccent overflow-hidden">
      <div className="px-4 pt-4 pb-3">
        <p className="text-xs font-medium uppercase tracking-wide text-muted">Token Breakdown</p>
        <p className="mt-0.5 text-2xl font-semibold text-primary">{formatNum(total)}</p>
        <p className="text-xs text-muted/50">across {entries.length} day{entries.length !== 1 ? 's' : ''}</p>
      </div>

      {rows.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-1.5 px-4 pb-6">
          <div className="h-8 w-full rounded" style={{
            background: 'repeating-linear-gradient(90deg,rgba(255,255,255,0.03) 0,rgba(255,255,255,0.03) 1px,transparent 1px,transparent 14px)',
            backgroundColor: 'rgba(255,255,255,0.02)',
          }} />
          <p className="text-xs uppercase tracking-widest text-muted/40">No data available yet</p>
        </div>
      ) : (
        <div className="px-4 pb-4">
          {/* Donut + legend row */}
          <div className="flex items-center gap-4 mb-4">
            <div className="relative shrink-0">
              <DonutChart slices={donutSlices} size={140} />
              {rows.length > 0 && (
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span className="text-base font-bold text-primary leading-tight">{((rows[0].value / total) * 100).toFixed(0)}%</span>
                  <span className="text-[9px] uppercase text-muted/60 mt-0.5 text-center max-w-[52px] leading-tight">{rows[0].label}</span>
                </div>
              )}
            </div>
            <div className="flex flex-col gap-1.5 flex-1">
              {rows.map((r) => {
                const pct = total > 0 ? (r.value / total) * 100 : 0
                return (
                  <div key={r.label} className="flex items-center gap-1.5">
                    <div className="size-2 rounded-full shrink-0" style={{ backgroundColor: r.color }} />
                    <span className="text-xs text-muted flex-1">{r.label}</span>
                    <span className="text-xs text-muted/70">{pct.toFixed(1)}%</span>
                  </div>
                )
              })}
            </div>
          </div>
          {/* Breakdown bars */}
          <div className="space-y-2.5">
            {rows.map((r, i) => {
              const pct = total > 0 ? (r.value / total) * 100 : 0
              return (
                <div key={r.label}>
                  <div className="flex items-center justify-between mb-1">
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
                    <motion.div
                      className="h-full rounded-full"
                      style={{ backgroundColor: r.color }}
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.6, ease: 'easeOut', delay: i * 0.05 }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
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
  const [data, setData]             = useState<MetricsResponse | null>(null)
  const [loading, setLoading]       = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError]           = useState<string | null>(null)
  const [selectedMonths, setSelectedMonths] = useState(1)
  const [selectedMonth, setSelectedMonth]   = useState<string | null>(null)

  // Month nav pill state: tracks the currently-displayed month (YYYY-MM)
  const [navMonth, setNavMonth] = useState<string>(() => dayjs().format('YYYY-MM'))
  const currentCalMonth = dayjs().format('YYYY-MM')

  const defaultEnd   = dayjs().format('YYYY-MM-DD')
  const defaultStart = dayjs().subtract(1, 'month').format('YYYY-MM-DD')
  const [startDate, setStartDate] = useState(defaultStart)
  const [endDate, setEndDate]     = useState(defaultEnd)

  const headers: Record<string, string> = {}
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`

  const fetchMetrics = useCallback(async (start = startDate, end = endDate) => {
    if (!selectedEndpoint) return
    setLoading(true); setError(null)
    try {
      const res = await fetch(APIRoutes.Metrics(selectedEndpoint, start, end), { headers })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.detail ?? `HTTP ${res.status}`)
      }
      const json = await res.json()
      setData(Array.isArray(json) ? { metrics: json, updated_at: null } : json)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load metrics')
    } finally { setLoading(false) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedEndpoint, authToken, startDate, endDate])

  /** Navigate to a specific month (YYYY-MM) and update the date range. */
  const goToMonth = useCallback((month: string) => {
    const start = dayjs(month).startOf('month').format('YYYY-MM-DD')
    const end   = dayjs(month).endOf('month').isBefore(dayjs())
      ? dayjs(month).endOf('month').format('YYYY-MM-DD')
      : dayjs().format('YYYY-MM-DD')
    setNavMonth(month)
    setSelectedMonth(month)
    setSelectedMonths(0)
    setStartDate(start)
    setEndDate(end)
    fetchMetrics(start, end)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchMetrics])

  const recalculate = useCallback(async () => {
    if (!selectedEndpoint) return
    setRefreshing(true); setError(null)
    try {
      const res = await fetch(APIRoutes.MetricsRefresh(selectedEndpoint), { method: 'POST', headers })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.detail ?? `HTTP ${res.status}`)
      }
      // Reload with the current date range so displayed data matches Reload
      await fetchMetrics(startDate, endDate)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Recalculation failed')
    } finally { setRefreshing(false) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedEndpoint, authToken, startDate, endDate, fetchMetrics])

  useEffect(() => { fetchMetrics() }, [fetchMetrics])

  const entries = data?.metrics ?? []

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
              {data?.updated_at && <span> · updated {dayjs(data.updated_at).fromNow()}</span>}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {/* Month range presets */}
            <div className="flex items-center gap-0.5 rounded-lg border border-accent bg-primaryAccent px-1.5 py-1">
              {([1, 3, 6] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => {
                    const end   = dayjs().format('YYYY-MM-DD')
                    const start = dayjs().subtract(m, 'month').format('YYYY-MM-DD')
                    setSelectedMonths(m)
                    setSelectedMonth(null)
                    setNavMonth(dayjs().format('YYYY-MM'))
                    setStartDate(start)
                    setEndDate(end)
                  }}
                  className={cn('px-2.5 py-0.5 text-xs rounded transition-colors', selectedMonths === m && !selectedMonth ? 'bg-accent text-primary font-medium' : 'text-muted/70 hover:text-muted')}
                >
                  {m}M
                </button>
              ))}
            </div>

            {/* Month prev / next navigator — exact pattern from spec */}
            <div className="flex h-9 items-center gap-x-2 rounded-md border border-border px-3 py-2 text-xs shadow-sm bg-primaryAccent">
              <button
                aria-label="Select previous month"
                onClick={() => goToMonth(dayjs(navMonth).subtract(1, 'month').format('YYYY-MM'))}
                className="flex items-center text-muted hover:text-primary transition-colors disabled:opacity-30"
              >
                <ChevronLeft className="size-3.5" />
              </button>
              <p className="font-mono w-16 select-none text-center uppercase text-primary">
                {dayjs(navMonth).format('MMM YYYY')}
              </p>
              <button
                aria-label="Select next month"
                disabled={navMonth >= currentCalMonth}
                onClick={() => goToMonth(dayjs(navMonth).add(1, 'month').format('YYYY-MM'))}
                className="flex items-center text-muted hover:text-primary transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronRight className="size-3.5" />
              </button>
            </div>

            <Button size="sm" variant="outline" onClick={() => fetchMetrics()} disabled={loading || refreshing} className="gap-1.5">
              <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />Reload
            </Button>
            <Button size="sm" variant="outline" onClick={recalculate} disabled={loading || refreshing} className="gap-1.5 border-brand/40 text-brand hover:bg-brand/10">
              <Activity className={cn('size-3.5', refreshing && 'animate-spin')} />Recalculate
            </Button>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-2 text-xs text-destructive">{error}</div>
        )}

        {/* 9 metric cards */}
        {loading && !data ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-40 rounded-xl" />)}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {CARDS.map((card) => <MetricCard key={card.key} card={card} entries={entries} />)}
          </div>
        )}

        {/* Donut charts row */}
        {loading && !data ? (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-56 rounded-xl" />)}
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
              Click <span className="font-semibold">Recalculate</span> to compute from existing run data,
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
