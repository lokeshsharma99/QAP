import { toast } from 'sonner'

import { APIRoutes } from './routes'

import { AgentDetails, AgentFullDetail, PaginatedSessions, Sessions, TeamDetails, TeamFullDetail, WorkflowDetails, WorkflowFullDetail } from '@/types/os'

const createHeaders = (authToken?: string): HeadersInit => {
  const headers: HeadersInit = {
    'Content-Type': 'application/json'
  }
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }
  return headers
}

export const getAgentsAPI = async (
  endpoint: string,
  authToken?: string
): Promise<AgentDetails[]> => {
  const url = APIRoutes.GetAgents(endpoint)
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: createHeaders(authToken)
    })
    if (!response.ok) {
      toast.error(`Failed to fetch agents: ${response.statusText}`)
      return []
    }
    return response.json()
  } catch {
    toast.error('Error fetching agents')
    return []
  }
}

export const getTeamsAPI = async (
  endpoint: string,
  authToken?: string
): Promise<TeamDetails[]> => {
  const url = APIRoutes.GetTeams(endpoint)
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: createHeaders(authToken)
    })
    if (!response.ok) {
      toast.error(`Failed to fetch teams: ${response.statusText}`)
      return []
    }
    return response.json()
  } catch {
    toast.error('Error fetching teams')
    return []
  }
}

export const getWorkflowsAPI = async (
  endpoint: string,
  authToken?: string
): Promise<WorkflowDetails[]> => {
  const url = APIRoutes.GetWorkflows(endpoint)
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: createHeaders(authToken)
    })
    if (!response.ok) return []
    return response.json()
  } catch {
    return []
  }
}

export const getAgentDetailAPI = async (
  endpoint: string,
  agentId: string,
  authToken?: string
): Promise<AgentFullDetail | null> => {
  try {
    const response = await fetch(APIRoutes.GetAgent(endpoint, agentId), {
      method: 'GET',
      headers: createHeaders(authToken)
    })
    if (!response.ok) return null
    return response.json()
  } catch {
    return null
  }
}

export const getTeamDetailAPI = async (
  endpoint: string,
  teamId: string,
  authToken?: string
): Promise<TeamFullDetail | null> => {
  try {
    const response = await fetch(APIRoutes.GetTeam(endpoint, teamId), {
      method: 'GET',
      headers: createHeaders(authToken)
    })
    if (!response.ok) return null
    return response.json()
  } catch {
    return null
  }
}

export const getWorkflowDetailAPI = async (
  endpoint: string,
  workflowId: string,
  authToken?: string
): Promise<WorkflowFullDetail | null> => {
  try {
    const response = await fetch(APIRoutes.GetWorkflow(endpoint, workflowId), {
      method: 'GET',
      headers: createHeaders(authToken)
    })
    if (!response.ok) return null
    return response.json()
  } catch {
    return null
  }
}

export const getStatusAPI = async (
  base: string,
  authToken?: string
): Promise<number> => {
  const response = await fetch(APIRoutes.Status(base), {
    method: 'GET',
    headers: createHeaders(authToken)
  })
  return response.status
}

export const getAllSessionsAPI = async (
  base: string,
  type: 'agent' | 'team' | 'workflow',
  componentId: string,
  dbId: string,
  authToken?: string
): Promise<Sessions | { data: [] }> => {
  try {
    const url = new URL(APIRoutes.GetSessions(base))
    url.searchParams.set('type', type)
    url.searchParams.set('component_id', componentId)
    url.searchParams.set('db_id', dbId)

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: createHeaders(authToken)
    })

    if (!response.ok) {
      if (response.status === 404) return { data: [] }
      throw new Error(`Failed to fetch sessions: ${response.statusText}`)
    }
    return response.json()
  } catch {
    return { data: [] }
  }
}

export const getSessionAPI = async (
  base: string,
  type: 'agent' | 'team' | 'workflow',
  sessionId: string,
  dbId?: string,
  authToken?: string
) => {
  const queryParams = new URLSearchParams({ type })
  if (dbId) queryParams.append('db_id', dbId)

  const response = await fetch(
    `${APIRoutes.GetSession(base, sessionId)}?${queryParams.toString()}`,
    {
      method: 'GET',
      headers: createHeaders(authToken)
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch session: ${response.statusText}`)
  }
  return response.json()
}

export const deleteSessionAPI = async (
  base: string,
  sessionId: string,
  authToken?: string
): Promise<boolean> => {
  try {
    const response = await fetch(APIRoutes.DeleteSession(base, sessionId), {
      method: 'DELETE',
      headers: createHeaders(authToken)
    })
    return response.ok
  } catch {
    return false
  }
}

export const deleteTeamSessionAPI = async (
  base: string,
  teamId: string,
  sessionId: string,
  authToken?: string
): Promise<boolean> => {
  try {
    const response = await fetch(
      APIRoutes.DeleteTeamSession(base, teamId, sessionId),
      {
        method: 'DELETE',
        headers: createHeaders(authToken)
      }
    )
    return response.ok
  } catch {
    return false
  }
}

export interface FetchSessionsParams {
  base: string
  sessionType?: 'agent' | 'team' | 'workflow'
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  limit?: number
  page?: number
  dbId?: string
  componentId?: string
  sessionName?: string
  authToken?: string
}

export const fetchSessionsPageAPI = async ({
  base,
  sessionType,
  sortBy = 'updated_at',
  sortOrder = 'desc',
  limit = 25,
  page = 1,
  dbId,
  componentId,
  sessionName,
  authToken,
}: FetchSessionsParams): Promise<PaginatedSessions> => {
  const url = new URL(APIRoutes.GetSessions(base))
  if (sessionType) url.searchParams.set('type', sessionType)
  url.searchParams.set('sort_by', sortBy)
  url.searchParams.set('sort_order', sortOrder)
  url.searchParams.set('limit', String(limit))
  url.searchParams.set('page', String(page))
  if (dbId) url.searchParams.set('db_id', dbId)
  if (componentId) url.searchParams.set('component_id', componentId)
  if (sessionName) url.searchParams.set('session_name', sessionName)

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: createHeaders(authToken),
  })
  if (!response.ok) {
    throw new Error(`Failed to fetch sessions: ${response.statusText}`)
  }
  return response.json()
}
