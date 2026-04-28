'use client'
import { useState, useEffect, useCallback } from 'react'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'
import {
  CalendarClock, Plus, Play, Trash2, RefreshCw, ChevronDown, ChevronUp,
  CheckCircle, XCircle, Clock, Zap, Edit2, X, Check
} from 'lucide-react'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Schedule {
  id: string
  name: string
  description?: string
  method: string
  endpoint: string
  payload?: Record<string, unknown>
  cron_expr: string
  timezone: string
  timeout_seconds: number
  max_retries: number
  retry_delay_seconds: number
  enabled: boolean
  next_run_at?: number
  created_at?: number
  updated_at?: number
}

interface ScheduleRun {
  id: string
  schedule_id: string
  attempt: number
  triggered_at?: number
  completed_at?: number
  status: string
  status_code?: number
  run_id?: string
  session_id?: string
  error?: string
  created_at?: number
}

interface CreateForm {
  name: string
  cron_expr: string
  endpoint: string
  method: string
  description: string
  payload: string
  timezone: string
  max_retries: string
  retry_delay_seconds: string
  timeout_seconds: string
}

const EMPTY_FORM: CreateForm = {
  name: '',
  cron_expr: '*/5 * * * *',
  endpoint: '',
  method: 'POST',
  description: '',
  payload: '{}',
  timezone: 'UTC',
  max_retries: '2',
  retry_delay_seconds: '30',
  timeout_seconds: '3600',
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const StatusBadge = ({ enabled }: { enabled: boolean }) => (
  <span className={cn(
    'flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
    enabled ? 'bg-positive/10 text-positive' : 'bg-accent text-muted'
  )}>
    <span className={cn('size-1.5 rounded-full', enabled ? 'bg-positive' : 'bg-muted')} />
    {enabled ? 'Active' : 'Disabled'}
  </span>
)

const RunStatusIcon = ({ status }: { status: string }) => {
  if (status === 'success' || status === 'completed') return <CheckCircle className="size-3.5 text-positive" />
  if (status === 'failed' || status === 'error') return <XCircle className="size-3.5 text-destructive" />
  if (status === 'running') return <RefreshCw className="size-3.5 text-brand animate-spin" />
  return <Clock className="size-3.5 text-muted" />
}

const FormField = ({
  label, value, onChange, placeholder, type = 'text', className,
}: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; type?: string; className?: string
}) => (
  <div className={className}>
    <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-muted/70">{label}</label>
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full rounded-xl border border-primary/15 bg-accent px-3 py-2 text-xs text-primary outline-none placeholder:text-muted/40 focus:border-primary/40"
    />
  </div>
)

// ---------------------------------------------------------------------------
// Create / Edit Modal
// ---------------------------------------------------------------------------

