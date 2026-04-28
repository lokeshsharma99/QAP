export interface ToolCall {
  role: 'user' | 'tool' | 'system' | 'assistant'
  content: string | null
  tool_call_id: string
  tool_name: string
  tool_args: Record<string, string>
  tool_call_error: boolean
  metrics: {
    time: number
  }
  created_at: number
}

export interface ReasoningSteps {
  title: string
  action?: string
  result: string
  reasoning: string
  confidence?: number
  next_action?: string
}

export interface ReasoningMessage {
  role: string
  content: string
  thinking?: string
  redacted_thinking?: string
  created_at: number
}

export interface ReasoningStepProps {
  index: number
  stepTitle: string
}

export interface ReasoningProps {
  reasoning: ReasoningSteps[]
}

export type ToolCallProps = {
  tools: ToolCall
}

interface ModelMessage {
  content: string | null
  context?: MessageContext[]
  created_at: number
  metrics?: {
    time: number
    prompt_tokens: number
    input_tokens: number
    completion_tokens: number
    output_tokens: number
  }
  name: string | null
  role: string
  tool_args?: unknown
  tool_call_id: string | null
  tool_calls: Array<{
    function: {
      arguments: string
      name: string
    }
    id: string
    type: string
  }> | null
}

export interface Model {
  name: string
  model: string
  provider: string
}

export interface AgentDetails {
  id: string
  agent_id: string
  name: string
  description: string
  model: Model
  storage?: boolean
  db_id?: string
}

export interface TeamDetails {
  id: string
  team_id: string
  name: string
  description: string
  model: Model
  storage?: boolean
  db_id?: string
}

export interface WorkflowDetails {
  id: string
  name: string
  description?: string
  db_id?: string
  is_factory?: boolean
  is_component?: boolean
}

// ---------------------------------------------------------------------------
// Rich detail types (fetched from GET /agents/:id, /teams/:id, /workflows/:id)
// ---------------------------------------------------------------------------

export interface ToolParam {
  name: string
  description?: string
  parameters?: Record<string, unknown>
  requires_confirmation?: boolean
}

export interface ToolsDetail {
  tools?: ToolParam[]
}

export interface SessionsDetail {
  session_table?: string
  add_history_to_context?: boolean
  num_history_runs?: number
}

export interface MemoryDetail {
  enable_agentic_memory?: boolean
  enable_user_memories?: boolean
  model?: Model
}

export interface KnowledgeDetail {
  db_id?: string
  knowledge_table?: string
}

export interface SystemMessageDetail {
  instructions?: string
  markdown?: boolean
  add_datetime_to_context?: boolean
}

export interface StreamingDetail {
  stream_member_events?: boolean
}

export interface DefaultToolsDetail {
  [key: string]: boolean | undefined
}

export interface MemberSummary {
  id: string
  name: string
  role?: string
  db_id?: string
}

export interface AgentFullDetail extends AgentDetails {
  tools?: ToolsDetail
  sessions?: SessionsDetail
  knowledge?: KnowledgeDetail
  memory?: MemoryDetail
  system_message?: SystemMessageDetail
  default_tools?: DefaultToolsDetail
  streaming?: StreamingDetail
}

export interface TeamFullDetail extends TeamDetails {
  mode?: string
  members?: MemberSummary[]
  tools?: ToolsDetail
  sessions?: SessionsDetail
  memory?: MemoryDetail
  default_tools?: DefaultToolsDetail
  system_message?: SystemMessageDetail
  streaming?: StreamingDetail
}

export interface WorkflowStep {
  name: string
  type: 'Step' | 'Condition' | 'Router' | string
  steps?: WorkflowStep[]
}

export interface WorkflowFullDetail extends WorkflowDetails {
  steps?: WorkflowStep[]
}

interface MessageContext {
  query: string
  docs?: Array<Record<string, object>>
  time?: number
}

export interface SessionEntry {
  session_id: string
  created_at: number
  updated_at?: number
}

export type Sessions = {
  data: SessionEntry[]
}

