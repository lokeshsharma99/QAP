'use client'
import { useState, useEffect, useCallback } from 'react'
import { useStore } from '@/store'
import { Button } from '@/components/ui/button'
import { TextArea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { APIRoutes } from '@/api/routes'
import { triggerWorkflowAPI } from '@/api/qap'
import { WorkflowStatus } from '@/types/qap'
import { toast } from 'sonner'
import {
  Play, Circle, CheckCircle, XCircle, Loader, GitBranch, Search, FileCode,
  Wrench, History, RefreshCw, PlayCircle, PauseCircle
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import rehypeSanitize from 'rehype-sanitize'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

const WORKFLOWS = [
  {
    id: 'spec-to-code',
    name: 'Spec to Code',
    description: 'Requirement → Gherkin → Playwright automation code',
    icon: FileCode,
    placeholder: 'Paste a Jira ticket ID or requirement description…\n\nExample: PROJ-123: Add login page with MFA support'
  },
  {
    id: 'discovery-onboard',
    name: 'Discovery Onboard',
    description: 'AUT URL → Site Manifesto → PgVector KB',
    icon: Search,
    placeholder: 'Enter the AUT URL to crawl…\n\nExample: https://demo.nopcommerce.com/'
  },
  {
    id: 'triage-heal',
    name: 'Triage & Heal',
    description: 'Trace ZIP → RCA Report → Healing Patch',
    icon: Wrench,
    placeholder: 'Paste CI failure log or test name…\n\nExample: [FAILED] Login test — Element not found: data-testid="login-btn"'
  }
]

interface WorkflowRun {
  run_id: string
  workflow_id?: string
  status: string
  created_at?: string
  updated_at?: string
  input?: string
  output?: string
}

const StatusIcon = ({ status }: { status: WorkflowStatus | string | null }) => {
  if (!status) return <Circle className="size-4 text-muted/40" />
  if (status === 'running')   return <Loader className="size-4 animate-spin text-warning" />
  if (status === 'completed') return <CheckCircle className="size-4 text-positive" />
  if (status === 'failed')    return <XCircle className="size-4 text-destructive" />
  if (status === 'paused')    return <PauseCircle className="size-4 text-warning" />
  return <Circle className="size-4 text-muted" />
}

const WorkflowCard = ({
  workflow,
  isSelected,
  onClick
}: {
  workflow: (typeof WORKFLOWS)[0]
  isSelected: boolean
  onClick: () => void
}) => {
  const Ico = workflow.icon
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex flex-col gap-2 rounded-xl border p-4 text-left transition-colors',
        isSelected
          ? 'border-brand/50 bg-accent/70'
          : 'border-accent bg-primaryAccent hover:border-primary/20'
      )}
    >
      <div className="flex items-center gap-2">
        <Ico className="size-4 text-brand" />
        <span className="text-sm font-medium text-primary">{workflow.name}</span>
      </div>
      <p className="text-xs text-muted">{workflow.description}</p>
    </button>
  )
}