const ScheduleModal = ({
  initial,
  onClose,
  onSave,
}: {
  initial?: Schedule
  onClose: () => void
  onSave: (form: CreateForm) => Promise<void>
}) => {
  const [form, setForm] = useState<CreateForm>(
    initial
      ? {
          name: initial.name,
          cron_expr: initial.cron_expr,
          endpoint: initial.endpoint,
          method: initial.method,
          description: initial.description ?? '',
          payload: JSON.stringify(initial.payload ?? {}, null, 2),
          timezone: initial.timezone,
          max_retries: String(initial.max_retries),
          retry_delay_seconds: String(initial.retry_delay_seconds),
          timeout_seconds: String(initial.timeout_seconds),
        }
      : EMPTY_FORM
  )
  const [saving, setSaving] = useState(false)

  const set = (key: keyof CreateForm) => (val: string) => setForm((f) => ({ ...f, [key]: val }))

  const handleSubmit = async () => {
    if (!form.name.trim()) { toast.error('Name is required'); return }
    if (!form.endpoint.startsWith('/')) { toast.error("Endpoint must start with '/'"); return }
    setSaving(true)
    await onSave(form)
    setSaving(false)
  }

  const CRON_PRESETS = [
    { label: 'Every 5 min',  value: '*/5 * * * *' },
    { label: 'Every 15 min', value: '*/15 * * * *' },
    { label: 'Hourly',       value: '0 * * * *' },
    { label: 'Daily (9am)',  value: '0 9 * * *' },
    { label: 'Weekdays',     value: '0 9 * * 1-5' },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="relative w-full max-w-lg rounded-2xl border border-accent bg-background shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-accent px-5 py-4">
          <div className="flex items-center gap-2">
            <CalendarClock className="size-4 text-brand" />
            <span className="text-sm font-semibold text-primary">
              {initial ? 'Edit Schedule' : 'Create Schedule'}
            </span>
          </div>
          <button onClick={onClose} className="rounded-lg p-1 text-muted hover:bg-accent hover:text-primary">
            <X className="size-4" />
          </button>
        </div>

        {/* Body */}
        <div className="max-h-[70vh] overflow-y-auto p-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Name *" value={form.name} onChange={set('name')} placeholder="e.g. daily-regression" className="col-span-2" />
            <FormField label="Endpoint *" value={form.endpoint} onChange={set('endpoint')} placeholder="/agents/architect/runs" className="col-span-2" />
          </div>

          {/* Cron */}
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-muted/70">Cron Expression *</label>
            <input
              value={form.cron_expr}
              onChange={(e) => set('cron_expr')(e.target.value)}
              className="w-full rounded-xl border border-primary/15 bg-accent px-3 py-2 font-mono text-xs text-primary outline-none focus:border-primary/40"
              placeholder="*/5 * * * *"
            />
            <div className="mt-1.5 flex flex-wrap gap-1">
              {CRON_PRESETS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => set('cron_expr')(p.value)}
                  className={cn(
                    'rounded-full px-2 py-0.5 text-[10px] transition-colors',
                    form.cron_expr === p.value
                      ? 'bg-brand/20 text-brand'
                      : 'bg-accent text-muted hover:text-primary'
                  )}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {/* Method */}
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-muted/70">Method</label>
              <select
                value={form.method}
                onChange={(e) => set('method')(e.target.value)}
                className="w-full rounded-xl border border-primary/15 bg-accent px-3 py-2 text-xs text-primary outline-none focus:border-primary/40"
              >
                {['POST', 'GET', 'PUT', 'PATCH', 'DELETE'].map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
            <FormField label="Timezone" value={form.timezone} onChange={set('timezone')} placeholder="UTC" />
          </div>

          {/* Payload */}
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-muted/70">Payload (JSON)</label>
            <textarea
              rows={3}
              value={form.payload}
              onChange={(e) => set('payload')(e.target.value)}
              className="w-full resize-none rounded-xl border border-primary/15 bg-accent px-3 py-2 font-mono text-xs text-primary outline-none placeholder:text-muted/40 focus:border-primary/40"
              placeholder='{}'
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <FormField label="Max Retries"        value={form.max_retries}        onChange={set('max_retries')}        type="number" />
            <FormField label="Retry Delay (s)"    value={form.retry_delay_seconds} onChange={set('retry_delay_seconds')} type="number" />
            <FormField label="Timeout (s)"         value={form.timeout_seconds}     onChange={set('timeout_seconds')}     type="number" />
          </div>

          <FormField label="Description" value={form.description} onChange={set('description')} placeholder="Optional description…" />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-accent px-5 py-4">
          <button onClick={onClose} className="rounded-xl px-4 py-2 text-xs text-muted hover:bg-accent hover:text-primary">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-medium text-primaryAccent transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {saving ? <RefreshCw className="size-3.5 animate-spin" /> : <Check className="size-3.5" />}
            {saving ? 'Saving…' : initial ? 'Update' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Run History Panel
// ---------------------------------------------------------------------------

const RunsPanel = ({
  schedule,
  runs,
  loadingRuns,
  onClose,
}: {
  schedule: Schedule
  runs: ScheduleRun[]
  loadingRuns: boolean
  onClose: () => void
}) => (
  <div className="flex flex-col h-full border-l border-accent bg-background">
    {/* Header */}
    <div className="flex items-center justify-between border-b border-accent px-4 py-3 shrink-0">
      <div>
        <div className="text-xs font-semibold text-primary">{schedule.name}</div>
        <div className="mt-0.5 font-mono text-[10px] text-muted/60">{schedule.cron_expr} · {schedule.timezone}</div>
      </div>
      <button onClick={onClose} className="rounded-lg p-1 text-muted hover:bg-accent hover:text-primary">
        <X className="size-4" />
      </button>
    </div>

    {/* Schedule info */}
    <div className="border-b border-accent px-4 py-3 shrink-0 space-y-1.5">
      <div className="flex items-center justify-between text-[10px]">
        <span className="text-muted">Endpoint</span>
        <span className="font-mono text-primary">{schedule.method} {schedule.endpoint}</span>
      </div>
      <div className="flex items-center justify-between text-[10px]">
        <span className="text-muted">Next Run</span>
        <span className="text-primary">
          {schedule.next_run_at ? dayjs.unix(schedule.next_run_at).fromNow() : '—'}
        </span>
      </div>
      <div className="flex items-center justify-between text-[10px]">
        <span className="text-muted">Max Retries</span>
        <span className="text-primary">{schedule.max_retries}</span>
      </div>
    </div>

    {/* Runs list */}
    <div className="flex-1 overflow-y-auto px-4 py-3">
      <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted">Run History</div>
      {loadingRuns ? (
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-10 rounded-xl bg-accent/60 animate-pulse" />
          ))}
        </div>
      ) : runs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <Clock className="size-8 text-muted/20" />
          <p className="mt-2 text-xs text-muted/40">No runs yet</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {runs.map((run) => (
            <div key={run.id} className="rounded-xl border border-accent bg-accent/10 px-3 py-2.5">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <RunStatusIcon status={run.status} />
                  <span className="text-xs font-medium text-primary capitalize">{run.status}</span>
                  {run.status_code && (
                    <span className="rounded-full bg-accent px-1.5 py-0.5 font-mono text-[10px] text-muted">
                      {run.status_code}
                    </span>
                  )}
                </div>
                <span className="shrink-0 text-[10px] text-muted/50">
                  {run.triggered_at ? dayjs.unix(run.triggered_at).format('MMM D, HH:mm:ss') : '—'}
                </span>
              </div>
              {run.error && (
                <p className="mt-1 truncate text-[10px] text-destructive font-mono">{run.error}</p>
              )}
              {run.session_id && (
                <p className="mt-0.5 text-[9px] text-muted/40 font-mono truncate">session: {run.session_id}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  </div>
)

// ---------------------------------------------------------------------------
// Main SchedulerPage
// ---------------------------------------------------------------------------

export default function SchedulerPage() {
  const { selectedEndpoint, authToken } = useStore()
  const endpointUrl = selectedEndpoint || ''
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
  }

  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [loading, setLoading] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [editingSchedule, setEditingSchedule] = useState<Schedule | null>(null)
  const [selectedSchedule, setSelectedSchedule] = useState<Schedule | null>(null)
  const [runs, setRuns] = useState<ScheduleRun[]>([])
  const [loadingRuns, setLoadingRuns] = useState(false)

  // ---------------------------------------------------------------------------
  // Fetch
  // ---------------------------------------------------------------------------

  const fetchSchedules = useCallback(async () => {
    if (!endpointUrl) return
    setLoading(true)
    try {
      const res = await fetch(APIRoutes.GetSchedules(endpointUrl), { headers })
      if (res.ok) {
        const data = await res.json()
        setSchedules(data?.data ?? [])
      }
    } catch { /* offline */ }
    finally { setLoading(false) }
  }, [endpointUrl, authToken])  // eslint-disable-line react-hooks/exhaustive-deps

  const fetchRuns = useCallback(async (scheduleId: string) => {
    setLoadingRuns(true)
    try {
      const res = await fetch(APIRoutes.GetScheduleRuns(endpointUrl, scheduleId), { headers })
      if (res.ok) {
        const data = await res.json()
        setRuns(data?.data ?? [])
      }
    } catch { /* offline */ }
    finally { setLoadingRuns(false) }
  }, [endpointUrl, authToken])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetchSchedules() }, [fetchSchedules])

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  const handleCreate = async (form: CreateForm) => {
    let payload: Record<string, unknown> = {}
    try { if (form.payload.trim()) payload = JSON.parse(form.payload) } catch { toast.error('Payload must be valid JSON'); return }

    const body = {
      name: form.name,
      cron_expr: form.cron_expr,
      endpoint: form.endpoint,
      method: form.method,
      description: form.description || undefined,
      payload: Object.keys(payload).length > 0 ? payload : undefined,
      timezone: form.timezone,
      max_retries: parseInt(form.max_retries) || 0,
      retry_delay_seconds: parseInt(form.retry_delay_seconds) || 30,
      timeout_seconds: parseInt(form.timeout_seconds) || 3600,
    }

    try {
      const res = await fetch(APIRoutes.CreateSchedule(endpointUrl), {
        method: 'POST', headers, body: JSON.stringify(body),
      })
      if (res.ok) {
        toast.success('Schedule created')
        setShowModal(false)
        fetchSchedules()
      } else {
        const err = await res.json().catch(() => ({}))
        toast.error(err?.detail ?? 'Failed to create schedule')
      }
    } catch { toast.error('Network error') }
  }

  const handleUpdate = async (form: CreateForm) => {
    if (!editingSchedule) return
    let payload: Record<string, unknown> = {}
    try { if (form.payload.trim()) payload = JSON.parse(form.payload) } catch { toast.error('Payload must be valid JSON'); return }

    const body = {
      name: form.name,
      cron_expr: form.cron_expr,
      endpoint: form.endpoint,
      method: form.method,
      description: form.description || undefined,
      payload: Object.keys(payload).length > 0 ? payload : undefined,
      timezone: form.timezone,
      max_retries: parseInt(form.max_retries) || 0,
      retry_delay_seconds: parseInt(form.retry_delay_seconds) || 30,
      timeout_seconds: parseInt(form.timeout_seconds) || 3600,
    }

    try {
      const res = await fetch(APIRoutes.UpdateSchedule(endpointUrl, editingSchedule.id), {
        method: 'PATCH', headers, body: JSON.stringify(body),
      })
      if (res.ok) {
        toast.success('Schedule updated')
        setEditingSchedule(null)
        fetchSchedules()
        if (selectedSchedule?.id === editingSchedule.id) fetchRuns(editingSchedule.id)
      } else {
        const err = await res.json().catch(() => ({}))
        toast.error(err?.detail ?? 'Failed to update schedule')
      }
    } catch { toast.error('Network error') }
  }

  const handleToggle = async (s: Schedule) => {
    const url = s.enabled
      ? APIRoutes.DisableSchedule(endpointUrl, s.id)
      : APIRoutes.EnableSchedule(endpointUrl, s.id)
    try {
      const res = await fetch(url, { method: 'POST', headers })
      if (res.ok) {
        setSchedules((prev) => prev.map((x) => x.id === s.id ? { ...x, enabled: !s.enabled } : x))
        toast.success(s.enabled ? 'Schedule disabled' : 'Schedule enabled')
      } else {
        toast.error('Toggle failed')
      }
    } catch { toast.error('Network error') }
  }

  const handleTrigger = async (s: Schedule) => {
    try {
      const res = await fetch(APIRoutes.TriggerSchedule(endpointUrl, s.id), { method: 'POST', headers })
      if (res.ok) {
        toast.success(`Triggered "${s.name}"`)
        if (selectedSchedule?.id === s.id) fetchRuns(s.id)
      } else {
        const err = await res.json().catch(() => ({}))
        toast.error(err?.detail ?? 'Trigger failed')
      }
    } catch { toast.error('Network error') }
  }

  const handleDelete = async (s: Schedule) => {
    try {
      const res = await fetch(APIRoutes.DeleteSchedule(endpointUrl, s.id), { method: 'DELETE', headers })
      if (res.ok || res.status === 204) {
        setSchedules((prev) => prev.filter((x) => x.id !== s.id))
        if (selectedSchedule?.id === s.id) setSelectedSchedule(null)
        toast.success('Schedule deleted')
      } else {
        toast.error('Delete failed')
      }
    } catch { toast.error('Network error') }
  }

  const handleSelectSchedule = (s: Schedule) => {
    if (selectedSchedule?.id === s.id) {
      setSelectedSchedule(null)
      return
    }
    setSelectedSchedule(s)
    fetchRuns(s.id)
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const isEmpty = !loading && schedules.length === 0

  return (
    <div className="flex h-full overflow-hidden">
      {/* Main panel */}
      <div className={cn('flex flex-col flex-1 overflow-hidden', selectedSchedule && 'border-r border-accent')}>
        {/* Header */}
        <div className="border-b border-accent/50 p-6 pb-4 shrink-0">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="flex items-center gap-2 text-lg font-medium text-primary">
                <CalendarClock className="size-5 text-brand" />
                Scheduler
              </h1>
              <p className="mt-1 text-xs text-muted">
                Cron-based scheduled execution for agents and workflows
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={fetchSchedules}
                disabled={loading}
                className="flex items-center gap-1.5 rounded-xl border border-accent px-3 py-2 text-xs text-muted transition-colors hover:bg-accent hover:text-primary disabled:opacity-50"
              >
                <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />
                Refresh
              </button>
              <button
                onClick={() => setShowModal(true)}
                className="flex items-center gap-1.5 rounded-xl bg-primary px-3 py-2 text-xs font-medium text-primaryAccent transition-opacity hover:opacity-90"
              >
                <Plus className="size-3.5" />
                New Schedule
              </button>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-6 space-y-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-14 rounded-xl bg-accent/60 animate-pulse" />
              ))}
            </div>
          ) : isEmpty ? (
            <div className="flex flex-col items-center justify-center h-full p-10 text-center">
              <CalendarClock className="size-14 text-muted/15" />
              <p className="mt-4 text-sm font-medium text-muted">No schedules yet</p>
              <p className="mt-1 text-xs text-muted/60 max-w-xs">
                Create a schedule to run agents or workflows automatically on a cron expression.
              </p>
              <button
                onClick={() => setShowModal(true)}
                className="mt-5 flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2.5 text-xs font-medium text-primaryAccent hover:opacity-90"
              >
                <Plus className="size-3.5" />
                Create First Schedule
              </button>
            </div>
          ) : (
            <table className="w-full text-xs">
              <thead className="sticky top-0 z-10 border-b border-accent bg-background">
                <tr>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wide text-muted">Name</th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wide text-muted hidden md:table-cell">Cron</th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wide text-muted hidden lg:table-cell">Endpoint</th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wide text-muted">Status</th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wide text-muted hidden md:table-cell">Next Run</th>
                  <th className="px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-wide text-muted">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-accent">
                {schedules.map((s) => (
                  <tr
                    key={s.id}
                    onClick={() => handleSelectSchedule(s)}
                    className={cn(
                      'cursor-pointer transition-colors hover:bg-accent/30',
                      selectedSchedule?.id === s.id && 'bg-accent/50'
                    )}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-primary">{s.name}</div>
                      {s.description && (
                        <div className="mt-0.5 text-[10px] text-muted/60 truncate max-w-[200px]">{s.description}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="font-mono text-[11px] text-primary">{s.cron_expr}</span>
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <span className="font-mono text-[11px] text-muted/80 truncate max-w-[180px] block">
                        {s.method} {s.endpoint}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge enabled={s.enabled} />
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell text-[11px] text-muted">
                      {s.next_run_at ? dayjs.unix(s.next_run_at).fromNow() : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                        {/* Toggle enable/disable */}
                        <button
                          onClick={() => handleToggle(s)}
                          title={s.enabled ? 'Disable' : 'Enable'}
                          className={cn(
                            'rounded-lg p-1.5 transition-colors',
                            s.enabled
                              ? 'text-positive hover:bg-positive/10'
                              : 'text-muted hover:bg-accent hover:text-primary'
                          )}
                        >
                          <Zap className="size-3.5" />
                        </button>
                        {/* Trigger now */}
                        <button
                          onClick={() => handleTrigger(s)}
                          title="Trigger now"
                          className="rounded-lg p-1.5 text-muted transition-colors hover:bg-brand/10 hover:text-brand"
                        >
                          <Play className="size-3.5" />
                        </button>
                        {/* Edit */}
                        <button
                          onClick={() => setEditingSchedule(s)}
                          title="Edit"
                          className="rounded-lg p-1.5 text-muted transition-colors hover:bg-accent hover:text-primary"
                        >
                          <Edit2 className="size-3.5" />
                        </button>
                        {/* Delete */}
                        <button
                          onClick={() => handleDelete(s)}
                          title="Delete"
                          className="rounded-lg p-1.5 text-muted transition-colors hover:bg-destructive/10 hover:text-destructive"
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Run history side panel */}
      {selectedSchedule && (
        <div className="w-80 shrink-0 overflow-hidden">
          <RunsPanel
            schedule={selectedSchedule}
            runs={runs}
            loadingRuns={loadingRuns}
            onClose={() => setSelectedSchedule(null)}
          />
        </div>
      )}

      {/* Create modal */}
      {showModal && (
        <ScheduleModal
          onClose={() => setShowModal(false)}
          onSave={handleCreate}
        />
      )}

      {/* Edit modal */}
      {editingSchedule && (
        <ScheduleModal
          initial={editingSchedule}
          onClose={() => setEditingSchedule(null)}
          onSave={handleUpdate}
        />
      )}
    </div>
  )
}
