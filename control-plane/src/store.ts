import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

import { AgentDetails, SessionEntry, TeamDetails, WorkflowDetails, type ChatMessage } from '@/types/os'

export interface ChatEvent {
  type: 'tool_start' | 'tool_done' | 'reasoning' | 'content' | 'run_start' | 'run_done' | 'error' | 'memory' | 'debug'
  label: string
  ts: number
  detail?: string
}

// Per-agent/team config overrides applied at run time
export interface AgentConfigOverride {
  name?: string
  instructions?: string
  model_id?: string
  model_provider?: string
  model_base_url?: string
  model_api_key?: string
  num_history_runs?: number
  add_history_to_context?: boolean
  session_state?: Record<string, unknown>
  add_session_state_to_context?: boolean
  enable_agentic_state?: boolean
  enable_agentic_memory?: boolean
  update_memory_on_run?: boolean
  metadata?: Record<string, unknown>
  extra_config?: Record<string, unknown>
}

interface Store {
  hydrated: boolean
  setHydrated: () => void
  streamingErrorMessage: string
  setStreamingErrorMessage: (streamingErrorMessage: string) => void
  endpoints: {
    endpoint: string
    id__endpoint: string
  }[]
  setEndpoints: (
    endpoints: {
      endpoint: string
      id__endpoint: string
    }[]
  ) => void
  isStreaming: boolean
  setIsStreaming: (isStreaming: boolean) => void
  isEndpointActive: boolean
  setIsEndpointActive: (isActive: boolean) => void
  isEndpointLoading: boolean
  setIsEndpointLoading: (isLoading: boolean) => void
  messages: ChatMessage[]
  setMessages: (
    messages: ChatMessage[] | ((prevMessages: ChatMessage[]) => ChatMessage[])
  ) => void
  chatInputRef: React.RefObject<HTMLTextAreaElement | null>
  selectedEndpoint: string
  setSelectedEndpoint: (selectedEndpoint: string) => void
  authToken: string
  setAuthToken: (authToken: string) => void
  currentUser: { user_id: string; email: string; name: string; org_id: string; role: string } | null
  setCurrentUser: (user: { user_id: string; email: string; name: string; org_id: string; role: string } | null) => void
  agents: AgentDetails[]
  setAgents: (agents: AgentDetails[]) => void
  teams: TeamDetails[]
  setTeams: (teams: TeamDetails[]) => void
  workflows: WorkflowDetails[]
  setWorkflows: (workflows: WorkflowDetails[]) => void
  selectedModel: string
  setSelectedModel: (model: string) => void
  mode: 'agent' | 'team' | 'workflow'
  setMode: (mode: 'agent' | 'team' | 'workflow') => void
  sessionsData: SessionEntry[] | null
  setSessionsData: (
    sessionsData:
      | SessionEntry[]
      | ((prevSessions: SessionEntry[] | null) => SessionEntry[] | null)
  ) => void
  isSessionsLoading: boolean
  setIsSessionsLoading: (isSessionsLoading: boolean) => void
  chatEvents: ChatEvent[]
  addChatEvent: (e: ChatEvent) => void
  clearChatEvents: () => void
  rightPanelOpen: boolean
  setRightPanelOpen: (open: boolean) => void
  navCollapsed: boolean
  setNavCollapsed: (collapsed: boolean) => void
  envSettings: Record<string, string>
  setEnvSettings: (settings: Record<string, string>) => void
  activeProvider: string
  setActiveProvider: (provider: string) => void
  activeModelId: string
  setActiveModelId: (modelId: string) => void
  // Active run tracking — used by the Stop button
  activeRunId: string | null
  setActiveRunId: (runId: string | null) => void
  // Per-entity config overrides — keyed by agent/team ID
  agentOverrides: Record<string, AgentConfigOverride>
  setAgentOverride: (id: string, override: AgentConfigOverride) => void
  clearAgentOverride: (id: string) => void
  // Approval pause state — true while the run is paused waiting for human input
  isPaused: boolean
  setIsPaused: (isPaused: boolean) => void
  // Sidebar pending-request badge counts
  pendingCounts: { approvals: number; specReview: number; healing: number }
  setPendingCounts: (patch: Partial<{ approvals: number; specReview: number; healing: number }>) => void
}

