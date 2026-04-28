'use client'
import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { HealingPatch } from '@/types/qap'
import { toast } from 'sonner'
import { Wrench, CheckCircle, XCircle, ChevronDown, ChevronUp, Shield, RefreshCw } from 'lucide-react'
import { useStore } from '@/store'
import { getAllSessionsAPI, getSessionAPI } from '@/api/os'
import { Sessions } from '@/types/os'

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

function isHealingPatch(obj: unknown): obj is Record<string, unknown> {
  if (!obj || typeof obj !== 'object') return false
  const o = obj as Record<string, unknown>
  return typeof o.diff === 'string' && typeof o.old_locator === 'string' && typeof o.new_locator === 'string' && typeof o.file_path === 'string'
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const ConfidenceBadge = ({ confidence }: { confidence?: number }) => {
  if (!confidence) return null
  const pct = Math.round(confidence * 100)
  return (
    <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', pct >= 90 ? 'bg-positive/10 text-positive' : 'bg-warning/10 text-warning')}>
      {pct}%
    </span>
  )
}

const VerificationBadge = ({ passes }: { passes: number }) => (
  <span className={cn('flex items-center gap-1 rounded-full px-2 py-0.5 text-xs', passes >= 3 ? 'bg-positive/10 text-positive' : 'bg-warning/10 text-warning')}>
    <Shield className="size-3" />
    {passes}/3 passes
  </span>
)

const StatusBadge = ({ status }: { status: HealingPatch['status'] }) => {
  const config = {
    pending:  { label: 'Pending',  cls: 'bg-warning/10 text-warning' },
    approved: { label: 'Approved', cls: 'bg-positive/10 text-positive' },
    rejected: { label: 'Rejected', cls: 'bg-destructive/10 text-destructive' },
    applied:  { label: 'Applied',  cls: 'bg-info/10 text-info' },
  }[status]
  return <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', config.cls)}>{config.label}</span>
}

const PatchCard = ({
  patch,
  onApprove,
  onReject,
}: {
  patch: HealingPatch
  onApprove: (id: string) => void
  onReject: (id: string) => void
}) => {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className={cn(
      'rounded-xl border bg-primaryAccent',
      patch.status === 'pending'  ? 'border-warning/30'  :
      patch.status === 'applied'  ? 'border-info/30'     :
      patch.status === 'approved' ? 'border-positive/30' : 'border-destructive/30'
    )}>
      <div className="flex items-start gap-3 p-4">
        <Wrench className="mt-0.5 size-4 shrink-0 text-brand" />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-primary">{patch.test_name}</span>
            <StatusBadge status={patch.status} />
            <ConfidenceBadge confidence={patch.confidence} />
            <VerificationBadge passes={patch.verification_passes} />
          </div>
          <div className="mt-0.5 truncate text-xs text-muted">{patch.file_path}</div>
          <div className="mt-1 text-xs text-muted/60">
            Old: <code className="text-muted">{patch.old_locator.slice(0, 60)}{patch.old_locator.length > 60 ? '…' : ''}</code>
          </div>
          <div className="text-xs text-muted/60">
            New: <code className="text-positive">{patch.new_locator.slice(0, 60)}{patch.new_locator.length > 60 ? '…' : ''}</code>
          </div>
        </div>
        <button onClick={() => setExpanded(!expanded)} className="shrink-0 text-muted hover:text-primary">
          {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
        </button>
      </div>

      {expanded && (
        <div className="border-t border-accent px-4 pb-4">
          <div className="mt-3 overflow-x-auto rounded-xl bg-background p-4 text-xs font-mono leading-relaxed">
            {patch.diff.split('\n').map((line, i) => (
              <div key={i} className={cn(
                'whitespace-pre',
                line.startsWith('+') && !line.startsWith('+++') && 'text-positive',
                line.startsWith('-') && !line.startsWith('---') && 'text-destructive',
                line.startsWith('@@') && 'text-info',
                !line.startsWith('+') && !line.startsWith('-') && !line.startsWith('@@') && 'text-muted'
              )}>{line}</div>
            ))}
          </div>

          {patch.logic_changed && (
            <div className="mt-2 rounded-xl border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
              ⚠ Logic change detected — Human review required
            </div>
          )}

          {patch.status === 'pending' && !patch.logic_changed && (
            <div className="mt-3 flex gap-2">
              <Button size="sm" onClick={() => onApprove(patch.id)} className="gap-1.5 bg-positive text-background hover:bg-positive/90">
                <CheckCircle className="size-3.5" />Approve Patch
              </Button>
              <Button size="sm" variant="outline" onClick={() => onReject(patch.id)} className="gap-1.5 border-destructive/40 text-destructive hover:bg-destructive/10">
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

export default function HealingDashboard() {
  const searchParams = useSearchParams()
  const agentId = searchParams.get('agent') ?? 'medic'
  const dbId    = searchParams.get('db_id') ?? 'quality-autopilot-db'

  const { selectedEndpoint, authToken } = useStore()

  const [patches, setPatches] = useState<HealingPatch[]>([])
  const [loading, setLoading] = useState(false)
  const [filter,  setFilter]  = useState<HealingPatch['status'] | 'all'>('all')

  const fetchPatches = useCallback(async () => {
    if (!selectedEndpoint) return
    setLoading(true)
    try {
      const sessionsRes = await getAllSessionsAPI(
        selectedEndpoint, 'agent', agentId, dbId, authToken || undefined
      ) as Sessions | { data: [] }
      const sessions = sessionsRes.data ?? []

      const found: HealingPatch[] = []

      for (const session of sessions) {
        try {
          const runs = await getSessionAPI(selectedEndpoint, 'agent', session.session_id, dbId, authToken || undefined)
          const runList: { messages?: { role: string; content: string | null }[] }[] =
            Array.isArray(runs) ? runs : (runs?.runs ?? [])

          for (const run of runList) {
            for (const msg of run.messages ?? []) {
              if (msg.role !== 'assistant' || !msg.content) continue
              const parsed = extractJson(msg.content)
              if (!isHealingPatch(parsed)) continue
              const p = parsed as Record<string, unknown>
              found.push({
                id:                  String(p.trace_id ?? `${session.session_id}-${found.length}`),
                test_name:           String(p.test_name ?? 'Unknown test'),
                trace_id:            String(p.trace_id ?? ''),
                file_path:           String(p.file_path ?? ''),
                old_locator:         String(p.old_locator ?? ''),
                new_locator:         String(p.new_locator ?? ''),
                diff:                String(p.diff ?? ''),
                verification_passes: typeof p.verification_passes === 'number' ? p.verification_passes : 0,
                logic_changed:       Boolean(p.logic_changed),
                status:              (p.status as HealingPatch['status']) ?? 'pending',
                created_at:          String(p.created_at ?? new Date(session.created_at * 1000).toISOString()),
                confidence:          typeof p.confidence === 'number' ? p.confidence : undefined,
              })
            }
          }
        } catch { /* skip failed session */ }
      }

      setPatches(found)
    } catch {
      toast.error('Failed to load healing patches')
    } finally {
      setLoading(false)
    }
  }, [selectedEndpoint, agentId, dbId, authToken])

  useEffect(() => { fetchPatches() }, [fetchPatches])

  const handleApprove = (id: string) => {
    setPatches((prev) => prev.map((p) => p.id === id ? { ...p, status: 'approved' as const } : p))
    toast.success('Patch approved — Healing Judge confidence met')
  }
  const handleReject = (id: string) => {
    setPatches((prev) => prev.map((p) => p.id === id ? { ...p, status: 'rejected' as const } : p))
    toast.error('Patch rejected — Sent back to Detective + Medic')
  }

  const filtered = filter === 'all' ? patches : patches.filter((p) => p.status === filter)
  const counts = {
    all:      patches.length,
    pending:  patches.filter((p) => p.status === 'pending').length,
    approved: patches.filter((p) => p.status === 'approved').length,
    applied:  patches.filter((p) => p.status === 'applied').length,
    rejected: patches.filter((p) => p.status === 'rejected').length,
  }
  const healingRate = patches.length > 0
    ? Math.round(((counts.approved + counts.applied) / patches.length) * 100)
    : 0

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-4xl space-y-6">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-medium text-primary">
              <Wrench className="size-5 text-brand" />
              Healing Dashboard
            </h1>
            <p className="mt-1 text-xs text-muted">
              Surgical locator patches from the <span className="text-primary">{agentId}</span> agent
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={fetchPatches} disabled={loading} className="gap-1.5">
            <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />
            Refresh
          </Button>
        </div>

        {/* Stats */}
        {loading ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div className="rounded-xl border border-accent bg-primaryAccent p-3">
              <div className="text-xs text-muted uppercase">Total Patches</div>
              <div className="text-2xl font-medium text-primary">{patches.length}</div>
            </div>
            <div className="rounded-xl border border-warning/30 bg-primaryAccent p-3">
              <div className="text-xs text-warning uppercase">Pending</div>
              <div className="text-2xl font-medium text-warning">{counts.pending}</div>
            </div>
            <div className="rounded-xl border border-positive/30 bg-primaryAccent p-3">
              <div className="text-xs text-positive uppercase">Applied</div>
              <div className="text-2xl font-medium text-positive">{counts.approved + counts.applied}</div>
            </div>
            <div className="rounded-xl border border-accent bg-primaryAccent p-3">
              <div className="text-xs text-muted uppercase">Heal Rate</div>
              <div className="text-2xl font-medium text-primary">{healingRate}%</div>
            </div>
          </div>
        )}

        {/* Filter */}
        <div className="flex gap-1 rounded-xl border border-accent bg-primaryAccent p-1">
          {(['all', 'pending', 'approved', 'applied', 'rejected'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                'flex-1 rounded-lg px-2 py-1.5 text-xs font-medium uppercase transition-colors',
                filter === f ? 'bg-accent text-primary' : 'text-muted hover:text-primary'
              )}
            >
              {f}{f !== 'all' && patches.length > 0 ? ` (${counts[f]})` : ''}
            </button>
          ))}
        </div>

        {/* Patch list */}
        <div className="space-y-3">
          {loading ? (
            Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-accent bg-primaryAccent py-16 text-center">
              <Wrench className="size-10 text-muted/20" />
              <p className="mt-3 text-sm font-medium text-muted">No healing patches found</p>
              <p className="mt-1 text-xs text-muted/60">
                Patches appear here when the <span className="text-primary">{agentId}</span> agent produces{' '}
                <code className="text-xs">HealingPatch</code> output in its sessions.
              </p>
            </div>
          ) : (
            filtered.map((patch) => (
              <PatchCard key={patch.id} patch={patch} onApprove={handleApprove} onReject={handleReject} />
            ))
          )}
        </div>
      </div>
    </div>
  )
}
