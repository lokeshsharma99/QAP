'use client'
import { useEffect, useState, useCallback } from 'react'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { Brain, RefreshCw, Search, Trash2, ChevronDown, ChevronUp, Sparkles } from 'lucide-react'
import dayjs from 'dayjs'
import { toast } from 'sonner'

interface Memory {
  id: string
  memory?: string
  summary?: string
  topics?: string[]
  user_id?: string
  agent_id?: string
  created_at?: string
  updated_at?: string
  score?: number
}

interface MemoryTopic {
  topic: string
  count: number
}

const MemoryCard = ({ mem, onDelete }: { mem: Memory; onDelete: (id: string) => void }) => {
  const [expanded, setExpanded] = useState(false)
  const text = mem.memory || mem.summary || ''

  return (
    <div className="rounded-xl border border-accent bg-primaryAccent">
      <div className="flex items-start gap-3 p-4">
        <Brain className="mt-0.5 size-4 shrink-0 text-brand" />
        <div className="flex-1 min-w-0">
          <div className="text-sm text-primary line-clamp-2">{text}</div>
          <div className="mt-1 flex flex-wrap gap-2">
            {mem.topics?.map((t) => (
              <span key={t} className="rounded-full bg-accent px-2 py-0.5 text-xs text-muted">{t}</span>
            ))}
            {mem.agent_id && <span className="rounded-full bg-brand/10 px-2 py-0.5 text-xs text-brand">{mem.agent_id}</span>}
            {mem.score !== undefined && (
              <span className={cn('rounded-full px-2 py-0.5 text-xs', mem.score >= 0.9 ? 'bg-positive/10 text-positive' : 'bg-accent text-muted')}>
                {Math.round(mem.score * 100)}%
              </span>
            )}
          </div>
          <div className="mt-0.5 text-xs text-muted/50">
            {mem.updated_at ? dayjs(mem.updated_at).format('MMM D, HH:mm') : mem.created_at ? dayjs(mem.created_at).format('MMM D, HH:mm') : ''}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button onClick={() => onDelete(mem.id)} className="rounded-lg p-1.5 text-muted hover:bg-destructive/10 hover:text-destructive">
            <Trash2 className="size-3.5" />
          </button>
          {text.length > 100 && (
            <button onClick={() => setExpanded(!expanded)} className="rounded-lg p-1.5 text-muted hover:bg-accent hover:text-primary">
              {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
            </button>
          )}
        </div>
      </div>
      {expanded && (
        <div className="border-t border-accent px-4 pb-4">
          <div className="mt-3 rounded-xl bg-background p-3 text-xs text-primary leading-relaxed whitespace-pre-wrap">{text}</div>
          {mem.id && <div className="mt-2 font-mono text-xs text-muted/50">ID: {mem.id}</div>}
        </div>
      )}
    </div>
  )
}

export default function MemoryPage() {
  const { selectedEndpoint, authToken } = useStore()
  const [memories, setMemories] = useState<Memory[]>([])
  const [topics, setTopics] = useState<MemoryTopic[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [optimizing, setOptimizing] = useState(false)

  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}) }

  const fetchAll = useCallback(async () => {
    if (!selectedEndpoint) return
    setLoading(true)
    try {
      const [memRes, topicRes] = await Promise.allSettled([
        fetch(APIRoutes.GetMemories(selectedEndpoint), { headers }),
        fetch(APIRoutes.MemoryTopics(selectedEndpoint), { headers }),
      ])
      if (memRes.status === 'fulfilled' && memRes.value.ok) {
        const d = await memRes.value.json(); setMemories(d?.data ?? [])
      }
      if (topicRes.status === 'fulfilled' && topicRes.value.ok) {
        const d = await topicRes.value.json(); setTopics(d?.data ?? d ?? [])
      }
    } catch { /* handled */ }
    finally { setLoading(false) }
  }, [selectedEndpoint, authToken])

  const handleDelete = async (id: string) => {
    if (!selectedEndpoint) return
    try {
      const res = await fetch(APIRoutes.GetMemory(selectedEndpoint, id), { method: 'DELETE', headers })
      if (!res.ok) throw new Error(res.statusText)
      setMemories((prev) => prev.filter((m) => m.id !== id))
      toast.success('Memory deleted')
    } catch { toast.error('Delete failed') }
  }

  const handleOptimize = async () => {
    if (!selectedEndpoint) return
    setOptimizing(true)
    try {
      const res = await fetch(APIRoutes.OptimizeMemories(selectedEndpoint), { method: 'POST', headers })
      if (!res.ok) throw new Error(res.statusText)
      toast.success('Memory optimization started')
      setTimeout(fetchAll, 2000)
    } catch { toast.error('Optimize failed') }
    finally { setOptimizing(false) }
  }

  useEffect(() => { fetchAll() }, [fetchAll])

  const filtered = search
    ? memories.filter((m) => (m.memory || m.summary || '').toLowerCase().includes(search.toLowerCase()) ||
        m.topics?.some((t) => t.toLowerCase().includes(search.toLowerCase())))
    : memories

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-medium text-primary">
              <Brain className="size-5 text-brand" />Memory
            </h1>
            <p className="mt-1 text-xs text-muted">Agent memories stored across sessions — view, search, delete</p>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={handleOptimize} disabled={optimizing} className="gap-1.5">
              <Sparkles className={cn('size-3.5', optimizing && 'animate-pulse')} />Optimize
            </Button>
            <Button size="sm" variant="outline" onClick={fetchAll} disabled={loading} className="gap-1.5">
              <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />Refresh
            </Button>
          </div>
        </div>

        {/* Stats + topics */}
        {loading ? (
          <Skeleton className="h-16 rounded-xl" />
        ) : (
          <div className="rounded-xl border border-accent bg-primaryAccent p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium uppercase text-muted">
                {memories.length} {memories.length === 1 ? 'memory' : 'memories'}
              </span>
            </div>
            {topics.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {topics.slice(0, 20).map((t) => (
                  <button key={t.topic} onClick={() => setSearch(t.topic)} className="flex items-center gap-1 rounded-full bg-accent px-2 py-0.5 text-xs text-muted hover:text-primary">
                    {t.topic}
                    <span className="text-muted/50">({t.count})</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search memories…"
            className="w-full rounded-xl border border-accent bg-primaryAccent pl-8 pr-3 py-2 text-xs text-primary outline-none focus:border-primary/30"
          />
        </div>

        {/* Memory list */}
        <div className="space-y-3">
          {loading ? (
            Array.from({length:3}).map((_,i)=><Skeleton key={i} className="h-16 rounded-xl"/>)
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-accent bg-primaryAccent py-16 text-center">
              <Brain className="size-10 text-muted/20" />
              <p className="mt-3 text-sm font-medium text-muted">No memories yet</p>
              <p className="mt-1 text-xs text-muted/60">Memories are created when agents run with <code>enable_agentic_memory=True</code>.</p>
            </div>
          ) : (
            filtered.map((mem) => <MemoryCard key={mem.id} mem={mem} onDelete={handleDelete} />)
          )}
        </div>
      </div>
    </div>
  )
}

