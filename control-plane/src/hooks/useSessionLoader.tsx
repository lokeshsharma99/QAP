import { useCallback } from 'react'
import { getSessionAPI, getAllSessionsAPI } from '@/api/os'
import { useStore } from '../store'
import { toast } from 'sonner'
import { ChatMessage, ToolCall, ReasoningMessage, ChatEntry } from '@/types/os'
import { getJsonMarkdown } from '@/lib/utils'

interface LoaderArgs {
  entityType: 'agent' | 'team' | 'workflow' | null
  agentId?: string | null
  teamId?: string | null
  workflowId?: string | null
  dbId: string | null
}

const useSessionLoader = () => {
  const setMessages = useStore((state) => state.setMessages)
  const selectedEndpoint = useStore((state) => state.selectedEndpoint)
  const authToken = useStore((state) => state.authToken)
  const setIsSessionsLoading = useStore((state) => state.setIsSessionsLoading)
  const setSessionsData = useStore((state) => state.setSessionsData)

  const getSessions = useCallback(
    async ({ entityType, agentId, teamId, workflowId, dbId }: LoaderArgs) => {
      const selectedId = entityType === 'workflow' ? workflowId : entityType === 'agent' ? agentId : teamId
      if (!selectedEndpoint || !entityType || !selectedId || !dbId) return

      try {
        setIsSessionsLoading(true)
        const sessions = await getAllSessionsAPI(
          selectedEndpoint,
          entityType,
          selectedId,
          dbId,
          authToken
        )
        setSessionsData(sessions.data ?? [])
      } catch {
        toast.error('Error loading sessions')
        setSessionsData([])
      } finally {
        setIsSessionsLoading(false)
      }
    },
    [selectedEndpoint, authToken, setSessionsData, setIsSessionsLoading]
  )

  const getSession = useCallback(
    async ({ entityType, agentId, teamId, workflowId, dbId }: LoaderArgs, sessionId: string) => {
      const selectedId = entityType === 'workflow' ? workflowId : entityType === 'agent' ? agentId : teamId
      if (!selectedEndpoint || !sessionId || !entityType || !selectedId) return

      try {
        const response = await getSessionAPI(
          selectedEndpoint,
          entityType,
          sessionId,
          dbId || undefined,
          authToken
        )
        if (response) {
          const runs: ChatEntry[] = Array.isArray(response)
            ? response
            : response.memory?.runs || response.memory?.chats || []

          // Collect all user-role message contents from run.messages arrays.
          // These are internal messages (e.g. team leader→member delegations) that Agno
          // stores as `role: 'user'` entries within a run's messages list.
          // Any run_input that also appears here is a synthetic delegation, not a human turn.
          const internalUserContents = new Set<string>()
          for (const run of runs) {
            for (const msg of run.messages ?? []) {
              if (msg.role === 'user' && msg.content) {
                internalUserContents.add(String(msg.content).trim())
              }
            }
          }

          const messages: ChatMessage[] = runs.flatMap((run: ChatEntry) => {
            const result: ChatMessage[] = []

            // Skip run_inputs that are internal team-leader→member delegation messages.
            // These are identified by:
            //   1. The <member_interaction_context> tag Agno injects for context-aware delegations
            //   2. Appearing as a role:'user' message inside another run's messages array
            const inputTrimmed = run.run_input?.trim() ?? ''
            const isMemberDelegationInput =
              inputTrimmed.includes('<member_interaction_context>') ||
              (inputTrimmed.length > 0 && internalUserContents.has(inputTrimmed))

            if (run.run_input && !isMemberDelegationInput) {
              result.push({
                role: 'user',
                content: run.run_input,
                created_at: run.created_at
              })
            }

            const toolCalls: ToolCall[] = [
              ...(run.tools ?? []),
              ...((run.extra_data?.reasoning_messages ?? []).reduce(
                (acc: ToolCall[], msg: ReasoningMessage) => {
                  acc.push({
                    role: 'tool',
                    content: msg.content,
                    tool_call_id: `reasoning-${msg.created_at}`,
                    tool_name: 'reasoning',
                    tool_args: {},
                    tool_call_error: false,
                    metrics: { time: 0 },
                    created_at: msg.created_at
                  })
                  return acc
                },
                []
              ) as ToolCall[])
            ]

            const content =
              run.messages
                ?.filter((m) => m.role === 'assistant')
                .map((m) => m.content || '')
                .join('') || ''

            if (content || toolCalls.length > 0) {
              result.push({
                role: 'agent',
                content: content,
                tool_calls: toolCalls,
                created_at: run.created_at + 1,
                extra_data: run.extra_data
              })
            }

            return result
          })

          // Sort by created_at so messages always appear in chronological order
          // regardless of how the API returns the runs.
          messages.sort((a, b) => (a.created_at ?? 0) - (b.created_at ?? 0))

          setMessages(messages)
        }
      } catch {
        toast.error('Error loading session')
      }
    },
    [selectedEndpoint, authToken, setMessages]
  )

  return { getSessions, getSession }
}

export default useSessionLoader
