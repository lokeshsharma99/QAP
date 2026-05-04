// QAP-specific API calls for workflows, spec review, and healing

import { APIRoutes } from './routes'
import { WorkflowRun } from '@/types/qap'

const createHeaders = (authToken?: string): HeadersInit => {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
  }
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`
  return headers
}

export const getWorkflowsAPI = async (
  endpoint: string,
  authToken?: string
): Promise<{ id: string; name: string; description?: string }[]> => {
  try {
    const response = await fetch(APIRoutes.GetWorkflows(endpoint), {
      method: 'GET',
      headers: createHeaders(authToken)
    })
    if (!response.ok) return []
    return response.json()
  } catch {
    return []
  }
}

export const triggerWorkflowAPI = async (
  endpoint: string,
  workflowId: string,
  input: string,
  authToken?: string
): Promise<WorkflowRun | null> => {
  try {
    const response = await fetch(APIRoutes.WorkflowRun(endpoint, workflowId), {
      method: 'POST',
      headers: createHeaders(authToken),
      body: JSON.stringify({ message: input })
    })
    if (!response.ok) return null
    return response.json()
  } catch {
    return null
  }
}

export const getWorkflowRunStatusAPI = async (
  endpoint: string,
  workflowId: string,
  runId: string,
  authToken?: string
): Promise<WorkflowRun | null> => {
  try {
    const response = await fetch(
      APIRoutes.GetWorkflowRunStatus(endpoint, workflowId, runId),
      {
        method: 'GET',
        headers: createHeaders(authToken)
      }
    )
    if (!response.ok) return null
    return response.json()
  } catch {
    return null
  }
}
