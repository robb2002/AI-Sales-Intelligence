import type {
  OrganizationSourcePage,
  OrganizationSummaryPage,
  ScanBatchResponse,
  ScanDetail,
  ScanSummaryPage,
} from '../types/api'
import { apiRequest } from './client'
import { listOrganizations as listOrganizationsApi } from './organizations'

/** @deprecated Prefer `../../api/organizations`. Kept for dashboard Scan All. */
export function listOrganizations(params?: {
  tracking_status?: string[]
}): Promise<OrganizationSummaryPage> {
  return listOrganizationsApi({
    tracking_status: params?.tracking_status,
    limit: 100,
  })
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

export function listScans(params?: { limit?: number }): Promise<ScanSummaryPage> {
  const search = new URLSearchParams({ limit: String(params?.limit ?? 1) })
  return apiRequest<ScanSummaryPage>(`/api/v1/scans?${search.toString()}`)
}

export function getScan(scanId: string): Promise<ScanDetail> {
  return apiRequest<ScanDetail>(`/api/v1/scans/${scanId}`)
}
