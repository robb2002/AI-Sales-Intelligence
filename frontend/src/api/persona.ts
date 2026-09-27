import type { PersonaRequest, PersonaResponse } from '../types/api'
import { apiRequest } from './client'

export function sendPersonaMessage(body: PersonaRequest): Promise<PersonaResponse> {
  return apiRequest<PersonaResponse>('/api/v1/persona/messages', {
    method: 'POST',
    body: JSON.stringify({
      message: body.message,
      history: body.history.slice(-6),
      organization_id: body.organization_id,
      mode: body.mode,
      scope: body.scope ?? 'auto',
    }),
  })
}
