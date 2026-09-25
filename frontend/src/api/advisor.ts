import { apiRequest } from './client'
import type {
  AdvisorAnswerResponse,
  AdvisorSessionResponse,
} from '../types/api'

export function askAdvisor(body: {
  scope_type: 'organization' | 'opportunity'
  scope_id: string
  message: string
  session_id?: string | null
}): Promise<AdvisorAnswerResponse> {
  return apiRequest<AdvisorAnswerResponse>('/api/v1/advisor/questions', {
    method: 'POST',
    body: JSON.stringify({
      scope_type: body.scope_type,
      scope_id: body.scope_id,
      message: body.message,
      session_id: body.session_id ?? null,
    }),
  })
}

export function getAdvisorSession(sessionId: string): Promise<AdvisorSessionResponse> {
  return apiRequest<AdvisorSessionResponse>(`/api/v1/advisor/sessions/${sessionId}`)
}
