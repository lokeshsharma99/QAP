'use client'
import { useState, useEffect, useRef, lazy, Suspense } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '@/store'
import useChatActions from '@/hooks/useChatActions'
import useAIChatStreamHandler from '@/hooks/useAIStreamHandler'
import useSessionLoader from '@/hooks/useSessionLoader'
import { TextArea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { StickToBottom } from 'use-stick-to-bottom'
import Icon from '@/components/ui/icon'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
// rehypeSanitize intentionally removed — it corrupts code block text nodes, breaking mermaid
import { useTheme } from 'next-themes'
import SyntaxHighlighter from 'react-syntax-highlighter'
import { atomOneDark, atomOneLight } from 'react-syntax-highlighter/dist/cjs/styles/hljs'
import { useQueryState } from 'nuqs'
import { cn } from '@/lib/utils'
import dayjs from 'dayjs'
import { toast } from 'sonner'
import { ChatMessage } from '@/types/os'
import {
  ChevronDown, ChevronUp, Wrench, Brain, Plus, PanelRightOpen, PanelRightClose,
  Bot, Cpu, Database, Hash, Clock, CheckCircle, XCircle, Zap, GitBranch, Activity,
  Users, Settings, BookOpen, MemoryStick, Layers, MessageSquare, MessagesSquare,
  Play, CornerDownRight, ArrowUp, Paperclip, X as XIcon, FileText, Image as ImageIcon,
  Hammer, ChevronRight, Copy, Check, Square, Search, Settings2
} from 'lucide-react'

import { getAgentDetailAPI, getTeamDetailAPI, getWorkflowDetailAPI } from '@/api/os'
import { AgentFullDetail, TeamFullDetail, WorkflowFullDetail, WorkflowStep } from '@/types/os'
import AgentConfigPanel from '@/components/chat/AgentConfigPanel'
import { constructEndpointUrl } from '@/lib/constructEndpointUrl'

// ---------------------------------------------------------------------------
// Tool Calls — accordion item inside the sidebar panel
// ---------------------------------------------------------------------------
const ToolCallAccordionItem = ({ toolCall }: { toolCall: NonNullable<ChatMessage['tool_calls']>[0] }) => {
  const [open, setOpen] = useState(false)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const anyCall = toolCall as any
  const durationMs: string | null =
    anyCall.metrics?.time != null ? (anyCall.metrics.time * 1000).toFixed(3)
    : anyCall.metrics?.execution_time != null ? Number(anyCall.metrics.execution_time).toFixed(3)
    : null

  return (
    <div className="w-full rounded-lg border border-border bg-primaryAccent p-4">
      <h3 className="flex">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex flex-1 items-center gap-2 justify-between text-sm font-medium"
        >
          <div className="flex w-full">
            <div className="flex flex-col gap-1">
              <p className="font-inter text-[0.875rem] font-medium leading-5 tracking-[-0.02em] text-left">
                {toolCall.tool_name}
              </p>
              {toolCall.tool_call_error && (
                <span className="text-[0.7rem] text-destructive">error</span>
              )}
            </div>
          </div>
          <ChevronDown
            className={cn(
              'shrink-0 transition-transform duration-200 text-muted bg-accent border border-border/50 size-6 rounded-sm p-1',
              open && 'rotate-180'
            )}
          />
        </button>
      </h3>

      {open && (
        <div className="mt-4 space-y-4">
          {/* Tool Name */}
          <div>
            <p className="text-xs font-medium uppercase text-muted mb-1">Tool Name</p>
            <p className="font-inter text-[0.875rem] font-medium tracking-[-0.02em]">{toolCall.tool_name}</p>
          </div>

          {/* Tool Args */}
          {toolCall.tool_args && Object.keys(toolCall.tool_args).length > 0 && (
            <div>
              <p className="text-xs font-medium uppercase text-muted mb-2">Tool Args</p>
              <div className="space-y-2">
                {Object.entries(toolCall.tool_args).map(([key, value]) => (
                  <div key={key}>
                    <p className="text-xs text-muted/60 mb-0.5">{key} :</p>
                    <pre className="overflow-x-auto rounded bg-background px-2 py-1.5 text-xs text-primary whitespace-pre-wrap break-all font-dmmono">
                      {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metrics */}
          {durationMs && (
            <div>
              <p className="text-xs font-medium uppercase text-muted mb-1">Tool Metrics</p>
              <p className="text-xs font-dmmono text-muted">Duration: {durationMs} ms</p>
            </div>
          )}

          {/* Result */}
          {toolCall.content && (
            <div>
              <p className="text-xs font-medium uppercase text-muted mb-1">Tool Result</p>
              <pre
                className={cn(
                  'max-h-64 overflow-y-auto rounded px-2 py-1.5 text-xs font-dmmono whitespace-pre-wrap break-all',
                  toolCall.tool_call_error ? 'bg-destructive/10 text-destructive' : 'bg-background text-primary'
                )}
              >
                {typeof toolCall.content === 'string'
                  ? toolCall.content
                  : JSON.stringify(toolCall.content, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tool Calls — sliding sidebar panel
// ---------------------------------------------------------------------------
const ToolCallsSidebar = ({
  open,
  onClose,
  toolCalls,
}: {
  open: boolean
  onClose: () => void
  toolCalls: NonNullable<ChatMessage['tool_calls']>
}) => (
  <AnimatePresence>
    {open && (
      <>
        {/* invisible backdrop to close on outside click */}
        <motion.div
          key="tc-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-40"
          onClick={onClose}
        />
        {/* panel */}
        <motion.div
          key="tc-panel"
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          className="fixed inset-y-0 right-0 z-50 flex w-[500px] flex-col bg-accent border-l border-border shadow-xl"
          role="dialog"
          aria-label="Tool Calls"
        >
          {/* header */}
          <div className="sticky top-0 z-20 flex items-center border-b border-border bg-accent px-6 py-4 shrink-0">
            <h2 className="font-inter text-[0.875rem] font-medium leading-normal tracking-[-0.02em] truncate min-w-0 flex-1 pr-8">
              Tool Calls
            </h2>
            <button
              onClick={onClose}
              className="inline-flex size-6 items-center justify-center rounded-sm bg-secondary text-primary opacity-70 hover:opacity-100 transition-opacity"
            >
              <XIcon style={{ width: '10.67px', height: '10.67px' }} />
              <span className="sr-only">Close</span>
            </button>
          </div>
          {/* scrollable content */}
          <div className="flex-1 overflow-y-auto p-6 pt-4">
            <div className="flex flex-col gap-4">
              {toolCalls.map((tc, i) => (
                <ToolCallAccordionItem key={i} toolCall={tc} />
              ))}
            </div>
          </div>
        </motion.div>
      </>
    )}
  </AnimatePresence>
)

// ---------------------------------------------------------------------------
// Inline tool call steps — numbered timeline inside the chat message
// ---------------------------------------------------------------------------
const InlineToolSteps = ({ toolCalls }: { toolCalls: NonNullable<ChatMessage['tool_calls']> }) => {
  const [expanded, setExpanded] = useState(false)
  const [openIdx, setOpenIdx] = useState<number | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getDuration = (tc: NonNullable<ChatMessage['tool_calls']>[0]) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const a = tc as any
    const ms = a.metrics?.time != null ? a.metrics.time * 1000
      : a.metrics?.execution_time != null ? Number(a.metrics.execution_time)
      : null
    return ms !== null ? `${ms.toFixed(0)}ms` : null
  }
  const hasErrors = toolCalls.some((tc) => tc.tool_call_error)

  return (
    <div className="pl-9 my-1 max-w-2xl">
      <button
        onClick={() => setExpanded((o) => !o)}
        className="flex items-center gap-2 rounded-lg border border-accent/60 bg-background/60 px-2.5 py-1.5 text-xs text-muted hover:bg-accent hover:text-primary transition-colors w-full"
      >
        <Hammer className="size-3 text-brand shrink-0" />
        <span className="font-medium flex-1 text-left">
          {toolCalls.length} tool call{toolCalls.length !== 1 ? 's' : ''}
        </span>
        {hasErrors && <XCircle className="size-3 text-destructive shrink-0" />}
        <ChevronDown className={cn('size-3 shrink-0 transition-transform text-muted/40', expanded && 'rotate-180')} />
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            className="overflow-hidden"
          >
            <div className="mt-1.5 ml-2 border-l-2 border-accent pl-3 space-y-1">
              {toolCalls.map((tc, i) => {
                const dur = getDuration(tc)
                const isOpen = openIdx === i
                const hasError = !!tc.tool_call_error
                return (
                  <div key={i} className="rounded-lg border border-accent/40 bg-background overflow-hidden">
                    <button
                      onClick={() => setOpenIdx(isOpen ? null : i)}
                      className="flex w-full items-center gap-2 px-2.5 py-1.5 text-xs hover:bg-accent/30 transition-colors"
                    >
                      <span className="font-mono text-muted/30 shrink-0 w-4 text-right tabular-nums">{i + 1}</span>
                      <Hammer className={cn('size-3 shrink-0', hasError ? 'text-destructive' : 'text-brand')} />
                      <span className={cn('flex-1 text-left font-mono truncate', hasError ? 'text-destructive' : 'text-primary')}>{tc.tool_name}</span>
                      {dur && <span className="text-muted/40 font-mono shrink-0 text-[10px]">{dur}</span>}
                      {hasError
                        ? <XCircle className="size-3 text-destructive shrink-0" />
                        : <CheckCircle className="size-3 text-positive/50 shrink-0" />}
                      <ChevronDown className={cn('size-3 text-muted/30 shrink-0 transition-transform', isOpen && 'rotate-180')} />
                    </button>

                    {isOpen && (
                      <div className="px-3 pb-3 pt-1 space-y-2 border-t border-accent/30">
                        {tc.tool_args && Object.keys(tc.tool_args).length > 0 && (
                          <div>
                            <p className="text-[10px] font-semibold uppercase text-muted/60 mb-1">Args</p>
                            <div className="space-y-1">
                              {Object.entries(tc.tool_args).map(([k, v]) => (
                                <div key={k} className="flex gap-1.5 text-xs">
                                  <span className="text-muted/50 shrink-0 font-mono">{k}:</span>
                                  <span className="font-mono text-primary/80 break-all">
                                    {typeof v === 'string' ? v : JSON.stringify(v)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        {tc.content && (
                          <div>
                            <p className="text-[10px] font-semibold uppercase text-muted/60 mb-1">Result</p>
                            <pre className={cn(
                              'max-h-32 overflow-y-auto rounded px-2 py-1.5 text-xs font-dmmono whitespace-pre-wrap break-all',
                              hasError ? 'bg-destructive/10 text-destructive' : 'bg-accent/40 text-primary/80'
                            )}>
                              {typeof tc.content === 'string' ? tc.content : JSON.stringify(tc.content, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Robust message timestamp formatter
// ---------------------------------------------------------------------------
const fmtMsgTime = (ts: number | undefined | null): string => {
  if (!ts) return ''
  // distinguish unix-seconds (10 digits) from unix-milliseconds (13 digits)
  const d = ts > 9_999_999_999 ? dayjs(ts) : dayjs.unix(ts)
  return d.isValid() ? d.format('HH:mm') : ''
}

// ---------------------------------------------------------------------------
// Mermaid diagram renderer (browser-only, lazy-loaded)
// ---------------------------------------------------------------------------
const MermaidBlock = ({ code }: { code: string }) => {
  const ref = useRef<HTMLDivElement>(null)
  const idRef = useRef(`mermaid-${Math.random().toString(36).slice(2)}`)

  useEffect(() => {
    let cancelled = false
    const showFallback = () => {
      if (!cancelled && ref.current) {
        ref.current.innerHTML = `<pre class="text-xs text-muted/60 whitespace-pre-wrap p-3 rounded-xl bg-background border border-border/30">${code.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>`
      }
    }
    import('mermaid').then((m) => {
      if (cancelled) return
      m.default.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'loose' })
      m.default.render(idRef.current, code)
        .then(({ svg }) => {
          if (cancelled) return
          // Mermaid resolves (not rejects) with an error SVG on syntax errors
          if (svg.includes('class="error-icon"') || svg.includes('Syntax error in text')) {
            showFallback()
          } else if (ref.current) {
            ref.current.innerHTML = svg
          }
        })
        .catch(showFallback)
    }).catch(showFallback)
    return () => { cancelled = true }
  }, [code])

  return <div ref={ref} className="my-3 flex justify-center overflow-x-auto [&>svg]:max-w-full [&>svg]:h-auto" />
}

// ---------------------------------------------------------------------------
// Syntax-highlighted code block with language label + copy button
// ---------------------------------------------------------------------------
const CodeBlock = ({ lang, children }: { lang: string; children: string }) => {
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme !== 'light'
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(children).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="rounded-md overflow-hidden border border-border/50 mb-3">
      {/* header bar: language label + copy button */}
      <div className={cn(
        'flex items-center justify-between px-3 py-1.5 border-b border-border/30',
        isDark ? 'bg-[#2d2d2d]' : 'bg-[#f0f0f0]'
      )}>
        <span className="text-[0.7rem] font-medium uppercase text-muted/70 font-dmmono">
          {lang || 'code'}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-[0.65rem] text-muted/60 hover:text-primary transition-colors"
          title="Copy code"
        >
          {copied
            ? <><Check className="size-3 text-green-500" /><span className="text-green-500">Copied</span></>
            : <><Copy className="size-3" /><span>Copy</span></>}
        </button>
      </div>
      {/* syntax-highlighted body */}
      <SyntaxHighlighter
        language={lang || 'text'}
        style={isDark ? atomOneDark : atomOneLight}
        customStyle={{
          margin: 0,
          padding: '12px',
          fontSize: '0.8rem',
          lineHeight: '1.6',
          overflowX: 'auto',
          background: isDark ? '#1e1e1e' : '#f9f9f9',
        }}
        codeTagProps={{ style: { fontFamily: 'DM Mono, monospace' } }}
        wrapLongLines={false}
      >
        {children}
      </SyntaxHighlighter>
    </div>
  )
}

const ReasoningBlock = ({ steps }: { steps: NonNullable<ChatMessage['extra_data']>['reasoning_steps'] }) => {
  const [open, setOpen] = useState(false)
  if (!steps || steps.length === 0) return null
  return (
    <div className="mb-2 rounded-xl border border-accent/60 bg-accent/10 text-xs overflow-hidden">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 px-3 py-2 hover:bg-accent/20 transition-colors">
        <Brain className="size-3 text-info shrink-0" />
        <span className="flex-1 text-left text-muted font-medium">Reasoning</span>
        <span className="text-muted/40 tabular-nums">{steps.length} step{steps.length !== 1 ? 's' : ''}</span>
        <ChevronDown className={cn('size-3 text-muted/40 shrink-0 transition-transform', open && 'rotate-180')} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            className="overflow-hidden"
          >
            <div className="border-t border-accent/40 px-3 py-2 space-y-2">
              {steps.map((step, i) => (
                <div key={i} className="flex gap-2">
                  <span className="shrink-0 w-4 text-right font-mono text-muted/30 text-[10px] mt-0.5 tabular-nums">{i + 1}</span>
                  <div className="border-l-2 border-info/30 pl-2 min-w-0">
                    <div className="font-semibold text-muted">{step.title}</div>
                    {step.reasoning && <div className="mt-0.5 text-muted/60 leading-relaxed">{step.reasoning}</div>}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ---------------------------------------------------------------------------
// FollowupSuggestions — clickable suggestion pills rendered after a response
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// RouteSuggestion — card rendered when Concierge emits a ```route block
// ---------------------------------------------------------------------------
interface RouteDirective {
  route_to: string
  mode: 'agent' | 'team' | 'workflow'
  name: string
  reason: string
  starter_prompt?: string
}

const RouteSuggestion = ({ directive, onRoute }: { directive: RouteDirective; onRoute: (d: RouteDirective) => void }) => {
  const ModeIcon = directive.mode === 'workflow' ? GitBranch : directive.mode === 'team' ? Users : Bot
  const modeColor = directive.mode === 'workflow' ? 'text-positive border-positive/30 bg-positive/5'
    : directive.mode === 'team' ? 'text-info border-info/30 bg-info/5'
    : 'text-brand border-brand/30 bg-brand/5'
  const buttonColor = directive.mode === 'workflow' ? 'bg-positive/10 text-positive hover:bg-positive/20 border-positive/30'
    : directive.mode === 'team' ? 'bg-info/10 text-info hover:bg-info/20 border-info/30'
    : 'bg-brand/10 text-brand hover:bg-brand/20 border-brand/30'
  return (
    <motion.div
      className={`my-2 max-w-2xl rounded-xl border p-4 ${modeColor}`}
      initial={{ opacity: 0, y: 8, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.22, ease: 'easeOut' }}
    >
      <div className="flex items-start gap-3">
        <div className={`flex size-8 shrink-0 items-center justify-center rounded-lg border ${modeColor}`}>
          <ModeIcon className="size-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-semibold text-primary">{directive.name}</span>
            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase ${modeColor}`}>
              {directive.mode}
            </span>
          </div>
          <p className="text-xs text-muted/80 leading-relaxed mb-3">{directive.reason}</p>
          {directive.starter_prompt && (
            <div className="mb-3 rounded-lg border border-accent bg-background/60 px-3 py-2">
              <p className="text-[10px] font-medium uppercase text-muted/60 mb-1">Starter prompt</p>
              <p className="text-xs text-muted/80 leading-relaxed font-mono whitespace-pre-wrap">{directive.starter_prompt}</p>
            </div>
          )}
          <button
            onClick={() => onRoute(directive)}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${buttonColor}`}
          >
            <ModeIcon className="size-3" />
            Switch to {directive.name}
            <ChevronRight className="size-3" />
          </button>
        </div>
      </div>
    </motion.div>
  )
}

const FollowupSuggestions = ({ suggestions, onSelect }: { suggestions: string[]; onSelect: (s: string) => void }) => (
  <motion.div
    className="flex flex-wrap gap-1.5 pt-2"
    initial={{ opacity: 0, y: 6 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.2, ease: 'easeOut' }}
  >
    {suggestions.map((s, i) => (
      <button
        key={i}
        onClick={() => onSelect(s)}
        className="inline-flex items-center gap-1 rounded-full border border-accent bg-accent/60 px-3 py-1 text-xs text-muted hover:border-brand/50 hover:bg-brand/10 hover:text-primary transition-colors"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="size-3 shrink-0 opacity-60"><path d="M8 1a.75.75 0 0 1 .75.75v5.5h5.5a.75.75 0 0 1 0 1.5h-5.5v5.5a.75.75 0 0 1-1.5 0v-5.5H1.75a.75.75 0 0 1 0-1.5h5.5v-5.5A.75.75 0 0 1 8 1Z" /></svg>
        {s}
      </button>
    ))}
  </motion.div>
)

// ---------------------------------------------------------------------------
// ApprovalBlock — inline HITL approval widget shown when run is paused
// ---------------------------------------------------------------------------
const ApprovalBlock = ({ runId }: { runId: string | null }) => {
  const { selectedEndpoint, authToken } = useStore()
  const [approvals, setApprovals] = useState<{ id: string; tool_name?: string | null; approval_type?: string | null; requirements?: { name?: string; description?: string }[] | null; tool_args?: Record<string, unknown> | null }[]>([])
  const [resolving, setResolving] = useState<string | null>(null)

  useEffect(() => {
    if (!runId || !selectedEndpoint) return
    const url = `${selectedEndpoint}/approvals?run_id=${runId}&status=pending&limit=10`
    const headers: HeadersInit = authToken ? { Authorization: `Bearer ${authToken}` } : {}
    fetch(url, { headers })
      .then((r) => r.json())
      .then((d) => {
        const list = Array.isArray(d) ? d : d?.approvals ?? d?.data ?? []
        setApprovals(list.filter((a: { status: string }) => a.status === 'pending'))
      })
      .catch(() => {})
  }, [runId, selectedEndpoint, authToken])

  if (!approvals.length) return null

  const resolve = async (id: string, approved: boolean) => {
    if (!selectedEndpoint) return
    setResolving(id)
    const headers: HeadersInit = { 'Content-Type': 'application/json', ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}) }
    try {
      await fetch(`${selectedEndpoint}/approvals/${id}/resolve`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ approved }),
      })
      setApprovals((prev) => prev.filter((a) => a.id !== id))
    } finally {
      setResolving(null)
    }
  }

  return (
    <div className="space-y-2">
      {approvals.map((a) => (
        <div key={a.id} className="rounded-xl border border-warning/40 bg-primaryAccent p-3 shadow-sm shadow-warning/10">
          <div className="flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-primary">
                {a.tool_name
                  ? <code className="font-mono text-xs bg-accent px-1.5 py-0.5 rounded">{a.tool_name}</code>
                  : <span>{a.approval_type ?? 'Human Review Required'}</span>}
              </div>
              {a.requirements && a.requirements.length > 0 && (
                <div className="mt-1 space-y-0.5">
                  {a.requirements.map((r, i) => (
                    <div key={i} className="text-xs text-muted/70">{r.name}{r.description ? ` — ${r.description}` : ''}</div>
                  ))}
                </div>
              )}
              {a.tool_args && Object.keys(a.tool_args).length > 0 && (
                <pre className="mt-1 text-xs text-muted/50 truncate max-w-xs">{JSON.stringify(a.tool_args).slice(0, 80)}…</pre>
              )}
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <Button size="sm" disabled={resolving === a.id}
                className="h-7 gap-1 bg-positive text-background hover:bg-positive/90 text-xs px-2.5"
                onClick={() => resolve(a.id, true)}>
                ✓ Approve
              </Button>
              <Button size="sm" variant="outline" disabled={resolving === a.id}
                className="h-7 gap-1 border-destructive/40 text-destructive hover:bg-destructive/10 text-xs px-2.5"
                onClick={() => resolve(a.id, false)}>
                ✕ Reject
              </Button>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// ThinkingBubble — animated dots + current Agno streaming event label
// Shown while the agent is working but hasn't produced any content yet
// ---------------------------------------------------------------------------
const ThinkingBubble = ({ latestEvent }: { latestEvent: import('@/store').ChatEvent | null }) => {
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(t)
  }, [])

  const label =
    latestEvent?.type === 'tool_start' ? latestEvent.label
    : latestEvent?.type === 'reasoning' ? latestEvent.label
    : latestEvent?.type === 'memory' ? latestEvent.label
    : latestEvent?.type === 'run_start' ? `Waiting for model response… (${elapsed}s)`
    : `Thinking… (${elapsed}s)`

  return (
    <div className="flex items-center gap-3 max-w-2xl rounded-xl bg-primaryAccent px-4 py-3">
      <div className="flex items-center gap-1 shrink-0">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="size-1.5 rounded-full bg-muted"
            animate={{ opacity: [0.25, 1, 0.25], y: [0, -3, 0] }}
            transition={{ duration: 1.0, repeat: Infinity, delay: i * 0.18, ease: 'easeInOut' }}
          />
        ))}
      </div>
      <span className="text-xs text-muted/70 truncate">{label}</span>
    </div>
  )
}

const MessageItem = ({ msg, index, isActiveStreaming = false, latestEvent = null, onFollowupClick, onRoute }: {
  msg: ChatMessage; index: number; isActiveStreaming?: boolean; latestEvent?: import('@/store').ChatEvent | null; onFollowupClick?: (s: string) => void; onRoute?: (d: RouteDirective) => void
}) => {
  const isUser = msg.role === 'user'
  return (
    <motion.div
      className={cn('flex flex-col gap-1', isUser ? 'items-end' : 'items-start')}
      initial={{ opacity: 0, y: 16, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.25, ease: 'easeOut', delay: Math.min(index * 0.04, 0.3) }}
    >
      <div className="flex items-center gap-2">
        <Icon type={isUser ? 'user' : 'agent'} size="xs" />
        <span className="text-xs font-medium uppercase text-muted">{isUser ? 'You' : 'Agent'}</span>
        <span className="text-xs text-muted/50">{fmtMsgTime(msg.created_at)}</span>
        {!isUser && isActiveStreaming && (
          <span className="flex items-center gap-1 rounded-full bg-positive/10 px-1.5 py-0.5 text-[10px] text-positive">
            <span className="size-1 rounded-full bg-positive animate-pulse inline-block" />
            Live
          </span>
        )}
      </div>
      {msg.extra_data?.reasoning_steps && <ReasoningBlock steps={msg.extra_data.reasoning_steps} />}
      {msg.tool_calls && msg.tool_calls.length > 0 && (
        <InlineToolSteps toolCalls={msg.tool_calls} />
      )}
      {msg.content && (
        <div className={cn('max-w-2xl rounded-xl px-4 py-3',
          isUser ? 'bg-accent text-primary text-sm'
            : msg.streamingError ? 'border border-destructive/30 bg-background text-destructive text-sm'
              : 'bg-primaryAccent text-primary'
        )}>
          {isUser ? (
            <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeRaw]}
              components={{
                p: ({ children }) => (
                  <p className="text-[0.875rem] font-normal leading-[21px] tracking-[-0.02em] whitespace-pre-wrap mb-3 last:mb-0">{children}</p>
                ),
                h1: ({ children }) => (
                  <h1 className="text-[1.5rem] font-semibold leading-tight tracking-[-0.02em] mb-3 mt-4 first:mt-0">{children}</h1>
                ),
                h2: ({ children }) => (
                  <h2 className="text-[1.25rem] font-semibold leading-tight tracking-[-0.02em] mb-2 mt-4 first:mt-0">{children}</h2>
                ),
                h3: ({ children }) => (
                  <h3 className="text-[1.1rem] font-semibold leading-tight tracking-[-0.02em] mb-2 mt-3 first:mt-0">{children}</h3>
                ),
                h4: ({ children }) => (
                  <h4 className="text-[1rem] font-semibold leading-tight tracking-[-0.02em] mb-2 mt-3 first:mt-0">{children}</h4>
                ),
                ul: ({ children }) => (
                  <ul className="list-disc flex flex-col gap-y-1.5 pl-5 mb-3 text-[0.875rem]">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal flex flex-col gap-y-1.5 pl-5 mb-3 text-[0.875rem]">{children}</ol>
                ),
                li: ({ children }) => (
                  <li className="leading-[21px] tracking-[-0.02em]">{children}</li>
                ),
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                code: ({ inline, children, className }: any) => {
                  // Inline detection: use the `inline` prop when available (react-markdown <9),
                  // but also fall back to checking className — fenced code blocks always have
                  // a `language-*` class; bare backtick inline code never does.
                  const isBlock = Boolean(className?.startsWith('language-'))
                  if (inline || !isBlock) {
                    return (
                      <code className="rounded bg-accent px-1.5 py-0.5 font-dmmono text-[0.8rem] text-primary/90">{children}</code>
                    )
                  }
                  const lang = className?.replace('language-', '') || ''
                  if (lang === 'route') {
                    try {
                      const directive = JSON.parse(String(children).trim()) as RouteDirective
                      if (directive.route_to && directive.mode && onRoute) {
                        return <RouteSuggestion directive={directive} onRoute={onRoute} />
                      }
                    } catch { /* fall through to CodeBlock */ }
                  }
                  if (lang === 'mermaid') {
                    return <MermaidBlock code={String(children).trim()} />
                  }
                  // Single-line no-lang blocks (e.g. ```\nSIMPLE_ID\n```) → render as
                  // enhanced inline rather than a full dark code box
                  const text = String(children).trim()
                  if (!lang && !text.includes('\n')) {
                    return (
                      <code className="rounded bg-accent px-1.5 py-0.5 font-dmmono text-[0.8rem] text-primary/90">{text}</code>
                    )
                  }
                  return <CodeBlock lang={lang} key={text.slice(0, 20)}>{text}</CodeBlock>
                },
                pre: ({ children }) => <>{children}</>,
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-border pl-4 italic text-muted mb-3 [&>p]:whitespace-normal">{children}</blockquote>
                ),
                strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                em: ({ children }) => <em className="italic">{children}</em>,
                hr: () => <hr className="my-4 h-px w-full border-0 bg-border" />,
                a: ({ href, children }) => (
                  <a href={href} target="_blank" rel="noopener noreferrer" className="text-brand underline underline-offset-2 hover:opacity-80">{children}</a>
                ),
                table: ({ children }) => (
                  <div className="w-full overflow-hidden rounded-md border border-border mb-3">
                    <div className="w-full overflow-x-auto">
                      <table className="w-full text-[0.8rem]">{children}</table>
                    </div>
                  </div>
                ),
                thead: ({ children }) => <thead className="border-b border-border bg-accent/60">{children}</thead>,
                tbody: ({ children }) => <tbody>{children}</tbody>,
                tr: ({ children }) => <tr className="border-b border-border last:border-b-0">{children}</tr>,
                th: ({ children }) => <th className="p-2 text-left text-xs font-semibold">{children}</th>,
                td: ({ children }) => <td className="whitespace-nowrap p-2 text-xs font-normal">{children}</td>,
              }}
            >
              {msg.content}
            </ReactMarkdown>
          )}
        </div>
      )}
      {!msg.content && !isUser && isActiveStreaming && (
        <ThinkingBubble latestEvent={latestEvent} />
      )}
      {!isUser && !isActiveStreaming && msg.followups && msg.followups.length > 0 && onFollowupClick && (
        <FollowupSuggestions suggestions={msg.followups} onSelect={onFollowupClick} />
      )}
    </motion.div>
  )
}

// ---------------------------------------------------------------------------
// Session sidebar items
// ---------------------------------------------------------------------------

const fmtSessionDate = (ts: string | number | undefined | null): string => {
  if (!ts) return '—'
  const d = typeof ts === 'number' ? dayjs.unix(ts) : dayjs(ts)
  return d.isValid() ? d.format('MMM D, HH:mm') : '—'
}

// ---------------------------------------------------------------------------
// Friendly session name — deterministic word-pair from session_id
// ---------------------------------------------------------------------------
const SESS_ADJ = ['Amber','Azure','Bold','Calm','Crisp','Deep','Dusty','Elder','Fern','Gold','Jade','Keen','Lime','Navy','Oak','Pine','Rose','Sage','Slate','Swift','Teal','Warm']
const SESS_NOUN = ['Arc','Atlas','Breeze','Cipher','Dawn','Echo','Forge','Grove','Hawk','Iris','Leaf','Mesa','Nova','Orbit','Peak','Reef','Spark','Tide','Vault','Wave','Zenith']
function friendlySessionName(id: string): string {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (Math.imul(h, 31) + id.charCodeAt(i)) | 0
  const pos = Math.abs(h)
  return `${SESS_ADJ[pos % SESS_ADJ.length]} ${SESS_NOUN[Math.floor(pos / SESS_ADJ.length) % SESS_NOUN.length]}`
}

const SessionItem = ({ session, isSelected, onClick }: {
  session: { session_id: string; session_name?: string; created_at: string | number }
  isSelected: boolean
  onClick: () => void
}) => {
  const displayName = session.session_name
    ? session.session_name.length > 40
      ? session.session_name.slice(0, 40).trimEnd() + '…'
      : session.session_name
    : friendlySessionName(session.session_id)
  return (
  <button
    onClick={onClick}
    className={cn(
      'w-full truncate rounded-xl px-3 py-2 text-left text-xs transition-colors',
      isSelected ? 'bg-accent text-primary' : 'text-muted hover:bg-accent/50 hover:text-primary'
    )}
  >
    <div className="font-medium leading-snug" title={session.session_name}>{displayName}</div>
    <div className="mt-0.5 text-muted/50">{fmtSessionDate(session.created_at)}</div>
  </button>
  )
}

// ---------------------------------------------------------------------------
// Mode & Entity selectors
// ---------------------------------------------------------------------------

const MODES = ['agent', 'team', 'workflow'] as const

const ModeSelector = () => {
  const { mode, setMode, setMessages } = useStore()
  const [, setAgentId] = useQueryState('agent')
  const [, setTeamId] = useQueryState('team')
  const [, setWorkflowId] = useQueryState('workflow')
  const [, setSessionId] = useQueryState('session')
  const activeIndex = MODES.indexOf(mode)

  const handleModeChange = (newMode: 'agent' | 'team' | 'workflow') => {
    setMode(newMode); setMessages([]); setAgentId(null); setTeamId(null); setWorkflowId(null); setSessionId(null)
  }
  return (
    <div className="relative flex h-9 items-center rounded-xl border border-primary/15 bg-accent overflow-hidden min-w-[11rem] shrink-0">
      {/* Sliding pill — width = exact 1/3, left anchored at 0, overflow-hidden clips spring overshoot */}
      <motion.div
        className="absolute inset-y-0.5 left-0 rounded-lg bg-primary"
        style={{ width: `calc(100% / ${MODES.length})` }}
        animate={{ x: `${activeIndex * 100}%` }}
        initial={false}
        transition={{ type: 'spring', stiffness: 400, damping: 35, mass: 0.8 }}
      />
      {MODES.map((m) => (
        <button
          key={m}
          onClick={() => handleModeChange(m)}
          className={cn(
            'relative z-10 w-1/3 py-1 text-xs font-medium uppercase text-center transition-colors duration-150',
            mode === m ? 'text-primaryAccent' : 'text-muted hover:text-primary'
          )}
        >{m === 'workflow' ? 'flow' : m}</button>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Searchable entity combobox
// ---------------------------------------------------------------------------
const EntitySelector = () => {
  const { mode, agents, teams, workflows, setMessages, setSelectedModel } = useStore()
  const [agentId, setAgentId] = useQueryState('agent')
  const [teamId, setTeamId] = useQueryState('team')
  const [workflowId, setWorkflowId] = useQueryState('workflow')
  const [, setSessionId] = useQueryState('session')
  const [, setDbId] = useQueryState('db_id')
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const entities = mode === 'team' ? teams : mode === 'workflow' ? workflows : agents
  const currentValue = mode === 'team' ? teamId : mode === 'workflow' ? workflowId : agentId
  const currentName = entities.find((e) => (e as { id: string }).id === currentValue)
  const displayName = (currentName as { name?: string; id: string } | undefined)?.name || currentValue || `Select ${mode === 'workflow' ? 'flow' : mode}`

  const filtered = entities.filter((e) => {
    const name = ((e as { name?: string; id: string }).name || (e as { id: string }).id).toLowerCase()
    return name.includes(query.toLowerCase())
  })

  const handleSelect = (value: string) => {
    if (mode === 'workflow') {
      const wf = workflows.find((w) => w.id === value)
      setDbId(wf?.db_id || null)
      setWorkflowId(value); setAgentId(null); setTeamId(null)
    } else {
      const entity = entities.find((e) => (e as { id: string }).id === value)
      const det = entity as { model?: { model?: string; provider?: string }; db_id?: string } | undefined
      setSelectedModel(det?.model?.model || det?.model?.provider || '')
      setDbId(det?.db_id || null)
      setMessages([]); setSessionId(null)
      if (mode === 'team') { setTeamId(value); setAgentId(null); setWorkflowId(null) }
      else { setAgentId(value); setTeamId(null); setWorkflowId(null) }
    }
    setOpen(false); setQuery('')
  }

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false); setQuery('')
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Focus input when opened
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50)
  }, [open])

  return (
    <div ref={containerRef} className="relative w-44 shrink-0">
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        disabled={entities.length === 0}
        className={cn(
          'flex w-full items-center justify-between gap-1 rounded-xl border border-accent bg-primaryAccent px-3 py-2 text-xs font-medium uppercase shadow-sm transition-colors',
          'hover:border-primary/30 focus:outline-none focus:ring-1 focus:ring-ring',
          'disabled:cursor-not-allowed disabled:opacity-50',
          open && 'border-primary/40'
        )}
      >
        <span className="truncate text-left">{entities.length === 0 ? `No ${mode}s` : displayName}</span>
        <ChevronDown className={cn('size-3.5 shrink-0 text-muted transition-transform duration-150', open && 'rotate-180')} />
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-64 rounded-xl border border-accent bg-background shadow-xl overflow-hidden">
          {/* Search input */}
          <div className="flex items-center gap-2 border-b border-accent px-3 py-2">
            <Search className="size-3.5 shrink-0 text-muted" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') { setOpen(false); setQuery('') }
                if (e.key === 'Enter' && filtered.length === 1) handleSelect((filtered[0] as { id: string }).id)
              }}
              placeholder={`Search ${mode}s…`}
              className="flex-1 bg-transparent text-xs outline-none placeholder:text-muted/50 text-primary"
            />
            {query && (
              <button onClick={() => setQuery('')} className="text-muted hover:text-primary">
                <XIcon className="size-3" />
              </button>
            )}
          </div>
          {/* List */}
          <div className="max-h-52 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <p className="px-3 py-4 text-center text-xs text-muted/50">No results</p>
            ) : filtered.map((entity) => {
              const id = (entity as { id: string }).id
              const name = (entity as { name?: string; id: string }).name || id
              const isSelected = id === currentValue
              const EntityIcon = mode === 'workflow' ? GitBranch : mode === 'team' ? Users : Bot
              const iconColor = mode === 'workflow' ? 'text-positive' : mode === 'team' ? 'text-info' : 'text-brand'
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => handleSelect(id)}
                  className={cn(
                    'flex w-full items-center gap-2.5 px-3 py-2 text-left text-xs transition-colors hover:bg-accent/50',
                    isSelected && 'bg-accent/30'
                  )}
                >
                  <EntityIcon className={cn('size-3.5 shrink-0', iconColor)} />
                  <span className={cn('flex-1 truncate uppercase font-medium', isSelected ? 'text-primary' : 'text-muted/80')}>{name}</span>
                  {isSelected && <Check className="size-3 shrink-0 text-primary" />}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Right panel — Agent config + SSE event log
// ---------------------------------------------------------------------------

const EventTypeIcon = ({ type }: { type: string }) => {
  switch (type) {
    case 'tool_start':  return <Wrench className="size-3 text-info" />
    case 'tool_done':   return <CheckCircle className="size-3 text-positive" />
    case 'reasoning':   return <Brain className="size-3 text-warning" />
    case 'run_start':   return <Zap className="size-3 text-brand" />
    case 'run_done':    return <CheckCircle className="size-3 text-positive" />
    case 'error':       return <XCircle className="size-3 text-destructive" />
    case 'memory':      return <Database className="size-3 text-muted" />
    default:            return <Hash className="size-3 text-muted" />
  }
}

// ---------------------------------------------------------------------------
// Inline Activity Log (toggled in toolbar)
// ---------------------------------------------------------------------------

const EVENT_COLOR: Record<string, string> = {
  run_start: 'text-brand',
  run_done: 'text-positive',
  tool_start: 'text-warning',
  tool_done: 'text-positive',
  reasoning: 'text-info',
  error: 'text-destructive',
  memory: 'text-muted',
  content: 'text-primary',
}

const ActivityLog = ({ events, isStreaming }: { events: import('@/store').ChatEvent[]; isStreaming: boolean }) => {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  return (
    <div className="border-t border-accent/50 bg-primaryAccent shrink-0">
      <div className="flex items-center justify-between px-4 py-1.5 border-b border-accent/30">
        <div className="flex items-center gap-1.5">
          <Activity className="size-3 text-brand" />
          <span className="text-xs font-medium uppercase text-muted">Activity Stream</span>
        </div>
        {isStreaming ? (
          <span className="flex items-center gap-1 text-xs text-positive">
            <span className="size-1.5 rounded-full bg-positive animate-pulse inline-block" />
            Live
          </span>
        ) : events.length > 0 ? (
          <span className="text-xs text-muted/40">{events.length} events</span>
        ) : null}
      </div>
      <div className="h-36 overflow-y-auto px-4 py-2 space-y-px font-mono text-xs">
        {events.length === 0 ? (
          <span className="text-muted/30">No events yet — start a run to see activity here.</span>
        ) : (
          events.map((e, i) => (
            <div key={i} className="flex items-baseline gap-2 leading-5">
              <span className="text-muted/40 shrink-0 tabular-nums">
                {dayjs(e.ts).format('HH:mm:ss.SSS')}
              </span>
              <span className={cn('shrink-0 font-medium', EVENT_COLOR[e.type] ?? 'text-primary')}>
                {e.label}
              </span>
              {e.detail && (
                <span className="text-muted/50 truncate min-w-0">{e.detail}</span>
              )}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Right panel helpers
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Model Switcher — provider + model quick picker in the toolbar
// ---------------------------------------------------------------------------

interface ProviderModel { id: string; label: string }
interface ProviderInfo {
  name: string; description: string; base_url: string
  models: ProviderModel[]; default_model: string; requires_key: boolean; key_env: string | null
}
interface ProvidersResponse {
  providers: Record<string, ProviderInfo>
  active_provider: string
  active_model: string
}

const ModelSwitcher = () => {
  const { selectedEndpoint, authToken, activeProvider, setActiveProvider, activeModelId, setActiveModelId } = useStore()
  const [open, setOpen] = useState(false)
  const [providers, setProviders] = useState<ProvidersResponse | null>(null)
  const [switching, setSwitching] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const endpointUrl = constructEndpointUrl(selectedEndpoint)

  useEffect(() => {
    fetchProviders()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const fetchProviders = async () => {
    try {
      const res = await fetch(`${endpointUrl}/model/providers`, {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      })
      if (res.ok) {
        const data: ProvidersResponse = await res.json()
        setProviders(data)
        // Sync store with backend active state
        if (data.active_provider) setActiveProvider(data.active_provider)
        if (data.active_model) setActiveModelId(data.active_model)
      }
    } catch { /* backend may not have model endpoint yet */ }
  }

  const handleSwitch = async (providerId: string, modelId: string) => {
    setSwitching(true)
    try {
      const res = await fetch(`${endpointUrl}/model/switch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({ provider: providerId, model_id: modelId }),
      })
      if (res.ok) {
        const data = await res.json()
        setActiveProvider(providerId)
        setActiveModelId(modelId)
        setOpen(false)
        toast.success(data.message ?? `Switched to ${modelId}`)
      } else {
        toast.error('Failed to switch model')
      }
    } catch { toast.error('Backend unreachable') }
    setSwitching(false)
  }

  const currentProvider = activeProvider || providers?.active_provider || 'kilo'
  const currentModel = activeModelId || providers?.active_model || 'kilo-auto/free'
  const providerName = providers?.providers?.[currentProvider]?.name ?? currentProvider
  const displayModel = currentModel.split('/').pop() ?? currentModel

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => { setOpen((o) => !o); if (!providers) fetchProviders() }}
        className="flex items-center gap-1.5 rounded-lg border border-accent px-2 py-1 text-xs text-muted hover:bg-accent hover:text-primary transition-colors"
        title="Switch model / provider"
      >
        <Cpu className="size-3 shrink-0" />
        <span className="font-medium">{providerName}</span>
        <span className="text-muted/40">/</span>
        <span className="font-mono max-w-[100px] truncate">{displayModel}</span>
        <ChevronDown className={cn('size-3 transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-72 rounded-xl border border-accent bg-background shadow-xl overflow-hidden">
          <div className="border-b border-accent/50 px-3 py-2">
            <span className="text-xs font-semibold uppercase text-muted">Switch Model</span>
          </div>
          {!providers ? (
            <div className="p-4 text-center text-xs text-muted/50">Loading providers…</div>
          ) : (
            <div className="max-h-72 overflow-y-auto p-2 space-y-2">
              {Object.entries(providers.providers).map(([pid, pInfo]) => (
                <div key={pid}>
                  <div className="px-2 pb-0.5 pt-1 text-[10px] font-semibold uppercase tracking-wide text-muted/50">{pInfo.name}</div>
                  {pInfo.models.map((m) => {
                    const isActive = currentProvider === pid && currentModel === m.id
                    return (
                      <button
                        key={m.id}
                        onClick={() => handleSwitch(pid, m.id)}
                        disabled={switching || isActive}
                        className={cn(
                          'flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-xs transition-colors',
                          isActive
                            ? 'bg-brand/10 text-brand cursor-default'
                            : 'text-muted hover:bg-accent hover:text-primary'
                        )}
                      >
                        <span className="font-mono">{m.label}</span>
                        {isActive && <CheckCircle className="size-3 text-positive shrink-0" />}
                      </button>
                    )
                  })}
                </div>
              ))}
            </div>
          )}
          <div className="border-t border-accent/50 px-3 py-2">
            <a href="/settings#model" className="text-[10px] text-muted/50 hover:text-muted">
              Advanced config → Settings
            </a>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------

const Section = ({ icon, title, children, defaultOpen = true }: { icon: React.ReactNode; title: string; children: React.ReactNode; defaultOpen?: boolean }) => {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        className="mb-1.5 flex w-full items-center gap-1.5 hover:opacity-80 transition-opacity"
      >
        {icon}
        <span className="text-xs font-semibold uppercase tracking-wide text-muted flex-1 text-left">{title}</span>
        <ChevronDown className={cn('size-3 text-muted/40 transition-transform', open && 'rotate-180')} />
      </button>
      {open && children}
    </div>
  )
}

const KV = ({ label, value }: { label: string; value: React.ReactNode }) => (
  <div className="flex flex-col gap-0.5 py-1 border-b border-accent/30 last:border-0">
    <span className="text-xs text-muted/60">{label}:</span>
    <span className="text-xs font-mono text-primary break-all">{value}</span>
  </div>
)

const Card = ({ children }: { children: React.ReactNode }) => (
  <div className="rounded-xl border border-accent bg-background p-3 space-y-0.5 text-xs">{children}</div>
)

// ---------------------------------------------------------------------------
// Agent metadata (descriptions for Details panel)
// ---------------------------------------------------------------------------
const AGENT_META: Record<string, { skill: string; description: string; jiraAccess: string; squad: string }> = {
  'architect': {
    skill: 'semantic_search',
    description: 'Parses Jira tickets, ADO work items, or plain-text requirements into a structured RequirementContext (Execution Plan). Queries the codebase KB to determine which Page Objects are affected and whether this is a new feature or existing coverage.',
    jiraAccess: 'Read — jira_get_issue, jira_search, confluence_search, confluence_get_page',
    squad: 'Spec Writing Squad',
  },
  'scribe': {
    skill: 'gherkin_formatter',
    description: 'Translates the Architect\'s RequirementContext into strictly formatted BDD Gherkin specs with full AC traceability. Ensures steps are BA-readable and reusable across feature files. Validates all acceptance criteria are covered.',
    jiraAccess: 'Read — jira_get_issue (AC cross-check), confluence_search',
    squad: 'Spec Writing Squad',
  },
  'discovery': {
    skill: 'ui_crawler',
    description: 'Launches a browser, authenticates with the AUT, and crawls every registered route. Extracts the Accessibility Tree snapshot per page — recording data-testid, role, and text locators for every interactable element — then persists the Site Manifesto to PgVector.',
    jiraAccess: 'None',
    squad: 'Discovery & Indexing Squad',
  },
  'librarian': {
    skill: 'vector_indexing',
    description: 'Watches the automation/ directory and re-indexes Page Objects, Step Definitions, and utilities into the PgVector codebase KB on every Git commit. Also detects obsolete scenarios, unused steps, and orphaned Page Objects.',
    jiraAccess: 'None',
    squad: 'Discovery & Indexing Squad',
  },
  'engineer': {
    skill: 'file_writer',
    description: 'Authors modular Playwright POMs and Cucumber Step Definitions following the Look-Before-You-Leap pattern: checks Site Manifesto → queries codebase KB → verifies selectors via MCP → writes code → submits GitHub PR. No hardcoded sleeps, no CSS/XPath locators.',
    jiraAccess: 'None',
    squad: 'Code Generation Squad',
  },
  'data-agent': {
    skill: 'data_factory',
    description: 'Provisions fresh test users, seeds database records, and sets up API mocks before each test run. Applies PII masking, validates unique constraints, and produces a RunContext with cleanup queries for safe teardown.',
    jiraAccess: 'None',
    squad: 'Code Generation Squad',
  },
  'detective': {
    skill: 'trace_analyzer',
    description: 'Pulls Playwright trace.zip from CI failures and classifies the root cause: LOCATOR_STALE (broken selector), DATA_MISMATCH, TIMING_FLAKE, ENV_FAILURE, or LOGIC_CHANGE (real app bug requiring human review). Confidence > 90% auto-routes to Medic.',
    jiraAccess: 'None',
    squad: 'Self-Healing Squad',
  },
  'medic': {
    skill: 'surgical_editor',
    description: 'Applies surgical one-locator patches to Page Objects when the Detective classifies a failure as LOCATOR_STALE. Strictly forbidden from changing business logic, assertions, or test flow. Every patch must pass 3 consecutive verification runs.',
    jiraAccess: 'None',
    squad: 'Self-Healing Squad',
  },
  'judge': {
    skill: 'adversarial_review',
    description: 'Quality gate that runs the Definition of Done checklist against every artifact — Gherkin specs, automation code, test data, and healing patches. Confidence ≥ 90% → auto-approve. Confidence < 90% → triggers HITL approval queue. Never bypassed.',
    jiraAccess: 'None',
    squad: 'Cross-cutting (Quality Gate)',
  },
  'ci_log_analyzer': {
    skill: 'rca_analysis',
    description: 'Analyses Azure DevOps CI pipeline logs end-to-end: fetches pipeline run logs via ADO MCP, performs historical RCA using the RCA knowledge base, deduplicates against existing Jira bugs, and creates a new Jira bug (or ADO work item) after HITL approval in the Approvals queue.',
    jiraAccess: 'Write — jira_search, jira_get_issue, jira_create_issue, jira_add_comment, jira_transition_issue',
    squad: 'CI Failure Squad',
  },
  'healing_judge': {
    skill: 'healing_validation',
    description: 'Adversarial reviewer specifically for Medic healing patches. Verifies the diff is truly surgical (one locator line changed), that no business logic was touched, and that the test passed 3 consecutive times post-patch before approving the PR.',
    jiraAccess: 'None',
    squad: 'Self-Healing Squad',
  },
  'technical_tester': {
    skill: 'test_generation',
    description: 'Rapid exploratory tester using Playwright Test Agents. Does not require a Gherkin spec — autonomously plans a test session, generates Playwright tests, executes them, and heals any failures on the fly. Ideal for smoke tests and new-feature sanity checks.',
    jiraAccess: 'None',
    squad: 'Code Generation Squad',
  },
  'impact-analyst': {
    skill: 'impact_analysis',
    description: 'Analyses GitHub PRs and Issues against the existing automation suite. Identifies missing coverage, obsolete tests, and stale locators. Assigns P0–P3 regression risk and produces a recommended action list for the Engineer and Scribe.',
    jiraAccess: 'Read — jira_get_issue, jira_search, confluence_search',
    squad: 'Impact Analysis Squad',
  },
  'pipeline-analyst': {
    skill: 'pipeline_analysis',
    description: 'Analyses GitHub Actions pipeline logs for trend-level insights — flakiness scoring, failure classification (LOCATOR_CHANGE / ENV_FAILURE / FLAKY_TEST / DATA_ISSUE), and produces a PipelineRCAReport with a prioritised remediation plan.',
    jiraAccess: 'Read — jira_search, jira_get_issue',
    squad: 'Impact Analysis Squad',
  },
  'curator': {
    skill: 'kb_maintenance',
    description: 'Monitors the PgVector knowledge base and automation codebase for drift. Detects obsolete scenarios, unused step definitions, and orphaned Page Objects. Presents deletion recommendations for HITL approval before any KB content is removed.',
    jiraAccess: 'None',
    squad: 'Discovery & Indexing Squad',
  },
}

// ---------------------------------------------------------------------------
// Workflow & Team metadata
// ---------------------------------------------------------------------------
const WORKFLOW_META: Record<string, { description: string; pipeline: string[]; inputFormat: string; placeholder: string; squad: string }> = {
  'spec-to-code': {
    description: 'Converts a Jira ticket or plain requirement into validated Playwright automation code. Architect parses the ticket, Scribe writes the Gherkin spec, Judge validates quality at two checkpoints, Data Agent provisions test data, and Engineer writes the POM + Step Definitions.',
    pipeline: ['Architect → RequirementContext', 'Scribe → GherkinSpec (.feature)', '⚖️ Gherkin Judge Gate (≥90% auto)', 'Data Agent → RunContext', 'Engineer → POM + StepDefs', '⚖️ Code Judge Gate (≥90% auto)', 'Engineer → GitHub PR'],
    inputFormat: 'Jira issue key (e.g. GDS-4) or a plain-text requirement description',
    placeholder: 'GDS-4\n\nor: "Add login page with MFA — must support TOTP and email fallback"',
    squad: 'Code Generation Squad',
  },
  'jira-to-pr': {
    description: 'Full end-to-end pipeline from Jira ticket to GitHub PR. Includes real Judge gates using JudgeVerdict confidence scoring (≥0.90 auto-approve, <0.90 human review).',
    pipeline: ['Architect → RequirementContext', 'Scribe → GherkinSpec', '⚖️ Gherkin Judge (JudgeVerdict)', 'Data Agent → RunContext', 'Engineer → POM + StepDefs', '⚖️ Code Judge (JudgeVerdict)', 'Engineer → GitHub PR'],
    inputFormat: 'Jira issue key',
    placeholder: 'GDS-4\nor: QAP-123',
    squad: 'Code Generation Squad',
  },
  'discovery-onboard': {
    description: 'Crawls an AUT, extracts the Accessibility Tree from every page, identifies interactable elements with data-testid / role / text locators, and stores the Site Manifesto in PgVector so the Engineering squad can use it.',
    pipeline: ['Discovery Agent → crawl AUT (login + navigate ≥3 pages)', 'Accessibility Tree extraction per page', 'SiteManifesto → PgVector KB'],
    inputFormat: 'Full AUT URL including protocol',
    placeholder: 'https://demo.nopcommerce.com/',
    squad: 'Discovery & Indexing Squad',
  },
  'triage-heal': {
    description: 'Analyses a failing Playwright test — parses trace.zip or CI log, classifies the root cause (LOCATOR_STALE, DATA_MISMATCH, TIMING_FLAKE, ENV_FAILURE, LOGIC_CHANGE), and if auto-healable applies a surgical patch verified 3 consecutive times.',
    pipeline: ['Detective → RCAReport (classify failure)', '↳ LOCATOR_STALE: Medic → HealingPatch (×3 verify loop)', '↳ else: Human escalation with RCA summary'],
    inputFormat: 'CI error message, test name, or pasted failure log',
    placeholder: '[FAILED] LoginTest — Element not found: data-testid="login-btn"\n\nor: paste full CI log output',
    squad: 'Self-Healing Squad',
  },
  'automation-scaffold': {
    description: 'Scaffolds a complete BDD+POM Playwright automation framework from scratch — creates directory structure, config files, BasePage class, and example feature/step/POM files.',
    pipeline: ['Engineer → Directory structure', 'cucumber.conf.ts + playwright.config.ts + tsconfig.json', 'BasePage.ts (common methods)', 'example.feature + example.steps.ts + HomePage.ts'],
    inputFormat: 'project_name, base_url, and optional browser/headless settings',
    placeholder: 'project_name=MyApp base_url=https://myapp.com browser=chromium headless=true',
    squad: 'Code Generation Squad',
  },
  'full-lifecycle': {
    description: 'End-to-end STLC pipeline using all 9 agents — from Jira ticket through spec, AUT discovery, code generation, test execution, failure analysis, and healing with a final quality gate.',
    pipeline: ['Architect', 'Scribe', '⚖️ Spec Judge', 'Discovery', 'Librarian', 'Data Agent', 'Engineer (POM)', 'Engineer (StepDefs)', '⚖️ Code Judge', 'Engineer (Execute)', 'Detective', 'Medic', 'Healing Judge', '⚖️ Final Judge', 'Scribe (Report)'],
    inputFormat: 'Jira issue key or plain requirement text',
    placeholder: 'GDS-4\n\nor: "Build full test suite for the checkout flow"',
    squad: 'All Squads',
  },
  'full-regression': {
    description: 'Runs the full regression loop — generates automation from requirements, executes tests, triages failures, applies surgical healing patches, and updates the knowledge base with learnings.',
    pipeline: ['Engineer → Generate automation', 'Engineer → Execute tests', 'Detective → Analyze failures', 'Medic → Healing patch', 'Healing Judge → Validate patch', 'Medic → Verify 3×', 'Librarian → Update KB'],
    inputFormat: 'Feature or module description',
    placeholder: 'Run full regression for the checkout module',
    squad: 'Code Generation Squad + Self-Healing Squad',
  },
  'grooming': {
    description: '3 Amigos user story review — BA (Architect), SDET (Judge), and Dev (Engineer) assess the ticket in parallel, then synthesise a verdict and post it back to Jira.',
    pipeline: ['Parallel: BA Assessment (Architect)', 'Parallel: SDET Assessment (Judge)', 'Parallel: Dev Assessment (Engineer)', 'Synthesize → GroomingAssessment', 'Post verdict comment to Jira'],
    inputFormat: 'Jira issue key',
    placeholder: 'GDS-5',
    squad: 'Spec Writing Squad',
  },
  'impact-assessment': {
    description: 'Analyses a PR or GitHub Issue against the existing test suite. Classifies gaps as missing_coverage, obsolete, or needs_update, assigns P0–P3 priority, and produces a recommended action list for the Engineer and Scribe.',
    pipeline: ['Impact Analyst → fetch PR/Issue diff', 'Query Automation KB + Site Manifesto KB', 'Classify gaps (missing / obsolete / stale)', 'Compute regression risk', 'ImpactReport → recommended actions'],
    inputFormat: 'GitHub PR number or Issue URL',
    placeholder: 'PR #42\nor: https://github.com/org/repo/issues/12',
    squad: 'Impact Analysis Squad',
  },
  'pipeline-failure-assessment': {
    description: 'Analyses a failed GitHub Actions or ADO pipeline run — classifies the root cause and produces a PipelineRCAReport with a prioritised remediation plan.',
    pipeline: ['Pipeline Analyst → fetch pipeline logs', 'Classify failure (LOCATOR_CHANGE / ENV_FAILURE / FLAKY_TEST / DATA_ISSUE)', 'PipelineRCAReport with remediation plan', 'Optional: Create ADO/Jira ticket (HITL approval)'],
    inputFormat: 'Pipeline run URL or pasted CI log',
    placeholder: 'https://github.com/org/repo/actions/runs/12345\nor: paste CI log output',
    squad: 'CI Failure Squad',
  },
  'regression_maintenance': {
    description: 'Scheduled locator health check — scans Page Objects for stale selectors against the live AUT, applies surgical healing for LOCATOR_STALE failures, and updates the knowledge base.',
    pipeline: ['Operations team scan all Page Objects', 'Detective → identify stale locators', 'Medic → auto-heal (LOCATOR_STALE)', 'Librarian → Update KB with learnings'],
    inputFormat: 'AUT URL or component scope (optional — leave blank to scan all)',
    placeholder: 'https://myapp.com/checkout\n\nor: leave blank to scan all registered pages',
    squad: 'Self-Healing Squad',
  },
  'technical-testing': {
    description: 'Rapid exploratory test generation via Playwright — the Technical Tester autonomously plans, generates, executes, and verifies tests for a given feature or page without requiring a pre-existing Gherkin spec.',
    pipeline: ['Technical Tester → Test plan', 'Technical Tester → Generate Playwright tests (no POM required)', 'Technical Tester → Execute + verify', 'Technical Tester → Heal if needed'],
    inputFormat: 'Plain English description of what to test',
    placeholder: 'Test the search functionality on the product listing page\n\nor: Verify that the checkout flow works end-to-end for a guest user',
    squad: 'Code Generation Squad',
  },
}

const TEAM_META: Record<string, { purpose: string; responsibility: string; outputContract: string }> = {
  'strategy': {
    purpose: 'Spec Writing Squad — bridges Business Analysts and the Technical team.',
    responsibility: 'Parse Jira tickets into structured RequirementContext (Architect), then author BDD Gherkin specs with full traceability to every acceptance criterion (Scribe).',
    outputContract: 'RequirementContext → GherkinSpec',
  },
  'context': {
    purpose: 'Discovery & Indexing Squad — maintain the Digital Twin of your AUT and codebase.',
    responsibility: 'Crawl the AUT to generate the Site Manifesto with Accessibility Tree snapshots (Discovery), re-index Page Objects and Step Definitions into PgVector on every Git commit (Librarian).',
    outputContract: 'SiteManifesto + PgVector Automation KB',
  },
  'engineering': {
    purpose: 'Code Generation Squad — generate production-grade Playwright automation code.',
    responsibility: 'Write modular POMs and Step Definitions using the Look-Before-You-Leap pattern (Engineer), provision fresh test data with PII masking and cleanup queries (Data Agent), submit GitHub PRs.',
    outputContract: 'RunContext → POM + StepDefs → GitHub PR',
  },
  'operations': {
    purpose: 'Self-Healing Squad — keep the regression suite green autonomously.',
    responsibility: 'Classify failures from trace.zip as LOCATOR_STALE / LOGIC_CHANGE / DATA_MISMATCH / ENV_FAILURE (Detective), apply surgical one-locator healing patches verified 3× (Medic).',
    outputContract: 'RCAReport → HealingPatch (verified 3×)',
  },
  'diagnostics': {
    purpose: 'CI Failure Squad — correlate pipeline logs with Playwright traces.',
    responsibility: 'Analyse GitHub Actions / ADO pipeline failures with log-level detail (CI Log Analyzer), cross-reference with Playwright trace analysis (Detective), create Jira/ADO tickets after HITL approval.',
    outputContract: 'PipelineRCAReport + RCAReport → ADO ticket (HITL)',
  },
  'grooming_team': {
    purpose: 'Backlog Grooming Squad — collaborative backlog refinement from three perspectives.',
    responsibility: 'BA perspective on testability (Architect), SDET assessment of automation feasibility and edge cases (Impact Analyst), combined into actionable grooming assessment posted to Jira.',
    outputContract: 'GroomingAssessment → Jira comment',
  },
  'intelligence': {
    purpose: 'Impact Analysis Squad — answers "what needs to change?" and "why did this fail?"',
    responsibility: 'Analyse PRs and Issues to identify missing/obsolete/stale tests and compute regression risk (Impact Analyst), analyse CI pipeline failures and produce remediation plans (Pipeline Analyst).',
    outputContract: 'ImpactReport + PipelineRCAReport',
  },
}

const StepTree = ({ steps, depth = 0 }: { steps: WorkflowStep[]; depth?: number }) => (
  <div className={cn('space-y-1', depth > 0 && 'ml-3 border-l border-accent/40 pl-2')}>
    {steps.map((s, i) => (
      <div key={i}>
        <div className="flex items-center gap-1.5 py-0.5">
          {s.type === 'Condition' || s.type === 'Router'
            ? <CornerDownRight className="size-3 shrink-0 text-warning" />
            : <Play className="size-3 shrink-0 text-brand" />}
          <span className="text-xs text-primary">{s.name}</span>
          {(s.type === 'Condition' || s.type === 'Router') && (
            <span className="text-xs text-muted/50 italic">runs if condition evaluates to true</span>
          )}
        </div>
        {s.steps && s.steps.length > 0 && <StepTree steps={s.steps} depth={depth + 1} />}
      </div>
    ))}
  </div>
)

// ---------------------------------------------------------------------------
// Right panel (config + event log)
// ---------------------------------------------------------------------------

const RightPanel = ({ agentId, teamId, workflowId, sessionId, clearChat, setSessionId }: {
  agentId: string | null; teamId: string | null; workflowId: string | null; sessionId: string | null
  clearChat: () => void; setSessionId: (id: string | null) => void
}) => {
  const { mode, chatEvents, isStreaming, selectedEndpoint, authToken, sessionsData, isSessionsLoading } = useStore()
  const [tab, setTab] = useState<'details' | 'config' | 'memory' | 'steps' | 'members'>('details')
  const [agentDetail, setAgentDetail] = useState<AgentFullDetail | null>(null)
  const [teamDetail, setTeamDetail] = useState<TeamFullDetail | null>(null)
  const [workflowDetail, setWorkflowDetail] = useState<WorkflowFullDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [panelView, setPanelView] = useState<'sessions' | 'details'>('sessions')
  const [memories, setMemories] = useState<Array<{id: string; memory?: string; summary?: string; topics?: string[]; agent_id?: string; created_at?: string; updated_at?: string}>>([])  
  const [memoriesLoading, setMemoriesLoading] = useState(false)

  const endpointUrl = constructEndpointUrl(selectedEndpoint)

  // Reset tab to a valid default whenever the entity or mode changes
  useEffect(() => {
    if (mode === 'agent') setTab('details')
    else if (mode === 'team') setTab('members')
    else if (mode === 'workflow') setTab('details')
  }, [mode, agentId, teamId, workflowId])

  useEffect(() => {
    // Clear all stale detail state so header/tabs never show data from a previous mode
    setAgentDetail(null); setTeamDetail(null); setWorkflowDetail(null)
    if (mode === 'agent' && agentId) {
      setLoading(true)
      getAgentDetailAPI(endpointUrl, agentId, authToken).then((d) => { setAgentDetail(d); setLoading(false) })
    } else if (mode === 'team' && teamId) {
      setLoading(true)
      getTeamDetailAPI(endpointUrl, teamId, authToken).then((d) => { setTeamDetail(d); setLoading(false) })
    } else if (mode === 'workflow' && workflowId) {
      setLoading(true)
      getWorkflowDetailAPI(endpointUrl, workflowId, authToken).then((d) => { setWorkflowDetail(d); setLoading(false) })
    } else {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId, teamId, workflowId, mode])

  const currentEntityId = agentId || teamId || null

  useEffect(() => {
    if (tab !== 'memory' || !currentEntityId) return
    setMemoriesLoading(true)
    setMemories([])
    const url = mode === 'agent'
      ? `${endpointUrl}/memories?agent_id=${currentEntityId}`
      : `${endpointUrl}/memories?team_id=${currentEntityId}`
    fetch(url, { headers: authToken ? { Authorization: `Bearer ${authToken}` } : {} })
      .then((r) => r.ok ? r.json() : [])
      .then((data) => { setMemories(Array.isArray(data) ? data : (data.memories ?? [])); setMemoriesLoading(false) })
      .catch(() => setMemoriesLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, currentEntityId, mode])

  const entityLabel = mode === 'team' ? 'Team' : mode === 'workflow' ? 'Workflow' : 'Agent'
  const EntityIcon = mode === 'workflow' ? GitBranch : mode === 'team' ? Users : Bot
  const modeColor = mode === 'workflow' ? 'text-positive' : mode === 'team' ? 'text-info' : 'text-brand'
  const modeBadgeBg = mode === 'workflow' ? 'bg-positive/10 text-positive border-positive/20'
    : mode === 'team' ? 'bg-info/10 text-info border-info/20'
    : 'bg-brand/10 text-brand border-brand/20'
  // Mode-aware name — never bleed stale data from a previous mode
  const currentEntityName =
    mode === 'agent'    ? (agentDetail?.name    ?? agentId    ?? 'Agent')
    : mode === 'team'   ? (teamDetail?.name     ?? teamId     ?? 'Team')
    :                     (workflowDetail?.name ?? workflowId ?? 'Workflow')

  // Tab definitions per mode
  const agentTabs  = [
    { key: 'details',  label: 'Details' },
    { key: 'config',   label: 'Config' },
    { key: 'memory',   label: 'Memory' },
  ] as const
  const teamTabs = [
    { key: 'members',  label: 'Members' },
    { key: 'config',   label: 'Config' },
    { key: 'memory',   label: 'Memory' },
  ] as const
  const workflowTabs = [
    { key: 'details',  label: 'Overview' },
    { key: 'steps',    label: 'Steps' },
  ] as const

  const activeTabs = mode === 'workflow' ? workflowTabs : mode === 'team' ? teamTabs : agentTabs
  const hasEntity = Boolean(agentId || teamId || workflowId)

  const sessionCount = sessionsData?.length ?? 0

  return (
    <div className="flex h-full flex-col gap-0 overflow-hidden">

      {/* ── Panel view toggle: Sessions | Details ── */}
      <div className="flex shrink-0 items-center gap-0 border-b border-accent/50 px-2 pt-2 pb-0">
        <button
          onClick={() => setPanelView('sessions')}
          className={cn(
            'flex flex-1 items-center justify-center gap-1.5 rounded-t-lg border-b-2 px-3 py-2 text-xs font-medium uppercase transition-colors',
            panelView === 'sessions'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted hover:text-primary'
          )}
        >
          <MessageSquare className="size-3.5 shrink-0" />
          Sessions
          {sessionCount > 0 && (
            <span className="rounded-full bg-accent px-1.5 py-0 text-[9px] font-semibold tabular-nums">{sessionCount}</span>
          )}
        </button>
        <button
          onClick={() => setPanelView('details')}
          className={cn(
            'flex flex-1 items-center justify-center gap-1.5 rounded-t-lg border-b-2 px-3 py-2 text-xs font-medium uppercase transition-colors',
            panelView === 'details'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted hover:text-primary'
          )}
        >
          <EntityIcon className="size-3.5 shrink-0" />
          {entityLabel}
        </button>
      </div>

      {/* ═══ SESSIONS VIEW ═══ */}
      {panelView === 'sessions' && (
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Header with new session button */}
          <div className="flex shrink-0 items-center justify-between px-3 py-2 border-b border-accent/30">
            <span className="text-xs font-medium uppercase text-muted">
              {sessionCount > 0 ? `${sessionCount} session${sessionCount !== 1 ? 's' : ''}` : 'No sessions yet'}
            </span>
            <button
              onClick={clearChat}
              className="flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-medium text-muted hover:bg-accent hover:text-primary transition-colors"
              title="New session"
            >
              <Plus className="size-3" />
              New
            </button>
          </div>
          {/* Full sessions list */}
          <div className="flex-1 overflow-y-auto px-2 py-2">
            {isSessionsLoading ? (
              <div className="space-y-1">{[...Array(5)].map((_, i) => <Skeleton key={i} className="h-8 rounded-lg" />)}</div>
            ) : !sessionsData || sessionsData.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center gap-2">
                <MessageSquare className="size-8 text-muted/20" />
                <p className="text-xs text-muted/50">No sessions yet</p>
                <p className="text-xs text-muted/30">Start chatting to create a session</p>
              </div>
            ) : (
              <div className="space-y-0.5">
                {sessionsData.map((s) => (
                  <SessionItem
                    key={s.session_id}
                    session={s}
                    isSelected={sessionId === s.session_id}
                    onClick={() => setSessionId(s.session_id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ═══ DETAILS VIEW ═══ */}
      {panelView === 'details' && (
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Panel header — mode-aware */}
          <div className="border-b border-accent/50 px-3 py-2.5 shrink-0">
            {/* Entity name + mode badge */}
            <div className="flex items-center gap-2 mb-2">
              <EntityIcon className={cn('size-3.5 shrink-0', modeColor)} />
              <span className="text-xs font-semibold text-primary truncate min-w-0 flex-1">
                {currentEntityName}
              </span>
              <span className={cn('shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide', modeBadgeBg)}>
                {entityLabel}
              </span>
            </div>
            {/* Tab bar */}
            {hasEntity && (
              <div className="flex items-center gap-0.5 rounded-xl border border-accent bg-accent/30 p-0.5">
                {activeTabs.map((t) => (
                  <button
                    key={t.key}
                    onClick={() => setTab(t.key as typeof tab)}
                    className={cn(
                      'flex-1 rounded-lg px-2 py-1 text-[10px] font-medium transition-colors',
                      tab === t.key ? 'bg-background text-primary shadow-sm' : 'text-muted hover:text-primary'
                    )}
                  >{t.label}</button>
                ))}
              </div>
            )}
          </div>
          {/* ── TAB CONTENT ── */}
          <AnimatePresence mode="wait">

      {/* ═══ AGENT tabs ═══ */}

      {mode === 'agent' && tab === 'config' && agentId && (
        <motion.div key="agent-config" className="flex-1 overflow-y-auto"
          initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
        >
          <AgentConfigPanel entityId={agentId} entityType="agent" />
        </motion.div>
      )}

      {mode === 'agent' && tab === 'memory' && agentId && (
        <motion.div key="agent-memory" className="flex-1 overflow-y-auto p-3 space-y-2"
          initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold uppercase text-muted">Stored Memories</span>
            <button
              onClick={() => {
                setMemoriesLoading(true); setMemories([])
                fetch(`${endpointUrl}/memories?agent_id=${agentId}`, { headers: authToken ? { Authorization: `Bearer ${authToken}` } : {} })
                  .then((r) => r.ok ? r.json() : [])
                  .then((data) => { setMemories(Array.isArray(data) ? data : (data.memories ?? [])); setMemoriesLoading(false) })
                  .catch(() => setMemoriesLoading(false))
              }}
              className="rounded-lg p-1 text-muted hover:bg-accent hover:text-primary" title="Refresh"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="size-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>
            </button>
          </div>
          {memoriesLoading ? (
            <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-14 rounded-xl" />)}</div>
          ) : memories.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <MemoryStick className="size-8 text-muted/20" />
              <p className="mt-2 text-xs text-muted/50">No memories yet</p>
              <p className="text-xs text-muted/30">Memories accumulate as the agent converses</p>
            </div>
          ) : memories.map((mem, i) => (
            <div key={mem.id || i} className="rounded-xl border border-accent bg-background p-3">
              <p className="text-xs text-primary leading-relaxed">{mem.memory || mem.summary || '—'}</p>
              {mem.topics && mem.topics.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {mem.topics.map((t) => <span key={t} className="rounded-full bg-accent px-2 py-0.5 text-[10px] text-muted">{t}</span>)}
                </div>
              )}
              <div className="mt-1 text-[10px] text-muted/40">
                {mem.updated_at ? dayjs(mem.updated_at).format('MMM D, HH:mm') : mem.created_at ? dayjs(mem.created_at).format('MMM D, HH:mm') : ''}
              </div>
            </div>
          ))}
        </motion.div>
      )}

      {mode === 'agent' && tab === 'details' && (
        <motion.div key="agent-details" className="flex-1 overflow-y-auto"
          initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
        >
          {loading && <div className="p-3 space-y-2">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-8 rounded-xl" />)}</div>}
          {!loading && agentDetail && (() => {
            const meta = AGENT_META[agentDetail.id]
            return (
            <div className="p-3 space-y-4">
              {/* Static description banner from AGENT_META */}
              {meta && (
                <div className="rounded-xl border border-info/20 bg-info/5 p-3 space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="rounded-full border border-brand/30 bg-brand/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-brand">{meta.skill}</span>
                    <span className="rounded-full border border-accent px-2 py-0.5 text-[10px] font-medium text-muted">{meta.squad}</span>
                  </div>
                  <p className="text-xs text-primary leading-relaxed">{meta.description}</p>
                  {meta.jiraAccess !== 'None' && (
                    <div className="pt-1 border-t border-accent/40">
                      <span className="text-[10px] font-semibold uppercase text-muted tracking-wide">Jira Access</span>
                      <p className="text-xs font-mono text-info mt-0.5">{meta.jiraAccess}</p>
                    </div>
                  )}
                </div>
              )}
              <Section icon={<Bot className="size-3.5 text-brand" />} title="Agent Details">
                <Card>
                  <KV label="Agent Id" value={agentDetail.id} />
                  <KV label="Agent Name" value={agentDetail.name} />
                  {agentDetail.role && <KV label="Role" value={agentDetail.role} />}
                </Card>
              </Section>
              {agentDetail.model && (
                <Section icon={<Cpu className="size-3.5 text-brand" />} title="Model">
                  <Card>
                    <KV label="model" value={agentDetail.model.model} />
                    <KV label="provider" value={agentDetail.model.provider} />
                  </Card>
                </Section>
              )}
              {agentDetail.tools?.tools && agentDetail.tools.tools.length > 0 && (
                <Section icon={<Wrench className="size-3.5 text-brand" />} title={`Tools (${agentDetail.tools.tools.length})`} defaultOpen={false}>
                  <div className="rounded-xl border border-accent bg-background p-3 space-y-1">
                    {agentDetail.tools.tools.map((t, i) => <div key={i} className="text-xs font-mono text-primary">{t.name}</div>)}
                  </div>
                </Section>
              )}
              {agentDetail.knowledge && (
                <Section icon={<BookOpen className="size-3.5 text-brand" />} title="Knowledge">
                  <Card>
                    {agentDetail.knowledge.db_id && <KV label="db_id" value={agentDetail.knowledge.db_id} />}
                    {agentDetail.knowledge.knowledge_table && <KV label="table" value={agentDetail.knowledge.knowledge_table} />}
                  </Card>
                </Section>
              )}
              {(agentDetail.memory || agentDetail.sessions) && (
                <Section icon={<MemoryStick className="size-3.5 text-brand" />} title="Memory & Session Config">
                  <Card>
                    {agentDetail.memory?.enable_agentic_memory !== undefined && <KV label="agentic_memory" value={String(agentDetail.memory.enable_agentic_memory)} />}
                    {agentDetail.memory?.enable_user_memories !== undefined && <KV label="user_memories" value={String(agentDetail.memory.enable_user_memories)} />}
                    {agentDetail.sessions?.add_history_to_context !== undefined && <KV label="history_context" value={String(agentDetail.sessions.add_history_to_context)} />}
                    {agentDetail.sessions?.num_history_runs !== undefined && <KV label="history_runs" value={String(agentDetail.sessions.num_history_runs)} />}
                  </Card>
                </Section>
              )}
              {agentDetail.system_message?.instructions && (
                <Section icon={<MessageSquare className="size-3.5 text-brand" />} title="Instructions" defaultOpen={false}>
                  <pre className="whitespace-pre-wrap rounded-xl bg-accent/20 p-3 text-xs text-primary font-mono max-h-52 overflow-y-auto">{agentDetail.system_message.instructions}</pre>
                </Section>
              )}
            </div>
            )
          })()}
          {!loading && !agentDetail && (
            <div className="flex flex-1 items-center justify-center p-6 text-center text-xs text-muted/40">Select an agent to view details</div>
          )}
        </motion.div>
      )}

      {/* ═══ TEAM tabs ═══ */}

      {mode === 'team' && tab === 'members' && (
        <motion.div key="team-members" className="flex-1 overflow-y-auto"
          initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
        >
          {loading && <div className="p-3 space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}</div>}
          {!loading && teamDetail && (
            <div className="p-3 space-y-4">
              {/* Team summary */}
              <div className={cn('rounded-xl border p-3', 'bg-info/5 border-info/20')}>
                <div className="flex items-center gap-2 mb-1">
                  <Users className="size-3.5 text-info shrink-0" />
                  <span className="text-xs font-semibold text-primary">{teamDetail.name}</span>
                </div>
                <p className="text-[10px] text-muted/70">ID: {teamDetail.id}</p>
                {teamDetail.model && <p className="text-[10px] text-muted/70 mt-0.5">Model: {teamDetail.model.model ?? teamDetail.model.provider}</p>}
              </div>
              {/* Member cards */}
              {teamDetail.members && teamDetail.members.length > 0 ? (
                <Section icon={<Users className="size-3.5 text-info" />} title={`Members (${teamDetail.members.length})`}>
                  <div className="space-y-2">
                    {teamDetail.members.map((m) => (
                      <div key={m.id} className="rounded-xl border border-accent bg-background p-3">
                        <div className="flex items-center gap-2">
                          <div className="flex size-6 shrink-0 items-center justify-center rounded-lg bg-brand/10">
                            <Bot className="size-3 text-brand" />
                          </div>
                          <span className="text-xs font-semibold text-primary">{m.name}</span>
                        </div>
                        {m.role && <p className="mt-1.5 text-[10px] text-muted/70 leading-relaxed">{m.role}</p>}
                        <p className="mt-0.5 text-[10px] text-muted/40 font-mono">id: {m.id}</p>
                      </div>
                    ))}
                  </div>
                </Section>
              ) : (
                <div className="py-6 text-center text-xs text-muted/40">No members found</div>
              )}
              {teamDetail.tools?.tools && teamDetail.tools.tools.length > 0 && (
                <Section icon={<Wrench className="size-3.5 text-info" />} title={`Team Tools (${teamDetail.tools.tools.length})`} defaultOpen={false}>
                  <div className="rounded-xl border border-accent bg-background p-3 space-y-1">
                    {teamDetail.tools.tools.map((t, i) => <div key={i} className="text-xs font-mono text-primary">{t.name}</div>)}
                  </div>
                </Section>
              )}
            </div>
          )}
          {!loading && !teamDetail && (
            <div className="flex flex-1 items-center justify-center p-6 text-center text-xs text-muted/40">Select a team to view members</div>
          )}
        </motion.div>
      )}

      {mode === 'team' && tab === 'config' && teamId && (
        <motion.div key="team-config" className="flex-1 overflow-y-auto"
          initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
        >
          <AgentConfigPanel entityId={teamId} entityType="team" />
        </motion.div>
      )}

      {mode === 'team' && tab === 'memory' && teamId && (
        <motion.div key="team-memory" className="flex-1 overflow-y-auto p-3 space-y-2"
          initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold uppercase text-muted">Team Memories</span>
            <button
              onClick={() => {
                setMemoriesLoading(true); setMemories([])
                fetch(`${endpointUrl}/memories?team_id=${teamId}`, { headers: authToken ? { Authorization: `Bearer ${authToken}` } : {} })
                  .then((r) => r.ok ? r.json() : [])
                  .then((data) => { setMemories(Array.isArray(data) ? data : (data.memories ?? [])); setMemoriesLoading(false) })
                  .catch(() => setMemoriesLoading(false))
              }}
              className="rounded-lg p-1 text-muted hover:bg-accent hover:text-primary" title="Refresh"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="size-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>
            </button>
          </div>
          {memoriesLoading ? (
            <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-14 rounded-xl" />)}</div>
          ) : memories.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <MemoryStick className="size-8 text-muted/20" />
              <p className="mt-2 text-xs text-muted/50">No team memories yet</p>
            </div>
          ) : memories.map((mem, i) => (
            <div key={mem.id || i} className="rounded-xl border border-accent bg-background p-3">
              <p className="text-xs text-primary leading-relaxed">{mem.memory || mem.summary || '—'}</p>
              {mem.topics && mem.topics.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {mem.topics.map((t) => <span key={t} className="rounded-full bg-accent px-2 py-0.5 text-[10px] text-muted">{t}</span>)}
                </div>
              )}
              <div className="mt-1 text-[10px] text-muted/40">
                {mem.updated_at ? dayjs(mem.updated_at).format('MMM D, HH:mm') : ''}
              </div>
            </div>
          ))}
        </motion.div>
      )}

      {/* ═══ WORKFLOW tabs ═══ */}

      {mode === 'workflow' && tab === 'details' && (
        <motion.div key="wf-overview" className="flex-1 overflow-y-auto"
          initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
        >
          {loading && <div className="p-3 space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-8 rounded-xl" />)}</div>}
          {!loading && workflowDetail && (() => {
            const wid = workflowDetail.id
            const meta = WORKFLOW_META[wid]
            return (
              <div className="p-3 space-y-3">
                {/* Header */}
                <div className="rounded-xl border border-positive/20 bg-positive/5 p-3">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="flex items-center gap-2">
                      <GitBranch className="size-4 text-positive shrink-0" />
                      <span className="text-xs font-semibold text-primary">{workflowDetail.name}</span>
                    </div>
                    {meta?.squad && (
                      <span className="shrink-0 rounded-full bg-positive/10 border border-positive/20 px-2 py-0.5 text-[9px] font-semibold uppercase text-positive tracking-wide">
                        {meta.squad}
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] text-muted/70 leading-relaxed">
                    {meta?.description ?? workflowDetail.description ?? 'No description available.'}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-muted/50">
                    <span className="font-mono">id: {workflowDetail.id}</span>
                    <span>·</span>
                    <span>{workflowDetail.steps?.length ?? 0} steps</span>
                  </div>
                </div>

                {/* Pipeline */}
                {meta?.pipeline && (
                  <Section icon={<Layers className="size-3.5 text-positive" />} title="Pipeline">
                    <div className="rounded-xl border border-accent bg-background p-3">
                      <div className="flex flex-col gap-1">
                        {meta.pipeline.map((step, i) => (
                          <div key={i} className="flex items-start gap-2">
                            <div className="flex flex-col items-center shrink-0 mt-0.5">
                              <span className="flex size-4 items-center justify-center rounded-full bg-positive/10 text-[9px] font-bold text-positive">{i + 1}</span>
                              {i < meta.pipeline.length - 1 && <div className="w-px flex-1 bg-accent/60 mt-0.5 h-3" />}
                            </div>
                            <span className="text-xs text-primary leading-relaxed pb-1">{step}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </Section>
                )}

                {/* Input format */}
                <Section icon={<Play className="size-3.5 text-positive" />} title="How to Run">
                  <div className="space-y-2">
                    {meta?.inputFormat && (
                      <div className="rounded-xl border border-accent bg-background p-2.5">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-muted/60 mb-1">Input Format</p>
                        <p className="text-xs text-primary">{meta.inputFormat}</p>
                      </div>
                    )}
                    {meta?.placeholder && (
                      <div className="rounded-xl border border-accent/50 bg-accent/20 p-2.5">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-muted/60 mb-1">Example</p>
                        <pre className="text-xs text-muted whitespace-pre-wrap font-mono">{meta.placeholder}</pre>
                      </div>
                    )}
                    {!meta && (
                      <div className="rounded-xl border border-accent bg-background p-3 text-xs text-muted leading-relaxed">
                        Type your input in the chat box and press Send. The workflow will execute all steps automatically.
                      </div>
                    )}
                  </div>
                </Section>
              </div>
            )
          })()}
          {!loading && !workflowDetail && (
            <div className="flex flex-1 items-center justify-center p-6 text-center text-xs text-muted/40">Select a workflow to view its overview</div>
          )}
        </motion.div>
      )}

      {mode === 'workflow' && tab === 'steps' && (
        <motion.div key="wf-steps" className="flex-1 overflow-y-auto"
          initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
        >
          {loading && <div className="p-3 space-y-2">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-10 rounded-xl" />)}</div>}
          {!loading && workflowDetail?.steps && workflowDetail.steps.length > 0 && (
            <div className="p-3 space-y-2">
              <div className="flex items-center gap-1.5 mb-3">
                <Layers className="size-3.5 text-positive" />
                <span className="text-xs font-semibold uppercase text-muted">{workflowDetail.steps.length} Steps</span>
              </div>
              {workflowDetail.steps.map((step, i) => {
                const stepsLen = workflowDetail.steps?.length ?? 0
                return (
                <div key={i} className="relative flex gap-3">
                  {i < stepsLen - 1 && (
                    <div className="absolute left-[13px] top-7 bottom-0 w-px bg-accent/60" />
                  )}
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-full border border-positive/40 bg-positive/10 text-[10px] font-bold text-positive z-10">
                    {i + 1}
                  </div>
                  <div className="flex-1 rounded-xl border border-accent bg-background px-3 py-2 mb-1">
                    <p className="text-xs font-semibold text-primary">{step.name ?? `Step ${i + 1}`}</p>
                    {step.type && (
                      <span className="mt-1 inline-block rounded-full bg-accent px-2 py-0.5 text-[9px] uppercase font-medium text-muted/70">
                        {step.type}
                      </span>
                    )}
                  </div>
                </div>
                )
              })}
            </div>
          )}
          {!loading && (!workflowDetail?.steps || workflowDetail.steps.length === 0) && (
            <div className="flex flex-col items-center justify-center py-12 text-center p-6">
              <Layers className="size-8 text-muted/20" />
              <p className="mt-2 text-xs text-muted/50">No step data available</p>
              <p className="text-xs text-muted/30">Select a workflow first</p>
            </div>
          )}
        </motion.div>
      )}

          </AnimatePresence>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main ChatPage
// ---------------------------------------------------------------------------
// Quick-prompt suggestions per agent / team
// ---------------------------------------------------------------------------

const AGENT_PROMPTS: Record<string, string[]> = {
  // Concierge
  concierge: [
    'Generate test cases from a Jira ticket',
    'Fix a failing test in CI',
    'Onboard a new app to automation',
    'Analyse a CI pipeline failure',
  ],
  // Squad 1 – Strategy
  architect:         ['Analyze this Jira ticket: PROJ-123', 'Which Page Objects are affected by the checkout redesign?', 'Parse this requirement and produce an execution plan'],
  scribe:            ['Write a Gherkin spec for user login with MFA', 'Convert this acceptance criterion into BDD steps', 'Generate reusable step definitions for the cart flow'],
  // Squad 2 – Context
  discovery:         ['Crawl the AUT and generate the Site Manifesto', 'What pages are available on the AUT?', 'Extract the accessibility tree for the login page'],
  librarian:         ['Index all Page Objects in the automation/ folder', 'Find the POM for the checkout page', 'Re-index the codebase after recent commits'],
  // Squad 3 – Engineering
  engineer:          ['Generate a Page Object for the dashboard', 'Write step definitions for the Gherkin spec', 'Create a Playwright POM following the Look-Before-You-Leap pattern'],
  'data-agent':      ['Provision a fresh test user for the smoke suite', 'Seed the DB with valid checkout data', 'Generate a RunContext for the login feature'],
  // Squad 4 – Operations
  detective:         ['Analyze this Playwright trace.zip for the failing test', 'Classify the root cause of the checkout timeout failure', 'Is this failure a locator issue or a real app bug?'],
  medic:             ['Heal the broken locator in CheckoutPage.ts', 'Fix the stale selector for the submit button', 'Apply a surgical patch to the failing locator only'],
  judge:             ['Review this Gherkin spec against the DoD checklist', 'Evaluate the generated Page Object for quality', 'Run adversarial review on this healing patch'],
  // Extras
  'ci-log-analyzer': ['Analyze the latest GitHub Actions failure log', 'Which step caused the pipeline to fail?', 'Summarize flaky tests from the last 10 runs'],
  curator:           ['What knowledge base entries are outdated?', 'Identify stale codebase vectors for cleanup', 'Show the indexing status of the automation/ folder'],
  'technical-tester':['Generate unit tests for the login module', 'Create API tests for the /auth endpoint', 'Write integration tests for the cart service'],
  // Teams
  strategy:          ['Architect + Scribe: Turn this Jira ticket into a ready Gherkin spec', 'Analyze requirements for the new search feature', 'Produce an execution plan with acceptance criteria coverage'],
  context:           ['Discovery + Librarian: Onboard the AUT and index the codebase', 'Crawl the app and sync the vector KB', 'What UI components are available on the dashboard page?'],
  engineering:       ['Engineer + Data Agent: Implement the checkout spec end-to-end', 'Generate POM, step defs and test data for the login feature', 'Build automation for the new user registration flow'],
  operations:        ['Detective + Medic: Triage and heal the failing smoke tests', 'Analyze trace.zip and patch broken locators', 'Run the full triage-heal loop on the CI failure'],
  grooming:          ['Curator + Librarian: Audit and clean the KB', 'Find and remove obsolete Page Object vectors', 'Sync the knowledge base with the latest commits'],
  diagnostics:       ['Analyze pipeline failures from the last sprint', 'Correlate test failures with recent code changes', 'Generate an RCA report for the nightly regression'],
}

const DEFAULT_PROMPTS: Record<string, string[]> = {
  agent:    ['What can you help me with?', 'Show me your available tools', 'Walk me through your primary skill'],
  team:     ['What does this team specialise in?', 'Run a quick smoke check on the AUT', 'Show me the team members and their roles'],
  workflow: ['Describe what this workflow does', 'Run the workflow with default parameters', 'Show me the workflow steps'],
}

// ---------------------------------------------------------------------------
// Main ChatPage
// ---------------------------------------------------------------------------

export default function ChatPage() {
  const [inputMessage, setInputMessage] = useState('')
  const [attachedFiles, setAttachedFiles] = useState<File[]>([])
  const [runInBackground, setRunInBackground] = useState(false)
  const [settingsMenuOpen, setSettingsMenuOpen] = useState(false)
  const settingsMenuRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [showActivity, setShowActivity] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const { messages, isStreaming, isPaused, isEndpointActive, rightPanelOpen, setRightPanelOpen, chatEvents, setMode, setMessages, activeRunId } = useStore()
  const { handleStreamResponse, cancelRun } = useAIChatStreamHandler()
  const { clearChat } = useChatActions()
  const { getSessions, getSession } = useSessionLoader()
  const [agentId, setAgentId] = useQueryState('agent')
  const [teamId, setTeamId] = useQueryState('team')
  const [workflowId, setWorkflowId] = useQueryState('workflow')
  const [sessionId, setSessionId] = useQueryState('session')
  const [dbId, setDbId] = useQueryState('db_id')
  const { mode } = useStore()

  // Route suggestion handler — switches mode + entity when user clicks "Switch to X"
  const handleRoute = (d: RouteDirective) => {
    setMessages([])
    setSessionId(null)
    setMode(d.mode)
    if (d.mode === 'agent')    { setAgentId(d.route_to); setTeamId(null); setWorkflowId(null); setDbId(null) }
    else if (d.mode === 'team')     { setTeamId(d.route_to); setAgentId(null); setWorkflowId(null); setDbId(null) }
    else                            { setWorkflowId(d.route_to); setAgentId(null); setTeamId(null); setDbId(null) }
    if (d.starter_prompt) setTimeout(() => { setInputMessage(d.starter_prompt!); textareaRef.current?.focus() }, 100)
  }

  // First-visit: auto-select Concierge and show welcome message
  useEffect(() => {
    if (typeof window === 'undefined') return
    if (agentId || teamId || workflowId || sessionId) return
    const visited = localStorage.getItem('qap_visited')
    if (visited) return
    localStorage.setItem('qap_visited', '1')
    setMode('agent')
    setAgentId('concierge')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!agentId && !teamId && !workflowId) return
    getSessions({ entityType: mode === 'workflow' ? 'workflow' : mode as 'agent' | 'team', agentId, teamId, workflowId, dbId })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId, teamId, workflowId, mode, dbId])

  useEffect(() => {
    if (sessionId && (agentId || teamId || workflowId)) {
      getSession({ entityType: mode === 'workflow' ? 'workflow' : mode as 'agent' | 'team', agentId, teamId, workflowId, dbId }, sessionId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  // Close settings popover when clicking outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (settingsMenuRef.current && !settingsMenuRef.current.contains(e.target as Node)) {
        setSettingsMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Auto-resize textarea as content grows
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 213)}px`
  }, [inputMessage])

  const handleSubmit = async () => {
    if ((!inputMessage.trim() && attachedFiles.length === 0) || isStreaming) return
    const msg = inputMessage
    const files = attachedFiles
    setInputMessage('')
    setAttachedFiles([])

    // Split: images go as binary (VLM-capable models), text files are read client-side
    const imageFiles = files.filter((f) => f.type.startsWith('image/'))
    const textFiles = files.filter((f) => !f.type.startsWith('image/'))

    // Read text/code/data file contents and embed as code blocks in the message
    let fullMsg = msg
    if (textFiles.length > 0) {
      const textContents = await Promise.all(
        textFiles.map(async (f) => {
          try {
            const content = await f.text()
            const ext = f.name.split('.').pop() ?? ''
            return `\n\n--- File: ${f.name} ---\n\`\`\`${ext}\n${content}\n\`\`\``
          } catch {
            return `\n\n[File: ${f.name} — could not read content]`
          }
        })
      )
      fullMsg = msg + textContents.join('')
    }

    if (imageFiles.length > 0) {
      // Send images as form data; requires a VLM-capable model on the backend
      const fd = new FormData()
      fd.append('message', fullMsg)
      if (runInBackground) fd.append('run_in_background', 'true')
      imageFiles.forEach((f) => fd.append('files', f))
      await handleStreamResponse(fd)
    } else if (runInBackground) {
      const fd = new FormData()
      fd.append('message', fullMsg)
      fd.append('run_in_background', 'true')
      await handleStreamResponse(fd)
    } else {
      await handleStreamResponse(fullMsg)
    }
  }

  const hasEntity = Boolean(agentId || teamId || workflowId)

  return (
    <div className="flex h-full overflow-hidden">

      {/* Chat area */}
      <div
        className="relative flex flex-1 flex-col overflow-hidden"
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
        onDragEnter={(e) => { e.preventDefault(); setIsDragOver(true) }}
        onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setIsDragOver(false) }}
        onDrop={(e) => {
          e.preventDefault()
          setIsDragOver(false)
          const droppedFiles = Array.from(e.dataTransfer.files)
          if (droppedFiles.length > 0) {
            const accepted = droppedFiles.filter((f) =>
              f.type.startsWith('image/') ||
              ['application/pdf', 'text/plain', 'text/markdown', 'text/csv', 'application/json'].includes(f.type) ||
              /\.(md|txt|csv|json|pdf)$/i.test(f.name)
            )
            if (accepted.length > 0) setAttachedFiles((prev) => [...prev, ...accepted])
          } else {
            const text = e.dataTransfer.getData('text/uri-list') || e.dataTransfer.getData('text/plain')
            if (text && /^https?:\/\//i.test(text.trim())) {
              setInputMessage((prev) => prev ? `${prev}\n${text.trim()}` : text.trim())
            }
          }
        }}
      >
        {isDragOver && (
          <motion.div
            className="pointer-events-none absolute inset-0 z-50 flex flex-col items-center justify-center gap-2 rounded-none border-2 border-dashed border-brand bg-brand/5 backdrop-blur-sm"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          >
            <Paperclip className="size-10 text-brand/60" />
            <p className="text-sm font-semibold text-brand">Drop files or a URL here</p>
            <p className="text-xs text-brand/60">Images · PDF · TXT · CSV · JSON · URLs</p>
          </motion.div>
        )}
        {/* Ribbon */}
        <div className="flex items-center gap-3 border-b border-accent/50 px-3 py-2 shrink-0">
          {/* Left: mode + entity picker */}
          <div className="flex items-center gap-2 shrink-0">
            <ModeSelector />
            <EntitySelector />
          </div>
          {/* Right: tools */}
          <div className="flex flex-1 items-center justify-end gap-1.5">
            <ModelSwitcher />
            <button
              onClick={() => setShowActivity(!showActivity)}
              title={showActivity ? 'Hide activity stream' : 'Show live activity stream'}
              className={cn(
                'rounded-lg p-1.5 hover:bg-accent',
                showActivity ? 'text-brand' : 'text-muted hover:text-primary'
              )}
            >
              <Activity className="size-4" />
            </button>
            <button
              onClick={() => setRightPanelOpen(!rightPanelOpen)}
              title={rightPanelOpen ? 'Hide panel' : 'Show config & events'}
              className="rounded-lg p-1.5 text-muted hover:bg-accent hover:text-primary"
            >
              {rightPanelOpen ? <PanelRightClose className="size-4" /> : <PanelRightOpen className="size-4" />}
            </button>
          </div>
        </div>

        {/* Messages */}
        <StickToBottom className="relative flex-1 overflow-y-auto" resize="smooth" initial="smooth">
          <StickToBottom.Content className="mx-auto w-full max-w-3xl space-y-6 px-4 py-6">
            <AnimatePresence mode="wait">
            {messages.length === 0 ? (
              <motion.div
                key="empty-state"
                className="flex size-full flex-grow flex-col items-center justify-center gap-6 px-4"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
              >
                <motion.div
                  className="flex max-w-[800px] flex-col items-center gap-2"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.08 }}
                >
                  <motion.div
                    initial={{ scale: 0.85, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: 0.1, duration: 0.3, type: 'spring', stiffness: 260, damping: 22 }}
                  >
                    <MessagesSquare className="size-5 text-primary" />
                  </motion.div>
                  <motion.p
                    className="text-[1.125rem] font-medium leading-[1.35rem] tracking-[-0.01em] text-primary"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.16 }}
                  >
                    {agentId === 'concierge' ? 'Welcome to Quality Autopilot'
                      : (agentId || teamId || workflowId) ? 'New Session' : 'Quality Autopilot'}
                  </motion.p>
                  <motion.p
                    className="text-center text-[0.875rem] font-normal leading-[21px] tracking-[-0.02em] text-muted"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.22 }}
                  >
                    {!isEndpointActive ? 'Connect to your AgentOS endpoint to start chatting.'
                      : agentId === 'concierge' ? "I'm your Concierge — tell me what you need and I'll route you to the right agent, team, or workflow."
                        : !hasEntity ? 'Select an agent, team, or workflow from the sidebar to begin.'
                          : 'Enter your input to get started with your agent.'}
                  </motion.p>
                </motion.div>

                {/* Quick-prompt chips */}
                {isEndpointActive && hasEntity && (() => {
                  const key = agentId ?? teamId ?? workflowId ?? ''
                  const prompts = AGENT_PROMPTS[key] ?? DEFAULT_PROMPTS[mode] ?? []
                  if (prompts.length === 0) return null
                  return (
                    <motion.div
                      className="mb-[10%] flex flex-wrap items-center justify-center gap-3"
                      initial="hidden"
                      animate="visible"
                      variants={{ visible: { transition: { staggerChildren: 0.07, delayChildren: 0.3 } } }}
                    >
                      {prompts.map((prompt) => (
                        <motion.button
                          key={prompt}
                          variants={{ hidden: { opacity: 0, scale: 0.9, y: 8 }, visible: { opacity: 1, scale: 1, y: 0 } }}
                          transition={{ type: 'spring', stiffness: 300, damping: 24 }}
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.97 }}
                          onClick={() => setInputMessage(prompt)}
                          className="flex w-full max-w-[325px] select-none items-center justify-center overflow-hidden rounded-full border border-accent bg-primaryAccent px-4 py-2 text-[0.875rem] text-primary transition-colors hover:cursor-pointer hover:bg-accent/60"
                        >
                          <span className="truncate text-center">{prompt}</span>
                        </motion.button>
                      ))}
                    </motion.div>
                  )
                })()}
              </motion.div>
            ) : (
              <motion.div key="messages" className="space-y-6" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.2 }}>
                {messages.map((msg, i) => {
                  const isLast = i === messages.length - 1
                  const isActiveStreaming = isLast && isStreaming
                  const latestEvent = isActiveStreaming && chatEvents.length > 0
                    ? chatEvents[chatEvents.length - 1]
                    : null
                  return <MessageItem key={i} msg={msg} index={i} isActiveStreaming={isActiveStreaming} latestEvent={latestEvent} onFollowupClick={(s) => { setInputMessage(s); setTimeout(() => textareaRef.current?.focus(), 0) }} onRoute={handleRoute} />
                })}
              </motion.div>
            )}
            </AnimatePresence>
          </StickToBottom.Content>
        </StickToBottom>

        {/* Inline activity log */}
        {showActivity && <ActivityLog events={chatEvents} isStreaming={isStreaming} />}

        {/* Inline approval block — shown when a run is paused waiting for human input */}
        <AnimatePresence>
          {(isPaused || !isStreaming) && messages.length > 0 && (
            <div className="px-4 pt-1 pb-0">
              <div className="mx-auto w-full max-w-3xl">
                <ApprovalBlock runId={activeRunId} />
              </div>
            </div>
          )}
        </AnimatePresence>


        {/* Input — agno.com card style */}
        <div className="px-4 pb-4 pt-2">
          <div
            id="chat-input-container"
            className="mx-auto w-full max-w-[800px] flex-col items-center gap-2 rounded-xl border border-accent bg-accent p-2 shadow-md"
          >
            {/* File preview strip — inside card */}
            {attachedFiles.length > 0 && (
              <div className="mb-2 flex flex-wrap gap-1.5 px-1 pt-1">
                {attachedFiles.map((file, i) => (
                  <div key={i} className="flex items-center gap-1.5 rounded-lg border border-accent/60 bg-background px-2 py-1 text-xs">
                    {file.type.startsWith('image/') ? (
                      <ImageIcon className="size-3 text-brand" />
                    ) : (
                      <FileText className="size-3 text-muted" />
                    )}
                    <span className="max-w-[120px] truncate text-primary">{file.name}</span>
                    <button
                      onClick={() => setAttachedFiles((prev) => prev.filter((_, idx) => idx !== i))}
                      className="text-muted hover:text-destructive"
                    >
                      <XIcon className="size-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Textarea */}
            <input
              ref={fileInputRef}
              type="file"
              id="file-upload"
              accept="image/*,.pdf,.csv,.json,.txt,.md,.doc,.docx,.webp,.jpeg,.jpg,.png"
              multiple
              className="hidden"
              onChange={(e) => {
                const files = Array.from(e.target.files ?? [])
                setAttachedFiles((prev) => [...prev, ...files])
                e.target.value = ''
              }}
            />
            <div className="rounded-lg bg-background/30">
              <TextArea
                ref={textareaRef}
                placeholder="Ask anything..."
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                    e.preventDefault(); handleSubmit()
                  }
                }}
                className="w-full resize-none border-none bg-transparent p-3 text-[0.875rem] leading-[21px] tracking-[-0.02em] placeholder:text-muted/50 focus-visible:ring-0 focus-visible:ring-offset-0 min-h-[44px] max-h-[213px]"
                disabled={!hasEntity}
              />
            </div>

            {/* Bottom toolbar */}
            <div className="flex w-full items-center justify-between gap-2 px-1 pb-1 mt-1">
              {/* Left: attach + run settings */}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  title="Attach files"
                  disabled={!hasEntity}
                  onClick={() => fileInputRef.current?.click()}
                  className="inline-flex size-8 shrink-0 items-center justify-center rounded-md border border-accent/70 bg-transparent text-primary shadow-sm transition-colors hover:bg-primary/5 disabled:pointer-events-none disabled:opacity-50"
                >
                  <Paperclip className="size-4" />
                </button>

                {/* Run settings popover */}
                <div ref={settingsMenuRef} className="relative">
                  <button
                    type="button"
                    title="Run settings"
                    onClick={() => setSettingsMenuOpen(v => !v)}
                    className={cn(
                      "inline-flex size-8 shrink-0 items-center justify-center rounded-md border border-accent/70 bg-transparent text-primary shadow-sm transition-colors hover:bg-primary/5",
                      runInBackground && "border-primary/60 text-primary"
                    )}
                  >
                    <Settings2 className="size-4" />
                  </button>

                  {settingsMenuOpen && (
                    <div
                      className="absolute bottom-full left-0 z-50 mb-2 w-64 rounded-md border border-accent bg-background p-2 shadow-xl"
                      onMouseLeave={() => setSettingsMenuOpen(false)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex flex-col gap-0.5">
                          <p className="text-[0.75rem] font-medium leading-[1.1rem] tracking-tight">Run in background</p>
                          <p className="text-[0.7rem] leading-[1.1rem] text-muted">Survives disconnects. Pick up right where you left off.</p>
                        </div>
                        {/* toggle switch */}
                        <button
                          type="button"
                          role="switch"
                          aria-checked={runInBackground}
                          onClick={() => setRunInBackground(v => !v)}
                          className={cn(
                            "inline-flex h-5 w-[30px] shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent shadow-sm transition-colors focus-visible:outline-none",
                            runInBackground ? "bg-primary" : "bg-muted/50"
                          )}
                        >
                          <span
                            className={cn(
                              "pointer-events-none block size-[13px] rounded-full bg-background shadow-lg ring-0 transition-transform",
                              runInBackground ? "translate-x-[13px]" : "translate-x-0"
                            )}
                          />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Right: stop / send */}
              {isStreaming ? (
                <button
                  onClick={cancelRun}
                  title="Stop run"
                  className="inline-flex size-8 shrink-0 items-center justify-center rounded-sm bg-destructive text-white shadow-sm transition-colors hover:bg-destructive/80"
                >
                  <Square className="size-[10px] fill-current" />
                </button>
              ) : (
                <button
                  onClick={handleSubmit}
                  disabled={(!inputMessage.trim() && attachedFiles.length === 0) || !hasEntity}
                  className="inline-flex size-8 shrink-0 items-center justify-center rounded-sm bg-primary text-background shadow-sm transition-colors hover:bg-primary/80 disabled:pointer-events-none disabled:opacity-50"
                >
                  <ArrowUp className="size-[10.67px]" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Right panel — collapsible */}
      {rightPanelOpen && (
        <aside className="flex w-72 shrink-0 flex-col border-l border-accent/50 bg-primaryAccent overflow-y-auto">
          <RightPanel agentId={agentId} teamId={teamId} workflowId={workflowId} sessionId={sessionId} clearChat={clearChat} setSessionId={setSessionId} />
        </aside>
      )}
    </div>
  )
}
