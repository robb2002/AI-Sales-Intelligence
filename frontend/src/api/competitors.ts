import type { CompetitorsResponse } from '../types/api'
import { apiRequest } from './client'

export function getCompetitors(): Promise<CompetitorsResponse> {
  return apiRequest<CompetitorsResponse>('/api/v1/competitors')
}