export default function WorkflowsPanel() {
  const { selectedEndpoint, authToken } = useStore()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [status, setStatus] = useState<WorkflowStatus | string | null>(null)
  const [output, setOutput] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [currentRunId, setCurrentRunId] = useState<string | null>(null)
  const [tab, setTab] = useState<'run' | 'history'>('run')
  const [runs, setRuns] = useState<WorkflowRun[]>([])
  const [runsLoading, setRunsLoading] = useState(false)
  const [continuing, setContinuing] = useState(false)

  const selectedWf = WORKFLOWS.find((w) => w.id === selectedId)
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
  }

  const fetchRuns = useCallback(async (wfId: string) => {
    if (!selectedEndpoint || !wfId) return
    setRunsLoading(true)
    try {
      const res = await fetch(APIRoutes.GetWorkflowRuns(selectedEndpoint, wfId), { headers })
      if (res.ok) {
        const d = await res.json()
        setRuns(d?.runs ?? d?.data ?? d ?? [])
      }
    } catch { /* silent */ }
    finally { setRunsLoading(false) }
  }, [selectedEndpoint, authToken])

  const handleTrigger = async () => {
    if (!selectedId || !input.trim()) return
    setIsRunning(true)
    setStatus('running')
    setOutput(null)
    setCurrentRunId(null)

    try {
      const result = await triggerWorkflowAPI(selectedEndpoint, selectedId, input, authToken)
      if (result) {
        const runId = (result as { run_id?: string })?.run_id
        if (runId) setCurrentRunId(runId)
        const resultStatus = (result as { status?: string })?.status?.toLowerCase()
        if (resultStatus === 'paused') {
          setStatus('paused')
          toast.info(`${selectedWf?.name} paused — awaiting human review`)
        } else {
          setStatus('completed')
          setOutput(typeof result === 'object' ? JSON.stringify(result, null, 2) : String(result))
          toast.success(`${selectedWf?.name} completed`)
        }
      } else {
        setStatus('failed')
        toast.error('Workflow failed — check AgentOS logs')
      }
    } catch (err) {
      setStatus('failed')
      toast.error(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setIsRunning(false)
    }
  }

  const handleContinue = async (continueInput = '') => {
    if (!selectedId || !currentRunId) return
    setContinuing(true)
    try {
      const res = await fetch(APIRoutes.ContinueWorkflowRun(selectedEndpoint, selectedId, currentRunId), {
        method: 'POST',
        headers,
        body: JSON.stringify({ input: continueInput || undefined }),
      })
      if (!res.ok) throw new Error(res.statusText)
      const data = await res.json()
      const resultStatus = (data?.status ?? '').toLowerCase()
      setStatus(resultStatus || 'running')
      if (data?.output) setOutput(typeof data.output === 'string' ? data.output : JSON.stringify(data.output, null, 2))
      toast.success('Workflow continued')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Continue failed')
    } finally {
      setContinuing(false)
    }
  }

  useEffect(() => {
    if (tab === 'history' && selectedId) fetchRuns(selectedId)
  }, [tab, selectedId, fetchRuns])

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-4xl space-y-6">
        <div>
          <h1 className="flex items-center gap-2 text-lg font-medium text-primary">
            <GitBranch className="size-5 text-brand" />
            Workflows
          </h1>
          <p className="mt-1 text-xs text-muted">
            Trigger QAP pipelines and monitor their progress
          </p>
        </div>

        {/* Workflow selector */}
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {WORKFLOWS.map((wf) => (
            <WorkflowCard
              key={wf.id}
              workflow={wf}
              isSelected={selectedId === wf.id}
              onClick={() => {
                setSelectedId(wf.id)
                setInput('')
                setStatus(null)
                setOutput(null)
                setCurrentRunId(null)
                setTab('run')
              }}
            />
          ))}
        </div>

        {selectedWf && (
          <>
            {/* Tab switcher */}
            <div className="flex gap-1 rounded-xl border border-accent bg-primaryAccent p-1">
              <button
                onClick={() => setTab('run')}
                className={cn(
                  'flex-1 rounded-lg py-1.5 text-xs font-medium uppercase transition-colors',
                  tab === 'run' ? 'bg-accent text-primary' : 'text-muted hover:text-primary'
                )}
              >
                <span className="flex items-center justify-center gap-1.5"><PlayCircle className="size-3.5" />Run</span>
              </button>
              <button
                onClick={() => setTab('history')}
                className={cn(
                  'flex-1 rounded-lg py-1.5 text-xs font-medium uppercase transition-colors',
                  tab === 'history' ? 'bg-accent text-primary' : 'text-muted hover:text-primary'
                )}
              >
                <span className="flex items-center justify-center gap-1.5"><History className="size-3.5" />History</span>
              </button>
            </div>

            {tab === 'run' ? (
              <>
                {/* Input panel */}
                <div className="rounded-xl border border-accent bg-primaryAccent p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <h3 className="text-sm font-medium text-primary">{selectedWf.name}</h3>
                    <StatusIcon status={status} />
                  </div>

                  <TextArea
                    placeholder={selectedWf.placeholder}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    className="min-h-[120px] bg-background text-sm"
                    disabled={isRunning || status === 'paused'}
                  />

                  <div className="mt-3 flex items-center justify-between gap-2">
                    <p className="text-xs text-muted">{selectedWf.description}</p>
                    <div className="flex gap-2">
                      {status === 'paused' && currentRunId && (
                        <Button
                          onClick={() => handleContinue()}
                          disabled={continuing}
                          size="sm"
                          variant="outline"
                          className="gap-2 border-warning/50 text-warning hover:bg-warning/10"
                        >
                          {continuing ? <Loader className="size-4 animate-spin" /> : <PlayCircle className="size-4" />}
                          {continuing ? 'Continuing…' : 'Continue (HITL)'}
                        </Button>
                      )}
                      <Button
                        onClick={handleTrigger}
                        disabled={!input.trim() || isRunning || status === 'paused'}
                        size="sm"
                        className="gap-2"
                      >
                        {isRunning ? (
                          <Loader className="size-4 animate-spin" />
                        ) : (
                          <Play className="size-4" />
                        )}
                        {isRunning ? 'Running…' : 'Run Workflow'}
                      </Button>
                    </div>
                  </div>
                </div>

                {status === 'paused' && (
                  <div className="flex items-center gap-3 rounded-xl border border-warning/30 bg-warning/5 p-4">
                    <PauseCircle className="size-5 shrink-0 text-warning" />
                    <div>
                      <div className="text-sm font-medium text-warning">Workflow paused — Human review required</div>
                      <div className="mt-0.5 text-xs text-muted">The Judge flagged confidence &lt; 90%. Check the Approvals page, then click &quot;Continue (HITL)&quot;.</div>
                    </div>
                  </div>
                )}

                {/* Output */}
                {output && (
                  <div className="rounded-xl border border-accent bg-primaryAccent p-4">
                    <div className="mb-3 flex items-center gap-2">
                      <StatusIcon status={status} />
                      <h3 className="text-sm font-medium text-primary">Output</h3>
                    </div>
                    <div className="prose prose-invert max-w-none text-sm">
                      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw, rehypeSanitize]}>
                        {output}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}
              </>
            ) : (
              /* History tab */
              <div className="space-y-3">
                <div className="flex justify-end">
                  <Button size="sm" variant="outline" onClick={() => fetchRuns(selectedId!)} disabled={runsLoading} className="gap-1.5">
                    <RefreshCw className={cn('size-3.5', runsLoading && 'animate-spin')} />Refresh
                  </Button>
                </div>
                {runsLoading ? (
                  Array.from({length: 3}).map((_, i) => <Skeleton key={i} className="h-14 rounded-xl" />)
                ) : runs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center rounded-xl border border-accent bg-primaryAccent py-12 text-center">
                    <History className="size-8 text-muted/20" />
                    <p className="mt-3 text-sm text-muted">No runs yet</p>
                  </div>
                ) : (
                  runs.map((run) => (
                    <div key={run.run_id} className="rounded-xl border border-accent bg-primaryAccent p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <StatusIcon status={run.status} />
                          <span className="font-mono text-xs text-primary">{run.run_id.slice(0, 12)}…</span>
                          <span className={cn(
                            'rounded-full px-2 py-0.5 text-[10px] uppercase font-medium',
                            run.status === 'completed' ? 'bg-positive/10 text-positive' :
                            run.status === 'failed'    ? 'bg-destructive/10 text-destructive' :
                            run.status === 'paused'    ? 'bg-warning/10 text-warning' : 'bg-accent text-muted'
                          )}>{run.status}</span>
                        </div>
                        <span className="text-xs text-muted">
                          {run.created_at ? dayjs(run.created_at).fromNow() : ''}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}

        {/* Empty state */}
        {!selectedId && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <GitBranch className="size-8 text-muted/30" />
            <p className="mt-3 text-sm text-muted">Select a workflow above to get started</p>
          </div>
        )}
      </div>
    </div>
  )
}

