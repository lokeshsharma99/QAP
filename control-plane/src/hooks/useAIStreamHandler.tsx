import { useCallback, useRef } from 'react'
import { flushSync } from 'react-dom'
import { APIRoutes } from '@/api/routes'

import useChatActions from '@/hooks/useChatActions'
import { useStore } from '../store'
import { RunEvent, RunResponseContent, type RunResponse } from '@/types/os'
import { constructEndpointUrl } from '@/lib/constructEndpointUrl'
import useAIResponseStream from './useAIResponseStream'
import { ToolCall } from '@/types/os'
import { useQueryState } from 'nuqs'
import { getJsonMarkdown } from '@/lib/utils'

const useAIChatStreamHandler = () => {
  const setMessages = useStore((state) => state.setMessages)
  const { addMessage, focusChatInput } = useChatActions()
  const [agentId] = useQueryState('agent')
  const [teamId] = useQueryState('team')
  const [workflowId] = useQueryState('workflow')
  const [sessionId, setSessionId] = useQueryState('session')
  const selectedEndpoint = useStore((state) => state.selectedEndpoint)
  const authToken = useStore((state) => state.authToken)
  const mode = useStore((state) => state.mode)
  const setStreamingErrorMessage = useStore((state) => state.setStreamingErrorMessage)
  const setIsStreaming = useStore((state) => state.setIsStreaming)
  const setSessionsData = useStore((state) => state.setSessionsData)
  const addChatEvent = useStore((state) => state.addChatEvent)
  const upsertLastChatEvent = useStore((state) => state.upsertLastChatEvent)
  const clearChatEvents = useStore((state) => state.clearChatEvents)
  const setActiveRunId = useStore((state) => state.setActiveRunId)
  const { streamResponse } = useAIResponseStream()
  const abortControllerRef = useRef<AbortController | null>(null)

  const updateMessagesWithErrorState = useCallback(() => {
    setMessages((prevMessages) => {
      const newMessages = [...prevMessages]
      const lastMessage = newMessages[newMessages.length - 1]
      if (lastMessage && lastMessage.role === 'agent') {
        lastMessage.streamingError = true
      }
      return newMessages
    })
  }, [setMessages])

  /**
   * Processes a new tool call and adds it to the message
   */
  const processToolCall = useCallback(
    (toolCall: ToolCall, prevToolCalls: ToolCall[] = []) => {
      const toolCallId =
        toolCall.tool_call_id || `${toolCall.tool_name}-${toolCall.created_at}`

      const existingToolCallIndex = prevToolCalls.findIndex(
        (tc) =>
          (tc.tool_call_id && tc.tool_call_id === toolCall.tool_call_id) ||
          (!tc.tool_call_id &&
            toolCall.tool_name &&
            toolCall.created_at &&
            `${tc.tool_name}-${tc.created_at}` === toolCallId)
      )
      if (existingToolCallIndex >= 0) {
        const updatedToolCalls = [...prevToolCalls]
        updatedToolCalls[existingToolCallIndex] = {
          ...updatedToolCalls[existingToolCallIndex],
          ...toolCall
        }
        return updatedToolCalls
      } else {
        return [...prevToolCalls, toolCall]
      }
    },
    []
  )

  /**
   * Processes tool calls from a chunk, handling both single tool object and tools array formats
   */
  const processChunkToolCalls = useCallback(
    (
      chunk: RunResponseContent | RunResponse,
      existingToolCalls: ToolCall[] = []
    ) => {
      let updatedToolCalls = [...existingToolCalls]
      if (chunk.tool) {
        updatedToolCalls = processToolCall(chunk.tool, updatedToolCalls)
      }
      if (chunk.tools && chunk.tools.length > 0) {
        for (const toolCall of chunk.tools) {
          updatedToolCalls = processToolCall(toolCall, updatedToolCalls)
        }
      }
      return updatedToolCalls
    },
    [processToolCall]
  )

  const handleStreamResponse = useCallback(
    async (input: string | FormData) => {
      setIsStreaming(true)
      clearChatEvents()
      addChatEvent({ type: 'run_start', label: 'Run started', ts: Date.now() })
      const controller = new AbortController()
      abortControllerRef.current = controller

      const formData = input instanceof FormData ? input : new FormData()
      if (typeof input === 'string') {
        formData.append('message', input)
      }

      // Optimistically add a placeholder session entry as soon as the user sends
      // a message so it appears in the sidebar immediately (not after agent responds).
      const PENDING_PREFIX = '__pending__'
      const pendingSessionId = PENDING_PREFIX + Date.now()
      if (!sessionId) {
        const userMessage = formData.get('message') as string | null
        setSessionsData((prev) => {
          const placeholder = {
            session_id: pendingSessionId,
            session_name: userMessage ?? 'New session',
            created_at: Math.floor(Date.now() / 1000),
          }
          return [placeholder, ...(prev ?? [])]
        })
      }

      setMessages((prevMessages) => {
        if (prevMessages.length >= 2) {
          const lastMessage = prevMessages[prevMessages.length - 1]
          const secondLastMessage = prevMessages[prevMessages.length - 2]
          if (
            lastMessage.role === 'agent' &&
            lastMessage.streamingError &&
            secondLastMessage.role === 'user'
          ) {
            return prevMessages.slice(0, -2)
          }
        }
        return prevMessages
      })

      addMessage({
        role: 'user',
        content: formData.get('message') as string,
        created_at: Math.floor(Date.now() / 1000)
      })

      addMessage({
        role: 'agent',
        content: '',
        tool_calls: [],
        streamingError: false,
        created_at: Math.floor(Date.now() / 1000) + 1
      })

      let lastContent = ''
      let pendingFollowups: string[] | null = null
      let newSessionId = sessionId
      try {
        const endpointUrl = constructEndpointUrl(selectedEndpoint)

        let RunUrl: string | null = null

        if (mode === 'team' && teamId) {
          RunUrl = APIRoutes.TeamRun(endpointUrl, teamId)
        } else if (mode === 'agent' && agentId) {
          RunUrl = APIRoutes.AgentRun(endpointUrl).replace('{agent_id}', agentId)
        } else if (mode === 'workflow' && workflowId) {
          RunUrl = APIRoutes.WorkflowRun(endpointUrl, workflowId)
        }

        if (!RunUrl) {
          const noAgentMsg = 'Please select an agent, team, or workflow first.'
          setMessages((prevMessages) => {
            const newMessages = [...prevMessages]
            const lastMessage = newMessages[newMessages.length - 1]
            if (lastMessage && lastMessage.role === 'agent') {
              newMessages[newMessages.length - 1] = { ...lastMessage, streamingError: true, content: noAgentMsg }
            }
            return newMessages
          })
          setStreamingErrorMessage(noAgentMsg)
          setIsStreaming(false)
          return
        }

        formData.append('stream', 'true')
        formData.append('session_id', sessionId ?? '')

        // For new sessions, pass the first user message as session_name so Agno persists it.
        if (!sessionId) {
          const userMessage = formData.get('message') as string | null
          if (userMessage) {
            const nameParam = userMessage.length > 60 ? userMessage.slice(0, 60).trimEnd() + '…' : userMessage
            const urlWithName = new URL(RunUrl)
            urlWithName.searchParams.set('session_name', nameParam)
            RunUrl = urlWithName.toString()
          }
        }

        const headers: Record<string, string> = {}
        if (authToken) {
          headers['Authorization'] = `Bearer ${authToken}`
        }

        await streamResponse({
          apiUrl: RunUrl,          signal: controller.signal,          headers,
          requestBody: formData,
          onChunk: (chunk: RunResponse) => {
            if (
              chunk.event === RunEvent.RunStarted ||
              chunk.event === RunEvent.TeamRunStarted ||
              chunk.event === RunEvent.ReasoningStarted ||
              chunk.event === RunEvent.TeamReasoningStarted ||
              chunk.event === RunEvent.WorkflowStarted
            ) {
              newSessionId = chunk.session_id as string
              if (chunk.run_id) setActiveRunId(chunk.run_id)
              setSessionId(chunk.session_id as string)
              if ((!sessionId || sessionId !== chunk.session_id) && chunk.session_id) {
                const sessionData = {
                  session_id: chunk.session_id as string,
                  session_name: formData.get('message') as string,
                  created_at: chunk.created_at
                }
                setSessionsData((prevSessionsData) => {
                  const sessionExists = prevSessionsData?.some(
                    (session) => session.session_id === chunk.session_id
                  )
                  if (sessionExists) return prevSessionsData
                  // Replace the optimistic placeholder (if present) with the real session entry
                  const withoutPlaceholder = (prevSessionsData ?? []).filter(
                    (s) => !s.session_id.startsWith(PENDING_PREFIX)
                  )
                  return [sessionData, ...withoutPlaceholder]
                })
              }
              addChatEvent({ type: 'run_start', label: `${chunk.event}`, ts: Date.now(), detail: chunk.session_id as string | undefined })
            } else if (
              chunk.event === RunEvent.ToolCallStarted ||
              chunk.event === RunEvent.TeamToolCallStarted ||
              chunk.event === RunEvent.ToolCallCompleted ||
              chunk.event === RunEvent.TeamToolCallCompleted
            ) {
              const toolName = chunk.tool?.tool_name ?? 'tool'
              const isDone = chunk.event === RunEvent.ToolCallCompleted || chunk.event === RunEvent.TeamToolCallCompleted
              addChatEvent({
                type: isDone ? 'tool_done' : 'tool_start',
                label: isDone ? `✓ ${toolName}` : `⚙ ${toolName}`,
                ts: Date.now(),
                detail: chunk.tool?.tool_args ? JSON.stringify(chunk.tool.tool_args).slice(0, 120) : undefined
              })
              setMessages((prevMessages) => {
                const newMessages = [...prevMessages]
                const idx = newMessages.length - 1
                const lastMessage = newMessages[idx]
                if (lastMessage && lastMessage.role === 'agent') {
                  newMessages[idx] = {
                    ...lastMessage,
                    tool_calls: processChunkToolCalls(chunk, lastMessage.tool_calls),
                  }
                }
                return newMessages
              })
            } else if (
              chunk.event === RunEvent.RunContent ||
              chunk.event === RunEvent.TeamRunContent
            ) {
              flushSync(() => {
                setMessages((prevMessages) => {
                  const newMessages = [...prevMessages]
                  const idx = newMessages.length - 1
                  const lastMessage = newMessages[idx]
                  if (
                    lastMessage &&
                    lastMessage.role === 'agent' &&
                    typeof chunk.content === 'string'
                  ) {
                    const uniqueContent = chunk.content.replace(lastContent, '')
                    lastContent = chunk.content
                    // Emit a live content event so the Activity Stream updates in real-time.
                    // upsertLastChatEvent replaces the previous content event instead of appending
                    // a new one for every token — keeps the stream readable.
                    if (uniqueContent.trim()) {
                      upsertLastChatEvent({
                        type: 'content',
                        label: '✍ Generating…',
                        ts: Date.now(),
                        detail: chunk.content.slice(-100).replace(/\n+/g, ' '),
                      })
                    }
                    newMessages[idx] = {
                      ...lastMessage,
                      content: lastMessage.content + uniqueContent,
                      tool_calls: processChunkToolCalls(chunk, lastMessage.tool_calls),
                      extra_data: {
                        ...lastMessage.extra_data,
                        ...(chunk.extra_data?.reasoning_steps && { reasoning_steps: chunk.extra_data.reasoning_steps }),
                        ...(chunk.extra_data?.references && { references: chunk.extra_data.references }),
                      },
                      created_at: chunk.created_at ?? lastMessage.created_at,
                      ...(chunk.images && { images: chunk.images }),
                      ...(chunk.videos && { videos: chunk.videos }),
                      ...(chunk.audio && { audio: chunk.audio }),
                    }
                  } else if (
                    lastMessage &&
                    lastMessage.role === 'agent' &&
                    typeof chunk?.content !== 'string' &&
                    chunk.content !== null
                  ) {
                    const jsonBlock = getJsonMarkdown(chunk?.content)
                    lastContent = jsonBlock
                    newMessages[idx] = { ...lastMessage, content: lastMessage.content + jsonBlock }
                  } else if (
                    chunk.response_audio?.transcript &&
                    typeof chunk.response_audio?.transcript === 'string' &&
                    lastMessage
                  ) {
                    const transcript = chunk.response_audio.transcript
                    newMessages[idx] = {
                      ...lastMessage,
                      response_audio: {
                        ...lastMessage.response_audio,
                        transcript: (lastMessage.response_audio?.transcript ?? '') + transcript,
                      },
                    }
                  }
                  return newMessages
                })
              })
            } else if (
              chunk.event === RunEvent.ReasoningStep ||
              chunk.event === RunEvent.TeamReasoningStep
            ) {
              const step = chunk.extra_data?.reasoning_steps?.[chunk.extra_data.reasoning_steps.length - 1]
              if (step) {
                addChatEvent({ type: 'reasoning', label: `Reasoning: ${step.title}`, ts: Date.now(), detail: step.reasoning?.slice(0, 100) })
              }
              setMessages((prevMessages) => {
                const newMessages = [...prevMessages]
                const idx = newMessages.length - 1
                const lastMessage = newMessages[idx]
                if (lastMessage && lastMessage.role === 'agent') {
                  const existingSteps = lastMessage.extra_data?.reasoning_steps ?? []
                  const incomingSteps = chunk.extra_data?.reasoning_steps ?? []
                  newMessages[idx] = {
                    ...lastMessage,
                    extra_data: {
                      ...lastMessage.extra_data,
                      reasoning_steps: [...existingSteps, ...incomingSteps],
                    },
                  }
                }
                return newMessages
              })
            } else if (
              chunk.event === RunEvent.ReasoningCompleted ||
              chunk.event === RunEvent.TeamReasoningCompleted
            ) {
              setMessages((prevMessages) => {
                const newMessages = [...prevMessages]
                const idx = newMessages.length - 1
                const lastMessage = newMessages[idx]
                if (lastMessage && lastMessage.role === 'agent' && chunk.extra_data?.reasoning_steps) {
                  newMessages[idx] = {
                    ...lastMessage,
                    extra_data: {
                      ...lastMessage.extra_data,
                      reasoning_steps: chunk.extra_data.reasoning_steps,
                    },
                  }
                }
                return newMessages
              })
            } else if (
              chunk.event === RunEvent.RunError ||
              chunk.event === RunEvent.TeamRunError ||
              chunk.event === RunEvent.TeamRunCancelled
            ) {
              const rawError = (chunk.content as string) || (chunk.event === RunEvent.TeamRunCancelled ? 'Run cancelled' : 'Error during run')
              const errorContent = /VLM|Vision Language Model|not a vlm/i.test(rawError)
                ? 'The current model does not support image/file attachments. Either use a vision-capable model or attach text/code files only.'
                : rawError
              // Populate the agent message content so the error bubble renders in the chat UI
              setMessages((prevMessages) => {
                const newMessages = [...prevMessages]
                const lastMessage = newMessages[newMessages.length - 1]
                if (lastMessage && lastMessage.role === 'agent') {
                  newMessages[newMessages.length - 1] = {
                    ...lastMessage,
                    streamingError: true,
                    content: lastMessage.content || errorContent,
                  }
                }
                return newMessages
              })
              addChatEvent({ type: 'error', label: `Error: ${String(errorContent).slice(0, 80)}`, ts: Date.now() })
              setStreamingErrorMessage(errorContent)
              if (newSessionId) {
                setSessionsData(
                  (prevSessionsData) =>
                    prevSessionsData?.filter((session) => session.session_id !== newSessionId) ?? null
                )
              }
            } else if (
              chunk.event === RunEvent.UpdatingMemory ||
              chunk.event === RunEvent.TeamMemoryUpdateStarted ||
              chunk.event === RunEvent.TeamMemoryUpdateCompleted
            ) {
              addChatEvent({
                type: 'memory',
                label: chunk.event === RunEvent.UpdatingMemory || chunk.event === RunEvent.TeamMemoryUpdateStarted
                  ? 'Updating memory…'
                  : '✓ Memory updated',
                ts: Date.now()
              })
            } else if (
              chunk.event === RunEvent.RunCompleted ||
              chunk.event === RunEvent.TeamRunCompleted ||
              chunk.event === RunEvent.WorkflowCompleted
            ) {
              addChatEvent({ type: 'run_done', label: 'Run completed', ts: Date.now() })
              const followupsToApply = pendingFollowups
              setMessages((prevMessages) => {
                const newMessages = prevMessages.map((message, index) => {
                  if (index === prevMessages.length - 1 && message.role === 'agent') {
                    let updatedContent: string
                    if (typeof chunk.content === 'string') {
                      updatedContent = chunk.content
                    } else {
                      try {
                        updatedContent = JSON.stringify(chunk.content)
                      } catch {
                        updatedContent = 'Error parsing response'
                      }
                    }
                    // For WorkflowCompleted: preserve any content already accumulated
                    // from StepCompleted events; only replace if the event has actual content.
                    if (chunk.event === RunEvent.WorkflowCompleted && !updatedContent) {
                      return message
                    }
                    return {
                      ...message,
                      content: updatedContent,
                      tool_calls: processChunkToolCalls(chunk, message.tool_calls),
                      images: chunk.images ?? message.images,
                      videos: chunk.videos ?? message.videos,
                      response_audio: chunk.response_audio,
                      created_at: chunk.created_at ?? message.created_at,
                      // Explicitly preserve followups collected from FollowupsCompleted event
                      followups: message.followups ?? followupsToApply ?? undefined,
                      extra_data: {
                        reasoning_steps:
                          chunk.extra_data?.reasoning_steps ?? message.extra_data?.reasoning_steps,
                        references:
                          chunk.extra_data?.references ?? message.extra_data?.references
                      }
                    }
                  }
                  return message
                })
                return newMessages
              })
            } else if (
              chunk.event === RunEvent.StepStarted
            ) {
              const stepName = (chunk as RunResponse & { step_name?: string }).step_name
              addChatEvent({ type: 'run_start', label: `▶ Step${stepName ? `: ${stepName}` : ''} started`, ts: Date.now() })
            } else if (
              chunk.event === RunEvent.StepCompleted
            ) {
              const stepName = (chunk as RunResponse & { step_name?: string }).step_name
              addChatEvent({ type: 'run_done', label: `✓ Step${stepName ? `: ${stepName}` : ''} completed`, ts: Date.now() })
              // Render step output into the chat bubble.
              // Agno workflows do NOT emit RunContent events from inner agents —
              // the step output arrives only via StepCompleted.content.
              if (chunk.content !== null && chunk.content !== undefined) {
                let stepContent = ''
                if (typeof chunk.content === 'string') {
                  stepContent = chunk.content
                } else {
                  try { stepContent = JSON.stringify(chunk.content, null, 2) } catch { /* skip */ }
                }
                if (stepContent) {
                  flushSync(() => {
                    setMessages((prevMessages) => {
                      const newMessages = [...prevMessages]
                      const idx = newMessages.length - 1
                      const lastMessage = newMessages[idx]
                      if (lastMessage && lastMessage.role === 'agent') {
                        newMessages[idx] = {
                          ...lastMessage,
                          content: lastMessage.content
                            ? lastMessage.content + '\n\n' + stepContent
                            : stepContent,
                        }
                      }
                      return newMessages
                    })
                  })
                }
              }
            } else if (
              chunk.event === RunEvent.WorkflowError ||
              chunk.event === RunEvent.StepError
            ) {
              const rawError = (chunk.content as string) || 'Workflow error'
              setMessages((prevMessages) => {
                const newMessages = [...prevMessages]
                const lastMessage = newMessages[newMessages.length - 1]
                if (lastMessage && lastMessage.role === 'agent') {
                  newMessages[newMessages.length - 1] = { ...lastMessage, streamingError: true, content: lastMessage.content || rawError }
                }
                return newMessages
              })
              addChatEvent({ type: 'error', label: `Error: ${String(rawError).slice(0, 80)}`, ts: Date.now() })
              setStreamingErrorMessage(rawError)
              if (newSessionId) {
                setSessionsData(
                  (prevSessionsData) =>
                    prevSessionsData?.filter((session) => session.session_id !== newSessionId) ?? null
                )
              }
            } else if (
              chunk.event === RunEvent.WorkflowCancelled
            ) {
              const cancelMsg = 'Workflow was cancelled'
              setMessages((prevMessages) => {
                const newMessages = [...prevMessages]
                const lastMessage = newMessages[newMessages.length - 1]
                if (lastMessage && lastMessage.role === 'agent') {
                  newMessages[newMessages.length - 1] = { ...lastMessage, streamingError: true, content: lastMessage.content || cancelMsg }
                }
                return newMessages
              })
              addChatEvent({ type: 'error', label: 'Workflow cancelled', ts: Date.now() })
              setStreamingErrorMessage(cancelMsg)
            } else if (
              chunk.event === RunEvent.FollowupsCompleted ||
              chunk.event === RunEvent.TeamFollowupsCompleted
            ) {
              const followups = (chunk as RunResponse & { followups?: string[] }).followups
              if (followups && followups.length > 0) {
                // Stash followups so RunCompleted handler can apply them reliably
                pendingFollowups = followups
                setMessages((prevMessages) => {
                  const newMessages = [...prevMessages]
                  const idx = newMessages.length - 1
                  const lastMessage = newMessages[idx]
                  if (lastMessage && lastMessage.role === 'agent') {
                    newMessages[idx] = { ...lastMessage, followups }
                  }
                  return newMessages
                })
              }
            } else if (
              chunk.event === RunEvent.RunOutput
            ) {
              // RunOutput carries structured output — surface it as a debug event
              addChatEvent({ type: 'debug', label: `◦ RunOutput`, ts: Date.now(), detail: typeof chunk.content === 'string' ? chunk.content.slice(0, 120) : undefined })
            } else if (
              chunk.event === RunEvent.RunCancelled
            ) {
              addChatEvent({ type: 'debug', label: '◦ Run cancelled', ts: Date.now() })
            } else if (
              chunk.event === RunEvent.RunPaused
            ) {
              addChatEvent({ type: 'debug', label: '⏸ Run paused', ts: Date.now() })
            } else if (
              chunk.event === RunEvent.RunContinued
            ) {
              addChatEvent({ type: 'debug', label: '▶ Run continued', ts: Date.now() })
            } else if (
              chunk.event === RunEvent.FollowupsStarted ||
              chunk.event === RunEvent.TeamFollowupsStarted
            ) {
              addChatEvent({ type: 'debug', label: '◦ Generating follow-ups…', ts: Date.now() })
            } else if (chunk.event) {
              // Catch-all: surface any other event type as a debug entry so nothing is invisible
              addChatEvent({ type: 'debug', label: `◦ ${chunk.event}`, ts: Date.now() })
            }
          },
          onError: (error) => {
            const errMsg = error.message
            setMessages((prevMessages) => {
              const newMessages = [...prevMessages]
              const lastMessage = newMessages[newMessages.length - 1]
              if (lastMessage && lastMessage.role === 'agent') {
                newMessages[newMessages.length - 1] = { ...lastMessage, streamingError: true, content: lastMessage.content || errMsg }
              }
              return newMessages
            })
            addChatEvent({ type: 'error', label: `Error: ${errMsg.slice(0, 80)}`, ts: Date.now() })
            setStreamingErrorMessage(errMsg)
            // Remove actual session entry or placeholder on error
            setSessionsData(
              (prevSessionsData) =>
                prevSessionsData?.filter(
                  (session) =>
                    session.session_id !== newSessionId &&
                    !session.session_id.startsWith(PENDING_PREFIX)
                ) ?? null
            )
          },
          onComplete: () => {}
        })
      } catch (error) {
        const errMsg = error instanceof Error ? error.message : String(error)
        setMessages((prevMessages) => {
          const newMessages = [...prevMessages]
          const lastMessage = newMessages[newMessages.length - 1]
          if (lastMessage && lastMessage.role === 'agent') {
            newMessages[newMessages.length - 1] = { ...lastMessage, streamingError: true, content: lastMessage.content || errMsg }
          }
          return newMessages
        })
        addChatEvent({ type: 'error', label: `Error: ${errMsg.slice(0, 80)}`, ts: Date.now() })
        setStreamingErrorMessage(errMsg)
        // Remove actual session entry or placeholder on error
        setSessionsData(
          (prevSessionsData) =>
            prevSessionsData?.filter(
              (session) =>
                session.session_id !== newSessionId &&
                !session.session_id.startsWith(PENDING_PREFIX)
            ) ?? null
        )
      } finally {
        focusChatInput()
        setIsStreaming(false)
        setActiveRunId(null)
      }
    },
    [
      setMessages,
      addMessage,
      selectedEndpoint,
      authToken,
      streamResponse,
      agentId,
      teamId,
      workflowId,
      mode,
      setStreamingErrorMessage,
      setIsStreaming,
      focusChatInput,
      setSessionsData,
      sessionId,
      setSessionId,
      processChunkToolCalls,
      addChatEvent,
      upsertLastChatEvent,
      clearChatEvents,
      setActiveRunId
    ]
  )

  const cancelRun = useCallback(async () => {
    // 1. Abort the SSE fetch immediately — flips button state right away
    abortControllerRef.current?.abort()
    setIsStreaming(false)
    setActiveRunId(null)

    // 2. Best-effort cancel on the backend
    const runId = useStore.getState().activeRunId
    if (!runId) return
    const endpointUrl = constructEndpointUrl(selectedEndpoint)
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`
    let cancelUrl: string | null = null
    if (mode === 'agent' && agentId) {
      cancelUrl = APIRoutes.CancelAgentRun(endpointUrl, agentId, runId)
    } else if (mode === 'team' && teamId) {
      cancelUrl = APIRoutes.CancelTeamRun(endpointUrl, teamId, runId)
    } else if (mode === 'workflow' && workflowId) {
      cancelUrl = APIRoutes.CancelWorkflowRun(endpointUrl, workflowId, runId)
    }
    if (!cancelUrl) return
    try {
      await fetch(cancelUrl, { method: 'POST', headers })
    } catch { /* ignore */ }
  }, [selectedEndpoint, authToken, mode, agentId, teamId, workflowId, setIsStreaming, setActiveRunId])

  return { handleStreamResponse, cancelRun }
}

export default useAIChatStreamHandler
