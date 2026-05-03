'use client'
import { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import {
  Activity, CheckCircle, XCircle, AlertTriangle, Play, RefreshCw,
  FileText, Layers, Terminal, Cpu, Archive, ChevronDown, ChevronRight,
  FlaskConical, Bug, Wrench, Loader2,
} from 'lucide-react'
import { toast } from 'sonner'

// ---------------------------------------------------------------------------
// Types (mirrors automation_health.py response)
// ---------------------------------------------------------------------------

interface FeatureSummary {
  path: string
  name: string
  scenario_count: number
  tag_count: number
  tags: string[]
}

interface StepDefSummary {
  path: string
  step_count: number
}

interface PageObjectSummary {
  path: string
  name: string
}

interface ReportSummary {
  status: 'PASS' | 'FAIL' | 'NO_RUNS' | 'ERROR'
  passed: number
  failed: number
  pending: number
  total: number
  failures: { feature: string; scenario: string; error: string }[]
}

interface AutomationHealth {
  status: 'healthy' | 'degraded' | 'no_tests'
  features: FeatureSummary[]
  step_definitions: StepDefSummary[]
  page_objects: PageObjectSummary[]
  total_scenarios: number
  total_steps: number
  total_pages: number
  npm_installed: boolean
  node_modules_present: boolean
  last_report_summary: ReportSummary | null
}

interface TraceFile {
  name: string
  path: string
  size_kb: number
  modified: string
}

type Tab = 'health' | 'results' | 'traces' | 'run'

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const StatusBadge = ({ status }: { status: AutomationHealth['status'] | ReportSummary['status'] }) => {
  const map: Record<string, { label: string; cls: string; icon: React.ElementType }> = {
    healthy:  { label: 'Healthy',  cls: 'bg-positive/10 text-positive',     icon: CheckCircle },
    degraded: { label: 'Degraded', cls: 'bg-warning/10 text-warning',       icon: AlertTriangle },
    no_tests: { label: 'No Tests', cls: 'bg-muted/30 text-muted-foreground', icon: FlaskConical },
    PASS:     { label: 'PASS',     cls: 'bg-positive/10 text-positive',     icon: CheckCircle },
    FAIL:     { label: 'FAIL',     cls: 'bg-destructive/10 text-destructive', icon: XCircle },
    NO_RUNS:  { label: 'No Runs',  cls: 'bg-muted/30 text-muted-foreground', icon: Activity },
    ERROR:    { label: 'Error',    cls: 'bg-destructive/10 text-destructive', icon: AlertTriangle },
  }
  const cfg = map[status] ?? map['ERROR']
  const Icon = cfg.icon
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium', cfg.cls)}>
      <Icon className="size-3" />
      {cfg.label}
    </span>
  )
}

const StatCard = ({ icon: Icon, label, value, sub, cls }: {
  icon: React.ElementType; label: string; value: string | number; sub?: string; cls?: string
}) => (
  <div className={cn('rounded-lg border bg-card p-4', cls)}>
    <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
      <Icon className="size-3.5" />
      {label}
    </div>
    <div className="text-2xl font-semibold text-foreground">{value}</div>
    {sub && <div className="text-xs text-muted-foreground mt-0.5">{sub}</div>}
  </div>
)

