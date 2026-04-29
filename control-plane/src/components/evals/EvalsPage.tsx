'use client'
import { motion } from 'framer-motion'
import { useEffect, useState, useCallback } from 'react'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  FlaskConical, RefreshCw, Plus, Trash2, CheckCircle, XCircle,
  ChevronDown, ChevronUp, X, Loader
} from 'lucide-react'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import { toast } from 'sonner'

dayjs.extend(relativeTime)

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface EvalRunData {
  eval_status: 'passed' | 'failed' | 'pending' | string
  score?: number
  passed_tool_calls?: string[]
  failed_tool_calls?: string[]
  reasoning?: string
}

interface EvalRun {
  eval_id: string
  agent_id?: string
  team_id?: string
  model_id?: string
  model_provider?: string
  eval_type: string
  eval_data: EvalRunData
  created_at: string
  input?: string
  expected_output?: string
}

const EVAL_TYPES = ['accuracy', 'agent_as_judge', 'performance', 'reliability'] as const
type EvalType = typeof EVAL_TYPES[number]

// ---------------------------------------------------------------------------
// EvalCard
// ---------------------------------------------------------------------------
const EvalCard = ({ run, onDelete }: { run: EvalRun; onDelete: (id: string) => void }) => {
  const [expanded, setExpanded] = useState(false)
  const passed = run.eval_data?.eval_status === 'passed'
  const score  = run.eval_data?.score

  return (
    <div className="rounded-xl border border-accent bg-primaryAccent">
      <div className="flex items-start gap-3 p-4">
        {passed
          ? <CheckCircle className="mt-0.5 size-4 shrink-0 text-positive" />
          : <XCircle    className="mt-0.5 size-4 shrink-0 text-destructive" />
        }
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-primary">{run.eval_type}</span>
            <span className={cn(
              'rounded-full px-2 py-0.5 text-[10px] uppercase font-medium',
              passed ? 'bg-positive/10 text-positive' : 'bg-destructive/10 text-destructive'
            )}>{run.eval_data?.eval_status}</span>
            {score !== undefined && (
              <span className="rounded-full bg-brand/10 px-2 py-0.5 text-xs text-brand">
                {Math.round(score * 100)}%
              </span>
            )}
            {run.agent_id && <span className="rounded-full bg-accent px-2 py-0.5 text-xs text-muted">{run.agent_id}</span>}
            {run.model_id && <span className="rounded-full bg-accent px-2 py-0.5 text-xs text-muted/60">{run.model_id}</span>}
          </div>
          <div className="mt-0.5 text-xs text-muted/50">
            {run.eval_id.slice(0, 12)}… · {dayjs(run.created_at).fromNow()}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button onClick={() => onDelete(run.eval_id)} className="rounded-lg p-1.5 text-muted hover:bg-destructive/10 hover:text-destructive">
            <Trash2 className="size-3.5" />
          </button>
          <button onClick={() => setExpanded(!expanded)} className="rounded-lg p-1.5 text-muted hover:bg-accent hover:text-primary">
            {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          </button>
        </div>
      </div>
      {expanded && (
        <div className="border-t border-accent px-4 pb-4 pt-3 space-y-3 text-xs">
          {run.input && (
            <div>
              <div className="text-muted/60 uppercase mb-0.5">Input</div>
              <pre className="rounded-xl bg-background p-3 text-xs text-primary whitespace-pre-wrap">{run.input}</pre>
            </div>
          )}
          {run.expected_output && (
            <div>
              <div className="text-muted/60 uppercase mb-0.5">Expected</div>
              <pre className="rounded-xl bg-background p-3 text-xs text-primary whitespace-pre-wrap">{run.expected_output}</pre>
            </div>
          )}
          {run.eval_data?.reasoning && (
            <div>
              <div className="text-muted/60 uppercase mb-0.5">Reasoning</div>
              <p className="text-primary leading-relaxed">{run.eval_data.reasoning}</p>
            </div>
          )}
          {(run.eval_data?.passed_tool_calls?.length ?? 0) > 0 && (
            <div>
              <div className="mb-1 text-positive uppercase">Passed Tool Calls</div>
              <div className="flex flex-wrap gap-1">
                {run.eval_data.passed_tool_calls!.map((tc) => (
                  <span key={tc} className="rounded-full bg-positive/10 px-2 py-0.5 text-positive">{tc}</span>
                ))}
              </div>
            </div>
          )}
          {(run.eval_data?.failed_tool_calls?.length ?? 0) > 0 && (
            <div>
              <div className="mb-1 text-destructive uppercase">Failed Tool Calls</div>
              <div className="flex flex-wrap gap-1">
                {run.eval_data.failed_tool_calls!.map((tc) => (
                  <span key={tc} className="rounded-full bg-destructive/10 px-2 py-0.5 text-destructive">{tc}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Run Eval Modal
// ---------------------------------------------------------------------------
const RunEvalModal = ({
  onClose,
  onSubmit,
}: {
  onClose: () => void
  onSubmit: (body: Record<string, unknown>) => Promise<void>
}) => {
  const { selectedEndpoint, authToken } = useStore()
  const [agents, setAgents] = useState<{ agent_id: string; name?: string }[]>([])
  const [form, setForm] = useState({
    agent_id: '',
    eval_type: 'accuracy' as EvalType,
    input: '',
    expected_output: '',
    criteria: '',
    num_iterations: 1,
  })
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!selectedEndpoint) return
    const headers: HeadersInit = { 'Content-Type': 'application/json' }
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`
    fetch(APIRoutes.GetAgents(selectedEndpoint), { headers })
      .then((r) => r.json())
      .then((d) => {
        // API may return a plain array or { agents: [...] } or { data: [...] }
        const list = Array.isArray(d) ? d : (d?.agents ?? d?.data ?? [])
        setAgents(list)
      })
      .catch(() => {})
  }, [selectedEndpoint, authToken])

  const handleSubmit = async () => {
    if (!form.agent_id) { toast.error('Please select an agent'); return }
    if (!form.input.trim()) { toast.error('Input is required'); return }
    const body: Record<string, unknown> = {
      eval_type: form.eval_type,
      input: form.input,
      num_iterations: form.num_iterations,
    }
    if (form.agent_id)        body.agent_id        = form.agent_id
    if (form.expected_output) body.expected_output = form.expected_output
    if (form.criteria)        body.criteria        = form.criteria
    setSubmitting(true)
    await onSubmit(body)
    setSubmitting(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-accent bg-background p-6 shadow-xl mx-4">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-primary">
            <FlaskConical className="size-4 text-brand" />Run Evaluation
          </h2>
          <button onClick={onClose} className="rounded-lg p-1 text-muted hover:bg-accent hover:text-primary">
            <X className="size-4" />
          </button>
        </div>

        <div className="space-y-3">
          {/* Agent */}
          <div>
            <label className="mb-1 block text-xs text-muted uppercase">Agent *</label>
            <select
              value={form.agent_id}
              onChange={(e) => setForm({ ...form, agent_id: e.target.value })}
              className="w-full rounded-xl border border-accent bg-primaryAccent px-3 py-2 text-xs text-primary outline-none focus:border-primary/30"
            >
              <option value="">— select an agent —</option>
              {agents.map((a) => {
                const key = (a as any).agent_id ?? (a as any).id ?? ''
                const label = (a as any).name ? `${(a as any).name} (${key})` : key
                return <option key={key} value={key}>{label}</option>
              })}
            </select>
          </div>

          {/* Eval type */}
          <div>
            <label className="mb-1 block text-xs text-muted uppercase">Eval Type</label>
            <div className="flex gap-1 rounded-xl border border-accent bg-primaryAccent p-1">
              {EVAL_TYPES.map((t) => (
                <button
                  key={t}
                  onClick={() => setForm({ ...form, eval_type: t })}
                  className={cn(
                    'flex-1 rounded-lg py-1 text-xs capitalize transition-colors',
                    form.eval_type === t ? 'bg-accent text-primary' : 'text-muted hover:text-primary'
                  )}
                >{t}</button>
              ))}
            </div>
          </div>

          {/* Input */}
          <div>
            <label className="mb-1 block text-xs text-muted uppercase">Input *</label>
            <textarea
              value={form.input}
              onChange={(e) => setForm({ ...form, input: e.target.value })}
              rows={3}
              placeholder="The prompt or message to send to the agent…"
              className="w-full rounded-xl border border-accent bg-primaryAccent px-3 py-2 text-xs text-primary outline-none resize-none focus:border-primary/30"
            />
          </div>

          {/* Expected output */}
          <div>
            <label className="mb-1 block text-xs text-muted uppercase">Expected Output (optional)</label>
            <textarea
              value={form.expected_output}
              onChange={(e) => setForm({ ...form, expected_output: e.target.value })}
              rows={2}
              placeholder="What the agent should respond with…"
              className="w-full rounded-xl border border-accent bg-primaryAccent px-3 py-2 text-xs text-primary outline-none resize-none focus:border-primary/30"
            />
          </div>

          {/* Criteria */}
          {form.eval_type === 'agent_as_judge' && (
            <div>
              <label className="mb-1 block text-xs text-muted uppercase">Evaluation Criteria</label>
              <input
                value={form.criteria}
                onChange={(e) => setForm({ ...form, criteria: e.target.value })}
                placeholder="e.g. The response must mention the login button"
                className="w-full rounded-xl border border-accent bg-primaryAccent px-3 py-2 text-xs text-primary outline-none focus:border-primary/30"
              />
            </div>
          )}

          {/* Iterations */}
          <div>
            <label className="mb-1 block text-xs text-muted uppercase">Iterations</label>
            <input
              type="number"
              min={1}
              max={10}
              value={form.num_iterations}
              onChange={(e) => setForm({ ...form, num_iterations: parseInt(e.target.value) || 1 })}
              className="w-32 rounded-xl border border-accent bg-primaryAccent px-3 py-2 text-xs text-primary outline-none focus:border-primary/30"
            />
          </div>

          <div className="flex gap-2 pt-2">
            <Button onClick={handleSubmit} disabled={submitting} className="gap-1.5 flex-1">
              {submitting ? <Loader className="size-3.5 animate-spin" /> : <FlaskConical className="size-3.5" />}
              {submitting ? 'Running…' : 'Run Eval'}
            </Button>
            <Button variant="outline" onClick={onClose}>Cancel</Button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// EvalsPage
// ---------------------------------------------------------------------------
export default function EvalsPage() {
  const { selectedEndpoint, authToken } = useStore()
  const [runs, setRuns] = useState<EvalRun[]>([])
  const [loading, setLoading] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [filterType, setFilterType] = useState<string>('all')

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
  }

  const fetchRuns = useCallback(async () => {
    if (!selectedEndpoint) return
    setLoading(true)
    try {
      const res = await fetch(APIRoutes.GetEvalRuns(selectedEndpoint), { headers })
      if (res.ok) {
        const d = await res.json()
        setRuns(d?.eval_runs ?? d?.data ?? d ?? [])
      }
    } catch { /* silent */ }
    finally { setLoading(false) }
  }, [selectedEndpoint, authToken])

  const handleDelete = async (id: string) => {
    if (!selectedEndpoint) return
    try {
      await fetch(APIRoutes.DeleteEvalRun(selectedEndpoint, id), { method: 'DELETE', headers })
      setRuns((prev) => prev.filter((r) => r.eval_id !== id))
      toast.success('Eval run deleted')
    } catch { toast.error('Delete failed') }
  }

  const handleRunEval = async (body: Record<string, unknown>) => {
    if (!selectedEndpoint) return
    try {
      const res = await fetch(APIRoutes.CreateEvalRun(selectedEndpoint), {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error(await res.text())
      toast.success('Eval submitted')
      setShowModal(false)
      setTimeout(fetchRuns, 1500)
    } catch (e) {
      toast.error(`Eval failed: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  useEffect(() => { fetchRuns() }, [fetchRuns])

  const passCount = runs.filter((r) => r.eval_data?.eval_status === 'passed').length
  const failCount = runs.filter((r) => r.eval_data?.eval_status === 'failed').length
  const filtered  = filterType === 'all' ? runs : runs.filter((r) => r.eval_type === filterType)

  const uniqueTypes = Array.from(new Set(runs.map((r) => r.eval_type)))

  return (
    <motion.div className="h-full overflow-y-auto p-6" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2, ease: 'easeOut' }}>
      <div className="mx-auto max-w-4xl space-y-6">

        <div className="flex items-start justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-medium text-primary">
              <FlaskConical className="size-5 text-brand" />Evals
            </h1>
            <p className="mt-1 text-xs text-muted">Run and track agent evaluations — accuracy, judge, performance, reliability</p>
          </div>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => setShowModal(true)} className="gap-1.5">
              <Plus className="size-3.5" />Run Eval
            </Button>
            <Button size="sm" variant="outline" onClick={fetchRuns} disabled={loading} className="gap-1.5">
              <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />Refresh
            </Button>
          </div>
        </div>

        {/* Stats */}
        {!loading && runs.length > 0 && (
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl border border-accent bg-primaryAccent p-3">
              <div className="text-xs text-muted uppercase">Total</div>
              <div className="text-2xl font-semibold text-primary">{runs.length}</div>
            </div>
            <div className="rounded-xl border border-positive/30 bg-primaryAccent p-3">
              <div className="text-xs text-positive uppercase">Passed</div>
              <div className="text-2xl font-semibold text-positive">{passCount}</div>
            </div>
            <div className="rounded-xl border border-destructive/30 bg-primaryAccent p-3">
              <div className="text-xs text-destructive uppercase">Failed</div>
              <div className="text-2xl font-semibold text-destructive">{failCount}</div>
            </div>
          </div>
        )}

        {/* Type filter */}
        {uniqueTypes.length > 0 && (
          <div className="flex gap-1 rounded-xl border border-accent bg-primaryAccent p-1 overflow-x-auto">
            {['all', ...uniqueTypes].map((t) => (
              <button
                key={t}
                onClick={() => setFilterType(t)}
                className={cn(
                  'shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium capitalize transition-colors',
                  filterType === t ? 'bg-accent text-primary' : 'text-muted hover:text-primary'
                )}
              >{t}</button>
            ))}
          </div>
        )}

        {/* List */}
        <div className="space-y-3">
          {loading ? (
            Array.from({length: 3}).map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-accent bg-primaryAccent py-16 text-center">
              <FlaskConical className="size-10 text-muted/20" />
              <p className="mt-3 text-sm font-medium text-muted">No eval runs yet</p>
              <p className="mt-1 text-xs text-muted/60">Click &quot;Run Eval&quot; to evaluate an agent.</p>
              <Button size="sm" className="mt-4 gap-1.5" onClick={() => setShowModal(true)}>
                <Plus className="size-3.5" />Run First Eval
              </Button>
            </div>
          ) : (
            filtered.map((run) => <EvalCard key={run.eval_id} run={run} onDelete={handleDelete} />)
          )}
        </div>
      </div>

      {showModal && (
        <RunEvalModal onClose={() => setShowModal(false)} onSubmit={handleRunEval} />
      )}
    </motion.div>
  )
}