// ---------------------------------------------------------------------------
// Sessions Page types
// ---------------------------------------------------------------------------
export interface SessionSchema {
  session_id: string
  session_name: string
  session_state?: Record<string, unknown>
  created_at?: string
  updated_at?: string
  session_type?: 'agent' | 'team' | 'workflow'
  user_id?: string
  agent_id?: string
  team_id?: string
  workflow_id?: string
  session_summary?: Record<string, unknown>
  metrics?: Record<string, unknown>
  total_tokens?: number
  metadata?: Record<string, unknown>
}

export interface PaginationMeta {
  page: number
  limit: number
  total_pages: number
  total_count: number
  search_time_ms: number
}

export interface PaginatedSessions {
  data: SessionSchema[]
  meta: PaginationMeta
}

export interface ChatEntry {
  run_id?: string
  run_input?: string
  messages?: ModelMessage[]
  tools?: ToolCall[]
  extra_data?: AgentExtraData
  created_at: number
}

export enum RunEvent {
  RunStarted = 'RunStarted',
  RunContent = 'RunContent',
  RunCompleted = 'RunCompleted',
  RunError = 'RunError',
  RunOutput = 'RunOutput',
  UpdatingMemory = 'UpdatingMemory',
  ToolCallStarted = 'ToolCallStarted',
  ToolCallCompleted = 'ToolCallCompleted',
  MemoryUpdateStarted = 'MemoryUpdateStarted',
  MemoryUpdateCompleted = 'MemoryUpdateCompleted',
  ReasoningStarted = 'ReasoningStarted',
  ReasoningStep = 'ReasoningStep',
  ReasoningCompleted = 'ReasoningCompleted',
  RunCancelled = 'RunCancelled',
  RunPaused = 'RunPaused',
  RunContinued = 'RunContinued',
  // Team Events
  TeamRunStarted = 'TeamRunStarted',
  TeamRunContent = 'TeamRunContent',
  TeamRunCompleted = 'TeamRunCompleted',
  TeamRunError = 'TeamRunError',
  TeamRunCancelled = 'TeamRunCancelled',
  TeamToolCallStarted = 'TeamToolCallStarted',
  TeamToolCallCompleted = 'TeamToolCallCompleted',
  TeamReasoningStarted = 'TeamReasoningStarted',
  TeamReasoningStep = 'TeamReasoningStep',
  TeamReasoningCompleted = 'TeamReasoningCompleted',
  TeamMemoryUpdateStarted = 'TeamMemoryUpdateStarted',
  TeamMemoryUpdateCompleted = 'TeamMemoryUpdateCompleted',
  // Workflow Events
  WorkflowStarted = 'WorkflowStarted',
  WorkflowCompleted = 'WorkflowCompleted',
  WorkflowError = 'WorkflowError',
  WorkflowCancelled = 'WorkflowCancelled',
  StepStarted = 'StepStarted',
  StepCompleted = 'StepCompleted',
  StepError = 'StepError'
}

export interface ResponseAudio {
  id?: string
  content?: string
  transcript?: string
  channels?: number
  sample_rate?: number
}

export interface NewRunResponse {
  status: 'RUNNING' | 'PAUSED' | 'CANCELLED'
}

interface ImageData {
  url?: string
  revised_prompt?: string
}
interface VideoData {
  url?: string
}
interface AudioData {
  base64_audio?: string
  mime_type?: string
}

interface AgentExtraData {
  reasoning_messages?: ReasoningMessage[]
  reasoning_steps?: ReasoningSteps[]
  references?: unknown[]
}

export interface RunResponseContent {
  content?: string | object
  content_type: string
  context?: MessageContext[]
  event: RunEvent
  event_data?: object
  messages?: ModelMessage[]
  metrics?: object
  model?: string
  run_id?: string
  agent_id?: string
  session_id?: string
  tool?: ToolCall
  tools?: Array<ToolCall>
  created_at: number
  extra_data?: AgentExtraData
  images?: ImageData[]
  videos?: VideoData[]
  audio?: AudioData[]
  response_audio?: ResponseAudio
}

export type RunResponse = RunResponseContent

export interface ChatMessage {
  role: 'user' | 'agent'
  content: string
  tool_calls?: ToolCall[]
  streamingError?: boolean
  created_at: number
  images?: ImageData[]
  videos?: VideoData[]
  audio?: AudioData[]
  response_audio?: ResponseAudio
  extra_data?: AgentExtraData
}