const CollapsibleSection = ({ title, count, children }: {
  title: string; count: number; children: React.ReactNode
}) => {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-lg border bg-card">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium hover:bg-accent/30 transition-colors"
      >
        <span>{title} <span className="text-muted-foreground font-normal">({count})</span></span>
        {open ? <ChevronDown className="size-4 text-muted-foreground" /> : <ChevronRight className="size-4 text-muted-foreground" />}
      </button>
      {open && <div className="border-t px-4 pb-4 pt-3">{children}</div>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function AutomationHealthPage() {
  const { selectedEndpoint, authToken } = useStore()
  const [health, setHealth] = useState<AutomationHealth | null>(null)
  const [traces, setTraces] = useState<TraceFile[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [runResult, setRunResult] = useState<ReportSummary | null>(null)
  const [runTags, setRunTags] = useState('')
  const [useDocker, setUseDocker] = useState(false)
  const [activeTab, setActiveTab] = useState<Tab>('health')
  const [expandedFailure, setExpandedFailure] = useState<number | null>(null)

  const headers = useCallback(() => ({
    'Content-Type': 'application/json',
    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
  }), [authToken])

  const fetchHealth = useCallback(async () => {
    if (!selectedEndpoint) return
    setLoading(true)
    try {
      const [hRes, tRes] = await Promise.all([
        fetch(APIRoutes.AutomationHealth(selectedEndpoint), { headers: headers() }),
        fetch(APIRoutes.AutomationTraces(selectedEndpoint), { headers: headers() }),
      ])
      if (hRes.ok) setHealth(await hRes.json())
      if (tRes.ok) setTraces(await tRes.json())
    } catch {
      toast.error('Failed to fetch automation health')
    } finally {
      setLoading(false)
    }
  }, [selectedEndpoint, headers])

  useEffect(() => { fetchHealth() }, [fetchHealth])

  const triggerRun = async () => {
    if (!selectedEndpoint) return
    setRunning(true)
    setRunResult(null)
    setActiveTab('run')
    toast.info('Test run started — this may take a few minutes…')
    try {
      const res = await fetch(APIRoutes.AutomationRun(selectedEndpoint), {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({ tags: runTags, use_docker: useDocker, timeout_seconds: 600 }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        toast.error(`Run failed: ${err.detail ?? res.statusText}`)
        return
      }
      const result: ReportSummary = await res.json()
      setRunResult(result)
      toast[result.status === 'PASS' ? 'success' : 'error'](
        result.status === 'PASS'
          ? `All ${result.passed} scenarios passed!`
          : `${result.failed} of ${result.total} scenarios failed.`
      )
      await fetchHealth()
    } finally {
      setRunning(false)
    }
  }

  const triggerHealing = async (traceName: string) => {
    toast.info(`Sending trace to Detective for RCA: ${traceName}`)
    // Kick off triage_heal workflow via chat — simplest approach without
    // blocking the UI. User can watch progress in /sessions.
    if (!selectedEndpoint) return
    try {
      const agentRes = await fetch(`${selectedEndpoint}/agents/detective/runs`, {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({
          message: `Analyse this trace and produce an RCA report: ${traceName}`,
          stream: false,
        }),
      })
      if (agentRes.ok) {
        toast.success('Detective is analysing the trace. Check /sessions for progress.')
      }
    } catch {
      toast.error('Failed to dispatch to Detective')
    }
  }

  // ---------------------------------------------------------------------------
  // Loading skeleton
  // ---------------------------------------------------------------------------
  if (loading) {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2, ease: 'easeOut' }}
        className="p-6 space-y-4 max-w-5xl mx-auto">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="h-48 w-full" />
      </motion.div>
    )
  }

  const report = health?.last_report_summary

  // ---------------------------------------------------------------------------
  // Tabs
  // ---------------------------------------------------------------------------
  const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: 'health', label: 'Framework', icon: Activity },
    { id: 'results', label: 'Last Results', icon: FlaskConical },
    { id: 'traces', label: `Traces (${traces.length})`, icon: Archive },
    { id: 'run', label: 'Run Tests', icon: Play },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className="p-6 space-y-6 max-w-5xl mx-auto"
    >
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground flex items-center gap-2">
            <Terminal className="size-5 text-primary" />
            Automation Health
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Inspect the test framework, view results, and trigger runs
          </p>
        </div>
        <div className="flex items-center gap-2">
          {health && <StatusBadge status={health.status} />}
          <Button variant="outline" size="sm" onClick={fetchHealth} className="gap-1.5">
            <RefreshCw className="size-3.5" />
            Refresh
          </Button>
        </div>
      </div>

      {/* ── Stat cards ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard icon={FileText}  label="Feature Files"   value={health?.features.length ?? 0}       sub={`${health?.total_scenarios ?? 0} scenarios`} />
        <StatCard icon={Layers}    label="Step Bindings"   value={health?.total_steps ?? 0}            sub={`across ${health?.step_definitions.length ?? 0} files`} />
        <StatCard icon={Cpu}       label="Page Objects"    value={health?.total_pages ?? 0}            sub="POM classes" />
        <StatCard
          icon={report?.status === 'PASS' ? CheckCircle : report?.status === 'FAIL' ? XCircle : Activity}
          label="Last Run"
          value={report ? `${report.passed}/${report.total}` : '—'}
          sub={report?.status ?? 'No report yet'}
          cls={report?.status === 'FAIL' ? 'border-destructive/30' : report?.status === 'PASS' ? 'border-positive/30' : ''}
        />
      </div>

      {/* ── npm / node_modules warning ── */}
      {health && !health.npm_installed && (
        <div className="rounded-lg border border-warning/40 bg-warning/5 px-4 py-3 flex items-center gap-2 text-sm text-warning">
          <AlertTriangle className="size-4 shrink-0" />
          <span><strong>node_modules</strong> not found inside <code>automation/</code>. Run <code>npm install</code> before triggering a test run.</span>
        </div>
      )}

      {/* ── Tabs ── */}
      <div className="flex gap-1 border-b">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === t.id
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground',
            )}
          >
            <t.icon className="size-3.5" />
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Tab: Framework Health ── */}
      {activeTab === 'health' && health && (
        <div className="space-y-3">
          {/* Features */}
          <CollapsibleSection title="Feature Files" count={health.features.length}>
            <div className="space-y-2">
              {health.features.length === 0 && (
                <p className="text-sm text-muted-foreground">No .feature files found in automation/features/</p>
              )}
              {health.features.map(f => (
                <div key={f.path} className="flex items-start justify-between text-sm py-1.5 border-b last:border-0">
                  <div>
                    <span className="font-medium text-foreground">{f.name}</span>
                    <span className="text-muted-foreground ml-2 text-xs">{f.path}</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {f.tags.map(tag => (
                        <span key={tag} className="bg-primary/10 text-primary text-[10px] rounded px-1.5 py-0.5">{tag}</span>
                      ))}
                    </div>
                  </div>
                  <span className="text-muted-foreground text-xs shrink-0 ml-4">{f.scenario_count} scenario{f.scenario_count !== 1 ? 's' : ''}</span>
                </div>
              ))}
            </div>
          </CollapsibleSection>

          {/* Step definitions */}
          <CollapsibleSection title="Step Definitions" count={health.step_definitions.length}>
            <div className="space-y-1">
              {health.step_definitions.length === 0 && (
                <p className="text-sm text-muted-foreground">No step definition files found.</p>
              )}
              {health.step_definitions.map(s => (
                <div key={s.path} className="flex items-center justify-between text-sm py-1 border-b last:border-0">
                  <span className="text-foreground font-mono text-xs">{s.path}</span>
                  <span className="text-muted-foreground text-xs">{s.step_count} bindings</span>
                </div>
              ))}
            </div>
          </CollapsibleSection>

          {/* Page objects */}
          <CollapsibleSection title="Page Objects" count={health.page_objects.length}>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {health.page_objects.length === 0 && (
                <p className="text-sm text-muted-foreground col-span-3">No Page Object files found.</p>
              )}
              {health.page_objects.map(p => (
                <div key={p.path} className="rounded border bg-muted/30 px-3 py-2 text-xs">
                  <div className="font-medium text-foreground">{p.name}</div>
                  <div className="text-muted-foreground truncate">{p.path}</div>
                </div>
              ))}
            </div>
          </CollapsibleSection>
        </div>
      )}

      {/* ── Tab: Last Results ── */}
      {activeTab === 'results' && (
        <div className="space-y-4">
          {!report ? (
            <div className="rounded-lg border bg-card p-8 text-center text-muted-foreground text-sm">
              No test report found. Trigger a run from the <strong>Run Tests</strong> tab.
            </div>
          ) : (
            <>
              {/* Summary row */}
              <div className="flex items-center gap-4 rounded-lg border bg-card px-4 py-3">
                <StatusBadge status={report.status} />
                <div className="flex gap-6 text-sm">
                  <span className="text-positive"><strong>{report.passed}</strong> passed</span>
                  <span className="text-destructive"><strong>{report.failed}</strong> failed</span>
                  <span className="text-muted-foreground"><strong>{report.pending}</strong> pending</span>
                  <span className="text-muted-foreground"><strong>{report.total}</strong> total</span>
                </div>
              </div>

              {/* Failures */}
              {report.failures.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-foreground flex items-center gap-1.5">
                    <Bug className="size-4 text-destructive" />
                    Failures
                  </h3>
                  {report.failures.map((f, i) => (
                    <div key={i} className="rounded-lg border border-destructive/20 bg-destructive/5">
                      <button
                        onClick={() => setExpandedFailure(expandedFailure === i ? null : i)}
                        className="w-full flex items-start justify-between px-4 py-3 text-sm text-left"
                      >
                        <div>
                          <div className="font-medium text-foreground">{f.scenario}</div>
                          <div className="text-xs text-muted-foreground mt-0.5">{f.feature}</div>
                        </div>
                        {expandedFailure === i
                          ? <ChevronDown className="size-4 text-muted-foreground shrink-0 mt-0.5" />
                          : <ChevronRight className="size-4 text-muted-foreground shrink-0 mt-0.5" />}
                      </button>
                      {expandedFailure === i && f.error && (
                        <div className="border-t px-4 pb-3 pt-2">
                          <pre className="text-xs text-destructive bg-destructive/5 rounded p-3 overflow-x-auto whitespace-pre-wrap">{f.error}</pre>
                          <Button
                            size="sm"
                            variant="outline"
                            className="mt-3 gap-1.5 text-xs"
                            onClick={() => triggerHealing(`Scenario: ${f.scenario} in ${f.feature}`)}
                          >
                            <Wrench className="size-3" />
                            Send to Detective for RCA
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Tab: Traces ── */}
      {activeTab === 'traces' && (
        <div className="space-y-2">
          {traces.length === 0 ? (
            <div className="rounded-lg border bg-card p-8 text-center text-muted-foreground text-sm">
              No trace ZIPs found in <code>automation/test-results/</code>.
              Traces are written automatically when a test fails (on first retry).
            </div>
          ) : (
            traces.map(t => (
              <div key={t.name} className="rounded-lg border bg-card px-4 py-3 flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium text-foreground font-mono">{t.name}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    {t.size_kb} KB · {new Date(t.modified).toLocaleString()}
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1.5 text-xs"
                  onClick={() => triggerHealing(t.path)}
                >
                  <Bug className="size-3" />
                  RCA
                </Button>
              </div>
            ))
          )}
        </div>
      )}

      {/* ── Tab: Run Tests ── */}
      {activeTab === 'run' && (
        <div className="space-y-4 max-w-lg">
          <div className="rounded-lg border bg-card p-4 space-y-4">
            <h3 className="text-sm font-medium text-foreground">Run Configuration</h3>

            {/* Tags filter */}
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Tag Filter (optional)</label>
              <input
                type="text"
                value={runTags}
                onChange={e => setRunTags(e.target.value)}
                placeholder="@smoke or @AC-001 or @regression"
                className="w-full rounded-md border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
              <p className="text-[11px] text-muted-foreground">Leave empty to run the full regression suite.</p>
            </div>

            {/* Docker toggle */}
            <div className="flex items-center gap-2">
              <input
                id="use-docker"
                type="checkbox"
                checked={useDocker}
                onChange={e => setUseDocker(e.target.checked)}
                className="rounded border-input"
              />
              <label htmlFor="use-docker" className="text-sm text-foreground">
                Run in <code>qap-playwright</code> container
                <span className="text-muted-foreground ml-1 text-xs">(requires <code>--profile runner</code>)</span>
              </label>
            </div>

            <Button
              onClick={triggerRun}
              disabled={running || !health?.npm_installed}
              className="w-full gap-2"
            >
              {running
                ? <><Loader2 className="size-4 animate-spin" /> Running…</>
                : <><Play className="size-4" /> Start Run</>}
            </Button>

            {!health?.npm_installed && (
              <p className="text-xs text-warning">node_modules not found — run <code>npm install</code> in automation/ first.</p>
            )}
          </div>

          {/* Run result */}
          {running && (
            <div className="rounded-lg border bg-card p-6 flex flex-col items-center gap-3 text-sm text-muted-foreground">
              <Loader2 className="size-8 animate-spin text-primary" />
              <div>Tests are running… check <strong>/sessions</strong> for live agent output.</div>
            </div>
          )}

          {runResult && !running && (
            <div className={cn(
              'rounded-lg border p-4 space-y-3',
              runResult.status === 'PASS' ? 'border-positive/30 bg-positive/5' : 'border-destructive/30 bg-destructive/5'
            )}>
              <div className="flex items-center gap-2">
                <StatusBadge status={runResult.status} />
                <span className="text-sm">
                  {runResult.passed}/{runResult.total} scenarios passed
                </span>
              </div>
              {runResult.failures.length > 0 && (
                <>
                  <div className="text-xs font-medium text-foreground">Failed scenarios:</div>
                  {runResult.failures.map((f, i) => (
                    <div key={i} className="text-xs bg-destructive/10 rounded px-3 py-2">
                      <div className="font-medium">{f.scenario}</div>
                      {f.error && <div className="text-muted-foreground mt-1 truncate">{f.error.slice(0, 150)}</div>}
                    </div>
                  ))}
                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-1.5 text-xs w-full"
                    onClick={() => triggerHealing('latest run failures')}
                  >
                    <Wrench className="size-3" />
                    Send failures to Detective + Medic for auto-healing
                  </Button>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </motion.div>
  )
}
