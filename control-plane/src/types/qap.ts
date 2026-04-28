// QAP-specific types for the Quality Autopilot control plane

export type PhaseStatus = 'done' | 'active' | 'locked'

export interface PhaseGate {
  phase: string
  label: string
  gate: string
  status: PhaseStatus
}

export type AgentHealthStatus = 'healthy' | 'degraded' | 'offline'

export interface AgentHealth {
  id: string
  name: string
  squad: string
  status: AgentHealthStatus
  lastRun?: string
}

export type WorkflowStatus = 'idle' | 'running' | 'completed' | 'failed'

export interface WorkflowRun {
  workflow_id: string
  workflow_name: string
  run_id: string
  status: WorkflowStatus
  started_at: string
  completed_at?: string
  input?: string
  output?: string
  error?: string
}

export interface GherkinSpec {
  id: string
  ticket_id: string
  feature_file: string
  feature_content: string
  status: 'pending' | 'approved' | 'rejected'
  created_at: string
  confidence?: number
  rejection_reasons?: string[]
}

export interface HealingPatch {
  id: string
  test_name: string
  trace_id: string
  file_path: string
  old_locator: string
  new_locator: string
  diff: string
  verification_passes: number
  logic_changed: boolean
  status: 'pending' | 'approved' | 'rejected' | 'applied'
  created_at: string
  confidence?: number
}

export interface RegressionMetric {
  date: string
  total: number
  passed: number
  failed: number
  healed: number
  autonomous_rate: number
}

export interface PipelineRun {
  id: string
  name: string
  status: 'success' | 'failure' | 'running' | 'cancelled'
  started_at: string
  completed_at?: string
  branch?: string
  commit?: string
  url?: string
}
