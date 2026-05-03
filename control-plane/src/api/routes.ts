export const APIRoutes = {
  // ── Auth ─────────────────────────────────────────────────────────────────
  AuthRegister:      (base: string) => `${base}/auth/register`,
  AuthLogin:         (base: string) => `${base}/auth/login`,
  AuthLogout:        (base: string) => `${base}/auth/logout`,
  AuthMe:            (base: string) => `${base}/auth/me`,
  AuthInvite:        (base: string) => `${base}/auth/invite`,
  AuthValidateInvite:(base: string, token: string) => `${base}/auth/invite/${encodeURIComponent(token)}`,
  AuthAcceptInvite:  (base: string) => `${base}/auth/accept-invite`,
  AuthUsers:         (base: string) => `${base}/auth/users`,
  AuthDeactivate:    (base: string, userId: string) => `${base}/auth/users/${userId}`,
  AuthChangeRole:    (base: string, userId: string) => `${base}/auth/users/${userId}/role`,
  AuthForgotPassword:(base: string) => `${base}/auth/forgot-password`,
  AuthResetPassword: (base: string) => `${base}/auth/reset-password`,
  AuthChangePassword:(base: string) => `${base}/auth/change-password`,
  AuthPermissions:   (base: string) => `${base}/auth/permissions`,
  AuthOrgLookup:     (base: string, name: string) => `${base}/auth/org-lookup?name=${encodeURIComponent(name)}`,
  AuthCreateOrg:     (base: string) => `${base}/auth/org`,
  AuthInvites:       (base: string) => `${base}/auth/invites`,
  AuthCancelInvite:  (base: string, token: string) => `${base}/auth/invites/${encodeURIComponent(token)}`,

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
  CancelAgentRun: (base: string, aid: string, rid: string) => `${base}/agents/${aid}/runs/${rid}/cancel`,

  // ── Teams ───────────────────────────────────────────────────────────────
  GetTeams:    (base: string) => `${base}/teams`,
  GetTeam:     (base: string, id: string) => `${base}/teams/${id}`,
  TeamRun:     (base: string, id: string) => `${base}/teams/${id}/runs`,
  CancelTeamRun: (base: string, tid: string, rid: string) => `${base}/teams/${tid}/runs/${rid}/cancel`,
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
  KnowledgeContentById: (base: string, id: string, params?: Record<string, string>) => {
    const url = new URL(`${base}/knowledge/content/${id}`)
    if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
    return url.toString()
  },
  KnowledgeSources:     (base: string, kid: string) => `${base}/knowledge/${kid}/sources`,
  KnowledgeSourceFiles: (base: string, kid: string, sid: string) => `${base}/knowledge/${kid}/sources/${sid}/files`,
  RemoteContent:        (base: string) => `${base}/knowledge/remote-content`,

  // ── Memory ───────────────────────────────────────────────────────────────
  GetMemories:    (base: string) => `${base}/memories`,
  GetMemory:      (base: string, id: string) => `${base}/memories/${id}`,
  MemoryTopics:   (base: string) => `${base}/memory_topics`,
  UserMemoryStats: (base: string) => `${base}/user_memory_stats`,
  OptimizeMemories: (base: string) => `${base}/optimize-memories`,

  // ── Culture ───────────────────────────────────────────────────────────────
  GetCulture:           (base: string) => `${base}/culture`,
  GetCultureEntry:      (base: string, id: string) => `${base}/culture/${id}`,
  CreateCultureEntry:   (base: string) => `${base}/culture`,
  DeleteCultureEntry:   (base: string, id: string) => `${base}/culture/${id}`,
  GetCultureCategories: (base: string) => `${base}/culture/categories`,

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

  // ── Profile ───────────────────────────────────────────────────────────────
  GetProfile:      (base: string) => `${base}/profile`,
  UpdateProfile:   (base: string) => `${base}/profile`,

  // ── Automation Health ─────────────────────────────────────────────────────
  AutomationHealth:  (base: string) => `${base}/automation/health`,
  AutomationReport:  (base: string, raw?: boolean) => `${base}/automation/report${raw ? '?raw=true' : ''}`,
  AutomationRun:     (base: string) => `${base}/automation/run`,
  AutomationTraces:  (base: string) => `${base}/automation/traces`,
  AutomationSync:    (base: string) => `${base}/automation/sync`,
  AutomationRunStream: (base: string, tags: string, useDocker: boolean, timeoutSecs: number) => {
    const wsBase = base.replace(/^http/, 'ws')
    const p = new URLSearchParams()
    if (tags) p.set('tags', tags)
    if (useDocker) p.set('use_docker', 'true')
    if (timeoutSecs) p.set('timeout_seconds', String(timeoutSecs))
    const qs = p.toString()
    return qs ? `${wsBase}/automation/run/stream?${qs}` : `${wsBase}/automation/run/stream`
  },
  AutomationFileContent:    (base: string, path: string) => `${base}/automation/files/content?path=${encodeURIComponent(path)}`,
  AutomationEditRequests:   (base: string, status?: string) => `${base}/automation/files/edit-requests${status ? `?status=${status}` : ''}`,
  AutomationEditRequest:    (base: string) => `${base}/automation/files/edit-request`,
  AutomationApproveEdit:    (base: string, id: string) => `${base}/automation/files/edit-requests/${id}/approve`,
  AutomationRejectEdit:     (base: string, id: string) => `${base}/automation/files/edit-requests/${id}/reject`,

  // ── RTM ──────────────────────────────────────────────────────────────────
  RTM:               (base: string, ticket?: string, tag?: string) =>
    `${base}/rtm${ticket ? `?ticket=${encodeURIComponent(ticket)}` : tag ? `?tag=${encodeURIComponent(tag)}` : ''}`,
  RTMSearch:         (base: string, q: string, limit?: number) =>
    `${base}/rtm/search?q=${encodeURIComponent(q)}${limit ? `&limit=${limit}` : ''}`,
  RTMByTicket:       (base: string, key: string) => `${base}/rtm/ticket/${encodeURIComponent(key)}`,
  RTMExplain:        (base: string) => `${base}/rtm/explain`,

  // ── Organization ──────────────────────────────────────────────────────────
  GetOrganization:    (base: string) => `${base}/organization`,
  UpdateOrganization: (base: string) => `${base}/organization`,
  InviteMember:       (base: string) => `${base}/organization/members`,
  RemoveMember:       (base: string, email: string) => `${base}/organization/members/${encodeURIComponent(email)}`,
  DeleteOrganization: (base: string) => `${base}/organization`,
}
