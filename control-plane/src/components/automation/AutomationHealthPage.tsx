'use client'
import { useEffect, useState, useCallback, useRef } from 'react'
import dynamic from 'next/dynamic'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import {
  Activity, CheckCircle, XCircle, AlertTriangle, Play, RefreshCw,
  FileText, Layers, Terminal, Cpu, Archive, ChevronDown, ChevronRight,
  FlaskConical, Bug, Wrench, Loader2, Eye, Edit2, Save, X, Check,
  ShieldCheck,
} from 'lucide-react'
import { toast } from 'sonner'

// Monaco editor — lazy-loaded to avoid SSR issues
const MonacoEditor = dynamic(
  () => import('@monaco-editor/react').then(m => m.default),
  { ssr: false, loading: () => <div className="flex items-center justify-center h-64 text-sm text-muted"><Loader2 className="size-4 animate-spin mr-2" />Loading editor…</div> }
)

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

interface FileViewerState {
  path: string
  content: string
  loading: boolean
  editMode: boolean
  editContent: string
  saving: boolean
}

interface EditRequest {
  id: string
  path: string
  original_content: string
  new_content: string
  comment: string
  status: 'pending' | 'approved' | 'rejected'
  created_at: string
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const StatusBadge = ({ status }: { status: AutomationHealth['status'] | ReportSummary['status'] }) => {
  const map: Record<string, { label: string; cls: string; icon: React.ElementType }> = {
    healthy:  { label: 'Healthy',  cls: 'bg-positive/10 text-positive',     icon: CheckCircle },
    degraded: { label: 'Degraded', cls: 'bg-warning/10 text-warning',       icon: AlertTriangle },
    no_tests: { label: 'No Tests', cls: 'bg-muted/30 text-muted', icon: FlaskConical },
    PASS:     { label: 'PASS',     cls: 'bg-positive/10 text-positive',     icon: CheckCircle },
    FAIL:     { label: 'FAIL',     cls: 'bg-destructive/10 text-destructive', icon: XCircle },
    NO_RUNS:  { label: 'No Runs',  cls: 'bg-muted/30 text-muted', icon: Activity },
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
  <div className={cn('rounded-xl border border-accent bg-primaryAccent p-4', cls)}>
    <div className="flex items-center gap-2 text-muted text-xs mb-1">
      <Icon className="size-3.5" />
      {label}
    </div>
    <div className="text-2xl font-semibold text-primary">{value}</div>
    {sub && <div className="text-xs text-muted mt-0.5">{sub}</div>}
  </div>
)

const CollapsibleSection = ({ title, count, children }: {
  title: string; count: number; children: React.ReactNode
}) => {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-xl border border-accent bg-primaryAccent">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium hover:bg-accent/30 transition-colors"
      >
        <span>{title} <span className="text-muted font-normal">({count})</span></span>
        {open ? <ChevronDown className="size-4 text-muted" /> : <ChevronRight className="size-4 text-muted" />}
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

  // WebSocket streaming state
  const [streamLog, setStreamLog] = useState<string[]>([])
  const logEndRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  // File viewer / Monaco editor state
  const [fileViewer, setFileViewer] = useState<FileViewerState | null>(null)
  const [editComment, setEditComment] = useState('')
  const [pendingEdits, setPendingEdits] = useState<EditRequest[]>([])
  const [editsPanelOpen, setEditsPanelOpen] = useState(false)

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
    setStreamLog([])
    setActiveTab('run')

    const wsUrl = APIRoutes.AutomationRunStream(selectedEndpoint, runTags, useDocker, 600)
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg.type === 'line') {
          setStreamLog(prev => [...prev, msg.data])
          // Auto-scroll to bottom
          setTimeout(() => logEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
        } else if (msg.type === 'result') {
          const result: ReportSummary = msg.summary
          setRunResult(result)
          setRunning(false)
          toast[result.status === 'PASS' ? 'success' : 'error'](
            result.status === 'PASS'
              ? `All ${result.passed} scenarios passed!`
              : `${result.failed} of ${result.total} scenarios failed.`
          )
          fetchHealth()
        } else if (msg.type === 'error') {
          toast.error(`Run error: ${msg.detail}`)
          setRunning(false)
        }
      } catch {
        // plain text line (shouldn't happen but handle gracefully)
        setStreamLog(prev => [...prev, ev.data])
      }
    }

