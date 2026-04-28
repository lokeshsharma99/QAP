'use client'
import { useEffect, useState, useCallback } from 'react'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { Database, RefreshCw, ChevronDown, ChevronUp, Copy, Search } from 'lucide-react'
import { toast } from 'sonner'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface RegistryEntry {
  id?: string
  name?: string
  type?: string
  provider?: string
  description?: string
  version?: string
  metadata?: Record<string, unknown>
  [key: string]: unknown
}

// ---------------------------------------------------------------------------
// EntryCard
// ---------------------------------------------------------------------------
const EntryCard = ({ entry }: { entry: RegistryEntry }) => {
  const [expanded, setExpanded] = useState(false)
  const label = entry.name ?? entry.id ?? 'Entry'
  const copyEntry = () => {
    navigator.clipboard.writeText(JSON.stringify(entry, null, 2))
      .then(() => toast.success('Copied'))
      .catch(() => {})
  }

  return (
    <div className="rounded-xl border border-accent bg-primaryAccent">
      <div className="flex items-start gap-3 p-4">
        <Database className="mt-0.5 size-4 shrink-0 text-brand" />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-primary truncate">{label}</span>
            {entry.type && (
              <span className="rounded-full bg-accent px-2 py-0.5 text-xs text-muted uppercase">{entry.type}</span>
            )}
            {entry.provider && (
              <span className="rounded-full bg-brand/10 px-2 py-0.5 text-xs text-brand">{entry.provider}</span>
            )}
            {entry.version && (
              <span className="rounded-full bg-accent px-2 py-0.5 text-xs text-muted/60">v{entry.version}</span>
            )}
          </div>
          {entry.description && (
            <p className="mt-1 text-xs text-muted/70 truncate">{entry.description}</p>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button onClick={copyEntry} className="rounded-lg p-1.5 text-muted hover:bg-accent hover:text-primary" title="Copy JSON">
            <Copy className="size-3.5" />
          </button>
          <button onClick={() => setExpanded(!expanded)} className="rounded-lg p-1.5 text-muted hover:bg-accent hover:text-primary">
            {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          </button>
        </div>
      </div>
      {expanded && (
        <div className="border-t border-accent px-4 pb-4 pt-3">
          <pre className="max-h-80 overflow-y-auto rounded-xl bg-background p-3 text-xs text-primary whitespace-pre-wrap">
            {JSON.stringify(entry, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// RegistryPage
// ---------------------------------------------------------------------------
export default function RegistryPage() {
  const { selectedEndpoint, authToken } = useStore()
  const [entries, setEntries] = useState<RegistryEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch]   = useState('')
  const [filterType, setFilterType] = useState('all')

  const headers: Record<string, string> = authToken ? { Authorization: `Bearer ${authToken}` } : {}

  const fetchRegistry = useCallback(async () => {
    if (!selectedEndpoint) return
    setLoading(true)
    try {
      const res = await fetch(APIRoutes.Registry(selectedEndpoint), { headers })
      if (res.ok) {
        const d = await res.json()
        // Registry can return an object keyed by type, or a flat list
        if (Array.isArray(d)) {
          setEntries(d)
        } else if (d && typeof d === 'object') {
          // Flatten keyed response: { models: [...], tools: [...] } → flat list with type injected
          const flat: RegistryEntry[] = []
          for (const [key, val] of Object.entries(d)) {
            if (Array.isArray(val)) {
              val.forEach((item) => flat.push({ ...item, type: item.type ?? key }))
            } else if (val && typeof val === 'object') {
              flat.push({ ...val as RegistryEntry, type: (val as RegistryEntry).type ?? key })
            }
          }
          setEntries(flat)
        }
      }
    } catch { /* silent */ }
    finally { setLoading(false) }
  }, [selectedEndpoint, authToken])

  useEffect(() => { fetchRegistry() }, [fetchRegistry])

  const uniqueTypes = Array.from(new Set(entries.map((e) => e.type ?? 'unknown').filter(Boolean)))

  const filtered = entries.filter((e) => {
    const typeMatch = filterType === 'all' || e.type === filterType
    if (!search) return typeMatch
    const q = search.toLowerCase()
    return typeMatch && (
      (e.name  ?? '').toLowerCase().includes(q) ||
      (e.id    ?? '').toLowerCase().includes(q) ||
      (e.type  ?? '').toLowerCase().includes(q) ||
      (e.provider ?? '').toLowerCase().includes(q)
    )
  })

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-4xl space-y-6">

        <div className="flex items-start justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-medium text-primary">
              <Database className="size-5 text-brand" />Registry
            </h1>
            <p className="mt-1 text-xs text-muted">AgentOS registry — models, tools, knowledge bases, embedders</p>
          </div>
          <Button size="sm" variant="outline" onClick={fetchRegistry} disabled={loading} className="gap-1.5">
            <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />Refresh
          </Button>
        </div>

        {/* Stats */}
        {!loading && entries.length > 0 && (
          <div className="rounded-xl border border-accent bg-primaryAccent p-4">
            <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
              <span>{entries.length} registered items</span>
              {uniqueTypes.map((t) => (
                <span key={t} className="rounded-full bg-accent px-2 py-0.5 capitalize">{t}: {entries.filter((e) => e.type === t).length}</span>
              ))}
            </div>
          </div>
        )}

        {/* Type filter + search */}
        <div className="space-y-2">
          {uniqueTypes.length > 1 && (
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
          <div className="relative">
            <Search className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, type, provider…"
              className="w-full rounded-xl border border-accent bg-primaryAccent pl-8 pr-3 py-2 text-xs text-primary outline-none focus:border-primary/30"
            />
          </div>
        </div>

        {/* List */}
        <div className="space-y-3">
          {loading ? (
            Array.from({length: 5}).map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-accent bg-primaryAccent py-16 text-center">
              <Database className="size-10 text-muted/20" />
              <p className="mt-3 text-sm font-medium text-muted">Registry is empty</p>
              <p className="mt-1 text-xs text-muted/60">Items are registered automatically when AgentOS starts.</p>
            </div>
          ) : (
            filtered.map((entry, i) => <EntryCard key={entry.id ?? entry.name ?? i} entry={entry} />)
          )}
        </div>
      </div>
    </div>
  )
}
