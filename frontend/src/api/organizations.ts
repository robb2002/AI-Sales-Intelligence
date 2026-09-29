import type {
  MarketRole,
  OrganizationDetail,
  OrganizationSourceItem,
  OrganizationSourcePage,
  OrganizationSummary,
  OrganizationSummaryPage,
  ScanSummary,
} from '../types/api'
import { apiRequest } from './client'

export type OrganizationWriteBody = {
  name: string
  organization_type: string
  market_role: string
  state_code?: string | null
  website_url: string
}

export type OrganizationPatchBody = {
  name?: string
  organization_type?: string
  market_role?: string
  state_code?: string | null
  website_url?: string
  tracking_status?: 'active' | 'inactive'
  /** ISO timestamp strictly in the future, or null to clear an existing schedule. */
  scheduled_scan_at?: string | null
}

export function listOrganizations(params?: {
  q?: string
  organization_type?: string[]
  state_code?: string[]
  tracking_status?: string[]
  marketRole?: MarketRole[]
  sort?: string
  direction?: string
  limit?: number
  offset?: number
}): Promise<OrganizationSummaryPage> {
  const search = new URLSearchParams()
  if (params?.q) search.set('q', params.q)
  for (const value of params?.organization_type ?? []) search.append('organization_type', value)
  for (const value of params?.state_code ?? []) search.append('state_code', value)
  for (const value of params?.tracking_status ?? []) search.append('tracking_status', value)
  for (const value of params?.marketRole ?? []) search.append('market_role', value)
  if (params?.sort) search.set('sort', params.sort)
  if (params?.direction) search.set('direction', params.direction)
  if (params?.limit != null) search.set('limit', String(params.limit))
  if (params?.offset != null) search.set('offset', String(params.offset))
  const query = search.toString()
  return apiRequest<OrganizationSummaryPage>(`/api/v1/organizations${query ? `?${query}` : ''}`)
}

export function getOrganization(organizationId: string): Promise<OrganizationDetail> {
  return apiRequest<OrganizationDetail>(`/api/v1/organizations/${organizationId}`)
}

export function createOrganization(body: OrganizationWriteBody): Promise<OrganizationDetail> {
  return apiRequest<OrganizationDetail>('/api/v1/organizations', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateOrganization(
  organizationId: string,
  body: OrganizationPatchBody,
): Promise<OrganizationDetail> {
  return apiRequest<OrganizationDetail>(`/api/v1/organizations/${organizationId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export function deleteOrganization(organizationId: string): Promise<void> {
  return apiRequest<void>(`/api/v1/organizations/${organizationId}`, {
    method: 'DELETE',
  })
}

export function listOrganizationSources(
  organizationId: string,
  params?: { status?: string[] },
): Promise<OrganizationSourcePage> {
  const search = new URLSearchParams()
  for (const status of params?.status ?? []) search.append('status', status)
  const query = search.toString()
  return apiRequest<OrganizationSourcePage>(
    `/api/v1/organizations/${organizationId}/sources${query ? `?${query}` : ''}`,
  )
}

export function startOrganizationScan(organizationId: string): Promise<ScanSummary> {
  return apiRequest<ScanSummary>(`/api/v1/organizations/${organizationId}/scans`, {
    method: 'POST',
  })
}

export function addOrganizationSource(
  organizationId: string,
  body: {
    url: string
    page_category: string
    source_title?: string | null
  },
): Promise<OrganizationSourceItem> {
  return apiRequest<OrganizationSourceItem>(`/api/v1/organizations/${organizationId}/sources`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function rejectOrganizationSource(
  organizationId: string,
  organizationSourceId: string,
  rejectionReason?: string | null,
): Promise<OrganizationSourceItem> {
  return apiRequest<OrganizationSourceItem>(
    `/api/v1/organizations/${organizationId}/sources/${organizationSourceId}`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        status: 'rejected',
        rejection_reason: rejectionReason ?? null,
      }),
    },
  )
}

export type { OrganizationSummary }
