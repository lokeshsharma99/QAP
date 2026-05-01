'use client'
import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useState, useCallback } from 'react'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  Sparkles, RefreshCw, Search, Trash2, ChevronDown, ChevronUp,
  Plus, X, Tag, Bot, BookOpen,
} from 'lucide-react'
import dayjs from 'dayjs'
import { toast } from 'sonner'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CultureEntry {
  id?: string
  name: string
  summary?: string
  content?: string
  categories: string[]
  notes: string[]
  agent_id?: string
  team_id?: string
  created_at?: number   // epoch seconds
  updated_at?: number
}

// ---------------------------------------------------------------------------
// Category colour mapping — keeps chips visually distinct per domain
// ---------------------------------------------------------------------------

const CAT_COLOURS: Record<string, string> = {
  engineering:    'bg-blue-500/10 text-blue-400',
  locators:       'bg-cyan-500/10 text-cyan-400',
  timing:         'bg-orange-500/10 text-orange-400',
  gherkin:        'bg-purple-500/10 text-purple-400',
  scribe:         'bg-violet-500/10 text-violet-400',
  pom:            'bg-teal-500/10 text-teal-400',
  'test-data':    'bg-yellow-500/10 text-yellow-400',
  security:       'bg-red-500/10 text-red-400',
  communication:  'bg-green-500/10 text-green-400',
  'code-review':  'bg-pink-500/10 text-pink-400',
  documentation:  'bg-sky-500/10 text-sky-400',
}

function catColour(cat: string) {
  return CAT_COLOURS[cat.toLowerCase()] ?? 'bg-accent text-muted'
}

// ---------------------------------------------------------------------------
// CultureCard
// ---------------------------------------------------------------------------

