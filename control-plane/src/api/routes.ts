export const APIRoutes = {
  // ── Core ────────────────────────────────────────────────────────────────
  Status:      (base: string) => `${base}/health`,
  Info:        (base: string) => `${base}/info`,
  Models:      (base: string) => `${base}/models`,
  Metrics:        (base: string, start?: string, end?: string) => {
    const p = new URLSearchParams()
    if (start) p.set('starting_date', start)
    if (end)   p.set('ending_date', end)
    const qs = p.toString()
    return qs ? `${base}/metrics?${qs}` : `${base}/metrics`
  },
  MetricsRefresh: (base: string) => `${base}/metrics/refresh`,
  Registry:    (base: string) => `${base}/registry`,
  Components:  (base: string) => `${base}/components`,

  // ── Agents ──────────────────────────────────────────────────────────────
  GetAgents:   (base: string) => `${base}/agents`,
  GetAgent:    (base: string, id: string) => `${base}/agents/${id}`,
  AgentRun:    (base: string) => `${base}/agents/{agent_id}/runs`,

  // ── Teams ───────────────────────────────────────────────────────────────
  GetTeams:    (base: string) => `${base}/teams`,
  GetTeam:     (base: string, id: string) => `${base}/teams/${id}`,
  TeamRun:     (base: string, id: string) => `${base}/teams/${id}/runs`,
  DeleteTeamSession: (base: string, tid: string, sid: string) => `${base}/v1/teams/${tid}/sessions/${sid}`,

  // ── Sessions ─────────────────────────────────────────────────────────────
  GetSessions:   (base: string) => `${base}/sessions`,
  CreateSession: (base: string) => `${base}/sessions`,
  GetSession:    (base: string, sid: string) => `${base}/sessions/${sid}/runs`,
  GetSessionRun: (base: string, sid: string, rid: string) => `${base}/sessions/${sid}/runs/${rid}`,
  DeleteSession: (base: string, sid: string) => `${base}/sessions/${sid}`,

  // ── Traces ───────────────────────────────────────────────────────────────
  GetTraces:      (base: string) => `${base}/traces`,
  GetTrace:       (base: string, id: string) => `${base}/traces/${id}`,
  SearchTraces:   (base: string) => `${base}/traces/search`,
  TraceStats:     (base: string) => `${base}/trace_session_stats`,

  // ── Knowledge ────────────────────────────────────────────────────────────
  KnowledgeConfig:      (base: string) => `${base}/knowledge/config`,
  KnowledgeContent:     (base: string) => `${base}/knowledge/content`,
  KnowledgeSearch:      (base: string) => `${base}/knowledge/search`,
  KnowledgeContentById: (base: string, id: string) => `${base}/knowledge/content/${id}`,
  KnowledgeSources:     (base: string, kid: string) => `${base}/knowledge/${kid}/sources`,
  KnowledgeSourceFiles: (base: string, kid: string, sid: string) => `${base}/knowledge/${kid}/sources/${sid}/files`,
  RemoteContent:        (base: string) => `${base}/knowledge/remote-content`,

  // ── Memory ───────────────────────────────────────────────────────────────
  GetMemories:    (base: string) => `${base}/memories`,
  GetMemory:      (base: string, id: string) => `${base}/memories/${id}`,
  MemoryTopics:   (base: string) => `${base}/memory_topics`,
  UserMemoryStats: (base: string) => `${base}/user_memory_stats`,
  OptimizeMemories: (base: string) => `${base}/optimize-memories`,

  // ── Approvals ────────────────────────────────────────────────────────────
  GetApprovals:    (base: string) => `${base}/approvals`,
  ApprovalCount:   (base: string) => `${base}/approvals/count`,
  GetApproval:     (base: string, id: string) => `${base}/approvals/${id}`,
  ResolveApproval: (base: string, id: string) => `${base}/approvals/${id}/resolve`,
  ApprovalStatus:  (base: string, id: string) => `${base}/approvals/${id}/status`,

  // ── Workflows ────────────────────────────────────────────────────────────
  GetWorkflows:         (base: string) => `${base}/workflows`,
  GetWorkflow:          (base: string, id: string) => `${base}/workflows/${id}`,
  WorkflowRun:          (base: string, id: string) => `${base}/workflows/${id}/runs`,
  GetWorkflowRuns:      (base: string, id: string) => `${base}/workflows/${id}/runs`,
  GetWorkflowRunStatus: (base: string, wid: string, rid: string) => `${base}/workflows/${wid}/runs/${rid}`,
  ContinueWorkflowRun:  (base: string, wid: string, rid: string) => `${base}/workflows/${wid}/runs/${rid}/continue`,
  CancelWorkflowRun:    (base: string, wid: string, rid: string) => `${base}/workflows/${wid}/runs/${rid}/cancel`,

  // ── Agent / Team Config ───────────────────────────────────────────────────
  GetAgentConfig:   (base: string, id: string) => `${base}/agents/${id}/config`,
  PatchAgentConfig: (base: string, id: string) => `${base}/agents/${id}/config`,
  GetTeamConfig:    (base: string, id: string) => `${base}/teams/${id}/config`,
  PatchTeamConfig:  (base: string, id: string) => `${base}/teams/${id}/config`,

  // ── Agent-scoped Memories ────────────────────────────────────────────────
  GetAgentMemories: (base: string, agentId: string) => `${base}/memories?agent_id=${agentId}`,

  // ── Scheduler ────────────────────────────────────────────────────────────
  GetSchedules:     (base: string) => `${base}/schedules`,
  CreateSchedule:   (base: string) => `${base}/schedules`,
  GetSchedule:      (base: string, id: string) => `${base}/schedules/${id}`,
  UpdateSchedule:   (base: string, id: string) => `${base}/schedules/${id}`,
  DeleteSchedule:   (base: string, id: string) => `${base}/schedules/${id}`,
  EnableSchedule:   (base: string, id: string) => `${base}/schedules/${id}/enable`,
  DisableSchedule:  (base: string, id: string) => `${base}/schedules/${id}/disable`,
  TriggerSchedule:  (base: string, id: string) => `${base}/schedules/${id}/trigger`,
  GetScheduleRuns:  (base: string, id: string) => `${base}/schedules/${id}/runs`,

  // ── Evals ────────────────────────────────────────────────────────────────
  GetEvalRuns:    (base: string) => `${base}/eval-runs`,
  GetEvalRun:     (base: string, id: string) => `${base}/eval-runs/${id}`,
  CreateEvalRun:  (base: string) => `${base}/eval-runs`,
  DeleteEvalRun:  (base: string, id: string) => `${base}/eval-runs/${id}`,

  // ── Traces (extended) ────────────────────────────────────────────────────
  TraceFilterSchema: (base: string) => `${base}/traces/filter-schema`,
  SearchTracesDSL:   (base: string) => `${base}/traces/search`,
}
