import type { TrendsResponse } from '../types/api'
import { apiRequest } from './client'

export function getTrends(months: number = 6): Promise<TrendsResponse> {
  const search = new URLSearchParams()
  search.set('months', String(months))
  return apiRequest<TrendsResponse>(`/api/v1/trends?${search.toString()}`)
}