export const useStore = create<Store>()(
  persist(
    (set) => ({
      hydrated: false,
      setHydrated: () => set({ hydrated: true }),
      streamingErrorMessage: '',
      setStreamingErrorMessage: (streamingErrorMessage) =>
        set(() => ({ streamingErrorMessage })),
      endpoints: [],
      setEndpoints: (endpoints) => set(() => ({ endpoints })),
      isStreaming: false,
      setIsStreaming: (isStreaming) => set(() => ({ isStreaming })),
      isEndpointActive: false,
      setIsEndpointActive: (isActive) => set(() => ({ isEndpointActive: isActive })),
      isEndpointLoading: true,
      setIsEndpointLoading: (isLoading) => set(() => ({ isEndpointLoading: isLoading })),
      messages: [],
      setMessages: (messages) =>
        set((state) => ({
          messages: typeof messages === 'function' ? messages(state.messages) : messages
        })),
      chatInputRef: { current: null },
      selectedEndpoint:
        process.env.NEXT_PUBLIC_AGENTOS_URL ||
        (typeof window !== 'undefined'
          ? `http://${window.location.hostname}:8000`
          : 'http://localhost:8000'),

      setSelectedEndpoint: (selectedEndpoint) => set(() => ({ selectedEndpoint })),
      authToken: '',
      setAuthToken: (authToken) => set(() => ({ authToken })),
      currentUser: null,
      setCurrentUser: (currentUser) => set(() => ({ currentUser })),
      agents: [],
      setAgents: (agents) => set({ agents }),
      teams: [],
      setTeams: (teams) => set({ teams }),
      workflows: [],
      setWorkflows: (workflows) => set({ workflows }),
      selectedModel: '',
      setSelectedModel: (selectedModel) => set(() => ({ selectedModel })),
      mode: 'agent',
      setMode: (mode) => set(() => ({ mode })),
      sessionsData: null,
      setSessionsData: (sessionsData) =>
        set((state) => ({
          sessionsData:
            typeof sessionsData === 'function'
              ? sessionsData(state.sessionsData)
              : sessionsData
        })),
      isSessionsLoading: false,
      setIsSessionsLoading: (isSessionsLoading) => set(() => ({ isSessionsLoading })),
      chatEvents: [],
      addChatEvent: (e) => set((s) => ({ chatEvents: [...s.chatEvents.slice(-199), e] })),
      clearChatEvents: () => set({ chatEvents: [] }),
      rightPanelOpen: true,
      setRightPanelOpen: (open) => set({ rightPanelOpen: open }),
      navCollapsed: false,
      setNavCollapsed: (collapsed) => set({ navCollapsed: collapsed }),
      envSettings: {},
      setEnvSettings: (envSettings) => set({ envSettings }),
      activeProvider: 'kilo',
      setActiveProvider: (activeProvider) => set({ activeProvider }),
      activeModelId: 'kilo-auto/free',
      setActiveModelId: (activeModelId) => set({ activeModelId }),
      activeRunId: null,
      setActiveRunId: (activeRunId) => set({ activeRunId }),
      agentOverrides: {},
      setAgentOverride: (id, override) => set((s) => ({ agentOverrides: { ...s.agentOverrides, [id]: override } })),
      clearAgentOverride: (id) => set((s) => {
        const next = { ...s.agentOverrides }
        delete next[id]
        return { agentOverrides: next }
      }),
      isPaused: false,
      setIsPaused: (isPaused) => set(() => ({ isPaused })),
      pendingCounts: { approvals: 0, specReview: 0, healing: 0 },
      setPendingCounts: (patch) => set((s) => ({ pendingCounts: { ...s.pendingCounts, ...patch } })),
    }),

    {
      name: 'qap-control-plane-store',
      storage: createJSONStorage(() => localStorage),
      onRehydrateStorage: () => (state) => {
        state?.setHydrated()
        // If the UI is accessed from a non-localhost host (e.g. 192.168.x.x)
        // but localStorage still holds the default localhost URL, update it
        // automatically so the backend URL matches the current access host.
        if (
          state &&
          typeof window !== 'undefined' &&
          window.location.hostname !== 'localhost' &&
          window.location.hostname !== '127.0.0.1'
        ) {
          const stored = state.selectedEndpoint
          if (stored.includes('localhost') || stored.includes('127.0.0.1')) {
            const port = new URL(stored).port || '8000'
            state.setSelectedEndpoint(
              `http://${window.location.hostname}:${port}`
            )
          }
        }
      },
      partialize: (state) => ({
        selectedEndpoint: state.selectedEndpoint,
        authToken: state.authToken,
        currentUser: state.currentUser,
        mode: state.mode,
        navCollapsed: state.navCollapsed,
        rightPanelOpen: state.rightPanelOpen,
        envSettings: state.envSettings,
        activeProvider: state.activeProvider,
        activeModelId: state.activeModelId,
        agentOverrides: state.agentOverrides,
      })
    }
  )
)
