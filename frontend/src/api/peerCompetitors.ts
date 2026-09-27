import type { PeerCompetitorsResponse } from '../types/api'
import { apiRequest } from './client'

export function getPeerCompetitors(organizationId: string): Promise<PeerCompetitorsResponse> {
  return apiRequest<PeerCompetitorsResponse>(
    `/api/v1/organizations/${organizationId}/peer-competitors`,
  )
}

export function refreshPeerCompetitors(organizationId: string): Promise<PeerCompetitorsResponse> {
  return apiRequest<PeerCompetitorsResponse>(
    `/api/v1/organizations/${organizationId}/peer-competitors/refresh`,
    { method: 'POST' },
  )
}
