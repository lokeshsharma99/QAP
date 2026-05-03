'use client'
import { motion } from 'framer-motion'
import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { GherkinSpec } from '@/types/qap'
import { toast } from 'sonner'
import { FileCheck, CheckCircle, XCircle, Clock, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'
import { useStore } from '@/store'
import { getAllSessionsAPI, getSessionAPI } from '@/api/os'
import { Sessions } from '@/types/os'
import { ApprovalBlock } from '@/components/ui/ApprovalBlock'

// ---------------------------------------------------------------------------
// JSON extraction helpers
// ---------------------------------------------------------------------------

function extractJson(text: string): unknown | null {
  try { return JSON.parse(text) } catch { /* noop */ }
  const match = text.match(/```(?:json)?\s*([\s\S]*?)```/)
  if (match) { try { return JSON.parse(match[1].trim()) } catch { /* noop */ } }
  const braceMatch = text.match(/\{[\s\S]*\}/)
  if (braceMatch) { try { return JSON.parse(braceMatch[0]) } catch { /* noop */ } }
  return null
}

function isGherkinSpec(obj: unknown): obj is Record<string, unknown> {
  if (!obj || typeof obj !== 'object') return false
  const o = obj as Record<string, unknown>
  return typeof o.feature_content === 'string' && typeof o.feature_file === 'string'
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const ConfidenceBadge = ({ confidence }: { confidence?: number }) => {
  if (!confidence) return null
  const pct = Math.round(confidence * 100)
  return (
    <span className={cn(
      'rounded-full px-2 py-0.5 text-xs font-medium',
      pct >= 90 ? 'bg-positive/10 text-positive' : pct >= 70 ? 'bg-warning/10 text-warning' : 'bg-destructive/10 text-destructive'
    )}>
      {pct}% confidence
    </span>
  )
}

const StatusBadge = ({ status }: { status: GherkinSpec['status'] }) => {
  const config = {
    pending:  { icon: Clock,        label: 'Pending Review', cls: 'bg-warning/10 text-warning' },
    approved: { icon: CheckCircle,  label: 'Approved',       cls: 'bg-positive/10 text-positive' },
    rejected: { icon: XCircle,      label: 'Rejected',       cls: 'bg-destructive/10 text-destructive' },
  }[status]
  const Ico = config.icon
  return (
    <span className={cn('flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium', config.cls)}>
      <Ico className="size-3" />
      {config.label}
    </span>
  )
}

const SpecCard = ({
  spec,
  onApprove,
  onReject,
}: {
  spec: GherkinSpec
  onApprove: (id: string) => void
  onReject: (id: string) => void
}) => {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className={cn(
      'rounded-xl border bg-primaryAccent transition-colors',
      spec.status === 'pending'  ? 'border-warning/30'  :
      spec.status === 'approved' ? 'border-positive/30' : 'border-destructive/30'
    )}>
      <div className="flex items-start gap-3 p-4">
        <FileCheck className="mt-0.5 size-4 shrink-0 text-brand" />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-primary">{spec.ticket_id || '—'}</span>
            <StatusBadge status={spec.status} />
            <ConfidenceBadge confidence={spec.confidence} />
          </div>
          <div className="mt-0.5 truncate text-xs text-muted">{spec.feature_file}</div>
        </div>
        <button onClick={() => setExpanded(!expanded)} className="shrink-0 text-muted hover:text-primary">
          {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
        </button>
      </div>

      {expanded && (
        <div className="border-t border-accent px-4 pb-4">
          <pre className="mt-3 overflow-x-auto rounded-xl bg-background p-4 text-xs text-primary leading-relaxed">
            {spec.feature_content}
          </pre>
          {spec.rejection_reasons && spec.rejection_reasons.length > 0 && (
            <div className="mt-2 rounded-xl border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
              {spec.rejection_reasons.join(', ')}
            </div>
          )}
          {spec.status === 'pending' && (
            <div className="mt-3 flex gap-2">
              <Button size="sm" onClick={() => onApprove(spec.id)} className="gap-1.5 bg-positive text-background hover:bg-positive/90">
                <CheckCircle className="size-3.5" />Approve
              </Button>
              <Button size="sm" variant="outline" onClick={() => onReject(spec.id)} className="gap-1.5 border-destructive/40 text-destructive hover:bg-destructive/10">
                <XCircle className="size-3.5" />Reject
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function SpecReview() {
  const searchParams = useSearchParams()
  // Only allow 'scribe' — ignore any other ?agent= param to prevent wrong display
  const agentId = 'scribe'
  const dbId    = searchParams.get('db_id') ?? 'quality-autopilot-db'

  const { selectedEndpoint, authToken, setPendingCounts } = useStore()

  const [specs,   setSpecs]   = useState<GherkinSpec[]>([])
  const [loading, setLoading] = useState(false)
  const [filter,  setFilter]  = useState<GherkinSpec['status'] | 'all'>('all')

  const fetchSpecs = useCallback(async () => {
    if (!selectedEndpoint) return
    setLoading(true)
    try {
      const sessionsRes = await getAllSessionsAPI(
        selectedEndpoint, 'agent', agentId, dbId, authToken || undefined
      ) as Sessions | { data: [] }
      const sessions = sessionsRes.data ?? []

      const found: GherkinSpec[] = []

      for (const session of sessions) {
        try {
          const runs = await getSessionAPI(selectedEndpoint, 'agent', session.session_id, dbId, authToken || undefined)
          const runList: { messages?: { role: string; content: string | null }[] }[] =
            Array.isArray(runs) ? runs : (runs?.runs ?? [])

          for (const run of runList) {
            for (const msg of run.messages ?? []) {
              if (msg.role !== 'assistant' || !msg.content) continue
              const parsed = extractJson(msg.content)
              if (!isGherkinSpec(parsed)) continue
              const p = parsed as Record<string, unknown>
              found.push({
                id:                String(p.ticket_id ?? `${session.session_id}-${found.length}`),
                ticket_id:         String(p.ticket_id ?? ''),
                feature_file:      String(p.feature_file ?? ''),
                feature_content:   String(p.feature_content ?? ''),
                status:            (p.status as GherkinSpec['status']) ?? 'pending',
                created_at:        String(p.created_at ?? new Date(session.created_at * 1000).toISOString()),
                confidence:        typeof p.confidence === 'number' ? p.confidence : undefined,
                rejection_reasons: Array.isArray(p.rejection_reasons) ? p.rejection_reasons as string[] : undefined,
              })
            }
          }
        } catch { /* skip failed session */ }
      }

      setSpecs(found)
      // Update sidebar badge with actual pending count
      setPendingCounts({ specReview: found.filter(s => s.status === 'pending').length })
    } catch {
      toast.error('Failed to load Gherkin specs')
    } finally {
      setLoading(false)
    }
  }, [selectedEndpoint, agentId, dbId, authToken])

  useEffect(() => { fetchSpecs() }, [fetchSpecs])

  const handleApprove = (id: string) => {
    setSpecs((prev) => {
      const next = prev.map((s) => s.id === id ? { ...s, status: 'approved' as const } : s)
      setPendingCounts({ specReview: next.filter(s => s.status === 'pending').length })
      return next
    })
    toast.success('Spec approved — Judge confidence met')
  }
  const handleReject = (id: string) => {
    setSpecs((prev) => {
      const next = prev.map((s) => s.id === id ? { ...s, status: 'rejected' as const } : s)
      setPendingCounts({ specReview: next.filter(s => s.status === 'pending').length })
      return next
    })
    toast.error('Spec rejected — Sent back to Scribe agent')
  }

  const filtered = filter === 'all' ? specs : specs.filter((s) => s.status === filter)
  const counts = {
    all:      specs.length,
    pending:  specs.filter((s) => s.status === 'pending').length,
    approved: specs.filter((s) => s.status === 'approved').length,
    rejected: specs.filter((s) => s.status === 'rejected').length,
  }

  return (
    <motion.div className="h-full overflow-y-auto p-6" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2, ease: 'easeOut' }}>
      <div className="mx-auto max-w-4xl space-y-6">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-medium text-primary">
              <FileCheck className="size-5 text-brand" />
              Spec Review
            </h1>
            <p className="mt-1 text-xs text-muted">
              Human Lead review panel — Gherkin specs from the <span className="text-primary">{agentId}</span> agent
            </p>
            <p className="mt-0.5 text-xs text-muted/50">
              Judge auto-approves specs with ≥90% confidence. Specs below 90% appear here for review.
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={fetchSpecs} disabled={loading} className="gap-1.5">
            <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />
            Refresh
          </Button>
        </div>

        {/* Approval block — shows pending agent approvals (Judge gate, HITL) */}
        <ApprovalBlock
          label="Scribe / Strategy squad paused — approve or reject to continue the run"
        />

        {/* Filter tabs */}
        <div className="flex gap-1 rounded-xl border border-accent bg-primaryAccent p-1">
          {(['all', 'pending', 'approved', 'rejected'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                'flex-1 rounded-lg px-3 py-1.5 text-xs font-medium uppercase transition-colors',
                filter === f ? 'bg-accent text-primary' : 'text-muted hover:text-primary'
              )}
            >
              {f}{f !== 'all' && specs.length > 0 ? ` (${counts[f]})` : ''}
            </button>
          ))}
        </div>

        {/* Spec list */}
        <div className="space-y-3">
          {loading ? (
            Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-accent bg-primaryAccent py-16 text-center">
              <FileCheck className="size-10 text-muted/20" />
              <p className="mt-3 text-sm font-medium text-muted">No specs found</p>
              <p className="mt-1 text-xs text-muted/60">
                Specs appear here when the <span className="text-primary">{agentId}</span> agent produces{' '}
                <code className="text-xs">GherkinSpec</code> output in its sessions.
              </p>
            </div>
          ) : (
            filtered.map((spec) => (
              <SpecCard key={spec.id} spec={spec} onApprove={handleApprove} onReject={handleReject} />
            ))
          )}
        </div>
      </div>
    </motion.div>
  )
}
