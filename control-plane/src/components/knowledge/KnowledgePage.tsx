'use client'
import { motion } from 'framer-motion'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useSearchParams } from 'next/navigation'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  BookOpen, RefreshCw, Search, ChevronDown, ChevronUp, Plus, Trash2,
  FileText, Link2, Upload, X, AlertCircle, Globe
} from 'lucide-react'
import dayjs from 'dayjs'
import { toast } from 'sonner'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface KBConfig { id: string; name: string }

interface KBDocument {
  id: string
  name?: string
  description?: string
  type?: string
  size?: string
  linked_to?: string | null
  metadata?: Record<string, unknown> | null
  access_count?: number | null
  status?: string
  status_message?: string
  created_at?: string
  updated_at?: string
  // populated only in search results
  content?: string
  score?: number
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const formatSize = (bytes?: string): string => {
  if (!bytes) return ''
  const n = parseInt(bytes, 10)
  if (isNaN(n)) return bytes
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

const inferKBName = (docs: KBDocument[]): string => {
  if (docs.length === 0) return 'Knowledge Base'
  const names = docs.map(d => (d.name ?? '').toLowerCase())
  const codeExts = /\.(ts|tsx|js|jsx|py|java|cs|go|rs|sh|yaml|yml|toml|md)$/
  if (names.some(n => codeExts.test(n))) return 'Automation Codebase'
  if (names.some(n => n.endsWith('.pdf'))) return 'Document Library'
  if (names.some(n => n.includes('rca') || n.includes('trace') || n.includes('failure'))) return 'RCA History'
  if (names.some(n => n.includes('manifest') || n.includes('site'))) return 'Site Manifesto'
  return docs[0]?.name?.slice(0, 28) ?? 'Knowledge Base'
}

// ---------------------------------------------------------------------------
// DocCard
// ---------------------------------------------------------------------------
const DocCard = ({ doc, onDelete }: { doc: KBDocument; onDelete: (id: string) => void }) => {
  const [expanded, setExpanded] = useState(false)
  const statusColor =
    doc.status === 'completed'  ? 'text-green-400' :
    doc.status === 'error'      ? 'text-destructive' :
    doc.status === 'processing' ? 'text-yellow-400' : 'text-muted'

  return (
    <div className="rounded-xl border border-accent bg-primaryAccent">
      <div className="flex items-start gap-3 p-4">
        <BookOpen className="mt-0.5 size-4 shrink-0 text-brand" />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-primary truncate">{doc.name || doc.id.slice(0, 16)}</span>
            {doc.status && (
              <span className={cn('rounded-full bg-accent px-2 py-0.5 text-xs uppercase', statusColor)}>{doc.status}</span>
            )}
            {doc.type && (
              <span className="rounded-full bg-accent px-2 py-0.5 text-xs text-muted">{doc.type}</span>
            )}
            {doc.size && (
              <span className="rounded-full bg-accent px-2 py-0.5 text-xs text-muted">{formatSize(doc.size)}</span>
            )}
          </div>
          {doc.description && (
            <div className="mt-1 truncate text-xs text-muted/70">{doc.description}</div>
          )}
          <div className="mt-0.5 text-xs text-muted/50">
            {doc.updated_at
              ? `Updated ${dayjs(doc.updated_at).format('MMM D, HH:mm')}`
              : doc.created_at
                ? dayjs(doc.created_at).format('MMM D, HH:mm')
                : null}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => onDelete(doc.id)}
            className="rounded-lg p-1.5 text-muted hover:bg-destructive/10 hover:text-destructive"
          >
            <Trash2 className="size-3.5" />
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="rounded-lg p-1.5 text-muted hover:bg-accent hover:text-primary"
          >
            {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          </button>
        </div>
      </div>
      {expanded && (
        <div className="border-t border-accent px-4 pb-4 pt-3 space-y-3 text-xs">
          {doc.description && (
            <div>
              <div className="text-muted/60 uppercase tracking-wide text-[10px] mb-0.5">Description</div>
              <p className="text-primary">{doc.description}</p>
            </div>
          )}
          <div className="grid grid-cols-2 gap-x-6 gap-y-2">
            {doc.type && (
              <div>
                <div className="text-muted/60 mb-0.5">Type</div>
                <div className="text-primary font-mono">{doc.type}</div>
              </div>
            )}
            {doc.size && (
              <div>
                <div className="text-muted/60 mb-0.5">Size</div>
                <div className="text-primary">{formatSize(doc.size)}</div>
              </div>
            )}
            {doc.access_count != null && (
              <div>
                <div className="text-muted/60 mb-0.5">Accessed</div>
                <div className="text-primary">{doc.access_count}×</div>
              </div>
            )}
            {doc.updated_at && (
              <div>
                <div className="text-muted/60 mb-0.5">Updated</div>
                <div className="text-primary">{dayjs(doc.updated_at).format('MMM D, YYYY HH:mm')}</div>
              </div>
            )}
          </div>
          {doc.status_message && (
            <div>
              <div className="text-muted/60 uppercase tracking-wide text-[10px] mb-0.5">Status</div>
              <p className="text-muted">{doc.status_message}</p>
            </div>
          )}
          {doc.linked_to && (
            <div>
              <div className="text-muted/60 uppercase tracking-wide text-[10px] mb-0.5">Linked To</div>
              <p className="font-mono text-brand truncate">{doc.linked_to}</p>
            </div>
          )}
          {doc.metadata && Object.keys(doc.metadata).length > 0 && (
            <div>
              <div className="text-muted/60 uppercase tracking-wide text-[10px] mb-0.5">Metadata</div>
              <pre className="mt-1 max-h-40 overflow-y-auto rounded-xl bg-background p-3 text-xs text-muted">
                {JSON.stringify(doc.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// SearchResultCard  (simpler — no delete)
// ---------------------------------------------------------------------------
const SearchResultCard = ({ doc }: { doc: KBDocument & { score?: number } }) => {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="rounded-xl border border-brand/20 bg-primaryAccent">
      <div className="flex items-start gap-3 p-4">
        <Search className="mt-0.5 size-4 shrink-0 text-brand" />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-primary truncate">{doc.name || doc.id?.slice(0, 16)}</span>
            {(doc as { score?: number }).score !== undefined && (
              <span className="rounded-full bg-brand/10 px-2 py-0.5 text-xs text-brand">
                {((doc as { score?: number }).score! * 100).toFixed(0)}% match
              </span>
            )}
          </div>
          {doc.content && (
            <div className="mt-1 text-xs text-muted/70 leading-relaxed">
              {expanded ? doc.content : doc.content.slice(0, 200) + (doc.content.length > 200 ? '…' : '')}
            </div>
          )}
        </div>
        {doc.content && doc.content.length > 200 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="shrink-0 rounded-lg p-1.5 text-muted hover:bg-accent hover:text-primary"
          >
            {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          </button>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------
type UploadTab = 'text' | 'file' | 'url' | 'remote'

export default function KnowledgePage() {
  const { selectedEndpoint, authToken } = useStore()
  const searchParams = useSearchParams()
  const dbId = searchParams.get('db_id') ?? ''
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Whether the selected KB id is a knowledge_id (UUID) or db_id (plain name)
  const [kbIdIsKnowledgeId, setKbIdIsKnowledgeId] = useState(false)
  const [kbs, setKbs]               = useState<KBConfig[]>([])
  const [selectedKb, setSelectedKb] = useState<string>(dbId)
  const [docs, setDocs]             = useState<KBDocument[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [loading, setLoading]       = useState(false)

  // search
  const [searchQuery, setSearchQuery]     = useState('')
  const [searchResults, setSearchResults] = useState<KBDocument[] | null>(null)
  const [searching, setSearching]         = useState(false)
  const [searchMaxResults, setSearchMaxResults] = useState(10)

  // upload panel
  const [uploadTab, setUploadTab]     = useState<UploadTab>('text')
  const [uploadName, setUploadName]   = useState('')
  const [textContent, setTextContent] = useState('')
  const [urlInput, setUrlInput]       = useState('')
  const [remoteUrl, setRemoteUrl]     = useState('')
  const [remoteLoader, setRemoteLoader] = useState('website')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading]     = useState(false)

  const authHeaders: Record<string, string> = authToken
    ? { Authorization: `Bearer ${authToken}` }
    : {}

  // Returns true when an ID looks like a UUID (knowledge_id), false for human-readable db_id
  const isUUID = (id: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)

  // Build the correct URL params for the given KB id
  const kbParam = useCallback((id: string): Record<string, string> => {
    return isUUID(id) ? { knowledge_id: id } : { db_id: id }
  }, [])

  // ── fetch KBs ───────────────────────────────────────────────────────
  const fetchKbs = useCallback(async () => {
    if (!selectedEndpoint) {
      setKbs([])
      setSelectedKb('')
      return
    }
    const probe = dbId || undefined
    try {
      const url = new URL(APIRoutes.KnowledgeContent(selectedEndpoint))
      url.searchParams.set('limit', '1')
      if (probe) url.searchParams.set('db_id', probe)
      const res = await fetch(url.toString(), { headers: authHeaders })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        const detail = String(err.detail ?? '')
        const match = detail.match(/Available IDs:\s*\[([^\]]+)\]/)
        if (match) {
          const ids = match[1].split(',').map((s) => s.trim().replace(/'/g, ''))
          setKbIdIsKnowledgeId(true)
          // Resolve a readable name for each KB by sampling its first documents
          const resolved = await Promise.all(
            ids.map(async (id) => {
              try {
                const docUrl = new URL(APIRoutes.KnowledgeContent(selectedEndpoint))
                docUrl.searchParams.set('knowledge_id', id)
                docUrl.searchParams.set('limit', '3')
                const r = await fetch(docUrl.toString(), { headers: authHeaders })
                if (r.ok) {
                  const d = await r.json()
                  return { id, name: inferKBName(d?.data ?? []) }
                }
              } catch { /* ignore */ }
              return { id, name: `KB ${id.slice(0, 8)}` }
            })
          )
          // Use only API-discovered KBs — no hardcoded fallbacks
          setKbs(resolved)
          setSelectedKb(probe && ids.includes(probe) ? probe : resolved[0]?.id ?? '')
          return
        }
      } else if (probe) {
        // Probe succeeded with a specific known ID
        setKbs([{ id: probe, name: inferKBName([]) }])
        setKbIdIsKnowledgeId(isUUID(probe))
        setSelectedKb(probe)
        return
      }
    } catch { /* silently handled */ }
    // No KBs discovered from backend — show empty state
    setKbs([])
    setSelectedKb('')
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedEndpoint, authToken, dbId])

  // ── fetch documents ─────────────────────────────────────────────────────
  const fetchDocs = useCallback(async (kbId?: string) => {
    if (!selectedEndpoint) return
    const resolvedId = kbId || selectedKb
    if (!resolvedId) return
    setLoading(true)
    try {
      const url = new URL(APIRoutes.KnowledgeContent(selectedEndpoint))
      url.searchParams.set('limit', '50')
      // Use knowledge_id for UUID-format IDs, db_id for human-readable names
      const params = kbId ? kbParam(kbId) : kbParam(resolvedId)
      Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
      const res = await fetch(url.toString(), { headers: authHeaders })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        const detail = String(err.detail ?? '')
        const match = detail.match(/Available IDs:\s*\[([^\]]+)\]/)
        if (match) {
          // API returns UUID-based knowledge_ids — probe each to find docs for the selected KB.
          // Never overwrite the friendly KB list; just swap in the UUID for this KB.
          const ids = match[1].split(',').map((s: string) => s.trim().replace(/'/g, ''))
          setKbIdIsKnowledgeId(true)
          for (const uuid of ids) {
            try {
              const uuidUrl = new URL(APIRoutes.KnowledgeContent(selectedEndpoint))
              uuidUrl.searchParams.set('knowledge_id', uuid)
              uuidUrl.searchParams.set('limit', '50')
              const uuidRes = await fetch(uuidUrl.toString(), { headers: authHeaders })
              if (uuidRes.ok) {
                const d = await uuidRes.json()
                const found: KBDocument[] = d?.data ?? []
                if (found.length > 0) {
                  setDocs(found)
                  setTotalCount(d?.meta?.total_count ?? found.length)
                  // Replace this KB's db_id with its UUID so future fetches skip the round-trip
                  setKbs(prev => prev.map(k => k.id === resolvedId ? { ...k, id: uuid } : k))
                  setSelectedKb(uuid)
                  return
                }
              }
            } catch { /* try next UUID */ }
          }
        }
        setDocs([]); return
      }
      const data = await res.json()
      setDocs(data?.data ?? [])
      setTotalCount(data?.meta?.total_count ?? data?.data?.length ?? 0)
    } catch { setDocs([]) }
    finally { setLoading(false) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedEndpoint, authToken])

  // ── search (POST) ────────────────────────────────────────────────────────
  const handleSearch = async () => {
    if (!searchQuery.trim() || !selectedEndpoint) return
    setSearching(true)
    try {
      const resolvedId = selectedKb
      const body: Record<string, unknown> = { query: searchQuery, max_results: searchMaxResults }
      if (resolvedId) {
        const p = kbParam(resolvedId)
        Object.assign(body, p)
      }
      const res = await fetch(APIRoutes.KnowledgeSearch(selectedEndpoint), {
        method: 'POST',
        headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      const data = await res.json()
      setSearchResults(data?.data ?? data ?? [])
    } catch { toast.error('Search failed') }
    finally { setSearching(false) }
  }

  // ── upload (multipart/form-data) ─────────────────────────────────────────
  const handleUpload = async () => {
    if (!selectedEndpoint) return
    if (uploadTab === 'text' && !textContent.trim()) return
    if (uploadTab === 'url'  && !urlInput.trim())    return
    if (uploadTab === 'file' && !selectedFile)        return
    if (uploadTab === 'remote' && !remoteUrl.trim())  return

    setUploading(true)
    try {
      if (uploadTab === 'remote') {
        const body: Record<string, unknown> = {
          url: remoteUrl.trim(),
          loader_type: remoteLoader,
        }
        if (selectedKb) Object.assign(body, kbParam(selectedKb))
        const res = await fetch(APIRoutes.RemoteContent(selectedEndpoint), {
          method: 'POST',
          headers: { ...authHeaders, 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        if (!res.ok) throw new Error(await res.text())
        toast.success('Remote source queued for indexing')
        setRemoteUrl('')
        setTimeout(() => fetchDocs(selectedKb), 2000)
        return
      }
      const resolvedId = selectedKb
      const uploadUrl = new URL(APIRoutes.KnowledgeContent(selectedEndpoint))
      if (resolvedId) {
        const params = kbParam(resolvedId)
        Object.entries(params).forEach(([k, v]) => uploadUrl.searchParams.set(k, v))
      }

      const fd = new FormData()
      if (uploadName.trim()) fd.append('name', uploadName.trim())

      if (uploadTab === 'text') {
        fd.append('text_content', textContent)
      } else if (uploadTab === 'url') {
        fd.append('url', urlInput.trim())
      } else if (uploadTab === 'file' && selectedFile) {
        fd.append('file', selectedFile)
      }

      const res = await fetch(uploadUrl.toString(), {
        method: 'POST',
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
        body: fd
      })
      if (!res.ok) throw new Error(await res.text())

      toast.success('Content uploaded — processing in background')
      setTextContent(''); setUrlInput(''); setUploadName(''); setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      setTimeout(() => fetchDocs(selectedKb), 1500)
    } catch (e) {
      toast.error(`Upload failed: ${e instanceof Error ? e.message : String(e)}`)
    } finally { setUploading(false) }
  }

  // ── delete ───────────────────────────────────────────────────────────────
  const handleDelete = async (docId: string) => {
    if (!selectedEndpoint) return
    try {
      await fetch(APIRoutes.KnowledgeContentById(selectedEndpoint, docId), {
        method: 'DELETE',
        headers: authHeaders
      })
      setDocs((prev) => prev.filter((d) => d.id !== docId))
      toast.success('Document deleted')
    } catch { toast.error('Delete failed') }
  }

  useEffect(() => { fetchKbs() }, [fetchKbs])
  useEffect(() => { if (selectedKb) fetchDocs(selectedKb) }, [selectedKb, fetchDocs])

  const canUpload =
    (uploadTab === 'text'   && textContent.trim().length > 0) ||
    (uploadTab === 'url'    && urlInput.trim().length > 0) ||
    (uploadTab === 'file'   && !!selectedFile) ||
    (uploadTab === 'remote' && remoteUrl.trim().length > 0)

  const displayDocs = searchResults !== null ? searchResults : docs

  return (
    <motion.div className="h-full overflow-y-auto p-6" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2, ease: 'easeOut' }}>
      <div className="mx-auto max-w-4xl space-y-6">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-medium text-primary">
              <BookOpen className="size-5 text-brand" />Knowledge
            </h1>
            <p className="mt-1 text-xs text-muted">Search and manage vectorized knowledge bases</p>
          </div>
          <Button size="sm" variant="outline" onClick={() => fetchDocs(selectedKb)} disabled={loading} className="gap-1.5">
            <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />Refresh
          </Button>
        </div>

        {/* KB selector */}
        {kbs.length > 1 && (
          <div className="flex gap-1 rounded-xl border border-accent bg-primaryAccent p-1 overflow-x-auto">
            {kbs.map((kb) => (
              <button
                key={kb.id}
                onClick={() => setSelectedKb(kb.id)}
                className={cn(
                  'shrink-0 rounded-lg px-3 py-1.5 text-xs font-mono transition-colors',
                  selectedKb === kb.id ? 'bg-accent text-primary' : 'text-muted hover:text-primary'
                )}
              >
                {kb.name}
              </button>
            ))}
          </div>
        )}

        {/* Empty state — no KBs discovered from backend */}
        {kbs.length === 0 && !loading && selectedEndpoint && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-accent bg-primaryAccent py-10 text-center">
            <BookOpen className="size-8 text-muted/20" />
            <p className="mt-3 text-sm font-medium text-muted">No knowledge bases found</p>
            <p className="mt-1 text-xs text-muted/60">
              No indexed knowledge bases were returned by the backend.
            </p>
          </div>
        )}

        {/* Search */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted" />
            <input
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); if (!e.target.value) setSearchResults(null) }}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Semantic search the knowledge base…"
              className="w-full rounded-xl border border-accent bg-primaryAccent pl-8 pr-3 py-2 text-xs text-primary outline-none focus:border-primary/30"
            />
          </div>
          <select
            value={searchMaxResults}
            onChange={(e) => setSearchMaxResults(Number(e.target.value))}
            className="rounded-xl border border-accent bg-primaryAccent px-2 py-2 text-xs text-muted outline-none focus:border-primary/30"
            title="Max results"
          >
            {[5, 10, 20, 50].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
          <Button size="sm" onClick={handleSearch} disabled={searching || !searchQuery.trim()} className="gap-1.5">
            <Search className="size-3.5" />{searching ? 'Searching…' : 'Search'}
          </Button>
          {searchResults !== null && (
            <Button size="sm" variant="outline" onClick={() => { setSearchResults(null); setSearchQuery('') }}>
              <X className="size-3.5" />
            </Button>
          )}
        </div>

        {/* Upload panel */}
        <div className="rounded-xl border border-accent bg-primaryAccent overflow-hidden">
          {/* Tab bar */}
          <div className="flex border-b border-accent">
            {([
              { id: 'text'   as UploadTab, icon: FileText, label: 'Text' },
              { id: 'file'   as UploadTab, icon: Upload,   label: 'Upload File' },
              { id: 'url'    as UploadTab, icon: Link2,    label: 'Add URL' },
              { id: 'remote' as UploadTab, icon: Globe,    label: 'Remote Source' },
            ] as const).map(({ id, icon: Icon, label }) => (
              <button
                key={id}
                onClick={() => setUploadTab(id)}
                className={cn(
                  'flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium transition-colors',
                  uploadTab === id
                    ? 'border-b-2 border-brand text-brand'
                    : 'text-muted hover:text-primary'
                )}
              >
                <Icon className="size-3.5" />{label}
              </button>
            ))}
          </div>

          <div className="p-4 space-y-3">
            <input
              value={uploadName}
              onChange={(e) => setUploadName(e.target.value)}
              placeholder="Name (optional)…"
              className="w-full rounded-xl border border-accent bg-background px-3 py-2 text-xs text-primary outline-none focus:border-primary/30"
            />

            {uploadTab === 'text' && (
              <textarea
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                placeholder="Paste text content here…"
                rows={5}
                className="w-full rounded-xl border border-accent bg-background px-3 py-2 text-xs text-primary outline-none resize-none focus:border-primary/30"
              />
            )}

            {uploadTab === 'file' && (
              <div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.csv,.docx,.txt,.json,.md"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed border-accent bg-background py-6 text-xs text-muted hover:border-brand/40 hover:text-primary transition-colors"
                >
                  {selectedFile ? (
                    <span className="flex items-center gap-2 text-primary">
                      <FileText className="size-4 text-brand" />{selectedFile.name}
                      <span className="text-muted">({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                    </span>
                  ) : (
                    <>
                      <Upload className="size-4" />
                      Click to select a file (PDF, CSV, DOCX, TXT, JSON, MD)
                    </>
                  )}
                </button>
                {selectedFile && (
                  <button
                    onClick={() => { setSelectedFile(null); if (fileInputRef.current) fileInputRef.current.value = '' }}
                    className="mt-1 flex items-center gap-1 text-xs text-muted hover:text-destructive"
                  >
                    <X className="size-3" />Remove file
                  </button>
                )}
              </div>
            )}

            {uploadTab === 'url' && (
              <div>
                <input
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="https://example.com/document or https://example.com/page"
                  className="w-full rounded-xl border border-accent bg-background px-3 py-2 text-xs text-primary outline-none focus:border-primary/30"
                />
                <p className="mt-1 text-xs text-muted/60">
                  Supports web pages, GitHub raw URLs, and direct document links
                </p>
              </div>
            )}

            {uploadTab === 'remote' && (
              <div className="space-y-2">
                <input
                  value={remoteUrl}
                  onChange={(e) => setRemoteUrl(e.target.value)}
                  placeholder="https://example.com/ — crawl and index via Agno loader"
                  className="w-full rounded-xl border border-accent bg-background px-3 py-2 text-xs text-primary outline-none focus:border-primary/30"
                />
                <select
                  value={remoteLoader}
                  onChange={(e) => setRemoteLoader(e.target.value)}
                  className="w-full rounded-xl border border-accent bg-background px-3 py-2 text-xs text-primary outline-none focus:border-primary/30"
                >
                  {['website', 'sitemap', 'pdf', 'docx', 'csv', 'arxiv', 'github', 'jira', 'confluence'].map((l) => (
                    <option key={l} value={l}>{l}</option>
                  ))}
                </select>
                <p className="text-xs text-muted/60">
                  Uses Agno&apos;s remote content loader — crawls and vectorizes the target source.
                </p>
              </div>
            )}

            <Button
              size="sm"
              onClick={handleUpload}
              disabled={uploading || !canUpload}
              className="gap-1.5"
            >
              {uploading ? (
                <RefreshCw className="size-3.5 animate-spin" />
              ) : (
                <Plus className="size-3.5" />
              )}
              {uploading ? 'Uploading…' : uploadTab === 'remote' ? 'Index Remote Source' : 'Add to Knowledge Base'}
            </Button>
          </div>
        </div>

        {/* Stats bar */}
        {!loading && docs.length > 0 && searchResults === null && (
          <div className="flex items-center gap-2 text-xs text-muted">
            <AlertCircle className="size-3.5" />
            {totalCount} document{totalCount !== 1 ? 's' : ''} indexed
            {selectedKb && (
              <span>· KB: <span className="font-mono">{kbs.find(k => k.id === selectedKb)?.name ?? selectedKb.slice(0, 12) + '…'}</span></span>
            )}
          </div>
        )}

        {/* Document / result list */}
        <div className="space-y-3">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)
          ) : displayDocs.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-accent bg-primaryAccent py-16 text-center">
              <BookOpen className="size-10 text-muted/20" />
              <p className="mt-3 text-sm font-medium text-muted">
                {searchResults !== null ? 'No results found' : 'No documents indexed'}
              </p>
              <p className="mt-1 text-xs text-muted/60">
                {searchResults !== null
                  ? 'Try a different search query.'
                  : 'Upload text, a file, or a URL to start indexing.'}
              </p>
            </div>
          ) : searchResults !== null ? (
            displayDocs.map((doc, i) => <SearchResultCard key={doc.id ?? i} doc={doc} />)
          ) : (
            displayDocs.map((doc) => <DocCard key={doc.id} doc={doc} onDelete={handleDelete} />)
          )}
        </div>
      </div>
    </motion.div>
  )
}