    ws.onerror = () => {
      toast.error('WebSocket connection failed — check the backend is running')
      setRunning(false)
    }

    ws.onclose = () => {
      setRunning(false)
    }
  }

  const stopRun = () => {
    wsRef.current?.close()
    setRunning(false)
  }

  // ── File viewer helpers ──────────────────────────────────────────────────
  const openFile = useCallback(async (path: string) => {
    if (!selectedEndpoint) return
    setFileViewer({ path, content: '', loading: true, editMode: false, editContent: '', saving: false })
    try {
      const res = await fetch(APIRoutes.AutomationFileContent(selectedEndpoint, path), { headers: headers() })
      if (!res.ok) { toast.error('Failed to load file'); setFileViewer(null); return }
      const data = await res.json()
      setFileViewer({ path, content: data.content, loading: false, editMode: false, editContent: data.content, saving: false })
    } catch {
      toast.error('Failed to load file')
      setFileViewer(null)
    }
  }, [selectedEndpoint, headers])

  const submitEdit = useCallback(async () => {
    if (!selectedEndpoint || !fileViewer) return
    setFileViewer(prev => prev ? { ...prev, saving: true } : null)
    try {
      const res = await fetch(APIRoutes.AutomationEditRequest(selectedEndpoint), {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({ path: fileViewer.path, content: fileViewer.editContent, comment: editComment }),
      })
      if (!res.ok) { toast.error('Failed to submit edit'); return }
      toast.success('Edit submitted for approval — check the Pending Edits panel')
      setFileViewer(prev => prev ? { ...prev, editMode: false, saving: false } : null)
      setEditComment('')
      loadPendingEdits()
    } catch {
      toast.error('Failed to submit edit')
    } finally {
      setFileViewer(prev => prev ? { ...prev, saving: false } : null)
    }
  }, [selectedEndpoint, fileViewer, editComment, headers])

  const loadPendingEdits = useCallback(async () => {
    if (!selectedEndpoint) return
    try {
      const res = await fetch(APIRoutes.AutomationEditRequests(selectedEndpoint, 'pending'), { headers: headers() })
      if (res.ok) setPendingEdits(await res.json())
    } catch { /* ignore */ }
  }, [selectedEndpoint, headers])

  const resolveEdit = async (id: string, action: 'approve' | 'reject') => {
    if (!selectedEndpoint) return
    const url = action === 'approve'
      ? APIRoutes.AutomationApproveEdit(selectedEndpoint, id)
      : APIRoutes.AutomationRejectEdit(selectedEndpoint, id)
    const res = await fetch(url, { method: 'POST', headers: headers() })
    if (res.ok) {
      toast.success(action === 'approve' ? 'Edit applied to file!' : 'Edit rejected')
      loadPendingEdits()
    } else {
      toast.error(`Failed to ${action} edit`)
    }
  }

  useEffect(() => { loadPendingEdits() }, [loadPendingEdits])

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
        className="h-full overflow-y-auto p-6 space-y-4">
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
      className="h-full overflow-y-auto p-6 space-y-6"
    >
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-primary flex items-center gap-2">
            <Terminal className="size-5 text-brand" />
            Automation Health
          </h1>
          <p className="text-sm text-muted mt-0.5">
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
                : 'border-transparent text-muted hover:text-primary',
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
                <p className="text-sm text-muted">No .feature files found in automation/features/</p>
              )}
              {health.features.map(f => (
                <div key={f.path} className="flex items-start justify-between text-sm py-1.5 border-b last:border-0">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-primary">{f.name}</span>
                      <span className="text-muted text-xs">{f.path}</span>
                    </div>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {f.tags.map(tag => (
                        <span key={tag} className="bg-primary/10 text-primary text-[10px] rounded px-1.5 py-0.5">{tag}</span>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-4">
                    <span className="text-muted text-xs">{f.scenario_count} scenario{f.scenario_count !== 1 ? 's' : ''}</span>
                    <Button size="sm" variant="ghost" className="h-6 px-2 text-xs gap-1" onClick={() => openFile(f.path)}>
                      <Eye className="size-3" /> View
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CollapsibleSection>

          {/* Step definitions */}
          <CollapsibleSection title="Step Definitions" count={health.step_definitions.length}>
            <div className="space-y-1">
              {health.step_definitions.length === 0 && (
                <p className="text-sm text-muted">No step definition files found.</p>
              )}
              {health.step_definitions.map(s => (
                <div key={s.path} className="flex items-center justify-between text-sm py-1 border-b last:border-0">
                  <span className="text-primary font-mono text-xs">{s.path}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-muted text-xs">{s.step_count} bindings</span>
                    <Button size="sm" variant="ghost" className="h-6 px-2 text-xs gap-1" onClick={() => openFile(s.path)}>
                      <Eye className="size-3" /> View
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CollapsibleSection>

          {/* Page objects */}
          <CollapsibleSection title="Page Objects" count={health.page_objects.length}>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {health.page_objects.length === 0 && (
                <p className="text-sm text-muted col-span-3">No Page Object files found.</p>
              )}
              {health.page_objects.map(p => (
                <button
                  key={p.path}
                  onClick={() => openFile(p.path)}
                  className="rounded border bg-muted/30 px-3 py-2 text-xs text-left hover:bg-accent/40 transition-colors group"
                >
                  <div className="font-medium text-primary flex items-center justify-between">
                    {p.name}
                    <Eye className="size-3 text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                  <div className="text-muted truncate">{p.path}</div>
                </button>
              ))}
            </div>
          </CollapsibleSection>

          {/* Pending edit requests */}
          {pendingEdits.length > 0 && (
            <div className="rounded-lg border border-warning/40 bg-warning/5">
              <button
                onClick={() => setEditsPanelOpen(o => !o)}
                className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium"
              >
                <span className="flex items-center gap-2">
                  <ShieldCheck className="size-4 text-warning" />
                  Pending File Edits
                  <span className="rounded-full bg-warning/20 text-warning text-[10px] px-2 py-0.5">{pendingEdits.length}</span>
                </span>
                {editsPanelOpen ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
              </button>
              {editsPanelOpen && (
                <div className="border-t px-4 pb-4 pt-3 space-y-3">
                  {pendingEdits.map(edit => (
                    <div key={edit.id} className="rounded-xl border border-accent bg-primaryAccent p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs text-primary">{edit.path}</span>
                        <span className="text-[10px] text-muted">{new Date(edit.created_at).toLocaleString()}</span>
                      </div>
                      {edit.comment && <p className="text-xs text-muted italic">"{edit.comment}"</p>}
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" className="gap-1 text-xs text-positive border-positive/30 hover:bg-positive/10"
                          onClick={() => resolveEdit(edit.id, 'approve')}>
                          <Check className="size-3" /> Approve
                        </Button>
                        <Button size="sm" variant="outline" className="gap-1 text-xs text-destructive border-destructive/30 hover:bg-destructive/10"
                          onClick={() => resolveEdit(edit.id, 'reject')}>
                          <X className="size-3" /> Reject
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Tab: Last Results ── */}
      {activeTab === 'results' && (
        <div className="space-y-4">
          {!report ? (
            <div className="rounded-xl border border-accent bg-primaryAccent p-8 text-center text-muted text-sm">
              No test report found. Trigger a run from the <strong>Run Tests</strong> tab.
            </div>
          ) : (
            <>
              {/* Summary row */}
              <div className="flex items-center gap-4 rounded-xl border border-accent bg-primaryAccent px-4 py-3">
                <StatusBadge status={report.status} />
                <div className="flex gap-6 text-sm">
                  <span className="text-positive"><strong>{report.passed}</strong> passed</span>
                  <span className="text-destructive"><strong>{report.failed}</strong> failed</span>
                  <span className="text-muted"><strong>{report.pending}</strong> pending</span>
                  <span className="text-muted"><strong>{report.total}</strong> total</span>
                </div>
              </div>

              {/* Failures */}
              {report.failures.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-primary flex items-center gap-1.5">
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
                          <div className="font-medium text-primary">{f.scenario}</div>
                          <div className="text-xs text-muted mt-0.5">{f.feature}</div>
                        </div>
                        {expandedFailure === i
                          ? <ChevronDown className="size-4 text-muted shrink-0 mt-0.5" />
                          : <ChevronRight className="size-4 text-muted shrink-0 mt-0.5" />}
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
            <div className="rounded-xl border border-accent bg-primaryAccent p-8 text-center text-muted text-sm">
              No trace ZIPs found in <code>automation/test-results/</code>.
              Traces are written automatically when a test fails (on first retry).
            </div>
          ) : (
            traces.map(t => (
              <div key={t.name} className="rounded-xl border border-accent bg-primaryAccent px-4 py-3 flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium text-primary font-mono">{t.name}</div>
                  <div className="text-xs text-muted mt-0.5">
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
        <div className="space-y-4">
          <div className="rounded-xl border border-accent bg-primaryAccent p-4 space-y-4 max-w-lg">
            <h3 className="text-sm font-medium text-primary">Run Configuration</h3>

            {/* Tags filter */}
            <div className="space-y-1">
              <label className="text-xs text-muted">Tag Filter (optional)</label>
              <input
                type="text"
                value={runTags}
                onChange={e => setRunTags(e.target.value)}
                placeholder="@smoke or @AC-001 or @regression"
                disabled={running}
                className="w-full rounded-xl border border-accent bg-background px-3 py-2 text-sm placeholder:text-muted focus:outline-none focus:border-primary/40 focus:ring-0 disabled:opacity-50"
              />
              <p className="text-[11px] text-muted">Leave empty to run the full regression suite.</p>
            </div>

            {/* Docker toggle */}
            <div className="flex items-center gap-2">
              <input
                id="use-docker"
                type="checkbox"
                checked={useDocker}
                onChange={e => setUseDocker(e.target.checked)}
                disabled={running}
                className="rounded border-input"
              />
              <label htmlFor="use-docker" className="text-sm text-primary">
                Run in <code>qap-playwright</code> container
                <span className="text-muted ml-1 text-xs">(requires <code>--profile runner</code>)</span>
              </label>
            </div>

            <div className="flex gap-2">
              <Button
                onClick={triggerRun}
                disabled={running || !health?.npm_installed}
                className="flex-1 gap-2"
              >
                {running
                  ? <><Loader2 className="size-4 animate-spin" /> Running…</>
                  : <><Play className="size-4" /> Start Run</>}
              </Button>
              {running && (
                <Button variant="outline" onClick={stopRun} className="gap-1.5 text-xs">
                  <X className="size-3.5" /> Stop
                </Button>
              )}
            </div>

            {!health?.npm_installed && (
              <p className="text-xs text-warning">node_modules not found — run <code>npm install</code> in automation/ first.</p>
            )}
          </div>

          {/* Live streaming log */}
          {(running || streamLog.length > 0) && (
            <div className="rounded-lg border bg-[#1e1e1e] overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2 bg-[#252526] border-b border-[#3c3c3c]">
                <span className="text-xs text-[#cccccc] flex items-center gap-2">
                  <Terminal className="size-3.5" />
                  Live Output
                </span>
                {running && <span className="flex items-center gap-1.5 text-[10px] text-[#4ec9b0]"><Loader2 className="size-3 animate-spin" /> Running</span>}
                {!running && streamLog.length > 0 && <span className="text-[10px] text-[#608b4e]">Completed</span>}
              </div>
              <div className="p-4 h-72 overflow-y-auto font-mono text-xs text-[#d4d4d4] space-y-0.5 scroll-smooth">
                {streamLog.map((line, i) => (
                  <div key={i} className={cn(
                    'leading-5 whitespace-pre-wrap break-all',
                    line.includes('passing') ? 'text-[#4ec9b0] font-semibold' :
                    line.includes('failing') || line.includes('failed') ? 'text-[#f44747]' :
                    line.includes('✓') || line.includes('√') ? 'text-[#608b4e]' :
                    line.includes('✗') || line.includes('×') ? 'text-[#f44747]' :
                    'text-[#d4d4d4]'
                  )}>{line || '\u00A0'}</div>
                ))}
                <div ref={logEndRef} />
              </div>
            </div>
          )}

          {/* Run result summary */}
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
                  <div className="text-xs font-medium text-primary">Failed scenarios:</div>
                  {runResult.failures.map((f, i) => (
                    <div key={i} className="text-xs bg-destructive/10 rounded px-3 py-2">
                      <div className="font-medium">{f.scenario}</div>
                      {f.error && <div className="text-muted mt-1 truncate">{f.error.slice(0, 150)}</div>}
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

      {/* ── File Viewer / Monaco Editor Modal ── */}
      <AnimatePresence>
        {fileViewer && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={e => { if (e.target === e.currentTarget) setFileViewer(null) }}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
              className="w-full max-w-5xl rounded-xl border border-accent bg-primaryAccent shadow-2xl overflow-hidden flex flex-col"
              style={{ maxHeight: '90vh' }}
            >
              {/* Modal header */}
              <div className="flex items-center justify-between px-4 py-3 border-b bg-accent/30">
                <div className="flex items-center gap-2 min-w-0">
                  <FileText className="size-4 text-brand shrink-0" />
                  <span className="font-mono text-sm text-primary truncate">{fileViewer.path}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {!fileViewer.editMode ? (
                    <Button size="sm" variant="outline" className="gap-1.5 text-xs"
                      onClick={() => setFileViewer(prev => prev ? { ...prev, editMode: true } : null)}>
                      <Edit2 className="size-3" /> Edit
                    </Button>
                  ) : (
                    <>
                      <Button size="sm" variant="outline" className="gap-1.5 text-xs"
                        onClick={() => setFileViewer(prev => prev ? { ...prev, editMode: false } : null)}>
                        <X className="size-3" /> Cancel
                      </Button>
                      <Button size="sm" className="gap-1.5 text-xs" onClick={submitEdit} disabled={fileViewer.saving}>
                        {fileViewer.saving ? <Loader2 className="size-3 animate-spin" /> : <Save className="size-3" />}
                        Submit for Approval
                      </Button>
                    </>
                  )}
                  <button onClick={() => setFileViewer(null)}
                    className="rounded p-1 hover:bg-accent transition-colors">
                    <X className="size-4 text-muted" />
                  </button>
                </div>
              </div>

              {/* Edit mode info banner */}
              {fileViewer.editMode && (
                <div className="px-4 py-2 bg-warning/10 border-b border-warning/20 flex items-center gap-2 text-xs text-warning">
                  <ShieldCheck className="size-3.5 shrink-0" />
                  Changes will not be applied immediately — they are submitted for approval first.
                  <input
                    type="text"
                    value={editComment}
                    onChange={e => setEditComment(e.target.value)}
                    placeholder="Optional comment…"
                    className="ml-auto rounded border bg-background px-2 py-0.5 text-xs w-48 focus:outline-none focus:border-primary/40 focus:ring-0"
                  />
                </div>
              )}

              {/* Monaco Editor */}
              <div className="flex-1 overflow-hidden" style={{ height: '60vh', minHeight: '400px' }}>
                {fileViewer.loading ? (
                  <div className="flex items-center justify-center h-full text-sm text-muted">
                    <Loader2 className="size-5 animate-spin mr-2" /> Loading file…
                  </div>
                ) : (
                  <MonacoEditor
                    height="60vh"
                    language={
                      fileViewer.path.endsWith('.feature') ? 'gherkin' :
                      fileViewer.path.endsWith('.ts') ? 'typescript' :
                      fileViewer.path.endsWith('.json') ? 'json' :
                      fileViewer.path.endsWith('.md') ? 'markdown' : 'plaintext'
                    }
                    value={fileViewer.editMode ? fileViewer.editContent : fileViewer.content}
                    onChange={val => fileViewer.editMode && setFileViewer(prev => prev ? { ...prev, editContent: val ?? '' } : null)}
                    options={{
                      readOnly: !fileViewer.editMode,
                      minimap: { enabled: false },
                      fontSize: 13,
                      lineNumbers: 'on',
                      scrollBeyondLastLine: false,
                      wordWrap: 'on',
                      theme: 'vs-dark',
                    }}
                    theme="vs-dark"
                  />
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
