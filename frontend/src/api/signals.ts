import type { SignalPage, SignalDetail, SignalState, SignalType } from '../types/api'
import { apiRequest } from './client'

export function listSignals(params?: {
  organization_id?: string
  signal_type?: SignalType[]
  state?: SignalState[]
  q?: string
  limit?: number
  offset?: number
}): Promise<SignalPage> {
  const search = new URLSearchParams()
  if (params?.organization_id) search.set('organization_id', params.organization_id)
  for (const t of params?.signal_type ?? []) search.append('signal_type', t)
  for (const s of params?.state ?? []) search.append('state', s)
  if (params?.q?.trim()) search.set('q', params.q.trim())
  if (params?.limit != null) search.set('limit', String(params.limit))
  if (params?.offset != null) search.set('offset', String(params.offset))
  const query = search.toString()
  return apiRequest<SignalPage>(`/api/v1/signals${query ? `?${query}` : ''}`)
}

export function getSignal(signalId: string): Promise<SignalDetail> {
  return apiRequest<SignalDetail>(`/api/v1/signals/${signalId}`)
}
