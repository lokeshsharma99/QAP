'use client'
/**
 * ApprovalBlock — inline approval card rendered in the chat window.
 *
 * Props:
 *   runId     – filter to approvals whose run_id matches (optional)
 *   sessionId – filter to approvals whose session_id matches (optional)
 *
 * When neither is provided every pending approval is shown (full-queue mode).
 * Polls every 5 s while approvals are pending; stops when queue is empty.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import {
  ShieldCheck, CheckCircle, XCircle, Clock, ChevronDown, ChevronUp,
  Cpu, GitBranch, Zap, AlertCircle, Timer, User,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import { toast } from 'sonner'

dayjs.extend(relativeTime)

// ---------------------------------------------------------------------------
// Types (local — mirrors ApprovalsPage types)
// ---------------------------------------------------------------------------
type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired' | 'cancelled'

interface Requirement { name?: string; description?: string; type?: string; [key: string]: unknown }

interface Approval {
  id: string
  run_id: string
  session_id: string
  status: ApprovalStatus
  source_type: string
  approval_type?: string | null
  pause_type?: string | null
  tool_name?: string | null
  tool_args?: Record<string, unknown> | null
  expires_at?: number | null
  agent_id?: string | null
  team_id?: string | null
  workflow_id?: string | null
  user_id?: string | null
  source_name?: string | null
  requirements?: Requirement[] | null
  context?: Record<string, unknown> | null
  resolution_data?: Record<string, unknown> | null
  resolved_by?: string | null
  resolved_at?: number | null
  created_at?: number | null
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const fmtTs = (ts?: number | null) => (ts ? dayjs.unix(ts).format('HH:mm:ss') : '')
const fromNow = (ts?: number | null) => (ts ? dayjs.unix(ts).fromNow() : '')

// ---------------------------------------------------------------------------
// StatusBadge
// ---------------------------------------------------------------------------
const StatusBadge = ({ status }: { status: ApprovalStatus }) => {
  const cfg: Record<ApprovalStatus, { icon: React.ElementType; cls: string; label: string }> = {
    pending:   { icon: Clock,       cls: 'bg-warning/10 text-warning',         label: 'Pending' },
    approved:  { icon: CheckCircle, cls: 'bg-positive/10 text-positive',       label: 'Approved' },
    rejected:  { icon: XCircle,     cls: 'bg-destructive/10 text-destructive', label: 'Rejected' },
    expired:   { icon: Timer,       cls: 'bg-muted/10 text-muted',             label: 'Expired' },
    cancelled: { icon: XCircle,     cls: 'bg-accent text-muted',               label: 'Cancelled' },
  }
  const { icon: Ico, cls, label } = cfg[status] ?? cfg.pending
  return (
    <span className={cn('flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium', cls)}>
      <Ico className="size-3" />{label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Single approval card (compact)
// ---------------------------------------------------------------------------
const InlineApprovalCard = ({
  approval,
  onResolve,
}: {
  approval: Approval
  onResolve: (id: string, approved: boolean) => void
}) => {
  const [expanded, setExpanded] = useState(false)
  const SourceIcon = approval.team_id ? GitBranch : approval.workflow_id ? Zap : Cpu
  const sourceLabel = approval.source_name ?? approval.agent_id ?? approval.team_id ?? approval.workflow_id ?? approval.source_type
  const expiresInMs = approval.expires_at ? (approval.expires_at * 1000) - Date.now() : null
  const isExpiringSoon = expiresInMs !== null && expiresInMs > 0 && expiresInMs < 5 * 60 * 1000

  return (
    <div className="rounded-xl border border-warning/40 bg-primaryAccent shadow-sm shadow-warning/10">
      {/* Header */}
      <div className="flex items-start gap-3 p-3">
        <ShieldCheck className="mt-0.5 size-4 shrink-0 text-warning" />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            {approval.tool_name ? (
              <code className="font-mono text-[11px] bg-accent px-1.5 py-0.5 rounded text-primary">{approval.tool_name}</code>
            ) : (
              <span className="text-xs font-medium text-primary">{approval.approval_type ?? 'Approval Required'}</span>
            )}
            <StatusBadge status={approval.status} />
            <span className="flex items-center gap-1 rounded-full bg-brand/10 px-2 py-0.5 text-[10px] text-brand">
              <SourceIcon className="size-3" />{sourceLabel}
            </span>
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-2 text-[10px] text-muted/50">
            {approval.created_at && <span>{fmtTs(approval.created_at)}</span>}
            {approval.user_id && <span>· <User className="inline size-3" /> {approval.user_id}</span>}
            {isExpiringSoon && <span className="text-warning">· Expires {fromNow(approval.expires_at)}</span>}
          </div>
        </div>

        {/* Approve / Reject */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={() => onResolve(approval.id, true)}
            className="flex h-7 items-center gap-1 rounded-lg bg-positive px-2.5 text-xs font-medium text-background hover:bg-positive/90 transition-colors"
          >
            <CheckCircle className="size-3" />Approve
          </button>
          <button
            onClick={() => onResolve(approval.id, false)}
            className="flex h-7 items-center gap-1 rounded-lg border border-destructive/40 px-2.5 text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors"
          >
            <XCircle className="size-3" />Reject
          </button>
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="shrink-0 rounded-lg p-1 text-muted hover:bg-accent hover:text-primary"
        >
          {expanded ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
        </button>
      </div>

      {/* Expanded details */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            className="overflow-hidden"
          >
            <div className="border-t border-accent px-3 pb-3 pt-2 space-y-2 text-xs">
              {/* Requirements */}
              {approval.requirements && approval.requirements.length > 0 && (
                <div>
                  <div className="mb-1 text-[10px] uppercase tracking-wide text-muted/60">Requirements</div>
                  {approval.requirements.map((req, i) => (
                    <div key={i} className="rounded-lg bg-background px-3 py-2 mb-1">
                      {req.name && <div className="font-medium text-primary text-xs">{req.name}</div>}
                      {req.description && <div className="text-muted/70 mt-0.5 text-xs">{req.description}</div>}
                    </div>
                  ))}
                </div>
              )}

              {/* Tool args */}
              {approval.tool_args && Object.keys(approval.tool_args).length > 0 && (
                <div>
                  <div className="mb-1 text-[10px] uppercase tracking-wide text-muted/60">Tool Arguments</div>
                  <pre className="overflow-x-auto rounded-lg bg-background px-3 py-2 text-xs text-primary leading-relaxed max-h-40 overflow-y-auto">
                    {JSON.stringify(approval.tool_args, null, 2)}
                  </pre>
                </div>
              )}

              {/* Context */}
              {approval.context && Object.keys(approval.context).length > 0 && (
                <div>
                  <div className="mb-1 text-[10px] uppercase tracking-wide text-muted/60">Context</div>
                  <pre className="overflow-x-auto rounded-lg bg-background px-3 py-2 text-xs text-muted max-h-24 overflow-y-auto">
                    {JSON.stringify(approval.context, null, 2)}
                  </pre>
                </div>
              )}

              {/* IDs */}
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 rounded-lg bg-background px-3 py-2">
                {[
                  { label: 'Run ID',     value: approval.run_id },
                  { label: 'Session ID', value: approval.session_id },
                  { label: 'Pause Type', value: approval.pause_type },
                ].filter(x => x.value).map(({ label, value }) => (
                  <div key={label}>
                    <div className="text-[9px] uppercase tracking-wide text-muted/50">{label}</div>
                    <div className="font-mono text-[10px] text-primary/80 truncate">{value}</div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ---------------------------------------------------------------------------
// ApprovalBlock — exported component
// ---------------------------------------------------------------------------
export interface ApprovalBlockProps {
  /** Only show approvals matching this run_id */
  runId?: string | null
  /** Only show approvals matching this session_id */
  sessionId?: string | null
  /** Label shown above the card list */
  label?: string
}

export function ApprovalBlock({ runId, sessionId, label }: ApprovalBlockProps) {
  const { selectedEndpoint, authToken } = useStore()
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [loading, setLoading] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
  }

  const fetchPending = useCallback(async () => {
    if (!selectedEndpoint) return
    setLoading(true)
    try {
      const url = new URL(APIRoutes.GetApprovals(selectedEndpoint))
      url.searchParams.set('status', 'pending')
      url.searchParams.set('limit', '50')
      const res = await fetch(url.toString(), { headers })
      if (!res.ok) return
      const d = await res.json()
      let list: Approval[] = d?.data ?? (Array.isArray(d) ? d : [])
      // Filter client-side by run_id / session_id when provided
      if (runId)     list = list.filter(a => a.run_id === runId)
      if (sessionId) list = list.filter(a => a.session_id === sessionId)
      setApprovals(list)
    } catch { /* silent */ } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedEndpoint, authToken, runId, sessionId])

  // Initial fetch + poll every 5 s while pending items exist
  useEffect(() => {
    fetchPending()
  }, [fetchPending])

  useEffect(() => {
    if (approvals.length > 0) {
      pollRef.current = setInterval(() => fetchPending(), 5_000)
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [approvals.length, fetchPending])

  const handleResolve = async (id: string, approved: boolean) => {
    if (!selectedEndpoint) return
    try {
      const res = await fetch(APIRoutes.ResolveApproval(selectedEndpoint, id), {
        method: 'POST',
        headers,
        body: JSON.stringify({ status: approved ? 'approved' : 'rejected', resolved_by: 'Human Lead' }),
      })
      if (!res.ok) throw new Error(await res.text())
      const updated: Approval = await res.json()
      setApprovals(prev => prev.map(a => a.id === id ? { ...a, ...updated } : a).filter(a => a.status === 'pending'))
      toast.success(approved ? 'Approved — run will continue' : 'Rejected — run will be halted')
    } catch (e) {
      toast.error(`Failed: ${e instanceof Error ? e.message : e}`)
    }
  }

  const pending = approvals.filter(a => a.status === 'pending')

  if (loading && approvals.length === 0) return null
  if (pending.length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className="max-w-2xl space-y-2"
    >
      {/* Banner */}
      <div className="flex items-center gap-2 rounded-xl border border-warning/30 bg-warning/5 px-3 py-2 text-xs text-warning">
        <AlertCircle className="size-3.5 shrink-0" />
        <span className="font-medium">
          {label ?? 'Agent paused — human approval required before run can continue'}
        </span>
        <span className="ml-auto shrink-0 rounded-full bg-warning/20 px-2 py-0.5 text-[10px] font-semibold tabular-nums">
          {pending.length}
        </span>
      </div>

      {/* Cards */}
      <div className="space-y-2">
        {pending.map(a => (
          <InlineApprovalCard key={a.id} approval={a} onResolve={handleResolve} />
        ))}
      </div>
    </motion.div>
  )
}
