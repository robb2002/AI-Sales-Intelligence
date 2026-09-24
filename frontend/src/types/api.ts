export type Role = 'SALES_REP' | 'SALES_MANAGER'

export interface CurrentUser {
  user_id: string
  clerk_user_id: string
  email: string
  role: Role
}

export interface HealthResponse {
  status: 'ok'
}

export type ScanStatus =
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'partial'
  | 'failed'
  | 'interrupted'

export type ScanStage =
  | 'discovering'
  | 'validating_sources'
  | 'saving_sources'
  | 'collecting'
  | 'extracting'
  | 'validating'
  | 'deduplicating'
  | 'correlating'
  | 'scoring'

export interface OrganizationSummary {
  organization_id: string
  name: string
  organization_type: string
  market_role: string
  tracking_status: string
  state_code: string | null
  website_url: string | null
  signal_count: number
  opportunity_count: number
  last_scanned_at: string | null
}

export interface OrganizationSummaryPage {
  data: OrganizationSummary[]
  total: number
  limit: number
  offset: number
}

export interface OrganizationSourceItem {
  organization_source_id: string
  organization_id: string
  url: string
  source_title: string | null
  page_category: string
  status: 'approved' | 'rejected'
  is_official: boolean
  rejection_reason: string | null
  last_validated_at: string
}

export interface OrganizationSourcePage {
  data: OrganizationSourceItem[]
  total: number
  limit: number
  offset: number
}

export interface ScanSummary {
  scan_id: string
  organization_id: string
  organization_name: string
  trigger: string
  status: ScanStatus
  stage: ScanStage | null
  started_at: string | null
  finished_at: string | null
  candidates_found: number
  sources_approved: number
  sources_rejected: number
  joined_existing?: boolean
}

export interface ScanDetail extends ScanSummary {
  sources: Array<{ source_name: string; status: string; detail: string | null }>
  batch_id: string | null
  error_detail: string | null
  changes: Record<string, unknown>
}

export interface ScanBatchResponse {
  batch_id: string
  status: string
  scan_ids: string[]
  organization_count: number
  scans: ScanSummary[]
}

export type ApiErrorCode =
  | 'VALIDATION_ERROR'
  | 'AUTH_MISSING'
  | 'AUTH_INVALID'
  | 'AUTH_EXPIRED'
  | 'USER_NOT_PROVISIONED'
  | 'USER_WITHOUT_ROLE'
  | 'INSUFFICIENT_PERMISSION'
  | 'NOT_FOUND'
  | 'SCAN_RATE_LIMITED'
  | 'ADVISOR_RATE_LIMITED'
  | 'INTERNAL_ERROR'

export interface ErrorEnvelope {
  error: {
    code: ApiErrorCode
    message: string
    details: Record<string, unknown>
  }
}
