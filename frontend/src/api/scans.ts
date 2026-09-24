import type {
  OrganizationSourcePage,
  OrganizationSummaryPage,
  ScanBatchResponse,
  ScanDetail,
} from '../types/api'
import { apiRequest } from './client'

export function listOrganizations(params?: {
  tracking_status?: string[]
}): Promise<OrganizationSummaryPage> {
  const search = new URLSearchParams()
  for (const status of params?.tracking_status ?? []) {
    search.append('tracking_status', status)
  }
  const query = search.toString()
  return apiRequest<OrganizationSummaryPage>(
    `/api/v1/organizations${query ? `?${query}` : ''}`,
  )
}

export function listOrganizationSources(
  organizationId: string,
  params?: { status?: string[] },
): Promise<OrganizationSourcePage> {
  const search = new URLSearchParams()
  for (const status of params?.status ?? []) {
    search.append('status', status)
  }
  const query = search.toString()
  return apiRequest<OrganizationSourcePage>(
    `/api/v1/organizations/${organizationId}/sources${query ? `?${query}` : ''}`,
  )
}

export function startScanAll(): Promise<ScanBatchResponse> {
  return apiRequest<ScanBatchResponse>('/api/v1/scans', {
    method: 'POST',
    body: JSON.stringify({ scope: 'all_tracked' }),
  })
}

export function getScanBatch(batchId: string): Promise<ScanBatchResponse> {
  return apiRequest<ScanBatchResponse>(`/api/v1/scan-batches/${batchId}`)
}

export function getScan(scanId: string): Promise<ScanDetail> {
  return apiRequest<ScanDetail>(`/api/v1/scans/${scanId}`)
}
