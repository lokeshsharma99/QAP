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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { StickToBottom } from 'use-stick-to-bottom'
import Icon from '@/components/ui/icon'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import rehypeSanitize from 'rehype-sanitize'
import { useQueryState } from 'nuqs'
import { cn } from '@/lib/utils'
import dayjs from 'dayjs'
import { toast } from 'sonner'
import { ChatMessage } from '@/types/os'
import {
  ChevronDown, ChevronUp, Wrench, Brain, Plus, PanelRightOpen, PanelRightClose,
  Bot, Cpu, Database, Hash, Clock, CheckCircle, XCircle, Zap, GitBranch, Activity,
  Users, Settings, BookOpen, MemoryStick, Layers, MessageSquare, MessagesSquare,
  Play, CornerDownRight, ArrowUp, Paperclip, X as XIcon, FileText, Image as ImageIcon
} from 'lucide-react'

import { getAgentDetailAPI, getTeamDetailAPI, getWorkflowDetailAPI } from '@/api/os'
import { AgentFullDetail, TeamFullDetail, WorkflowFullDetail, WorkflowStep } from '@/types/os'
import AgentConfigPanel from '@/components/chat/AgentConfigPanel'
import { constructEndpointUrl } from '@/lib/constructEndpointUrl'

const ToolCallItem = ({ toolCall }: { toolCall: NonNullable<ChatMessage['tool_calls']>[0] }) => {
  const [open, setOpen] = useState(false)
  return (
    <div className={cn('rounded-xl border text-xs', toolCall.tool_call_error ? 'border-destructive/30' : 'border-accent')}>
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 px-3 py-2 text-left">
        <Wrench className="size-3 shrink-0 text-muted" />
        <span className="flex-1 font-medium text-muted">{toolCall.tool_name}</span>
        {toolCall.tool_call_error && <span className="rounded bg-destructive/20 px-1.5 py-0.5 text-destructive">error</span>}
        {open ? <ChevronUp className="size-3 text-muted" /> : <ChevronDown className="size-3 text-muted" />}
      </button>
      {open && (
        <div className="border-t border-accent px-3 py-2 space-y-2">
          {toolCall.tool_args && Object.keys(toolCall.tool_args).length > 0 && (
            <div>
              <div className="mb-1 text-xs font-medium uppercase text-muted">Args</div>
              <pre className="overflow-x-auto rounded bg-background px-2 py-1.5 text-xs text-primary">{JSON.stringify(toolCall.tool_args, null, 2)}</pre>
            </div>
          )}
          {toolCall.content && (
            <div>
              <div className="mb-1 text-xs font-medium uppercase text-muted">Result</div>
              <pre className="max-h-40 overflow-y-auto rounded bg-background px-2 py-1.5 text-xs text-primary">
                {typeof toolCall.content === 'string' ? toolCall.content : JSON.stringify(toolCall.content, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const ReasoningBlock = ({ steps }: { steps: NonNullable<ChatMessage['extra_data']>['reasoning_steps'] }) => {
  const [open, setOpen] = useState(false)
  if (!steps || steps.length === 0) return null
  return (
    <div className="mb-2 rounded-xl border border-accent text-xs">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 px-3 py-2">
        <Brain className="size-3 text-muted" />
        <span className="flex-1 text-left text-muted">Reasoning ({steps.length} steps)</span>
        {open ? <ChevronUp className="size-3 text-muted" /> : <ChevronDown className="size-3 text-muted" />}
      </button>
      {open && (
        <div className="space-y-2 border-t border-accent px-3 py-2">
          {steps.map((step, i) => (
            <div key={i} className="border-l-2 border-accent pl-2">
              <div className="font-medium text-muted">{step.title}</div>
              {step.reasoning && <div className="mt-0.5 text-muted/70">{step.reasoning}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const MessageItem = ({ msg, index }: { msg: ChatMessage; index: number }) => {
  const isUser = msg.role === 'user'
  return (
    <motion.div
      className={cn('flex flex-col gap-1', isUser ? 'items-end' : 'items-start')}
      initial={{ opacity: 0, y: 16, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1], delay: Math.min(index * 0.04, 0.3) }}
    >
      <div className="flex items-center gap-2">
        <Icon type={isUser ? 'user' : 'agent'} size="xs" />
        <span className="text-xs font-medium uppercase text-muted">{isUser ? 'You' : 'Agent'}</span>
        <span className="text-xs text-muted/50">{dayjs.unix(msg.created_at).format('HH:mm')}</span>
      </div>
      {msg.extra_data?.reasoning_steps && <ReasoningBlock steps={msg.extra_data.reasoning_steps} />}
      {msg.tool_calls && msg.tool_calls.length > 0 && (
        <div className="w-full max-w-2xl space-y-1">
          {msg.tool_calls.map((tc, i) => <ToolCallItem key={i} toolCall={tc} />)}
        </div>
      )}
      {msg.content && (
        <div className={cn('max-w-2xl rounded-xl px-4 py-3 text-sm',
          isUser ? 'bg-accent text-primary'
            : msg.streamingError ? 'border border-destructive/30 bg-background text-destructive'
              : 'bg-primaryAccent text-primary'
        )}>
          {isUser ? <p className="whitespace-pre-wrap">{msg.content}</p>
            : <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw, rehypeSanitize]}>{msg.content}</ReactMarkdown>}
        </div>
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

const SessionItem = ({ session, isSelected, onClick }: {
  session: { session_id: string; created_at: string | number }
  isSelected: boolean
  onClick: () => void
}) => (
  <motion.button
    onClick={onClick}
    whileHover={{ x: 2 }}
    whileTap={{ scale: 0.98 }}
    transition={{ duration: 0.15 }}
    className={cn(
      'w-full truncate rounded-xl px-3 py-2 text-left text-xs transition-colors',
      isSelected ? 'bg-accent text-primary' : 'text-muted hover:bg-accent/50 hover:text-primary'
    )}
  >
    <div className="font-medium">Session {session.session_id.slice(0, 8)}…</div>
    <div className="mt-0.5 text-muted/50">{fmtSessionDate(session.created_at)}</div>
  </motion.button>
)

// ---------------------------------------------------------------------------
// Mode & Entity selectors
// ---------------------------------------------------------------------------

const ModeSelector = () => {
  const { mode, setMode, setMessages } = useStore()
  const [, setAgentId] = useQueryState('agent')
  const [, setTeamId] = useQueryState('team')
  const [, setWorkflowId] = useQueryState('workflow')
  const [, setSessionId] = useQueryState('session')

  const handleModeChange = (newMode: 'agent' | 'team' | 'workflow') => {
    setMode(newMode); setMessages([]); setAgentId(null); setTeamId(null); setWorkflowId(null); setSessionId(null)
  }
  return (
    <div className="flex rounded-xl border border-primary/15 bg-accent p-0.5">
      {(['agent', 'team', 'workflow'] as const).map((m) => (
        <button key={m} onClick={() => handleModeChange(m)} className={cn(
          'flex-1 rounded-lg px-2 py-1 text-xs font-medium uppercase transition-colors',
          mode === m ? 'bg-primary text-primaryAccent' : 'text-muted hover:text-primary'
        )}>{m}</button>
      ))}
    </div>
  )
}

const EntitySelector = () => {
  const { mode, agents, teams, workflows, setMessages, setSelectedModel } = useStore()
  const [agentId, setAgentId] = useQueryState('agent')
  const [teamId, setTeamId] = useQueryState('team')
  const [workflowId, setWorkflowId] = useQueryState('workflow')
  const [, setSessionId] = useQueryState('session')
  const [, setDbId] = useQueryState('db_id')

  const entities = mode === 'team' ? teams : mode === 'workflow' ? workflows : agents
  const currentValue = mode === 'team' ? teamId : mode === 'workflow' ? workflowId : agentId

  const handleChange = (value: string) => {
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
  }

  if (entities.length === 0) {
    return (
      <Select disabled>
        <SelectTrigger className="h-9 text-xs font-medium uppercase opacity-50">
          <SelectValue placeholder={`No ${mode}s`} />
        </SelectTrigger>
      </Select>
    )
  }
  return (
    <Select value={currentValue || ''} onValueChange={handleChange}>
      <SelectTrigger className="h-9 text-xs font-medium uppercase">
        <SelectValue placeholder={`Select ${mode}`} />
      </SelectTrigger>
      <SelectContent>
        {entities.map((entity) => (
          <SelectItem key={(entity as { id: string }).id} value={(entity as { id: string }).id} className="text-xs uppercase">
            {(entity as { name?: string; id: string }).name || (entity as { id: string }).id}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
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

const Section = ({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) => (
  <div>
    <div className="mb-1.5 flex items-center gap-1.5">
      {icon}
      <span className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</span>
    </div>
    {children}
  </div>
)

const KV = ({ label, value }: { label: string; value: React.ReactNode }) => (
  <div className="flex flex-col gap-0.5 py-1 border-b border-accent/30 last:border-0">
    <span className="text-xs text-muted/60">{label}:</span>
    <span className="text-xs font-mono text-primary break-all">{value}</span>
  </div>
)

const Card = ({ children }: { children: React.ReactNode }) => (
  <div className="rounded-xl border border-accent bg-background p-3 space-y-0.5 text-xs">{children}</div>
)

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

const RightPanel = ({ agentId, teamId, workflowId, sessionId }: { agentId: string | null; teamId: string | null; workflowId: string | null; sessionId: string | null }) => {
  const { mode, chatEvents, isStreaming, selectedEndpoint, authToken } = useStore()
  const [tab, setTab] = useState<'details' | 'config' | 'memory'>('details')
  const [agentDetail, setAgentDetail] = useState<AgentFullDetail | null>(null)
  const [teamDetail, setTeamDetail] = useState<TeamFullDetail | null>(null)
  const [workflowDetail, setWorkflowDetail] = useState<WorkflowFullDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [memories, setMemories] = useState<Array<{id: string; memory?: string; summary?: string; topics?: string[]; agent_id?: string; created_at?: string; updated_at?: string}>>([])  
  const [memoriesLoading, setMemoriesLoading] = useState(false)

  const endpointUrl = constructEndpointUrl(selectedEndpoint)

  useEffect(() => {
    if (mode === 'agent' && agentId) {
      setLoading(true)
      setTab((t) => (t === 'memory' ? 'details' : t))
      getAgentDetailAPI(endpointUrl, agentId, authToken).then((d) => { setAgentDetail(d); setLoading(false) })
    } else if (mode === 'team' && teamId) {
      setLoading(true)
      setTab((t) => (t === 'memory' ? 'details' : t))
      getTeamDetailAPI(endpointUrl, teamId, authToken).then((d) => { setTeamDetail(d); setLoading(false) })
    } else if (mode === 'workflow' && workflowId) {
      setLoading(true)
      getWorkflowDetailAPI(endpointUrl, workflowId, authToken).then((d) => { setWorkflowDetail(d); setLoading(false) })
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

  const isConfigurable = (mode === 'agent' || mode === 'team') && !!currentEntityId

  return (
    <div className="flex h-full flex-col gap-0 overflow-y-auto">
      {/* Header */}
      <div className="border-b border-accent/50 px-3 py-2.5 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <EntityIcon className="size-3.5 text-brand" />
            <span className="text-xs font-semibold text-primary">
              {(agentDetail?.name ?? teamDetail?.name ?? workflowDetail?.name ?? (agentId || teamId || workflowId) ?? entityLabel)}
            </span>
          </div>
          {isConfigurable && (
            <div className="flex items-center gap-0.5 rounded-xl border border-accent bg-accent/30 p-0.5">
              <button
                onClick={() => setTab('details')}
                className={cn(
                  'rounded-lg px-2.5 py-1 text-[10px] font-medium transition-colors',
                  tab === 'details' ? 'bg-background text-primary shadow-sm' : 'text-muted hover:text-primary'
                )}
              >Details</button>
              <button
                onClick={() => setTab('config')}
                className={cn(
                  'rounded-lg px-2.5 py-1 text-[10px] font-medium transition-colors',
                  tab === 'config' ? 'bg-background text-primary shadow-sm' : 'text-muted hover:text-primary'
                )}
              >Config</button>
              <button
                onClick={() => setTab('memory')}
                className={cn(
                  'rounded-lg px-2.5 py-1 text-[10px] font-medium transition-colors',
                  tab === 'memory' ? 'bg-background text-primary shadow-sm' : 'text-muted hover:text-primary'
                )}
              >Memory</button>
            </div>
          )}
        </div>
      </div>

      {/* Config tab — editable AgentConfigPanel */}
      <AnimatePresence mode="wait">
      {tab === 'config' && isConfigurable && currentEntityId && (
        <motion.div
          key="config"
          className="flex-1 overflow-y-auto"
          initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
        >
          <AgentConfigPanel
            entityId={currentEntityId}
            entityType={mode as 'agent' | 'team'}
          />
        </motion.div>
      )}

      {tab === 'config' && isConfigurable && !currentEntityId && (
        <motion.div
          key="config-empty"
          className="flex flex-1 items-center justify-center p-6 text-center text-xs text-muted/40"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          Select an agent or team to configure
        </motion.div>
      )}

      {/* Memory tab */}
      {tab === 'memory' && isConfigurable && (
        <motion.div
          key="memory"
          className="flex-1 overflow-y-auto p-3 space-y-2"
          initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold uppercase text-muted">Stored Memories</span>
            <button
              onClick={() => {
                if (!currentEntityId) return
                setMemoriesLoading(true)
                setMemories([])
                const url = mode === 'agent'
                  ? `${endpointUrl}/memories?agent_id=${currentEntityId}`
                  : `${endpointUrl}/memories?team_id=${currentEntityId}`
                fetch(url, { headers: authToken ? { Authorization: `Bearer ${authToken}` } : {} })
                  .then((r) => r.ok ? r.json() : [])
                  .then((data) => { setMemories(Array.isArray(data) ? data : (data.memories ?? [])); setMemoriesLoading(false) })
                  .catch(() => setMemoriesLoading(false))
              }}
              className="rounded-lg p-1 text-muted hover:bg-accent hover:text-primary"
              title="Refresh memories"
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
              <p className="text-xs text-muted/30">Memories accumulate as the {mode} converses</p>
            </div>
          ) : (
            memories.map((mem, i) => (
              <motion.div
                key={mem.id || i}
                className="rounded-xl border border-accent bg-background p-3"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: i * 0.05 }}
              >
                <p className="text-xs text-primary leading-relaxed">{mem.memory || mem.summary || '—'}</p>
                {mem.topics && mem.topics.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {mem.topics.map((t) => (
                      <span key={t} className="rounded-full bg-accent px-2 py-0.5 text-[10px] text-muted">{t}</span>
                    ))}
                  </div>
                )}
                <div className="mt-1 text-[10px] text-muted/40">
                  {mem.updated_at ? dayjs(mem.updated_at).format('MMM D, HH:mm') : mem.created_at ? dayjs(mem.created_at).format('MMM D, HH:mm') : ''}
                </div>
              </motion.div>
            ))
          )}
        </motion.div>
      )}
      </AnimatePresence>

      {/* Details tab — existing read-only view */}
      {(tab === 'details' || !isConfigurable) && (
        <>

      {loading && (
        <div className="p-3 space-y-2">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-8 rounded-xl" />)}
        </div>
      )}

      {/* ── WORKFLOW DETAIL ── */}
      {!loading && mode === 'workflow' && workflowDetail && (
        <div className="p-3 space-y-4">
          <Section icon={<GitBranch className="size-3.5 text-brand" />} title="Workflow Details">
            <Card>
              <KV label="Workflow Id" value={workflowDetail.id} />
              <KV label="Workflow Name" value={workflowDetail.name} />
            </Card>
          </Section>

          {workflowDetail.steps && workflowDetail.steps.length > 0 && (
            <Section icon={<Layers className="size-3.5 text-brand" />} title={`Steps (${workflowDetail.steps.length})`}>
              <div className="rounded-xl border border-accent bg-background p-3">
                <StepTree steps={workflowDetail.steps} />
              </div>
            </Section>
          )}

          {workflowDetail.db_id && (
            <Section icon={<Database className="size-3.5 text-brand" />} title="Db Id">
              <Card><KV label="db_id" value={workflowDetail.db_id} /></Card>
            </Section>
          )}
        </div>
      )}

      {/* ── TEAM DETAIL ── */}
      {!loading && mode === 'team' && teamDetail && (
        <div className="p-3 space-y-4">
          <Section icon={<Users className="size-3.5 text-brand" />} title="Team Details">
            <Card>
              <KV label="Team Id" value={teamDetail.id} />
              <KV label="Team Name" value={teamDetail.name} />
            </Card>
          </Section>

          {teamDetail.members && teamDetail.members.length > 0 && (
            <Section icon={<Users className="size-3.5 text-brand" />} title={`Members (${teamDetail.members.length})`}>
              <div className="rounded-xl border border-accent bg-background p-3 space-y-2">
                {teamDetail.members.map((m) => (
                  <div key={m.id} className="flex items-center gap-2">
                    <Bot className="size-3 shrink-0 text-muted" />
                    <span className="text-xs font-medium text-primary">{m.name}</span>
                    {m.role && <span className="text-xs text-muted/50 truncate">{m.role.split(',')[0]}</span>}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {teamDetail.model && (
            <Section icon={<Cpu className="size-3.5 text-brand" />} title="Model">
              <Card>
                <KV label="model" value={teamDetail.model.model} />
                <KV label="name" value={teamDetail.model.name} />
                <KV label="provider" value={teamDetail.model.provider} />
              </Card>
            </Section>
          )}

          {teamDetail.tools?.tools && teamDetail.tools.tools.length > 0 && (
            <Section icon={<Wrench className="size-3.5 text-brand" />} title={`Tools (${teamDetail.tools.tools.length})`}>
              <div className="rounded-xl border border-accent bg-background p-3 space-y-1">
                {teamDetail.tools.tools.map((t, i) => (
                  <div key={i} className="text-xs font-mono text-primary">{t.name}</div>
                ))}
              </div>
            </Section>
          )}

          {teamDetail.sessions && (
            <Section icon={<Hash className="size-3.5 text-brand" />} title="Sessions">
              <Card>
                {teamDetail.sessions.session_table && <KV label="session_table" value={teamDetail.sessions.session_table} />}
                {teamDetail.sessions.add_history_to_context !== undefined && <KV label="add_history_to_context" value={String(teamDetail.sessions.add_history_to_context)} />}
                {teamDetail.sessions.num_history_runs !== undefined && <KV label="num_history_runs" value={String(teamDetail.sessions.num_history_runs)} />}
              </Card>
            </Section>
          )}

          {teamDetail.memory && (
            <Section icon={<MemoryStick className="size-3.5 text-brand" />} title="Memory">
              <Card>
                {teamDetail.memory.enable_agentic_memory !== undefined && <KV label="enable_agentic_memory" value={String(teamDetail.memory.enable_agentic_memory)} />}
                {teamDetail.memory.enable_user_memories !== undefined && <KV label="enable_user_memories" value={String(teamDetail.memory.enable_user_memories)} />}
              </Card>
            </Section>
          )}

          {teamDetail.default_tools && Object.keys(teamDetail.default_tools).length > 0 && (
            <Section icon={<Settings className="size-3.5 text-brand" />} title="Default Tools">
              <Card>
                {Object.entries(teamDetail.default_tools).map(([k, v]) => (
                  <KV key={k} label={k} value={String(v)} />
                ))}
              </Card>
            </Section>
          )}

          {teamDetail.system_message && (
            <Section icon={<MessageSquare className="size-3.5 text-brand" />} title="System Message">
              <Card>
                {teamDetail.system_message.add_datetime_to_context !== undefined && <KV label="add_datetime_to_context" value={String(teamDetail.system_message.add_datetime_to_context)} />}
                {teamDetail.system_message.markdown !== undefined && <KV label="markdown" value={String(teamDetail.system_message.markdown)} />}
                {teamDetail.system_message.instructions && (
                  <div className="mt-1">
                    <span className="text-xs text-muted/60">instructions:</span>
                    <pre className="mt-1 whitespace-pre-wrap rounded bg-accent/20 p-2 text-xs text-primary font-mono max-h-48 overflow-y-auto">{teamDetail.system_message.instructions}</pre>
                  </div>
                )}
              </Card>
            </Section>
          )}

          {teamDetail.streaming && (
            <Section icon={<Zap className="size-3.5 text-brand" />} title="Streaming">
              <Card>
                {teamDetail.streaming.stream_member_events !== undefined && <KV label="stream_member_events" value={String(teamDetail.streaming.stream_member_events)} />}
              </Card>
            </Section>
          )}
        </div>
      )}

      {/* ── AGENT DETAIL ── */}
      {!loading && mode === 'agent' && agentDetail && (
        <div className="p-3 space-y-4">
          <Section icon={<Bot className="size-3.5 text-brand" />} title="Agent Details">
            <Card>
              <KV label="Agent Id" value={agentDetail.id} />
              <KV label="Agent Name" value={agentDetail.name} />
            </Card>
          </Section>

          {agentDetail.model && (
            <Section icon={<Cpu className="size-3.5 text-brand" />} title="Model">
              <Card>
                <KV label="model" value={agentDetail.model.model} />
                <KV label="name" value={agentDetail.model.name} />
                <KV label="provider" value={agentDetail.model.provider} />
              </Card>
            </Section>
          )}

          {agentDetail.tools?.tools && agentDetail.tools.tools.length > 0 && (
            <Section icon={<Wrench className="size-3.5 text-brand" />} title={`Tools (${agentDetail.tools.tools.length})`}>
              <div className="rounded-xl border border-accent bg-background p-3 space-y-1">
                {agentDetail.tools.tools.map((t, i) => (
                  <div key={i} className="text-xs font-mono text-primary">{t.name}</div>
                ))}
              </div>
            </Section>
          )}

          {agentDetail.sessions && (
            <Section icon={<Hash className="size-3.5 text-brand" />} title="Sessions">
              <Card>
                {agentDetail.sessions.session_table && <KV label="session_table" value={agentDetail.sessions.session_table} />}
                {agentDetail.sessions.add_history_to_context !== undefined && <KV label="add_history_to_context" value={String(agentDetail.sessions.add_history_to_context)} />}
                {agentDetail.sessions.num_history_runs !== undefined && <KV label="num_history_runs" value={String(agentDetail.sessions.num_history_runs)} />}
              </Card>
            </Section>
          )}

          {agentDetail.knowledge && (
            <Section icon={<BookOpen className="size-3.5 text-brand" />} title="Knowledge">
              <Card>
                {agentDetail.knowledge.db_id && <KV label="db_id" value={agentDetail.knowledge.db_id} />}
                {agentDetail.knowledge.knowledge_table && <KV label="knowledge_table" value={agentDetail.knowledge.knowledge_table} />}
              </Card>
            </Section>
          )}

          {agentDetail.memory && (
            <Section icon={<MemoryStick className="size-3.5 text-brand" />} title="Memory">
              <Card>
                {agentDetail.memory.enable_agentic_memory !== undefined && <KV label="enable_agentic_memory" value={String(agentDetail.memory.enable_agentic_memory)} />}
                {agentDetail.memory.enable_user_memories !== undefined && <KV label="enable_user_memories" value={String(agentDetail.memory.enable_user_memories)} />}
              </Card>
            </Section>
          )}

          {agentDetail.default_tools && Object.keys(agentDetail.default_tools).length > 0 && (
            <Section icon={<Settings className="size-3.5 text-brand" />} title="Default Tools">
              <Card>
                {Object.entries(agentDetail.default_tools).map(([k, v]) => (
                  <KV key={k} label={k} value={String(v)} />
                ))}
              </Card>
            </Section>
          )}

          {agentDetail.system_message && (
            <Section icon={<MessageSquare className="size-3.5 text-brand" />} title="System Message">
              <Card>
                {agentDetail.system_message.add_datetime_to_context !== undefined && <KV label="add_datetime_to_context" value={String(agentDetail.system_message.add_datetime_to_context)} />}
                {agentDetail.system_message.markdown !== undefined && <KV label="markdown" value={String(agentDetail.system_message.markdown)} />}
                {agentDetail.system_message.instructions && (
                  <div className="mt-1">
                    <span className="text-xs text-muted/60">instructions:</span>
                    <pre className="mt-1 whitespace-pre-wrap rounded bg-accent/20 p-2 text-xs text-primary font-mono max-h-48 overflow-y-auto">{agentDetail.system_message.instructions}</pre>
                  </div>
                )}
              </Card>
            </Section>
          )}

          {agentDetail.streaming && (
            <Section icon={<Zap className="size-3.5 text-brand" />} title="Streaming">
              <Card>
                {agentDetail.streaming.stream_member_events !== undefined && <KV label="stream_member_events" value={String(agentDetail.streaming.stream_member_events)} />}
              </Card>
            </Section>
          )}
        </div>
      )}

      {/* No entity selected */}
      {!loading && !agentDetail && !teamDetail && !workflowDetail && (
        <div className="flex flex-1 items-center justify-center p-6 text-center text-xs text-muted/40">
          Select {mode === 'workflow' ? 'a workflow' : `an ${entityLabel.toLowerCase()}`} to see configuration
        </div>
      )}
        </>
      )}
      {/* End details tab wrapper */}

      {/* SSE Event Log */}
      <div className="mt-auto border-t border-accent/50 p-3 shrink-0">
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Zap className="size-3.5 text-brand" />
            <span className="text-xs font-semibold uppercase text-muted">Event Log</span>
          </div>
          {isStreaming && (
            <span className="flex items-center gap-1 rounded-full bg-positive/10 px-2 py-0.5 text-xs text-positive">
              <span className="size-1.5 rounded-full bg-positive animate-pulse inline-block" />
              Live
            </span>
          )}
        </div>
        {chatEvents.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-accent bg-background py-6 text-center">
            <Clock className="size-5 text-muted/20" />
            <p className="mt-1.5 text-xs text-muted/50">Events appear here during a run</p>
          </div>
        ) : (
          <div className="space-y-1 overflow-y-auto rounded-xl border border-accent bg-background p-2 max-h-52">
            {chatEvents.map((e, i) => (
              <div key={i} className="flex items-start gap-2 rounded-lg px-2 py-1.5 hover:bg-accent/30">
                <EventTypeIcon type={e.type} />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-primary truncate">{e.label}</div>
                  {e.detail && <div className="text-xs text-muted/60 truncate font-mono">{e.detail}</div>}
                </div>
                <div className="shrink-0 text-xs text-muted/40 font-mono">
                  {dayjs(e.ts).format('HH:mm:ss')}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main ChatPage
// ---------------------------------------------------------------------------
// Quick-prompt suggestions per agent / team
// ---------------------------------------------------------------------------

const AGENT_PROMPTS: Record<string, string[]> = {
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
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [showActivity, setShowActivity] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const { messages, isStreaming, sessionsData, isSessionsLoading, isEndpointLoading, isEndpointActive, rightPanelOpen, setRightPanelOpen, chatEvents } = useStore()
  const { handleStreamResponse } = useAIChatStreamHandler()
  const { clearChat } = useChatActions()
  const { getSessions, getSession } = useSessionLoader()
  const [agentId] = useQueryState('agent')
  const [teamId] = useQueryState('team')
  const [workflowId] = useQueryState('workflow')
  const [sessionId, setSessionId] = useQueryState('session')
  const [dbId] = useQueryState('db_id')
  const { mode } = useStore()

  useEffect(() => {
    if (!agentId && !teamId) return
    getSessions({ entityType: mode === 'workflow' ? null : mode, agentId, teamId, dbId })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId, teamId, mode, dbId])

  useEffect(() => {
    if (sessionId && (agentId || teamId)) {
      getSession({ entityType: mode === 'workflow' ? null : mode, agentId, teamId, dbId }, sessionId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

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
      imageFiles.forEach((f) => fd.append('files', f))
      await handleStreamResponse(fd)
    } else {
      await handleStreamResponse(fullMsg)
    }
  }

  const hasEntity = Boolean(agentId || teamId || workflowId)

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left session sidebar */}
      <aside className="flex w-52 shrink-0 flex-col gap-3 border-r border-accent/50 p-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium uppercase text-muted">Sessions</span>
          <button onClick={clearChat} className="rounded-lg p-1 text-muted hover:bg-accent hover:text-primary">
            <Plus className="size-3.5" />
          </button>
        </div>
        <ModeSelector />
        <EntitySelector />
        {mode !== 'workflow' && (
          <div className="flex-1 overflow-y-auto">
            {isSessionsLoading || isEndpointLoading ? (
              <div className="space-y-1">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-12 rounded-xl" />)}</div>
            ) : !sessionsData || sessionsData.length === 0 ? (
              <div className="py-8 text-center text-xs text-muted/50">No sessions yet</div>
            ) : (
              <div className="space-y-0.5">
                {sessionsData.map((s) => (
                  <SessionItem key={s.session_id} session={s} isSelected={sessionId === s.session_id} onClick={() => setSessionId(s.session_id)} />
                ))}
              </div>
            )}
          </div>
        )}
        {mode === 'workflow' && (
          <div className="flex-1 overflow-y-auto py-2">
            <p className="text-center text-xs text-muted/50">Run workflows via the chat panel</p>
          </div>
        )}
      </aside>

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
        {/* Toolbar */}
        <div className="flex items-center justify-between border-b border-accent/50 px-4 py-2">
          <div className="text-xs text-muted/60">
            {agentId || teamId || workflowId
              ? <span>Chatting with <span className="text-primary font-medium">{agentId || teamId || workflowId}</span></span>
              : <span>Select an agent, team, or workflow to start</span>}
          </div>
          <div className="flex items-center gap-2">
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
                    {(agentId || teamId || workflowId) ? 'New Session' : 'Quality Autopilot'}
                  </motion.p>
                  <motion.p
                    className="text-center text-[0.875rem] font-normal leading-[21px] tracking-[-0.02em] text-muted"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.22 }}
                  >
                    {!isEndpointActive ? 'Connect to your AgentOS endpoint to start chatting.'
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
                {messages.map((msg, i) => <MessageItem key={i} msg={msg} index={i} />)}
              </motion.div>
            )}
            </AnimatePresence>
          </StickToBottom.Content>
        </StickToBottom>

        {/* Inline activity log */}
        {showActivity && <ActivityLog events={chatEvents} isStreaming={isStreaming} />}

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
            <div className="flex w-full items-center justify-between gap-2 px-1 pb-1">
              {/* Left: attach + model switcher */}
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
                <ModelSwitcher />
              </div>

              {/* Right: entity chip + send */}
              <div className="flex items-center gap-2">
                {(agentId || teamId || workflowId) && (
                  <div className="flex h-8 max-w-[220px] items-center gap-2 rounded-md border border-accent/60 px-3">
                    <span className="truncate text-[0.75rem] uppercase tracking-[-0.02em] text-primary font-medium">
                      {agentId ?? teamId ?? workflowId}
                    </span>
                    <div className="shrink-0 rounded-[6px] border border-accent/60 p-[2px]">
                      <Icon type="agno" size="xxs" />
                    </div>
                  </div>
                )}
                <button
                  onClick={handleSubmit}
                  disabled={(!inputMessage.trim() && attachedFiles.length === 0) || isStreaming || !hasEntity}
                  className="inline-flex size-8 shrink-0 items-center justify-center rounded-sm bg-primary text-background shadow-sm transition-colors hover:bg-primary/80 disabled:pointer-events-none disabled:opacity-50"
                >
                  <ArrowUp className="size-[10.67px]" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right panel — collapsible */}
      {rightPanelOpen && (
        <aside className="flex w-80 shrink-0 flex-col border-l border-accent/50 bg-primaryAccent overflow-y-auto">
          <RightPanel agentId={agentId} teamId={teamId} workflowId={workflowId} sessionId={sessionId} />
        </aside>
      )}
    </div>
  )
}
