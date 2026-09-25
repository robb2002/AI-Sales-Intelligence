import type { OpportunityDetail, OpportunityPage, ScoreBand } from '../types/api'
import { apiRequest } from './client'

export function listOpportunities(params?: {
  organization_id?: string
  organization_type?: string[]
  state_code?: string[]
  band?: ScoreBand[]
  sort?: 'score' | 'updated_at'
  direction?: 'asc' | 'desc'
  limit?: number
  offset?: number
}): Promise<OpportunityPage> {
  const search = new URLSearchParams()
  if (params?.organization_id) search.set('organization_id', params.organization_id)
  for (const t of params?.organization_type ?? []) search.append('organization_type', t)
  for (const s of params?.state_code ?? []) search.append('state_code', s)
  for (const b of params?.band ?? []) search.append('band', b)
  if (params?.sort) search.set('sort', params.sort)
  if (params?.direction) search.set('direction', params.direction)
  if (params?.limit != null) search.set('limit', String(params.limit))
  if (params?.offset != null) search.set('offset', String(params.offset))
  const query = search.toString()
  return apiRequest<OpportunityPage>(`/api/v1/opportunities${query ? `?${query}` : ''}`)
}

export function getOpportunity(opportunityId: string): Promise<OpportunityDetail> {
  return apiRequest<OpportunityDetail>(`/api/v1/opportunities/${opportunityId}`)
}
