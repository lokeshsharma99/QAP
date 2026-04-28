'use client'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  ShieldCheck, RefreshCw, CheckCircle, XCircle, Clock, ChevronDown, ChevronUp,
  AlertCircle, Timer, User, Cpu, GitBranch, Zap
} from 'lucide-react'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import { toast } from 'sonner'

dayjs.extend(relativeTime)

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired' | 'cancelled'

interface Requirement {
  name?: string
  description?: string
  type?: string
  [key: string]: unknown
}

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
  schedule_id?: string | null
  schedule_run_id?: string | null
  source_name?: string | null
  requirements?: Requirement[] | null
  context?: Record<string, unknown> | null
  resolution_data?: Record<string, unknown> | null
  resolved_by?: string | null
  resolved_at?: number | null
  created_at?: number | null
  updated_at?: number | null
  run_status?: string | null
}

interface ApprovalMeta {
  page: number
  limit: number
  total_pages: number
  total_count: number
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const fmtTs = (ts?: number | null): string => {
  if (!ts) return ''
  return dayjs.unix(ts).format('MMM D, HH:mm:ss')
}

const fromNow = (ts?: number | null): string => {
  if (!ts) return ''
  return dayjs.unix(ts).fromNow()
}

// ---------------------------------------------------------------------------
// StatusBadge
// ---------------------------------------------------------------------------
const StatusBadge = ({ status }: { status: ApprovalStatus }) => {
  const cfg: Record<ApprovalStatus, { icon: React.ElementType; cls: string; label: string }> = {
    pending:   { icon: Clock,        cls: 'bg-warning/10 text-warning',         label: 'Pending' },
    approved:  { icon: CheckCircle,  cls: 'bg-positive/10 text-positive',       label: 'Approved' },
    rejected:  { icon: XCircle,      cls: 'bg-destructive/10 text-destructive', label: 'Rejected' },
    expired:   { icon: Timer,        cls: 'bg-muted/10 text-muted',             label: 'Expired' },
    cancelled: { icon: XCircle,      cls: 'bg-accent text-muted',               label: 'Cancelled' },
  }
  const { icon: Ico, cls, label } = cfg[status] ?? cfg.pending
  return (
    <span className={cn('flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium', cls)}>
      <Ico className="size-3" />{label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// SourceBadge
// ---------------------------------------------------------------------------
const SourceBadge = ({ approval }: { approval: Approval }) => {
  const label = approval.source_name ?? approval.agent_id ?? approval.team_id ?? approval.workflow_id ?? approval.source_type
  const IconComp = approval.team_id ? GitBranch : approval.workflow_id ? Zap : Cpu
  return (
    <span className="flex items-center gap-1 rounded-full bg-brand/10 px-2 py-0.5 text-xs text-brand">
      <IconComp className="size-3" />{label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// ApprovalCard
// ---------------------------------------------------------------------------
const ApprovalCard = ({
  approval,
  onResolve,
}: {
  approval: Approval
  onResolve: (id: string, approved: boolean) => void
}) => {
  const [expanded, setExpanded] = useState(approval.status === 'pending')

  const borderCls =
    approval.status === 'pending'  ? 'border-warning/40' :
    approval.status === 'approved' ? 'border-positive/30' :
    approval.status === 'rejected' ? 'border-destructive/30' : 'border-accent'

  const expiresInMs = approval.expires_at ? (approval.expires_at * 1000) - Date.now() : null
  const isExpiringSoon = expiresInMs !== null && expiresInMs > 0 && expiresInMs < 5 * 60 * 1000

  return (
    <div className={cn('rounded-xl border bg-primaryAccent transition-all', borderCls,
      approval.status === 'pending' && 'shadow-sm shadow-warning/10'
    )}>
      {/* Header row */}
      <div className="flex items-start gap-3 p-4">
        <ShieldCheck className={cn('mt-0.5 size-4 shrink-0',
          approval.status === 'pending' ? 'text-warning' : 'text-brand'
        )} />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-primary">
              {approval.tool_name
                ? <code className="font-mono text-xs bg-accent px-1.5 py-0.5 rounded">{approval.tool_name}</code>
                : approval.approval_type ?? 'Approval'}
            </span>
            <StatusBadge status={approval.status} />
            <SourceBadge approval={approval} />
            {approval.approval_type && approval.approval_type !== 'tool_call' && (
              <span className="rounded-full bg-accent px-2 py-0.5 text-xs text-muted">{approval.approval_type}</span>
            )}
          </div>

          {/* Tool args preview when collapsed */}
          {approval.tool_args && Object.keys(approval.tool_args).length > 0 && !expanded && (
            <div className="mt-1 truncate text-xs text-muted/70 font-mono">
              {JSON.stringify(approval.tool_args).slice(0, 100)}…
            </div>
          )}

          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted/50">
            {approval.created_at && <span>{fmtTs(approval.created_at)}</span>}
            {approval.user_id && <span>· <User className="inline size-3" /> {approval.user_id}</span>}
            {isExpiringSoon && <span className="text-warning">· Expires {fromNow(approval.expires_at)}</span>}
          </div>
        </div>

        {/* Inline approve/reject for pending */}
        {approval.status === 'pending' && (
          <div className="flex items-center gap-1.5 shrink-0">
            <Button size="sm" onClick={() => onResolve(approval.id, true)}
              className="h-7 gap-1 bg-positive text-background hover:bg-positive/90 text-xs px-2.5">
              <CheckCircle className="size-3" />Approve
            </Button>
            <Button size="sm" variant="outline" onClick={() => onResolve(approval.id, false)}
              className="h-7 gap-1 border-destructive/40 text-destructive hover:bg-destructive/10 text-xs px-2.5">
              <XCircle className="size-3" />Reject
            </Button>
          </div>
        )}

        <button onClick={() => setExpanded(!expanded)}
          className="shrink-0 rounded-lg p-1.5 text-muted hover:bg-accent hover:text-primary">
          {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
        </button>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="border-t border-accent px-4 pb-4 pt-3 space-y-3 text-xs">

          {/* Requirements (human review gate) */}
          {approval.requirements && approval.requirements.length > 0 && (
            <div>
              <div className="mb-1 text-muted/60 uppercase tracking-wide text-[10px]">Requirements</div>
              <div className="space-y-1">
                {approval.requirements.map((req, i) => (
                  <div key={i} className="rounded-lg bg-background px-3 py-2">
                    {req.name && <div className="font-medium text-primary">{req.name}</div>}
                    {req.description && <div className="text-muted/70 mt-0.5">{req.description}</div>}
                    {req.type && <div className="text-muted/50 mt-0.5">Type: {req.type}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tool args */}
          {approval.tool_args && Object.keys(approval.tool_args).length > 0 && (
            <div>
              <div className="mb-1 text-muted/60 uppercase tracking-wide text-[10px]">Tool Arguments</div>
              <pre className="overflow-x-auto rounded-xl bg-background p-3 text-xs text-primary leading-relaxed max-h-48 overflow-y-auto">
                {JSON.stringify(approval.tool_args, null, 2)}
              </pre>
            </div>
          )}

          {/* Context */}
          {approval.context && Object.keys(approval.context).length > 0 && (
            <div>
              <div className="mb-1 text-muted/60 uppercase tracking-wide text-[10px]">Context</div>
              <pre className="overflow-x-auto rounded-xl bg-background p-3 text-xs text-muted max-h-32 overflow-y-auto">
                {JSON.stringify(approval.context, null, 2)}
              </pre>
            </div>
          )}

          {/* Resolution data */}
          {approval.resolution_data && Object.keys(approval.resolution_data).length > 0 && (
            <div>
              <div className="mb-1 text-muted/60 uppercase tracking-wide text-[10px]">Resolution</div>
              <pre className="overflow-x-auto rounded-xl bg-background p-3 text-xs text-muted max-h-32 overflow-y-auto">
                {JSON.stringify(approval.resolution_data, null, 2)}
              </pre>
            </div>
          )}

          {/* Meta grid */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 rounded-xl bg-background px-3 py-2">
            {[
              { label: 'Approval ID',  value: approval.id },
              { label: 'Run ID',       value: approval.run_id },
              { label: 'Session ID',   value: approval.session_id },
              { label: 'Source Type',  value: approval.source_type },
              { label: 'Pause Type',   value: approval.pause_type },
              { label: 'Resolved By',  value: approval.resolved_by },
              { label: 'Resolved At',  value: approval.resolved_at ? fmtTs(approval.resolved_at) : null },
              { label: 'Expires At',   value: approval.expires_at  ? fmtTs(approval.expires_at)  : null },
              { label: 'Run Status',   value: approval.run_status },
            ].filter(x => x.value).map(({ label, value }) => (
              <div key={label}>
                <div className="text-muted/50 uppercase tracking-wide text-[10px]">{label}</div>
                <div className="font-mono text-primary/80 truncate text-[11px]">{value}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------
const FILTER_TABS = [
  { value: 'all',       label: 'All' },
  { value: 'pending',   label: 'Pending' },
  { value: 'approved',  label: 'Approved' },
  { value: 'rejected',  label: 'Rejected' },
  { value: 'expired',   label: 'Expired' },
  { value: 'cancelled', label: 'Cancelled' },
] as const

type FilterValue = (typeof FILTER_TABS)[number]['value']

export default function ApprovalsPage() {
  const { selectedEndpoint, authToken } = useStore()
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [meta, setMeta] = useState<ApprovalMeta | null>(null)
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState<FilterValue>('all')
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
  }

  const fetchApprovals = useCallback(async (silent = false) => {
    if (!selectedEndpoint) return
    if (!silent) setLoading(true)
    try {
      const url = new URL(APIRoutes.GetApprovals(selectedEndpoint))
      if (filter !== 'all') url.searchParams.set('status', filter)
      url.searchParams.set('limit', '50')
      url.searchParams.set('page', '1')
      const res = await fetch(url.toString(), { headers })
      if (!res.ok) throw new Error(await res.text())
      const d = await res.json()
      setApprovals(d?.data ?? [])
      setMeta(d?.meta ?? null)
    } catch (e) {
      if (!silent) toast.error(`Failed to load approvals: ${e instanceof Error ? e.message : e}`)
    } finally {
      if (!silent) setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedEndpoint, authToken, filter])

  useEffect(() => { fetchApprovals() }, [fetchApprovals])

  // Auto-refresh every 10s while there are pending approvals
  useEffect(() => {
    const hasPending = approvals.some(a => a.status === 'pending')
    if (hasPending) {
      pollRef.current = setInterval(() => fetchApprovals(true), 10_000)
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [approvals, fetchApprovals])

  const handleResolve = async (id: string, approved: boolean) => {
    if (!selectedEndpoint) return
    try {
      const res = await fetch(APIRoutes.ResolveApproval(selectedEndpoint, id), {
        method: 'POST',
        headers,
        body: JSON.stringify({
          status: approved ? 'approved' : 'rejected',
          resolved_by: 'Human Lead',
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      const updated: Approval = await res.json()
      setApprovals(prev => prev.map(a => a.id === id ? { ...a, ...updated } : a))
      toast.success(approved ? 'Approved — run will continue' : 'Rejected — run will be halted')
    } catch (e) {
      toast.error(`Failed: ${e instanceof Error ? e.message : e}`)
    }
  }

  const pendingCount  = approvals.filter(a => a.status === 'pending').length
  const approvedCount = approvals.filter(a => a.status === 'approved').length
  const rejectedCount = approvals.filter(a => a.status === 'rejected').length
  const total         = meta?.total_count ?? approvals.length

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-4xl space-y-6">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-medium text-primary">
              <ShieldCheck className="size-5 text-brand" />Approvals
              {pendingCount > 0 && (
                <span className="rounded-full bg-warning/20 px-2 py-0.5 text-xs font-medium text-warning">
                  {pendingCount} pending
                </span>
              )}
            </h1>
            <p className="mt-1 text-xs text-muted">
              Human-in-the-loop gate — approve or reject paused agent actions (tool calls, file deletions, etc.)
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={() => fetchApprovals()} disabled={loading} className="gap-1.5">
            <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />Refresh
          </Button>
        </div>

        {/* Pending alert */}
        {pendingCount > 0 && (
          <div className="flex items-center gap-2 rounded-xl border border-warning/30 bg-warning/5 px-4 py-3 text-xs text-warning">
            <AlertCircle className="size-4 shrink-0" />
            <span>
              {pendingCount} approval{pendingCount > 1 ? 's' : ''} require{pendingCount === 1 ? 's' : ''} your attention —
              agent run{pendingCount > 1 ? 's are' : ' is'} paused waiting for review.
              Auto-refreshing every 10s.
            </span>
          </div>
        )}

        {/* Stats */}
        {!loading && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div className="rounded-xl border border-accent bg-primaryAccent p-3">
              <div className="text-xs text-muted uppercase">Total</div>
              <div className="mt-1 text-2xl font-medium text-primary">{total}</div>
            </div>
            <div className={cn('rounded-xl border bg-primaryAccent p-3', pendingCount > 0 ? 'border-warning/30' : 'border-accent')}>
              <div className={cn('text-xs uppercase', pendingCount > 0 ? 'text-warning' : 'text-muted')}>Pending</div>
              <div className={cn('mt-1 text-2xl font-medium', pendingCount > 0 ? 'text-warning' : 'text-primary')}>{pendingCount}</div>
            </div>
            <div className="rounded-xl border border-positive/20 bg-primaryAccent p-3">
              <div className="text-xs text-positive uppercase">Approved</div>
              <div className="mt-1 text-2xl font-medium text-positive">{approvedCount}</div>
            </div>
            <div className="rounded-xl border border-destructive/20 bg-primaryAccent p-3">
              <div className="text-xs text-destructive uppercase">Rejected</div>
              <div className="mt-1 text-2xl font-medium text-destructive">{rejectedCount}</div>
            </div>
          </div>
        )}

        {/* Filter tabs */}
        <div className="flex gap-1 rounded-xl border border-accent bg-primaryAccent p-1 overflow-x-auto">
          {FILTER_TABS.map(({ value, label }) => {
            const count = value === 'all'      ? total
              : value === 'pending'   ? pendingCount
              : value === 'approved'  ? approvedCount
              : value === 'rejected'  ? rejectedCount : null
            return (
              <button
                key={value}
                onClick={() => setFilter(value)}
                className={cn(
                  'shrink-0 flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
                  filter === value ? 'bg-accent text-primary' : 'text-muted hover:text-primary'
                )}
              >
                {label}
                {count !== null && count > 0 && (
                  <span className={cn('rounded-full px-1.5 py-0.5 text-[10px]',
                    value === 'pending' ? 'bg-warning/20 text-warning' : 'bg-accent text-muted'
                  )}>{count}</span>
                )}
              </button>
            )
          })}
        </div>

        {/* List */}
        <div className="space-y-3">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)
          ) : approvals.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-accent bg-primaryAccent py-16 text-center">
              <ShieldCheck className="size-10 text-muted/20" />
              <p className="mt-3 text-sm font-medium text-muted">No approvals</p>
              <p className="mt-1 text-xs text-muted/60">
                Approvals appear when agents pause and request human confirmation before executing
                sensitive actions like deleting files or test cases.
              </p>
            </div>
          ) : (
            approvals.map(a => (
              <ApprovalCard key={a.id} approval={a} onResolve={handleResolve} />
            ))
          )}
        </div>

        {meta && meta.total_count > meta.limit && (
          <p className="text-center text-xs text-muted/50">
            Showing {approvals.length} of {meta.total_count} approvals
          </p>
        )}
      </div>
    </div>
  )
}