const CultureCard = ({
  entry,
  onDelete,
}: {
  entry: CultureEntry
  onDelete: (id: string) => void
}) => {
  const [expanded, setExpanded] = useState(false)
  const id = entry.id ?? ''
  const ts = entry.updated_at ?? entry.created_at
  const hasLongContent = (entry.content ?? '').length > 120

  return (
    <div className="rounded-xl border border-accent bg-primaryAccent transition-colors hover:border-primary/20">
      <div className="flex items-start gap-3 p-4">
        {/* Icon */}
        <Sparkles className="mt-0.5 size-4 shrink-0 text-brand" />

        {/* Body */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <span className="text-sm font-medium text-primary leading-snug">{entry.name}</span>
          </div>

          {entry.summary && (
            <p className="mt-0.5 text-xs text-muted leading-relaxed line-clamp-2">{entry.summary}</p>
          )}

          {/* Chips row */}
          <div className="mt-2 flex flex-wrap gap-1.5">
            {entry.categories.map((c) => (
              <span key={c} className={cn('flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-medium', catColour(c))}>
                <Tag className="size-2.5" />{c}
              </span>
            ))}
            {entry.agent_id && (
              <span className="flex items-center gap-0.5 rounded-full bg-brand/10 px-2 py-0.5 text-xs text-brand">
                <Bot className="size-2.5" />{entry.agent_id}
              </span>
            )}
          </div>

          {/* Timestamp */}
          {ts && (
            <div className="mt-1 text-xs text-muted/50">
              {dayjs.unix(ts).format('MMM D YYYY, HH:mm')}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex shrink-0 items-center gap-1">
          {id && (
            <button
              onClick={() => onDelete(id)}
              className="rounded-lg p-1.5 text-muted transition-colors hover:bg-destructive/10 hover:text-destructive"
              title="Delete"
            >
              <Trash2 className="size-3.5" />
            </button>
          )}
          {hasLongContent && (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="rounded-lg p-1.5 text-muted transition-colors hover:bg-accent hover:text-primary"
              title={expanded ? 'Collapse' : 'Expand'}
            >
              {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
            </button>
          )}
        </div>
      </div>

      {/* Expanded content */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="expanded"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            className="overflow-hidden border-t border-accent"
          >
            <div className="px-4 pb-4">
              <pre className="mt-3 whitespace-pre-wrap rounded-xl bg-background p-3 text-xs text-primary leading-relaxed">
                {entry.content}
              </pre>
              {entry.notes.length > 0 && (
                <div className="mt-2 space-y-0.5">
                  {entry.notes.map((n, i) => (
                    <p key={i} className="text-xs text-muted/70 italic">• {n}</p>
                  ))}
                </div>
              )}
              {id && <div className="mt-2 font-mono text-xs text-muted/40">ID: {id}</div>}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ---------------------------------------------------------------------------
// AddCultureModal
// ---------------------------------------------------------------------------

const COMMON_CATEGORIES = [
  'engineering', 'locators', 'timing', 'gherkin', 'scribe',
  'pom', 'test-data', 'security', 'communication', 'documentation',
]

const AddCultureModal = ({
  onClose,
  onCreated,
  endpoint,
  headers,
}: {
  onClose: () => void
  onCreated: () => void
  endpoint: string
  headers: Record<string, string>
}) => {
  const [name, setName] = useState('')
  const [summary, setSummary] = useState('')
  const [content, setContent] = useState('')
  const [catInput, setCatInput] = useState('')
  const [categories, setCategories] = useState<string[]>([])
  const [saving, setSaving] = useState(false)

  const addCat = (c: string) => {
    const v = c.trim().toLowerCase()
    if (v && !categories.includes(v)) setCategories((p) => [...p, v])
    setCatInput('')
  }

  const handleSubmit = async () => {
    if (!name.trim() || !content.trim()) {
      toast.error('Name and Content are required')
      return
    }
    setSaving(true)
    try {
      const res = await fetch(APIRoutes.CreateCultureEntry(endpoint), {
        method: 'POST',
        headers,
        body: JSON.stringify({ name: name.trim(), summary: summary.trim() || undefined, content: content.trim(), categories }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        toast.error(`Failed: ${err?.detail ?? res.statusText}`)
        return
      }
      toast.success('Cultural knowledge added')
      onCreated()
      onClose()
    } catch {
      toast.error('Request failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 8 }}
        transition={{ duration: 0.18, ease: 'easeOut' }}
        className="relative mx-4 w-full max-w-lg rounded-2xl border border-accent bg-primaryAccent p-6 shadow-2xl"
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-primary">
            <Sparkles className="size-4 text-brand" />Add Cultural Knowledge
          </h2>
          <button onClick={onClose} className="rounded-lg p-1.5 text-muted hover:bg-accent hover:text-primary">
            <X className="size-4" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Name */}
          <div>
            <label className="mb-1 block text-xs font-medium uppercase text-muted">Name *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Response Format Standard"
              className="w-full rounded-xl border border-accent bg-background px-3 py-2 text-xs text-primary outline-none focus:border-primary/30"
            />
          </div>

          {/* Summary */}
          <div>
            <label className="mb-1 block text-xs font-medium uppercase text-muted">Summary</label>
            <input
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="One-line description of this principle"
              className="w-full rounded-xl border border-accent bg-background px-3 py-2 text-xs text-primary outline-none focus:border-primary/30"
            />
          </div>

          {/* Content */}
          <div>
            <label className="mb-1 block text-xs font-medium uppercase text-muted">Content *</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={5}
              placeholder="The full principle text agents will read…"
              className="w-full resize-none rounded-xl border border-accent bg-background px-3 py-2 text-xs text-primary outline-none focus:border-primary/30"
            />
          </div>

          {/* Categories */}
          <div>
            <label className="mb-1 block text-xs font-medium uppercase text-muted">Categories</label>
            <div className="mb-2 flex flex-wrap gap-1.5">
              {COMMON_CATEGORIES.map((c) => (
                <button
                  key={c}
                  onClick={() => addCat(c)}
                  className={cn(
                    'rounded-full px-2 py-0.5 text-xs transition-colors',
                    categories.includes(c)
                      ? cn(catColour(c), 'ring-1 ring-current/30')
                      : 'bg-accent text-muted hover:text-primary',
                  )}
                >
                  {c}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                value={catInput}
                onChange={(e) => setCatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addCat(catInput)}
                placeholder="Custom category…"
                className="flex-1 rounded-xl border border-accent bg-background px-3 py-1.5 text-xs text-primary outline-none focus:border-primary/30"
              />
              <Button size="sm" variant="outline" onClick={() => addCat(catInput)}>Add</Button>
            </div>
            {categories.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {categories.map((c) => (
                  <span key={c} className={cn('flex items-center gap-1 rounded-full px-2 py-0.5 text-xs', catColour(c))}>
                    {c}
                    <button onClick={() => setCategories((p) => p.filter((x) => x !== c))}>
                      <X className="size-2.5" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <Button size="sm" variant="outline" onClick={onClose}>Cancel</Button>
          <Button size="sm" onClick={handleSubmit} disabled={saving} className="gap-1.5">
            <Sparkles className={cn('size-3.5', saving && 'animate-pulse')} />
            {saving ? 'Saving…' : 'Add Principle'}
          </Button>
        </div>
      </motion.div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// CulturePage
// ---------------------------------------------------------------------------

export default function CulturePage() {
  const { selectedEndpoint, authToken } = useStore()
  const [entries, setEntries] = useState<CultureEntry[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [activeCat, setActiveCat] = useState<string | null>(null)
  const [showAdd, setShowAdd] = useState(false)

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
  }

  const fetchAll = useCallback(async () => {
    if (!selectedEndpoint) return
    setLoading(true)
    try {
      const [entryRes, catRes] = await Promise.allSettled([
        fetch(APIRoutes.GetCulture(selectedEndpoint), { headers }),
        fetch(APIRoutes.GetCultureCategories(selectedEndpoint), { headers }),
      ])
      if (entryRes.status === 'fulfilled' && entryRes.value.ok) {
        const d = await entryRes.value.json()
        setEntries(d?.data ?? [])
      }
      if (catRes.status === 'fulfilled' && catRes.value.ok) {
        const d = await catRes.value.json()
        setCategories(d?.data ?? [])
      }
    } catch { /* silent */ }
    finally { setLoading(false) }
  }, [selectedEndpoint, authToken]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetchAll() }, [fetchAll])

  const handleDelete = async (id: string) => {
    if (!selectedEndpoint) return
    try {
      const res = await fetch(APIRoutes.DeleteCultureEntry(selectedEndpoint, id), { method: 'DELETE', headers })
      if (!res.ok) throw new Error(res.statusText)
      setEntries((prev) => prev.filter((e) => e.id !== id))
      toast.success('Principle deleted')
    } catch { toast.error('Delete failed') }
  }

  // Client-side filter (server already handles this for initial load;
  // here we filter the cached list as user types)
  const filtered = entries.filter((e) => {
    const matchesCat = activeCat ? e.categories.includes(activeCat) : true
    if (!matchesCat) return false
    if (!search) return true
    const ql = search.toLowerCase()
    return (
      e.name.toLowerCase().includes(ql) ||
      (e.summary ?? '').toLowerCase().includes(ql) ||
      (e.content ?? '').toLowerCase().includes(ql) ||
      e.categories.some((c) => c.toLowerCase().includes(ql))
    )
  })

  // Derived stats
  const agentIds = [...new Set(entries.map((e) => e.agent_id).filter(Boolean))] as string[]
  const autoLearned = entries.filter((e) => e.agent_id).length
  const manualSeeded = entries.length - autoLearned

  return (
    <motion.div
      className="h-full overflow-y-auto p-6"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
    >
      <div className="mx-auto max-w-4xl space-y-6">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-medium text-primary">
              <Sparkles className="size-5 text-brand" />Culture
            </h1>
            <p className="mt-1 text-xs text-muted">
              Universal principles &amp; best practices shared across all agents — the collective intelligence of your fleet
            </p>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => setShowAdd(true)} className="gap-1.5">
              <Plus className="size-3.5" />Add Principle
            </Button>
            <Button size="sm" variant="outline" onClick={fetchAll} disabled={loading} className="gap-1.5">
              <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />Refresh
            </Button>
          </div>
        </div>

        {/* Stats row */}
        {loading ? (
          <div className="grid grid-cols-3 gap-3">
            {[0,1,2].map((i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-3">
            {[
              ['Total Principles', entries.length],
              ['Auto-learned', autoLearned],
              ['Manually Seeded', manualSeeded],
            ].map(([label, val]) => (
              <div key={String(label)} className="rounded-xl border border-accent bg-primaryAccent p-4 text-center">
                <div className="text-2xl font-semibold text-primary">{val}</div>
                <div className="mt-1 text-xs uppercase text-muted">{label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Category chips */}
        {categories.length > 0 && (
          <div className="rounded-xl border border-accent bg-primaryAccent p-4">
            <div className="mb-2.5 flex items-center gap-2">
              <BookOpen className="size-3.5 text-muted" />
              <span className="text-xs font-medium uppercase text-muted">Filter by category</span>
              {activeCat && (
                <button
                  onClick={() => setActiveCat(null)}
                  className="ml-auto flex items-center gap-1 rounded-full bg-accent px-2 py-0.5 text-xs text-muted hover:text-primary"
                >
                  <X className="size-3" />Clear
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {categories.map((c) => (
                <button
                  key={c}
                  onClick={() => setActiveCat(activeCat === c ? null : c)}
                  className={cn(
                    'flex items-center gap-0.5 rounded-full px-2.5 py-1 text-xs font-medium transition-colors',
                    activeCat === c
                      ? cn(catColour(c), 'ring-1 ring-current/30')
                      : 'bg-accent text-muted hover:text-primary',
                  )}
                >
                  <Tag className="size-2.5" />{c}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Agent contribution bar */}
        {agentIds.length > 0 && (
          <div className="rounded-xl border border-accent bg-primaryAccent p-4">
            <div className="mb-3 flex items-center gap-2">
              <Bot className="size-3.5 text-muted" />
              <span className="text-xs font-medium uppercase text-muted">Agent contributions</span>
            </div>
            <div className="space-y-2">
              {agentIds
                .map((a) => ({ agent: a, count: entries.filter((e) => e.agent_id === a).length }))
                .sort((a, b) => b.count - a.count)
                .map(({ agent, count }) => (
                  <div key={agent} className="flex items-center gap-3">
                    <button
                      onClick={() => setActiveCat(null)}
                      className="w-28 truncate text-left text-xs text-primary hover:text-brand"
                    >
                      {agent}
                    </button>
                    <div className="flex-1 overflow-hidden rounded-full bg-accent" style={{ height: '6px' }}>
                      <div
                        className="h-full rounded-full bg-brand"
                        style={{ width: `${Math.round((count / entries.length) * 100)}%` }}
                      />
                    </div>
                    <div className="w-6 text-right text-xs text-muted">{count}</div>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search principles…"
            className="w-full rounded-xl border border-accent bg-primaryAccent pl-8 pr-3 py-2 text-xs text-primary outline-none focus:border-primary/30"
          />
        </div>

        {/* Count line */}
        {!loading && (
          <div className="text-xs text-muted">
            {filtered.length} {filtered.length === 1 ? 'principle' : 'principles'}
            {activeCat && <> in <span className={cn('rounded-full px-1.5 py-0.5 text-xs', catColour(activeCat))}>{activeCat}</span></>}
            {search && <> matching &quot;{search}&quot;</>}
          </div>
        )}

        {/* List */}
        <div className="space-y-3">
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-accent bg-primaryAccent py-16 text-center">
              <Sparkles className="size-10 text-muted/20" />
              <p className="mt-3 text-sm font-medium text-muted">
                {entries.length === 0 ? 'No cultural knowledge yet' : 'No results'}
              </p>
              <p className="mt-1 text-xs text-muted/60">
                {entries.length === 0
                  ? <>Seed principles with <code className="rounded bg-accent px-1">scripts/seed_culture.py</code> or click "Add Principle".</>
                  : 'Try a different search or category filter.'}
              </p>
              {entries.length === 0 && (
                <Button size="sm" variant="outline" onClick={() => setShowAdd(true)} className="mt-4 gap-1.5">
                  <Plus className="size-3.5" />Add First Principle
                </Button>
              )}
            </div>
          ) : (
            filtered.map((e) => (
              <CultureCard key={e.id ?? e.name} entry={e} onDelete={handleDelete} />
            ))
          )}
        </div>
      </div>

      {/* Add modal */}
      <AnimatePresence>
        {showAdd && (
          <AddCultureModal
            endpoint={selectedEndpoint}
            headers={headers}
            onClose={() => setShowAdd(false)}
            onCreated={fetchAll}
          />
        )}
      </AnimatePresence>
    </motion.div>
  )
}
