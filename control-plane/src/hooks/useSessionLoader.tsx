import { useCallback } from 'react'
import { getSessionAPI, getAllSessionsAPI } from '@/api/os'
import { useStore } from '../store'
import { toast } from 'sonner'
import { ChatMessage, ToolCall, ReasoningMessage, ChatEntry } from '@/types/os'
import { getJsonMarkdown } from '@/lib/utils'

interface LoaderArgs {
  entityType: 'agent' | 'team' | null
  agentId?: string | null
  teamId?: string | null
  dbId: string | null
}

const useSessionLoader = () => {
  const setMessages = useStore((state) => state.setMessages)
  const selectedEndpoint = useStore((state) => state.selectedEndpoint)
  const authToken = useStore((state) => state.authToken)
  const setIsSessionsLoading = useStore((state) => state.setIsSessionsLoading)
  const setSessionsData = useStore((state) => state.setSessionsData)

  const getSessions = useCallback(
    async ({ entityType, agentId, teamId, dbId }: LoaderArgs) => {
      const selectedId = entityType === 'agent' ? agentId : teamId
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
    async ({ entityType, agentId, teamId, dbId }: LoaderArgs, sessionId: string) => {
      const selectedId = entityType === 'agent' ? agentId : teamId
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

          const messages: ChatMessage[] = runs.flatMap((run: ChatEntry) => {
            const result: ChatMessage[] = []

            if (run.run_input) {
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
