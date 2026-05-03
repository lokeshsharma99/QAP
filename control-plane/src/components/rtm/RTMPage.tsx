'use client'
import { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import {
  GitBranch, Search, RefreshCw, Tag, FileText, Ticket, ChevronDown, ChevronRight,
  CheckCircle, AlertCircle, Loader2, ExternalLink,
} from 'lucide-react'
import { toast } from 'sonner'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface RTMRow {
  ticket_ids: string[]
  feature_title: string
  feature_file: string
  scenario_name: string
  scenario_type: string
  tags: string[]
  steps: string[]
  source: string
}

interface ExplainResponse {
  scenario_name: string
  feature_title: string
  feature_file: string
  ticket_ids: string[]
  tags: string[]
  steps: string[]
  explanation: string
}

// ---------------------------------------------------------------------------
// RTM Page
// ---------------------------------------------------------------------------
export default function RTMPage() {
  const { selectedEndpoint, authToken } = useStore()
  const [rows, setRows] = useState<RTMRow[]>([])
  const [loading, setLoading] = useState(false)
  const [ticketFilter, setTicketFilter] = useState('')
  const [tagFilter, setTagFilter] = useState('')
  const [searchQ, setSearchQ] = useState('')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [explain, setExplain] = useState<ExplainResponse | null>(null)
  const [explainLoading, setExplainLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'live' | 'semantic'>('live')

  const headers = { Authorization: `Bearer ${authToken}` }

  const fetchLive = useCallback(async () => {
    if (!selectedEndpoint) return
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (ticketFilter) params.set('ticket', ticketFilter)
      if (tagFilter) params.set('tag', tagFilter)
      const url = `${selectedEndpoint}/rtm${params.toString() ? '?' + params : ''}`
      const res = await fetch(url, { headers })
      if (!res.ok) throw new Error(await res.text())
      setRows(await res.json())
    } catch (e: unknown) {
      toast.error(`RTM fetch failed: ${e instanceof Error ? e.message : e}`)
    } finally {
      setLoading(false)
    }
  }, [selectedEndpoint, authToken, ticketFilter, tagFilter])

  const fetchSemantic = useCallback(async () => {
    if (!selectedEndpoint || !searchQ.trim()) return
    setLoading(true)
    try {
      const url = APIRoutes.RTMSearch(selectedEndpoint, searchQ)
      const res = await fetch(url, { headers })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      // Convert KB rows to display format
      setRows(data.map((r: Record<string, unknown>) => ({
        ticket_ids: r.ticket_id ? [r.ticket_id as string] : [],
        feature_title: (r.feature_title as string) || '',
        feature_file: (r.feature_file as string) || '',
        scenario_name: (r.scenario_name as string) || '',
        scenario_type: 'Scenario',
        tags: typeof r.tags === 'string' ? (r.tags as string).split(' ') : [],
        steps: [],
        source: 'rtm_kb',
      })))
    } catch (e: unknown) {
      toast.error(`Search failed: ${e instanceof Error ? e.message : e}`)
    } finally {
      setLoading(false)
    }
  }, [selectedEndpoint, authToken, searchQ])

  const explainScenario = useCallback(async (scenarioName: string) => {
    if (!selectedEndpoint) return
    setExplainLoading(true)
    try {
      const res = await fetch(APIRoutes.RTMExplain(selectedEndpoint), {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_name: scenarioName, include_steps: true, include_ticket_context: true }),
      })
      if (!res.ok) throw new Error(await res.text())
      setExplain(await res.json())
    } catch (e: unknown) {
      toast.error(`Explain failed: ${e instanceof Error ? e.message : e}`)
    } finally {
      setExplainLoading(false)
    }
  }, [selectedEndpoint, authToken])

  useEffect(() => { fetchLive() }, [fetchLive])

  const toggleRow = (key: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  const allTickets = Array.from(new Set(rows.flatMap(r => r.ticket_ids))).sort()

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2, ease: 'easeOut' }}
      className="h-full overflow-y-auto p-6 space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <GitBranch className="w-6 h-6 text-primary" />
          <div>
            <h1 className="text-xl font-semibold">Requirements Traceability Matrix</h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              {rows.length} scenario{rows.length !== 1 ? 's' : ''} · {allTickets.length} ticket{allTickets.length !== 1 ? 's' : ''} covered
            </p>
          </div>
        </div>
        <Button size="sm" variant="outline" onClick={fetchLive} disabled={loading}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          <span className="ml-2">Refresh</span>
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-border">
        {(['live', 'semantic'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
              activeTab === tab
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            {tab === 'live' ? 'Live (Feature Files)' : 'Semantic Search (RTM KB)'}
          </button>
        ))}
      </div>

      {/* Filters */}
      {activeTab === 'live' ? (
        <div className="flex gap-3 flex-wrap">
          <div className="flex items-center gap-2 bg-accent/30 rounded-lg px-3 py-1.5 flex-1 min-w-[180px]">
            <Ticket className="w-4 h-4 text-muted-foreground shrink-0" />
            <input
              className="bg-transparent text-sm outline-none w-full placeholder:text-muted-foreground"
              placeholder="Filter by ticket (e.g. GDS-42)"
              value={ticketFilter}
              onChange={e => setTicketFilter(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && fetchLive()}
            />
          </div>
          <div className="flex items-center gap-2 bg-accent/30 rounded-lg px-3 py-1.5 flex-1 min-w-[180px]">
            <Tag className="w-4 h-4 text-muted-foreground shrink-0" />
            <input
              className="bg-transparent text-sm outline-none w-full placeholder:text-muted-foreground"
              placeholder="Filter by tag (e.g. smoke)"
              value={tagFilter}
              onChange={e => setTagFilter(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && fetchLive()}
            />
          </div>
          <Button size="sm" onClick={fetchLive} disabled={loading}>
            <Search className="w-4 h-4 mr-2" /> Filter
          </Button>
        </div>
      ) : (
        <div className="flex gap-3">
          <div className="flex items-center gap-2 bg-accent/30 rounded-lg px-3 py-1.5 flex-1">
            <Search className="w-4 h-4 text-muted-foreground shrink-0" />
            <input
              className="bg-transparent text-sm outline-none w-full placeholder:text-muted-foreground"
              placeholder="Search RTM KB: 'personal details AC-001', 'login validation'…"
              value={searchQ}
              onChange={e => setSearchQ(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && fetchSemantic()}
            />
          </div>
          <Button size="sm" onClick={fetchSemantic} disabled={loading || !searchQ.trim()}>
            <Search className="w-4 h-4 mr-2" /> Search
          </Button>
        </div>
      )}

      {/* Explain Panel */}
      {explain && (
        <div className="bg-accent/20 border border-border rounded-xl p-4 space-y-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-positive" />
              <span className="text-sm font-medium">{explain.scenario_name}</span>
            </div>
            <button onClick={() => setExplain(null)} className="text-muted-foreground hover:text-foreground text-xs">✕ close</button>
          </div>
          <div className="text-xs text-muted-foreground space-y-1">
            <div><span className="font-medium text-foreground">Tickets:</span> {explain.ticket_ids.join(', ') || 'none'}</div>
            <div><span className="font-medium text-foreground">Feature:</span> {explain.feature_title}</div>
            <div><span className="font-medium text-foreground">File:</span> <code className="text-xs">{explain.feature_file}</code></div>
            <div><span className="font-medium text-foreground">Tags:</span> {explain.tags.map(t => `@${t}`).join(' ')}</div>
          </div>
          {explain.steps.length > 0 && (
            <div>
              <div className="text-xs font-medium text-foreground mb-1">Steps:</div>
              <div className="space-y-0.5">
                {explain.steps.map((s, i) => (
                  <div key={i} className="text-xs text-muted-foreground font-mono pl-2 border-l border-border">{s}</div>
                ))}
              </div>
            </div>
          )}
          <pre className="text-xs bg-background/60 rounded p-3 whitespace-pre-wrap border border-border">{explain.explanation}</pre>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}
        </div>
      ) : rows.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground space-y-2">
          <AlertCircle className="w-8 h-8" />
          <p className="text-sm">No scenarios found.</p>
          <p className="text-xs">
            {activeTab === 'live'
              ? 'Add .feature files to automation/features/ — Scribe will populate them automatically.'
              : 'Run the Scribe agent on a Jira ticket to persist RTM rows to the KB.'}
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-border overflow-hidden">
          {/* Table header */}
          <div className="grid grid-cols-[1fr_1.5fr_2fr_auto] gap-4 px-4 py-2.5 bg-accent/30 border-b border-border text-xs font-medium text-muted-foreground uppercase tracking-wide">
            <span>Ticket(s)</span>
            <span>Feature</span>
            <span>Scenario</span>
            <span>Actions</span>
          </div>
          {/* Rows */}
          {rows.map((row, idx) => {
            const key = `${row.feature_file}:${row.scenario_name}:${idx}`
            const isExpanded = expanded.has(key)
            return (
              <div key={key} className={cn('border-b border-border last:border-0', isExpanded && 'bg-accent/10')}>
                <div className="grid grid-cols-[1fr_1.5fr_2fr_auto] gap-4 px-4 py-3 items-start">
                  {/* Tickets */}
                  <div className="flex flex-wrap gap-1">
                    {row.ticket_ids.length > 0
                      ? row.ticket_ids.map(t => (
                        <span key={t} className="inline-flex items-center gap-1 text-xs bg-primary/10 text-primary rounded px-1.5 py-0.5 font-mono">
                          <Ticket className="w-3 h-3" />{t}
                        </span>
                      ))
                      : <span className="text-xs text-muted-foreground">—</span>}
                  </div>
                  {/* Feature */}
                  <div className="space-y-0.5">
                    <div className="text-xs font-medium truncate">{row.feature_title}</div>
                    <div className="text-xs text-muted-foreground font-mono truncate">{row.feature_file.split('/').pop()}</div>
                  </div>
                  {/* Scenario */}
                  <div className="space-y-1">
                    <div className="text-sm">{row.scenario_name}</div>
                    <div className="flex flex-wrap gap-1">
                      {row.tags.slice(0, 5).map(t => (
                        <span key={t} className="text-xs bg-accent/40 text-muted-foreground rounded px-1 py-0.5">@{t}</span>
                      ))}
                      {row.tags.length > 5 && <span className="text-xs text-muted-foreground">+{row.tags.length - 5}</span>}
                    </div>
                  </div>
                  {/* Actions */}
                  <div className="flex items-center gap-1">
                    {row.steps.length > 0 && (
                      <button
                        onClick={() => toggleRow(key)}
                        className="p-1 rounded hover:bg-accent/50 text-muted-foreground"
                        title="Toggle steps"
                      >
                        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      </button>
                    )}
                    <button
                      onClick={() => explainScenario(row.scenario_name)}
                      disabled={explainLoading}
                      className="p-1 rounded hover:bg-accent/50 text-muted-foreground"
                      title="Explain lineage"
                    >
                      {explainLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ExternalLink className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                {/* Steps expander */}
                {isExpanded && row.steps.length > 0 && (
                  <div className="px-6 pb-3">
                    <div className="bg-background/60 rounded-lg border border-border p-3 space-y-0.5">
                      {row.steps.map((step, i) => (
                        <div key={i} className="text-xs font-mono text-muted-foreground">{step}</div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </motion.div>
  )
}
