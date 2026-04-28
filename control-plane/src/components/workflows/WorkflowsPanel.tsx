'use client'
import { useState } from 'react'
import { useStore } from '@/store'
import { Button } from '@/components/ui/button'
import { TextArea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { triggerWorkflowAPI } from '@/api/qap'
import { WorkflowStatus } from '@/types/qap'
import { toast } from 'sonner'
import { Play, Circle, CheckCircle, XCircle, Loader, GitBranch, Search, FileCode, Wrench } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import rehypeSanitize from 'rehype-sanitize'

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

const StatusIcon = ({ status }: { status: WorkflowStatus | null }) => {
  if (!status) return <Circle className="size-4 text-muted/40" />
  if (status === 'running') return <Loader className="size-4 animate-spin text-warning" />
  if (status === 'completed') return <CheckCircle className="size-4 text-positive" />
  if (status === 'failed') return <XCircle className="size-4 text-destructive" />
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
  const [status, setStatus] = useState<WorkflowStatus | null>(null)
  const [output, setOutput] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)

  const selectedWf = WORKFLOWS.find((w) => w.id === selectedId)

  const handleTrigger = async () => {
    if (!selectedId || !input.trim()) return
    setIsRunning(true)
    setStatus('running')
    setOutput(null)

    try {
      const result = await triggerWorkflowAPI(selectedEndpoint, selectedId, input, authToken)
      if (result) {
        setStatus('completed')
        setOutput(typeof result === 'object' ? JSON.stringify(result, null, 2) : String(result))
        toast.success(`${selectedWf?.name} completed`)
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
              }}
            />
          ))}
        </div>

        {/* Input panel */}
        {selectedWf && (
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
              disabled={isRunning}
            />

            <div className="mt-3 flex items-center justify-between">
              <p className="text-xs text-muted">{selectedWf.description}</p>
              <Button
                onClick={handleTrigger}
                disabled={!input.trim() || isRunning}
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
